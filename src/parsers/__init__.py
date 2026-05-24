"""Parsers for XBRL, iXBRL, and PDF financial documents."""

from .ixbrl_parser import parse_ixbrl
from .pdf_section_parser import DocumentSection, build_chunks, split_sections
from .pdf_table_parser import extract_financial_tables
from .pdf_text_parser import PageText, extract_pages
from .xbrl_parser import parse_xbrl

__all__ = [
    "parse_xbrl",
    "parse_ixbrl",
    "extract_pages",
    "PageText",
    "split_sections",
    "build_chunks",
    "DocumentSection",
    "extract_financial_tables",
]
