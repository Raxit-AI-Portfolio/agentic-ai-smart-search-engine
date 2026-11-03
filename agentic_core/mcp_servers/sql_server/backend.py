import ast
import re
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import asyncpg

from agentic_core.configs.config import settings

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


def _coerce_params(query: str, params: list) -> list:
    """asyncpg's binary codecs (int4, date, uuid, ...) require the matching
    native Python type even when the SQL explicitly casts the placeholder —
    Postgres infers the parameter's wire type from that cast, so asyncpg
    still rejects a plain str there. Every LLM-generated param arrives as
    text (and as JSON text over MCP) and SQL_SYSTEM_PROMPT tells the LLM to
    cast any non-text placeholder, so convert each param using that same
    cast before executing, instead of sending text asyncpg won't accept.
    Lives server-side because native types can't cross the MCP boundary."""
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


async def execute_query(database: str, query: str, params: list | None = None) -> list[dict]:
    pool = await _get_pool(database)
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *_coerce_params(query, params or []))
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
    # Only manager ever reaches this server (see the module comment above),
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
