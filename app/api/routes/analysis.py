"""
API routes for safety analysis
"""
from fastapi import APIRouter, UploadFile, File
from typing import Annotated

from app.schemas.safety import SafetyReport
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/image", response_model=SafetyReport)
async def analyze_image(file: Annotated[UploadFile, File(description="Image file to analyze")]):
    """
    Analyze an image for safety hazards using VLM and RAG
    
    - **file**: Image file (JPEG, PNG, etc.)
    
    Returns a safety report with detected violations and recommendations
    """
    service = AnalysisService()
    return await service.analyze_image(file)
