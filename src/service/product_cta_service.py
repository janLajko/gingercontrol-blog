"""Append GingerControl product CTAs to generated articles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse


@dataclass(frozen=True)
class ProductLinkRule:
    """Rule used to match an article to a GingerControl product page."""

    product_id: str
    name: str
    url: str
    keywords: tuple[str, ...]
    priority: int
    cta: str


PRODUCT_LINK_RULES: tuple[ProductLinkRule, ...] = (
    ProductLinkRule(
        product_id="export_control",
        name="GingerControl Export Control",
        url="https://gingercontrol.com/products/export-control",
        keywords=(
            "eccn",
            "bis",
            "ear",
            "export control",
            "export license",
            "license processing",
            "snap-r",
            "china license",
            "dual-use",
        ),
        priority=100,
        cta=(
            "If your team needs a repeatable way to assess export-control risk, "
            "use [GingerControl Export Control]({url}) to review ECCN exposure, "
            "license requirements, and export-control workflows before shipments move."
        ),
    ),
    ProductLinkRule(
        product_id="hts_classifier",
        name="GingerControl HTS Classifier",
        url="https://gingercontrol.com/products/hts-classifier",
        keywords=(
            "hts classification",
            "hts code",
            "tariff classification",
            "classification",
            "gri",
            "cross ruling",
            "cbp ruling",
            "ruling",
            "heading",
            "subheading",
        ),
        priority=90,
        cta=(
            "If you need to turn this classification analysis into a documented "
            "workflow, use [GingerControl HTS Classifier]({url}) to classify "
            "products, compare rulings, and preserve the reasoning behind each HTS decision."
        ),
    ),
    ProductLinkRule(
        product_id="tariff_calculator",
        name="GingerControl Tariff Calculator",
        url="https://gingercontrol.com/products/tariff-calculator",
        keywords=(
            "tariff",
            "duty",
            "landed cost",
            "section 301",
            "section 232",
            "ieepa",
            "import cost",
            "duty rate",
            "customs value",
            "tariff stacking",
        ),
        priority=80,
        cta=(
            "If your team needs to model the numbers before making a shipment decision, "
            "use [GingerControl Tariff Calculator]({url}) to estimate duties, stacked tariffs, "
            "and landed cost by product and origin."
        ),
    ),
    ProductLinkRule(
        product_id="compliance_radar",
        name="GingerControl Compliance Radar",
        url="https://gingercontrol.com/products/compliance-radar",
        keywords=(
            "policy alert",
            "trade policy",
            "compliance monitoring",
            "tariff change",
            "regulatory update",
            "monitor",
            "alerts",
            "watch",
            "risk alert",
        ),
        priority=75,
        cta=(
            "If you need to catch trade-policy changes before they affect margin or operations, "
            "use [GingerControl Compliance Radar]({url}) to monitor tariff, customs, "
            "and enforcement updates tied to your products."
        ),
    ),
    ProductLinkRule(
        product_id="openapi",
        name="GingerControl OpenAPI",
        url="https://gingercontrol.com/products/openapi",
        keywords=(
            "openapi",
            "api",
            "integration",
            "automation",
            "3pl",
            "ecommerce",
            "platform",
            "scale",
            "workflow",
        ),
        priority=70,
        cta=(
            "If your team needs to embed this workflow into internal systems, "
            "use [GingerControl OpenAPI]({url}) to integrate HTS, duty, tax, "
            "and compliance checks directly into your product or logistics stack."
        ),
    ),
    ProductLinkRule(
        product_id="product_sandbox",
        name="GingerControl Product Sandbox",
        url="https://gingercontrol.com/products/product-sandbox",
        keywords=(
            "scenario",
            "simulate",
            "simulation",
            "nearshoring",
            "origin planning",
            "fta",
            "sourcing",
            "sku",
            "country of origin",
            "supply chain",
        ),
        priority=65,
        cta=(
            "If you need to compare sourcing, origin, or SKU-level scenarios before changing suppliers, "
            "use [GingerControl Product Sandbox]({url}) to test duty impact and compliance exposure "
            "across product plans."
        ),
    ),
)

PRODUCT_URL_PATH_RE = re.compile(
    r"https?://(?:www\.)?gingercontrol\.com/(?:zh-cn/|zh-tw/)?products/[^)\s\"'<>]+",
    re.IGNORECASE,
)
PRODUCT_HREF_PATH_RE = re.compile(
    r"href=[\"'](/(?:zh-cn/|zh-tw/)?products/[^\"'#?]+)",
    re.IGNORECASE,
)


def append_product_cta(
    article: dict[str, Any],
    *,
    keyword: str = "",
    min_score: int = 1,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return article with a matched product CTA appended to the body.

    A CTA is skipped when the tail of the article already includes a GingerControl
    product link. This prevents repeated CTA blocks during retries or manual edits.
    """

    body = str(article.get("body") or "").strip()
    if not body:
        return article, None

    existing_tail_url = find_tail_product_url(body)
    if existing_tail_url:
        metadata = {
            "appended": False,
            "reason": "tail_product_link_exists",
            "url": existing_tail_url,
        }
        return article, metadata

    match = match_product_for_article(article, keyword=keyword)
    if match["score"] < min_score:
        match = {
            "product_id": "tariff_calculator",
            "name": "GingerControl Tariff Calculator",
            "url": "https://gingercontrol.com/products/tariff-calculator",
            "score": 0,
            "confidence": "fallback",
        }
        rule = _rule_by_product_id(match["product_id"])
    else:
        rule = _rule_by_product_id(match["product_id"])

    updated_article = dict(article)
    updated_article["body"] = insert_cta_before_references(
        body,
        rule.cta.format(url=rule.url),
    )

    metadata = {
        "appended": True,
        "product_id": rule.product_id,
        "name": rule.name,
        "url": rule.url,
        "match_score": match["score"],
        "match_confidence": match["confidence"],
    }
    return updated_article, metadata


