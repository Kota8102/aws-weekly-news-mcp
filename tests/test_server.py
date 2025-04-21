from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp import Context as MCPContext
from pydantic import ConfigDict

from models import WeeklyAWSJpDetailedUpdate, WeeklyAWSJpUpdate
from server import (
    get_latest_generative_ai_jp_update_details,
    get_latest_jp_update_details,
    get_weekly_jp_updates,
)


class MockContext(MCPContext):
    """サーバー関数のテスト用モックコンテキスト。

    MCPContext を継承し、ログメッセージを内部リストに記録します。
    Pydantic モデルとして、追加の属性 (`info_messages` など) を許可します。
    """

    model_config = ConfigDict(extra="allow")

    def __init__(self) -> None:
        super().__init__()
        self.info_messages: list[str] = []
        self.warning_messages: list[str] = []
        self.error_messages: list[str] = []

    async def info(self, message: str) -> None:
        """INFO レベルのログメッセージを記録します。

        Args:
            message: 記録するログメッセージ。

        """
        self.info_messages.append(message)

    async def warning(self, message: str) -> None:
        """WARNING レベルのログメッセージを記録します。

        Args:
            message: 記録するログメッセージ。

        """
        self.warning_messages.append(message)

    async def error(self, message: str) -> None:
        """ERROR レベルのログメッセージを記録します。

        Args:
            message: 記録するログメッセージ。

        """
        self.error_messages.append(message)


NOW = datetime.now(UTC)
YESTERDAY = NOW - timedelta(days=1)
TWO_DAYS_AGO = NOW - timedelta(days=2)

MOCK_WEEKLY_UPDATES = [
    WeeklyAWSJpUpdate(
        title="週刊AWS テスト記事1",
        url="https://example.com/test1",
        published=YESTERDAY,
        summary="これはテスト記事1の要約です。",
    ),
    WeeklyAWSJpUpdate(
        title="週刊AWS テスト記事2",
        url="https://example.com/test2",
        published=TWO_DAYS_AGO,
        summary="これはテスト記事2の要約です。",
    ),
]

MOCK_LATEST_WEEKLY_DETAIL = WeeklyAWSJpDetailedUpdate(
    title="最新の週刊AWS記事",
    url="https://example.com/latest-weekly",
    published=YESTERDAY,
    summary="最新の週刊AWS記事の要約。",
    content="<h1>最新記事</h1><p>これが本文です。</p>",
)

MOCK_LATEST_GEN_AI_DETAIL = WeeklyAWSJpDetailedUpdate(
    title="最新の週刊生成AI with AWS記事",
    url="https://example.com/latest-gen-ai",
    published=YESTERDAY,
    summary="最新の週刊生成AI記事の要約。",
    content="<h1>最新生成AI記事</h1><p>これが本文です。</p>",
)


class TestGetWeeklyJpUpdates:
    """`get_weekly_jp_updates` ツール関数のテストクラス。"""

    @pytest.mark.asyncio
    @patch("server.get_recent_entries")
    async def test_get_weekly_jp_updates_success(self, mock_get_recent_entries: MagicMock) -> None:
        """`get_weekly_jp_updates` が正常に記事リストを返すケースをテストします。

        `server.get_recent_entries` をモック化し、期待される記事リストを返すように設定します。
        関数呼び出し後、戻り値とモックの呼び出し引数、ログメッセージを検証します。

        Args:
            mock_get_recent_entries: `server.get_recent_entries` のモックオブジェクト。

        """
        mock_get_recent_entries.return_value = MOCK_WEEKLY_UPDATES

        ctx = MockContext()
        days = 7
        limit = 5

        result = await get_weekly_jp_updates(ctx, days=days, limit=limit)

        # Assert list length and individual item attributes
        assert len(result) == len(MOCK_WEEKLY_UPDATES)
        for i, item in enumerate(result):
            assert isinstance(item, WeeklyAWSJpUpdate)
            assert item.title == MOCK_WEEKLY_UPDATES[i].title
            assert item.url == MOCK_WEEKLY_UPDATES[i].url
            assert item.published == MOCK_WEEKLY_UPDATES[i].published
            assert item.summary == MOCK_WEEKLY_UPDATES[i].summary

        mock_get_recent_entries.assert_called_once_with(days=days, limit=limit)
        assert f"過去 {days} 日分の週刊AWS記事を取得します (最大 {limit} 件)" in ctx.info_messages
        assert f"{len(MOCK_WEEKLY_UPDATES)} 件の記事が見つかりました。" in ctx.info_messages


