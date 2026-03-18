"""Test cases for FastAPI endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient


def mock_graph_result(success: bool = True):
    return {
        "success": success,
        "article": {
            "slug": "test-post",
            "title": "Test Post",
            "description": "A valid meta description for testing.",
            "tags": ["test", "product"],
            "body": "# Test Post\n\nBody content.\n\n## Sources\n\n- [Source](https://example.com/source-1)",
        },
        "final_blog": "# Test Post\n\nBody content.\n\n## Sources\n\n- [Source](https://example.com/source-1)",
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


class TestErrorHandling:
    def test_404_endpoint(self, client: TestClient):
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, client: TestClient):
        response = client.put("/api/v1/health")
        assert response.status_code == 405
