from fastembed import TextEmbedding

from rag_ingestion.config import settings

_model = TextEmbedding(model_name=settings.embedding_model)


def embed_passages(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in _model.embed(texts)]


def embed_query(text: str) -> list[float]:
    return next(_model.query_embed(text)).tolist()
