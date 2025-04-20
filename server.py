import argparse
import os
import sys

from loguru import logger
from mcp.server.fastmcp import Context, FastMCP

# models と util から必要なものをインポート
from models import WeeklyAWSJpDetailedUpdate, WeeklyAWSJpUpdate
from util import (
    get_latest_generative_ai_details,  # 変更
    get_latest_weekly_aws_details,  # 変更
    get_recent_entries,
)

# ロギング設定
logger.remove()
logger.add(sys.stderr, level=os.getenv("FASTMCP_LOG_LEVEL", "INFO"))

# MCP サーバー定義
mcp = FastMCP(
    "custom.weekly-aws-jp-mcp-server",
    instructions="""
    # 週刊AWS 日本語版取得サーバー

    日本語サイトの「週刊AWS」タグページから、過去 n 日間の記事一覧・最新記事を取得して返します。
    また、記事の見出しやリンクを抽出する機能も提供しています。
    """,
    dependencies=[
        "pydantic",
        "feedparser",
        "loguru",
        "requests",
        "readabilipy",
        "markdownify",
    ],
)


@mcp.tool()
async def get_weekly_jp_updates(
    ctx: Context,
    days: int = 7,
    limit: int = 10,
) -> list[WeeklyAWSJpUpdate]:
    """指定された日数内の「週刊AWS」日本語版ブログ記事のリストを取得します。

    ## Usage
    このツールは、AWS Japan Blog の RSS フィードから、指定された日数 (`days`) 以内に公開された
    「週刊AWS」タグの記事を取得し、最大 `limit` 件までのリストを返します。

    ## When to Use
    - 特定期間内の週刊AWSの更新情報をまとめて確認したい場合。
    - 最新の数件だけでなく、少し前の週刊AWS記事も参照したい場合。

    ## Result Interpretation
    戻り値は `WeeklyAWSJpUpdate` モデルのリストです。各要素には以下の情報が含まれます:
    - `title`: 記事のタイトル
    - `url`: 記事のURL
    - `published`: 記事の公開日時 (UTC)
    - `summary`: 記事の要約 (利用可能な場合)

    Args:
        ctx: MCP コンテキスト
        days: 何日前までの記事を取得するか (デフォルト: 7)
        limit: 最大取得件数 (デフォルト: 10)

    Returns:
        WeeklyAWSJpUpdate モデルのリスト

    """
    await ctx.info(f"過去 {days} 日分の週刊AWS記事を取得します (最大 {limit} 件)")
    entries = get_recent_entries(days=days, limit=limit)
    await ctx.info(f"{len(entries)} 件の記事が見つかりました。")
    return entries


@mcp.tool()
async def get_latest_jp_update_details(ctx: Context) -> WeeklyAWSJpDetailedUpdate | None:  # 名前と戻り値の型を変更
    """「週刊AWS」日本語版ブログの最新記事の詳細(本文コンテンツ含む)を1件取得します。

    ## Usage
    このツールは、AWS Japan Blog の RSS フィードから、「週刊AWS」タグが付いた最新の記事のメタデータと、
    本文コンテンツを取得します。(「週刊生成AI with AWS」の記事は除外されます)

    ## When to Use
    - 最新の週刊AWS記事のメタデータと本文コンテンツを一度に取得したい場合。
    - 記事のメタデータと整形された本文の両方が必要な場合。

    ## Result Interpretation
    戻り値は `WeeklyAWSJpDetailedUpdate` モデル、または記事が見つからない場合は `None` です。
    モデルには以下の情報が含まれます:
    - `title`: 記事のタイトル
    - `url`: 記事のURL
    - `published`: 記事の公開日時 (UTC)
    - `summary`: 記事の要約 (利用可能な場合)
    - `content`: 記事本文のコンテンツ (取得できない場合は None になる可能性あり)

    Args:
        ctx: MCP コンテキスト

    Returns:
        WeeklyAWSJpDetailedUpdate モデル、または None

    """
    await ctx.info("最新の「週刊AWS」記事の詳細を取得します")
    entry = get_latest_weekly_aws_details()  # 呼び出す関数を変更
    if not entry:
        await ctx.warning("最新の「週刊AWS」記事が見つかりませんでした")
        return None
    await ctx.info(f"最新記事の詳細が見つかりました: {entry.title}")
    return entry


@mcp.tool()
async def get_latest_generative_ai_jp_update_details(
    ctx: Context,
) -> WeeklyAWSJpDetailedUpdate | None:  # 名前と戻り値の型を変更
    """「週刊生成AI with AWS」日本語版ブログの最新記事の詳細(本文コンテンツ含む)を1件取得します。

    ## Usage
    このツールは、AWS Japan Blog の RSS フィードから、「週刊生成AI with AWS」を含む最新の記事のメタデータと、
    本文コンテンツを取得します。

    ## When to Use
    - 最新の「週刊生成AI with AWS」記事のメタデータと本文コンテンツを一度に取得したい場合。
    - 記事のメタデータと整形された本文の両方が必要な場合。

    ## Result Interpretation
    戻り値は `WeeklyAWSJpDetailedUpdate` モデル、または記事が見つからない場合は `None` です。
    モデルには以下の情報が含まれます:
    - `title`: 記事のタイトル
    - `url`: 記事のURL
    - `published`: 記事の公開日時 (UTC)
    - `summary`: 記事の要約 (利用可能な場合)
    - `content`: 記事本文のコンテンツ (取得できない場合は None になる可能性あり)

    Args:
        ctx: MCP コンテキスト

    Returns:
        WeeklyAWSJpDetailedUpdate モデル、または None

    """
    await ctx.info("最新の「週刊生成AI with AWS」記事の詳細を取得します")
    entry = get_latest_generative_ai_details()  # 呼び出す関数を変更
    if not entry:
        await ctx.warning("最新の「週刊生成AI with AWS」記事が見つかりませんでした")
        return None
    await ctx.info(f"最新記事の詳細が見つかりました: {entry.title}")
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description="週刊AWS日本語版 MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8888, help="Port to run the server on")
    args = parser.parse_args()

    logger.info("Starting Weekly AWS JP MCP Server")
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport="sse")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
