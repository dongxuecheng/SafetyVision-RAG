"""
Dependencies for dependency injection
"""

from functools import lru_cache
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import cohere
from loguru import logger

from app.core.config import get_settings


@lru_cache()
def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance"""
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


@lru_cache()
def get_llm() -> ChatOpenAI:
    """
    Get Multimodal LLM instance

    Supports two deployment modes:
    - 'aliyun': Use Aliyun DashScope API
    - 'local': Use local vLLM service
    """
    settings = get_settings()
    import os

    if settings.deployment_mode == "aliyun":
        logger.info("Initializing LLM with Aliyun DashScope API")
        api_key = settings.dashscope_api_key or os.getenv("DASHSCOPE_API_KEY", "")

        if not api_key:
            raise ValueError(
                "DashScope API Key not found. "
                "Please set DASHSCOPE_API_KEY environment variable or configure it in settings."
            )

        return ChatOpenAI(
            model_name=settings.llm_model_name,
            api_key=api_key,
            base_url=settings.dashscope_base_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False}
            }
        )
    else:  # local mode
        logger.info("Initializing LLM with local vLLM service")
        return ChatOpenAI(
            model_name=settings.vllm_llm_model,
            api_key="EMPTY",  # vLLM doesn't require API key
            base_url=settings.vllm_llm_url,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            extra_body={
                "chat_template_kwargs": {"enable_thinking": False}
            }
        )

@lru_cache()
def get_vlm() -> ChatOpenAI:
    """
    Since models are now natively multimodal, get_vlm returns exactly what get_llm does.
    Preserved for backward compatibility.
    """
    return get_llm()


@lru_cache()
def get_embeddings() -> OpenAIEmbeddings:
    """Get embeddings instance"""
    settings = get_settings()
    return OpenAIEmbeddings(
        model=settings.vllm_embed_model,
        api_key="not-needed",
        base_url=settings.vllm_embed_url,
    )


def get_vector_store(collection_type: str = "regulations") -> QdrantVectorStore:
    """Get vector store instance for specific collection type

    Args:
        collection_type: Type of collection - 'regulations', 'hazard_db', or 'qa'

    Returns:
        QdrantVectorStore instance
    """
    settings = get_settings()

    # Map collection type to collection name
    collection_map = {
        "regulations": settings.qdrant_collection_regulations,
        "hazard_db": settings.qdrant_collection_hazard_db,
        "qa": settings.qdrant_collection_qa,  # New QA collection
    }

    collection_name = collection_map.get(
        collection_type, settings.qdrant_collection_regulations
    )

    return QdrantVectorStore(
        client=get_qdrant_client(),
        collection_name=collection_name,
        embedding=get_embeddings(),
    )


def ensure_collection(collection_type: str = "all") -> None:
    """Ensure Qdrant collection(s) exist

    Args:
        collection_type: 'all', 'regulations', 'hazard_db', or 'qa'
    """
    settings = get_settings()
    client = get_qdrant_client()

    # Determine which collections to create
    collections_to_create = []
    if collection_type == "all":
        collections_to_create = [
            settings.qdrant_collection_regulations,
            settings.qdrant_collection_hazard_db,
            settings.qdrant_collection_qa,  # Include QA collection
        ]
    elif collection_type == "regulations":
        collections_to_create = [settings.qdrant_collection_regulations]
    elif collection_type == "hazard_db":
        collections_to_create = [settings.qdrant_collection_hazard_db]
    elif collection_type == "qa":
        collections_to_create = [settings.qdrant_collection_qa]

    # Create collections if they don't exist
    for collection_name in collections_to_create:
        try:
            client.get_collection(collection_name)
        except:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )


@lru_cache()
def get_reranker_client() -> cohere.ClientV2:
    """
    Get Cohere Rerank client instance (connected to vLLM)

    vLLM's /v1/rerank endpoint is compatible with Cohere API
    """
    settings = get_settings()
    rerank_url = settings.vllm_rerank_url

    return cohere.ClientV2(
        api_key="dummy-key", base_url=rerank_url  # vLLM doesn't validate API keys
    )


def get_document_service():
    """Get document service instance for dependency injection"""
    from app.services.document_service import DocumentService

    return DocumentService()


def get_analysis_service():
    """Get analysis service instance for dependency injection"""
    from app.services.analysis_service import AnalysisService

    return AnalysisService()
