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
        "安全管理",
        "文明施工",
        "脚手架工程",
        "基坑工程",
        "模板工程",
        "高处作业",
        "安全防护",
        "施工用电",
        "起重吊装",
        "施工机具",
        "交叉作业",
        "有限空间",
        "生活营地",
        "危险物品管理",
        "爆破作业",
        "地下工程",
        "围堰工程",
        "施工道路与交通",
        "消防安全",
        "其他",
    ]

    hazard_levels: List[str] = [
        "一般隐患",
        "重要隐患",
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
