> 🌐 其他语言: [English](README.md) · [日本語](README.ja.md)
>
> # 知识库 — 自构建 MCP 服务

一个**会自动构建**的个人技术知识库：容器每天从 GitHub Trending、AI 新闻 RSS（含
Anthropic HTML 抓取）、arXiv 采集，用 LLM 提炼成结构化 wiki 页面，由 MCP 服务对外
提供语义检索 + 交互式知识图谱可视化。

> 灵感来自 [mufans/knowledge-base](https://github.com/mufans/knowledge-base)
> 与 [Karpathy LLM Wiki 方法](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)。

## 工作原理

```
A1 主机（单容器 knowledge-mcp）— 完全本地，每日流程不经过 GitHub
  ├─ collect 线程（UTC 16:00）：scripts/collect.py → /data/kb-self/raw/inbox/
  ├─ distill 线程（UTC 16:45）：scripts/distill.py → /data/kb-self/wiki/
  │     （LLM key 仅存在于容器环境变量，永不经过 GitHub）
  ├─ 提供 /mcp 端点（Streamable HTTP，可选 Bearer 认证）读取本地 wiki
  └─ 提供 /graph 端点（浏览器交互式知识图谱可视化）
```

> **安全说明**：采集与提炼全部在你的 A1 机器上完成。GitHub 只托管源码并
> 构建 Docker 镜像——它既看不到采集数据，也看不到 LLM API key。

## 仓库结构

```
.github/workflows/
  build.yml           # 构建 arm64 镜像 → ghcr.io/zhengr/knowledge-mcp
Dockerfile
docker-compose.yml
knowledge-graph.html  # 交互式知识图谱（通过 /graph 端点提供）
scripts/
  collect.py          # 免费采集器（GitHub + AI 新闻 RSS + Anthropic HTML + arXiv）
  distill.py          # LLM → wiki 页面（OpenAI 兼容接口）
server.py             # MCP 服务（search_kb / get_entity / list_recent）+ /graph 路由
pyproject.toml
```

> `raw/inbox/` 和 `wiki/` 在运行时由容器本地生成，**不存储在 GitHub 仓库中**。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | `/kb` | 知识库根目录（含 `wiki/`、`raw/inbox/`） |
| `KB_TRANSPORT` | `http` | `http` / `sse` / `stdio` |
| `KB_HOST` | `0.0.0.0` | 监听地址 |
| `KB_PORT` | `8000` | 监听端口 |
| `MCP_AUTH_TOKEN` | _(空)_ | 设置后 `/mcp` 要求 `Authorization: Bearer ***` |
| `LLM_API_BASE` | `https://api.openai.com/v1` | 提炼用 LLM 端点 |
| `LLM_API_KEY` | _(空)_ | LLM API key（为空则跳过提炼线程） |
| `LLM_MODEL` | `gpt-4o-mini` | LLM 模型名 |

## 部署（单容器）

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

容器**单进程内运行三件事**：
1. **collect 线程** — 每天 UTC 16:00，写入 `raw/inbox/`
2. **distill 线程** — 每天 UTC 16:45，调 LLM 生成 `wiki/`
3. **MCP server** — 端口 8000 提供 `/mcp`（检索）+ `/graph`（可视化）

## 端点

| 路径 | 认证 | 说明 |
|---|---|---|
| `/mcp` | Bearer token | MCP streamable-http 端点（search_kb / get_entity / list_recent） |
| `/graph` | 无 | 交互式知识图谱（浏览器力导向图） |

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

## 查看知识图谱

在浏览器中打开 `http://<host>:8000/graph`。图谱通过浏览器从 `/mcp` 实时拉取 wiki
数据（fetch），功能包括：
- **力导向布局** — 节点按标签共现自动排列
- **点击节点** — 右侧滑出详情面板（标题、评分、标签、摘要）
- **搜索高亮** — 输入关键词实时高亮匹配节点
- **缩放平移** — 滚轮缩放，拖拽空白处平移
- **筛选** — 只看项目（entities）或新闻/论文（sources）
- **标签云** — 点击标签高亮所有关联节点

## 工具

- `search_kb(query, category?, limit?)` — wiki 全文检索
- `get_entity(name)` — 获取单个 wiki 页面
- `list_recent(limit?, days?, min_score?)` — 最近更新的页面
