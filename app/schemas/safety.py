"""
Pydantic schemas for API request/response models
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


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
    hazard_category: str = Field(
        description="Hazard category (validated against config.py)"
    )
    hazard_level: str = Field(description="Hazard level (validated against config.py)")
    recommendations: str = Field(description="Safety recommendations")
    rule_reference: str = Field(
        description="Reference to safety rules and source documents"
    )

    @field_validator("hazard_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        from app.core.config import get_settings

        settings = get_settings()
        if v not in settings.hazard_categories:
            raise ValueError(
                f"hazard_category must be one of {settings.hazard_categories}, got '{v}'"
            )
        return v

    @field_validator("hazard_level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        from app.core.config import get_settings

        settings = get_settings()
        if v not in settings.hazard_levels:
            raise ValueError(
                f"hazard_level must be one of {settings.hazard_levels}, got '{v}'"
            )
        return v


class SafetyViolation(BaseModel):
    """Complete safety violation model with source tracking"""

    hazard_id: int = Field(ge=1, description="Hazard ID")
    hazard_description: str = Field(description="Hazard description")
    hazard_category: str = Field(
        description="Hazard category (validated against config.py)"
    )
    hazard_level: str = Field(description="Hazard level (validated against config.py)")
    recommendations: str = Field(description="Safety recommendations")
    rule_reference: str = Field(
        description="Reference to safety rules and source documents"
    )
    source_documents: List[SourceReference] = Field(
        default_factory=list,
        description="List of source documents with precise locations",
    )

    @field_validator("hazard_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        from app.core.config import get_settings

        settings = get_settings()
        if v not in settings.hazard_categories:
            raise ValueError(
                f"hazard_category must be one of {settings.hazard_categories}, got '{v}'"
            )
        return v

    @field_validator("hazard_level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        from app.core.config import get_settings

        settings = get_settings()
        if v not in settings.hazard_levels:
            raise ValueError(
                f"hazard_level must be one of {settings.hazard_levels}, got '{v}'"
            )
        return v


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
