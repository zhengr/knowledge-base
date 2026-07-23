"""Knowledge Base MCP Server — provides search_kb, get_entity, list_recent tools."""

import json
import os
import re
import subprocess
import threading
import time
import io
import shutil
import tarfile
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from mcp.server.fastmcp import FastMCP

KB_PATH = os.environ.get(
    "KNOWLEDGE_BASE_PATH",
    "/Users/liujun/Nutstore Files/我的坚果云/knowledge",
)
WIKI_DIR = Path(KB_PATH) / "wiki"
CATEGORIES = ["concepts", "entities", "sources", "syntheses"]

mcp = FastMCP("knowledge-base")

# 允许公网/远程访问：关闭 DNS rebinding 防护并放行所有 Host。
# 默认 allowed_hosts 仅含 localhost/127.0.0.1，会导致跨机访问返回 421。
try:
    from mcp.server.transport_security import TransportSecuritySettings

    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=["*"],
        allowed_origins=["*"],
    )
except Exception:
    ts = mcp.settings.transport_security
    if ts is not None:
        ts.enable_dns_rebinding_protection = False
        ts.allowed_hosts = ["*"]
        ts.allowed_origins = ["*"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_md_files(category: str | None = None) -> list[Path]:
    """Return all .md files under wiki/ (excluding index.md)."""
    dirs = [WIKI_DIR / c for c in (["category"] if category else CATEGORIES) if (WIKI_DIR / (c or category)).is_dir()]
    if category:
        d = WIKI_DIR / category
        dirs = [d] if d.is_dir() else []
    files: list[Path] = []
    for d in dirs:
        for f in sorted(d.rglob("*.md")):
            if f.stem != "index":
                files.append(f)
    return files


def _parse_frontmatter(text: str) -> dict:
    """Extract metadata from the blockquote header of a wiki page."""
    meta: dict = {}
    # tags: #tag1 #tag2
    m = re.search(r">\s*tags:\s*(.+)", text)
    if m:
        meta["tags"] = re.findall(r"#(\S+)", m.group(1))
    # source: [...](url)
    m = re.search(r">\s*source:\s*\[(.+?)\]\((.+?)\)", text)
    if m:
        meta["source"] = m.group(1)
        meta["source_url"] = m.group(2)
    # score: 综合 X.X/10
    m = re.search(r"综合\s+([\d.]+)/10", text)
    if m:
        meta["score"] = float(m.group(1))
    return meta


def _parse_sections(text: str, max_chars: int = 500) -> list[dict]:
    """Split markdown into sections by ## headings, truncate content."""
    sections = []
    # Skip the first H1 title line(s)
    lines = text.split("\n")
    current_heading = "概述"
    current_lines: list[str] = []
    started = False
    for line in lines:
        if re.match(r"^# ", line) and not started:
            started = True
            continue
        hm = re.match(r"^## (.+)", line)
        if hm:
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append({"heading": current_heading, "content": content[:max_chars]})
            current_heading = hm.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({"heading": current_heading, "content": content[:max_chars]})
    return sections


def _parse_related(text: str, current_file: Path) -> list[dict]:
    """Extract [name](path.md) links as related entries."""
    related = []
    seen = set()
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+\.md)\)", text):
        name, path = m.group(1), m.group(2)
        if path.startswith("http"):
            continue
        # Resolve relative path
        resolved = (current_file.parent / path).resolve()
        if resolved.stem == "index":
            continue
        if name not in seen:
            seen.add(name)
            # Compute relative wiki path
            try:
                rel = resolved.relative_to(WIKI_DIR)
            except ValueError:
                continue
            related.append({"name": name, "path": str(rel)})
    return related


def _get_summary(text: str) -> str:
    """Extract a brief summary: first non-empty, non-metadata paragraph."""
    lines = text.split("\n")
    paragraph: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">") or stripped.startswith("#") or stripped == "---":
            continue
        if stripped:
            paragraph.append(stripped)
        elif paragraph:
            break
    result = " ".join(paragraph)[:200]
    return result


