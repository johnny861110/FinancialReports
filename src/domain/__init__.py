"""Domain models and taxonomy for the Financial Insight Engine."""

from .identity import FilingIdentity
from .models import Chunk, DetectedEvent, Evidence, Fact, Filing, InsightCard
from .taxonomy import (
    ALL_CANONICAL,
    CANONICAL_BALANCE,
    CANONICAL_CASHFLOW,
    CANONICAL_INCOME,
    FIELD_TO_STATEMENT,
    KNOWN_XBRL_TAGS,
    XBRL_TO_CANONICAL,
)

__all__ = [
    "FilingIdentity",
    "Filing",
    "Fact",
    "Evidence",
    "Chunk",
    "InsightCard",
    "DetectedEvent",
    "ALL_CANONICAL",
    "CANONICAL_INCOME",
    "CANONICAL_BALANCE",
    "CANONICAL_CASHFLOW",
    "XBRL_TO_CANONICAL",
    "KNOWN_XBRL_TAGS",
    "FIELD_TO_STATEMENT",
]
