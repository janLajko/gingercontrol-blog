"""Enhanced blog generation API routes with security and better customization."""

import uuid
import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request, File, UploadFile, Query
from fastapi.responses import JSONResponse

from src.schemas.models import (
    EnhancedBlogGenerationRequest,
    EnhancedBlogGenerationResponse,
    SEOScoreDetails,
    ContentMetadata,
    BlogCustomization,
    GeneratedArticle,
    ArticleAuthorDetails,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    ArticleCreate,
    ArticleUpdate,
    ArticleResponse,
    PaginatedArticleListResponse,
)
from src.api.auth import verify_api_key
from src.agents.graph import get_blog_generation_graph
from src.config.settings import GCS_CMS_IMAGE_PREFIX
from src.db.service import (
    save_blog_post,
    list_blog_post_summaries,
    get_blog_post,
    create_blog_post,
    update_blog_post,
    delete_blog_post,
    list_categories,
    get_category_by_id,
    create_category,
    update_category,
    delete_category,
)
from src.service.gcs_upload_service import GcsUploadService
from src.utils.logger import get_logger
from src.utils.seo import calculate_keyword_density, normalize_seo_scores
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["blog"])

@router.post(
    "/generate-blog",
    response_model=EnhancedBlogGenerationResponse,
    summary="Generate Enhanced SEO-optimized blog content",
    description="Generate a comprehensive, customizable blog post using AI agents with advanced options",
)
async def generate_enhanced_blog(
    request: EnhancedBlogGenerationRequest,
    background_tasks: BackgroundTasks,
    # authorized: bool = Depends(verify_api_key),
    fastapi_request: Request = None
) -> EnhancedBlogGenerationResponse:
    """Generate enhanced SEO-optimized blog content with customization options.

    This endpoint provides advanced blog generation with:
    - Custom tone, audience, and content type
    - Flexible word count targets
    - Advanced SEO optimization
    - Detailed analytics and metadata
    - Rate limiting and security

    Args:
        request: Enhanced blog generation request with customization options
        background_tasks: FastAPI background tasks
        authorized: API key verification result
        fastapi_request: FastAPI request object for tracking

    Returns:
        EnhancedBlogGenerationResponse with detailed content and analytics

    Raises:
        HTTPException: If generation fails or validation errors occur
    """
    start_time = time.time()
    run_id = str(uuid.uuid4())
    app_state = (
        fastapi_request.app.state
        if fastapi_request is not None and hasattr(fastapi_request, "app")
        else None
    )

    # Track usage statistics
    if app_state is not None and hasattr(app_state, 'usage_stats'):
        app_state.usage_stats["total_requests"] += 1

    logger.info(
        "Enhanced blog generation request received",
        run_id=run_id,
        keyword=request.keyword,
        max_attempts=request.max_attempts,
        seo_threshold=request.seo_threshold,
        user_id=request.user_id,
        priority=request.priority,
        customization=request.customization.dict(),
        timestamp=datetime.utcnow().isoformat(),
    )

    try:
        # Validate and prepare customization
        customization = request.customization or BlogCustomization()
        
        # Get blog generation graph
        blog_graph = await get_blog_generation_graph()

        # Execute workflow with enhanced parameters
        result = await blog_graph.run_blog_generation(
            keyword=request.keyword.strip(),
            customization=customization.model_dump(),
            max_attempts=request.max_attempts or 3,
            seo_threshold=request.seo_threshold or 75.0,
            thread_id=run_id,
        )

        processing_time = time.time() - start_time

        # Calculate additional metrics
        article_payload = result.get("article") or {}
        article = GeneratedArticle(
            slug=article_payload.get("slug", ""),
            title=article_payload.get("title", ""),
            description=article_payload.get("description", ""),
            tags=article_payload.get("tags", []),
            body=article_payload.get("body", result["final_blog"]),
        )
        word_count = len(article.body.split()) if article.body else 0
        reading_time = max(1, word_count // 200)  # ~200 words per minute
        
        # Determine content quality grade based on SEO score
        final_score = result["final_score"]
        if final_score >= 90:
            quality_grade = "A"
        elif final_score >= 80:
            quality_grade = "B"
        elif final_score >= 70:
            quality_grade = "C"
        elif final_score >= 60:
            quality_grade = "D"
        else:
            quality_grade = "F"

        # Create enhanced SEO scores
        normalized_scores = normalize_seo_scores(
            result.get("seo_scores"),
            fallback_final_score=final_score,
        )
        seo_scores = SEOScoreDetails(
            **normalized_scores,
            word_count=word_count,
            reading_time_minutes=reading_time,
            keyword_density=result.get(
                "keyword_density",
                calculate_keyword_density(article.body, request.keyword),
            ),
        )

        # Create metadata
        metadata = ContentMetadata(
            sources_used=result.get("sources_used", []),
            processing_time_seconds=round(processing_time, 2),
            model_used=result.get("model_used", "gpt-5-mini"),
            content_language="en",
            # generated_at=datetime.utcnow()
        )

        author = ArticleAuthorDetails(
            author_name=request.author_name,
            author_avatar=request.author_avatar,
            category=request.category,
            cover_image=request.cover_image,
        )

        post_id = None
        try:
            post_id = save_blog_post(
                {
                    "run_id": run_id,
                    "keyword": request.keyword,
                    "slug": article.slug,
                    "title": article.title,
                    "description": article.description,
                    "body": article.body,
                    "tags": article.tags,
                    "author_name": request.author_name,
                    "author_avatar": request.author_avatar,
                    "category": request.category,
                    "cover_image": request.cover_image,
                    "user_id": request.user_id,
                    "customization": customization.model_dump(),
                    "sources_used": result.get("sources_used", []),
                    "source_details": result.get("source_details", []),
                    "seo_scores": normalized_scores,
                    "final_score": final_score,
                    "model_used": result.get("model_used", "gpt-5-mini"),
                    "success": result["success"],
                    "status": "completed" if result["success"] else "failed",
                    "error_message": result.get("error"),
                }
            )
        except Exception as db_error:
            logger.warning(
                "Failed to persist generated blog post",
                run_id=run_id,
                keyword=request.keyword,
                error=str(db_error),
            )

        # Create enhanced response
        response = EnhancedBlogGenerationResponse(
            run_id=run_id,
            final_blog=article.body,
            article=article,
            seo_scores=seo_scores,
            attempts=result["attempts"],
            success=result["success"],
            metadata=metadata,
            customization_applied=customization,
            author=author,
            post_id=post_id,
            status="completed" if result["success"] else "failed",
            progress_percentage=100,
            estimated_reading_time=reading_time,
            content_quality_grade=quality_grade
        )

        # Update usage statistics
        if app_state is not None and hasattr(app_state, 'usage_stats'):
            if result["success"]:
                app_state.usage_stats["successful_requests"] += 1
            else:
                app_state.usage_stats["failed_requests"] += 1

        # Send webhook notification if callback URL provided
        if request.callback_url:
            background_tasks.add_task(
                send_webhook_notification,
                request.callback_url,
                response.dict(),
                run_id
            )

        logger.info(
            "Enhanced blog generation completed",
            run_id=run_id,
            keyword=request.keyword,
            final_score=final_score,
            attempts=result["attempts"],
            content_length=len(article.body),
            word_count=word_count,
            processing_time=round(processing_time, 2),
            quality_grade=quality_grade,
            success=result["success"],
        )

        return response

    except HTTPException:
        # Update failed requests counter
        if app_state is not None and hasattr(app_state, 'usage_stats'):
            app_state.usage_stats["failed_requests"] += 1
        raise
    except Exception as e:
        # Update failed requests counter
        if app_state is not None and hasattr(app_state, 'usage_stats'):
            app_state.usage_stats["failed_requests"] += 1
            
        logger.error(
            "Enhanced blog generation failed with unexpected error",
            run_id=run_id,
            keyword=request.keyword,
            error=str(e),
            error_type=type(e).__name__,
            processing_time=round(time.time() - start_time, 2)
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Blog generation failed: {str(e)}"
        )

async def send_webhook_notification(callback_url: str, response_data: dict, run_id: str):
    """Send webhook notification for async processing."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                callback_url,
                json=response_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    logger.info("Webhook notification sent successfully", run_id=run_id)
                else:
                    logger.warning(
                        "Webhook notification failed",
                        run_id=run_id,
                        status=resp.status
                    )
    except Exception as e:
        logger.error(
            "Failed to send webhook notification",
            run_id=run_id,
            error=str(e)
        )

# Legacy endpoint for backward compatibility
@router.post(
    "/generate-blog-simple",
    summary="Simple blog generation (legacy)",
    description="Legacy endpoint for backward compatibility"
)
async def generate_blog_simple(
    request: dict,
    authorized: bool = Depends(verify_api_key)
):
    """Legacy endpoint for backward compatibility."""
    # Convert legacy request to enhanced request
    enhanced_request = EnhancedBlogGenerationRequest(
        keyword=request.get("keyword"),
        max_attempts=request.get("max_attempts", 3),
        seo_threshold=request.get("seo_threshold", 75.0)
    )
    
    # Call enhanced endpoint
    response = await generate_enhanced_blog(
        request=enhanced_request,
        background_tasks=BackgroundTasks(),
        fastapi_request=None,
    )
    
    # Return simplified response for backward compatibility
    return {
        "run_id": response.run_id,
        "final_blog": response.final_blog,
        "article": response.article.model_dump(),
        "seo_scores": response.seo_scores.dict(),
        "attempts": response.attempts,
        "success": response.success
    }


@router.get(
    "/articles",
    response_model=PaginatedArticleListResponse,
    summary="List articles",
    description="Return a paginated list of article summaries ordered by newest first",
)
async def get_articles(
    category: str | None = Query(
        default=None,
        description="Optional category filter. Matches the article category exactly.",
    ),
    page: int = Query(default=1, ge=1, description="Page number, starting from 1"),
    page_limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of articles returned per page",
    ),
):
    """List paginated article summaries, optionally filtered by category."""
    return list_blog_post_summaries(
        page=page,
        page_limit=page_limit,
        category=category,
    )


@router.get(
    "/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Get article",
    description="Return one article by ID",
)
async def get_article(article_id: int):
    """Get a single article."""
    article = get_blog_post(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post(
    "/articles",
    response_model=ArticleResponse,
    status_code=201,
    summary="Create article",
    description="Create a new article record",
)
async def create_article_endpoint(payload: ArticleCreate):
    """Create a new article from CMS input."""
    try:
        article = create_blog_post(payload.model_dump())
        return article
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put(
    "/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Update article",
    description="Update an existing article record",
)
async def update_article_endpoint(article_id: int, payload: ArticleUpdate):
    """Update a persisted article."""
    try:
        article = update_blog_post(article_id, payload.model_dump())
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.delete(
    "/articles/{article_id}",
    summary="Delete article",
    description="Delete an article by ID",
)
async def delete_article_endpoint(article_id: int):
    """Delete an article."""
    try:
        deleted = delete_blog_post(article_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Article not found")
    return {"success": True, "id": article_id}


@router.post(
    "/uploads/images",
    summary="Upload article image",
    description="Upload a CMS image to Google Cloud Storage and return its public URL",
)
async def upload_article_image(file: UploadFile = File(...)):
    """Upload an image for CMS article cover/avatar usage."""
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported")

    try:
        upload_service = GcsUploadService(prefix=GCS_CMS_IMAGE_PREFIX)
        uploaded = upload_service.upload_fileobj(
            fileobj=file.file,
            filename=file.filename or "image",
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        logger.error(
            "Failed to upload CMS image",
            filename=file.filename,
            content_type=file.content_type,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail="Image upload failed") from exc
    finally:
        await file.close()

    logger.info(
        "CMS image uploaded",
        filename=file.filename,
        content_type=uploaded.content_type,
        gcs_uri=uploaded.gcs_uri,
        public_url=uploaded.public_url,
        size_bytes=uploaded.size_bytes,
    )

    return {
        "success": True,
        "filename": file.filename,
        "content_type": uploaded.content_type,
        "size_bytes": uploaded.size_bytes,
        "gcs_uri": uploaded.gcs_uri,
        "url": uploaded.public_url,
    }


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="List categories",
    description="Return all categories ordered by name",
)
async def get_categories():
    """List all categories."""
    return list_categories()


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Get category",
    description="Return one category by ID",
)
async def get_category(category_id: int):
    """Get a single category."""
    category = get_category_by_id(category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=201,
    summary="Create category",
    description="Create a new unique category",
)
async def create_category_endpoint(payload: CategoryCreate):
    """Create a category."""
    try:
        category = create_category(payload.name)
        return {
            "id": category.id,
            "name": category.name,
            "article_count": 0,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
        }
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Update category",
    description="Rename an existing category",
)
async def update_category_endpoint(category_id: int, payload: CategoryUpdate):
    """Update a category."""
    try:
        category = update_category(category_id, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return {
        "id": category.id,
        "name": category.name,
        "article_count": 0,
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


@router.delete(
    "/categories/{category_id}",
    summary="Delete category",
    description="Delete a category by ID",
)
async def delete_category_endpoint(category_id: int):
    """Delete a category."""
    try:
        deleted = delete_category(category_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"success": True, "id": category_id}
