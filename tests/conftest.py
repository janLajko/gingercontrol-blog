"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.api.app import create_app
from src.config import settings
from src.schemas.state import GraphState


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_keyword() -> str:
    return "fastapi tutorial"


@pytest.fixture
def sample_graph_state(sample_keyword: str) -> GraphState:
    return GraphState(
        keyword=sample_keyword,
        customization={"tone": "professional"},
        max_attempts=3,
        seo_threshold=75.0,
    )


@pytest.fixture
def sample_source_details():
    return [
        {
            "title": "FastAPI Official Tutorial",
            "url": "https://fastapi.tiangolo.com/tutorial/",
            "publisher": "FastAPI",
            "published_at": "2026-03-01",
            "reason": "Primary product documentation",
        },
        {
            "title": "Starlette Documentation",
            "url": "https://www.starlette.io/",
            "publisher": "Starlette",
            "published_at": "2026-02-10",
            "reason": "Framework context",
        },
    ]


@pytest.fixture
def sample_blog_content():
    return """
    # Complete FastAPI Tutorial

    Learn FastAPI with a practical tutorial covering setup, routing, validation, deployment, and best practices for modern APIs.

    ## Table of Contents

    Introduction and key sections.

    ## What Is FastAPI?

    FastAPI is a Python framework for building APIs with type hints.

    ## Getting Started

    Install FastAPI and Uvicorn to begin building endpoints quickly.

    ## Validation and Serialization

    Pydantic models help validate request and response payloads.

    ## Deployment

    Deploy FastAPI behind an ASGI server and a reverse proxy.

    ## FAQ

    ### Is FastAPI production ready?

    Yes. Many teams use FastAPI in production workloads.

    ## Conclusion

    FastAPI is a strong option for modern Python API development.

    ## Sources

    - [FastAPI Docs](https://fastapi.tiangolo.com/tutorial/)
    """


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_RESEARCH_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OPENAI_EVALUATOR_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OPENAI_OPTIMIZER_MODEL", "gpt-5-mini")
    monkeypatch.setenv("OPENAI_MAX_OUTPUT_TOKENS", "4000")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-pro-latest")
    monkeypatch.setenv("LANGSMITH_API_KEY", "")
    monkeypatch.setenv("MAX_CONCURRENT_REQUESTS", "5")
    monkeypatch.setenv("MAX_SCRAPE_TIMEOUT", "5")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("TRUSTED_HOSTS", "testserver,localhost,127.0.0.1")
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setattr(settings, "DATABASE_URL", None)
