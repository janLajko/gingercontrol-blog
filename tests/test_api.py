"""Test cases for FastAPI endpoints."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient


def mock_graph_result(success: bool = True):
    return {
        "success": success,
        "article": {
            "slug": "test-post",
            "title": "ECCN Export License Guide",
            "description": "A valid meta description for BIS export license testing.",
            "tags": ["ECCN", "export control"],
            "body": "# ECCN Export License Guide\n\nBody content.\n\n## Sources\n\n- [Source](https://example.com/source-1)",
        },
        "final_blog": "# ECCN Export License Guide\n\nBody content.\n\n## Sources\n\n- [Source](https://example.com/source-1)",
        "seo_scores": {
            "title_score": 80,
            "meta_description_score": 80,
            "keyword_optimization_score": 75,
            "content_structure_score": 78,
            "readability_score": 82,
            "content_quality_score": 79,
            "technical_seo_score": 77,
            "final_score": 78.71,
        },
        "final_score": 78.71,
        "attempts": 1,
        "sources_used": ["https://example.com/source-1"],
        "source_details": [],
        "model_used": "gpt-5-mini",
        "quality_feedback": "",
        "error": None,
    }


class TestHealthEndpoint:
    def test_health_check_sync(self, client: TestClient):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_check_async(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200


class TestBlogGenerationEndpoint:
    def test_blog_generation_invalid_keyword(self, client: TestClient):
        response = client.post("/api/v1/generate-blog", json={"keyword": ""})
        assert response.status_code == 422

    def test_blog_generation_valid_request_structure(self, client: TestClient):
        mock_graph = AsyncMock()
        mock_graph.run_blog_generation.return_value = mock_graph_result()

        with patch(
            "src.api.routes.blog.get_blog_generation_graph",
            AsyncMock(return_value=mock_graph),
        ):
            response = client.post(
                "/api/v1/generate-blog",
                json={
                    "keyword": "fastapi tutorial",
                    "max_attempts": 2,
                    "seo_threshold": 70.0,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["article"]["slug"] == "test-post"
        assert (
            "https://gingercontrol.com/products/export-control"
            in data["article"]["body"]
        )
        assert (
            "https://gingercontrol.com/products/export-control"
            in data["final_blog"]
        )
        assert data["seo_scores"]["final_score"] > 0
        assert data["metadata"]["model_used"] == "gpt-5-mini"

    def test_blog_generation_failed_run_returns_response(self, client: TestClient):
        mock_graph = AsyncMock()
        mock_graph.run_blog_generation.return_value = mock_graph_result(success=False)

        with patch(
            "src.api.routes.blog.get_blog_generation_graph",
            AsyncMock(return_value=mock_graph),
        ):
            response = client.post(
                "/api/v1/generate-blog",
                json={
                    "keyword": "fastapi tutorial",
                    "max_attempts": 1,
                    "seo_threshold": 95.0,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "failed"

    def test_blog_generation_invalid_max_attempts(self, client: TestClient):
        response = client.post(
            "/api/v1/generate-blog",
            json={"keyword": "fastapi tutorial", "max_attempts": 0},
        )
        assert response.status_code == 422

    def test_blog_generation_invalid_seo_threshold(self, client: TestClient):
        response = client.post(
            "/api/v1/generate-blog",
            json={"keyword": "fastapi tutorial", "seo_threshold": 150.0},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_blog_generation_async(self, async_client: AsyncClient):
        mock_graph = AsyncMock()
        mock_graph.run_blog_generation.return_value = mock_graph_result()

        with patch(
            "src.api.routes.blog.get_blog_generation_graph",
            AsyncMock(return_value=mock_graph),
        ):
            response = await async_client.post(
                "/api/v1/generate-blog",
                json={
                    "keyword": "python tutorial",
                    "max_attempts": 1,
                    "seo_threshold": 60.0,
                },
            )

        assert response.status_code == 200


def make_article_record(article_id: int = 1, status: str = "draft"):
    return SimpleNamespace(
        id=article_id,
        run_id="manual-test",
        keyword="test article",
        slug="test-article",
        title="Test Article",
        description="Test article description.",
        tags=[],
        body="Test article body.",
        author_name=None,
        author_avatar=None,
        category=None,
        language="en",
        cover_image=None,
        user_id=None,
        status=status,
        success=True,
        sources_used=[],
        source_details=[],
        seo_scores={},
        final_score=0.0,
        model_used=None,
        customization={},
        type="article",
        error_message=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def make_article_payload(status: str = "draft"):
    return {
        "slug": "test-article",
        "title": "Test Article",
        "description": "Test article description.",
        "tags": [],
        "body": "Test article body.",
        "status": status,
    }


class TestArticleRevalidateWebhook:
    def test_create_published_article_schedules_revalidate(self, client: TestClient):
        article = make_article_record(status="published")

        with (
            patch("src.api.routes.blog.create_blog_post", return_value=article),
            patch("src.api.routes.blog._schedule_article_revalidate") as schedule,
        ):
            response = client.post(
                "/api/v1/articles",
                json=make_article_payload(status="published"),
            )

        assert response.status_code == 201
        schedule.assert_called_once()
        assert schedule.call_args.kwargs["operation"] == "create"
        assert schedule.call_args.kwargs["article"] is article

    def test_create_draft_article_skips_revalidate(self, client: TestClient):
        article = make_article_record(status="draft")

        with (
            patch("src.api.routes.blog.create_blog_post", return_value=article),
            patch("src.api.routes.blog._schedule_article_revalidate") as schedule,
        ):
            response = client.post(
                "/api/v1/articles",
                json=make_article_payload(status="draft"),
            )

        assert response.status_code == 201
        schedule.assert_not_called()

    def test_update_published_article_schedules_revalidate(self, client: TestClient):
        previous_article = make_article_record(status="published")
        updated_article = make_article_record(status="draft")

        with (
            patch("src.api.routes.blog.get_blog_post", return_value=previous_article),
            patch("src.api.routes.blog.update_blog_post", return_value=updated_article),
            patch("src.api.routes.blog._schedule_article_revalidate") as schedule,
        ):
            response = client.put(
                "/api/v1/articles/1",
                json=make_article_payload(status="draft"),
            )

        assert response.status_code == 200
        schedule.assert_called_once()
        assert schedule.call_args.kwargs["operation"] == "update"
        assert schedule.call_args.kwargs["article"] is updated_article

    def test_delete_published_article_schedules_revalidate(self, client: TestClient):
        article = make_article_record(status="published")

        with (
            patch("src.api.routes.blog.get_blog_post", return_value=article),
            patch("src.api.routes.blog.delete_blog_post", return_value=True),
            patch("src.api.routes.blog._schedule_article_revalidate") as schedule,
        ):
            response = client.delete("/api/v1/articles/1")

        assert response.status_code == 200
        schedule.assert_called_once()
        assert schedule.call_args.kwargs["operation"] == "delete"
        assert schedule.call_args.kwargs["article"] is article


class TestErrorHandling:
    def test_404_endpoint(self, client: TestClient):
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, client: TestClient):
        response = client.put("/api/v1/health")
        assert response.status_code == 405
