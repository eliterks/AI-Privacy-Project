from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REDACT = "REDACT"
    BLOCK = "BLOCK"


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class PIIFinding(BaseModel):
    entity_type: str
    start: int
    end: int
    confidence: float
    validated: bool


class InjectionResult(BaseModel):
    label: str
    score: float
    threshold: float
    model_version: str


class ComponentVersions(BaseModel):
    gateway: str
    injection_model: str
    pii_engine: str
    policy: str
    evaluation_set: str
    model_revision: str


class AnalysisResponse(BaseModel):
    decision: Decision
    injection: InjectionResult
    pii: list[PIIFinding]
    sanitized_text: str
    reasons: list[str]
    versions: ComponentVersions


class GenerateResponse(AnalysisResponse):
    response: str | None = None
    response_pii: list[PIIFinding] = Field(default_factory=list)
    response_sanitized: bool = False

