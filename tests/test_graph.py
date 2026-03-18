"""Test cases for the refactored blog workflow."""

from unittest.mock import AsyncMock, patch

import pytest
from langgraph.constants import END

from src.agents.nodes.evaluate_seo import evaluate_seo
from src.agents.nodes.generate_blog import generate_blog
from src.agents.nodes.react_agent import decide_next_action, react_agent
from src.agents.nodes.seo_optimize import seo_optimize
from src.schemas.state import GraphState


class TestGraphState:
    def test_graph_state_creation(self, sample_keyword):
        state = GraphState(keyword=sample_keyword)

        assert state.keyword == sample_keyword
        assert state.customization == {}
        assert state.source_details == []
        assert state.sources_used == []
        assert state.draft_blog == ""
        assert state.final_blog == ""
        assert state.seo_scores == {}
        assert state.quality_feedback == ""

    def test_graph_state_with_custom_values(self):
        state = GraphState(
            keyword="test keyword",
            customization={"tone": "technical"},
            max_attempts=5,
            attempts=2,
            final_score=85.5,
            seo_threshold=80.0,
        )

        assert state.customization["tone"] == "technical"
        assert state.max_attempts == 5
        assert state.attempts == 2
        assert state.final_score == 85.5
        assert state.seo_threshold == 80.0


class TestGenerateNode:
    @pytest.mark.asyncio
    async def test_generate_blog_success(self, sample_graph_state, sample_source_details):
        mock_client = AsyncMock()
        mock_client.generate_blog.return_value = {
            "article": {
                "slug": "draft",
                "title": "Draft",
                "description": "Draft description",
                "tags": ["draft"],
                "body": "# Draft\n\nBody",
            },
            "draft_blog": "# Draft\n\nBody",
            "sources_used": [item["url"] for item in sample_source_details],
            "source_details": sample_source_details,
            "model_used": "gpt-5-mini",
        }

        with patch(
            "src.agents.nodes.generate_blog.get_openai_blog_client",
            AsyncMock(return_value=mock_client),
        ):
            result = await generate_blog(sample_graph_state)

        assert result["attempts"] == 1
        assert result["article"]["slug"] == "draft"
        assert result["draft_blog"].startswith("# Draft")
        assert len(result["sources_used"]) == 2
        assert result["model_used"] == "gpt-5-mini"

    @pytest.mark.asyncio
    async def test_generate_blog_failure(self, sample_graph_state):
        mock_client = AsyncMock()
        mock_client.generate_blog.side_effect = RuntimeError("boom")

        with patch(
            "src.agents.nodes.generate_blog.get_openai_blog_client",
            AsyncMock(return_value=mock_client),
        ):
            result = await generate_blog(sample_graph_state)

        assert result["attempts"] == 1
        assert result["draft_blog"] == ""
        assert result["error_message"] == "boom"


class TestEvaluateNode:
    @pytest.mark.asyncio
    async def test_evaluate_seo_with_content(
        self,
        sample_graph_state,
        sample_blog_content,
        sample_source_details,
    ):
        sample_graph_state.draft_blog = sample_blog_content
        sample_graph_state.article = {
            "slug": "complete-fastapi-tutorial",
            "title": "Complete FastAPI Tutorial",
            "description": "Learn FastAPI with a practical tutorial covering setup and deployment.",
            "tags": ["fastapi", "python"],
            "body": sample_blog_content,
        }
        sample_graph_state.source_details = sample_source_details
        sample_graph_state.sources_used = [item["url"] for item in sample_source_details]

        mock_client = AsyncMock()
        mock_client.evaluate_blog.return_value = {
            "title_score": 84,
            "meta_description_score": 81,
            "keyword_optimization_score": 79,
            "content_structure_score": 88,
            "readability_score": 82,
            "content_quality_score": 86,
            "technical_seo_score": 83,
            "final_score": 84,
            "feedback": "Tighten the title and keep the sources section visible.",
        }

        with patch(
            "src.agents.nodes.evaluate_seo.get_openai_blog_client",
            AsyncMock(return_value=mock_client),
        ):
            result = await evaluate_seo(sample_graph_state)

        assert "seo_scores" in result
        assert result["final_score"] > 0
        assert result["quality_feedback"]
        assert result["seo_scores"]["title_score"] > 0
        assert result["keyword_density"] > 0

    @pytest.mark.asyncio
    async def test_evaluate_seo_empty_content(self, sample_graph_state):
        result = await evaluate_seo(sample_graph_state)

        assert result["final_score"] == 0.0
        assert result["seo_scores"]["final_score"] == 0.0
        assert result["quality_feedback"]


