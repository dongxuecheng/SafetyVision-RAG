"""
API routes for safety analysis
"""

from fastapi import APIRouter, UploadFile, File, Depends, Form
from typing import Annotated, Optional

from app.schemas.safety import SafetyReport
from app.services.analysis_service import AnalysisService
from app.core.deps import get_analysis_service

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/image", response_model=SafetyReport)
async def analyze_image(
    file: Annotated[UploadFile, File(description="Image file to analyze")],
    user_hazards: Annotated[
        Optional[str], Form(description="User-provided hazard description")
    ] = None,
    service: AnalysisService = Depends(get_analysis_service),
):
    """
    Analyze an image for safety hazards using VLM and RAG

    - **file**: Image file (JPEG, PNG, etc.)
    - **user_hazards**: Optional user-provided hazard description (single text)
      (e.g., "高空作业时，工人未佩戴安全帽")
      If empty or not provided, only VLM-detected hazards will be used.

    Returns a safety report with detected violations and recommendations.
    User-provided hazard will be combined with VLM-detected hazards.
    """
    # Parse user_hazards: treat entire string as one hazard
    user_hazards_list = None
    if user_hazards and user_hazards.strip():
        user_hazards_list = [user_hazards.strip()]

    return await service.analyze_image(file, user_hazards=user_hazards_list)
