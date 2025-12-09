"""
Pydantic schemas for API request/response models
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

# Hazard classification types - must match config.py definitions
HazardCategory = Literal[
    "高处坠落",
    "物体打击",
    "机械伤害",
    "起重伤害",
    "触电",
    "坍塌",
    "火灾",
    "中毒窒息",
    "其他伤害",
]

HazardLevel = Literal[
    "A级-重大隐患",
    "B级-较大隐患",
    "C级-一般隐患",
    "D级-轻微隐患",
]


class HazardList(BaseModel):
    """List of detected hazards from VLM analysis"""

    hazards: List[str] = Field(
        description="List of detected safety hazards, each described in 10-20 words"
    )


class SourceReference(BaseModel):
    """Source document reference with location"""

    filename: str = Field(description="Source document filename")
    location: str = Field(
        description="Location within document (e.g., 'Sheet1, Row 5' or 'Page 3')"
    )


class SafetyViolationLLM(BaseModel):
    """Safety violation model for LLM structured output (without source_documents)"""

    hazard_id: int = Field(ge=1, description="Hazard ID")
    hazard_description: str = Field(description="Hazard description")
    hazard_category: HazardCategory = Field(description="Hazard category")
    hazard_level: HazardLevel = Field(description="Hazard level")
    recommendations: str = Field(description="Safety recommendations")
    rule_reference: str = Field(
        description="Reference to safety rules and source documents"
    )


class SafetyViolation(BaseModel):
    """Complete safety violation model with source tracking"""

    hazard_id: int = Field(ge=1, description="Hazard ID")
    hazard_description: str = Field(description="Hazard description")
    hazard_category: HazardCategory = Field(description="Hazard category")
    hazard_level: HazardLevel = Field(description="Hazard level")
    recommendations: str = Field(description="Safety recommendations")
    rule_reference: str = Field(
        description="Reference to safety rules and source documents"
    )
    source_documents: List[SourceReference] = Field(
        default_factory=list,
        description="List of source documents with precise locations",
    )


class SafetyReport(BaseModel):
    """Safety analysis report"""

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
