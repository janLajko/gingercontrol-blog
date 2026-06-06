"""Persistence helpers for generated blog posts and categories."""

from __future__ import annotations

import uuid
from math import ceil
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from src.db.base import Base, get_billing_engine, get_engine, get_session_local
from src.db.models import (
    BillingEntitlementGrantRecord,
    BillingFeaturePolicyRecord,
    BillingProductRecord,
    BillingPurchaseRecord,
    BillingUsageEventRecord,
    BlogPost,
    Category,
    OpenApiClientRecord,
    OpenApiKeyRecord,
    UserRecord,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _normalize_optional_string(value: Any) -> Optional[str]:
    """Normalize optional string inputs from API payloads."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    return value or None


def _prepare_blog_post_payload(
    payload: Dict[str, Any],
    *,
    existing: Optional[BlogPost] = None,
) -> Dict[str, Any]:
    """Normalize payloads so manual and AI-created articles share one persistence path."""
    normalized = dict(payload)

    title = _normalize_optional_string(normalized.get("title")) or (
        existing.title if existing is not None else None
    )
    keyword = _normalize_optional_string(normalized.get("keyword")) or (
        existing.keyword if existing is not None else None
    )
    run_id = _normalize_optional_string(normalized.get("run_id")) or (
        existing.run_id if existing is not None else None
    )

    normalized["title"] = title
    normalized["slug"] = _normalize_optional_string(normalized.get("slug")) or (
        existing.slug if existing is not None else None
    )
    normalized["description"] = _normalize_optional_string(
        normalized.get("description")
    ) or (existing.description if existing is not None else None)
    normalized["body"] = _normalize_optional_string(normalized.get("body")) or (
        existing.body if existing is not None else None
    )
    normalized["author_name"] = _normalize_optional_string(
        normalized.get("author_name")
    )
    normalized["author_avatar"] = _normalize_optional_string(
        normalized.get("author_avatar")
    )
    normalized["category"] = _normalize_optional_string(normalized.get("category"))
    normalized["cover_image"] = _normalize_optional_string(
        normalized.get("cover_image")
    )
    normalized["user_id"] = _normalize_optional_string(normalized.get("user_id"))
    normalized["model_used"] = _normalize_optional_string(normalized.get("model_used"))
    normalized["error_message"] = _normalize_optional_string(
        normalized.get("error_message")
    )
    normalized_status = _normalize_optional_string(normalized.get("status"))

    normalized["keyword"] = keyword or title
    normalized["run_id"] = run_id or f"manual-{uuid.uuid4().hex[:24]}"
    normalized["tags"] = normalized.get("tags") or []
    normalized["customization"] = normalized.get("customization") or {}
    normalized["sources_used"] = normalized.get("sources_used") or []
    normalized["source_details"] = normalized.get("source_details") or []
    normalized["seo_scores"] = normalized.get("seo_scores") or {}

    if normalized.get("final_score") is None:
        normalized["final_score"] = 0.0
    if normalized.get("success") is None:
        normalized["success"] = True
    normalized["status"] = normalized_status or "draft"
    normalized.setdefault("type", "article")

    return normalized


def init_db() -> None:
    """Create blog tables and billing tables on their configured databases."""
    engine = get_engine()
    if engine is None:
        logger.warning("DATABASE_URL is not configured. Skipping blog database init.")
    else:
        Base.metadata.create_all(
            bind=engine,
            tables=[BlogPost.__table__, Category.__table__],
        )
        logger.info("Blog database tables initialized")

    billing_engine = get_billing_engine()
    if billing_engine is None:
        logger.warning(
            "BILLING_DATABASE_URL is not configured. Skipping billing database init."
        )
    else:
        Base.metadata.create_all(
            bind=billing_engine,
            tables=[
                UserRecord.__table__,
                BillingProductRecord.__table__,
                BillingFeaturePolicyRecord.__table__,
                BillingPurchaseRecord.__table__,
                BillingEntitlementGrantRecord.__table__,
                BillingUsageEventRecord.__table__,
                OpenApiClientRecord.__table__,
                OpenApiKeyRecord.__table__,
            ],
        )
        logger.info("Billing database tables initialized")


def save_blog_post(payload: Dict[str, Any]) -> Optional[int]:
    """Persist a generated blog post and return its row ID."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping blog persistence.")
        return None

    session = session_local()
    try:
        blog_post = BlogPost(**_prepare_blog_post_payload(payload))
        session.add(blog_post)
        session.commit()
        session.refresh(blog_post)
        logger.info(
            "Blog post persisted", post_id=blog_post.id, run_id=blog_post.run_id
        )
        return blog_post.id
    except Exception as exc:
        session.rollback()
        logger.error("Failed to persist blog post", error=str(exc))
        raise
    finally:
        session.close()


