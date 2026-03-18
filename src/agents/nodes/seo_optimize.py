"""SEO optimization node implementation."""

from typing import Any, Dict

from src.schemas.state import GraphState
from src.tools.openai_blog_client import get_openai_blog_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def seo_optimize(state: GraphState) -> Dict[str, Any]:
    """Optimize a validated draft for SEO while preserving facts and sources."""
    article = state.article or {}
    body = str(article.get("body", "")).strip() or state.draft_blog or state.final_blog
    if not body.strip():
        logger.warning("No article content available for SEO optimization")
        return {
            "article": {},
            "final_blog": "",
            "error_message": "No article content to optimize",
        }

    if not article:
        article = {
            "slug": "",
            "title": "",
            "description": "",
            "tags": [],
            "body": body,
        }

    try:
        client = await get_openai_blog_client()
        result = await client.optimize_blog(
            keyword=state.keyword,
            article=article,
            feedback=state.quality_feedback,
            customization=state.customization,
            source_details=state.source_details,
        )
        return result
    except Exception as exc:
        logger.error("SEO optimization failed", keyword=state.keyword, error=str(exc))
        return {
            "article": article,
            "final_blog": body,
            "error_message": str(exc),
        }
