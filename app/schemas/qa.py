"""
QA system schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class QARequest(BaseModel):
    """QA request schema"""

    question: str = Field(
        ..., description="User question", min_length=1, max_length=500
    )


class SourceDocument(BaseModel):
    """Retrieved source document with metadata"""

    content: str = Field(description="Document content")
    filename: str = Field(description="Source filename")
    location: str = Field(description="Location in document")
    score: float = Field(description="Similarity score", ge=0.0, le=1.0)


class QAResponse(BaseModel):
    """QA response schema"""

    answer: str = Field(description="Generated answer")
    sources: List[SourceDocument] = Field(
        default_factory=list, description="Source documents used for answer"
    )
    has_relevant_sources: bool = Field(
        description="Whether relevant sources were found"
    )
