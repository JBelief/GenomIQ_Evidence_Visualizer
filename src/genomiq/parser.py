from __future__ import annotations

import re

from genomiq.input_extractor import extract_variant_markers
from genomiq.schema import ParsedCase


SENSITIVE_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\bMRN[:\s]*[A-Z0-9-]+\b", re.IGNORECASE),
    re.compile(r"\bDOB[:\s]*\d{1,2}/\d{1,2}/\d{2,4}\b", re.IGNORECASE),
]


def parse_research_case(text: str) -> ParsedCase:
    upper_text = text.upper()
    variants = extract_variant_markers(text)
    contains_sensitive = any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)

    confidence = 0.35 + min(len(variants), 3) * 0.18
    if "DE-IDENTIFIED" in upper_text or "SYNTHETIC" in upper_text:
        confidence += 0.08
    if contains_sensitive:
        confidence -= 0.25

    if "OVARIAN" in upper_text:
        area = "Ovarian cancer research"
    elif "COLORECTAL" in upper_text or "COLON" in upper_text or "CRC" in upper_text:
        area = "Colorectal cancer research"
    elif "GASTRIC" in upper_text or "STOMACH" in upper_text:
        area = "Gastric cancer research"
    else:
        area = "Precision oncology research"

    return ParsedCase(
        variants=variants or ["unresolved_marker"],
        confidence_score=max(0.0, min(confidence, 1.0)),
        primary_research_area=area,
        contains_sensitive_identifiers=contains_sensitive,
    )
