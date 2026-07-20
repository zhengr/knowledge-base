> 🌐 Other languages: [中文](README.zh.md) · [日本語](README.ja.md)
>
> # Knowledge Base — Self-Building MCP Server

A personal technical knowledge base that **builds itself**: a GitHub Actions
pipeline collects from GitHub Trending, AI news RSS (incl. Anthropic via HTML
scraping), and arXiv daily, distills the content into structured wiki pages with
an LLM, and an MCP server (deployable via Docker / Portainer) serves semantic
search over it.

> Inspired by [mufans/knowledge-base](https://github.com/mufans/knowledge-base)
> and the [Karpathy LLM Wiki method](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## How it works

```
GitHub Actions (daily, UTC 16:00) — collect only, no LLM key
  ├─ scripts/collect.py  → raw/inbox/   (GitHub + AI news RSS + arXiv, free)
  └─ commit & push raw/inbox back to this repo
        ↓  (A1 host pulls the repo)
MCP container (knowledge-mcp) on A1
  ├─ background thread (UTC 16:30): re-pulls latest repo → /data/kb-self
  ├─ background thread (UTC 16:45): scripts/distill.py → wiki/
  │     (LLM key lives ONLY in the container env, never touches GitHub)
  └─ serves /mcp  (Streamable HTTP, optional Bearer auth) over the local wiki
```

> **Security note:** the LLM API key is injected as a container environment
> variable on the A1 host. GitHub only ever sees the free, key-less collection
> output — distillation happens entirely on your machine.

## Repository layout

```
.github/workflows/
  build.yml      # build arm64 image → ghcr.io/zhengr/knowledge-mcp
  knowledge.yml  # daily collect only (distill runs locally on A1)
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
| `LLM_API_BASE` | `https://api.openai.com/v1` |
| `LLM_API_KEY` | `sk-...` |
| `LLM_MODEL` | `gpt-4o-mini` |

## Tools

- `search_kb(query, category?, limit?)` — full-text search over the wiki
- `get_entity(name)` — fetch one wiki page
- `list_recent(limit?, days?, min_score?)` — recently updated pages
