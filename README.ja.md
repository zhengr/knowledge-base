# 知識ベース — 自動構築型 MCP サーバー

自分で**知識を構築する**個人技術ナレッジベースです。GitHub Actions が毎日
GitHub Trending と arXiv から収集し、LLM で構造化された wiki ページに抽出、
Docker / Portainer でデプロイ可能な MCP サーバーが意味検索を提供します。

> [mufans/knowledge-base](https://github.com/mufans/knowledge-base) および
> [Karpathy LLM Wiki 手法](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
> に着想を得ています。

## 仕組み

```
GitHub Actions（毎日 UTC 16:00）
  ├─ scripts/collect.py  → raw/inbox/   （GitHub Trending + arXiv RSS、無料）
  ├─ scripts/distill.py  → wiki/         （LLM が entities/sources へ抽出）
  └─ このリポジトリへ自動コミット＆プッシュ
        ↓  （A1 ホストがリポジトリを取得）
MCP コンテナ（knowledge-mcp）
  ├─ /mcp エンドポイント提供（Streamable HTTP、Bearer 認証は任意）
  └─ バックグラウンドスレッドが毎日 UTC 16:30 に最新 wiki を再取得
```

## リポジトリ構成

```
.github/workflows/
  build.yml      # arm64 イメージ構築 → ghcr.io/zhengr/knowledge-mcp
  knowledge.yml  # 毎日 collect + distill + push
Dockerfile
docker-compose.yml
scripts/
  collect.py     # 無料収集器（GitHub + arXiv）
  distill.py     # LLM → wiki ページ（OpenAI 互換 API）
  update_wiki.py # 独立更新器（コンテナ内で使用）
server.py        # MCP サーバー（search_kb / get_entity / list_recent）
pyproject.toml
raw/inbox/       # 収集した生コンテンツ（自動生成）
wiki/            # 抽出された知識（自動生成）
```

## 環境変数

| 変数 | デフォルト | 説明 |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | `/kb` | ナレッジベースのルート（ `wiki/` を含む） |
| `KB_TRANSPORT` | `http` | `http` / `sse` / `stdio` |
| `KB_HOST` | `0.0.0.0` | バインドアドレス |
| `KB_PORT` | `8000` | リスンポート |
| `MCP_AUTH_TOKEN` | _(空)_ | 設定すると `Authorization: Bearer <token>` を要求 |
| `KB_UPDATE_URL` | リポジトリ tarball | 自動更新元 URL の上書き |

## デプロイ（単一コンテナ）

```bash
docker run -d --name knowledge-mcp -p 8000:8000 \
  -e KNOWLEDGE_BASE_PATH=/data/kb-self \
  -e MCP_AUTH_TOKEN=your-secret-token \
  -v /opt:/data:rw \
  ghcr.io/zhengr/knowledge-mcp:latest
```

コンテナは MCP エンドポイントを**提供**すると同時に、wiki をその場で
**自動更新**します（マウント先 `/data/kb-self` へ書き込み）。

## クライアント接続（Claude Code / Cursor）

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

## LLM の設定（抽出用）

リポジトリの **Settings → Secrets → Actions** で以下を設定：
`LLM_API_BASE`、`LLM_API_KEY`、`LLM_MODEL`。

## ツール

- `search_kb(query, category?, limit?)` — wiki の全文検索
- `get_entity(name)` — 単一 wiki ページの取得
- `list_recent(limit?, days?, min_score?)` — 最近更新されたページ

参照：[English](README.md) · [中文](README.zh.md)
