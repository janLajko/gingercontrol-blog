# 文章 CMS API 文档

本文档覆盖后端真实文章接口：

| 方法 | 路径 | 函数 | 说明 |
|---|---|---|---|
| `GET` | `/api/v1/articles` | `get_articles` | 查询文章列表，支持筛选和分页。 |
| `GET` | `/api/v1/articles/{article_id}` | `get_article` | 查询单篇文章详情。 |
| `POST` | `/api/v1/articles` | `create_article_endpoint` | 创建文章。 |
| `PUT` | `/api/v1/articles/{article_id}` | `update_article_endpoint` | 更新文章。 |
| `DELETE` | `/api/v1/articles/{article_id}` | `delete_article_endpoint` | 删除文章。 |

## 创建文章

创建一条新的文章记录。

```http
POST /api/v1/articles
Content-Type: application/json
```

处理函数：

- `agent_system/src/api/routes/blog.py`
- 函数：`create_article_endpoint(payload: ArticleCreate)`

后端处理流程：

1. FastAPI 使用 `ArticleCreate` 校验请求 JSON。
2. 接口调用 `create_blog_post(payload.model_dump())`。
3. `create_blog_post()` 通过 `_prepare_blog_post_payload()` 规范化字段和默认值。
4. 向 `blog_posts` 表插入一条记录。
5. 返回创建后的记录，响应模型为 `ArticleResponse`。

成功状态码：`201 Created`

## 创建/更新请求体

创建文章请求 schema 为 `ArticleCreate`，继承自 `ArticleBase`。

更新文章请求 schema 为 `ArticleUpdate`，继承自 `ArticleBase`。

重要区别：

- `POST /api/v1/articles` 支持额外传入 `keyword` 和 `run_id`。
- `PUT /api/v1/articles/{article_id}` 的 schema 不包含 `keyword` 和 `run_id`；更新时后端会保留原记录中的 `keyword` 和 `run_id`。
- `PUT` 是全量更新，不是 PATCH。`slug`、`title`、`description`、`body` 仍然是必填字段。

`ArticleBase` 配置了 `populate_by_name=True`，因此带 alias 的字段既可以使用接口字段名，也可以使用 Python 字段名：

- `authorName` 或 `author_name`
- `authorAvatar` 或 `author_avatar`
- `coverImage` 或 `cover_image`

| 字段 | 类型 | 必填 | 默认值 | 校验 / 说明 |
|---|---|---:|---|---|
| `slug` | string | 是 | - | `min_length=1`，`max_length=255`。会规范化为小写 slug：非 `a-z0-9-` 字符会转为 `-`；连续 `-` 会合并；首尾 `-` 会移除。规范化后为空会校验失败。 |
| `title` | string | 是 | - | `min_length=1`，`max_length=255`。 |
| `description` | string | 是 | - | `min_length=1`。 |
| `tags` | string[] 或 string | 否 | `[]` | 如果传 string，会按英文逗号分割并 trim。 |
| `body` | string | 是 | - | `min_length=1`。 |
| `authorName` | string 或 null | 否 | `null` | `author_name` 的 alias。`max_length=120`。空字符串入库前会规范化为 `null`。 |
| `authorAvatar` | string 或 null | 否 | `null` | `author_avatar` 的 alias。`max_length=500`。空字符串入库前会规范化为 `null`。 |
| `category` | string 或 null | 否 | `null` | schema 中 `max_length=255`；数据库列为 `String(120)`。空字符串入库前会规范化为 `null`。 |
| `language` | string 或 null | 否 | `en` | `max_length=16`。空字符串或 null 入库时会使用 `en`。用于区分英文、中文、日语等文章语言。 |
| `coverImage` | string 或 null | 否 | `null` | `cover_image` 的 alias。`max_length=500`。空字符串入库前会规范化为 `null`。 |
| `user_id` | string 或 null | 否 | `null` | `max_length=100`。空字符串入库前会规范化为 `null`。 |
| `status` | string 或 null | 否 | `draft` | `max_length=32`。空字符串或 null 入库时会使用 `draft`。后端没有用 `Literal` 强制枚举。 |
| `success` | boolean 或 null | 否 | `true` | 如果为 null，入库为 `true`。 |
| `sources_used` | string[] | 否 | `[]` | JSON 字段。 |
| `source_details` | object[] | 否 | `[]` | JSON 字段。 |
| `seo_scores` | object | 否 | `{}` | JSON 字段。 |
| `final_score` | number 或 null | 否 | `0.0` | 如果为 null，入库为 `0.0`。 |
| `model_used` | string 或 null | 否 | `null` | `max_length=120`。空字符串入库前会规范化为 `null`。 |
| `customization` | object | 否 | `{}` | JSON 字段。 |
| `type` | string 或 null | 否 | `article` | `max_length=32`。如果省略，入库为 `article`。 |
| `error_message` | string 或 null | 否 | `null` | 空字符串入库前会规范化为 `null`。 |
| `keyword` | string 或 null | 创建时可传 | `title` | 仅 `ArticleCreate` 支持。`max_length=200`。如果省略或为空，入库为 `title`。 |
| `run_id` | string 或 null | 创建时可传 | `manual-<24位hex>` | 仅 `ArticleCreate` 支持。`max_length=64`。如果省略或为空，会生成 `manual-` 加 24 位 hex 字符。 |

