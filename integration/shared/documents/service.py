from pathlib import Path

from fastapi.concurrency import run_in_threadpool

from rag_ingestion.config import settings
from rag_ingestion.ingest import delete_document, ingest_document, list_documents

VALID_ROLES = {"customer", "worker", "manager"}


async def upload_document(filename: str, content: bytes, allowed_roles: list[str], notes: str | None = None) -> int:
    path = Path(settings.documents_dir) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return await run_in_threadpool(ingest_document, path, allowed_roles, None, notes)


async def get_documents() -> list[dict]:
    return await run_in_threadpool(list_documents)


async def remove_document(filename: str) -> bool:
    return await run_in_threadpool(delete_document, filename)
