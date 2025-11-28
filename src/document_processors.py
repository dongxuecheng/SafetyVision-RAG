"""Document processors for multi-format support"""

from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import openpyxl
from docx import Document as DocxDocument


class DocumentProcessorFactory:
    """Factory for creating document processors based on file type"""

    @staticmethod
    def process(
        file_path: str, metadata: Dict[str, Any], chunk_size: int = 1000, chunk_overlap: int = 200
    ) -> List[Document]:
        """Process document based on file extension"""
        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            return PDFProcessor.process(file_path, metadata, chunk_size, chunk_overlap)
        elif ext in [".docx", ".doc"]:
            return WordProcessor.process(file_path, metadata, chunk_size, chunk_overlap)
        elif ext in [".xlsx", ".xls"]:
            return ExcelProcessor.process(file_path, metadata)
        else:
            raise ValueError(f"Unsupported file type: {ext}")


class PDFProcessor:
    """PDF处理：传统Chunking策略"""

    @staticmethod
    def process(
        file_path: str, metadata: Dict[str, Any], chunk_size: int, chunk_overlap: int
    ) -> List[Document]:
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        for doc in docs:
            doc.metadata.update(metadata)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
        )
        return splitter.split_documents(docs)


class WordProcessor:
    """Word处理：传统Chunking策略"""

    @staticmethod
    def process(
        file_path: str, metadata: Dict[str, Any], chunk_size: int, chunk_overlap: int
    ) -> List[Document]:
        doc = DocxDocument(file_path)
        content = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

        document = Document(page_content=content, metadata=metadata)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
        )
        return splitter.split_documents([document])


class ExcelProcessor:
    """
    Excel处理：Row-to-Text策略
    将每行数据结合表头转换为语义文本，保留结构信息
    """

    @staticmethod
    def process(file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        documents = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))

            if not rows:
                continue

            # 第一行作为表头
            headers = [str(h).strip() if h else "" for h in rows[0]]

            # 处理数据行
            for row_idx, row in enumerate(rows[1:], start=2):
                row_data = []
                for header, value in zip(headers, row):
                    if header and value is not None:
                        value_str = (
                            value.strftime("%Y-%m-%d %H:%M:%S")
                            if isinstance(value, datetime)
                            else str(value).strip()
                        )
                        if value_str:
                            row_data.append(f"{header}为{value_str}")

                if row_data:
                    # 生成语义文本
                    text = f"第{row_idx}行数据：{'，'.join(row_data)}。"
                    doc_metadata = {
                        **metadata,
                        "sheet_name": sheet_name,
                        "row_number": row_idx,
                        "content_type": "excel_row",
                    }
                    documents.append(Document(page_content=text, metadata=doc_metadata))

        wb.close()
        return documents
