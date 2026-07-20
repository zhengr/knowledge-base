#!/usr/bin/env python3
"""collect.py — 知识库采集脚本（0 token 成本）

数据源（全部免费，无需付费 LLM）：
  - GitHub Search API: 每日热门 AI/Agent/移动端/开发工具项目（按 star 排序）
  - AI 新闻 RSS（依据 readless.app 2026 评测的可信源）:
      OpenAI / Hugging Face / MarkTechPost / MIT Tech Review AI /
      Google AI / Ahead of AI (Raschka) / The Gradient / Last Week in AI / The Verge AI
      （Anthropic 无公开 RSS，改以 HTML 抓取 Newsroom 页面，同样作为知识来源）
  - arXiv cs.AI: 当日精选论文（RSS）

输出：raw/inbox/YYYY-MM-DD-{GitHub项目,AI新闻,AI论文}.md
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

# AI 新闻 RSS 源（来源：https://www.readless.app/blog/best-ai-news-rss-feeds-2026）
# 注：Anthropic 无公开 RSS feed（仅 https://www.anthropic.com/news 网页），故不列入自动拉取。
AI_NEWS_FEEDS = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
    ("MarkTechPost", "https://www.marktechpost.com/feed/"),
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed/"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("Ahead of AI (Raschka)", "https://magazine.sebastianraschka.com/feed"),
    ("The Gradient", "https://thegradient.pub/rss/"),
    ("Last Week in AI", "https://lastweekin.ai/feed"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
]


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


def _parse_rss(xml_text):
    """从 RSS/Atom XML 解析出 (title, link) 列表，兼容 RSS 与 Atom。"""
    root = ET.fromstring(xml_text)
    items = []
    # RSS: <item><title><link>
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if title and link:
            items.append((title, link))
    # Atom: <entry><title><link href=...>
    if not items:
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            link = ""
            for l in entry.iter("{http://www.w3.org/2005/Atom}link"):
                link = l.get("href") or link
            if title and link:
                items.append((title, link))
    return items


def collect_ai_news():
    """AI 新闻 RSS 聚合（readless.app 2026 评测的 10 个可信源）。"""
    lines = [f"# AI 新闻精选 · {TODAY}", ""]
    lines.append("> 数据来源：AI 新闻 RSS（OpenAI / Anthropic / Hugging Face / MarkTechPost / "
                 "MIT Tech Review / Google AI / Ahead of AI / The Gradient / Last Week in AI / The Verge AI）")
    lines.append("")
    total = 0
    for name, url in AI_NEWS_FEEDS:
        try:
            xml = _get(url, timeout=25)
            items = _parse_rss(xml)[:5]  # 每源取最新 5 条，控制体量
            if not items:
                continue
            lines.append(f"## {name}")
            lines.append("")
            for title, link in items:
                lines.append(f"- [{title}]({link})")
            lines.append("")
            total += len(items)
        except Exception as e:
            print(f"[news:{name}] 跳过: {e}", file=sys.stderr)
    lines.append(f"> 共聚合 {total} 条新闻")
    return "\n".join(lines)


def collect_anthropic():
    """Anthropic 新闻（无公开 RSS，改抓 HTML 列表页）。"""
    import re as _re
    import html as _html
    url = "https://www.anthropic.com/news"
    try:
        html_text = _get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        links = _re.findall(r'<a[^>]+href="(/news/[^"]+)"[^>]*>(.*?)</a>', html_text, _re.S)
        seen = set()
        items = []
        for href, inner in links:
            if href in seen:
                continue
            seen.add(href)
            txt = _html.unescape(_re.sub(r"<[^>]+>", " ", inner)).strip()
            txt = _re.sub(r"\s+", " ", txt)
            if len(txt) > 10 and href.startswith("/news/"):
                items.append((txt, "https://www.anthropic.com" + href))
        items = items[:10]  # 取最新 10 条
        lines = [f"# Anthropic 新闻精选 · {TODAY}", ""]
        lines.append("> 数据来源：Anthropic Newsroom（HTML 抓取，无公开 RSS）")
        lines.append("")
        lines.append("## Anthropic")
        lines.append("")
        for title, link in items:
            lines.append(f"- [{title}]({link})")
        lines.append("")
        return "\n".join(lines)
    except Exception as e:
        print(f"[anthropic] 跳过: {e}", file=sys.stderr)
        return ""


def collect_huggingface():
    """arXiv cs.AI 每日 RSS（完全公开，无需 auth）。"""
    url = "https://rss.arxiv.org/rss/cs.AI"
    try:
        xml = _get(url)
        papers = _parse_rss(xml)
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
    news = collect_ai_news()
    with open(os.path.join(INBOX, f"{TODAY}-AI新闻.md"), "w") as f:
        f.write(news + "\n")
    print(f"[ok] AI 新闻采集 -> {TODAY}-AI新闻.md ({news.count(chr(10)+'- [')} 条)")
    hf = collect_huggingface()
    if hf:
        with open(os.path.join(INBOX, f"{TODAY}-AI论文.md"), "w") as f:
            f.write(hf + "\n")
        print(f"[ok] HF 采集 -> {TODAY}-AI论文.md")
    else:
        print("[warn] HF 采集为空，跳过")
    anth = collect_anthropic()
    if anth:
        with open(os.path.join(INBOX, f"{TODAY}-Anthropic新闻.md"), "w") as f:
            f.write(anth + "\n")
        print(f"[ok] Anthropic 采集 -> {TODAY}-Anthropic新闻.md")
    else:
        print("[warn] Anthropic 采集为空，跳过")


if __name__ == "__main__":
    main()
