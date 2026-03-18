"""Quality and SEO evaluation node implementation."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from src.schemas.state import GraphState
from src.tools.openai_blog_client import get_openai_blog_client
from src.utils.logger import get_logger
from src.utils.seo import calculate_keyword_density, normalize_seo_scores

logger = get_logger(__name__)


async def evaluate_seo(state: GraphState) -> Dict[str, Any]:
    """Evaluate the generated draft for source quality and SEO."""
    article = state.article or {}
    draft_blog = str(article.get("body", "")).strip() or state.draft_blog
    keyword = state.keyword

    if not draft_blog.strip():
        logger.warning("No draft blog content to evaluate")
        return {
            "seo_scores": normalize_seo_scores(None, fallback_final_score=0.0),
            "final_score": 0.0,
            "quality_feedback": state.error_message or "No draft was generated.",
            "keyword_density": 0.0,
        }

    logger.info("Starting quality assessment", keyword=keyword, attempts=state.attempts)

    rule_based_scores = _evaluate_with_rules(article=article, body=draft_blog, keyword=keyword)
    ai_scores: Dict[str, Any] = {}
    feedback = ""

    try:
        client = await get_openai_blog_client()
        ai_scores = await client.evaluate_blog(
            keyword=keyword,
            article=article,
            source_details=state.source_details,
        )
        feedback = str(ai_scores.get("feedback", "")).strip()
    except Exception as exc:
        logger.warning("AI evaluation failed, falling back to rules", error=str(exc))
        feedback = "Improve specificity, tighten headings, and preserve source-backed claims."

    source_quality_score = _score_sources(state.source_details)
    freshness_score = _score_freshness(state.source_details)

    final_scores = _combine_scores(
        rule_based_scores=rule_based_scores,
        ai_scores=ai_scores,
        source_quality_score=source_quality_score,
        freshness_score=freshness_score,
    )
    keyword_density = calculate_keyword_density(draft_blog, keyword)

    if not feedback:
        feedback = _build_feedback(
            final_scores=final_scores,
            source_quality_score=source_quality_score,
            freshness_score=freshness_score,
        )

    logger.info(
        "Quality assessment completed",
        keyword=keyword,
        final_score=final_scores["final_score"],
        source_quality_score=source_quality_score,
        freshness_score=freshness_score,
    )

    return {
        "seo_scores": final_scores,
        "final_score": final_scores["final_score"],
        "quality_feedback": feedback,
        "keyword_density": keyword_density,
    }


def _combine_scores(
    *,
    rule_based_scores: Dict[str, float],
    ai_scores: Dict[str, Any],
    source_quality_score: float,
    freshness_score: float,
) -> Dict[str, float]:
    base_ai = normalize_seo_scores(ai_scores, fallback_final_score=0.0)

    merged: Dict[str, float] = {}
    for field, rule_value in rule_based_scores.items():
        ai_value = base_ai.get(field, 0.0)
        if field == "final_score":
            continue
        merged[field] = round((rule_value * 0.55) + (ai_value * 0.45), 2)

    merged["source_quality_score"] = source_quality_score
    merged["freshness_score"] = freshness_score

    seo_score = sum(
        merged[field]
        for field in (
            "title_score",
            "meta_description_score",
            "keyword_optimization_score",
            "content_structure_score",
            "readability_score",
            "content_quality_score",
            "technical_seo_score",
        )
    ) / 7
    merged["final_score"] = round(
        (seo_score * 0.7) + (source_quality_score * 0.15) + (freshness_score * 0.15),
        2,
    )

    return merged


def _evaluate_with_rules(*, article: Dict[str, Any], body: str, keyword: str) -> Dict[str, float]:
    """Evaluate content using deterministic rules."""
    scores: Dict[str, float] = {}

    title = str(article.get("title", "")).strip()
    if title:
        title_score = 0
        if keyword.lower() in title.lower():
            title_score += 40
        if 30 <= len(title) <= 65:
            title_score += 35
        if title:
            title_score += 25
        scores["title_score"] = float(min(title_score, 100))
    else:
        scores["title_score"] = 0.0

    meta_desc = str(article.get("description", "")).strip()
    if meta_desc:
        meta_score = 0
        if keyword.lower() in meta_desc.lower():
            meta_score += 40
        if 120 <= len(meta_desc) <= 170:
            meta_score += 40
        if meta_desc:
            meta_score += 20
        scores["meta_description_score"] = float(min(meta_score, 100))
    else:
        scores["meta_description_score"] = 0.0

    keyword_density = calculate_keyword_density(body, keyword)
    if 0.8 <= keyword_density <= 2.5:
        scores["keyword_optimization_score"] = 92.0
    elif 0.4 <= keyword_density < 0.8 or 2.5 < keyword_density <= 3.2:
        scores["keyword_optimization_score"] = 75.0
    elif keyword_density > 0:
        scores["keyword_optimization_score"] = 55.0
    else:
        scores["keyword_optimization_score"] = 0.0

    h1_count = len(re.findall(r"(?m)^#\s+", body))
    h2_count = len(re.findall(r"(?m)^##\s+", body))
    h3_count = len(re.findall(r"(?m)^###\s+", body))
    p_count = len([part for part in re.split(r"\n\s*\n", body) if part.strip()])
    structure_score = 0
    if h1_count == 1:
        structure_score += 25
    if h2_count >= 3:
        structure_score += 35
    if h3_count >= 2:
        structure_score += 20
    if p_count >= 8:
        structure_score += 20
    scores["content_structure_score"] = float(min(structure_score, 100))

    plain_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", body)
    plain_text = re.sub(r"[#>*_`-]", " ", plain_text)
    word_count = len(plain_text.split())
    sentence_count = max(1, len(re.findall(r"[.!?]+", plain_text)))
    avg_sentence_length = word_count / sentence_count if sentence_count else word_count
    if 10 <= avg_sentence_length <= 22:
        scores["readability_score"] = 88.0
    elif 22 < avg_sentence_length <= 28:
        scores["readability_score"] = 72.0
    elif word_count >= 700:
        scores["readability_score"] = 65.0
    else:
        scores["readability_score"] = 50.0

    source_section = bool(re.search(r"(?im)^##\s+sources\b", body))
    if word_count >= 1200 and source_section:
        scores["content_quality_score"] = 90.0
    elif word_count >= 900:
        scores["content_quality_score"] = 78.0
    elif word_count >= 600:
        scores["content_quality_score"] = 65.0
    else:
        scores["content_quality_score"] = 45.0

    technical_score = 0
    if title:
        technical_score += 30
    if meta_desc:
        technical_score += 25
    if re.search(r"(?m)^#\s+", body):
        technical_score += 20
    if re.search(r"\[[^\]]+\]\([^)]+\)", body):
        technical_score += 15
    if source_section:
        technical_score += 10
    scores["technical_seo_score"] = float(min(technical_score, 100))

    scores["final_score"] = round(
        sum(
            scores[field]
            for field in (
                "title_score",
                "meta_description_score",
                "keyword_optimization_score",
                "content_structure_score",
                "readability_score",
                "content_quality_score",
                "technical_seo_score",
            )
        )
        / 7,
        2,
    )
    return scores


def _score_sources(source_details: List[Dict[str, Any]]) -> float:
    if not source_details:
        return 0.0
    count_score = min(len(source_details) * 18, 60)
    dated_sources = sum(1 for source in source_details if source.get("published_at"))
    date_score = min(dated_sources * 8, 24)
    titled_sources = sum(1 for source in source_details if source.get("title"))
    title_score = min(titled_sources * 4, 16)
    return round(min(100.0, count_score + date_score + title_score), 2)


def _score_freshness(source_details: List[Dict[str, Any]]) -> float:
    if not source_details:
        return 0.0

    recent_count = 0
    known_dates = 0
    current_year = 2026
    for source in source_details:
        published_at = str(source.get("published_at", "")).strip()
        if not published_at:
            continue
        known_dates += 1
        if published_at[:4].isdigit() and int(published_at[:4]) >= current_year - 2:
            recent_count += 1

    if known_dates == 0:
        return 55.0
    return round((recent_count / known_dates) * 100, 2)


def _build_feedback(
    *,
    final_scores: Dict[str, float],
    source_quality_score: float,
    freshness_score: float,
) -> str:
    suggestions: List[str] = []
    if final_scores["title_score"] < 70:
        suggestions.append("Rewrite the title to include the keyword more naturally.")
    if final_scores["meta_description_score"] < 70:
        suggestions.append("Add a stronger meta description between 120 and 160 characters.")
    if final_scores["content_structure_score"] < 70:
        suggestions.append("Improve heading hierarchy and add clearer section breaks.")
    if final_scores["technical_seo_score"] < 70:
        suggestions.append("Ensure the article includes title, meta description, and linked sources.")
    if source_quality_score < 70:
        suggestions.append("Use more high-quality sources and cite them explicitly.")
    if freshness_score < 70:
        suggestions.append("Prioritize more recent sources and mention exact dates.")

    return " ".join(suggestions) or "Tighten the article while preserving facts and source links."
