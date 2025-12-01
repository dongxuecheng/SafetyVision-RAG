"""Document processors for multi-format support"""

from .factory import DocumentProcessorFactory
from .pdf import PDFProcessor
from .word import WordProcessor, LegacyWordProcessor
from .excel import ExcelProcessor, LegacyExcelProcessor

__all__ = [
    "DocumentProcessorFactory",
    "PDFProcessor",
    "WordProcessor",
    "LegacyWordProcessor",
    "ExcelProcessor",
    "LegacyExcelProcessor",
]
