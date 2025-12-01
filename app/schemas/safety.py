"""
Pydantic schemas for API request/response models
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class HazardList(BaseModel):
    """List of detected hazards from VLM analysis"""

    hazards: List[str] = Field(
        description="List of detected safety hazards, each described in 10-20 words"
    )


class SafetyViolation(BaseModel):
    """Safety violation model"""

    hazard_id: int = Field(ge=1, description="Hazard ID")
    hazard_description: str = Field(description="Hazard description")
    recommendations: str = Field(description="Safety recommendations")
    rule_reference: str = Field(
        description="Reference to safety rules and source documents"
    )


class SafetyReport(BaseModel):
    """Safety analysis report"""

    report_id: str = Field(description="Report ID")
    violations: List[SafetyViolation] = Field(description="List of safety violations")


class DocumentDetail(BaseModel):
    """Document upload detail"""

    filename: str
    status: str
    chunks: Optional[int] = None
    message: str


class DocumentUploadResponse(BaseModel):
    """Document upload response"""

    success: bool
    message: str
    details: List[DocumentDetail]


class DocumentInfo(BaseModel):
    """Document information"""

    filename: str
    chunks_count: int


class DocumentDeleteResult(BaseModel):
    """Document deletion result"""

    filename: str
    status: str
    chunks_removed: Optional[int] = None
