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

    # Logging Settings
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_file_path: str = "logs/app.log"  # Log file path
    log_rotation: str = "100 MB"  # Rotate when file reaches 100MB
    log_retention: str = "30 days"  # Keep logs for 30 days
    log_format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # Qdrant Settings
    qdrant_host: str = "qdrant-server"
    qdrant_port: int = 6333

    # Multiple Collection Names for different document types
    qdrant_collection_regulations: str = "rag-regulations"  # PDF/Markdown/Word
    qdrant_collection_hazard_db: str = "rag-hazard-db"  # Excel files
    qdrant_collection_qa: str = "rag-qa-knowledge"  # QA system knowledge base

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

    # Deployment Mode: 'local' or 'aliyun'
    deployment_mode: str = "aliyun"  # Set via environment variable DEPLOYMENT_MODE

    # Aliyun DashScope API Settings (for aliyun mode)
    dashscope_api_key: str = ""  # Set via environment variable DASHSCOPE_API_KEY
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # VLM Model for Image Analysis (Multimodal)
    vlm_model_name: str = "qwen3-vl-plus"  # Aliyun multimodal model (aliyun mode)

    # LLM Model for RAG QA (Text-only)
    llm_model_name: str = "qwen3-max-preview"  # Aliyun text model (aliyun mode)

    # Local vLLM Settings (for local mode)
    vllm_llm_url: str = "http://vllm-qwen-vl:8000/v1"  # Local vLLM service URL
    vllm_llm_model: str = "/model/Qwen3-VL-4B"  # Local model path (serves both VLM and LLM)

    # Embedding Settings (Self-hosted)
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

    # LLM Settings (Aliyun API)
    llm_temperature: float = 0.0
    llm_max_tokens: int = 3500  # Max tokens for LLM response
    vlm_temperature: float = 0.0  # VLM temperature for image analysis

    # RAG Retrieval Settings
    retrieval_score_threshold: float = 0.2  # Lowered: Let reranker do the filtering
    rerank_score_threshold: float = 0.3  # Minimum rerank score for filtering
    fetch_k_multiplier: int = 100  # Increased: Fetch more candidates for reranking

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
    max_doc_length: int = 1500  # Max characters per document in context
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

    # Document List Pagination Settings
    documents_default_page_size: int = 20  # Default items per page
    documents_max_page_size: int = 100  # Maximum items per page
    documents_min_page_size: int = 1  # Minimum items per page

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
        "重大隐患",
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
