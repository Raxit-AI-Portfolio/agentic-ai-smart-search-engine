from mcp.server.fastmcp import FastMCP

from agentic_core.mcp_servers.sql_server.backend import describe_objects, execute_query, list_permissions

mcp = FastMCP("sql-server", host="127.0.0.1", port=8010)


@mcp.tool()
async def execute_sql(database: str, query: str, params: list[str] | None = None) -> list[dict]:
    """Execute a SQL query against customerdb or operationsdb (manager access only). Params are positional ($1, $2, ...) as text."""
    return await execute_query(database, query, params)


@mcp.tool()
async def list_sql_permissions() -> dict[str, list[str]]:
    """List each ss-schema function/view (in customerdb and operationsdb) and the roles allowed to call it."""
    return await list_permissions()


@mcp.tool()
async def describe_sql_objects() -> dict[str, str]:
    """Each ss-schema function/view's live signature or columns plus its comment, keyed like list_sql_permissions."""
    return await describe_objects()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
