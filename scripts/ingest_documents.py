import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag_ingestion.config import settings
from rag_ingestion.ingest import ingest_document, needs_ingest
from rag_ingestion.manifest import load_manifest
from rag_ingestion.qdrant_store import ensure_collection, get_client


def ingest() -> None:
    client = get_client()
    ensure_collection(client)

    ingested, skipped = 0, 0
    for doc_path in sorted(Path(settings.documents_dir).glob("*.md")):
        if not needs_ingest(doc_path, load_manifest()):
            print(f"skip  {doc_path.name} (already ingested, unchanged)")
            skipped += 1
            continue

        chunk_count = ingest_document(doc_path, client=client)
        print(f"ingest {doc_path.name} ({chunk_count} chunks)")
        ingested += 1

    print(f"Done: {ingested} ingested, {skipped} skipped (up to date)")


if __name__ == "__main__":
    ingest()
