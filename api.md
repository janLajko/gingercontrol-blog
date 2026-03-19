# API 接口文档

## 1. 获取分类列表

**URL**

```http
GET /api/v1/categories
```

**示例**

```http
GET https://gingercontrol-blog-backend-1019079553349.us-west2.run.app/api/v1/categories
```

**说明**

返回所有分类，并附带每个分类下的文章数量。

**请求参数**

无

**成功响应**

`200 OK`

```json
[
  {
    "name": "global tarde",
    "id": 1,
    "article_count": 1,
    "created_at": "2026-03-18T16:31:42.095961",
    "updated_at": "2026-03-18T16:31:42.095969"
  },
  {
    "name": "tariff",
    "id": 2,
    "article_count": 1,
    "created_at": "2026-03-18T16:42:45.667423",
    "updated_at": "2026-03-18T16:42:45.667438"
  }
]
```

**响应字段**

- `id`: 分类 ID
- `name`: 分类名称
- `article_count`: 该分类下的文章数量
- `created_at`: 创建时间，ISO 8601
- `updated_at`: 更新时间，ISO 8601

---

## 2. 按分类筛选文章列表

**URL**

```http
GET /api/v1/articles?category={category}
```

**示例**

```http
GET https://gingercontrol-blog-backend-1019079553349.us-west2.run.app/api/v1/articles?category=tariff
```

**说明**

按文章的 `category` 字段做精确匹配筛选。

**查询参数**

- `category`: 分类名称，字符串，可选。传空时返回全部文章

**成功响应**

`200 OK`

```json
[
  {
    "slug": "section-122-tariff-law-2026-guide",
    "title": "Section 122 Tariff Authority in 2026: What the Law Means for U.S. Trade",
    "description": "Section 122 and tariff policy in 2026: a concise guide to the law, the Federal Register proclamation, and what importers should know.",
    "tags": [
      "trade",
      "tariff",
      "section-122",
      "import-policy",
      "trade-law"
    ],
    "body": "## Table of Contents ...",
    "authorName": "Chen",
    "authorAvatar": null,
    "category": "tariff",
    "coverImage": null,
    "user_id": "cms-user",
    "status": "completed",
    "success": true,
    "sources_used": [
      "https://www.whitehouse.gov/presidential-actions/2026/02/imposing-a-temporary-import-surcharge-to-address-fundamental-international-payments-problems/"
    ],
    "source_details": [],
    "seo_scores": {
      "title_score": 92.8,
      "meta_description_score": 90.1,
      "keyword_optimization_score": 87.5,
      "content_structure_score": 80.85,
      "readability_score": 86.65,
      "content_quality_score": 85.5,
      "technical_seo_score": 78.2,
      "final_score": 90.16
    },
    "final_score": 90.16,
    "model_used": "gpt-5.4-mini",
    "customization": {
      "tone": "professional",
      "target_audience": "general",
      "content_type": "guide",
      "word_count_target": 1500,
      "include_faq": true,
      "include_conclusion": true,
      "include_table_of_contents": true,
      "focus_keywords": [
        "trade",
        "tariff"
      ],
      "exclude_domains": []
    },
    "error_message": null,
    "id": 5,
    "run_id": "d8be3a23-cf37-4e8c-b661-f448448bee43",
    "keyword": "section 122",
    "created_at": "2026-03-19T01:31:22.475870",
    "updated_at": "2026-03-19T01:31:22.475876"
  }
]
```

**响应字段**

- `id`: 文章 ID
- `run_id`: 生成任务 ID
- `keyword`: 生成关键词
- `slug`: 文章 slug
- `title`: 标题
- `description`: 描述
- `tags`: 标签数组
- `body`: Markdown 正文
- `authorName`: 作者名
- `authorAvatar`: 作者头像 URL
- `category`: 分类
- `coverImage`: 封面图 URL
- `user_id`: 用户 ID
- `status`: 状态
- `success`: 是否生成成功
- `sources_used`: 引用来源 URL 数组
- `source_details`: 来源详情数组
- `seo_scores`: SEO 分数详情
- `final_score`: 最终分数
- `model_used`: 使用的模型
- `customization`: 生成参数
- `error_message`: 错误信息
- `created_at`: 创建时间
- `updated_at`: 更新时间

---

## 3. 获取单篇文章详情

**URL**

```http
GET /api/cms/articles/{id}
```

**示例**

```http
GET https://gingercontrol-blog-frontend-1019079553349.us-west2.run.app/api/cms/articles/5
```

**说明**

这是前端服务提供的 CMS 代理接口，会转发到后端文章详情接口并返回单篇文章完整数据。

**路径参数**

- `id`: 文章 ID，整数，必填

**成功响应**

`200 OK`

```json
{
  "slug": "section-122-tariff-law-2026-guide",
  "title": "Section 122 Tariff Authority in 2026: What the Law Means for U.S. Trade",
  "description": "Section 122 and tariff policy in 2026: a concise guide to the law, the Federal Register proclamation, and what importers should know.",
  "tags": [
    "trade",
    "tariff",
    "section-122",
    "import-policy",
    "trade-law"
  ],
  "body": "## Table of Contents ...",
  "authorName": "Chen",
  "authorAvatar": null,
  "category": "tariff",
  "coverImage": null,
  "user_id": "cms-user",
  "status": "completed",
  "success": true,
  "sources_used": [
    "https://www.whitehouse.gov/presidential-actions/2026/02/imposing-a-temporary-import-surcharge-to-address-fundamental-international-payments-problems/"
  ],
  "source_details": [],
  "seo_scores": {
    "title_score": 92.8,
    "meta_description_score": 90.1,
    "keyword_optimization_score": 87.5,
    "content_structure_score": 80.85,
    "readability_score": 86.65,
    "content_quality_score": 85.5,
    "technical_seo_score": 78.2,
    "final_score": 90.16
  },
  "final_score": 90.16,
  "model_used": "gpt-5.4-mini",
  "customization": {
    "tone": "professional",
    "target_audience": "general",
    "content_type": "guide",
    "word_count_target": 1500,
    "include_faq": true,
    "include_conclusion": true,
    "include_table_of_contents": true,
    "focus_keywords": [
      "trade",
      "tariff"
    ],
    "exclude_domains": []
  },
  "error_message": null,
  "id": 5,
  "run_id": "d8be3a23-cf37-4e8c-b661-f448448bee43",
  "keyword": "section 122",
  "created_at": "2026-03-19T01:31:22.475870",
  "updated_at": "2026-03-19T01:31:22.475876"
}
```

**可能状态码**

- `200`: 成功
- `404`: 文章不存在
- `500`: 服务端异常
