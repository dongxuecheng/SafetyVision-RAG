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

    # Multiple Collection Names for different document types
    qdrant_collection_regulations: str = "rag-regulations"  # PDF/Markdown/Word
    qdrant_collection_hazard_db: str = "rag-hazard-db"  # Excel files

    # Excel Processing Settings
    excel_rows_per_chunk: int = 10  # Merge N rows into one chunk to reduce total chunks
    excel_key_fields: List[str] = [
        "隐患问题",
        "隐患描述",
        "整改措施",
        "整改要求",
        "依据条款",
        "规范依据",
        "隐患类别",
        "隐患级别",
        "检查项目",
        "检查内容",
        "违规行为",
        "处理措施",
        "参考依据",
        "条文内容",
        "规范条文",
        "隐患整改要求",
    ]  # Only index these key fields from Excel

    # VLM Settings
    vllm_chat_url: str = "http://vllm-qwen-vl:8000/v1"
    vllm_model_name: str = "/model/qwen3-vl-4b"

    # Embedding Settings
    vllm_embed_url: str = "http://vllm-bge-m3:8000/v1"
    vllm_embed_model: str = "/model/bge-m3"

    # Rerank Settings
    vllm_rerank_url: str = "http://vllm-bge-reranker:8000"
    vllm_rerank_model: str = "/model/bge-reranker-v2-m3"
    rerank_top_n_multiplier: int = 10  # top_n = k * multiplier for rerank candidates

    # File Upload Settings
    max_file_size: int = 500 * 1024 * 1024  # 50MB
    max_files: int = 10

    # Text Processing Settings
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # LLM Settings
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096  # Max tokens for LLM response

    # RAG Retrieval Settings
    retrieval_score_threshold: float = 0.4  # Minimum similarity score for relevance
    rerank_score_threshold: float = 0.3  # Minimum rerank score for filtering
    fetch_k_multiplier: int = 50  # Multiplier for fetch_k (k * multiplier)

    # Multi-Collection Retrieval Settings
    regulations_retrieval_k: int = (
        5  # Number of docs to retrieve from regulations collection
    )
    regulations_score_threshold: float = 0.5  # Score threshold for regulations
    regulations_min_sufficient_docs: int = (
        2  # Min docs needed for regulations to be sufficient
    )
    hazard_db_retrieval_k: int = (
        5  # Number of docs to retrieve from hazard_db collection
    )
    hazard_db_score_threshold: float = 0.4  # Score threshold for hazard_db
    max_combined_docs: int = 5  # Max combined docs per hazard

    # Document Formatting Settings
    max_doc_length: int = 600  # Max characters per document in context
    max_context_length: int = 3000  # Max total context length for LLM

    # Hard Threshold for Low Quality Retrieval
    min_retrieval_score: float = 0.3  # Below this score, return "no relevant docs"

    # Confidence Level Thresholds
    high_confidence_threshold: float = 0.7  # ≥0.7 = high confidence
    medium_confidence_threshold: float = 0.5  # 0.5-0.7 = medium confidence
    # Below medium = low confidence

    # Qdrant Query Settings
    qdrant_scroll_limit: int = 100  # Default scroll limit for listing documents
    qdrant_scroll_limit_large: int = 10000  # Limit for bulk operations (delete)

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
