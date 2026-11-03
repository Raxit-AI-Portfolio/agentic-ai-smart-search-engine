import json
from pathlib import Path

from rag_ingestion.chunking import Chunk
from rag_ingestion.config import settings


def _to_dict(chunk: Chunk) -> dict:
    return {
        "id": chunk.id,
        "text": chunk.text,
        "source_file": chunk.source_file,
        "header_path": chunk.header_path,
        "chunk_index": chunk.chunk_index,
        "allowed_roles": chunk.allowed_roles,
    }


def save_corpus(chunks: list[Chunk]) -> None:
    path = Path(settings.corpus_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([_to_dict(chunk) for chunk in chunks], indent=2), encoding="utf-8")


def load_corpus() -> list[dict]:
    path = Path(settings.corpus_path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_chunks_for_source(source_file: str, chunks: list[Chunk]) -> None:
    corpus = [entry for entry in load_corpus() if entry["source_file"] != source_file]
    corpus.extend(_to_dict(chunk) for chunk in chunks)
    path = Path(settings.corpus_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(corpus, indent=2), encoding="utf-8")
