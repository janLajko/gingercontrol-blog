"""Persistence helpers for generated blog posts and categories."""

from __future__ import annotations

from math import ceil
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select

from src.db.base import Base, get_engine, get_session_local
from src.db.models import BlogPost, Category
from src.utils.logger import get_logger

logger = get_logger(__name__)


def init_db() -> None:
    """Create database tables when DATABASE_URL is configured."""
    engine = get_engine()
    if engine is None:
        logger.warning("DATABASE_URL is not configured. Skipping database init.")
        return
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


def save_blog_post(payload: Dict[str, Any]) -> Optional[int]:
    """Persist a generated blog post and return its row ID."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping blog persistence.")
        return None

    session = session_local()
    try:
        blog_post = BlogPost(**payload)
        session.add(blog_post)
        session.commit()
        session.refresh(blog_post)
        logger.info("Blog post persisted", post_id=blog_post.id, run_id=blog_post.run_id)
        return blog_post.id
    except Exception as exc:
        session.rollback()
        logger.error("Failed to persist blog post", error=str(exc))
        raise
    finally:
        session.close()


def list_blog_posts(category: Optional[str] = None) -> List[BlogPost]:
    """Return all blog posts ordered by newest first."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping blog listing.")
        return []

    session = session_local()
    try:
        stmt = select(BlogPost).order_by(BlogPost.created_at.desc(), BlogPost.id.desc())
        normalized_category = (category or "").strip()
        if normalized_category:
            stmt = stmt.where(BlogPost.category == normalized_category)
        return list(session.execute(stmt).scalars().all())
    finally:
        session.close()


def list_blog_post_summaries(
    *,
    page: int = 1,
    page_limit: int = 20,
    category: Optional[str] = None,
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

        count_stmt = select(func.count()).select_from(BlogPost)
        items_stmt = (
            select(
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
            )
            .order_by(BlogPost.created_at.desc(), BlogPost.id.desc())
            .offset((page - 1) * page_limit)
            .limit(page_limit)
        )

        if normalized_category:
            count_stmt = count_stmt.where(BlogPost.category == normalized_category)
            items_stmt = items_stmt.where(BlogPost.category == normalized_category)

        total_count = int(session.execute(count_stmt).scalar_one() or 0)
        total_pages = ceil(total_count / page_limit) if total_count > 0 else 0

        rows = session.execute(items_stmt).all()
        articles = [
            {
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
        blog_post = BlogPost(**payload)
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

        for key, value in payload.items():
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


def _serialize_category_with_count(category: Category, article_count: int) -> Dict[str, Any]:
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
