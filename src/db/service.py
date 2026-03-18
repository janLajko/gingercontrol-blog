"""Persistence helpers for generated blog posts and categories."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select

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


def list_blog_posts() -> List[BlogPost]:
    """Return all blog posts ordered by newest first."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping blog listing.")
        return []

    session = session_local()
    try:
        stmt = select(BlogPost).order_by(BlogPost.created_at.desc(), BlogPost.id.desc())
        return list(session.execute(stmt).scalars().all())
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


def list_categories() -> List[Category]:
    """Return all categories ordered by name."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping category listing.")
        return []

    session = session_local()
    try:
        stmt = select(Category).order_by(Category.name.asc())
        return list(session.execute(stmt).scalars().all())
    finally:
        session.close()


def get_category_by_id(category_id: int) -> Optional[Category]:
    """Return one category by primary key."""
    session_local = get_session_local()
    if session_local is None:
        logger.warning("DATABASE_URL is not configured. Skipping category lookup.")
        return None

    session = session_local()
    try:
        return session.get(Category, category_id)
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
