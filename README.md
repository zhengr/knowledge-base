# knowledge-base MCP Server — Docker 部署包

为 [mufans/knowledge-base](https://github.com/mufans/knowledge-base) 的 MCP Server
补的 Docker 部署包，支持 **GitHub Actions 构建并推送到 ghcr.io**，Portainer 直接 pull 部署。

## 特点
- `server.py` 支持三种 transport（环境变量 `KB_TRANSPORT` 切换）：
  - `http`（默认）：Streamable HTTP，端点 `/mcp`，最适合公网远程连接
  - `sse`：SSE 模式（同源/本地用，公网远程易遇 Origin 校验 421）
  - `stdio`：标准 stdio（Claude Code/Cursor 用 command 方式本地连）
- 镜像不含 wiki 数据，知识库通过 volume 挂载到 `/kb`
- `search_kb` 依赖 `ripgrep`（已在镜像内安装）

## 文件
```
Dockerfile              # python:3.12-slim + ripgrep + mcp，暴露 8000
docker-compose.yml      # Portainer 部署参考
.github/workflows/build.yml  # push 到 main 时自动 build arm64 镜像推 ghcr.io
pyproject.toml
server.py               # 来自 mufans/knowledge-base/mcp_server/server.py（加 http/sse/stdio 入口）
README.md
```

## 部署（Portainer）
1. 在目标机器上准备好知识库本体：`git clone https://github.com/mufans/knowledge-base /opt/knowledge-base`
2. Portainer → Containers → **Add container**（或 Stacks）：
   - Image: `ghcr.io/zhengr/knowledge-mcp:latest`
   - Port mapping: `8000:8000`
   - Volume: 主机 `/opt/knowledge-base` → 容器 `/kb:ro`
   - Env: `KNOWLEDGE_BASE_PATH=/kb`、`KB_TRANSPORT=http`

## 远程 MCP 客户端配置（Streamable HTTP，默认）
Claude Code / Cursor 用 `url` 方式连接（端点 `/mcp`）：
```json
{
  "mcpServers": {
    "knowledge": {
      "url": "http://<服务器IP>:8000/mcp"
    }
  }
}
```
> SSE 模式（`KB_TRANSPORT=sse`）在公网远程连接时易遇 Origin 校验 421，故默认改 `streamable-http`。

## 环境变量
| 变量 | 默认 | 说明 |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | `/kb` | 知识库根目录（含 wiki/） |
| `KB_TRANSPORT` | `http` | `http` / `sse` / `stdio` |
| `KB_HOST` | `0.0.0.0` | 监听地址 |
| `KB_PORT` | `8000` | 监听端口 |
