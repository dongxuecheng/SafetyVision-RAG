"""PDF document processor"""

from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .base import DocumentProcessor


class PDFProcessor(DocumentProcessor):
    """PDF处理：使用 PyMuPDF4LLM 提取表格和结构化内容"""

    @staticmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process PDF file with table extraction using PyMuPDF4LLM

        使用 PyMuPDF4LLM 处理 PDF，支持：
        - 表格识别（自动转为 Markdown 格式）
        - 标题层级
        - 列表（有序/无序）
        - 保留文档结构

        Args:
            file_path: Path to PDF file
            metadata: Metadata to attach to documents
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks

        Returns:
            List of Document objects with chunked content
        """
        try:
            import pymupdf4llm
        except ImportError:
            raise ImportError(
                "pymupdf4llm is required for PDF processing. "
                "Install it with: pip install pymupdf4llm"
            )

        # 使用 PyMuPDF4LLM 提取 Markdown 格式内容（包含表格）
        md_text = pymupdf4llm.to_markdown(
            file_path,
            page_chunks=False,  # 全文提取，后续用 splitter 切分
            table_strategy="lines_strict",  # 严格表格检测（识别有线条的表格）
            # 其他策略: "lines"（宽松）, "text"（基于文本对齐）, "explicit"（手动指定）
        )

        # 创建 Document 对象
        document = Document(page_content=md_text, metadata=metadata)

        # 使用标准 splitter 切分（保留 Markdown 结构）
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
        )

        chunks = splitter.split_documents([document])

        # 为每个 chunk 添加元数据
        for chunk in chunks:
            chunk.metadata.update(metadata)

        return chunks
