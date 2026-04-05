from typing import List, Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Text to analyze for PII")
    language: str = Field("uk", description="Language code (default: uk)")
    entities: Optional[List[str]] = Field(
        None,
        description="Specific entity types to detect; if None, detects all supported entities",
    )
    score_threshold: float = Field(
        0.5, ge=0.0, le=1.0, description="Minimum confidence score for a match"
    )


class EntityResult(BaseModel):
    entity_type: str
    start: int
    end: int
    score: float
    text: str


class AnalyzeResponse(BaseModel):
    results: List[EntityResult]
    total: int


class AnonymizeRequest(BaseModel):
    text: str = Field(..., description="Text to anonymize")
    language: str = Field("uk", description="Language code (default: uk)")
    score_threshold: float = Field(
        0.5, ge=0.0, le=1.0, description="Minimum confidence score for a match"
    )


class AnonymizeResponse(BaseModel):
    anonymized_text: str
    entities_found: int
