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
    purpose: str = Query(
        "safety",
        description="Document purpose: 'qa' (RAG知识问答) or 'safety' (隐患识别)",
        regex="^(qa|safety)$",
    ),
    skip_existing: bool = Query(True, description="Skip already uploaded files"),
    service: DocumentService = Depends(get_document_service),
):
    """Upload documents for specified purpose (QA system or safety inspection)

    - **qa**: All files go to qa collection (no Excel files expected)
    - **safety**: Excel → hazard_db, others → regulations
    """
    details = await service.upload_documents(files, skip_existing, purpose)

    success_count = sum(1 for d in details if d.status == "success")
    return DocumentUploadResponse(
        success=success_count == len(files),
        message=f"Processed {len(files)} files, {success_count} succeeded",
        details=details,
    )


@router.get("", response_model=List[DocumentInfo])
async def list_documents(
    purpose: str = Query(
        "safety",
        description="Document purpose: 'qa' (RAG知识问答) or 'safety' (隐患识别)",
        regex="^(qa|safety)$",
    ),
    service: DocumentService = Depends(get_document_service),
):
    """List documents by purpose

    - **qa**: Lists documents from qa collection
    - **safety**: Lists documents from regulations + hazard_db collections
    """
    return service.list_documents(purpose)


@router.delete("")
async def delete_documents(
    filenames: List[str] = Query(..., description="Filenames to delete"),
    purpose: str = Query(
        "safety",
        description="Document purpose: 'qa' (RAG知识问答) or 'safety' (隐患识别)",
        regex="^(qa|safety)$",
    ),
    service: DocumentService = Depends(get_document_service),
):
    """Delete documents by purpose

    - **qa**: Deletes from qa collection
    - **safety**: Deletes from regulations + hazard_db collections
    """
    results = service.delete_documents(filenames, purpose)
    return {"success": True, "results": results}
