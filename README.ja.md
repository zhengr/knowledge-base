> 🌐 他言語: [English](README.md) · [中文](README.zh.md)
>
> # 知識ベース — 自動構築型 MCP サーバー

自分で**知識を構築する**個人技術ナレッジベースです。ホスト上のコンテナが毎日
GitHub Trending、AI ニュース RSS（Anthropic は HTML スクレイピング）、arXiv から
収集し、LLM で構造化された wiki ページに抽出、MCP サーバーが意味検索とインタラクティブ
な知識グラフ可視化を提供します。

> [mufans/knowledge-base](https://github.com/mufans/knowledge-base) および
> [Karpathy LLM Wiki 手法](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
> に着想を得ています。

## 仕組み

```
A1 ホスト（単一コンテナ knowledge-mcp）— 完全ローカル、毎日のフローは GitHub を通らない
  ├─ collect スレッド（UTC 16:00）：scripts/collect.py → /data/kb-self/raw/inbox/
  ├─ distill スレッド（UTC 16:45）：scripts/distill.py → /data/kb-self/wiki/
  │     （LLM key はコンテナ環境変数のみに存在し、GitHub を通らない）
  ├─ /mcp エンドポイント提供（Streamable HTTP、Bearer 認証は任意）でローカル wiki を検索
  └─ /graph エンドポイント提供（ブラウザでインタラクティブな知識グラフ可視化）
```

> **セキュリティ注意**：収集と抽出はすべて A1 マシン上で完結します。GitHub
> はソースコードのホスティングと Docker イメージのビルドのみ——収集データも
> LLM API key も一切触れません。

## リポジトリ構成

```
.github/workflows/
  build.yml           # arm64 イメージ構築 → ghcr.io/zhengr/knowledge-mcp
Dockerfile
docker-compose.yml
knowledge-graph.html  # インタラクティブ知識グラフ（/graph エンドポイントで提供）
scripts/
  collect.py          # 無料収集器（GitHub + AI ニュース RSS + Anthropic HTML + arXiv）
  distill.py          # LLM → wiki ページ（OpenAI 互換 API）
server.py             # MCP サーバー（search_kb / get_entity / list_recent）+ /graph ルート
pyproject.toml
```

> `raw/inbox/` と `wiki/` は実行時にコンテナ上でローカル生成され、**GitHub リポジトリには保存されません**。

## 環境変数

| 変数 | デフォルト | 説明 |
|---|---|---|
| `KNOWLEDGE_BASE_PATH` | `/kb` | ナレッジベースのルート（ `wiki/`、`raw/inbox/` を含む） |
| `KB_TRANSPORT` | `http` | `http` / `sse` / `stdio` |
| `KB_HOST` | `0.0.0.0` | バインドアドレス |
| `KB_PORT` | `8000` | リスンポート |
| `MCP_AUTH_TOKEN` | _(空)_ | 設定すると `/mcp` で `Authorization: Bearer ***` を要求 |
| `LLM_API_BASE` | `https://api.openai.com/v1` | 抽出用 LLM エンドポイント |
| `LLM_API_KEY` | _(空)_ | LLM API key（空の場合、抽出スレッドはスキップ） |
| `LLM_MODEL` | `gpt-4o-mini` | LLM モデル名 |

## デプロイ（単一コンテナ）

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

コンテナは**単一プロセスで 3 つの処理を実行**：
1. **collect スレッド** — 毎日 UTC 16:00、`raw/inbox/` に書き込み
2. **distill スレッド** — 毎日 UTC 16:45、LLM 呼出 → `wiki/` を生成
3. **MCP サーバー** — ポート 8000 で `/mcp`（検索）+ `/graph`（可視化）を提供

## エンドポイント

| パス | 認証 | 説明 |
|---|---|---|
| `/mcp` | Bearer トークン | MCP streamable-http エンドポイント（search_kb / get_entity / list_recent） |
| `/graph` | なし | インタラクティブ知識グラフ（ブラウザで力指向図） |

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

## 知識グラフの表示

ブラウザで `http://<host>:8000/graph` を開きます。グラフはブラウザから `/mcp` 経由で
wiki データをリアルタイムに取得（fetch）します。機能：
- **力指向レイアウト** — ノードがタグ共起により自動配置
- **ノードクリック** — 右側に詳細パネル（タイトル、スコア、タグ、要約）
- **検索ハイライト** — キーワード入力で一致ノードをリアルタイムハイライト
- **ズーム & パン** — スクロールでズーム、背景ドラッグでパン
- **フィルタ** — entities（プロジェクト）または sources（ニュース/論文）のみ表示
- **タグクラウド** — タグをクリックして関連ノードをハイライト

## ツール

- `search_kb(query, category?, limit?)` — wiki の全文検索
- `get_entity(name)` — 単一 wiki ページの取得
- `list_recent(limit?, days?, min_score?)` — 最近更新されたページ
