#!/usr/bin/env python3
"""distill.py — 知识提炼脚本

读取 raw/inbox 中当日采集文件，调用 LLM 把每条高价值内容提炼成
wiki 页面（concepts/entities/sources/syntheses），格式严格对齐
server.py 的 _parse_frontmatter：
  > tags: #tag1 #tag2
  > source: [名称](url)
  > score: 综合 X.X/10

LLM 配置（环境变量，缺省走 OpenAI 兼容接口）：
  LLM_API_BASE  (默认 https://api.openai.com/v1)
  LLM_API_KEY   (默认空，由调用方注入)
  LLM_MODEL     (默认 gpt-4o-mini)
"""
import os
import sys
import json
import glob
import datetime
import urllib.request

REPO_ROOT = os.environ.get(
    "KB_REPO_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)
INBOX = os.path.join(REPO_ROOT, "raw", "inbox")
WIKI = os.path.join(REPO_ROOT, "wiki")
TODAY = datetime.date.today().strftime("%Y-%m-%d")

API_BASE = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1").rstrip("/")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")

WIKI_SKELETON = """# {title}

> tags: {tags}
> source: [{source_name}]({source_url})
> score: 技术深度{t1}/10 | 实用价值{t2}/10 | 时效性{t3}/10 | 领域匹配{t4}/10 | 综合 {overall}/10

## 核心概念
{concept}

## 设计原理
{principle}

## 关键实现
{impl}

## 关联分析
{relate}

## 可执行建议
{suggest}
"""


def _chat(system, user, max_tokens=900):
    last_err = None
    # 重试 2 次（应对偶发网络抖动 / 空响应）
    for attempt in range(3):
        try:
            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            req = urllib.request.Request(
                f"{API_BASE}/v1/chat/completions",
                data=json.dumps(payload).encode(),
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode())
            content = data["choices"][0]["message"]["content"]
            if not content or not content.strip():
                last_err = "empty response"
                continue  # 空响应，重试
            return content
        except Exception as e:
            last_err = e
            print(f"    [retry {attempt+1}/3] {e}", file=sys.stderr)
    raise RuntimeError(f"LLM 调用失败: {last_err}")


def _clean_json(text):
    """容错解析 LLM 返回的 JSON（清理控制字符、截取大括号段）。"""
    import re
    # 去掉非打印控制字符（保留 \n \t）
    text = "".join(ch if (ch in "\n\t" or ord(ch) >= 32) else " " for ch in text)
    s, e = text.find("{"), text.rfind("}")
    if s == -1 or e == -1:
        return None
    raw = text[s:e + 1]
    try:
        return json.loads(raw)
    except Exception:
        # 尝试修复常见截断：补 closing
        try:
            return json.loads(raw + "}}")
        except Exception:
            return None


def parse_items(md_text):
    """从采集文件解析出 (name, url, desc) 列表。

    支持两种格式：
      - 同行: - [**name**](url) desc
      - 跨行: - **name** | ⭐123 | lang
              [name](url)
              desc
    """
    import re
    items = []
    lines = md_text.split("\n")
    pending_name = None
    for line in lines:
        line_s = line.strip()
        # 先找当前行里的 [name](url)
        m = re.search(r"\[([^\]]+)\]\((https?://[^)]+)\)", line_s)
        if m:
            url = m.group(2)
            # name: 优先括号前 **name**，否则用链接文字
            name_m = re.search(r"\*\*([^*]+)\*\*", line_s)
            name = name_m.group(1) if name_m else m.group(1)
            if name.startswith("http"):
                name = m.group(1)
            # 清理 Anthropic 等 HTML 抓取带来的「分类 日期」前缀
            import re as _re
            name = _re.sub(
                r"^(Announcements|Product|Case Study|Research|Press|Engineering|Safety)\s+"
                r"[A-Z][a-z]+\s+\d{1,2},?\s*\d{4}\s+",
                "", name,
            ).strip()
            desc = line_s.split("](")[0].split("**")[-1][:120]
            items.append((name, url, desc))
            pending_name = None
            continue
        # 跨行：上一行有 **name** 但本行没有 url，记录待匹配
        bm = re.search(r"^- \*\*(.+?)\*\*", line_s)
        if bm:
            pending_name = bm.group(1)
    # 去重
    seen = {}
    for n, u, d in items:
        seen[u] = (n, u, d)
    return list(seen.values())[:8]


def distill_one(name, url, category, date):
    system = (
        "你是技术知识库编辑。把一条技术内容提炼成结构化 wiki 页面。"
        "必须严格输出如下 JSON（不要多余文字）：\n"
        '{"title":"页面标题","tags":["#英文标签1","#英文标签2"],'
        '"t1":8,"t2":7,"t3":8,"t4":9,"overall":7.5,'
        '"concept":"核心概念(2-3句，含具体技术细节)","principle":"设计原理",'
        '"impl":"关键实现(含算法/参数/接口等具体细节)","relate":"关联分析(交叉引用同类项目)",'
        '"suggest":"可执行建议(读者能立刻做的1-2件事)"}'
    )
    user = f"项目名称：{name}\n链接：{url}\n分类：{category}\n请提炼。"
    try:
        out = _chat(system, user)
        obj = _clean_json(out)
        if not obj:
            return None
        tags = " ".join(obj.get("tags", ["#uncategorized"]))
        page = WIKI_SKELETON.format(
            title=obj["title"],
            tags=tags,
            source_name=name,
            source_url=url,
            t1=obj.get("t1", 7), t2=obj.get("t2", 7),
            t3=obj.get("t3", 7), t4=obj.get("t4", 7),
            overall=obj.get("overall", 7.0),
            concept=obj.get("concept", ""),
            principle=obj.get("principle", ""),
            impl=obj.get("impl", ""),
            relate=obj.get("relate", ""),
            suggest=obj.get("suggest", ""),
        )
        return page, obj["title"]
    except Exception as ex:
        print(f"  [distill:{name}] 失败: {ex}", file=sys.stderr)
        return None


def main():
    if not API_KEY:
        print("[warn] 未设置 LLM_API_KEY，跳过提炼", file=sys.stderr)
        return
    # 当日采集文件
    files = glob.glob(os.path.join(INBOX, f"{TODAY}-*.md"))
    if not files:
        print(f"[warn] 今日无采集文件 {TODAY}-*.md", file=sys.stderr)
        return
    made = 0
    for fp in files:
        fname = os.path.basename(fp)
        category = "entities" if "GitHub" in fname else "sources"
        text = open(fp, encoding="utf-8").read()
        items = parse_items(text)
        print(f"[distill] {fname}: {len(items)} 条 -> {category}")
        for name, url, desc in items:
            res = distill_one(name, url, category, TODAY)
            if not res:
                continue
            page, title = res
            # 文件名安全化
            safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in title)[:60]
            outp = os.path.join(WIKI, category, f"{safe}.md")
            os.makedirs(os.path.dirname(outp), exist_ok=True)
            if os.path.exists(outp):
                continue  # 已存在则跳过，避免覆盖
            with open(outp, "w", encoding="utf-8") as f:
                f.write(page)
            made += 1
            print(f"  [ok] {category}/{safe}.md")
    print(f"[done] 新增 wiki 页面 {made} 个")


if __name__ == "__main__":
    main()
