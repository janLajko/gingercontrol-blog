"""Research and generation node implementation."""

from typing import Any, Dict

from src.schemas.state import GraphState
from src.tools.openai_blog_client import get_openai_blog_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def generate_blog(state: GraphState) -> Dict[str, Any]:
    """Research and generate a grounded blog draft using web search."""
    attempt = state.attempts + 1

    logger.info(
        "Starting web-grounded blog generation",
        keyword=state.keyword,
        attempt=attempt,
        max_attempts=state.max_attempts,
    )

    try:
        client = await get_openai_blog_client()
        result = await client.generate_blog(
            keyword=state.keyword,
            customization=state.customization,
            feedback=state.quality_feedback,
            attempt=attempt,
        )
        result["attempts"] = attempt
        result["error_message"] = None
        return result
    except Exception as exc:
        logger.error(
            "Web-grounded blog generation failed",
            keyword=state.keyword,
            attempt=attempt,
            error=str(exc),
        )
        return {
            "article": {},
            "draft_blog": "",
            "sources_used": [],
            "source_details": [],
            "attempts": attempt,
            "error_message": str(exc),
        }
