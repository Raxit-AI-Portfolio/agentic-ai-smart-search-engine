import asyncio

from mcp.server.fastmcp import FastMCP

from agentic_core.mcp_servers.rag_server.backend import TOP_K_FINAL, describe_objects, list_permissions, search

mcp = FastMCP("rag-server", host="127.0.0.1", port=8011)


@mcp.tool()
async def search_documents(
    query: str, role: str, top_k: int = TOP_K_FINAL, source_file: str | None = None
) -> list[dict]:
    """Hybrid (vector + BM25) search over the RAG document store, scoped to the caller's role and optionally to one document."""
    # embedding + Qdrant + BM25 are blocking; keep them off the server's event loop.
    chunks = await asyncio.to_thread(search, query, role, top_k, source_file)
    return [chunk.model_dump() for chunk in chunks]


@mcp.tool()
async def list_document_permissions() -> dict[str, list[str]]:
    """List each RAG document and the roles allowed to retrieve it."""
    return await asyncio.to_thread(list_permissions)


@mcp.tool()
async def describe_documents() -> dict[str, str]:
    """Each RAG document's purpose description, keyed like list_document_permissions."""
    return await asyncio.to_thread(describe_objects)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
