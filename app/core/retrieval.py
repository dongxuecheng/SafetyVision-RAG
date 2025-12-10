"""
Advanced retrieval strategies for RAG

Implements various retrieval techniques following LangChain best practices
"""

from typing import List, Optional
from langchain_core.documents import Document
import cohere


class SafetyRetriever:
    """Advanced retriever with multiple strategies"""

    def __init__(self, vector_store, reranker_client: Optional[cohere.ClientV2] = None):
        self.vector_store = vector_store
        self.reranker = reranker_client

    async def retrieve_with_score(
        self, query: str, k: int = 5, score_threshold: Optional[float] = None
    ) -> List[Document]:
        """
        Retrieve with similarity scores and store them in document metadata

        Optionally filter by minimum score threshold
        """
        # Use similarity_search_with_score to get scores
        if score_threshold:
            results = await self.vector_store.asimilarity_search_with_score(
                query, k=k, score_threshold=score_threshold
            )
        else:
            results = await self.vector_store.asimilarity_search_with_score(query, k=k)

        # Store scores in document metadata
        docs_with_scores = []
        for doc, score in results:
            doc.metadata["score"] = score
            docs_with_scores.append(doc)

        return docs_with_scores

    async def retrieve_with_rerank(
        self,
        query: str,
        k: int = 3,
        fetch_k: int = 30,
        model: str = "/model/bge-reranker-v2-m3",
        rerank_score_threshold: float = 0.3,
    ) -> List[Document]:
        """
        Two-stage retrieval: Similarity (coarse) → Rerank (fine)

        Args:
            query: Query text
            k: Number of final documents to return
            fetch_k: Number of candidates to fetch (should >= k, default 30 for better coverage)
            model: Rerank model name
            rerank_score_threshold: Minimum rerank score to keep documents (default 0.3)

        Returns:
            Reranked top_k documents filtered by score threshold
        """
        # Stage 1: Coarse ranking - retrieve candidates with similarity search
        candidates = await self.retrieve_with_score(query, k=fetch_k)

        if not self.reranker or len(candidates) <= k:
            # No reranker or insufficient candidates, return as-is
            return candidates[:k]

        # Stage 2: Fine ranking - rerank with Rerank model
        try:
            # Extract document content
            documents_text = [doc.page_content for doc in candidates]

            # Import settings for top_n multiplier
            from app.core.config import get_settings

            settings = get_settings()

            # Call Rerank API
            rerank_response = self.reranker.rerank(
                model=model,
                query=query,
                documents=documents_text,
                top_n=k * settings.rerank_top_n_multiplier,
            )

            # Filter by rerank score threshold and reorder
            reranked_docs = []
            for result in rerank_response.results:
                # Only keep documents above threshold
                if (
                    hasattr(result, "relevance_score")
                    and result.relevance_score >= rerank_score_threshold
                ):
                    doc = candidates[result.index]
                    # Store rerank score in metadata for later use
                    doc.metadata["score"] = result.relevance_score
                    reranked_docs.append(doc)
                elif not hasattr(result, "relevance_score"):
                    # Fallback: if no score attribute, keep all (backwards compatibility)
                    reranked_docs.append(candidates[result.index])

            # Return top k from filtered results
            return reranked_docs[:k]

        except Exception as e:
            # Fallback: if rerank fails, return similarity results
            print(f"Rerank failed: {e}, falling back to similarity")
            return candidates[:k]

    async def retrieve_with_fallback(
        self,
        query: str,
        k: int = 5,
        score_threshold: float = 0.65,
    ) -> List[Document]:
        """
        Smart fallback: prioritize Rerank with score filtering, fallback to similarity search

        Recommended for production use

        Args:
            query: Search query
            k: Number of documents to return
            score_threshold: Minimum similarity score for retrieval (default 0.65)
        """
        if self.reranker:
            try:
                # Import settings to get fetch_k multiplier
                from app.core.config import get_settings

                settings = get_settings()

                # Use configurable fetch_k for better coverage
                return await self.retrieve_with_rerank(
                    query,
                    k=k,
                    fetch_k=k * settings.fetch_k_multiplier,
                    rerank_score_threshold=settings.rerank_score_threshold,
                )
            except Exception as e:
                print(f"Rerank unavailable, falling back to similarity search: {e}")

        # Fallback to similarity search with score threshold
        try:
            return await self.retrieve_with_score(
                query, k=k, score_threshold=score_threshold
            )
        except Exception as e:
            # Last resort: similarity without threshold
            print(f"Similarity with threshold failed ({e}), using basic similarity")
            return await self.retrieve_with_score(query, k=k)
