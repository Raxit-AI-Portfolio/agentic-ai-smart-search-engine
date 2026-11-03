import httpx
from mcp.server.fastmcp import FastMCP

from agentic_core.mcp_servers.api_server.backend import call_api, describe_objects, list_permissions

mcp = FastMCP("api-server", host="127.0.0.1", port=8012)


@mcp.tool()
async def call_endpoint(
    service: str,
    method: str,
    path: str,
    authorization_header: str,
    params: dict | None = None,
    json: dict | None = None,
) -> dict | list:
    """Call an endpoint on the customer-api or operations-api, forwarding the caller's bearer token.
    A non-2xx answer is returned as {"_http_error": status_code} so the client can tell 404 from 422."""
    try:
        return await call_api(service, method, path, authorization_header, params, json)
    except httpx.HTTPStatusError as exc:
        return {"_http_error": exc.response.status_code}


@mcp.tool()
async def list_api_permissions() -> dict[str, list[str]]:
    """List each customer-api/operations-api endpoint and the roles allowed to call it."""
    return await list_permissions()


@mcp.tool()
async def describe_api_endpoints() -> dict[str, str]:
    """Each endpoint's docstring, keyed like list_api_permissions."""
    return await describe_objects()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
