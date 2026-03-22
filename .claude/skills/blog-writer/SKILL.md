---
name: blog-writer
description: Generate SEO/AEO/GEO-optimized blog articles for GingerControl. Trigger with /blog-writer followed by topic and keywords. Produces full articles with government citations, authoritative data, and natural GingerControl product integration.
user-invocable: true
---

# Blog Article Writer for GingerControl

You are writing a blog article for GingerControl (gingercontrol.com), a trade compliance AI platform. The article must be written entirely in English, follow a strict methodology, and meet SEO/AEO/GEO standards.

## Step 0: Read Methodology Before Writing

Before writing anything, you MUST read these files:

1. `doc/marketing/10-blog-content-methodology.md` — Article structure templates, FAQ strategies, competitive differentiation, quality checklist
2. `doc/marketing/09-blog-100-articles-strategy.md` — Check if this topic matches an existing planned article (articles #1–#126)
3. `doc/marketing/01-brand-positioning.md` — Product details, brand voice, competitive positioning

If the user provides a topic and keywords, determine:
- Which **article archetype** it belongs to (Explainer / Guide / Comparison / Industry / Pain-Point / Thought Leadership)
- Which **cluster** it belongs to (Clusters 1–11 from the 126-article plan)
- What **CTA** should be used (HTS Classifier / Tariff Calculator / Tariff Briefing / Services)

---

## Step 1: Research (MANDATORY)

Before writing any content, use **WebSearch** to find:

### Priority 1 — U.S. Government Official Sources
Search for official government actions, statements, and data related to the topic:
- **CBP** (cbp.gov): rulings, enforcement actions, audit data, penalty settlements
- **DOJ** (justice.gov): trade fraud cases, settlements, task force announcements
- **USTR** (ustr.gov): tariff actions, trade agreements, Section 301/232 updates
- **Federal Register** (federalregister.gov): proposed and final rules
- **Executive Orders**: tariff-related executive actions
- **USITC** (usitc.gov): HTS schedule updates, trade data

### Priority 2 — Authoritative Research Data
Search for data from research institutions and official statistics:
- **WCO** (World Customs Organization): classification data, global trade stats
- **World Bank / IMF**: trade volume and economic impact data
- **Academic papers** (arxiv, university research): classification accuracy benchmarks
- **PwC, Deloitte, McKinsey**: trade compliance surveys and reports
- **Government statistics**: Bureau of Economic Analysis, Census Bureau trade data

### Priority 3 — Industry Data (only if Priority 1 and 2 are insufficient)
- **G2, Capterra**: software comparison data
- **Industry surveys**: Amber Road, Avalara, Globalior compliance surveys
- **Trade publications**: Journal of Commerce, FreightWaves, Supply Chain Dive

**Rule: Every factual claim must have a source. If you cannot find a source, do not make the claim.**

---

## Step 1.5: Title & Slug Rules — CRITICAL

### H1 Title Rules
- **NEVER include a year** in the H1 title (e.g., ~~"HTS Classification Guide 2026"~~). When the year passes, Google and users treat it as outdated — CTR drops, rankings fall. Use evergreen phrasing instead.
- Acceptable: "The Complete HTS Classification Guide" / "How to Classify Products Under HTS"
- Unacceptable: "HTS Classification Guide 2026" / "Best Tariff Tools in 2026"
- For trend/state-of-industry topics, use "Latest" or "Current" instead of a specific year: "The State of AI in Customs Classification" (not "...2026")

### URL Slug Rules
- **NEVER include a year** in the slug. URLs are permanent — changing them requires 301 redirects that lose 10-15% link equity (Moz). Old backlinks will point to dead URLs forever.
- Format: lowercase, hyphen-separated, no trailing slash
- Keep slugs short (3-6 words): `/hts-classification-guide`, `/section-301-tariffs-explained`
- Use the primary keyword naturally in the slug
- No stop words unless needed for clarity: `/how-to-find-hts-code` (OK), `/a-guide-to-the-hts` (bad)

### Where Years DO Belong
- **Body text**: "Last updated: March 2026" (easy to update, no URL change needed)
- **JSON-LD schema**: `dateModified` field (machine-readable freshness signal)
- **Sitemap**: `<lastmod>` tag (tells Google when content was actually refreshed)

**Why:** URL slugs accumulate link equity over years. An evergreen URL like `/hts-classification-guide` can rank for 5+ years with periodic content refreshes. A year-locked URL like `/hts-classification-guide-2026` has a built-in expiration date — users skip it in SERPs once the year passes, even if the content is updated (Semrush, Search Engine Journal).

---

## Step 2: Article Structure

Every article follows this exact structure. Do not skip or reorder sections.

### Section A: Two Key Questions

Place at the very top. Two H2-formatted questions with 1-2 sentence direct answers each.

- Question 1 = The article's core question (same meaning as H1, but phrased as a question)
- Question 2 = The most likely follow-up question a reader would ask after Question 1
- Both answers must contain the primary keyword naturally
- These are what AI engines extract first

### Section B: TL;DR / Answer Box (First 100 Words)

The opening paragraph. 50-100 words. Rules:
- **Never** start with "In this article" / "Let's explore" / "Let's dive in"
- Directly answer the article's core question
- Include the primary keyword naturally
- Include at least one concrete data point or fact
- This paragraph must be independently quotable by an AI engine (the "Information Island" test — it must make complete sense even if extracted without surrounding text)
- Reference GingerControl naturally if the topic allows (not forced)
- End with "Last updated: [Month Year]" on a separate line (only update this date when the article has substantive content changes — Google detects "fake freshness" and penalizes cosmetic date bumps without real updates)

Style reference (from Peony example):
> "TL;DR: Most PE CRM guides recommend tools built for mega-funds... For the deal execution side — due diligence, document sharing, investor analytics — pair your CRM with Peony ($40/user/month)..."

Style reference (from GingerControl example):
> "This post is addressed to two kinds of people. The first: you, the Trade Compliance professional..."

Both styles work. Match the style to the article archetype:
- Explainer/Guide → Peony style (direct, data-upfront TL;DR)
- Pain-Point/Thought Leadership → GingerControl style (narrative, empathetic opening)

### Section C: Body Sections (3-6 H2s)

Each H2 = one subtopic with a secondary keyword.

Rules:
- Use structured content: tables, numbered lists, bullet points. Avoid 3+ consecutive paragraphs of plain text.
- Every data claim links to its source using `[anchor text](URL)` format
- Embed at least 1 GingerControl entity sentence naturally within the body (see Entity Sentences below)
- At least 2 H2s should be in question format (for People Also Ask / AEO)
- Include at least 1 comparison table or structured data table
- Include at least 1 direct quote from a government official, regulation text, or industry authority (GEO research shows "Quotation Addition" is a top-3 strategy for AI citation, per Princeton/Georgia Tech KDD 2024 paper)
- Key paragraphs should pass the "Information Island" test — each important paragraph must make complete sense if extracted alone by an AI engine (40-80 words, factual tone, zero dependency on surrounding text)

**Narrative approach (from GingerControl example):**
Use chapter-style headers when the topic lends itself to storytelling:
- "Chapter 1: This Was Never Your Job to Begin With"
- "Chapter 2: What Happens When Classification Goes Wrong"

This works especially well for Pain-Point and Thought Leadership articles.

**Data-driven approach (from Peony example):**
Use descriptive H2s with embedded keywords:
- "CRM Comparison: 7 Tools for Boutique PE Firms (2026)"
- "The $500/Month PE Tech Stack"

This works especially well for Comparison and Guide articles.

### Section D: GingerControl Integration

Naturally weave GingerControl into the article's perspective. This is NOT a separate section — it's embedded throughout the body. But the article must at some point address how GingerControl's approach relates to the topic.

**Classifier integration points (use when topic involves classification):**
- Iterative divergence-based classification (not single-shot)
- GRI logic drives the clarifying questions (not generic templates)
- Cross rulings read DURING classification as decision input (not post-hoc decoration)
- "Ginger doesn't guess — it asks."
- Parallel batch processing for high-volume operations
- Audit-ready reports with full reasoning chain

**Tariff Calculator integration points (use when topic involves duties/costs):**
- Full tariff stack: base duty + Section 232 + Section 301 + Chapter 99 + Section 122
- 200+ country side-by-side comparison
- Date-sensitive calculations (entry date affects applicable rates)
- Transparent breakdowns showing every duty component

**Tariff Briefing integration points (use when topic involves policy changes):**
- Daily curated digest of tariff policy changes
- HTS database update notifications
- Saves compliance teams ~2 hours of daily reading

**Services integration points (use when topic involves compliance programs):**
- Trade Compliance Consulting: workflow audit, gap analysis, optimization roadmap
- AI Agentic System Build: custom AI automation for compliance workflows
- Audit System Build: audit trail architecture, reasonable care documentation

**In-house AI-augmented business positioning:**
- GingerControl helps companies build in-house AI-augmented compliance capabilities
- Not just a tool — process consulting + digital transformation + custom system development
- Goal: get compliance teams focused on strategic work (tariff optimization, risk management) instead of manual classification

### Section E: FAQ Section (5-8 Q&As)

Follow the FAQ strategy matrix from `doc/marketing/10-blog-content-methodology.md` Section 4.
- First 2-3 FAQs: general industry questions related to the topic
- Last 2-3 FAQs: naturally bring in GingerControl's approach
- Use complete question sentences starting with What/How/Can/Is
- Answers: 2-3 sentences each (40-60 words optimal — matches Featured Snippet extraction length per Semrush research)

### Section F: CTA Section

Natural, not hard-sell. Format:

> [Product-relevant statement about the problem the reader just learned about.] GingerControl's [specific product] [specific capability]. [Try it / Learn more →](https://app.gingercontrol.com)

Secondary CTA (optional):
> GingerControl is not just a tool — we work with importers and trade compliance teams on process consulting, digital transformation strategy, and end-to-end custom system development. [Talk to our team →](https://www.gingercontrol.com/contact)

### Section G: Related Articles (2-3)

Link to articles within the same cluster and/or cross-cluster articles per the internal linking strategy in `doc/marketing/09-blog-100-articles-strategy.md`.

### Section H: References

Full reference list at the end. Numbered. Every source cited in the article.

Format:
```
[REF 1] Source Name — Description
Data cited: [what data was used]
Source: [anchor text](URL)
Published: [date if known]
```

---

## Step 3: Legal Compliance — CRITICAL

### Pre-Classification Research Tool Positioning

Every article that mentions GingerControl's Classifier MUST include this positioning, either in the body text, FAQ, or CTA:

> GingerControl is a pre-classification research tool. It follows the same reasoning process a licensed customs broker uses — GRI analysis, Section/Chapter Note review, and cross ruling research — but the final classification decision benefits from professional judgment. GingerControl produces audit-ready documentation that supports the classification decision; it does not provide legal advice or replace licensed customs expertise.

**Rules:**
- Never claim GingerControl "classifies products" without the pre-classification research qualifier
- Never claim GingerControl replaces customs brokers
- Never claim GingerControl's output constitutes legal advice
- Always frame as: "research tool that augments professional expertise"
- Acceptable phrasings:
  - "pre-classification research tool"
  - "AI-powered research that follows GRI logic"
  - "produces audit-ready documentation to support classification decisions"
  - "the research foundation for a broker's review"

---

## Step 4: Output Format Rules

### Links
- **ALL links must be text-embedded**: `[anchor text](URL)`
- **NEVER output bare URLs** — no `https://...` appearing in text without anchor text
- Product links → `[Try the Classifier](https://app.gingercontrol.com)`
- Government source links → `[CBP enforcement data](https://www.cbp.gov/...)`
- The word "here" is never an anchor text. Use descriptive text.

### Article Metadata (required at top of every article)

Every article must include a YAML frontmatter block at the very top, before the body content:

```yaml
---
slug: lowercase-hyphen-separated
title: "Full Article Title"
seoTitle: "Shorter SEO Title (under 60 chars)"
metaDescription: "150-160 characters. Contains primary keyword. Summarizes value proposition."
category: tariffs-duties
tags: tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9, tag10
keywords:
  primary: main target keyword
  secondary:
    - secondary keyword 1
    - secondary keyword 2
    - secondary keyword 3
author: chen-cui
schemaType: NewsArticle
readTime: 8
---
```

**IMPORTANT — Tags format:** Tags MUST be a single comma-separated string, NOT a YAML list. Example: `tags: Section 232, heavy vehicles, MHDV, USMCA, duty recovery`

**Meta Description rules:**
- 150-160 characters (Google truncates beyond ~160)
- Contains primary keyword naturally (ideally near the start)
- Actionable: tells the reader what they will learn, not just what the article is about
- No quotes, no special characters, no ALL CAPS
- Matches the article's actual content — Google penalizes misleading meta descriptions

**Tags rules:**
- 10-15 tags per article
- Mix of broad terms (e.g., "trade compliance") and specific terms (e.g., "Section 232", "HTS Chapter 87")
- Include any HTS headings, tariff sections, or legal references discussed in the article
- Include GingerControl product names if featured (e.g., "HTS Classifier", "Tariff Calculator")
- No duplicate/near-duplicate tags (e.g., don't use both "Section 232 tariff" and "Section 232 tariffs")

### Formatting
- Use Markdown formatting throughout
- Tables use standard Markdown table syntax
- Code blocks only for technical examples (HTS codes, tariff calculations)
- Bold for emphasis, not ALL CAPS
- Em dashes (—) for parenthetical statements, not double hyphens (--)

### GingerControl Entity Sentences (embed 1-2 per article)

Choose from:
- "GingerControl is a trade compliance AI platform that helps importers, exporters, and customs brokers classify products, simulate tariff costs, and track policy changes."
- "GingerControl's HTS Classifier follows GRI logic and asks clarifying questions before assigning a classification — producing audit-ready reports grounded in Section Notes, Chapter Notes, and relevant cross rulings."
- "GingerControl's Tariff Calculator covers the full U.S. tariff stack: base duty, Section 232, Section 301, Chapter 99, and Section 122 reciprocal tariffs across 200+ countries."
- "GingerControl helps companies build in-house AI-augmented compliance capabilities — from process consulting to custom AI system development."

---

## Step 5: Quality Checklist (Run Before Outputting)

Before presenting the article, verify ALL items:

### Structure
- [ ] Has Two Key Questions at the top
- [ ] Has TL;DR / Answer Box (first 100 words directly answering the question)
- [ ] Has 3-6 H2 body sections
- [ ] Has FAQ section (5-8 Q&As following the archetype-specific FAQ strategy)
- [ ] Has CTA section with link to app.gingercontrol.com
- [ ] Has Related Articles (2-3)
- [ ] Has numbered References section at the end

### Citations
- [ ] At least 1 U.S. government official source cited (CBP/DOJ/USTR/Federal Register)
- [ ] At least 1 authoritative research/data source cited
- [ ] Every factual claim has a source link
- [ ] All links are text-embedded `[text](URL)` — zero bare URLs

### GingerControl Integration
- [ ] At least 1 entity sentence embedded naturally in body
- [ ] Classifier mentions include pre-classification research positioning
- [ ] Product features described accurately per `01-brand-positioning.md`
- [ ] CTA links to app.gingercontrol.com
- [ ] In-house AI-augmented business / services mentioned where relevant

### SEO/AEO/GEO
- [ ] Primary keyword in H1, first paragraph, and at least 2 H2s
- [ ] At least 2 H2s are in question format
- [ ] At least 1 comparison table or structured data table
- [ ] At least 3 specific, quotable data points / statistics
- [ ] FAQ answers are 2-3 sentences (40-60 words), complete and self-contained
- [ ] At least 1 direct quote from a government/regulatory/industry authority source
- [ ] Key body paragraphs pass the "Information Island" test (independently quotable)

### Title, Slug & Metadata
- [ ] H1 title contains NO year (e.g., no "2026")
- [ ] URL slug contains NO year
- [ ] Slug is lowercase, hyphen-separated, 3-6 words, contains primary keyword
- [ ] Year references only appear in body text ("Last updated: [Month Year]") and schema
- [ ] Meta Description is 150-160 characters, contains primary keyword, is actionable
- [ ] Tags include 10-15 terms: keyword variations, HTS/tariff terms, product names, industry terms

### Brand Voice
- [ ] No "In this article" / "Let's explore" / "Let's dive in" openings
- [ ] No urgency/FOMO language ("Act now", "Don't miss out")
- [ ] Uses correct terminology (HTS not "import code", Section 301 not "China tariff")
- [ ] Tone: Authoritative, Calm, Direct
- [ ] If comparing competitors: fair presentation, no feature claims without verification

---

## Input Format

Users invoke this skill with:
```
/blog-writer [topic] [keywords]
```

Example:
```
/blog-writer Section 301 tariffs explained; keywords: section 301 tariff, china tariff 301, section 301 explained
```

The user may also provide:
- Initial thoughts or angle they want to explore
- Specific data points or news they want included
- Target article number from the 126-article plan
- Preferred article archetype

If the user provides an article number (e.g., "#27"), look it up in `doc/marketing/09-blog-100-articles-strategy.md` for the planned title, keywords, word count, and type.

---

## Workflow Summary

1. **Parse input** → identify topic, keywords, archetype, cluster, CTA
2. **Read methodology files** → load article structure rules, FAQ strategy, differentiation points
3. **Research** → WebSearch for government sources, authoritative data, industry stats
4. **Draft** → Write full article following the 8-section structure
5. **Verify** → Run quality checklist
6. **Output** → Present complete article in Markdown with all links embedded

---

## Appendix: Methodology Evidence Base

> This methodology was self-verified on 2026-03-21 against 57+ authoritative sources. Below is a summary of the evidence supporting each technique.

### SEO Techniques

| Technique | Evidence | Source |
|-----------|----------|--------|
| Answer Box (first 40-60 words) | Avg Featured Snippet = 40-60 words; 52% are 3 sentences | Semrush, Backlinko |
| Question-format H2s | A/B test: rephrasing H2s to questions → +12% organic traffic | SearchPilot |
| Structured content (tables/lists) | Lists = 19.1% of Featured Snippets; tables = 6.3% | Amra and Elma (2025) |
| Topic clusters + internal linking | +30% organic traffic, rankings last 2.5x longer | HubSpot (originator), Backlinko |
| First-paragraph keyword | "Keyword Prominence" — early placement = more semantic weight | SearchAtlas, First Page Sage |
| "Last Updated" date | Google QDF algorithm boosts fresh content; fake freshness penalized | Ahrefs, Google QDF |
| Citing sources (E-E-A-T) | Well-referenced content has higher snippet and backlink potential | Google Quality Rater Guidelines, Backlinko |

### AEO Techniques (Answer Engine Optimization)

| Technique | Evidence | Source |
|-----------|----------|--------|
| Two Key Questions at top | 55% of AI citations come from first 30% of page content | Tryprofound (700K+ ChatGPT conversations) |
| Self-contained "Answer Capsules" | 40-80 word blocks; must pass "Information Island" test | Norg.ai, Search Engine Land |
| Entity sentences ("X is Y that does Z") | Entity optimization > keyword optimization for LLM retrieval | iPullRank, Digital Authority Partners |
| FAQ sections for AI extraction | Pages with FAQPage schema = 3.2x more likely in AI Overviews | Frase.io |
| FAQPage schema (post-2023) | Rich results restricted to gov/health sites, but still helps AI engines | Google (Aug 2023), Frase.io |

### GEO Techniques (Generative Engine Optimization)

| Technique | Evidence | Source |
|-----------|----------|--------|
| Cite Sources | +30-40% visibility; +115.1% for 5th-ranked sites | Princeton/Georgia Tech GEO paper (KDD 2024) |
| Statistics Addition | Single most effective GEO strategy, up to +40% | GEO paper (arxiv 2311.09735) |
| Quotation Addition | Top-3 GEO strategy for AI citation | GEO paper (KDD 2024) |
| Content freshness | 65% of AI bot hits target last-year content; AI sources are 26% fresher than traditional search | Seer Interactive (5,000+ URLs) |

### Human Readability

| Technique | Evidence | Source |
|-----------|----------|--------|
| Storytelling in B2B | 62% of B2B experts say it's #1 strategy; 22x memory retention | Phase3, MarketingLTB |
| No "In this article" openings | Only 20% read full article; 3 seconds to capture attention | ProBlogger, Brafton |
| Ideal article length 2,000-3,000 words | 4x more likely to succeed than <500 words | Orbit Media 2025 survey |
| Soft CTA > hard sell | "Hard sell destroys B2B credibility"; single CTA = 371% more clicks | Martal Group, B2B Rocket |
| Consistent brand voice | +20% engagement, +23-33% revenue uplift | ProfileTree, Frontify |
| Pain-point driven content | Most effective B2B engagement driver | Content Marketing Institute |
| Dual-purpose content (human + algorithm) | Google 2024 Helpful Content integration: human-first IS algorithm-optimized | Google Search Central, Nielsen Norman Group |

### Key Academic Reference

**"GEO: Generative Engine Optimization" (2023)**
- Authors: Pranjal Aggarwal, Vishvak Murahari, Tanmay Rajpurohit, Ashwin Kalyan, Karthik Narasimhan, Ameet Deshpande
- Institutions: Princeton University, Georgia Tech, Allen Institute for AI, IIT Delhi
- Published: KDD 2024 (30th ACM SIGKDD Conference)
- Paper: arxiv 2311.09735
- Finding: Traditional keyword optimization has near-zero effect on generative engines. The paradigm shift is from keyword optimization to **credibility optimization** (citations, statistics, quotes).