from datetime import UTC, datetime, timedelta

import feedparser
from feedparser import FeedParserDict
from loguru import logger

from models import WeeklyAWSJpDetailedUpdate, WeeklyAWSJpUpdate

# --- Constants ---
RSS_FEED_URL = "https://aws.amazon.com/jp/blogs/news/tag/%E9%80%B1%E5%88%8Aaws/feed/"
REQUEST_TIMEOUT = 10


def get_feed_entries() -> FeedParserDict:
    """RSSフィードを取得してパースする"""
    feed = feedparser.parse(RSS_FEED_URL)
    if getattr(feed, "bozo", False):
        logger.warning(f"RSSパースエラー: {feed.bozo_exception}")
    return feed


def _extract_content_string(content_data: str) -> str | None:
    """Feedparser の content データから文字列を抽出する"""
    if not content_data:
        return None
    if isinstance(content_data, list):
        if not content_data:
            return None
        # 最初の要素を取得
        first_content = content_data[0]
        # .value 属性があればそれを使う (なければ None)
        content_value = getattr(first_content, "value", None)
        if isinstance(content_value, str):
            return content_value
        # .value が文字列でない場合も None とする
        logger.warning(f"content[0].value が文字列ではありません: {type(content_value)}")
        return None
    if isinstance(content_data, str):
        return content_data
    # 予期しない型の場合は None を返す
    logger.warning(f"予期しない content の型: {type(content_data)}")
    return None


def get_recent_entries(days: int = 7, limit: int = 20) -> list[WeeklyAWSJpUpdate]:
    """指定日数分の記事エントリを取得する"""
    feed = get_feed_entries()
    cutoff = datetime.now(UTC) - timedelta(days=days)

    entries = []
    for entry in feed.entries:
        pub_date = datetime(*entry.published_parsed[:6], tzinfo=UTC)
        if pub_date >= cutoff:
            entries.append(
                WeeklyAWSJpUpdate(
                    title=entry.title,
                    url=entry.link,
                    published=pub_date,
                    summary=getattr(entry, "summary", None),
                ),
            )
        if len(entries) >= limit:
            break

    return entries


def get_latest_weekly_aws_details() -> WeeklyAWSJpDetailedUpdate | None:
    """最新の「週刊AWS」記事の詳細を1件取得する

    Returns:
        WeeklyAWSJpDetailedUpdate | None: 最新の「週刊AWS」記事の詳細

    """
    feed = get_feed_entries()
    if not feed.entries:
        return None

    # タイトルに「週刊AWS」を含み、「週刊生成AI with AWS」を含まないエントリをフィルタリング
    weekly_aws_entries = [
        e for e in feed.entries if "週刊AWS" in getattr(e, "title", "") and "週刊生成AI" not in getattr(e, "title", "")
    ]
    if not weekly_aws_entries:
        logger.info("最新の「週刊AWS」記事が見つかりませんでした。")
        return None

    try:
        latest = max(weekly_aws_entries, key=lambda e: datetime(*e.published_parsed[:6], tzinfo=UTC))

        content_data = getattr(latest, "content", None)
        content_str = _extract_content_string(content_data)

        return WeeklyAWSJpDetailedUpdate(
            title=latest.title,
            url=latest.link,
            published=datetime(*latest.published_parsed[:6], tzinfo=UTC),
            summary=getattr(latest, "summary", None),
            content=content_str,
        )

    except Exception as e:
        logger.error(f"最新の「週刊AWS」記事詳細の処理中にエラー: {e}", exc_info=True)
        return None


def get_latest_generative_ai_details() -> WeeklyAWSJpDetailedUpdate | None:
    """最新の「週刊生成AI with AWS」記事の詳細を1件取得する"""
    feed = get_feed_entries()
    if not feed.entries:
        return None

    # タイトルに「週刊生成AI with AWS」を含むエントリをフィルタリング
    gen_ai_entries = [e for e in feed.entries if "週刊生成AI" in getattr(e, "title", "")]
    if not gen_ai_entries:
        logger.info("最新の「週刊生成AI with AWS」記事が見つかりませんでした。")
        return None

    try:
        latest = max(gen_ai_entries, key=lambda e: datetime(*e.published_parsed[:6], tzinfo=UTC))
        pub_date = datetime(*latest.published_parsed[:6], tzinfo=UTC)

        content_data = getattr(latest, "content", None)
        content_str = _extract_content_string(content_data)

        # 詳細モデルを作成して返す
        return WeeklyAWSJpDetailedUpdate(
            title=latest.title,
            url=latest.link,
            published=pub_date,
            summary=getattr(latest, "summary", None),
            content=content_str,  # Use the extracted string or None
        )

    except Exception as e:
        logger.error(f"最新の「週刊生成AI with AWS」記事詳細の処理中にエラー: {e}", exc_info=True)
        return None
