# Knowledge Base — Self-Building MCP Server

A personal technical knowledge base that **builds itself**: a GitHub Actions
pipeline collects from GitHub Trending + arXiv daily, distills the content into
structured wiki pages with an LLM, and an MCP server (deployable via Docker /
Portainer) serves semantic search over it.

> Inspired by [mufans/knowledge-base](https://github.com/mufans/knowledge-base)
> and the [Karpathy LLM Wiki method](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## How it works

```
GitHub Actions (daily, UTC 16:00)
  ├─ scripts/collect.py  → raw/inbox/   (GitHub Trending + arXiv RSS, free)
  ├─ scripts/distill.py  → wiki/         (LLM distills into entities/sources)
  └─ commit & push back to this repo
        ↓  (A1 host pulls the repo)
MCP container (knowledge-mcp)
  ├─ serves /mcp  (Streamable HTTP, optional Bearer auth)
  └─ background thread re-pulls latest wiki daily at UTC 16:30
```

## Repository layout

```
.github/workflows/
  build.yml      # build arm64 image → ghcr.io/zhengr/knowledge-mcp
  knowledge.yml  # daily collect + distill + push
Dockerfile
docker-compose.yml
scripts/
  collect.py     # free collectors (GitHub + arXiv)
  distill.py     # LLM → wiki pages (OpenAI-compatible API)
  update_wiki.py # standalone updater (used inside the container)
server.py        # MCP server (search_kb / get_entity / list_recent)
pyproject.toml
raw/inbox/       # collected raw content (auto-generated)
wiki/            # distilled knowledge (auto-generated)
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | `/kb` | Knowledge base root (contains `wiki/`) |
| `KB_TRANSPORT` | `http` | `http` / `sse` / `stdio` |
| `KB_HOST` | `0.0.0.0` | Bind address |
| `KB_PORT` | `8000` | Listen port |
| `MCP_AUTH_TOKEN` | _(empty)_ | If set, requires `Authorization: Bearer <token>` |
| `KB_UPDATE_URL` | repo tarball | Override the auto-update source URL |

## Deploy (single container)

```bash
docker run -d --name knowledge-mcp -p 8000:8000 \
  -e KNOWLEDGE_BASE_PATH=/data/kb-self \
  -e MCP_AUTH_TOKEN=your-secret-token \
  -v /opt:/data:rw \
  ghcr.io/zhengr/knowledge-mcp:latest
```

The container both **serves** the MCP endpoint and **auto-updates** the wiki
in-place (writes to the mounted `/data/kb-self`).

## Connect a client (Claude Code / Cursor)

```json
{
  "mcpServers": {
    "knowledge": {
      "url": "http://<host>:8000/mcp",
      "headers": { "Authorization": "Bearer your-secret-token" }
    }
  }
}
```

## Configure the LLM (for distillation)

Set these as **repository secrets** (Settings → Secrets → Actions):

| Secret | Example |
|---|---|
| `LLM_API_BASE` | `http://158.101.23.34:8080/tingly/openai` |
| `LLM_API_KEY` | `your-key` |
| `LLM_MODEL` | `mixtao` |

## Tools

- `search_kb(query, category?, limit?)` — full-text search over the wiki
- `get_entity(name)` — fetch one wiki page
- `list_recent(limit?, days?, min_score?)` — recently updated pages

---

# 知识库 — 自构建 MCP 服务

一个**会自动构建**的个人技术知识库：GitHub Actions 每天从 GitHub Trending 和
arXiv 采集，用 LLM 提炼成结构化 wiki 页面，再由可 Docker/Portainer 部署的
MCP 服务对外提供语义检索。

> 灵感来自 [mufans/knowledge-base](https://github.com/mufans/knowledge-base)
> 与 [Karpathy LLM Wiki 方法](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。

## 工作原理

```
GitHub Actions（每日 UTC 16:00）
  ├─ scripts/collect.py  → raw/inbox/   （GitHub Trending + arXiv RSS，免费）
  ├─ scripts/distill.py  → wiki/         （LLM 提炼为 entities/sources）
  └─ 自动提交并 push 回本仓库
        ↓  （A1 主机拉取仓库）
MCP 容器（knowledge-mcp）
  ├─ 提供 /mcp 端点（Streamable HTTP，可选 Bearer 认证）
  └─ 后台线程每日 UTC 16:30 重新拉取最新 wiki
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | `/kb` | 知识库根目录（含 `wiki/`） |
| `KB_TRANSPORT` | `http` | `http` / `sse` / `stdio` |
| `MCP_AUTH_TOKEN` | _(空)_ | 设置后要求 `Authorization: Bearer <token>` |
| `KB_UPDATE_URL` | 仓库 tarball | 覆盖自动更新源地址 |

## 部署（单容器）

```bash
docker run -d --name knowledge-mcp -p 8000:8000 \
  -e KNOWLEDGE_BASE_PATH=/data/kb-self \
  -e MCP_AUTH_TOKEN=your-secret-token \
  -v /opt:/data:rw \
  ghcr.io/zhengr/knowledge-mcp:latest
```

容器同时**提供 MCP 端点**并在原地**自动更新** wiki（写入挂载的 `/data/kb-self`）。

## 客户端连接（Claude Code / Cursor）

```json
{
  "mcpServers": {
    "knowledge": {
      "url": "http://<host>:8000/mcp",
      "headers": { "Authorization": "Bearer your-secret-token" }
    }
  }
}
```

## 配置 LLM（用于提炼）

在仓库 **Settings → Secrets → Actions** 中设置：
`LLM_API_BASE`、`LLM_API_KEY`、`LLM_MODEL`。

---

# 知識ベース — 自動構築型 MCP サーバー

自分で**知識を構築する**個人技術ナレッジベースです。GitHub Actions が毎日
GitHub Trending と arXiv から収集し、LLM で構造化された wiki ページに抽出、
Docker / Portainer でデプロイ可能な MCP サーバーが意味検索を提供します。

> [mufans/knowledge-base](https://github.com/mufans/knowledge-base) および
> [Karpathy LLM Wiki 手法](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
> に着想を得ています。

## 仕組み

```
GitHub Actions（毎日 UTC 16:00）
  ├─ scripts/collect.py  → raw/inbox/   （GitHub Trending + arXiv RSS、無料）
  ├─ scripts/distill.py  → wiki/         （LLM が entities/sources へ抽出）
  └─ このリポジトリへ自動コミット＆プッシュ
        ↓  （A1 ホストがリポジトリを取得）
MCP コンテナ（knowledge-mcp）
  ├─ /mcp エンドポイント提供（Streamable HTTP、Bearer 認証は任意）
  └─ バックグラウンドスレッドが毎日 UTC 16:30 に最新 wiki を再取得
```

## 環境変数

| 変数 | デフォルト | 説明 |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | `/kb` | ナレッジベースのルート（ `wiki/` を含む） |
| `KB_TRANSPORT` | `http` | `http` / `sse` / `stdio` |
| `MCP_AUTH_TOKEN` | _(空)_ | 設定すると `Authorization: Bearer <token>` を要求 |
| `KB_UPDATE_URL` | リポジトリ tarball | 自動更新元 URL の上書き |

## デプロイ（単一コンテナ）

```bash
docker run -d --name knowledge-mcp -p 8000:8000 \
  -e KNOWLEDGE_BASE_PATH=/data/kb-self \
  -e MCP_AUTH_TOKEN=your-secret-token \
  -v /opt:/data:rw \
  ghcr.io/zhengr/knowledge-mcp:latest
```

コンテナは MCP エンドポイントを**提供**すると同時に、wiki をその場で
**自動更新**します（マウント先 `/data/kb-self` へ書き込み）。

## クライアント接続（Claude Code / Cursor）

```json
{
  "mcpServers": {
    "knowledge": {
      "url": "http://<host>:8000/mcp",
      "headers": { "Authorization": "Bearer your-secret-token" }
    }
  }
}
```

## LLM の設定（抽出用）

リポジトリの **Settings → Secrets → Actions** で以下を設定：
`LLM_API_BASE`、`LLM_API_KEY`、`LLM_MODEL`。
