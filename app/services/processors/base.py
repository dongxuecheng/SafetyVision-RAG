"""Base classes for document processors"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from langchain_core.documents import Document


class DocumentProcessor(ABC):
    """Abstract base class for document processors"""

    @staticmethod
    @abstractmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """Process document and return list of Document objects"""
        pass
