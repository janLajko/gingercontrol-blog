"""Utilities for SEO scoring and content metrics."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


REQUIRED_SEO_FIELDS = (
    "title_score",
    "meta_description_score",
    "keyword_optimization_score",
    "content_structure_score",
    "readability_score",
    "content_quality_score",
    "technical_seo_score",
    "final_score",
)


def clamp_score(value: Any) -> float:
    """Clamp any value into a valid 0-100 score."""
    try:
        return round(max(0.0, min(100.0, float(value))), 2)
    except (TypeError, ValueError):
        return 0.0


def default_seo_scores(final_score: float = 0.0) -> Dict[str, float]:
    """Build a complete SEO score payload with safe defaults."""
    scores = {field: 0.0 for field in REQUIRED_SEO_FIELDS}
    scores["final_score"] = clamp_score(final_score)
    return scores


def normalize_seo_scores(
    scores: Optional[Dict[str, Any]],
    *,
    fallback_final_score: Optional[float] = None,
) -> Dict[str, float]:
    """Normalize a partial score payload into the full response shape."""
    normalized = default_seo_scores()

    for field in REQUIRED_SEO_FIELDS:
        if scores and field in scores:
            normalized[field] = clamp_score(scores[field])

    if fallback_final_score is not None:
        normalized["final_score"] = clamp_score(
            normalized["final_score"] or fallback_final_score
        )

    return normalized


def calculate_keyword_density(content: str, keyword: str) -> float:
    """Calculate keyword density for plain text or HTML content."""
    if not content or not keyword:
        return 0.0

    content_text = re.sub(r"<[^>]+>", " ", content)
    words = content_text.split()
    if not words:
        return 0.0

    occurrences = len(
        re.findall(r"\b" + re.escape(keyword.lower()) + r"\b", content_text.lower())
    )
    return round((occurrences / len(words)) * 100, 2)
