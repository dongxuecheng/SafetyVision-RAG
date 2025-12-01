"""
API routes for document operations
"""
from typing import List
from fastapi import APIRouter, UploadFile, File, Query

from app.schemas.safety import DocumentUploadResponse, DocumentInfo
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    files: List[UploadFile] = File(...),
    skip_existing: bool = Query(True, description="Skip already uploaded files")
):
    """Upload and process multiple documents"""
    service = DocumentService()
    details = await service.upload_documents(files, skip_existing)
    
    success_count = sum(1 for d in details if d.status == "success")
    return DocumentUploadResponse(
        success=success_count == len(files),
        message=f"Processed {len(files)} files, {success_count} succeeded",
        details=details,
    )


@router.get("", response_model=List[DocumentInfo])
async def list_documents():
    """List all uploaded documents"""
    service = DocumentService()
    return service.list_documents()


@router.delete("")
async def delete_documents(filenames: List[str] = Query(..., description="Filenames to delete")):
    """Delete documents by filename"""
    service = DocumentService()
    results = service.delete_documents(filenames)
    return {"success": True, "results": results}
