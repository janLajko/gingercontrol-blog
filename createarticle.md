# 创建文章 API

## 接口

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

## 请求体

后端请求 schema 为 `ArticleCreate`，继承自 `ArticleBase`。

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
| `keyword` | string 或 null | 否 | `title` | `max_length=200`。如果省略或为空，入库为 `title`。 |
| `run_id` | string 或 null | 否 | `manual-<24位hex>` | `max_length=64`。如果省略或为空，会生成 `manual-` 加 24 位 hex 字符。 |

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

后端 schema 细节：

- `status` 类型是 `Optional[str]`。
- schema 限制为 `max_length=32`。
- 后端没有为文章状态定义 `Literal` 枚举，也没有数据库 check constraint。

当前后端代码路径会设置以下状态值：

| status | 来源 |
|---|---|
| `draft` | `_prepare_blog_post_payload()` 在 `status` 省略、空字符串或 null 时使用的默认值；也是 `ArticleBase` 的默认值。 |
| `completed` | 文章生成流程成功时保存的状态。 |
| `failed` | 文章生成流程失败时保存的状态；也是 SQLAlchemy 模型 `BlogPost.status` 的默认值。 |

因为 `create_article_endpoint` 接收的是字符串且没有强制枚举，调用方传入其他不超过 32 字符的状态字符串也可以被保存。

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

## 错误响应

### 422 Unprocessable Entity

由 FastAPI/Pydantic 校验返回，例如：

- 缺少必填字段：`slug`、`title`、`description`、`body`。
- 字符串长度不符合限制。
- `slug` 规范化后为空。
- 字段 JSON 结构不符合类型要求。

### 500 Internal Server Error

当 `create_blog_post()` 抛出 `RuntimeError` 时，由 `create_article_endpoint` 返回。例如：

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

未捕获的数据库异常会由全局异常处理器返回 `500`：

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
