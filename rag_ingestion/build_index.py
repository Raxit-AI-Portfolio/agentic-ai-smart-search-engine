from pathlib import Path

from rag_ingestion.chunking import Chunk, chunk_document
from rag_ingestion.config import settings
from rag_ingestion.corpus_store import save_corpus
from rag_ingestion.embedder import embed_passages
from rag_ingestion.manifest import hash_text, save_manifest
from rag_ingestion.permissions import default_allowed_roles
from rag_ingestion.qdrant_store import get_client, recreate_collection, upsert_chunks


def build() -> None:
    chunks: list[Chunk] = []
    manifest: dict[str, dict] = {}
    for doc_path in sorted(Path(settings.documents_dir).glob("*.md")):
        text = doc_path.read_text(encoding="utf-8")
        allowed_roles = default_allowed_roles(doc_path.stem)
        manifest[doc_path.name] = {"hash": hash_text(text), "allowed_roles": allowed_roles}
        chunks.extend(chunk_document(doc_path.name, text, allowed_roles))

    print(f"Chunked {len(chunks)} chunks from {settings.documents_dir}")

    vectors = embed_passages([chunk.text for chunk in chunks])

    client = get_client()
    recreate_collection(client)
    upsert_chunks(client, chunks, vectors)
    save_corpus(chunks)
    save_manifest(manifest)

    print(f"Indexed {len(chunks)} chunks into Qdrant collection '{settings.qdrant_collection}'")
    print(f"Corpus saved to {settings.corpus_path}")


if __name__ == "__main__":
    build()
