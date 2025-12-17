"""
QA API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas.qa import QARequest, QAResponse
from app.services.qa_service import QAService

router = APIRouter(prefix="/api/qa", tags=["QA"])


def get_qa_service() -> QAService:
    """
    Dependency injection for QA service
    Lazy initialization to avoid collection not found error
    """
    return QAService()


@router.post("/ask", response_model=QAResponse)
async def ask_question(
    request: QARequest, qa_service: QAService = Depends(get_qa_service)
):
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
            detail=f"Failed to answer question: {str(e)}",
        )
