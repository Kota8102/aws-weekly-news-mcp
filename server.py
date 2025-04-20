import argparse
import os
import sys

from loguru import logger
from mcp.server.fastmcp import Context, FastMCP

from models import WeeklyAWSJpUpdate, WeeklyAWSJpDetailedUpdate
from util import (
    fetch_weekly_jp_entries,
    fetch_latest_jp_entry,
    fetch_latest_jp_entry_with_details,
    fetch_url_content,
)

# ロギング設定
logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'INFO'))

# MCP サーバー定義
mcp = FastMCP(
    'custom.weekly-aws-jp-mcp-server',
    instructions="""
    # 週刊AWS 日本語版取得サーバー

    日本語サイトの「週刊AWS」タグページから、過去 n 日間の記事一覧・最新記事を取得して返します。
    また、記事の見出しやリンクを抽出する機能も提供しています。
    """,
    dependencies=[
        'pydantic',
        'feedparser',
        'loguru',
    ],
)

@mcp.tool()
async def get_weekly_jp_updates(ctx: Context, days: int = 7, limit: int = 10) -> list[WeeklyAWSJpUpdate]:
    """
    過去 `days` 日以内の「週刊AWS」記事を最大 `limit` 件取得。
    """
    # 非同期ログ呼び出しを info レベルで行う
    await ctx.info(f'Fetching JP weekly AWS entries for the past {days} days')
    raw = fetch_weekly_jp_entries(days=days, limit=limit)
    return [WeeklyAWSJpUpdate(**item) for item in raw]

@mcp.tool()
async def get_latest_jp_update(ctx: Context) -> WeeklyAWSJpUpdate | None:
    """
    「週刊AWS」最新記事を 1 件だけ取得。
    """
    # 非同期ログ呼び出しを info レベルで行う
    await ctx.info('Fetching latest JP weekly AWS entry')
    raw = fetch_latest_jp_entry()
    if not raw:
        # エントリがない場合は warning レベルでログ
        await ctx.warning('No entries found in the JP weekly AWS feed')
        return None
    return WeeklyAWSJpUpdate(**raw)

@mcp.tool()
async def get_latest_jp_update_with_details(ctx: Context) -> WeeklyAWSJpDetailedUpdate | None:
    """
    「週刊AWS」最新記事を1件取得し、記事ページから詳細情報も含めて返す。
    """
    await ctx.info('Fetching latest JP weekly AWS entry with details')
    raw = fetch_latest_jp_entry_with_details()
    if not raw:
        await ctx.warning('No entries found in the JP weekly AWS feed')
        return None
    return WeeklyAWSJpDetailedUpdate(**raw)

@mcp.tool()
async def get_latest_jp_update_content(ctx: Context) -> dict | None:
    """
    最新の「週刊AWS」記事のURLを取得し、そのコンテンツを返す。
    
    Returns:
        dict: {
            'entry': WeeklyAWSJpUpdate - 記事のメタデータ
            'content': str - 記事のコンテンツ（Markdown形式）
        }
    """
    await ctx.info('最新の週刊AWS記事とそのコンテンツを取得')
    
    # 最新の記事を取得
    entry = fetch_latest_jp_entry()
    if not entry:
        await ctx.warning('週刊AWSフィードにエントリがありません')
        return None
    
    # URLからコンテンツを取得
    content = fetch_url_content(entry['url'])
    
    return {
        'entry': WeeklyAWSJpUpdate(**entry),
        'content': content
    }

def main():
    parser = argparse.ArgumentParser(description='週刊AWS日本語版 MCP Server')
    parser.add_argument('--sse', action='store_true', help='Use SSE transport')
    parser.add_argument('--port', type=int, default=8888, help='Port to run the server on')
    args = parser.parse_args()

    logger.info('Starting Weekly AWS JP MCP Server')
    if args.sse:
        mcp.settings.port = args.port
        mcp.run(transport='sse')
    else:
        mcp.run()

if __name__ == '__main__':
    main()