## Category 可选值

后端在 `blog_posts.category` 中保存的是分类名称，不是分类 ID。

当前 `categories` 表中的分类值：

| id | name |
|---:|---|
| 2 | `Tariffs & Duties` |
| 3 | `HTS Classification` |
| 5 | `CBP & Customs` |
| 6 | `Trade Compliance` |
| 7 | `Trade Basics` |
| 8 | `Global Trade` |
| 10 | `Regulatory Updates` |
| 11 | `AI & Technology` |

后端重要细节：

- `create_article_endpoint` 不校验 `category` 是否存在于 `categories` 表。
- `category` 会作为普通字符串保存到 `blog_posts.category`。

## Language 可选值

后端在 `blog_posts.language` 中保存语言代码。默认值为英文 `en`。

推荐使用以下值：

| language | 说明 |
|---|---|
| `en` | 英文 blog |
| `zh` | 中文 blog |
| `ja` | 日语 blog |

后端重要细节：

- `language` 是字符串字段，schema 限制为 `max_length=16`。
- 后端会 trim 并转小写。
- `language` 省略、空字符串或 null 时会保存为 `en`。
- 当前后端不强制枚举，调用方可以传其他不超过 16 字符的语言代码。
- 列表查询接口支持用 `language` 精确过滤：`GET /api/v1/articles?language=zh`。

## Status 可选值

`create_article_endpoint` 是 CMS 文章创建接口。按当前 CMS 编辑器代码，文章状态使用以下业务值：

| status | 说明 |
|---|---|
| `draft` | 草稿。`status` 省略、空字符串或 null 时，后端会默认保存为 `draft`。 |
| `pending_review` | 待审核。CMS 编辑器下拉框可选。 |
| `published` | 已发布。CMS 编辑器下拉框可选；点击发布时也会保存为该状态。 |

后端实现细节：

- `status` 类型是 `Optional[str]`。
- schema 限制为 `max_length=32`。
- 后端没有为文章状态定义 `Literal` 枚举，也没有数据库 check constraint。
- 因此调用方技术上可以传其他不超过 32 字符的状态字符串，但 CMS 创建/编辑文章建议只使用 `draft`、`pending_review`、`published`。

其他代码路径中的状态：

| status | 来源 |
|---|---|
| `completed` | 文章生成接口 `/api/v1/generate-blog` 成功持久化时使用，不是 CMS 创建文章的常规状态。 |
| `failed` | 文章生成失败时使用；SQLAlchemy 模型默认值也是 `failed`。CMS 编辑器读取到 `failed` 时会归一化显示为 `pending_review`。 |

## 请求示例

```json
{
  "slug": "section-122-tariffs-explained",
  "title": "Section 122 Tariffs Explained",
  "description": "A practical guide for US importers.",
  "tags": ["tariffs", "trade compliance"],
  "body": "<h1>Section 122 Tariffs Explained</h1><p>...</p>",
  "authorName": "chen-cui",
  "authorAvatar": "https://example.com/avatar.png",
  "category": "Regulatory Updates",
  "language": "en",
  "coverImage": "https://example.com/cover.png",
  "user_id": "cms-user",
  "status": "draft",
  "success": true,
  "sources_used": [],
  "source_details": [],
  "seo_scores": {},
  "final_score": 0,
  "model_used": "gpt-5-mini",
  "customization": {},
  "type": "article",
  "error_message": null,
  "keyword": "section 122 tariffs"
}
```

