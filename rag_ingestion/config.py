from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "efsse_docs"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    documents_dir: str = "documents"
    corpus_path: str = "rag_ingestion/data/corpus.json"

    chunk_size: int = 800
    chunk_overlap: int = 100


settings = Settings()
