"""Analytics: metrics computation, period comparisons, event detection, insight building."""

from .comparisons import compute_changes, get_prior_quarter, get_prior_year
from .event_detector import detect_events
from .insight_builder import build_all_insights
from .metrics import compute_all_metrics, compute_fcf, compute_margins, compute_ratios

__all__ = [
    "compute_margins",
    "compute_ratios",
    "compute_fcf",
    "compute_all_metrics",
    "compute_changes",
    "get_prior_quarter",
    "get_prior_year",
    "detect_events",
    "build_all_insights",
]
