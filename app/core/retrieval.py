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

    async def retrieve_with_mmr(
        self, query: str, k: int = 5, fetch_k: int = 10, lambda_mult: float = 0.7
    ) -> List[Document]:
        """
        Retrieve using Maximal Marginal Relevance

        MMR balances relevance and diversity to avoid redundant results

        Args:
            query: Search query
            k: Number of documents to return
            fetch_k: Number of candidates to fetch before MMR selection
            lambda_mult: Balance between relevance (1.0) and diversity (0.0)
        """
        retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": fetch_k, "lambda_mult": lambda_mult},
        )
        return await retriever.ainvoke(query)

    async def retrieve_with_score(
        self, query: str, k: int = 5, score_threshold: Optional[float] = None
    ) -> List[Document]:
        """
        Retrieve with similarity scores

        Optionally filter by minimum score threshold
        """
        retriever = self.vector_store.as_retriever(
            search_type=(
                "similarity_score_threshold" if score_threshold else "similarity"
            ),
            search_kwargs=(
                {"k": k, "score_threshold": score_threshold}
                if score_threshold
                else {"k": k}
            ),
        )
        return await retriever.ainvoke(query)

    async def retrieve_with_rerank(
        self,
        query: str,
        k: int = 3,
        fetch_k: int = 10,
        model: str = "/model/bge-reranker-v2-m3",
    ) -> List[Document]:
        """
        Two-stage retrieval: MMR (coarse) → Rerank (fine)

        Args:
            query: Query text
            k: Number of final documents to return
            fetch_k: Number of candidates to fetch (should >= k)
            model: Rerank model name

        Returns:
            Reranked top_k documents
        """
        # Stage 1: Coarse ranking - retrieve candidates with MMR
        candidates = await self.retrieve_with_mmr(query, k=fetch_k)

        if not self.reranker or len(candidates) <= k:
            # No reranker or insufficient candidates, return as-is
            return candidates[:k]

        # Stage 2: Fine ranking - rerank with Rerank model
        try:
            # Extract document content
            documents_text = [doc.page_content for doc in candidates]

            # Call Rerank API
            rerank_response = self.reranker.rerank(
                model=model, query=query, documents=documents_text, top_n=k
            )

            # Reorder original Document objects based on rerank results
            reranked_docs = [
                candidates[result.index] for result in rerank_response.results
            ]

            return reranked_docs

        except Exception as e:
            # Fallback: if rerank fails, return MMR results
            print(f"Rerank failed: {e}, falling back to MMR")
            return candidates[:k]

    async def retrieve_with_fallback(self, query: str, k: int = 5) -> List[Document]:
        """
        Smart fallback: prioritize Rerank, fallback to MMR on failure

        Recommended for production use
        """
        if self.reranker:
            try:
                return await self.retrieve_with_rerank(query, k=k, fetch_k=k * 3)
            except Exception as e:
                print(f"Rerank unavailable, falling back to MMR: {e}")

        # Fallback to MMR
        try:
            return await self.retrieve_with_mmr(query, k=k)
        except Exception as e:
            print(f"MMR failed ({e}), falling back to similarity search")
            return await self.retrieve_with_score(query, k=k)
