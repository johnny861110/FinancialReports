"""
Factory functions for data source clients.
"""

from __future__ import annotations

from src.sources.mops_client import MOPSClient
from src.sources.pdf_client import MOPSPDFClient
from src.sources.xbrl_client import XBRLClient

_pdf_client: MOPSPDFClient | None = None
_xbrl_client: XBRLClient | None = None
_mops_client: MOPSClient | None = None


def get_pdf_client() -> MOPSPDFClient:
    """Return a shared MOPSPDFClient instance."""
    global _pdf_client
    if _pdf_client is None:
        _pdf_client = MOPSPDFClient()
    return _pdf_client


def get_xbrl_client() -> XBRLClient:
    """Return a shared XBRLClient instance."""
    global _xbrl_client
    if _xbrl_client is None:
        _xbrl_client = XBRLClient()
    return _xbrl_client


def get_mops_client() -> MOPSClient:
    """Return a shared MOPSClient instance."""
    global _mops_client
    if _mops_client is None:
        _mops_client = MOPSClient()
    return _mops_client
