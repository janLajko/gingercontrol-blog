"""OpenAI-powered blog generation helpers using the Responses API."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

SOURCE_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "url": {"type": "string"},
        "publisher": {"type": "string"},
        "published_at": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["title", "url", "publisher", "published_at", "reason"],
    "additionalProperties": False,
}

GENERATE_BLOG_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "body": {"type": "string"},
        "sources_used": {
            "type": "array",
            "items": SOURCE_ITEM_SCHEMA,
        },
    },
    "required": ["slug", "title", "description", "tags", "body", "sources_used"],
    "additionalProperties": False,
}

EVALUATE_BLOG_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title_score": {"type": "number"},
        "meta_description_score": {"type": "number"},
        "keyword_optimization_score": {"type": "number"},
        "content_structure_score": {"type": "number"},
        "readability_score": {"type": "number"},
        "content_quality_score": {"type": "number"},
        "technical_seo_score": {"type": "number"},
        "final_score": {"type": "number"},
        "feedback": {"type": "string"},
        "source_quality_score": {"type": "number"},
        "freshness_score": {"type": "number"},
    },
    "required": [
        "title_score",
        "meta_description_score",
        "keyword_optimization_score",
        "content_structure_score",
        "readability_score",
        "content_quality_score",
        "technical_seo_score",
        "final_score",
        "feedback",
        "source_quality_score",
        "freshness_score",
    ],
    "additionalProperties": False,
}

OPTIMIZE_BLOG_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "slug": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
        },
        "body": {"type": "string"},
    },
    "required": ["slug", "title", "description", "tags", "body"],
    "additionalProperties": False,
}


@dataclass
class OpenAIBlogConfig:
    api_key: str
    research_model: str = "gpt-5-mini"
    optimizer_model: str = "gpt-5-mini"
    evaluator_model: str = "gpt-5-mini"
    max_output_tokens: int = 6000


class OpenAIBlogClient:
    """Lazy OpenAI client wrapper for web-search-grounded content generation."""

    _instance: Optional["OpenAIBlogClient"] = None

    def __init__(self, config: OpenAIBlogConfig):
        if not config.api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI blog client.")

        self.config = config
        self._client: Any = None

    @classmethod
    async def get_instance(cls) -> "OpenAIBlogClient":
        if cls._instance is None:
            api_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY
            cls._instance = cls(
                OpenAIBlogConfig(
                    api_key=api_key,
                    research_model=os.getenv(
                        "OPENAI_RESEARCH_MODEL", settings.OPENAI_RESEARCH_MODEL
                    ),
                    optimizer_model=os.getenv(
                        "OPENAI_OPTIMIZER_MODEL", settings.OPENAI_OPTIMIZER_MODEL
                    ),
                    evaluator_model=os.getenv(
                        "OPENAI_EVALUATOR_MODEL", settings.OPENAI_EVALUATOR_MODEL
                    ),
                    max_output_tokens=int(
                        os.getenv(
                            "OPENAI_MAX_OUTPUT_TOKENS",
                            str(settings.OPENAI_MAX_OUTPUT_TOKENS),
                        )
                    ),
                )
            )
        return cls._instance

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "openai package is not installed. Install dependencies first."
                ) from exc

            self._client = AsyncOpenAI(api_key=self.config.api_key)
        return self._client

    async def generate_blog(
        self,
        *,
        keyword: str,
        customization: Optional[Dict[str, Any]] = None,
        feedback: str = "",
        attempt: int = 1,
    ) -> Dict[str, Any]:
        """Research and generate a blog draft with live web search."""
        customization = customization or {}
        prompt = _build_generation_prompt(
            keyword=keyword,
            customization=customization,
            feedback=feedback,
            attempt=attempt,
        )
        response = await self._get_client().responses.create(
            model=self.config.research_model,
            tools=[{"type": "web_search"}],
            tool_choice="auto",
            max_output_tokens=self.config.max_output_tokens,
            text={
                "format": _json_schema_format(
                    name="grounded_blog_article",
                    schema=GENERATE_BLOG_SCHEMA,
                    description="Structured grounded blog article output.",
                )
            },
            input=prompt,
        )
        raw_text = _extract_output_text(response)
        logger.info(
            "OpenAI generate raw response",
            keyword=keyword,
            attempt=attempt,
            raw_response=raw_text,
        )
        payload = _parse_json_payload(raw_text)
        article = _normalize_article_payload(payload, keyword=keyword)
        sources = _normalize_sources(payload.get("sources_used", []))

        if not article["body"]:
            raise ValueError("OpenAI generation returned empty article body")

        logger.info(
            "OpenAI draft generated",
            keyword=keyword,
            attempt=attempt,
            sources=len(sources),
            content_length=len(article["body"]),
            model=self.config.research_model,
        )

        return {
            "article": article,
            "draft_blog": article["body"],
            "sources_used": [source["url"] for source in sources],
            "source_details": sources,
            "model_used": self.config.research_model,
        }

    async def evaluate_blog(
        self,
        *,
        keyword: str,
        article: Dict[str, Any],
        source_details: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Ask a model to score quality and SEO using the current draft."""
        prompt = _build_evaluation_prompt(
            keyword=keyword,
            article=article,
            source_details=source_details or [],
        )
        response = await self._get_client().responses.create(
            model=self.config.evaluator_model,
            max_output_tokens=1600,
            text={
                "format": _json_schema_format(
                    name="blog_quality_assessment",
                    schema=EVALUATE_BLOG_SCHEMA,
                    description="Structured quality and SEO assessment.",
                )
            },
            input=prompt,
        )
        raw_text = _extract_output_text(response)
        logger.info(
            "OpenAI evaluate raw response",
            keyword=keyword,
            raw_response=raw_text,
        )
        payload = _parse_json_payload(raw_text)

        logger.info(
            "OpenAI evaluation completed",
            keyword=keyword,
            model=self.config.evaluator_model,
        )

        return payload

    async def optimize_blog(
        self,
        *,
        keyword: str,
        article: Dict[str, Any],
        feedback: str,
        customization: Optional[Dict[str, Any]] = None,
        source_details: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Optimize a validated draft for SEO while preserving facts and sources."""
        prompt = _build_optimization_prompt(
            keyword=keyword,
            article=article,
            feedback=feedback,
            customization=customization or {},
            source_details=source_details or [],
        )
        response = await self._get_client().responses.create(
            model=self.config.optimizer_model,
            max_output_tokens=self.config.max_output_tokens,
            text={
                "format": _json_schema_format(
                    name="optimized_blog_article",
                    schema=OPTIMIZE_BLOG_SCHEMA,
                    description="Structured optimized article output.",
                )
            },
            input=prompt,
        )
        raw_text = _extract_output_text(response)
        logger.info(
            "OpenAI optimize raw response",
            keyword=keyword,
            raw_response=raw_text,
        )
        payload = _parse_json_payload(raw_text)
        article = _normalize_article_payload(payload, keyword=keyword)

        if not article["body"]:
            raise ValueError("OpenAI optimization returned empty article body")

        logger.info(
            "OpenAI SEO optimization completed",
            keyword=keyword,
            model=self.config.optimizer_model,
            content_length=len(article["body"]),
        )

        return {
            "article": article,
            "final_blog": article["body"],
            "model_used": self.config.optimizer_model,
        }


async def get_openai_blog_client() -> OpenAIBlogClient:
    return await OpenAIBlogClient.get_instance()


def _extract_output_text(response: Any) -> str:
    """Extract plain text from a Responses API payload."""
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    outputs = getattr(response, "output", None) or []
    collected: List[str] = []

    for item in outputs:
        for content in getattr(item, "content", None) or []:
            refusal_text = getattr(content, "refusal", None)
            if refusal_text:
                raise ValueError(f"Model refused structured output: {refusal_text}")
            text_value = getattr(content, "text", None)
            if text_value:
                collected.append(text_value)
            elif isinstance(content, dict):
                if content.get("refusal"):
                    raise ValueError(
                        f"Model refused structured output: {content['refusal']}"
                    )
                if content.get("text"):
                    collected.append(content["text"])

    if collected:
        return "\n".join(collected)

    if isinstance(response, dict):
        return response.get("output_text", "")

    return ""


def _parse_json_payload(raw_text: str) -> Dict[str, Any]:
    """Parse a JSON object from model output."""
    if not raw_text:
        raise ValueError("Model response was empty")

    cleaned = raw_text.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if not match:
            raise ValueError("Model response did not contain a JSON object")
        return json.loads(match.group(1))


def _json_schema_format(*, name: str, schema: Dict[str, Any], description: str) -> Dict[str, Any]:
    """Build a Responses API structured output format."""
    return {
        "type": "json_schema",
        "name": name,
        "description": description,
        "schema": schema,
        "strict": True,
    }


def _normalize_sources(raw_sources: Any) -> List[Dict[str, str]]:
    """Normalize source entries into a predictable structure."""
    normalized: List[Dict[str, str]] = []
    seen_urls = set()

    if not isinstance(raw_sources, list):
        return normalized

    for item in raw_sources:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        normalized.append(
            {
                "title": str(item.get("title", "")).strip(),
                "url": url,
                "publisher": str(item.get("publisher", "")).strip(),
                "published_at": str(item.get("published_at", "")).strip(),
                "reason": str(item.get("reason", "")).strip(),
            }
        )

    return normalized


def _normalize_article_payload(payload: Dict[str, Any], *, keyword: str) -> Dict[str, Any]:
    """Normalize generated article fields and guarantee a usable slug."""
    title = str(payload.get("title", "")).strip()
    description = str(payload.get("description", "")).strip()
    body = str(payload.get("body", "")).strip()
    tags = [
        str(tag).strip()
        for tag in (payload.get("tags") or [])
        if str(tag).strip()
    ]

    raw_slug = str(payload.get("slug", "")).strip()
    slug = _slugify(raw_slug or title or keyword)

    return {
        "slug": slug,
        "title": title,
        "description": description,
        "tags": tags,
        "body": body,
    }


def _slugify(value: str) -> str:
    """Create a stable URL slug."""
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "generated-article"


def _build_generation_prompt(
    *,
    keyword: str,
    customization: Dict[str, Any],
    feedback: str,
    attempt: int,
) -> str:
    focus_keywords = customization.get("focus_keywords") or []
    exclude_domains = customization.get("exclude_domains") or []
    today = datetime.now(timezone.utc).date().isoformat()

    feedback_block = (
        f"Revision feedback from the previous attempt:\n{feedback}\n"
        if feedback
        else "This is the first draft attempt.\n"
    )

    return f"""
You are creating a fact-grounded blog post using live web search on {today}.

Task:
- Research the topic "{keyword}" with the web_search tool before writing.
- Build a current, factual article using reputable and recent sources.
- Prefer primary sources and established news, policy, market, or company publications where relevant.
- Exclude these domains when possible: {", ".join(exclude_domains) if exclude_domains else "none"}.

Audience and format:
- Tone: {customization.get("tone", "professional")}
- Target audience: {customization.get("target_audience", "general")}
- Content type: {customization.get("content_type", "guide")}
- Target word count: {customization.get("word_count_target", 1500)}
- Include FAQ: {bool(customization.get("include_faq", True))}
- Include conclusion: {bool(customization.get("include_conclusion", True))}
- Include table of contents: {bool(customization.get("include_table_of_contents", True))}
- Focus keywords: {", ".join(focus_keywords) if focus_keywords else "none"}

Quality rules:
- Use at least 4 distinct sources unless the topic truly does not support it.
- Preserve concrete dates when discussing recent events or policy changes.
- Do not invent facts, statistics, quotes, or URLs.
- Output the article body in Markdown, not HTML.
- Add a final Markdown section named "Sources" with linked citations.

{feedback_block}
This is attempt #{attempt}. If feedback is present, fix those issues instead of merely rephrasing.

Return only a JSON object with this exact shape:
{{
  "slug": "seo-friendly-slug",
  "title": "Article title",
  "description": "A concise meta description",
  "tags": ["tag-1", "tag-2"],
  "body": "## Heading\\n\\nMarkdown content...",
  "sources_used": [
    {{
      "title": "Source title",
      "url": "https://...",
      "publisher": "Publisher name",
      "published_at": "YYYY-MM-DD or empty string",
      "reason": "Why this source was used"
    }}
  ]
}}
""".strip()


def _build_evaluation_prompt(
    *,
    keyword: str,
    article: Dict[str, Any],
    source_details: List[Dict[str, Any]],
) -> str:
    sources_json = json.dumps(source_details[:8], ensure_ascii=True)
    article_json = json.dumps(article, ensure_ascii=True)
    return f"""
Evaluate the article below for factual discipline, source quality, freshness, and SEO.

Target keyword: {keyword}
Source details: {sources_json}

Return only a JSON object with these exact fields:
{{
  "title_score": 0,
  "meta_description_score": 0,
  "keyword_optimization_score": 0,
  "content_structure_score": 0,
  "readability_score": 0,
  "content_quality_score": 0,
  "technical_seo_score": 0,
  "final_score": 0,
  "feedback": "Short, concrete revision guidance",
  "source_quality_score": 0,
  "freshness_score": 0
}}

Article:
{article_json[:12000]}
""".strip()


def _build_optimization_prompt(
    *,
    keyword: str,
    article: Dict[str, Any],
    feedback: str,
    customization: Dict[str, Any],
    source_details: List[Dict[str, Any]],
) -> str:
    sources_json = json.dumps(source_details[:8], ensure_ascii=True)
    article_json = json.dumps(article, ensure_ascii=True)
    return f"""
Optimize the article below for SEO without weakening factual accuracy.

Rules:
- Keep all facts, dates, and URLs aligned with the provided article and sources.
- Improve slug, title, description, headings, internal structure, and keyword placement.
- Preserve or improve the final markdown "Sources" section.
- Do not fabricate new claims or URLs.
- Keep the tone as {customization.get("tone", "professional")}.
- Keep the article body in Markdown format.

Target keyword: {keyword}
Feedback to address: {feedback or "Polish the article while preserving facts."}
Source details: {sources_json}

Return only a JSON object:
{{
  "slug": "seo-friendly-slug",
  "title": "Article title",
  "description": "A concise meta description",
  "tags": ["tag-1", "tag-2"],
  "body": "## Heading\\n\\nMarkdown content..."
}}

Article:
{article_json[:12000]}
""".strip()
