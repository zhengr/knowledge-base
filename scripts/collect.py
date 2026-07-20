#!/usr/bin/env python3
"""collect.py — 知识库采集脚本（0 token 成本）

数据源（全部免费，无需付费 LLM）：
  - GitHub Search API: 每日热门 AI/Agent/移动端/开发工具项目（按 star 排序）
  - HuggingFace Daily Papers: 当日 arXiv 精选论文（RSS）

输出：raw/inbox/YYYY-MM-DD-GitHub项目.md, YYYY-MM-DD-AI论文.md
"""
import os
import sys
import json
import urllib.request
import urllib.parse
import datetime
import xml.etree.ElementTree as ET

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(REPO_ROOT, "raw", "inbox")
TODAY = datetime.date.today().strftime("%Y-%m-%d")


def _get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "kb-collector/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def collect_github():
    """GitHub Search API：按 star 排序的热门项目（语言过滤）。"""
    queries = [
        ("AI/Agent", "llm OR rag OR mcp OR agent in:name,description stars:>1000"),
        ("移动端", "topic:mobile stars:>300"),
        ("开发工具", "topic:developer-tools stars:>300"),
    ]
    items = []
    for label, q in queries:
        try:
            params = urllib.parse.urlencode({
                "q": q, "sort": "stars", "order": "desc", "per_page": "8",
            })
            url = f"https://api.github.com/search/repositories?{params}"
            data = json.loads(_get(url))
            for it in data.get("items", []):
                items.append({
                    "name": it["full_name"],
                    "stars": it["stargazers_count"],
                    "lang": it.get("language") or "—",
                    "desc": (it.get("description") or "").replace("\n", " "),
                    "url": it["html_url"],
                })
        except Exception as e:
            print(f"[github:{label}] 跳过: {e}", file=sys.stderr)
    # 去重 + 按 star 排序
    seen = {}
    for it in items:
        seen[it["name"]] = it
    ranked = sorted(seen.values(), key=lambda x: x["stars"], reverse=True)[:15]
    lines = [f"# GitHub 项目精选 · {TODAY}", ""]
    lines.append("> 数据来源：GitHub Search API（按 star 排序，覆盖 AI/Agent/移动端/开发工具）")
    lines.append("")
    lines.append("## 精选项目")
    lines.append("")
    for it in ranked:
        lines.append(f"- **{it['name']}** | ⭐{it['stars']} | {it['lang']}")
        lines.append(f"  [{it['name']}]({it['url']})")
        lines.append(f"  {it['desc']}")
        lines.append("")
    if ranked:
        lines.append("## ⭐【值得关注】")
        lines.append("")
        for i, it in enumerate(ranked[:5], 1):
            lines.append(f"{i}. **{it['name'].split('/')[-1]}** — {it['desc']}（⭐{it['stars']}）")
    return "\n".join(lines)


def collect_huggingface():
    """arXiv cs.AI / cs.CL 每日 RSS（完全公开，无需 auth）。"""
    url = "http://export.arxiv.org/rss/cs.AI"
    try:
        xml = _get(url)
        root = ET.fromstring(xml)
        papers = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = item.findtext("link") or ""
            if title and link:
                papers.append((title, link))
        lines = [f"# AI 论文精选 · {TODAY}", ""]
        lines.append("> 数据来源：arXiv cs.AI RSS（每日最新）")
        lines.append("")
        lines.append("## 精选论文")
        lines.append("")
        for title, link in papers[:15]:
            lines.append(f"- [{title}]({link})")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        print(f"[arxiv] 跳过: {e}", file=sys.stderr)
        return ""


def main():
    os.makedirs(INBOX, exist_ok=True)
    gh = collect_github()
    with open(os.path.join(INBOX, f"{TODAY}-GitHub项目.md"), "w") as f:
        f.write(gh + "\n")
    print(f"[ok] GitHub 采集 -> {TODAY}-GitHub项目.md")
    hf = collect_huggingface()
    if hf:
        with open(os.path.join(INBOX, f"{TODAY}-AI论文.md"), "w") as f:
            f.write(hf + "\n")
        print(f"[ok] HF 采集 -> {TODAY}-AI论文.md")
    else:
        print("[warn] HF 采集为空，跳过")


if __name__ == "__main__":
    main()
