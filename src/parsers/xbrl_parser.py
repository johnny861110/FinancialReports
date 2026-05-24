"""
XBRL instance document parser using lxml.
Handles Taiwan IFRS XBRL with ifrs-full: and twse: namespaces.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.domain.identity import FilingIdentity
from src.domain.taxonomy import KNOWN_XBRL_TAGS

logger = logging.getLogger(__name__)

try:
    from lxml import etree

    HAS_LXML = True
except ImportError:
    HAS_LXML = False
    logger.warning("lxml not available — XBRL parsing disabled")


def parse_xbrl(xml_path: Path, identity: FilingIdentity) -> list[dict]:
    """
    Parse an XBRL instance document.

    Returns a list of raw fact dicts:
      {xbrl_tag, value, unit_ref, context_ref, period_start, period_end, period_type}

    Handles any namespace; matches element local names against KNOWN_XBRL_TAGS.
    """
    if not HAS_LXML:
        logger.error("lxml is required for XBRL parsing")
        return []

    try:
        tree = etree.parse(str(xml_path))  # type: ignore[attr-defined]
        root = tree.getroot()
    except Exception as exc:
        logger.error("Failed to parse XBRL file %s: %s", xml_path, exc)
        return []

    # Build context map: context_ref -> {period_start, period_end, period_type}
    contexts = _parse_contexts(root)

    facts: list[dict] = []
    for element in root.iter():
        local_name = etree.QName(element.tag).localname  # type: ignore[attr-defined]
        if local_name not in KNOWN_XBRL_TAGS:
            continue
        if element.text is None or not element.text.strip():
            continue

        raw_value = element.text.strip()
        # Skip non-numeric (tags like decimals/precision attributes on non-fact elements)
        try:
            numeric_value = float(raw_value.replace(",", ""))
        except ValueError:
            continue

        unit_ref = element.get("unitRef", "")
        context_ref = element.get("contextRef", "")
        decimals = element.get("decimals", "")

        period_info = contexts.get(context_ref, {})

        facts.append(
            {
                "xbrl_tag": local_name,
                "value": numeric_value,
                "unit_ref": unit_ref,
                "context_ref": context_ref,
                "decimals": decimals,
                "period_start": period_info.get("period_start"),
                "period_end": period_info.get("period_end"),
                "period_type": period_info.get("period_type", "duration"),
            }
        )

    logger.info("Parsed %d raw XBRL facts from %s", len(facts), xml_path.name)
    return facts


def _parse_contexts(root: Any) -> dict[str, dict]:
    """
    Extract all xbrli:context elements and return a dict
    mapping context_ref -> {period_start, period_end, period_type}.
    """
    contexts: dict[str, dict] = {}
    # xbrli namespace variants
    for element in root.iter():
        local = etree.QName(element.tag).localname  # type: ignore[attr-defined]
        if local != "context":
            continue
        ctx_id = element.get("id", "")
        period_info = _parse_period(element)
        contexts[ctx_id] = period_info
    return contexts


def _parse_period(context_element: Any) -> dict:
    """Extract period dates from a context element."""
    for child in context_element.iter():
        local = etree.QName(child.tag).localname  # type: ignore[attr-defined]
        if local == "instant":
            inst = child.text.strip() if child.text else None
            return {
                "period_start": inst,
                "period_end": inst,
                "period_type": "instant",
            }
        if local == "startDate":
            start = child.text.strip() if child.text else None
        if local == "endDate":
            end = child.text.strip() if child.text else None

    # Try to extract from iteration result
    start = None
    end = None
    for child in context_element.iter():
        local = etree.QName(child.tag).localname  # type: ignore[attr-defined]
        if local == "startDate" and child.text:
            start = child.text.strip()
        elif local == "endDate" and child.text:
            end = child.text.strip()

    if start or end:
        return {
            "period_start": start,
            "period_end": end,
            "period_type": "duration",
        }
    return {"period_start": None, "period_end": None, "period_type": "duration"}
