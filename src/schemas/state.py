"""LangGraph state schema definition."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class GraphState(BaseModel):
    """State schema for the LangGraph workflow."""

    # Use ConfigDict instead of Config class (Pydantic v2)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    keyword: str = Field(..., description="Target keyword for blog generation")
    customization: Dict[str, Any] = Field(
        default_factory=dict,
        description="User customization passed through generation nodes",
    )
    source_details: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured source metadata used during generation",
    )
    sources_used: List[str] = Field(
        default_factory=list,
        description="Source URLs used to ground the generated article",
    )
    article: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured generated article payload",
    )
    draft_blog: str = Field(default="", description="Generated blog content draft")
    seo_scores: Dict[str, float] = Field(
        default_factory=dict, description="SEO evaluation scores breakdown"
    )
    final_score: float = Field(default=0.0, description="Final aggregated SEO score")
    attempts: int = Field(default=0, description="Number of generation attempts made")
    max_attempts: int = Field(
        default=3, description="Maximum allowed generation attempts"
    )
    seo_threshold: float = Field(
        default=75.0, description="Minimum SEO score threshold for acceptance"
    )
    final_blog: str = Field(default="", description="Final optimized blog content")
    quality_feedback: str = Field(
        default="",
        description="Concrete revision guidance from the quality assessment step",
    )
    keyword_density: float = Field(
        default=0.0,
        description="Keyword density percentage computed during evaluation",
    )
    model_used: str = Field(
        default="",
        description="Last model used to produce or optimize the content",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Execution error captured during generation or optimization",
    )
