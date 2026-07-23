> 🌐 Other languages: [中文](README.zh.md) · [日本語](README.ja.md)
>
> # Knowledge Base — Self-Building MCP Server

A personal technical knowledge base that **builds itself**: a container on
your host collects from GitHub Trending, AI news RSS (incl. Anthropic via HTML
scraping), and arXiv daily, distills the content into structured wiki pages
with an LLM, and an MCP server serves semantic search + an interactive
knowledge graph over it.

> Inspired by [mufans/knowledge-base](https://github.com/mufans/knowledge-base)
> and the [Karpathy LLM Wiki method](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

## How it works

```
A1 host (single container: knowledge-mcp) — fully local, no GitHub in daily loop
  ├─ collect thread (UTC 16:00): scripts/collect.py → /data/kb-self/raw/inbox/
  ├─ distill thread (UTC 16:45): scripts/distill.py → /data/kb-self/wiki/
  │     (LLM key lives ONLY in the container env, never touches GitHub)
  ├─ serves /mcp  (Streamable HTTP, optional Bearer auth) over the local wiki
  └─ serves /graph  (interactive knowledge graph visualization in browser)
```

> **Security note:** collection and distillation both run entirely on your A1
> machine. GitHub only hosts the source code and builds the Docker image —
> it never sees collected data or the LLM API key.

## Repository layout

```
.github/workflows/
  build.yml           # build arm64 image → ghcr.io/zhengr/knowledge-mcp
Dockerfile
docker-compose.yml
knowledge-graph.html  # interactive knowledge graph (served at /graph)
scripts/
  collect.py          # free collectors (GitHub + AI news RSS + Anthropic HTML + arXiv)
  distill.py          # LLM → wiki pages (OpenAI-compatible API)
server.py             # MCP server (search_kb / get_entity / list_recent) + /graph route
pyproject.toml
```

> `raw/inbox/` and `wiki/` are generated locally on the host at runtime —
> they are NOT stored in the GitHub repo.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | `/kb` | Knowledge base root (contains `wiki/`, `raw/inbox/`) |
| `KB_TRANSPORT` | `http` | `http` / `sse` / `stdio` |
| `KB_HOST` | `0.0.0.0` | Bind address |
| `KB_PORT` | `8000` | Listen port |
| `MCP_AUTH_TOKEN` | _(empty)_ | If set, requires `Authorization: Bearer ***` on `/mcp` |
| `LLM_API_BASE` | `https://api.openai.com/v1` | LLM endpoint for distillation |
| `LLM_API_KEY` | _(empty)_ | LLM API key (if empty, distill thread skips) |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model name |

## Deploy (single container)

```bash
docker run -d --name knowledge-mcp -p 8000:8000 \
  -e KNOWLEDGE_BASE_PATH=/data/kb-self \
  -e MCP_AUTH_TOKEN=your-secret-token \
  -e LLM_API_BASE=https://api.openai.com/v1 \
  -e LLM_API_KEY=sk-... \
  -e LLM_MODEL=gpt-4o-mini \
  -v /opt:/data:rw \
  ghcr.io/zhengr/knowledge-mcp:latest
```

The container runs **three things in one process**:
1. **collect thread** — daily UTC 16:00, writes `raw/inbox/`
2. **distill thread** — daily UTC 16:45, calls LLM → generates `wiki/`
3. **MCP server** — serves `/mcp` (search) + `/graph` (visualization) on port 8000

## Endpoints

| Path | Auth | Description |
|---|---|---|
| `/mcp` | Bearer token | MCP streamable-http endpoint (search_kb, get_entity, list_recent) |
| `/graph` | None | Interactive knowledge graph (force-directed graph in browser) |

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

## View the knowledge graph

Open `http://<host>:8000/graph` in any browser. The graph pulls wiki data
from `/mcp` in real-time (via browser fetch). Features:
- **Force-directed layout** — nodes auto-arrange by tag co-occurrence
- **Click a node** — slide-out detail panel (title, score, tags, summary)
- **Search** — highlight matching nodes/labels in real-time
- **Zoom & pan** — scroll to zoom, drag background to pan
- **Filter** — show only entities (projects) or sources (news/papers)
- **Tag cloud** — click a tag to highlight all connected nodes

## Tools

- `search_kb(query, category?, limit?)` — full-text search over the wiki
- `get_entity(name)` — fetch one wiki page
- `list_recent(limit?, days?, min_score?)` — recently updated pages
