"""
Pydantic v2 domain models for the Financial Insight Engine.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Filing(BaseModel):
    """Represents a single quarterly filing."""

    filing_key: str  # e.g. "2330_2025Q1"
    stock_code: str
    year: int
    quarter: str  # "Q1"|"Q2"|"Q3"|"Q4"
    company_name_zh: str | None = None
    company_name_en: str | None = None
    industry: str | None = None
    status: str = "pending"  # pending → ingested → extracted → validated → insight_ready
    quality_score: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("quarter")
    @classmethod
    def validate_quarter(cls, v: str) -> str:
        if v not in ("Q1", "Q2", "Q3", "Q4"):
            raise ValueError(f"Invalid quarter: {v}. Must be Q1|Q2|Q3|Q4")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = {"pending", "ingested", "extracted", "validated", "insight_ready", "failed"}
        if v not in valid:
            raise ValueError(f"Invalid status: {v}")
        return v


class Fact(BaseModel):
    """A single extracted financial data point."""

    filing_key: str
    field: str  # canonical field name e.g. "net_revenue"
    value: float
    unit: str = "TWD_thousands"
    period_start: date | None = None
    period_end: date | None = None
    period_type: str = "duration"  # "duration" | "instant"
    source_type: str = "xbrl"  # "xbrl" | "ixbrl" | "pdf_table" | "pdf_text" | "computed"
    confidence: float = 1.0
    xbrl_tag: str | None = None

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        valid = {"xbrl", "ixbrl", "pdf_table", "pdf_text", "computed", "finmind"}
        if v not in valid:
            raise ValueError(f"Invalid source_type: {v}")
        return v


class Evidence(BaseModel):
    """Evidence record linking a Fact to its source location."""

    fact_id: int
    page_number: int | None = None
    section_title: str | None = None
    raw_text: str | None = None
    extraction_method: str = "xbrl"


class Chunk(BaseModel):
    """A text chunk from a document, for RAG retrieval."""

    doc_id: int
    page_number: int
    section_type: str | None = None
    section_title: str | None = None
    chunk_index: int = 0
    content: str
    char_count: int = 0
    contains_numbers: bool = False
    contains_table: bool = False
    importance_score: float = 0.5

    def __init__(self, **data: Any) -> None:
        if "char_count" not in data or data["char_count"] == 0:
            data["char_count"] = len(data.get("content", ""))
        super().__init__(**data)


class InsightCard(BaseModel):
    """A structured insight derived from financial data."""

    filing_key: str
    card_type: str  # e.g. "performance_summary", "revenue_growth"
    title: str
    summary: str
    data_points: dict[str, Any] = Field(default_factory=dict)
    sentiment: str | None = None  # "positive" | "negative" | "neutral"
    confidence: float = 0.8


class DetectedEvent(BaseModel):
    """A notable financial event detected by rule-based analysis."""

    filing_key: str
    event_type: str  # e.g. "revenue_decline", "fcf_negative"
    severity: str = "info"  # "error" | "warning" | "info"
    title: str = ""
    description: str
    related_fields: list[str] = Field(default_factory=list)
    confidence: float = 0.9

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid = {"error", "warning", "info"}
        if v not in valid:
            raise ValueError(f"Invalid severity: {v}")
        return v
