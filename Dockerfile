# 知识库 MCP Server 镜像（SSE / stdio 双模式）
# 原仓库 mufans/knowledge-base 没有 Dockerfile，这里补一套。
# server 默认以 SSE(Streamable HTTP) 模式运行，便于在 Portainer 常驻并暴露端口，
# 远程 MCP 客户端（Claude Code / Cursor / OpenCode）用 url 方式连接。
FROM python:3.12-slim

# 安装 ripgrep：search_kb 用 rg 做全文搜索，不装则搜索静默返回空
RUN apt-get update \
    && apt-get install -y --no-install-recommends ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 仅依赖官方 mcp 包
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir mcp

COPY server.py /app/server.py

# 知识库内容通过 volume 挂载到 /kb（镜像不含 wiki 数据）
ENV KNOWLEDGE_BASE_PATH=/kb
# 默认 SSE 模式，监听 8000
ENV KB_TRANSPORT=sse
ENV KB_HOST=0.0.0.0
ENV KB_PORT=8000

EXPOSE 8000

# SSE 模式：前台常驻 HTTP 服务
CMD ["python", "server.py"]