def _file_mtime(path: Path) -> str:
    mt = path.stat().st_mtime
    return datetime.fromtimestamp(mt).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def search_kb(query: str, category: str | None = None, limit: int = 10) -> list[dict]:
    """Full-text search the knowledge base wiki using ripgrep.

    Args:
        query: Search keywords
        category: Optional filter — concepts, entities, sources, or syntheses
        limit: Max results (default 10)
    """
    if category:
        d = WIKI_DIR / category
        search_dirs = [d] if d.is_dir() else []
    else:
        search_dirs = [WIKI_DIR / c for c in CATEGORIES if (WIKI_DIR / c).is_dir()]

    if not search_dirs:
        return []

    # Build rg command
    cmd = [
        "rg", "--no-heading", "-n", "-l", "-i",
        "--glob", "!index.md",
        "-e", query,
    ] + [str(d) for d in search_dirs]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    matched_files = result.stdout.strip().split("\n") if result.stdout.strip() else []
    results: list[dict] = []

    for fpath_str in matched_files[:limit]:
        fpath = Path(fpath_str)
        text = fpath.read_text(encoding="utf-8", errors="ignore")
        meta = _parse_frontmatter(text)

        # Get highlights: lines containing the query
        highlights = []
        for line in text.split("\n"):
            if re.search(re.escape(query), line, re.IGNORECASE):
                stripped = line.strip()
                if stripped.startswith(">") or stripped.startswith("#"):
                    continue
                highlights.append(stripped[:200])
                if len(highlights) >= 3:
                    break

        # Determine category from path
        try:
            rel = fpath.relative_to(WIKI_DIR)
            cat = rel.parts[0] if rel.parts else ""
        except ValueError:
            cat = ""

        results.append({
            "title": fpath.stem,
            "path": str(rel),
            "category": cat,
            "score": meta.get("score"),
            "tags": meta.get("tags", []),
            "summary": _get_summary(text),
            "key_concepts": meta.get("tags", [])[:5],
            "highlights": highlights,
        })

    return results


@mcp.tool()
def get_entity(name: str) -> dict | None:
    """Get details of a single wiki page by name (filename without .md).

    Args:
        name: Page name, e.g. "OpenClaw" or "Self-RAG"
    """
    # Search all wiki subdirs
    for cat_dir in [WIKI_DIR / c for c in CATEGORIES]:
        if not cat_dir.is_dir():
            continue
        for fpath in cat_dir.rglob(f"{name}.md"):
            text = fpath.read_text(encoding="utf-8", errors="ignore")
            meta = _parse_frontmatter(text)
            rel = fpath.relative_to(WIKI_DIR)
            return {
                "title": fpath.stem,
                "path": str(rel),
                "category": rel.parts[0] if rel.parts else "",
                "score": meta.get("score"),
                "tags": meta.get("tags", []),
                "source_url": meta.get("source_url"),
                "sections": _parse_sections(text),
                "related": _parse_related(text, fpath),
            }
    return None


@mcp.tool()
def list_recent(
    category: str | None = None,
    days: int = 7,
    min_score: float = 7.0,
) -> list[dict]:
    """List recently updated wiki pages.

    Args:
        category: Optional filter — concepts, entities, sources, or syntheses
        days: How many days back to look (default 7)
        min_score: Minimum composite score (default 7.0)
    """
    cutoff = datetime.now() - timedelta(days=days)
    results: list[dict] = []

    for fpath in _find_md_files(category):
        mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
        if mtime < cutoff:
            continue
        text = fpath.read_text(encoding="utf-8", errors="ignore")
        meta = _parse_frontmatter(text)
        score = meta.get("score", 0)
        if score < min_score:
            continue

        try:
            rel = fpath.relative_to(WIKI_DIR)
            cat = rel.parts[0] if rel.parts else ""
        except ValueError:
            cat = ""

        results.append({
            "title": fpath.stem,
            "path": str(rel),
            "category": cat,
            "score": score,
            "tags": meta.get("tags", []),
            "summary": _get_summary(text),
            "updated": mtime.strftime("%Y-%m-%d"),
        })

    results.sort(key=lambda x: x["updated"], reverse=True)
    return results


def _collect_loop():
    """后台线程：每天 UTC 16:00 本地采集知识源，写入 KB_PATH/raw/inbox。

    替代原来的 GitHub 拉取（updater）—— collect 完全在 A1 本地完成，
    GitHub 不再参与每日流程。仅当 KB_PATH 可写时生效。
    """
    import datetime as _dt
    import subprocess

    collect_script = "/app/scripts/collect.py"
    if not os.path.exists(collect_script):
        print(f"[collect] 找不到 {collect_script}，跳过", flush=True)
        return

    def do_collect():
        subprocess.run(
            ["python", collect_script],
            cwd=KB_PATH,
            timeout=600,  # 最多 10 分钟
        )
        print(f"[collect] 本地采集完成: {KB_PATH}/raw/inbox", flush=True)

    # 首次立即尝试一次
    try:
        do_collect()
    except Exception as e:
        print(f"[collect] 首次采集失败(下次重试): {e}", flush=True)
    # 之后每天 UTC 16:00
    while True:
        now = _dt.datetime.now(_dt.timezone.utc)
        target = now.replace(hour=16, minute=0, second=0, microsecond=0)
        if target <= now:
            target = target + _dt.timedelta(days=1)
        time.sleep((target - now).total_seconds())
        try:
            do_collect()
        except Exception as e:
            print(f"[collect] 采集失败(下次重试): {e}", flush=True)


