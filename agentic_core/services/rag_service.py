from agentic_core.models.models import RetrievedChunk
from agentic_core.services.mcp_client import call_tool


async def search(query: str, role: str, source_file: str | None = None) -> list[RetrievedChunk]:
    rows = await call_tool("rag", "search_documents", {"query": query, "role": role, "source_file": source_file})
    return [RetrievedChunk(**row) for row in rows]


async def list_permissions() -> dict[str, list[str]]:
    return await call_tool("rag", "list_document_permissions") or {}


async def describe_objects() -> dict[str, str]:
    return await call_tool("rag", "describe_documents") or {}
