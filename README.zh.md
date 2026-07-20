> 🌐 其他语言: [English](README.md) · [日本語](README.ja.md)
>
> # 知识库 — 自构建 MCP 服务

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

## 仓库结构

```
.github/workflows/
  build.yml      # 构建 arm64 镜像 → ghcr.io/zhengr/knowledge-mcp
  knowledge.yml  # 每日 collect + distill + push
Dockerfile
docker-compose.yml
scripts/
  collect.py     # 免费采集器（GitHub + arXiv）
  distill.py     # LLM → wiki 页面（OpenAI 兼容接口）
  update_wiki.py # 独立更新器（容器内使用）
server.py        # MCP 服务（search_kb / get_entity / list_recent）
pyproject.toml
raw/inbox/       # 采集原始内容（自动生成）
wiki/            # 提炼知识（自动生成）
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | `/kb` | 知识库根目录（含 `wiki/`） |
| `KB_TRANSPORT` | `http` | `http` / `sse` / `stdio` |
| `KB_HOST` | `0.0.0.0` | 监听地址 |
| `KB_PORT` | `8000` | 监听端口 |
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

## 工具

- `search_kb(query, category?, limit?)` — wiki 全文检索
- `get_entity(name)` — 获取单个 wiki 页面
- `list_recent(limit?, days?, min_score?)` — 最近更新的页面