def _distill_loop():
    """后台线程：每天 UTC 16:45 基于本地采集的 raw/inbox 提炼 wiki。

    仅在 LLM_API_KEY 存在时生效（mixtao key 通过容器环境变量注入，不进 GitHub）。
    依赖 _collect_loop 先把当日知识源采集到 KB_PATH/raw/inbox。
    """
    import datetime as _dt
    import subprocess

    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        print("[distill] 未设置 LLM_API_KEY，跳过本地提炼", flush=True)
        return

    distill_script = "/app/scripts/distill.py"
    if not os.path.exists(distill_script):
        print(f"[distill] 找不到 {distill_script}，跳过", flush=True)
        return

    def do_distill():
        env = dict(os.environ)
        env["KB_REPO_ROOT"] = KB_PATH  # distill 把 KB_PATH 当作 REPO_ROOT
        # 切到 KB_PATH 目录跑，确保 raw/inbox 与 wiki 相对路径正确
        subprocess.run(
            ["python", distill_script],
            cwd=KB_PATH,
            env=env,
            timeout=1800,  # 最多 30 分钟
        )
        print(f"[distill] 本地提炼完成: {KB_PATH}/wiki", flush=True)

    # 首次立即尝试一次
    try:
        do_distill()
    except Exception as e:
        print(f"[distill] 首次提炼失败(下次重试): {e}", flush=True)
    # 之后每天 UTC 16:45（等 updater 16:30 拉完 repo）
    while True:
        now = _dt.datetime.now(_dt.timezone.utc)
        target = now.replace(hour=16, minute=45, second=0, microsecond=0)
        if target <= now:
            target = target + _dt.timedelta(days=1)
        time.sleep((target - now).total_seconds())
        try:
            do_distill()
        except Exception as e:
            print(f"[distill] 提炼失败(下次重试): {e}", flush=True)


def _run_with_auth(host: str, port: int, auth_token: str):
    """用 uvicorn 跑带 Bearer token 认证的 Streamable HTTP 服务。"""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse
    import uvicorn

    app = mcp.streamable_http_app()

    async def auth_middleware(request, call_next):
        # 健康检查放行
        if request.url.path in ("/healthz", "/health", "/"):
            return await call_next(request)
        # 校验 token：Authorization: Bearer <t> 或 ?token=<t>
        auth = request.headers.get("Authorization", "")
        q_token = request.query_params.get("token", "")
        ok = False
        if auth.startswith("Bearer "):
            ok = auth[len("Bearer "):].strip() == auth_token
        if not ok and q_token:
            ok = q_token == auth_token
        if not ok:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "missing or invalid MCP_AUTH_TOKEN"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)

    app.add_middleware(BaseHTTPMiddleware, dispatch=auth_middleware)

    # CORS 中间件：允许浏览器端直接 fetch MCP 端点（知识图谱可视化等）
    from starlette.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], expose_headers=["mcp-session-id"])

    print(f"[auth] MCP 端点已启用 Bearer token 认证 (port {port})", flush=True)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    # 启动后台本地采集线程（每天 UTC 16:00，写 KB_PATH/raw/inbox）
    try:
        if os.access(os.path.dirname(KB_PATH) or ".", os.W_OK):
            threading.Thread(target=_collect_loop, daemon=True).start()
        else:
            print("[collect] KB_PATH 父目录不可写，跳过本地采集", flush=True)
    except Exception as e:
        print(f"[collect] 启动失败: {e}", flush=True)

    # 启动后台本地提炼线程（若 LLM_API_KEY 存在则每天 UTC 16:45 本地生成 wiki）
    try:
        if os.environ.get("LLM_API_KEY", "").strip():
            threading.Thread(target=_distill_loop, daemon=True).start()
        else:
            print("[distill] 未设置 LLM_API_KEY，跳过本地提炼", flush=True)
    except Exception as e:
        print(f"[distill] 启动失败: {e}", flush=True)

    # transport 通过环境变量 KB_TRANSPORT 选择：
    #   "stdio"   -> 标准 stdio 模式（Claude Code/Cursor 用 command 方式连接）
    #   "sse"     -> SSE 模式（适合同源/本地，公网远程易遇 Origin 校验 421）
    #   "http"    -> Streamable HTTP 模式（推荐公网远程，端点 /mcp，无同源校验）
    transport = os.environ.get("KB_TRANSPORT", "http").lower()
    host = os.environ.get("KB_HOST", "0.0.0.0")
    port = int(os.environ.get("KB_PORT", "8000"))

    if transport == "stdio":
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="stdio")
    elif transport == "sse":
        mcp.settings.host = host
        mcp.settings.port = port
        mcp.run(transport="sse")
    else:
        # Streamable HTTP：支持可选 token 认证
        auth_token = os.environ.get("MCP_AUTH_TOKEN", "").strip()
        if auth_token:
            _run_with_auth(host, port, auth_token)
        else:
            mcp.settings.host = host
            mcp.settings.port = port
            mcp.run(transport="streamable-http")
