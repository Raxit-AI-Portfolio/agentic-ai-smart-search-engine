from mcp.server.fastmcp import FastMCP

from agentic_core.services.rag_service import TOP_K_FINAL, list_permissions, search

mcp = FastMCP("rag-server")


@mcp.tool()
def search_documents(query: str, role: str, top_k: int = TOP_K_FINAL) -> list[dict]:
    """Hybrid (vector + BM25) search over the RAG document store, scoped to the caller's role."""
    return [chunk.model_dump() for chunk in search(query, role, top_k)]


@mcp.tool()
def list_document_permissions() -> dict[str, list[str]]:
    """List each RAG document and the roles allowed to retrieve it."""
    return list_permissions()


if __name__ == "__main__":
    mcp.run()