class TestReactAgentNode:
    @pytest.mark.asyncio
    async def test_react_agent_accept(self, sample_graph_state):
        sample_graph_state.final_score = 80.0
        sample_graph_state.seo_threshold = 75.0
        sample_graph_state.draft_blog = "Content"

        decision = await react_agent(sample_graph_state)
        assert decision == "ACCEPT"

    @pytest.mark.asyncio
    async def test_react_agent_revise(self, sample_graph_state):
        sample_graph_state.final_score = 60.0
        sample_graph_state.attempts = 1
        sample_graph_state.max_attempts = 3
        sample_graph_state.seo_threshold = 75.0
        sample_graph_state.draft_blog = "Content"

        decision = await react_agent(sample_graph_state)
        assert decision == "REVISE"

    def test_decide_next_action_accept(self, sample_graph_state):
        sample_graph_state.final_score = 80.0
        sample_graph_state.draft_blog = "Test blog content"
        sample_graph_state.seo_threshold = 75.0

        action = decide_next_action(sample_graph_state)
        assert action == "seo_optimize"

    def test_decide_next_action_retry(self, sample_graph_state):
        sample_graph_state.final_score = 60.0
        sample_graph_state.attempts = 1
        sample_graph_state.max_attempts = 3
        sample_graph_state.seo_threshold = 75.0
        sample_graph_state.draft_blog = "Test blog content"

        action = decide_next_action(sample_graph_state)
        assert action == "generate"

    def test_decide_next_action_end_when_no_content(self, sample_graph_state):
        sample_graph_state.final_score = 0.0
        sample_graph_state.attempts = 3
        sample_graph_state.max_attempts = 3
        sample_graph_state.draft_blog = ""

        action = decide_next_action(sample_graph_state)
        assert action == END


class TestSeoOptimizeNode:
    @pytest.mark.asyncio
    async def test_seo_optimize_success(
        self,
        sample_graph_state,
        sample_blog_content,
        sample_source_details,
    ):
        sample_graph_state.draft_blog = sample_blog_content
        sample_graph_state.article = {
            "slug": "optimized",
            "title": "Optimized",
            "description": "Improved description",
            "tags": ["fastapi"],
            "body": sample_blog_content,
        }
        sample_graph_state.source_details = sample_source_details
        sample_graph_state.quality_feedback = "Improve title and meta description."

        mock_client = AsyncMock()
        mock_client.optimize_blog.return_value = {
            "article": {
                "slug": "optimized",
                "title": "Optimized",
                "description": "Improved description",
                "tags": ["fastapi"],
                "body": "# Optimized\n\nBody",
            },
            "final_blog": "# Optimized\n\nBody",
            "model_used": "gpt-5-mini",
        }

        with patch(
            "src.agents.nodes.seo_optimize.get_openai_blog_client",
            AsyncMock(return_value=mock_client),
        ):
            result = await seo_optimize(sample_graph_state)

        assert result["article"]["slug"] == "optimized"
        assert result["final_blog"].startswith("# Optimized")

    @pytest.mark.asyncio
    async def test_seo_optimize_no_content(self, sample_graph_state):
        result = await seo_optimize(sample_graph_state)
        assert result["final_blog"] == ""
        assert "error_message" in result
