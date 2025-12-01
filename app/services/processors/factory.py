"""Factory for creating document processors based on file type"""

from pathlib import Path
from typing import List, Dict, Any

from langchain_core.documents import Document

from .pdf import PDFProcessor
from .word import WordProcessor, LegacyWordProcessor
from .excel import ExcelProcessor, LegacyExcelProcessor


class DocumentProcessorFactory:
    """Factory for creating document processors based on file type"""

    @staticmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """Process document based on file extension"""
        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            return PDFProcessor.process(file_path, metadata, chunk_size, chunk_overlap)
        elif ext == ".docx":
            return WordProcessor.process(file_path, metadata, chunk_size, chunk_overlap)
        elif ext == ".doc":
            return LegacyWordProcessor.process(
                file_path, metadata, chunk_size, chunk_overlap
            )
        elif ext == ".xlsx":
            return ExcelProcessor.process(file_path, metadata)
        elif ext == ".xls":
            return LegacyExcelProcessor.process(file_path, metadata)
        else:
            raise ValueError(
                f"不支持的文件类型: {ext}。支持的格式: .pdf, .docx, .doc, .xlsx, .xls"
            )

    @staticmethod
    def get_supported_extensions() -> List[str]:
        """Get list of supported file extensions"""
        return [".pdf", ".docx", ".doc", ".xlsx", ".xls"]
