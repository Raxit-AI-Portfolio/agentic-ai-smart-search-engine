from agentic_core.services.mcp_client import call_tool


class ApiCallError(Exception):
    """The downstream API answered with a non-2xx status."""

    def __init__(self, status_code: int):
        super().__init__(f"API returned HTTP {status_code}")
        self.status_code = status_code


async def call_api(
    service: str,
    method: str,
    path: str,
    authorization_header: str,
    params: dict | None = None,
    json: dict | None = None,
) -> dict | list:
    result = await call_tool(
        "api",
        "call_endpoint",
        {
            "service": service,
            "method": method,
            "path": path,
            "authorization_header": authorization_header,
            "params": params,
            "json": json,
        },
    )
    if isinstance(result, dict) and "_http_error" in result:
        raise ApiCallError(result["_http_error"])
    return result


async def list_permissions() -> dict[str, list[str]]:
    return await call_tool("api", "list_api_permissions") or {}


async def describe_objects() -> dict[str, str]:
    return await call_tool("api", "describe_api_endpoints") or {}
