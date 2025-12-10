"""Markdown document processor with HTML cleaning"""

import re
from pathlib import Path
from typing import List, Dict, Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from bs4 import BeautifulSoup

from .base import DocumentProcessor


class MarkdownProcessor(DocumentProcessor):
    """Processor for Markdown files (.md, .markdown) with HTML cleaning"""

    @staticmethod
    def clean_html_tags(content: str) -> str:
        """
        Remove HTML tags and extract clean text from markdown content

        Args:
            content: Raw markdown content that may contain HTML

        Returns:
            Cleaned text with HTML removed and tables converted to readable format
        """
        # Use BeautifulSoup to parse HTML
        soup = BeautifulSoup(content, "html.parser")

        # Convert tables to readable text format
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells and any(cells):  # Skip empty rows
                    rows.append(" | ".join(cells))

            # Replace table with pipe-separated text
            if rows:
                table_text = "\n" + "\n".join(rows) + "\n"
                table.replace_with(table_text)

        # Convert common HTML elements to plain text
        for tag in soup.find_all(["div", "span", "p", "strong", "em", "b", "i"]):
            tag.unwrap()

        # Get clean text
        text = soup.get_text(separator="\n")

        # Remove excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)  # Max 2 consecutive newlines
        text = re.sub(r" {2,}", " ", text)  # Max 1 space
        text = re.sub(r"\t", " ", text)  # Replace tabs with spaces

        # Remove lines that are just whitespace
        lines = [line.rstrip() for line in text.split("\n")]
        text = "\n".join(line for line in lines if line or lines.index(line) == 0)

        return text.strip()

    @staticmethod
    def process(
        file_path: str,
        metadata: Dict[str, Any],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> List[Document]:
        """
        Process Markdown file and return chunks

        Args:
            file_path: Path to the Markdown file
            metadata: Metadata to attach to documents
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of Document objects with text chunks
        """
        # Read markdown content
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Clean HTML tags from markdown content
        clean_content = MarkdownProcessor.clean_html_tags(content)

        # Extract filename for metadata
        filename = Path(file_path).name

        # Create text splitter optimized for markdown
        # Use markdown-specific separators to preserve structure
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n## ",  # Split by H2 headers first
                "\n### ",  # Then H3 headers
                "\n#### ",  # Then H4 headers
                "\n\n",  # Then paragraphs
                "\n",  # Then lines
                " ",  # Then words
                "",  # Finally characters
            ],
            keep_separator=True,  # Keep headers with their content
        )

        # Split cleaned content into chunks
        chunks = text_splitter.split_text(clean_content)

        # Create Document objects with metadata
        documents = []
        for i, chunk in enumerate(chunks):
            # Extract section header from chunk for location info
            section = MarkdownProcessor._extract_section_header(chunk)

            doc_metadata = {
                **metadata,
                "chunk_id": i,
                "total_chunks": len(chunks),
                "source_type": "markdown",
                "section": section,  # Add section header as location
            }
            documents.append(Document(page_content=chunk, metadata=doc_metadata))

        return documents

    @staticmethod
    def _extract_section_header(chunk: str) -> str:
        """
        Extract the first markdown header from chunk as section identifier

        Args:
            chunk: Text chunk that may start with a header

        Returns:
            Section header text or "文档开头" if no header found
        """
        lines = chunk.strip().split("\n")
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            # Match markdown headers (# ## ### etc.)
            if line.startswith("#"):
                # Remove # symbols and strip whitespace
                header = re.sub(r"^#+\s*", "", line).strip()
                if header:
                    return header
        return "文档开头"
