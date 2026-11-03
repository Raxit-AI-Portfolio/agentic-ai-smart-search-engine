from typing import Any, Literal

from langsmith import traceable
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from agentic_core.configs.config import settings

McpServer = Literal["sql", "rag", "api"]

_URLS: dict[McpServer, str] = {
    "sql": settings.sql_mcp_url,
    "rag": settings.rag_mcp_url,
    "api": settings.api_mcp_url,
}


class McpToolError(RuntimeError):
    """The MCP server ran the tool and it reported an error."""


# One short-lived session per call: sessions are bound to the event loop that
# opened them, and loops differ between main.py, Streamlit and pytest-asyncio.
# The extra handshake is negligible on localhost.
@traceable(run_type="tool", name="mcp_call")
async def call_tool(server: McpServer, tool: str, arguments: dict[str, Any] | None = None) -> Any:
    async with streamablehttp_client(_URLS[server]) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments or {})

    if result.isError:
        message = " ".join(block.text for block in result.content if getattr(block, "text", None))
        raise McpToolError(f"{server}.{tool}: {message}")

    payload = result.structuredContent
    # FastMCP wraps non-object returns (list, union) as {"result": ...}.
    if isinstance(payload, dict) and set(payload) == {"result"}:
        return payload["result"]
    return payload
