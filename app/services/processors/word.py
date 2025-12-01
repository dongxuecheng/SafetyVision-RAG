"""Word document processors"""

import subprocess
import shutil
from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from docx import Document as DocxDocument

from .base import DocumentProcessor


class WordProcessor(DocumentProcessor):
    """Word (.docx) 处理：传统Chunking策略"""

    @staticmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process DOCX file using traditional chunking strategy

        Args:
            file_path: Path to DOCX file
            metadata: Metadata to attach to documents
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks

        Returns:
            List of Document objects with chunked content
        """
        doc = DocxDocument(file_path)
        content = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())

        document = Document(page_content=content, metadata=metadata)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
        )
        return splitter.split_documents([document])


class LegacyWordProcessor(DocumentProcessor):
    """旧版Word (.doc) 处理：使用antiword转换为文本，传统Chunking策略"""

    @staticmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process legacy DOC file using antiword tool

        Args:
            file_path: Path to DOC file
            metadata: Metadata to attach to documents
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks

        Returns:
            List of Document objects with chunked content

        Raises:
            ValueError: If antiword is not installed or processing fails
        """
        # 检查 antiword 是否安装
        antiword_path = shutil.which("antiword")
        if not antiword_path:
            raise ValueError(
                "antiword 工具未安装或未找到。"
                "请确保系统已安装 antiword: apt-get install antiword"
            )

        try:
            # 使用 antiword 命令行工具提取文本
            result = subprocess.run(
                [antiword_path, file_path],
                capture_output=True,
                text=True,
                timeout=60,  # 设置超时保护
                check=False,  # 不自动抛出异常，手动处理
            )

            # 检查返回码
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                raise ValueError(
                    f"antiword 执行失败 (返回码: {result.returncode}): {error_msg}"
                )

            content = result.stdout

        except subprocess.TimeoutExpired:
            raise ValueError("处理 .doc 文件超时，文件可能太大或格式复杂")
        except Exception as e:
            raise ValueError(f"处理 .doc 文件时出错: {str(e)}")

        if not content or not content.strip():
            raise ValueError("无法从 .doc 文件中提取文本内容，文件可能为空或格式不支持")

        document = Document(page_content=content, metadata=metadata)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
        )
        return splitter.split_documents([document])
