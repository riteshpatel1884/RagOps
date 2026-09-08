from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://ragops:ragops@localhost:5432/ragops"

    # Vector store — set QDRANT_URL to use Qdrant Cloud / a real server;
    # leave it empty to fall back to local embedded mode via QDRANT_PATH.
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_path: str = "./qdrant_data"
    qdrant_collection: str = "ragops_chunks"

    # LLM — using Groq via langchain-groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

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
