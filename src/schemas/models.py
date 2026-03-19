"""Enhanced Pydantic models for better API customization."""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, validator, ConfigDict
from datetime import datetime
import re

class BlogCustomization(BaseModel):
    """Blog customization options for enhanced user control."""
    
    tone: Optional[Literal["professional", "casual", "technical", "friendly", "authoritative"]] = Field(
        default="professional",
        description="Writing tone for the blog content"
    )
    
    target_audience: Optional[Literal["beginners", "intermediate", "advanced", "general"]] = Field(
        default="general",
        description="Target audience level"
    )
    
    content_type: Optional[Literal["tutorial", "guide", "review", "comparison", "news", "opinion"]] = Field(
        default="guide",
        description="Type of content to generate"
    )
    
    word_count_target: Optional[int] = Field(
        default=1500,
        ge=800,
        le=5000,
        description="Target word count for the blog post"
    )
    
    include_faq: Optional[bool] = Field(
        default=True,
        description="Whether to include FAQ section"
    )
    
    include_conclusion: Optional[bool] = Field(
        default=True,
        description="Whether to include conclusion section"
    )
    
    include_table_of_contents: Optional[bool] = Field(
        default=True,
        description="Whether to include table of contents"
    )
    
    focus_keywords: Optional[List[str]] = Field(
        default=[],
        max_items=10,
        description="Additional focus keywords to include"
    )
    
    exclude_domains: Optional[List[str]] = Field(
        default=[],
        max_items=20,
        description="Domains to exclude from content scraping"
    )

class EnhancedBlogGenerationRequest(BaseModel):
    """Enhanced request schema with customization options."""

    model_config = ConfigDict(populate_by_name=True)

    keyword: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Target keyword for blog content generation",
    )
    
    max_attempts: Optional[int] = Field(
        default=3, 
        ge=1, 
        le=10, 
        description="Maximum number of generation attempts"
    )
    
    seo_threshold: Optional[float] = Field(
        default=75.0,
        ge=0.0,
        le=100.0,
        description="Minimum SEO score threshold for acceptance",
    )
    
    customization: Optional[BlogCustomization] = Field(
        default=BlogCustomization(),
        description="Blog customization options"
    )
    
    priority: Optional[Literal["low", "normal", "high"]] = Field(
        default="normal",
        description="Processing priority level"
    )
    
    callback_url: Optional[str] = Field(
        default=None,
        description="Webhook URL for async processing notifications"
    )
    
    user_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User identifier for tracking"
    )

    author_name: Optional[str] = Field(
        default=None,
        alias="authorName",
        max_length=120,
        description="Author display name"
    )

    author_avatar: Optional[str] = Field(
        default=None,
        alias="authorAvatar",
        max_length=500,
        description="Author avatar URL"
    )

    category: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Article category"
    )

    cover_image: Optional[str] = Field(
        default=None,
        alias="coverImage",
        max_length=500,
        description="Cover image URL"
    )
    
    @validator('keyword')
    def validate_keyword(cls, v):
        """Validate keyword format."""
        if not v.strip():
            raise ValueError("Keyword cannot be empty or whitespace only")
        
        # Remove excessive whitespace
        v = re.sub(r'\s+', ' ', v.strip())
        
        # Basic validation for reasonable keywords
        if len(v.split()) > 10:
            raise ValueError("Keyword should not exceed 10 words")
            
        return v
    
    @validator('callback_url')
    def validate_callback_url(cls, v):
        """Validate callback URL format."""
        if v is not None:
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE
            )
            if not url_pattern.match(v):
                raise ValueError("Invalid callback URL format")
        return v

class SEOScoreDetails(BaseModel):
    """Detailed SEO score breakdown."""
    
    title_score: float = Field(..., ge=0, le=100)
    meta_description_score: float = Field(..., ge=0, le=100)
    keyword_optimization_score: float = Field(..., ge=0, le=100)
    content_structure_score: float = Field(..., ge=0, le=100)
    readability_score: float = Field(..., ge=0, le=100)
    content_quality_score: float = Field(..., ge=0, le=100)
    technical_seo_score: float = Field(..., ge=0, le=100)
    final_score: float = Field(..., ge=0, le=100)
    
    # Additional metrics
    word_count: Optional[int] = Field(default=None, description="Total word count")
    reading_time_minutes: Optional[int] = Field(default=None, description="Estimated reading time")
    keyword_density: Optional[float] = Field(default=None, description="Target keyword density percentage")

class ContentMetadata(BaseModel):
    """Metadata about the generated content."""
    
    sources_used: List[str] = Field(default=[], description="URLs of sources used")
    processing_time_seconds: float = Field(..., description="Total processing time")
    model_used: str = Field(..., description="AI model used for generation")
    content_language: str = Field(default="en", description="Content language")
    # generated_at=datetime.utcnow().isoformat()
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO timestamp of generation")


