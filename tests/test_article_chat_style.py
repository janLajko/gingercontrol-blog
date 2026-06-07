"""Tests for CMS article chat style and CTA behavior."""

import asyncio
from unittest.mock import AsyncMock, patch

from src.api.routes.blog import _execute_article_chat_request
from src.schemas.models import ArticleChatReplyRequest
from src.tools.openai_blog_client import _build_article_chat_prompt


def test_article_chat_prompt_uses_database_blog_style_for_creation():
    prompt = _build_article_chat_prompt(
        article={},
        messages=[],
        message="Write an article about ECCN 3B991 license processing to China.",
        customization={},
        metadata={},
        source_details=[],
        has_existing_article=False,
    )

    assert "DATABASE BLOG STYLE TO MATCH" in prompt
    assert "Start the body directly with two H2 question sections" in prompt
    assert "End complete articles with a References section using the corpus format" in prompt
    assert "Export Control for ECCN, BIS, EAR, SNAP-R" in prompt


def test_article_chat_reply_appends_product_cta():
    mock_client = AsyncMock()
    mock_client.chat_article.return_value = {
        "assistant_message": "Article created.",
        "article": {
            "slug": "eccn-license-guide",
            "title": "ECCN Export License Guide",
            "description": "BIS license workflow for exporters.",
            "tags": ["ECCN", "export control"],
            "body": "## How long does an ECCN license take?\n\nExport license timing depends on BIS review.",
        },
        "source_details": [],
        "sources_used": [],
        "model_used": "gpt-5-mini",
    }
    request = ArticleChatReplyRequest(
        message="Write an article about ECCN export license processing.",
        metadata={"keyword": "ECCN export license"},
    )

    with patch(
        "src.api.routes.blog.get_openai_blog_client",
        AsyncMock(return_value=mock_client),
    ):
        response = asyncio.run(_execute_article_chat_request(request))

    assert "https://gingercontrol.com/products/export-control" in response.article.body
    assert response.metadata["product_cta"]["product_id"] == "export_control"
    assert response.metadata["product_cta"]["appended"] is True
