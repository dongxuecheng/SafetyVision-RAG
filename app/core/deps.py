"""
Dependencies for dependency injection
"""

from functools import lru_cache
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import cohere

from app.core.config import get_settings


@lru_cache()
def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance"""
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


@lru_cache()
def get_llm() -> ChatOpenAI:
    """Get LLM instance"""
    settings = get_settings()
    return ChatOpenAI(
        model_name=settings.vllm_model_name,
        api_key="not-needed",
        base_url=settings.vllm_chat_url,
        temperature=0,
        max_tokens=4096,  # Increased to 4096 for structured output generation
    )


@lru_cache()
def get_embeddings() -> OpenAIEmbeddings:
    """Get embeddings instance"""
    settings = get_settings()
    return OpenAIEmbeddings(
        model=settings.vllm_embed_model,
        api_key="not-needed",
        base_url=settings.vllm_embed_url,
    )


def get_vector_store() -> QdrantVectorStore:
    """Get vector store instance"""
    settings = get_settings()
    return QdrantVectorStore(
        client=get_qdrant_client(),
        collection_name=settings.qdrant_collection,
        embedding=get_embeddings(),
    )


def ensure_collection() -> None:
    """Ensure Qdrant collection exists"""
    settings = get_settings()
    client = get_qdrant_client()
    try:
        client.get_collection(settings.qdrant_collection)
    except:
        client.create_collection(
            collection_name=settings.qdrant_collection,
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
