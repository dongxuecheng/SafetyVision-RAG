"""PDF document processor"""

from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base import DocumentProcessor


class PDFProcessor(DocumentProcessor):
    """PDF处理：传统Chunking策略"""

    @staticmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process PDF file using traditional chunking strategy
        
        Args:
            file_path: Path to PDF file
            metadata: Metadata to attach to documents
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of Document objects with chunked content
        """
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        # Add metadata to all documents
        for doc in docs:
            doc.metadata.update(metadata)

        # Split documents into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
        )
        return splitter.split_documents(docs)
