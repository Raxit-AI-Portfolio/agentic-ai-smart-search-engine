from pathlib import Path

from qdrant_client import QdrantClient

from rag_ingestion.chunking import chunk_document, extract_description
from rag_ingestion.config import settings
from rag_ingestion.corpus_store import upsert_chunks_for_source
from rag_ingestion.embedder import embed_passages
from rag_ingestion.manifest import hash_text, load_manifest, save_manifest
from rag_ingestion.permissions import default_allowed_roles
from rag_ingestion.qdrant_store import delete_by_source, ensure_collection, get_client, upsert_chunks


def needs_ingest(path: Path, manifest: dict) -> bool:
    entry = manifest.get(path.name)
    if entry is None:
        return True
    return entry["hash"] != hash_text(path.read_text(encoding="utf-8"))


def ingest_document(
    path: Path,
    allowed_roles: list[str] | None = None,
    client: QdrantClient | None = None,
    notes: str | None = None,
) -> int:
    client = client or get_client()
    ensure_collection(client)

    text = path.read_text(encoding="utf-8")
    manifest = load_manifest()
    existing = manifest.get(path.name)
    if allowed_roles is None:
        allowed_roles = existing["allowed_roles"] if existing else default_allowed_roles(path.stem)
    # A re-ingest (e.g. the manager "edit" flow re-uploading a file without
    # touching the note) should keep the existing note rather than blank it.
    if notes is None:
        notes = existing.get("notes") if existing else None

    chunks = chunk_document(path.name, text, allowed_roles)
    vectors = embed_passages([chunk.text for chunk in chunks])

    delete_by_source(client, path.name)
    upsert_chunks(client, chunks, vectors)
    upsert_chunks_for_source(path.name, chunks)

    manifest[path.name] = {
        "hash": hash_text(text),
        "allowed_roles": allowed_roles,
        "description": extract_description(text),
        "notes": notes,
    }
    save_manifest(manifest)
    return len(chunks)


def list_documents() -> list[dict]:
    manifest = load_manifest()
    return [
        {
            "filename": filename,
            "allowed_roles": entry["allowed_roles"],
            "notes": entry.get("notes"),
            "description": entry.get("description"),
        }
        for filename, entry in sorted(manifest.items())
    ]


def delete_document(filename: str, client: QdrantClient | None = None) -> bool:
    client = client or get_client()
    doc_path = Path(settings.documents_dir) / filename
    manifest = load_manifest()

    if filename not in manifest and not doc_path.exists():
        return False

    delete_by_source(client, filename)
    upsert_chunks_for_source(filename, [])
    manifest.pop(filename, None)
    save_manifest(manifest)
    doc_path.unlink(missing_ok=True)
    return True