## 响应体

响应模型：`ArticleResponse`

`ArticleResponse` 包含所有可编辑文章字段，以及后端生成的元数据。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | 数据库主键。 |
| `run_id` | string 或 null | 请求传入的值，或自动生成的 `manual-<24位hex>`。 |
| `keyword` | string 或 null | 请求传入的值，或 fallback 到 `title`。 |
| `slug` | string | 规范化后的 slug。 |
| `title` | string | 文章标题。 |
| `description` | string | 文章描述。 |
| `tags` | string[] | 规范化后的标签。 |
| `body` | string | 文章正文。 |
| `authorName` | string 或 null | 使用 alias 返回。 |
| `authorAvatar` | string 或 null | 使用 alias 返回。 |
| `category` | string 或 null | 分类名称。 |
| `language` | string 或 null | 文章语言代码；默认 `en`。 |
| `coverImage` | string 或 null | 使用 alias 返回。 |
| `user_id` | string 或 null | 用户标识。 |
| `status` | string 或 null | 已保存的状态值。 |
| `success` | boolean 或 null | 已保存的 success 标记。 |
| `sources_used` | string[] | 来源列表。 |
| `source_details` | object[] | 来源详情列表。 |
| `seo_scores` | object | SEO 分数对象。 |
| `final_score` | number 或 null | 最终分数。 |
| `model_used` | string 或 null | 模型名称。 |
| `customization` | object | 自定义配置。 |
| `type` | string 或 null | 内容类型。 |
| `error_message` | string 或 null | 错误信息。 |
| `created_at` | string | 创建时间。 |
| `updated_at` | string | 更新时间。 |

响应示例：

```json
{
  "slug": "section-122-tariffs-explained",
  "title": "Section 122 Tariffs Explained",
  "description": "A practical guide for US importers.",
  "tags": ["tariffs", "trade compliance"],
  "body": "<h1>Section 122 Tariffs Explained</h1><p>...</p>",
  "authorName": "chen-cui",
  "authorAvatar": "https://example.com/avatar.png",
  "category": "Regulatory Updates",
  "language": "en",
  "coverImage": "https://example.com/cover.png",
  "user_id": "cms-user",
  "status": "draft",
  "success": true,
  "sources_used": [],
  "source_details": [],
  "seo_scores": {},
  "final_score": 0.0,
  "model_used": "gpt-5-mini",
  "customization": {},
  "type": "article",
  "error_message": null,
  "keyword": "section 122 tariffs",
  "run_id": "manual-1234567890abcdef12345678",
  "id": 123,
  "created_at": "2026-06-09T12:00:00",
  "updated_at": "2026-06-09T12:00:00"
}
```

## 查询文章列表

查询文章列表，支持筛选。未传分页参数时返回完整 `ArticleResponse[]`；传入 `page` 或 `page_limit` 时返回分页摘要结构 `PaginatedArticleListResponse`。

```http
GET /api/v1/articles
```

处理函数：

- `agent_system/src/api/routes/blog.py`
- 函数：`get_articles(...)`

### Query 参数

| 参数 | 类型 | 必填 | 默认值 | 校验 / 说明 |
|---|---|---:|---|---|
| `category` | string | 否 | `null` | 精确匹配 `blog_posts.category`。 |
| `status` | string | 否 | `null` | 精确匹配 `blog_posts.status`。建议值见上方 Status 可选值。 |
| `type` | string | 否 | `article` | 精确匹配 `blog_posts.type`。当前 CMS 主要使用 `article` 和 `news`。 |
| `title` | string | 否 | `null` | 对文章标题做模糊搜索，SQL 使用 `ilike("%title%")`。 |
| `language` | string | 否 | `null` | 精确匹配 `blog_posts.language`，后端会 trim 并转小写。 |
| `page` | integer | 否 | `null` | `ge=1`。传入 `page` 或 `page_limit` 后启用分页模式。 |
| `page_limit` | integer | 否 | `null` | `ge=1`，`le=100`。分页大小；分页模式下未传则默认使用 `20`。 |

