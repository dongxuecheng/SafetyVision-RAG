"""
API routes for document operations
"""

from typing import List
from fastapi import APIRouter, UploadFile, File, Query, Depends

from app.schemas.safety import DocumentUploadResponse, DocumentInfo
from app.services.document_service import DocumentService
from app.core.deps import get_document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    collection: str = Query(
        "auto",
        description="Target collection: 'auto' (auto-detect by file type), 'regulations', 'hazard_db', or 'qa'",
        regex="^(auto|regulations|hazard_db|qa)$"
    ),
    skip_existing: bool = Query(True, description="Skip already uploaded files"),
    service: DocumentService = Depends(get_document_service),
):
    """Upload and process multiple documents to specified collection"""
    details = await service.upload_documents(files, skip_existing, collection)

    success_count = sum(1 for d in details if d.status == "success")
    return DocumentUploadResponse(
        success=success_count == len(files),
        message=f"Processed {len(files)} files, {success_count} succeeded",
        details=details,
    )


@router.get("", response_model=List[DocumentInfo])
async def list_documents(
    collection: str = Query(
        "all",
        description="Collection to list: 'all', 'regulations', 'hazard_db', or 'qa'",
        regex="^(all|regulations|hazard_db|qa)$"
    ),
    service: DocumentService = Depends(get_document_service),
):
    """List documents from specified collection(s)"""
    return service.list_documents(collection)


@router.delete("")
async def delete_documents(
    filenames: List[str] = Query(..., description="Filenames to delete"),
    collection: str = Query(
        "all",
        description="Collection to delete from: 'all', 'regulations', 'hazard_db', or 'qa'",
        regex="^(all|regulations|hazard_db|qa)$"
    ),
    service: DocumentService = Depends(get_document_service),
):
    """Delete documents by filename from specified collection(s)"""
    results = service.delete_documents(filenames, collection)
    return {"success": True, "results": results}