class TestGetLatestJpUpdateDetails:
    """`get_latest_jp_update_details` ツール関数のテストクラス。"""

    @pytest.mark.asyncio
    @patch("server.get_latest_weekly_aws_details")
    async def test_get_latest_jp_update_details_success(self, mock_get_latest_details: MagicMock) -> None:
        """`get_latest_jp_update_details` が正常に最新記事詳細を返すケースをテストします。

        `server.get_latest_weekly_aws_details` をモック化し、期待される記事詳細を返すように設定します。
        関数呼び出し後、戻り値とモックの呼び出し、ログメッセージを検証します。

        Args:
            mock_get_latest_details: `server.get_latest_weekly_aws_details` のモックオブジェクト。

        """
        mock_get_latest_details.return_value = MOCK_LATEST_WEEKLY_DETAIL

        ctx = MockContext()
        result = await get_latest_jp_update_details(ctx)

        # Assert individual attributes of the result object
        assert isinstance(result, WeeklyAWSJpDetailedUpdate)
        assert result.title == MOCK_LATEST_WEEKLY_DETAIL.title
        assert result.url == MOCK_LATEST_WEEKLY_DETAIL.url
        assert result.published == MOCK_LATEST_WEEKLY_DETAIL.published
        assert result.summary == MOCK_LATEST_WEEKLY_DETAIL.summary
        assert result.content == MOCK_LATEST_WEEKLY_DETAIL.content

        mock_get_latest_details.assert_called_once()
        assert "最新の「週刊AWS」記事の詳細を取得します" in ctx.info_messages

    @pytest.mark.asyncio
    @patch("server.get_latest_weekly_aws_details")
    async def test_get_latest_jp_update_details_not_found(
        self,
        mock_get_latest_details: MagicMock,
    ) -> None:
        """`get_latest_jp_update_details` で最新記事が見つからないケースをテストします。

        `server.get_latest_weekly_aws_details` をモック化し、`None` を返すように設定します。
        関数呼び出し後、戻り値が `None` であること、モックの呼び出し、警告ログを検証します。

        Args:
            mock_get_latest_details: `server.get_latest_weekly_aws_details` のモックオブジェクト。

        """
        mock_get_latest_details.return_value = None

        ctx = MockContext()
        result = await get_latest_jp_update_details(ctx)

        assert result is None
        mock_get_latest_details.assert_called_once()
        assert "最新の「週刊AWS」記事の詳細を取得します" in ctx.info_messages
        assert "最新の「週刊AWS」記事が見つかりませんでした" in ctx.warning_messages


class TestGetLatestGenerativeAiJpUpdateDetails:
    """`get_latest_generative_ai_jp_update_details` ツール関数のテストクラス。"""

    @pytest.mark.asyncio
    @patch("server.get_latest_generative_ai_details")
    async def test_get_latest_gen_ai_details_success(self, mock_get_latest_gen_ai: MagicMock) -> None:
        """`get_latest_generative_ai_jp_update_details` が正常に最新記事詳細を返すケースをテストします。

        `server.get_latest_generative_ai_details` をモック化し、期待される記事詳細を返すように設定します。
        関数呼び出し後、戻り値とモックの呼び出し、ログメッセージを検証します。

        Args:
            mock_get_latest_gen_ai: `server.get_latest_generative_ai_details` のモックオブジェクト。

        """
        mock_get_latest_gen_ai.return_value = MOCK_LATEST_GEN_AI_DETAIL

        ctx = MockContext()
        result = await get_latest_generative_ai_jp_update_details(ctx)

        assert isinstance(result, WeeklyAWSJpDetailedUpdate)
        assert result.title == MOCK_LATEST_GEN_AI_DETAIL.title
        assert result.url == MOCK_LATEST_GEN_AI_DETAIL.url
        assert result.published == MOCK_LATEST_GEN_AI_DETAIL.published
        assert result.summary == MOCK_LATEST_GEN_AI_DETAIL.summary
        assert result.content == MOCK_LATEST_GEN_AI_DETAIL.content

        mock_get_latest_gen_ai.assert_called_once()
        assert "最新の「週刊生成AI with AWS」記事の詳細を取得します" in ctx.info_messages

    @pytest.mark.asyncio
    @patch("server.get_latest_generative_ai_details")
    async def test_get_latest_gen_ai_details_not_found(self, mock_get_latest_gen_ai: MagicMock) -> None:
        """`get_latest_generative_ai_jp_update_details` で最新記事が見つからないケースをテストします。

        `server.get_latest_generative_ai_details` をモック化し、`None` を返すように設定します。
        関数呼び出し後、戻り値が `None` であること、モックの呼び出し、警告ログを検証します。

        Args:
            mock_get_latest_gen_ai: `server.get_latest_generative_ai_details` のモックオブジェクト。

        """
        mock_get_latest_gen_ai.return_value = None

        ctx = MockContext()
        result = await get_latest_generative_ai_jp_update_details(ctx)

        assert result is None
        mock_get_latest_gen_ai.assert_called_once()
        assert "最新の「週刊生成AI with AWS」記事の詳細を取得します" in ctx.info_messages
        assert "最新の「週刊生成AI with AWS」記事が見つかりませんでした" in ctx.warning_messages
