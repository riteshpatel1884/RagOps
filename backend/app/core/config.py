from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://ragops:ragops@localhost:5432/ragops"

    # Vector store
    qdrant_path: str = "./qdrant_data"
    qdrant_collection: str = "ragops_chunks"

    # LLM
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Retrieval
    top_k: int = 5

    # Storage
    upload_dir: str = "./uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
