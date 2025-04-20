from datetime import UTC, datetime, timedelta
from typing import Any

import feedparser
import markdownify
import readabilipy.simple_json
import requests
from bs4 import BeautifulSoup, Tag
from dateutil import parser
from loguru import logger

from models import WeeklyAWSJpDetailedUpdate, WeeklyAWSJpUpdate

# --- Constants ---
RSS_FEED_URL_JP = "https://aws.amazon.com/jp/blogs/news/tag/%E9%80%B1%E5%88%8Aaws/feed/"

# Selectors for fetch_article_details
CONTENT_SELECTORS = [
    "div.post-content",
    "div.blog-post__content",
    "article.post-content",
    "div.entry-content",
    "main.content",
]
AUTHOR_SELECTORS = [
    "div.post-author-name",
    "div.blog-post__author-name",
    "span.author-name",
    'meta[name="author"]',
]
TAG_SELECTORS = [
    "a.post-tags-link",
    "a.blog-post__tag",
    "span.tag",
    'meta[property="article:tag"]',
]
DATE_SELECTORS = [
    "time.post-date",
    "time.blog-post__date",
    'meta[property="article:published_time"]',
    'meta[name="date"]',
]


def extract_content_from_html(html: str) -> str:
    """HTMLコンテンツをMarkdown形式に変換する

    Args:
        html: HTML文字列
    Returns:
        str: Markdown形式のコンテンツ

    """
    try:
        ret = readabilipy.simple_json.simple_json_from_html_string(
            html,
            use_readability=True,
        )
        if not ret["content"]:
            return "<error>ページの簡略化に失敗しました</error>"
    except (ValueError, KeyError, TypeError) as e:  # 具体的な例外型を指定
        logger.error(f"HTMLコンテンツの抽出中にエラーが発生しました: {e}")
        return "<error>コンテンツの抽出中にエラーが発生しました</error>"
    else:
        return markdownify.markdownify(ret["content"], heading_style=markdownify.ATX)


