import ast
import re
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from uuid import UUID

import asyncpg
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from agentic_core.configs.config import settings
from agentic_core.prompts.sql_prompts import SQL_SYSTEM_PROMPT, build_sql_prompt, build_sql_retry_prompt
from agentic_core.state.models.state_models import SqlResult

# The SQL MCP server is manager-only (see agentic_core/models/constants.py's
# ROLE_PERMISSIONS_DELTA) — customer/worker roles query through the customer-api
# and operations-api instead, which enforce access via role-scoped Postgres
# views/functions, not through this direct connection.
_DB_URLS = {
    "customerdb": settings.customerdb_manager_url,
    "operationsdb": settings.operationsdb_manager_url,
}

_pools: dict[str, asyncpg.Pool] = {}


async def _get_pool(database: str) -> asyncpg.Pool:
    if database not in _pools:
        _pools[database] = await asyncpg.create_pool(_DB_URLS[database])
    return _pools[database]


async def execute_query(database: str, query: str, params: list | None = None) -> list[dict]:
    pool = await _get_pool(database)
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *(params or []))
    return [dict(row) for row in rows]


_SS_OBJECTS_QUERY = """
    SELECT
        p.proname AS name,
        'function' AS kind,
        pg_get_function_arguments(p.oid) AS signature,
        pg_get_function_result(p.oid) AS returns,
        obj_description(p.oid, 'pg_proc') AS comment
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'ss'
      -- The SQL server always connects as manager (see module docstring) —
      -- checking real EXECUTE/SELECT grants (rather than assuming every ss
      -- object is usable) keeps not-actually-callable internal helpers like
      -- ss.order_amount out of the catalog manager is offered.
      AND has_function_privilege(p.oid, 'EXECUTE')

    UNION ALL

    SELECT
        c.relname AS name,
        'view' AS kind,
        NULL::text AS signature,
        (
            SELECT string_agg(a.attname || ' ' || format_type(a.atttypid, a.atttypmod), ', ' ORDER BY a.attnum)
            FROM pg_attribute a
            WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
        ) AS returns,
        obj_description(c.oid, 'pg_class') AS comment
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'ss' AND c.relkind = 'v'
      AND has_table_privilege(c.oid, 'SELECT')
"""


async def _fetch_ss_objects(database: str) -> list[asyncpg.Record]:
    pool = await _get_pool(database)
    return await pool.fetch(_SS_OBJECTS_QUERY)


async def list_permissions() -> dict[str, list[str]]:
    # Only manager ever reaches this server (see the module docstring above),
    # so every ss object that passes the grant check above resolves to the
    # same role.
    permissions: dict[str, list[str]] = {}
    for database in _DB_URLS:
        for row in await _fetch_ss_objects(database):
            permissions[f"{database}.{row['name']}"] = ["manager"]
    return permissions


def _describe_row(row: asyncpg.Record) -> str:
    comment = (row["comment"] or "").strip()
    if row["kind"] == "function":
        signature = row["signature"] or ""
        detail = f"call as {row['name']}({signature}) -> returns {row['returns']}"
    else:
        detail = f"columns: {row['returns']}"
    return f"{comment} [{detail}]" if comment else detail


async def describe_objects() -> dict[str, str]:
    """Each ss object's real signature/columns (live-introspected — never
    drifts from the schema) plus its COMMENT ON description, if any — used to
    give the planning and SQL-generation LLM calls a real idea of what a
    resource does and exactly how to call it, instead of guessing from the
    bare object name."""
    descriptions: dict[str, str] = {}
    for database in _DB_URLS:
        for row in await _fetch_ss_objects(database):
            descriptions[f"{database}.{row['name']}"] = _describe_row(row)
    return descriptions


class _GeneratedQuery(BaseModel):
    sql: str
    # Positional asyncpg params ($1, $2, ...) as strings — asyncpg does its own
    # type coercion, and keeping the LLM output to one scalar type avoids
    # structured-output schema issues with a union/Any type.
    params: list[str] = Field(default_factory=list)


@lru_cache
def _sql_generator():
    llm = ChatGoogleGenerativeAI(model=settings.planning_model, google_api_key=settings.google_api_key)
    return llm.with_structured_output(_GeneratedQuery)


MAX_SQL_RETRIES = 1

_CAST_RE = re.compile(r"\$(\d+)::([\w ]+(?:\[\])?)")
_INT_TYPES = {"integer", "int", "int4", "int8", "bigint", "smallint", "int2", "serial", "bigserial"}
_NUMERIC_TYPES = {"numeric", "decimal", "real", "double precision", "float", "float4", "float8"}
_BOOL_TYPES = {"boolean", "bool"}
_DATE_TYPES = {"date"}
_TIMESTAMP_TYPES = {"timestamp", "timestamp without time zone", "timestamp with time zone", "timestamptz"}
_UUID_TYPES = {"uuid"}


def _coerce_scalar(value: str, pg_type: str) -> object:
    try:
        if pg_type in _INT_TYPES:
            return int(value)
        if pg_type in _NUMERIC_TYPES:
            return Decimal(value)
        if pg_type in _BOOL_TYPES:
            return value.strip().lower() in ("t", "true", "1", "yes")
        if pg_type in _DATE_TYPES:
            return date.fromisoformat(value)
        if pg_type in _TIMESTAMP_TYPES:
            return datetime.fromisoformat(value)
        if pg_type in _UUID_TYPES:
            return UUID(value)
    except (ValueError, TypeError):
        return value
    return value


def _coerce_params(query: str, params: list[str]) -> list:
    """asyncpg's binary codecs (int4, date, uuid, ...) require the matching
    native Python type even when the SQL explicitly casts the placeholder —
    Postgres infers the parameter's wire type from that cast, so asyncpg
    still rejects a plain str there. Every LLM-generated param arrives as
    text (see _GeneratedQuery.params) and SQL_SYSTEM_PROMPT tells the LLM to
    cast any non-text placeholder, so convert each param using that same
    cast before executing, instead of sending text asyncpg won't accept."""
    coerced: list = list(params)
    for index, pg_type in _CAST_RE.findall(query):
        position = int(index) - 1
        if position >= len(coerced) or not isinstance(coerced[position], str):
            continue
        pg_type = pg_type.strip().lower()
        if pg_type.endswith("[]"):
            element_type = pg_type[:-2].strip()
            try:
                items = ast.literal_eval(coerced[position])
            except (ValueError, SyntaxError):
                continue
            if isinstance(items, (list, tuple)):
                coerced[position] = [_coerce_scalar(str(item), element_type) for item in items]
            continue
        coerced[position] = _coerce_scalar(coerced[position], pg_type)
    return coerced


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
    generated = _sql_generator().invoke(messages)

    attempt = 0
    while True:
        try:
            rows = await execute_query(database, generated.sql, _coerce_params(generated.sql, generated.params))
        except Exception as exc:
            if attempt >= MAX_SQL_RETRIES:
                return SqlResult(query=generated.sql, error=str(exc), retries=attempt)
            messages += [("ai", generated.sql), ("human", build_sql_retry_prompt(error=str(exc)))]
            generated = _sql_generator().invoke(messages)
            attempt += 1
            continue

        if not rows and attempt < MAX_SQL_RETRIES:
            messages += [("ai", generated.sql), ("human", build_sql_retry_prompt(empty=True))]
            generated = _sql_generator().invoke(messages)
            attempt += 1
            continue

        return SqlResult(query=generated.sql, rows=rows, retries=attempt)
