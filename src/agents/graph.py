"""LangGraph workflow for web-search-grounded blog generation."""

from __future__ import annotations

from typing import Any, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END
from langgraph.graph import StateGraph

from src.agents.nodes import evaluate_seo, generate_blog, seo_optimize
from src.agents.nodes.react_agent import decide_next_action
from src.schemas.state import GraphState
from src.utils.logger import get_logger
from src.utils.seo import normalize_seo_scores

logger = get_logger(__name__)


class BlogGenerationGraph:
    """Blog generation workflow using LangGraph."""

    def __init__(self):
        self.workflow = None
        self.app = None

    async def create_workflow(self) -> StateGraph:
        """Create and configure the LangGraph workflow."""
        logger.info("Creating blog generation workflow")

        workflow = StateGraph(GraphState)
        workflow.add_node("generate", generate_blog)
        workflow.add_node("evaluate", evaluate_seo)
        workflow.add_node("seo_optimize", seo_optimize)

        workflow.set_entry_point("generate")
        workflow.set_finish_point("seo_optimize")

        workflow.add_edge("generate", "evaluate")
        workflow.add_conditional_edges(
            "evaluate",
            decide_next_action,
            {
                "generate": "generate",
                "seo_optimize": "seo_optimize",
                END: END,
            },
        )
        workflow.add_edge("seo_optimize", END)

        self.workflow = workflow
        logger.info("Blog generation workflow created successfully")
        return workflow

    async def compile_app(self):
        """Compile the workflow into a runnable application."""
        if not self.workflow:
            await self.create_workflow()

        self.app = self.workflow.compile(checkpointer=MemorySaver())
        logger.info("Blog generation app compiled successfully")
        return self.app

    async def run_blog_generation(
        self,
        *,
        keyword: str,
        customization: Dict[str, Any] | None = None,
        max_attempts: int = 3,
        seo_threshold: float = 75.0,
        thread_id: str = "default",
    ) -> Dict[str, Any]:
        """Run the complete blog generation workflow."""
        if not self.app:
            await self.compile_app()

        initial_state = GraphState(
            keyword=keyword,
            customization=customization or {},
            max_attempts=min(max_attempts, 5),
            seo_threshold=seo_threshold,
        )

        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 15,
            "max_concurrency": 4,
        }

        logger.info(
            "Starting blog generation workflow",
            keyword=keyword,
            max_attempts=initial_state.max_attempts,
            seo_threshold=seo_threshold,
            thread_id=thread_id,
            recursion_limit=config["recursion_limit"],
        )

        try:
            raw_final_state = await self.app.ainvoke(initial_state, config=config)
            final_graph_state = _coerce_graph_state(raw_final_state)

            article = final_graph_state.article or {}
            final_content = (
                str(article.get("body", "")).strip()
                or final_graph_state.final_blog
                or final_graph_state.draft_blog
            )
            scores = normalize_seo_scores(
                final_graph_state.seo_scores,
                fallback_final_score=final_graph_state.final_score,
            )
            final_score = scores["final_score"]
            success = bool(final_content.strip()) and final_score >= seo_threshold

            logger.info(
                "Blog generation workflow completed",
                keyword=keyword,
                success=success,
                final_score=final_score,
                attempts=final_graph_state.attempts,
                content_length=len(final_content),
                thread_id=thread_id,
            )

            return {
                "success": success,
                "article": article,
                "final_blog": final_content,
                "seo_scores": scores,
                "final_score": final_score,
                "attempts": final_graph_state.attempts,
                "keyword": keyword,
                "thread_id": thread_id,
                "sources_used": final_graph_state.sources_used,
                "source_details": final_graph_state.source_details,
                "model_used": final_graph_state.model_used,
                "quality_feedback": final_graph_state.quality_feedback,
                "keyword_density": final_graph_state.keyword_density,
                "error": final_graph_state.error_message,
            }
        except Exception as exc:
            logger.error(
                "Blog generation workflow failed",
                keyword=keyword,
                thread_id=thread_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return {
                "success": False,
                "article": {},
                "final_blog": "",
                "seo_scores": normalize_seo_scores(None, fallback_final_score=0.0),
                "final_score": 0.0,
                "attempts": 0,
                "keyword": keyword,
                "thread_id": thread_id,
                "sources_used": [],
                "source_details": [],
                "model_used": "",
                "quality_feedback": "",
                "keyword_density": 0.0,
                "error": str(exc),
            }


def _coerce_graph_state(raw_state: Any) -> GraphState:
    """Normalize LangGraph output into a GraphState."""
    if isinstance(raw_state, GraphState):
        return raw_state

    if isinstance(raw_state, dict) and "__end__" in raw_state:
        return _coerce_graph_state(raw_state["__end__"])

    if isinstance(raw_state, dict):
        return GraphState(**raw_state)

    raise TypeError(f"Unsupported graph state type: {type(raw_state)!r}")


_BLOG_GENERATION_GRAPH: BlogGenerationGraph | None = None


async def get_blog_generation_graph() -> BlogGenerationGraph:
    """Return a singleton graph instance."""
    global _BLOG_GENERATION_GRAPH
    if _BLOG_GENERATION_GRAPH is None:
        _BLOG_GENERATION_GRAPH = BlogGenerationGraph()
        await _BLOG_GENERATION_GRAPH.compile_app()
    return _BLOG_GENERATION_GRAPH
