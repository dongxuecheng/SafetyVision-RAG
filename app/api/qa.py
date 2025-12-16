"""
QA API endpoints
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.qa import QARequest, QAResponse
from app.services.qa_service import QAService

router = APIRouter(prefix="/api/qa", tags=["QA"])

# Initialize QA service (singleton)
qa_service = QAService()


@router.post("/ask", response_model=QAResponse)
async def ask_question(request: QARequest):
    """
    Ask a question and get answer from knowledge base
    
    - **question**: User question (1-500 characters)
    
    Returns:
    - **answer**: Generated answer based on retrieved documents
    - **sources**: List of source documents with metadata
    - **has_relevant_sources**: Whether relevant sources were found
    """
    try:
        response = await qa_service.answer_question(request.question)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check for QA service"""
    return {"status": "ok", "service": "QA"}
