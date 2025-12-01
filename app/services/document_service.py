"""
Document processing service
"""

import tempfile
from pathlib import Path
from datetime import datetime
from typing import List

from fastapi import UploadFile, HTTPException, status
from langchain_qdrant import QdrantVectorStore
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import get_settings
from app.core.deps import get_qdrant_client, get_embeddings, get_vector_store
from app.schemas.safety import DocumentDetail, DocumentInfo
from app.services.processors import DocumentProcessorFactory


class DocumentService:
    """Service for document operations"""

    def __init__(self):
        self.settings = get_settings()
        self.client = get_qdrant_client()
        self.embeddings = get_embeddings()

    async def upload_documents(
        self, files: List[UploadFile], skip_existing: bool = True
    ) -> List[DocumentDetail]:
        """Upload and process multiple documents"""
        if len(files) > self.settings.max_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many files. Maximum {self.settings.max_files} files allowed",
            )

        details = []
        for file in files:
            detail = await self._process_single_file(file, skip_existing)
            details.append(detail)

        return details

    async def _process_single_file(
        self, file: UploadFile, skip_existing: bool
    ) -> DocumentDetail:
        """Process a single file"""
        # Get file extension
        file_ext = Path(file.filename).suffix.lower()

        # Check if file type is supported
        supported_exts = [".pdf", ".docx", ".doc", ".xlsx", ".xls"]
        if file_ext not in supported_exts:
            return DocumentDetail(
                filename=file.filename,
                status="failed",
                message=f"不支持的文件类型。支持: {', '.join(supported_exts)}",
            )

        # Read file content
        content = await file.read()
        if len(content) > self.settings.max_file_size:
            return DocumentDetail(
                filename=file.filename, status="failed", message="文件过大"
            )

        # Check if exists
        result = self.client.scroll(
            collection_name=self.settings.qdrant_collection,
            scroll_filter={
                "must": [
                    {"key": "metadata.filename", "match": {"value": file.filename}}
                ]
            },
            limit=1,
            with_vectors=False,
        )

        if len(result[0]) > 0 and skip_existing:
            return DocumentDetail(
                filename=file.filename, status="skipped", message="Already exists"
            )

        # Process document
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            metadata = {
                "filename": file.filename,
                "upload_time": datetime.now().isoformat(),
            }

            # Process the document
            chunks = DocumentProcessorFactory.process(
                tmp_path,
                metadata,
                self.settings.chunk_size,
                self.settings.chunk_overlap,
            )

            # Store in vector database
            QdrantVectorStore.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                url=self.settings.qdrant_url,
                collection_name=self.settings.qdrant_collection,
                force_recreate=False,
            )

            return DocumentDetail(
                filename=file.filename,
                status="success",
                chunks=len(chunks),
                message="Uploaded successfully",
            )
        except ValueError as e:
            return DocumentDetail(
                filename=file.filename,
                status="failed",
                message=str(e),
            )
        except Exception as e:
            return DocumentDetail(
                filename=file.filename,
                status="failed",
                message=f"Processing failed: {str(e)}",
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def list_documents(self) -> List[DocumentInfo]:
        """List all documents"""
        all_docs = {}
        offset = None

        while True:
            points, offset = self.client.scroll(
                collection_name=self.settings.qdrant_collection,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            if not points:
                break

            for point in points:
                filename = point.payload.get("metadata", {}).get("filename", "unknown")
                all_docs.setdefault(filename, 0)
                all_docs[filename] += 1

            if offset is None:
                break

        return [
            DocumentInfo(filename=name, chunks_count=count)
            for name, count in all_docs.items()
        ]

    def delete_documents(self, filenames: List[str]) -> List[dict]:
        """Delete documents by filename"""
        results = []
        for filename in filenames:
            result = self.client.scroll(
                collection_name=self.settings.qdrant_collection,
                scroll_filter={
                    "must": [{"key": "metadata.filename", "match": {"value": filename}}]
                },
                limit=10000,
                with_vectors=False,
            )

            if len(result[0]) == 0:
                results.append({"filename": filename, "status": "not_found"})
                continue

            self.client.delete(
                collection_name=self.settings.qdrant_collection,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="metadata.filename", match=MatchValue(value=filename)
                        )
                    ]
                ),
            )

            results.append(
                {
                    "filename": filename,
                    "status": "deleted",
                    "chunks_removed": len(result[0]),
                }
            )

        return results