后端处理逻辑：

- 当 `page` 和 `page_limit` 都省略时，调用 `list_blog_posts(...)`，返回完整文章数组 `ArticleResponse[]`。
- 当 `page` 或 `page_limit` 任一存在时，调用 `list_blog_post_summaries(...)`，返回分页摘要。
- 排序方式：`created_at desc, id desc`。
- 如果数据库未配置，列表接口返回空列表或空分页结构。

### 非分页请求示例

```http
GET /api/v1/articles?type=article&language=zh&status=published
```

非分页响应模型：`List[ArticleResponse]`

```json
[
  {
    "id": 123,
    "run_id": "manual-1234567890abcdef12345678",
    "keyword": "section 122 tariffs",
    "slug": "section-122-tariffs-explained",
    "title": "Section 122 Tariffs Explained",
    "description": "A practical guide for US importers.",
    "tags": ["tariffs", "trade compliance"],
    "body": "<h1>Section 122 Tariffs Explained</h1><p>...</p>",
    "authorName": "chen-cui",
    "authorAvatar": "https://example.com/avatar.png",
    "category": "Regulatory Updates",
    "language": "en",
    "coverImage": "https://example.com/cover.png",
    "user_id": "cms-user",
    "status": "published",
    "success": true,
    "sources_used": [],
    "source_details": [],
    "seo_scores": {},
    "final_score": 0.0,
    "model_used": null,
    "customization": {},
    "type": "article",
    "error_message": null,
    "created_at": "2026-06-09T12:00:00",
    "updated_at": "2026-06-09T12:00:00"
  }
]
```

### 分页请求示例

```http
GET /api/v1/articles?page=1&page_limit=20&type=article&title=tariff&language=en
```

