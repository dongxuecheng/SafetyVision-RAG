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
        self,
        files: List[UploadFile],
        skip_existing: bool = True,
        purpose: str = "safety",
    ) -> List[DocumentDetail]:
        """Upload and process multiple documents based on purpose

        Args:
            files: List of files to upload
            skip_existing: Skip files that already exist
            purpose: 'qa' (RAG知识问答) or 'safety' (隐患识别)
                - qa: All files → qa collection
                - safety: Excel → hazard_db, others → regulations
        """
        if len(files) > self.settings.max_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Too many files. Maximum {self.settings.max_files} files allowed",
            )

        details = []
        for file in files:
            detail = await self._process_single_file(file, skip_existing, purpose)
            details.append(detail)

        return details

    async def _process_single_file(
        self, file: UploadFile, skip_existing: bool, purpose: str = "safety"
    ) -> DocumentDetail:
        """Process a single file based on purpose

        Args:
            file: File to process
            skip_existing: Skip if file already exists
            purpose: 'qa' or 'safety'
        """
        # Get file extension
        file_ext = Path(file.filename).suffix.lower()

        # Check if file type is supported
        supported_exts = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".md", ".markdown"]
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

        # Determine target collection based on purpose and file type
        if purpose == "qa":
            # QA system: all files go to qa collection
            if file_ext in [".xlsx", ".xls"]:
                return DocumentDetail(
                    filename=file.filename,
                    status="failed",
                    message="QA系统不支持 Excel 文件，请使用 PDF/Word/Markdown 格式",
                )
            target_collection = self.settings.qdrant_collection_qa
        elif purpose == "safety":
            # Safety inspection: Excel → hazard_db, others → regulations
            if file_ext in [".xlsx", ".xls"]:
                target_collection = self.settings.qdrant_collection_hazard_db
            else:
                target_collection = self.settings.qdrant_collection_regulations
        else:
            return DocumentDetail(
                filename=file.filename,
                status="failed",
                message=f"Invalid purpose: {purpose}. Must be 'qa' or 'safety'",
            )

        # Check if exists in the target collection (only if skip_existing is True)
        if skip_existing:
            try:
                result = self.client.scroll(
                    collection_name=target_collection,
                    scroll_filter={
                        "must": [
                            {
                                "key": "metadata.filename",
                                "match": {"value": file.filename},
                            }
                        ]
                    },
                    limit=1,
                    with_vectors=False,
                )

                # result is a tuple: (points, offset)
                points = result[0]
                if len(points) > 0:
                    return DocumentDetail(
                        filename=file.filename,
                        status="skipped",
                        message="Already exists",
                    )
            except Exception as e:
                # Collection might not exist yet, that's OK - will be created during upload
                # Or other errors during scroll - just continue with upload
                pass

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

            # Use the target_collection determined earlier
            collection_name = target_collection

            # Store in vector database (routed to appropriate collection)
            QdrantVectorStore.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                url=self.settings.qdrant_url,
                collection_name=collection_name,
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

    def list_documents(self, purpose: str = "safety") -> List[DocumentInfo]:
        """List documents by purpose

        Args:
            purpose: 'qa' (RAG知识问答) or 'safety' (隐患识别)
        """
        all_docs = {}

        # Determine which collections to query based on purpose
        if purpose == "qa":
            collections = [self.settings.qdrant_collection_qa]
        elif purpose == "safety":
            collections = [
                self.settings.qdrant_collection_regulations,
                self.settings.qdrant_collection_hazard_db,
            ]
        else:
            return []

        for collection_name in collections:
            # Check if collection exists
            try:
                self.client.get_collection(collection_name)
            except:
                continue

            offset = None
            while True:
                points, offset = self.client.scroll(
                    collection_name=collection_name,
                    limit=1000,  # 使用更大的 limit 提高效率
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not points:
                    break

                for point in points:
                    filename = point.payload.get("metadata", {}).get(
                        "filename", "unknown"
                    )
                    all_docs.setdefault(filename, 0)
                    all_docs[filename] += 1

                # 继续获取直到 offset 为 None（表示没有更多数据）
                if offset is None:
                    break

        return [
            DocumentInfo(filename=name, chunks_count=count)
            for name, count in all_docs.items()
        ]

    def delete_documents(
        self, filenames: List[str], purpose: str = "safety"
    ) -> List[dict]:
        """Delete documents by filename based on purpose

        Args:
            filenames: List of filenames to delete
            purpose: 'qa' (RAG知识问答) or 'safety' (隐患识别)
        """
        results = []

        # Determine which collections to delete from based on purpose
        if purpose == "qa":
            collections = [self.settings.qdrant_collection_qa]
        elif purpose == "safety":
            collections = [
                self.settings.qdrant_collection_regulations,
                self.settings.qdrant_collection_hazard_db,
            ]
        else:
            return [{"filename": f, "status": "invalid_purpose"} for f in filenames]

        for filename in filenames:
            total_removed = 0
            found = False

            # Try deleting from both collections
            for collection_name in collections:
                result = self.client.scroll(
                    collection_name=collection_name,
                    scroll_filter={
                        "must": [
                            {"key": "metadata.filename", "match": {"value": filename}}
                        ]
                    },
                    limit=self.settings.qdrant_scroll_limit_large,
                    with_vectors=False,
                )

                if len(result[0]) > 0:
                    found = True
                    total_removed += len(result[0])

                    self.client.delete(
                        collection_name=collection_name,
                        points_selector=Filter(
                            must=[
                                FieldCondition(
                                    key="metadata.filename",
                                    match=MatchValue(value=filename),
                                )
                            ]
                        ),
                    )

            if not found:
                results.append({"filename": filename, "status": "not_found"})
            else:
                results.append(
                    {
                        "filename": filename,
                        "status": "deleted",
                        "chunks_removed": total_removed,
                    }
                )

        return results