def match_product_for_article(
    article: dict[str, Any],
    *,
    keyword: str = "",
) -> dict[str, Any]:
    """Choose the best GingerControl product page for an article."""

    field_values = {
        "title": str(article.get("title") or ""),
        "keyword": keyword,
        "description": str(article.get("description") or ""),
        "tags": " ".join(str(tag) for tag in article.get("tags") or []),
        "body": str(article.get("body") or ""),
    }
    field_weights = {
        "title": 5,
        "keyword": 4,
        "tags": 4,
        "description": 3,
        "body": 1,
    }

    best_rule = PRODUCT_LINK_RULES[0]
    best_score = -1
    for rule in PRODUCT_LINK_RULES:
        score = 0
        for field_name, value in field_values.items():
            matches = sum(1 for term in rule.keywords if _contains_term(value, term))
            score += matches * field_weights[field_name]

        if score > best_score or (
            score == best_score and rule.priority > best_rule.priority
        ):
            best_rule = rule
            best_score = score

    return {
        "product_id": best_rule.product_id,
        "name": best_rule.name,
        "url": best_rule.url,
        "score": max(best_score, 0),
        "confidence": "rule" if best_score > 0 else "fallback",
    }


def find_tail_product_url(body: str, *, tail_chars: int = 4000) -> str | None:
    """Return the last normalized GingerControl product URL in the body tail."""

    tail = body[-tail_chars:]
    urls: list[str] = []
    for raw_url in PRODUCT_URL_PATH_RE.findall(tail):
        normalized = normalize_product_url(raw_url)
        if normalized:
            urls.append(normalized)
    for raw_path in PRODUCT_HREF_PATH_RE.findall(tail):
        normalized = normalize_product_url(raw_path)
        if normalized:
            urls.append(normalized)
    return urls[-1] if urls else None


def insert_cta_before_references(body: str, cta: str) -> str:
    """Insert CTA before a References section, falling back to the end."""

    references_match = re.search(r"(?im)^##\s+References\s*$", body)
    if not references_match:
        return f"{body.rstrip()}\n\n{cta}"

    before = body[: references_match.start()].rstrip()
    after = body[references_match.start() :].lstrip()
    return f"{before}\n\n{cta}\n\n{after}"


def normalize_product_url(raw_url: str) -> str | None:
    """Normalize GingerControl product URLs across locale and tracking variants."""

    value = (raw_url or "").strip().strip(".,;:!?)'\"<>]")
    if value.startswith("/"):
        value = f"https://gingercontrol.com{value}"

    parsed = urlparse(value)
    host = (parsed.netloc or "").lower().removeprefix("www.")
    if host != "gingercontrol.com":
        return None

    path = re.sub(
        r"^/(zh-cn|zh-tw)(?=/)",
        "",
        parsed.path.rstrip("/"),
        flags=re.IGNORECASE,
    )
    if not path.startswith("/products/"):
        return None

    return urlunparse(("https", host, path, "", "", ""))


def _contains_term(value: str, term: str) -> bool:
    if not value:
        return False

    pattern = r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, value.lower()) is not None


def _rule_by_product_id(product_id: str) -> ProductLinkRule:
    for rule in PRODUCT_LINK_RULES:
        if rule.product_id == product_id:
            return rule
    raise ValueError(f"Unknown product CTA rule: {product_id}")
