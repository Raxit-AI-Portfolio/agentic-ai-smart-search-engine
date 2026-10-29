import re
from pathlib import Path

from qdrant_client.models import FieldCondition, Filter, MatchValue
from rank_bm25 import BM25Okapi

from agentic_core.models.models import RetrievedChunk
from rag_ingestion.config import settings
from rag_ingestion.corpus_store import load_corpus
from rag_ingestion.embedder import embed_query
from rag_ingestion.manifest import load_manifest
from rag_ingestion.qdrant_store import get_client

TOP_K_VECTOR = 10
TOP_K_BM25 = 10
TOP_K_FINAL = 5
RRF_K = 60


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


_client = get_client()

# Qdrant is queried live on every call, so it always reflects the latest
# uploads/deletes. The BM25 side runs over an in-memory corpus, which would
# otherwise go stale after a manager uploads/deletes a doc via shared-api —
# so it's rebuilt whenever corpus.json's mtime changes, rather than once at
# import time.
_bm25_cache: dict = {"mtime": None, "corpus": [], "corpus_by_id": {}, "bm25": None}


def _load_bm25_state() -> dict:
    path = Path(settings.corpus_path)
    mtime = path.stat().st_mtime if path.exists() else None
    if mtime != _bm25_cache["mtime"]:
        corpus = load_corpus()
        _bm25_cache["mtime"] = mtime
        _bm25_cache["corpus"] = corpus
        _bm25_cache["corpus_by_id"] = {entry["id"]: entry for entry in corpus}
        _bm25_cache["bm25"] = BM25Okapi([_tokenize(entry["text"]) for entry in corpus]) if corpus else None
    return _bm25_cache


def _vector_search(query: str, role: str, top_k: int, source_file: str | None) -> list[str]:
    vector = embed_query(query)
    must = [FieldCondition(key="allowed_roles", match=MatchValue(value=role))]
    if source_file:
        must.append(FieldCondition(key="source_file", match=MatchValue(value=source_file)))
    hits = _client.query_points(
        collection_name=settings.qdrant_collection,
        query=vector,
        limit=top_k,
        query_filter=Filter(must=must),
    ).points
    return [hit.payload["chunk_id"] for hit in hits]


def _bm25_search(query: str, role: str, top_k: int, source_file: str | None, state: dict) -> list[str]:
    if state["bm25"] is None:
        return []
    scores = state["bm25"].get_scores(_tokenize(query))
    ranked = sorted(
        (
            (entry["id"], score)
            for entry, score in zip(state["corpus"], scores)
            if role in entry["allowed_roles"]
            and score > 0
            and (source_file is None or entry["source_file"] == source_file)
        ),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return [chunk_id for chunk_id, _ in ranked[:top_k]]


def _rrf_fuse(*ranked_lists: list[str]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank + 1)
    return scores


def search(query: str, role: str, top_k: int = TOP_K_FINAL, source_file: str | None = None) -> list[RetrievedChunk]:
    state = _load_bm25_state()

    vector_ranked = _vector_search(query, role, TOP_K_VECTOR, source_file)
    bm25_ranked = _bm25_search(query, role, TOP_K_BM25, source_file, state)
    fused_scores = _rrf_fuse(vector_ranked, bm25_ranked)
    fused = sorted(fused_scores, key=fused_scores.get, reverse=True)[:top_k]

    corpus_by_id = state["corpus_by_id"]
    return [
        RetrievedChunk(
            text=corpus_by_id[chunk_id]["text"],
            source_file=corpus_by_id[chunk_id]["source_file"],
            header_path=corpus_by_id[chunk_id]["header_path"],
            score=fused_scores[chunk_id],
        )
        for chunk_id in fused
        if chunk_id in corpus_by_id
    ]


def list_permissions() -> dict[str, list[str]]:
    return {filename: entry["allowed_roles"] for filename, entry in load_manifest().items()}


def describe_objects() -> dict[str, str]:
    # Written by rag_ingestion.ingest.ingest_document (extract_description) —
    # pulled straight from each document's own "Purpose"-style paragraph, not
    # hand-maintained here. Older manifest entries from before this field
    # existed just have no description until the doc is next re-ingested.
    return {filename: entry.get("description", "") for filename, entry in load_manifest().items()}