def fetch_url_content(url: str, max_length: int = 5000) -> str:
    """指定されたURLからコンテンツを取得しMarkdown化して返す

    Args:
        url: 取得対象のURL
        max_length: 返すコンテンツの最大長
    Returns:
        str: 取得したコンテンツ(Markdown形式)、またはエラーメッセージ

    """
    try:
        logger.info(f"URLからコンテンツを取得しています: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        content_type = response.headers.get("content-type", "")
        is_html = (
            "<html" in response.text[:100].lower()
            or "text/html" in content_type
            or not content_type
        )
        content = extract_content_from_html(response.text) if is_html else response.text
        return content[:max_length]
    except requests.exceptions.RequestException as e:
        logger.error(f"URLからのコンテンツ取得中にエラーが発生しました: {e}")
        return f"<error>コンテンツの取得中にエラーが発生しました: {e}</error>"


def fetch_weekly_jp_entries(days: int = 7, limit: int = 20) -> list[WeeklyAWSJpUpdate]:
    """日本語『週刊AWS』フィードから過去 n 日分の記事を取得"""
    feed = feedparser.parse(RSS_FEED_URL_JP)
    if getattr(feed, "bozo", False):
        logger.warning(f"RSSパースエラー: {feed.bozo_exception}")

    cutoff = datetime.now(UTC) - timedelta(days=days)
    entries: list[WeeklyAWSJpUpdate] = []
    for entry in feed.entries:
        pub = datetime(*entry.published_parsed[:6], tzinfo=UTC)
        if pub >= cutoff:
            entries.append(
                WeeklyAWSJpUpdate(
                    title=entry.title,
                    url=entry.link,
                    published=pub,
                    summary=getattr(entry, "summary", None),
                ),
            )
        if len(entries) >= limit:
            break
    logger.info(f"fetch_weekly_jp_entries: {len(entries)}件のエントリーが見つかりました")
    return entries


def fetch_latest_jp_entry() -> WeeklyAWSJpUpdate | None:
    """フィードから最新記事を1件返す

    Args:
        None
    Returns:
        Optional[WeeklyAWSJpUpdate]: 最新記事のデータ、またはNone

    """
    feed = feedparser.parse(RSS_FEED_URL_JP)
    if not feed.entries:
        return None
    latest = max(feed.entries, key=lambda e: datetime(*e.published_parsed[:6], tzinfo=UTC))
    pub = datetime(*latest.published_parsed[:6], tzinfo=UTC)
    return WeeklyAWSJpUpdate(
        title=latest.title,
        url=latest.link,
        published=pub,
        summary=getattr(latest, "summary", None),
    )


# --- Helper functions for fetch_article_details ---


def _extract_element_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    """複数のセレクターを試して要素のテキストを取得"""
    for sel in selectors:
        element = soup.select_one(sel)
        if not element:
            continue
        if sel.startswith("meta"):
            content = element.get("content")
            if isinstance(content, str):  # Ensure content is a string
                return content
        elif isinstance(element, Tag):  # Ensure it's a Tag before calling get_text
            return element.get_text(separator="\\n", strip=True)
    return None


def _extract_all_tags(soup: BeautifulSoup, selectors: list[str]) -> list[str]:
    """複数のセレクターを試してタグを抽出

    Args:
        soup: BeautifulSoupオブジェクト
        selectors: セレクターのリスト
    Returns:
        list[str]: 抽出されたタグのリスト

    """
    tags = []
    for sel in selectors:
        for tag_element in soup.select(sel):
            tag_text = None
            if sel.startswith("meta"):
                content = tag_element.get("content")
                if isinstance(content, str):  # Ensure content is a string
                    tag_text = content
            elif isinstance(tag_element, Tag):  # Ensure it's a Tag
                tag_text = tag_element.get_text(strip=True)

            if tag_text and tag_text not in tags:
                tags.append(tag_text)
    return tags


def fetch_article_details(url: str) -> dict[str, Any]:  # noqa: C901, PLR0912
    """記事ページをスクレイピングして本文・著者などを取得

    Args:
        url: 記事のURL
    Returns:
        Dict[str, Any]: 記事の詳細情報

    """
    try:
        logger.info(f"記事の詳細情報を取得しています: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # --- Extract details using helper functions ---
        content = _extract_element_text(soup, CONTENT_SELECTORS)
        author = _extract_element_text(soup, AUTHOR_SELECTORS)
        tags = _extract_all_tags(soup, TAG_SELECTORS)

        # --- Simplified date extraction ---
        published_date: datetime | None = None
        for sel in DATE_SELECTORS:
            element = soup.select_one(sel)
            if not element:
                continue

            date_str: str | None = None
            if sel.startswith("meta"):
                content_attr = element.get("content")
                if isinstance(content_attr, str):
                    date_str = content_attr
            elif isinstance(element, Tag):
                datetime_attr = element.get("datetime")
                if isinstance(datetime_attr, str):
                    date_str = datetime_attr
                else:
                    # Fallback to text content if datetime attribute is missing/not string
                    text_content = element.get_text(strip=True)
                    if text_content:
                        date_str = text_content

            if date_str:
                try:
                    parsed = parser.parse(date_str)
                    if parsed.tzinfo is None:
                        published_date = parsed.replace(tzinfo=UTC)
                    else:
                        # Convert to UTC if it has timezone info but is not UTC
                        published_date = parsed.astimezone(UTC)
                    logger.debug(f"日付のパースに成功: {date_str} -> {published_date}")
                    break  # Stop after finding the first valid date
                except (ValueError, TypeError, OverflowError) as e:
                    logger.warning(f"日付文字列のパースに失敗: {date_str}, エラー: {e}")
                    continue  # Try next selector if parsing fails

    except requests.exceptions.RequestException as e:
        logger.error(f"記事詳細の取得中にエラーが発生しました: {e}")
        return {
            "content": None,
            "author": None,
            "tags": [],
            "published_date": None,
        }
    else:
        return {
            "content": content,
            "author": author,
            "tags": tags,
            "published_date": published_date,
        }


def fetch_latest_jp_entry_with_details() -> WeeklyAWSJpDetailedUpdate | None:
    """最新記事とその詳細を取得して返す

    Args:
        None
    Returns:
        Optional[WeeklyAWSJpDetailedUpdate]: 最新記事のデータ、またはNone

    """
    entry_base = fetch_latest_jp_entry()
    if not entry_base:
        return None
    details = fetch_article_details(entry_base.url)

    # Filter out None values from details before passing to model constructor
    filtered_details = {k: v for k, v in details.items() if v is not None}

    # Combine base entry data with filtered details
    combined_data = {
        "title": entry_base.title,
        "url": entry_base.url,
        "published": entry_base.published,  # Keep original published date from feed
        "summary": entry_base.summary,
        **filtered_details,  # Add details like content, author, tags
    }

    # Use the more specific published_date from details if available
    # but keep the original 'published' key for the model
    if "published_date" in filtered_details:
        combined_data["published"] = filtered_details["published_date"]
        # Don't need to delete 'published_date' as it's not expected by the model key 'published'

    try:
        # Remove 'published_date' explicitly if it exists, as the model expects 'published'
        combined_data.pop("published_date", None)
        return WeeklyAWSJpDetailedUpdate(**combined_data)
    except TypeError as e:
        logger.error(f"Error creating WeeklyAWSJpDetailedUpdate: {e}, data: {combined_data}")
        return None
