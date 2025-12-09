"""
Application configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    app_name: str = "SafetyVision-RAG"
    app_version: str = "2.0.0"
    debug: bool = False

    # Qdrant Settings
    qdrant_host: str = "qdrant-server"
    qdrant_port: int = 6333
    qdrant_collection: str = "rag-test"

    # VLM Settings
    vllm_chat_url: str = "http://vllm-qwen-vl:8000/v1"
    vllm_model_name: str = "/model/qwen3-vl-4b"

    # Embedding Settings
    vllm_embed_url: str = "http://vllm-bge-m3:8000/v1"
    vllm_embed_model: str = "/model/bge-m3"

    # Rerank Settings
    vllm_rerank_url: str = "http://vllm-bge-reranker:8000"
    vllm_rerank_model: str = "/model/bge-reranker-v2-m3"

    # File Upload Settings
    max_file_size: int = 500 * 1024 * 1024  # 50MB
    max_files: int = 10

    # Text Processing Settings
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # RAG Retrieval Settings
    retrieval_score_threshold: float = 0.65  # Minimum similarity score for relevance
    rerank_score_threshold: float = 0.3  # Minimum rerank score for filtering

    # Hazard Classification Settings
    hazard_categories: List[str] = [
        "高处坠落",
        "物体打击",
        "机械伤害",
        "起重伤害",
        "触电",
        "坍塌",
        "火灾",
        "中毒窒息",
        "其他伤害",
    ]

    hazard_levels: List[str] = [
        "A级-重大隐患",
        "B级-较大隐患",
        "C级-一般隐患",
        "D级-轻微隐患",
    ]

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
