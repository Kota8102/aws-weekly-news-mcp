# 週刊 AWS JP MCP Server

日本語版『週刊 AWS』タグ記事を取得するためのMCPサーバー

## 機能

* 最新の「週刊 AWS」記事の取得
* 過去の記事の一覧取得と日数・件数の指定
* 記事の詳細情報（タグ、著者など）の取得
* 記事本文のMarkdown形式での取得

## 前提条件

* Python 3.11以上
* [uv](https://github.com/astral-sh/uv) - 高速Pythonパッケージインストーラー

## インストール

Claude DesktopやCursorなどのMCPをサポートするアプリケーションで使用するために、以下のような設定を行います（例: `~/.mcp/mcp.json`）:

```json
{
  "mcpServers": {
    "weekly-aws-jp-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-awsnews-python",
        "run",
        "server.py"
      ]
    }
  }
}
```

## ツールとリソース

このサーバーは以下のツールをMCPインターフェースを通じて提供します：

* `get_weekly_jp_updates(days=7, limit=10)` - 過去n日分の『週刊 AWS』記事一覧を取得します
* `get_latest_jp_update()` - 最新の『週刊 AWS』記事を1件取得します
* `get_latest_jp_update_with_details()` - 最新記事と詳細情報（タグ、著者など）を取得します
* `get_latest_jp_update_content()` - 最新記事の本文をMarkdown形式で取得します

## レスポンス例

### get_weekly_jp_updates

```json
[
  {
    "title": "週刊 AWS – 2025年4月第2週号",
    "url": "https://aws.amazon.com/jp/blogs/news/aws-weekly-2025-04-2/",
    "published": "2025-04-10T00:00:00"
  }
]
```

### get_latest_jp_update_with_details

```json
{
  "title": "週刊 AWS – 2025年4月第3週号",
  "url": "https://aws.amazon.com/jp/blogs/news/aws-weekly-2025-04-3/",
  "published": "2025-04-17T00:00:00",
  "tags": ["週刊 AWS", "新機能", "アップデート"],
  "author": "AWS Japan Blog Team"
}
```

### get_latest_jp_update_content

```json
{
  "content": "# 週刊 AWS – 2025年4月第3週号\n\nこんにちは、AWS Japanブログチームです...",
  "title": "週刊 AWS – 2025年4月第3週号"
}
```