def list_blog_posts(
    category: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    title: Optional[str] = None,
) -> List[BlogPost]:
    """Return all blog posts ordered by newest first."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping blog listing.")
        return []

    session = session_local()
    try:
        stmt = select(BlogPost).order_by(BlogPost.created_at.desc(), BlogPost.id.desc())
        normalized_category = (category or "").strip()
        normalized_status = (status or "").strip()
        normalized_type = (type or "").strip()
        normalized_title = (title or "").strip()
        if normalized_category:
            stmt = stmt.where(BlogPost.category == normalized_category)
        if normalized_status:
            stmt = stmt.where(BlogPost.status == normalized_status)
        if normalized_type:
            stmt = stmt.where(BlogPost.type == normalized_type)
        if normalized_title:
            stmt = stmt.where(BlogPost.title.ilike(f"%{normalized_title}%"))
        return list(session.execute(stmt).scalars().all())
    finally:
        session.close()


def list_blog_post_summaries(
    *,
    page: int = 1,
    page_limit: int = 20,
    category: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a paginated list of article summaries."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping blog listing.")
        return {
            "page": page,
            "page_limit": page_limit,
            "total_count": 0,
            "total_pages": 0,
            "articles": [],
        }

    session = session_local()
    try:
        normalized_category = (category or "").strip()
        normalized_status = (status or "").strip()
        normalized_type = (type or "").strip()
        normalized_title = (title or "").strip()

        count_stmt = select(func.count()).select_from(BlogPost)
        items_stmt = (
            select(
                BlogPost.id,
                BlogPost.slug,
                BlogPost.title,
                BlogPost.description,
                BlogPost.tags,
                BlogPost.created_at,
                BlogPost.final_score,
                BlogPost.cover_image,
                BlogPost.author_name,
                BlogPost.author_avatar,
                BlogPost.category,
                BlogPost.type,
            )
            .order_by(BlogPost.created_at.desc(), BlogPost.id.desc())
            .offset((page - 1) * page_limit)
            .limit(page_limit)
        )

        if normalized_category:
            count_stmt = count_stmt.where(BlogPost.category == normalized_category)
            items_stmt = items_stmt.where(BlogPost.category == normalized_category)
        if normalized_status:
            count_stmt = count_stmt.where(BlogPost.status == normalized_status)
            items_stmt = items_stmt.where(BlogPost.status == normalized_status)
        if normalized_type:
            count_stmt = count_stmt.where(BlogPost.type == normalized_type)
            items_stmt = items_stmt.where(BlogPost.type == normalized_type)
        if normalized_title:
            count_stmt = count_stmt.where(BlogPost.title.ilike(f"%{normalized_title}%"))
            items_stmt = items_stmt.where(BlogPost.title.ilike(f"%{normalized_title}%"))

        total_count = int(session.execute(count_stmt).scalar_one() or 0)
        total_pages = ceil(total_count / page_limit) if total_count > 0 else 0

        rows = session.execute(items_stmt).all()
        articles = [
            {
                "id": row.id,
                "slug": row.slug,
                "title": row.title,
                "description": row.description,
                "tags": row.tags or [],
                "created_at": row.created_at,
                "final_score": row.final_score,
                "cover_image": row.cover_image,
                "author_name": row.author_name,
                "author_avatar": row.author_avatar,
                "category": row.category,
                "type": row.type,
            }
            for row in rows
        ]

        return {
            "page": page,
            "page_limit": page_limit,
            "total_count": total_count,
            "total_pages": total_pages,
            "articles": articles,
        }
    finally:
        session.close()


def get_blog_post(post_id: int) -> Optional[BlogPost]:
    """Return one blog post by primary key."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping blog lookup.")
        return None

    session = session_local()
    try:
        return session.get(BlogPost, post_id)
    finally:
        session.close()


