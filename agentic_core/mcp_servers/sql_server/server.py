from mcp.server.fastmcp import FastMCP

from agentic_core.services.sql_service import execute_query, list_permissions

mcp = FastMCP("sql-server")


@mcp.tool()
async def execute_sql(database: str, query: str) -> list[dict]:
    """Execute a SQL query against customerdb or operationsdb (manager access only)."""
    return await execute_query(database, query)


@mcp.tool()
async def list_sql_permissions() -> dict[str, list[str]]:
    """List each ss-schema function/view (in customerdb and operationsdb) and the roles allowed to call it."""
    return await list_permissions()


if __name__ == "__main__":
    mcp.run()
