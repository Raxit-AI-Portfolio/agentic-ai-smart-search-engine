from mcp.server.fastmcp import FastMCP

from agentic_core.services.api_service import call_api, list_permissions

mcp = FastMCP("api-server")


@mcp.tool()
async def call_endpoint(
    service: str,
    method: str,
    path: str,
    authorization_header: str,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    """Call an endpoint on the customer-api or operations-api, forwarding the caller's bearer token."""
    return await call_api(service, method, path, authorization_header, params, json)


@mcp.tool()
async def list_api_permissions() -> dict[str, list[str]]:
    """List each customer-api/operations-api endpoint and the roles allowed to call it."""
    return await list_permissions()


if __name__ == "__main__":
    mcp.run()