def create_blog_post(payload: Dict[str, Any]) -> BlogPost:
    """Create a blog post from a payload."""
    session_local = get_session_local()
    if session_local is None:
        raise RuntimeError("DATABASE_URL is not configured.")

    session = session_local()
    try:
        blog_post = BlogPost(**_prepare_blog_post_payload(payload))
        session.add(blog_post)
        session.commit()
        session.refresh(blog_post)
        logger.info("Blog post created", post_id=blog_post.id, slug=blog_post.slug)
        return blog_post
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_blog_post(post_id: int, payload: Dict[str, Any]) -> Optional[BlogPost]:
    """Update a persisted blog post."""
    session_local = get_session_local()
    if session_local is None:
        raise RuntimeError("DATABASE_URL is not configured.")

    session = session_local()
    try:
        blog_post = session.get(BlogPost, post_id)
        if blog_post is None:
            return None

        normalized_payload = _prepare_blog_post_payload(payload, existing=blog_post)
        for key, value in normalized_payload.items():
            setattr(blog_post, key, value)

        session.commit()
        session.refresh(blog_post)
        logger.info("Blog post updated", post_id=blog_post.id, slug=blog_post.slug)
        return blog_post
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_blog_post(post_id: int) -> bool:
    """Delete a blog post by ID."""
    session_local = get_session_local()
    if session_local is None:
        raise RuntimeError("DATABASE_URL is not configured.")

    session = session_local()
    try:
        blog_post = session.get(BlogPost, post_id)
        if blog_post is None:
            return False

        session.delete(blog_post)
        session.commit()
        logger.info("Blog post deleted", post_id=post_id)
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _serialize_category_with_count(
    category: Category, article_count: int
) -> Dict[str, Any]:
    """Convert a category row plus article count into a response payload."""
    return {
        "id": category.id,
        "name": category.name,
        "article_count": int(article_count or 0),
        "created_at": category.created_at,
        "updated_at": category.updated_at,
    }


def list_categories() -> List[Dict[str, Any]]:
    """Return all categories ordered by name with article counts."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping category listing.")
        return []

    session = session_local()
    try:
        stmt = (
            select(Category, func.count(BlogPost.id))
            .outerjoin(BlogPost, BlogPost.category == Category.name)
            .group_by(Category.id)
            .order_by(Category.name.asc())
        )
        rows = session.execute(stmt).all()
        return [
            _serialize_category_with_count(category, article_count)
            for category, article_count in rows
        ]
    finally:
        session.close()


def get_category_by_id(category_id: int) -> Optional[Dict[str, Any]]:
    """Return one category by primary key with article count."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping category lookup.")
        return None

    session = session_local()
    try:
        stmt = (
            select(Category, func.count(BlogPost.id))
            .outerjoin(BlogPost, BlogPost.category == Category.name)
            .where(Category.id == category_id)
            .group_by(Category.id)
        )
        row = session.execute(stmt).one_or_none()
        if row is None:
            return None
        category, article_count = row
        return _serialize_category_with_count(category, article_count)
    finally:
        session.close()


def create_category(name: str) -> Category:
    """Create a unique category."""
    session_local = get_session_local()
    if session_local is None:
        raise RuntimeError("DATABASE_URL is not configured.")

    session = session_local()
    try:
        existing = session.execute(
            select(Category).where(Category.name == name)
        ).scalar_one_or_none()
        if existing is not None:
            raise ValueError("Category already exists.")

        category = Category(name=name)
        session.add(category)
        session.commit()
        session.refresh(category)
        logger.info("Category created", category_id=category.id, name=category.name)
        return category
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_category(category_id: int, name: str) -> Optional[Category]:
    """Update a category name."""
    session_local = get_session_local()
    if session_local is None:
        raise RuntimeError("DATABASE_URL is not configured.")

    session = session_local()
    try:
        category = session.get(Category, category_id)
        if category is None:
            return None

        existing = session.execute(
            select(Category).where(Category.name == name, Category.id != category_id)
        ).scalar_one_or_none()
        if existing is not None:
            raise ValueError("Category already exists.")

        category.name = name
        session.commit()
        session.refresh(category)
        logger.info("Category updated", category_id=category.id, name=category.name)
        return category
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def delete_category(category_id: int) -> bool:
    """Delete a category by ID."""
    session_local = get_session_local()
    if session_local is None:
        raise RuntimeError("DATABASE_URL is not configured.")

    session = session_local()
    try:
        category = session.get(Category, category_id)
        if category is None:
            return False

        session.delete(category)
        session.commit()
        logger.info("Category deleted", category_id=category_id)
        return True
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