分页响应模型：`PaginatedArticleListResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `page` | integer | 当前页码。 |
| `page_limit` | integer | 每页条数。 |
| `total_count` | integer | 符合条件的总条数。 |
| `total_pages` | integer | 总页数。 |
| `articles` | object[] | 文章摘要列表。 |

分页文章摘要字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | integer | 数据库主键。 |
| `slug` | string | 文章 slug。 |
| `title` | string | 标题。 |
| `description` | string | 描述。 |
| `tags` | string[] | 标签。 |
| `created_at` | string | 创建时间。 |
| `final_score` | number 或 null | 最终分数。 |
| `cover_image` | string 或 null | 封面图 URL。 |
| `author_name` | string 或 null | 作者名。 |
| `author_avatar` | string 或 null | 作者头像 URL。 |
| `category` | string 或 null | 分类名称。 |
| `language` | string 或 null | 语言代码，默认 `en`。 |
| `type` | string 或 null | 内容类型。 |

```json
{
  "page": 1,
  "page_limit": 20,
  "total_count": 1,
  "total_pages": 1,
  "articles": [
    {
      "id": 123,
      "slug": "section-122-tariffs-explained",
      "title": "Section 122 Tariffs Explained",
      "description": "A practical guide for US importers.",
      "tags": ["tariffs", "trade compliance"],
      "created_at": "2026-06-09T12:00:00",
      "final_score": 0.0,
      "cover_image": "https://example.com/cover.png",
      "author_name": "chen-cui",
      "author_avatar": "https://example.com/avatar.png",
      "category": "Regulatory Updates",
      "language": "en",
      "type": "article"
    }
  ]
}
```

## 查询单篇文章

根据文章 ID 查询一篇文章详情。

```http
GET /api/v1/articles/{article_id}
```

处理函数：

- `agent_system/src/api/routes/blog.py`
- 函数：`get_article(article_id: int)`

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `article_id` | integer | 是 | `blog_posts.id`。 |

成功状态码：`200 OK`

响应模型：`ArticleResponse`

请求示例：

```http
GET /api/v1/articles/123
```

响应示例同创建文章的 `ArticleResponse`。

错误：

- `404 Not Found`：文章不存在，`error_message` 为 `Article not found`。

## 更新文章

更新已有文章记录。

```http
PUT /api/v1/articles/{article_id}
Content-Type: application/json
```

处理函数：

- `agent_system/src/api/routes/blog.py`
- 函数：`update_article_endpoint(article_id: int, payload: ArticleUpdate)`

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `article_id` | integer | 是 | 要更新的 `blog_posts.id`。 |

请求体：

- 使用 `ArticleUpdate`。
- 字段与上方“创建/更新请求体”中的 `ArticleBase` 一致。
- `keyword` 和 `run_id` 不属于 `ArticleUpdate`；更新时后端保留原记录中的值。
- 这是全量更新。`slug`、`title`、`description`、`body` 必填。

后端处理逻辑：

1. 查询 `article_id` 对应的 `BlogPost`。
2. 不存在则返回 `404`。
3. 存在则调用 `_prepare_blog_post_payload(payload, existing=blog_post)` 规范化字段。
4. 将规范化后的字段写回原记录。
5. 返回更新后的 `ArticleResponse`。

成功状态码：`200 OK`

请求示例：

```json
{
  "slug": "section-122-tariffs-explained",
  "title": "Section 122 Tariffs Explained",
  "description": "Updated description.",
  "tags": ["tariffs", "trade compliance"],
  "body": "<h1>Section 122 Tariffs Explained</h1><p>Updated body.</p>",
  "authorName": "chen-cui",
  "authorAvatar": "https://example.com/avatar.png",
  "category": "Regulatory Updates",
  "language": "en",
  "coverImage": "https://example.com/cover.png",
  "user_id": "cms-user",
  "status": "pending_review",
  "success": true,
  "sources_used": [],
  "source_details": [],
  "seo_scores": {},
  "final_score": 0,
  "model_used": null,
  "customization": {},
  "type": "article",
  "error_message": null
}
```

响应模型：`ArticleResponse`

错误：

- `404 Not Found`：文章不存在，`error_message` 为 `Article not found`。
- `422 Unprocessable Entity`：请求体不符合 `ArticleUpdate`。
- `500 Internal Server Error`：数据库未配置或更新失败。

## 删除文章

根据文章 ID 删除文章记录。

```http
DELETE /api/v1/articles/{article_id}
```

处理函数：

- `agent_system/src/api/routes/blog.py`
- 函数：`delete_article_endpoint(article_id: int)`

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `article_id` | integer | 是 | 要删除的 `blog_posts.id`。 |

后端处理逻辑：

1. 查询 `article_id` 对应的 `BlogPost`。
2. 不存在则返回 `404`。
3. 存在则删除并提交事务。
4. 返回删除成功结果。

成功状态码：`200 OK`

响应示例：

```json
{
  "success": true,
  "id": 123
}
```

错误：

- `404 Not Found`：文章不存在，`error_message` 为 `Article not found`。
- `500 Internal Server Error`：数据库未配置或删除失败。

## 错误响应

文章接口中的 `HTTPException` 会经过全局异常处理器包装为 `ErrorDetail`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `error_code` | string | 例如 `HTTP_404`、`HTTP_500`。 |
| `error_message` | string | 错误消息，例如 `Article not found`。 |
| `details` | object | 包含请求 path、method、status_code 等信息。 |
| `timestamp` | string | 错误时间。 |
| `run_id` | string 或 null | 关联 run id；文章接口通常为 null。 |

### 422 Unprocessable Entity

由 FastAPI/Pydantic 校验返回，例如：

- 缺少必填字段：`slug`、`title`、`description`、`body`。
- 字符串长度不符合限制。
- `slug` 规范化后为空。
- 字段 JSON 结构不符合类型要求。

### 500 Internal Server Error

当 `create_blog_post()`、`update_blog_post()` 或 `delete_blog_post()` 抛出 `RuntimeError` 时，对应接口会返回 `500`。例如：

```json
{
  "error_code": "HTTP_500",
  "error_message": "DATABASE_URL is not configured.",
  "details": {
    "path": "/api/v1/articles",
    "method": "POST",
    "status_code": 500
  },
  "timestamp": "2026-06-09T12:00:00",
  "run_id": null
}
```

未捕获的数据库异常也会由全局异常处理器返回 `500`：

```json
{
  "error_code": "INTERNAL_SERVER_ERROR",
  "error_message": "An unexpected error occurred",
  "details": {
    "path": "/api/v1/articles",
    "method": "POST",
    "error_type": "ExceptionType"
  },
  "timestamp": "2026-06-09T12:00:00",
  "run_id": null
}
```
