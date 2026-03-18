"""Routing logic for quality-assessment retries."""

from typing import Dict, Any, Literal
from langgraph.constants import END  # canonical END literal

from src.schemas.state import GraphState
from src.utils.logger import get_logger

logger = get_logger(__name__)

DecisionType = Literal["ACCEPT", "REVISE", "FAIL"]


# ------------------------------------------------------------------
# 1. Core decision node (used if you *call* the agent as a node)
# ------------------------------------------------------------------
async def react_agent(state: GraphState) -> DecisionType:
    """
    Decide whether to ACCEPT, REVISE, or fail the current blog attempt.
    This function is **not** used by the conditional edge logic below;
    it is kept for backward compatibility / unit tests.
    """
    final_score = state.final_score
    attempts = state.attempts
    max_attempts = state.max_attempts
    seo_threshold = state.seo_threshold

    logger.info(
        "React agent making decision",
        final_score=final_score,
        attempts=attempts,
        max_attempts=max_attempts,
        threshold=seo_threshold,
        has_content=bool(state.draft_blog.strip()),
        sources=len(state.sources_used),
    )

    # 1) Hard failure rules
    if attempts >= max_attempts:
        logger.warning("FAIL: Maximum attempts reached")
        return "FAIL"

    if not state.draft_blog.strip():
        logger.warning("FAIL: No content and no source material")
        return "FAIL"

    # 2) Accept rules
    if final_score >= seo_threshold and state.draft_blog.strip():
        logger.info("ACCEPT: Score meets threshold")
        return "ACCEPT"

    if state.draft_blog.strip() and len(state.draft_blog) > 500 and attempts >= 2:
        logger.info("ACCEPT: Reasonable content after ≥2 attempts")
        return "ACCEPT"

    # 3) Otherwise retry
    logger.info("REVISE: Retrying generation")
    return "REVISE"


# ------------------------------------------------------------------
# 2. Conditional-edge router used in graph.py
#    Must return strings understood by LangGraph 0.5.x
# ------------------------------------------------------------------
def decide_next_action(state: GraphState):
    """
    Router used by the conditional edge coming out of the 'evaluate' node.
    Returns:
        "generate"  – loop back to generate node
        "seo_optimize" – finalize with SEO polish
        END         – finish the workflow (LangGraph constant)
    """
    final_score = state.final_score
    attempts = state.attempts
    max_attempts = state.max_attempts
    seo_threshold = state.seo_threshold

    logger.info(
        "Deciding next action",
        final_score=final_score,
        attempts=attempts,
        max_attempts=max_attempts,
        threshold=seo_threshold,
        has_content=bool(state.draft_blog.strip()),
        sources=len(state.sources_used),
    )

    # --- Termination conditions -------------------------------------------------
    if attempts >= max_attempts:
        if state.draft_blog.strip():
            logger.info("Proceeding to SEO optimization after max attempts")
            return "seo_optimize"
        logger.info("Terminating: max attempts reached without content")
        return END

    if not state.draft_blog.strip():
        logger.info("Terminating: no generated content")
        return END

    if final_score >= seo_threshold and state.draft_blog.strip():
        logger.info("Proceeding to SEO optimization: target score achieved")
        return "seo_optimize"

    if state.draft_blog.strip() and len(state.draft_blog) > 500 and attempts >= 2:
        logger.info("Proceeding to SEO optimization: acceptable draft")
        return "seo_optimize"

    # --- Continue ---------------------------------------------------------------
    logger.info("Continuing: retrying generation")
    return "generate"
