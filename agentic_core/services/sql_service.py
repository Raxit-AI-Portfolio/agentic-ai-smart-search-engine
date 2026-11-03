import re
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from agentic_core.configs.config import settings
from agentic_core.services.mcp_client import call_tool
from agentic_core.prompts.sql_prompts import SQL_SYSTEM_PROMPT, build_sql_prompt, build_sql_retry_prompt
from agentic_core.state.models.state_models import SqlResult


async def execute_query(database: str, query: str, params: list[str] | None = None) -> list[dict]:
    return await call_tool("sql", "execute_sql", {"database": database, "query": query, "params": params or []})


async def list_permissions() -> dict[str, list[str]]:
    return await call_tool("sql", "list_sql_permissions") or {}


async def describe_objects() -> dict[str, str]:
    return await call_tool("sql", "describe_sql_objects") or {}


class _GeneratedQuery(BaseModel):
    sql: str
    # Positional asyncpg params ($1, $2, ...) as strings — asyncpg does its own
    # type coercion, and keeping the LLM output to one scalar type avoids
    # structured-output schema issues with a union/Any type.
    params: list[str] = Field(default_factory=list)


@lru_cache
def _sql_generator():
    llm = ChatGoogleGenerativeAI(
        model=settings.planning_model, google_api_key=settings.google_api_key, timeout=60, max_retries=2
    )
    return llm.with_structured_output(_GeneratedQuery)


MAX_SQL_RETRIES = 1


def _array_param_names(resource_description: str) -> set[str]:
    """Names of parameters the real Postgres signature declares as an array
    (trailing "[]" on the type) — used to tell a genuinely array-typed
    parameter (e.g. get_payments_by_method_ids(p_payment_method_ids
    integer[])) apart from a scalar parameter that a fan-out step is calling
    once per upstream row (see run_text_to_sql)."""
    match = re.search(r"call as \w+\((.*?)\)\s*->", resource_description)
    if not match:
        return set()
    names = set()
    for token in match.group(1).split(","):
        parts = token.strip().split()
        if len(parts) >= 2 and parts[-1].endswith("[]"):
            names.add(parts[0])
    return names


async def run_text_to_sql(resource: str, description: str, inputs: dict, resource_description: str = "") -> SqlResult:
    """Dispatches to _run_single_text_to_sql, except when an input is a list
    for a parameter the signature declares as scalar (not "[]") — that's a
    fan-out ref from an upstream multi-row step (e.g. p_invoice_id per
    invoice), and the target function only accepts one value per call, so
    each list element gets its own call and the rows are merged."""
    array_params = _array_param_names(resource_description)
    fanout_key = next((name for name, value in inputs.items() if isinstance(value, list) and name not in array_params), None)
    if fanout_key is None:
        return await _run_single_text_to_sql(resource, description, inputs, resource_description)

    combined_rows: list[dict] = []
    last_query = ""
    total_retries = 0
    for value in inputs[fanout_key]:
        result = await _run_single_text_to_sql(
            resource, description, {**inputs, fanout_key: value}, resource_description
        )
        if result.error:
            return result
        combined_rows.extend(result.rows)
        last_query = result.query
        total_retries += result.retries
    return SqlResult(query=last_query, rows=combined_rows, retries=total_retries)


async def _run_single_text_to_sql(
    resource: str, description: str, inputs: dict, resource_description: str = ""
) -> SqlResult:
    """Self-correcting text-to-SQL for one plan step: resource is a specific
    "{database}.{ss object}" the planner already chose, so generation only
    has to produce the call (and its params), not pick the target itself.
    resource_description is that object's real signature/columns (from
    describe_objects), given to the generator so it doesn't have to guess the
    parameter count/order from the object name alone. On an execution error
    or an empty result, the error/emptiness is fed back to the LLM for one
    revision before giving up.
    """
    database, _, object_name = resource.partition(".")
    messages = [
        ("system", SQL_SYSTEM_PROMPT),
        ("human", build_sql_prompt(object_name, description, inputs, resource_description)),
    ]
    generated = await _sql_generator().ainvoke(messages)

    attempt = 0
    while True:
        try:
            rows = await execute_query(database, generated.sql, generated.params)
        except Exception as exc:
            if attempt >= MAX_SQL_RETRIES:
                return SqlResult(query=generated.sql, error=str(exc), retries=attempt)
            messages += [("ai", generated.sql), ("human", build_sql_retry_prompt(error=str(exc)))]
            generated = await _sql_generator().ainvoke(messages)
            attempt += 1
            continue

        if not rows and attempt < MAX_SQL_RETRIES:
            messages += [("ai", generated.sql), ("human", build_sql_retry_prompt(empty=True))]
            generated = await _sql_generator().ainvoke(messages)
            attempt += 1
            continue

        return SqlResult(query=generated.sql, rows=rows, retries=attempt)
