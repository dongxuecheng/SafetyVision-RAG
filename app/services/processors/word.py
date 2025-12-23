"""Word document processors"""

import subprocess
import shutil
import tempfile
import os
from pathlib import Path
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
    """旧版Word (.doc) 处理：使用LibreOffice转换"""

    @staticmethod
    def _try_libreoffice_convert(file_path: str) -> str:
        """
        使用 LibreOffice 将 .doc 转换为 .docx，然后提取文本

        LibreOffice 优势：
        - 支持 Visio 嵌入图、OLE 对象
        - 支持横向页面和复杂布局
        - 兼容性最强

        Args:
            file_path: .doc 文件路径

        Returns:
            提取的文本内容

        Raises:
            ValueError: 转换失败
        """
        # 查找 LibreOffice 可执行文件
        libreoffice_paths = [
            "libreoffice",
            "soffice",
            "/usr/bin/libreoffice",
            "/usr/bin/soffice",
            "/usr/local/bin/libreoffice",
            "/usr/local/bin/soffice",
            "/opt/libreoffice/program/soffice",
        ]

        soffice_path = None
        for path in libreoffice_paths:
            if shutil.which(path):
                soffice_path = path
                break

        if not soffice_path:
            raise ValueError("LibreOffice 未安装。请安装: apt-get install libreoffice")

        # 创建临时目录用于转换
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            try:
                # 使用 LibreOffice 无头模式转换 .doc -> .docx
                # --headless: 无GUI模式
                # --convert-to docx: 转换为docx格式
                # --outdir: 输出目录
                result = subprocess.run(
                    [
                        soffice_path,
                        "--headless",
                        "--convert-to",
                        "docx",
                        "--outdir",
                        str(temp_dir_path),
                        file_path,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2分钟超时
                    check=False,
                )

                if result.returncode != 0:
                    error_msg = (
                        result.stderr.strip()
                        if result.stderr
                        else result.stdout.strip()
                    )
                    raise ValueError(
                        f"LibreOffice 转换失败 (返回码: {result.returncode}): {error_msg}"
                    )

                # 查找转换后的 .docx 文件
                docx_files = list(temp_dir_path.glob("*.docx"))
                if not docx_files:
                    raise ValueError("LibreOffice 转换成功但未找到输出文件")

                converted_docx = docx_files[0]

                # 使用 python-docx 提取文本（增强版：包含表格、页眉页脚）
                doc = DocxDocument(str(converted_docx))

                # 0. 获取所有表格的段落集合（避免重复提取）
                table_paragraphs = set()
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            for paragraph in cell.paragraphs:
                                table_paragraphs.add(paragraph)

                # 1. 提取段落（排除表格内的段落）
                paragraphs = [
                    p.text
                    for p in doc.paragraphs
                    if p.text.strip() and p not in table_paragraphs
                ]

                # 2. 提取表格（Markdown 格式，含表头）
                tables_text = []
                for table in doc.tables:
                    # 检查表格是否为空
                    if not any(
                        cell.text.strip() for row in table.rows for cell in row.cells
                    ):
                        continue

                    # 提取表头（第一行）
                    if len(table.rows) > 0:
                        first_row = table.rows[0]
                        seen_cells = set()
                        header_cells = []

                        for cell in first_row.cells:
                            cell_id = id(cell)
                            if cell_id not in seen_cells:
                                header_cells.append(cell.text.strip())
                                seen_cells.add(cell_id)

                        if header_cells:
                            # 添加表头行
                            tables_text.append(" | ".join(header_cells))
                            # 添加分隔符行
                            tables_text.append(" | ".join(["---"] * len(header_cells)))

                    # 提取数据行（从第二行开始）
                    for row in table.rows[1:]:
                        seen_cells = set()
                        row_cells = []

                        for cell in row.cells:
                            # 使用单元格对象 ID 去重（合并单元格会重复）
                            cell_id = id(cell)
                            if cell_id not in seen_cells:
                                row_cells.append(cell.text.strip())
                                seen_cells.add(cell_id)

                        # 只添加非空行
                        if any(row_cells):
                            tables_text.append(" | ".join(row_cells))

                    # 表格后添加空行分隔
                    tables_text.append("")

                # 3. 合并所有内容（段落 + 表格）
                all_parts = paragraphs + tables_text

                # 合并为最终内容
                content = "\n\n".join(all_parts)

                if not content or not content.strip():
                    raise ValueError("转换后的文档内容为空")

                return content

            except subprocess.TimeoutExpired:
                raise ValueError("LibreOffice 转换超时（超过120秒）")
            except Exception as e:
                if isinstance(e, ValueError):
                    raise
                raise ValueError(f"LibreOffice 处理出错: {str(e)}")

    @staticmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process legacy DOC file using LibreOffice

        使用 LibreOffice 处理 .doc 文件，支持：
        - Visio 嵌入图、OLE 对象
        - 横向页面和复杂布局
        - 所有 Word 97-2003 及更新格式

        Args:
            file_path: Path to DOC file
            metadata: Metadata to attach to documents
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks

        Returns:
            List of Document objects with chunked content

        Raises:
            ValueError: If conversion fails
        """
        try:
            content = LegacyWordProcessor._try_libreoffice_convert(file_path)
            metadata["conversion_method"] = "libreoffice"
        except ValueError as e:
            raise ValueError(
                f"处理 .doc 文件失败: {str(e)}\n\n"
                f"建议：请将 .doc 文件手动转换为 .docx 格式后重新上传"
            )

        document = Document(page_content=content, metadata=metadata)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "],
        )
        return splitter.split_documents([document])
