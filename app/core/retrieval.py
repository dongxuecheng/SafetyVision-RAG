"""
Advanced retrieval strategies for RAG

Implements various retrieval techniques following LangChain best practices
"""

from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.runnables import chain


class SafetyRetriever:
    """Advanced retriever with multiple strategies"""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    @chain
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

    @chain
    async def retrieve_with_score(
        self, query: str, k: int = 5, score_threshold: Optional[float] = None
    ) -> List[Document]:
        """
        Retrieve with similarity scores
        
        Optionally filter by minimum score threshold
        """
        retriever = self.vector_store.as_retriever(
            search_type="similarity_score_threshold" if score_threshold else "similarity",
            search_kwargs=(
                {"k": k, "score_threshold": score_threshold}
                if score_threshold
                else {"k": k}
            ),
        )
        return await retriever.ainvoke(query)

    @chain
    async def retrieve_with_fallback(
        self, query: str, k: int = 5
    ) -> List[Document]:
        """
        Retrieve with automatic fallback
        
        Tries MMR first, falls back to similarity search if it fails
        """
        try:
            return await self.retrieve_with_mmr(query, k=k)
        except Exception as e:
            print(f"MMR failed ({e}), falling back to similarity search")
            return await self.retrieve_with_score(query, k=k)
