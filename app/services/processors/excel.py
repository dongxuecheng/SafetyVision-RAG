"""Excel document processors"""

from datetime import datetime
from typing import List, Dict, Any

from langchain_core.documents import Document
import openpyxl
import xlrd

from .base import DocumentProcessor


class ExcelProcessor(DocumentProcessor):
    """
    Excel (.xlsx) 处理：Row-to-Text策略
    将每行数据结合表头转换为语义文本，保留结构信息
    """

    @staticmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process XLSX file using Row-to-Text strategy
        
        Converts each row into semantic text combined with headers.
        This preserves the structured nature of Excel data while
        enabling semantic search.
        
        Args:
            file_path: Path to XLSX file
            metadata: Metadata to attach to documents
            chunk_size: Not used for Excel (each row is a document)
            chunk_overlap: Not used for Excel
            
        Returns:
            List of Document objects, one per row
        """
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
                        # 处理日期时间类型
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


class LegacyExcelProcessor(DocumentProcessor):
    """旧版Excel (.xls) 处理：Row-to-Text策略"""

    @staticmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process legacy XLS file using Row-to-Text strategy
        
        Args:
            file_path: Path to XLS file
            metadata: Metadata to attach to documents
            chunk_size: Not used for Excel (each row is a document)
            chunk_overlap: Not used for Excel
            
        Returns:
            List of Document objects, one per row
        """
        workbook = xlrd.open_workbook(file_path)
        documents = []

        for sheet in workbook.sheets():
            sheet_name = sheet.name

            if sheet.nrows == 0:
                continue

            # 第一行作为表头
            headers = [
                (
                    str(sheet.cell_value(0, col)).strip()
                    if sheet.cell_value(0, col)
                    else ""
                )
                for col in range(sheet.ncols)
            ]

            # 处理数据行
            for row_idx in range(1, sheet.nrows):
                row_data = []
                for col_idx, header in enumerate(headers):
                    if header and col_idx < sheet.ncols:
                        cell_value = sheet.cell_value(row_idx, col_idx)
                        if cell_value:
                            # 处理日期类型
                            if sheet.cell_type(row_idx, col_idx) == xlrd.XL_CELL_DATE:
                                date_tuple = xlrd.xldate_as_tuple(
                                    cell_value, workbook.datemode
                                )
                                value_str = f"{date_tuple[0]}-{date_tuple[1]:02d}-{date_tuple[2]:02d}"
                            else:
                                value_str = str(cell_value).strip()

                            if value_str:
                                row_data.append(f"{header}为{value_str}")

                if row_data:
                    # 生成语义文本
                    text = f"第{row_idx + 1}行数据：{'，'.join(row_data)}。"
                    doc_metadata = {
                        **metadata,
                        "sheet_name": sheet_name,
                        "row_number": row_idx + 1,
                        "content_type": "excel_row",
                    }
                    documents.append(Document(page_content=text, metadata=doc_metadata))

        return documents