class GeneratedArticle(BaseModel):
    """Structured generated article output."""

    slug: str = Field(..., description="SEO-friendly article slug")
    title: str = Field(..., description="Article title")
    description: str = Field(..., description="Article meta description")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    body: str = Field(..., description="Markdown article body")


class ArticleAuthorDetails(BaseModel):
    """Author and presentation metadata for a generated article."""

    model_config = ConfigDict(populate_by_name=True)

    author_name: Optional[str] = Field(default=None, alias="authorName")
    author_avatar: Optional[str] = Field(default=None, alias="authorAvatar")
    category: Optional[str] = Field(default=None)
    cover_image: Optional[str] = Field(default=None, alias="coverImage")


class CategoryBase(BaseModel):
    """Category payload."""

    name: str = Field(..., min_length=1, max_length=255, description="Category name")

    @validator("name")
    def validate_name(cls, v):
        value = re.sub(r"\s+", " ", v.strip())
        if not value:
            raise ValueError("Category name cannot be empty")
        return value


class CategoryCreate(CategoryBase):
    """Create category payload."""


class CategoryUpdate(CategoryBase):
    """Update category payload."""


class CategoryResponse(CategoryBase):
    """Category response payload."""

    id: int = Field(..., description="Category ID")
    article_count: int = Field(default=0, description="Number of articles in this category")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")


class ArticleBase(BaseModel):
    """Editable article fields for CMS operations."""

    model_config = ConfigDict(populate_by_name=True)

    slug: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    body: str = Field(..., min_length=1)
    author_name: Optional[str] = Field(default=None, alias="authorName", max_length=120)
    author_avatar: Optional[str] = Field(default=None, alias="authorAvatar", max_length=500)
    category: Optional[str] = Field(default=None, max_length=255)
    cover_image: Optional[str] = Field(default=None, alias="coverImage", max_length=500)
    user_id: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default="draft", max_length=32)
    success: Optional[bool] = Field(default=True)
    sources_used: List[str] = Field(default_factory=list)
    source_details: List[Dict[str, Any]] = Field(default_factory=list)
    seo_scores: Dict[str, Any] = Field(default_factory=dict)
    final_score: Optional[float] = Field(default=0.0)
    model_used: Optional[str] = Field(default=None, max_length=120)
    customization: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = Field(default=None)

    @validator("slug")
    def validate_slug(cls, v):
        value = re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9-]+", "-", v.lower().strip())).strip("-")
        if not value:
            raise ValueError("Slug cannot be empty")
        return value

    @validator("tags", pre=True)
    def normalize_tags(cls, v):
        if isinstance(v, str):
            return [part.strip() for part in v.split(",") if part.strip()]
        return v or []


class ArticleCreate(ArticleBase):
    """Create article payload."""

    keyword: Optional[str] = Field(default=None, max_length=200)
    run_id: Optional[str] = Field(default=None, max_length=64)


class ArticleUpdate(ArticleBase):
    """Update article payload."""


class ArticleResponse(ArticleBase):
    """Article response payload for CMS."""

    id: int = Field(..., description="Article ID")
    run_id: Optional[str] = Field(default=None)
    keyword: Optional[str] = Field(default=None)
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
    
class EnhancedBlogGenerationResponse(BaseModel):
    """Enhanced response schema with detailed information."""

    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(..., description="Unique identifier for this generation run")
    final_blog: str = Field(..., description="Generated blog content")
    article: GeneratedArticle = Field(..., description="Structured generated article")
    seo_scores: SEOScoreDetails = Field(..., description="Detailed SEO score breakdown")
    attempts: int = Field(..., description="Number of attempts made")
    success: bool = Field(..., description="Whether generation was successful")
    
    # Enhanced fields
    metadata: ContentMetadata = Field(..., description="Content generation metadata")
    customization_applied: BlogCustomization = Field(..., description="Applied customization settings")
    author: ArticleAuthorDetails = Field(..., description="Author and display metadata")
    post_id: Optional[int] = Field(default=None, description="Persisted database row ID")
    
    # Optional fields for async processing
    status: Literal["completed", "processing", "failed"] = Field(default="completed")
    progress_percentage: Optional[int] = Field(default=100, ge=0, le=100)
    
    # Analytics
    estimated_reading_time: Optional[int] = Field(default=None, description="Estimated reading time in minutes")
    content_quality_grade: Optional[Literal["A", "B", "C", "D", "F"]] = Field(default=None)

class ApiUsageStats(BaseModel):
    """API usage statistics for monitoring."""
    
    total_requests: int = Field(..., description="Total API requests")
    successful_requests: int = Field(..., description="Successful requests")
    failed_requests: int = Field(..., description="Failed requests")
    average_processing_time: float = Field(..., description="Average processing time in seconds")
    rate_limit_hits: int = Field(..., description="Number of rate limit violations")
    last_request_at: Optional[datetime] = Field(default=None)

class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default={}, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    run_id: Optional[str] = Field(default=None, description="Associated run ID if available")
