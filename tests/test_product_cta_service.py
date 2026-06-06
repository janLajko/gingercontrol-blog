"""Tests for generated article product CTA selection."""

from src.service.product_cta_service import append_product_cta, match_product_for_article


def test_export_control_article_matches_export_control_product():
    article = {
        "title": "ECCN 3B991 to China: License Processing Reality in 2026",
        "description": "BIS SNAP-R license requirements for export-control teams.",
        "tags": ["ECCN", "BIS", "export control"],
        "body": "Export license processing under the EAR depends on ECCN exposure.",
    }

    match = match_product_for_article(article, keyword="ECCN license to China")

    assert match["product_id"] == "export_control"
    assert match["url"] == "https://gingercontrol.com/products/export-control"


def test_hts_article_matches_hts_classifier_product():
    article = {
        "title": "HTS Classification Accuracy Benchmarks",
        "description": "How to document GRI analysis and CROSS ruling support.",
        "tags": ["HTS classification"],
        "body": "Classification teams need repeatable reasoning for each HTS code.",
    }

    match = match_product_for_article(article, keyword="HTS classification")

    assert match["product_id"] == "hts_classifier"
    assert match["url"] == "https://gingercontrol.com/products/hts-classifier"


def test_tariff_article_matches_tariff_calculator_product():
    article = {
        "title": "How to Estimate Landed Cost",
        "description": "Calculate import duty, Section 301, and tariff stacking.",
        "tags": ["tariff", "duty"],
        "body": "Importers need to model landed cost before placing orders.",
    }

    match = match_product_for_article(article, keyword="tariff calculator")

    assert match["product_id"] == "tariff_calculator"
    assert match["url"] == "https://gingercontrol.com/products/tariff-calculator"


def test_compliance_article_matches_compliance_radar_product():
    article = {
        "title": "Trade Policy Alert Services Compared",
        "description": "Monitor tariff changes and regulatory updates.",
        "tags": ["policy alert"],
        "body": "Compliance teams need alerts before tariff changes hit margin.",
    }

    match = match_product_for_article(article, keyword="trade policy alerts")

    assert match["product_id"] == "compliance_radar"
    assert match["url"] == "https://gingercontrol.com/products/compliance-radar"


def test_api_article_matches_openapi_product():
    article = {
        "title": "Duty Tax API Pricing Compared",
        "description": "Integrate automated duty and tax checks at 3PL scale.",
        "tags": ["API", "integration"],
        "body": "Platforms need an OpenAPI-compatible compliance workflow.",
    }

    match = match_product_for_article(article, keyword="duty tax API")

    assert match["product_id"] == "openapi"
    assert match["url"] == "https://gingercontrol.com/products/openapi"


def test_origin_planning_article_matches_product_sandbox_product():
    article = {
        "title": "Mexico vs China Import Duty",
        "description": "Simulate nearshoring and country of origin scenarios by SKU.",
        "tags": ["nearshoring", "FTA"],
        "body": "Origin planning teams need to compare sourcing scenarios.",
    }

    match = match_product_for_article(article, keyword="origin planning")

    assert match["product_id"] == "product_sandbox"
    assert match["url"] == "https://gingercontrol.com/products/product-sandbox"


def test_append_product_cta_skips_existing_tail_product_link():
    article = {
        "title": "HTS Classification Guide",
        "description": "Classification workflow.",
        "tags": ["HTS"],
        "body": (
            "Existing body.\n\n"
            "Use [GingerControl HTS Classifier]"
            "(https://gingercontrol.com/products/hts-classifier)."
        ),
    }

    updated_article, metadata = append_product_cta(
        article,
        keyword="HTS classification",
    )

    assert updated_article["body"] == article["body"]
    assert metadata == {
        "appended": False,
        "reason": "tail_product_link_exists",
        "url": "https://gingercontrol.com/products/hts-classifier",
    }


def test_append_product_cta_adds_matched_link():
    article = {
        "title": "ECCN Export License Guide",
        "description": "BIS license workflow.",
        "tags": ["ECCN"],
        "body": "Article body.",
    }

    updated_article, metadata = append_product_cta(article, keyword="ECCN license")

    assert "https://gingercontrol.com/products/export-control" in updated_article["body"]
    assert metadata is not None
    assert metadata["appended"] is True
    assert metadata["product_id"] == "export_control"
