import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from rag_ingestion.chunking import Chunk
from rag_ingestion.config import settings

_ID_NAMESPACE = uuid.UUID("a8c9a0d2-6b7b-4a3b-9c1e-1c6e1f6f8b1a")


def _point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(_ID_NAMESPACE, chunk_id))


def get_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url)


def recreate_collection(client: QdrantClient) -> None:
    client.recreate_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
    )


def ensure_collection(client: QdrantClient) -> None:
    if not client.collection_exists(settings.qdrant_collection):
        recreate_collection(client)


def delete_by_source(client: QdrantClient, source_file: str) -> None:
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=Filter(must=[FieldCondition(key="source_file", match=MatchValue(value=source_file))]),
    )


def upsert_chunks(client: QdrantClient, chunks: list[Chunk], vectors: list[list[float]]) -> None:
    points = [
        PointStruct(
            id=_point_id(chunk.id),
            vector=vector,
            payload={
                "chunk_id": chunk.id,
                "text": chunk.text,
                "source_file": chunk.source_file,
                "header_path": chunk.header_path,
                "chunk_index": chunk.chunk_index,
                "allowed_roles": chunk.allowed_roles,
            },
        )
        for chunk, vector in zip(chunks, vectors)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)
