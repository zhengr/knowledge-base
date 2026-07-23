# 知识库 MCP Server 镜像（自构建知识库 + 可选认证）
# 基于 mufans/knowledge-base 的 MCP server，扩展为：
#   - 支持 http(sse)/stdio 多 transport
#   - 内置后台线程，每天 UTC 16:30 自动拉取最新自构建知识库
#   - 可选 Bearer token 认证（MCP_AUTH_TOKEN）
FROM python:3.12-slim

# 安装 ripgrep：search_kb 用 rg 做全文搜索，不装则搜索静默返回空
RUN apt-get update \
    && apt-get install -y --no-install-recommends ripgrep \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 仅依赖官方 mcp 包（含 starlette/uvicorn）
COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir mcp

COPY server.py /app/server.py
COPY scripts/ /app/scripts/
COPY knowledge-graph.html /app/knowledge-graph.html

# 知识库内容通过 volume 挂载（镜像不含 wiki 数据）
ENV KNOWLEDGE_BASE_PATH=/kb
# 默认 Streamable HTTP 模式，监听 8000
ENV KB_TRANSPORT=http
ENV KB_HOST=0.0.0.0
ENV KB_PORT=8000
# 可选：设置后启用 Bearer token 认证；留空则不认证
# ENV MCP_AUTH_TOKEN=your-secret-token

EXPOSE 8000

CMD ["python", "server.py"]
