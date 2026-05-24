"""
Inline XBRL (iXBRL) parser.
Extracts tagged financial values from HTML documents containing ix: elements.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.domain.identity import FilingIdentity
from src.domain.taxonomy import KNOWN_XBRL_TAGS

logger = logging.getLogger(__name__)

try:
    from lxml import etree
    from lxml import html as lxml_html

    HAS_LXML = True
except ImportError:
    HAS_LXML = False
    logger.warning("lxml not available — iXBRL parsing disabled")

# iXBRL namespace
_IX_NS = "http://www.xbrl.org/2013/inlineXBRL"
_IX_NS_ALT = "http://www.xbrl.org/2008/inlineXBRL"


def parse_ixbrl(html_path: Path, identity: FilingIdentity) -> list[dict]:
    """
    Parse inline XBRL document.
    Returns list of raw fact dicts matching the same schema as xbrl_parser.parse_xbrl().

    Finds all ix:nonFraction and ix:nonNumeric elements and extracts:
      xbrl_tag, value, context_ref, period_start, period_end, period_type
    """
    if not HAS_LXML:
        logger.error("lxml is required for iXBRL parsing")
        return []

    try:
        content = html_path.read_bytes()
        parser = lxml_html.HTMLParser(encoding="utf-8")
        tree = etree.fromstring(content, parser)  # type: ignore[attr-defined]
    except Exception as exc:
        logger.error("Failed to parse iXBRL file %s: %s", html_path, exc)
        return []

    facts: list[dict] = []

    # Search for ix:nonFraction and ix:nonNumeric elements
    # Use xpath with namespace-agnostic local-name matching
    try:
        elements = tree.xpath("//*[local-name()='nonFraction' or local-name()='nonNumeric']")
    except Exception as exc:
        logger.error("XPath query failed: %s", exc)
        return []

    for element in elements:
        name_attr = element.get("name", "")
        context_ref = element.get("contextRef", "")
        scale = element.get("scale", "0")
        sign = element.get("sign", "")
        format_attr = element.get("format", "")

        # Extract local name from prefixed name (e.g. "ifrs-full:Revenue" -> "Revenue")
        local_name = name_attr.split(":")[-1] if ":" in name_attr else name_attr
        if local_name not in KNOWN_XBRL_TAGS:
            continue

        raw_text = _get_text(element)
        if not raw_text:
            continue

        # Clean and parse numeric value
        numeric_str = re.sub(r"[,\s]", "", raw_text)
        numeric_str = re.sub(r"[^\d.\-]", "", numeric_str)
        if not numeric_str:
            continue
        try:
            value = float(numeric_str)
        except ValueError:
            continue

        # Apply scale factor (e.g. scale="3" means multiply by 10^3)
        try:
            scale_factor = 10 ** int(scale)
            value *= scale_factor
        except (ValueError, OverflowError):
            pass

        # Apply sign flip if sign="-"
        if sign == "-":
            value = -value

        facts.append(
            {
                "xbrl_tag": local_name,
                "value": value,
                "unit_ref": element.get("unitRef", ""),
                "context_ref": context_ref,
                "decimals": element.get("decimals", ""),
                "period_start": None,  # resolved later via context lookup if needed
                "period_end": None,
                "period_type": "duration",
                "source_format": format_attr,
            }
        )

    logger.info("Parsed %d raw iXBRL facts from %s", len(facts), html_path.name)
    return facts


def _get_text(element) -> str:
    """Extract all text content from an element, ignoring child tags."""
    texts = []
    if element.text:
        texts.append(element.text)
    for child in element:
        if child.tail:
            texts.append(child.tail)
    return "".join(texts).strip()
