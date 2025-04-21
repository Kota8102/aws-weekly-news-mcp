from datetime import UTC, datetime, timedelta

import pytest
from feedparser import FeedParserDict
from pytest_mock import MockerFixture

from models import WeeklyAWSJpDetailedUpdate, WeeklyAWSJpUpdate
from util import (
    _extract_content_string,
    get_feed_entries,
    get_latest_generative_ai_details,
    get_latest_weekly_aws_details,
    get_recent_entries,
)

# --- Test Data Fixtures ---


@pytest.fixture
def mock_feed_entry_base() -> dict:
    """基本的なフィードエントリの辞書を返すフィクスチャ。"""
    return {
        "title": "Test Title",
        "link": "http://example.com/test",
        "published": "Mon, 01 Apr 2024 10:00:00 +0000",
        "published_parsed": (2024, 4, 1, 10, 0, 0, 0, 91, 0),  # UTC
        "summary": "Test Summary",
        "content": [{"value": "Test Content"}],
    }


@pytest.fixture
def mock_feed_data(
    mock_feed_entry_base: dict,
    mock_datetime_now: datetime,
) -> FeedParserDict:
    """テスト用の FeedParserDict オブジェクトを返すフィクスチャ。"""
    # mock_datetime_now フィクスチャからの固定時刻を使用
    fixed_now = mock_datetime_now
    entry1_time = fixed_now - timedelta(days=1)
    entry2_time = fixed_now - timedelta(days=5)
    entry3_time = fixed_now - timedelta(days=10)  # cutoff対象

    entry1 = mock_feed_entry_base.copy()
    entry1.update(
        {
            "title": "週刊AWS - 2024/04/01",
            "link": "http://example.com/weekly1",
            "published_parsed": entry1_time.timetuple(),
            "published": entry1_time.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        },
    )

    entry2 = mock_feed_entry_base.copy()
    entry2.update(
        {
            "title": "週刊生成AI with AWS - 2024/03/25",
            "link": "http://example.com/genai1",
            "published_parsed": entry2_time.timetuple(),
            "published": entry2_time.strftime("%a, %d %b %Y %H:%M:%S +0000"),
            # content が属性アクセス用に FeedParserDict を使用することを確認
            "content": [FeedParserDict({"value": "GenAI Content"})],
        },
    )

    entry3 = mock_feed_entry_base.copy()
    entry3.update(
        {
            "title": "週刊AWS - 2024/03/18",
            "link": "http://example.com/weekly2",
            "published_parsed": entry3_time.timetuple(),
            "published": entry3_time.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        },
    )

    feed = FeedParserDict()
    feed.bozo = 0  # 正常なフィード
    feed.entries = [
        FeedParserDict(entry1),
        FeedParserDict(entry2),
        FeedParserDict(entry3),
    ]
    return feed


@pytest.fixture
def mock_feed_data_bozo() -> FeedParserDict:
    """パースエラーがある FeedParserDict オブジェクトを返すフィクスチャ。"""
    feed = FeedParserDict()
    feed.bozo = 1
    feed.bozo_exception = Exception("Test parse error")
    feed.entries = []
    return feed


@pytest.fixture
def mock_feed_data_empty() -> FeedParserDict:
    """エントリが空の FeedParserDict オブジェクトを返すフィクスチャ。"""
    feed = FeedParserDict()
    feed.bozo = 0
    feed.entries = []
    return feed


# --- Test Functions ---

# ここから各関数のテストを記述していきます
# --- Tests for get_feed_entries ---


def test_get_feed_entries_success(mocker: MockerFixture, mock_feed_data: FeedParserDict) -> None:
    """有効なフィードを正常にパースできることをテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。

    """
    mock_parse = mocker.patch("util.feedparser.parse", return_value=mock_feed_data)
    mocker.patch("util.logger")

    feed = get_feed_entries()

    assert feed == mock_feed_data
    mock_parse.assert_called_once_with("https://aws.amazon.com/jp/blogs/news/tag/%E9%80%B1%E5%88%8Aaws/feed/")


def test_get_feed_entries_bozo(mocker: MockerFixture, mock_feed_data_bozo: FeedParserDict) -> None:
    """パースエラーのあるフィード(bozo=1)を適切に処理できることをテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data_bozo: bozoフラグが設定されたモックフィードデータを提供するフィクスチャ。

    """
    mock_parse = mocker.patch("util.feedparser.parse", return_value=mock_feed_data_bozo)
    mock_logger_warning = mocker.patch("util.logger.warning")

    feed = get_feed_entries()

    assert feed == mock_feed_data_bozo
    mock_parse.assert_called_once_with("https://aws.amazon.com/jp/blogs/news/tag/%E9%80%B1%E5%88%8Aaws/feed/")
    mock_logger_warning.assert_called_once_with(
        f"RSSパースエラー: {mock_feed_data_bozo.bozo_exception}",
    )


# --- Tests for _extract_content_string ---


@pytest.mark.parametrize(
    ("content_data", "expected_output", "expected_log"),  # 名前にはタプルを使用
    [
        # テストケース 1: content_data が None
        (None, None, None),
        # テストケース 2: content_data が空文字列
        ("", None, None),
        # テストケース 3: content_data が空リスト
        ([], None, None),
        # テストケース 4: content_data が有効な content オブジェクトを持つリスト
        ([FeedParserDict({"value": "Valid Content"})], "Valid Content", None),
        # テストケース 5: content_data が複数の content オブジェクトを持つリスト (最初の要素を取得)
        (
            [FeedParserDict({"value": "First Content"}), FeedParserDict({"value": "Second Content"})],
            "First Content",
            None,
        ),
        # テストケース 6: content_data がリストで、最初の要素が文字列でない値を持つ
        ([FeedParserDict({"value": 123})], None, "content[0].value が文字列ではありません: <class 'int'>"),
        # テストケース 7: content_data がリストで、最初の要素に 'value' 属性がない
        (
            [FeedParserDict({"other_key": "Some data"})],
            None,
            "content[0].value が文字列ではありません: <class 'NoneType'>",
        ),  # getattr は None を返す
        # テストケース 8: content_data が単純な文字列
        ("Simple String Content", "Simple String Content", None),
        # テストケース 9: content_data が予期しない型 (整数)
        (12345, None, "予期しない content の型: <class 'int'>"),
        # テストケース 10: content_data が予期しない型 (辞書)
        ({"value": "dict value"}, None, "予期しない content の型: <class 'dict'>"),
    ],
    ids=[
        "None input",
        "Empty string input",
        "Empty list input",
        "List with valid content",
        "List with multiple contents",
        "List with non-string value",
        "List item without value attr",
        "Simple string input",
        "Integer input",
        "Dict input",
    ],
)
def test_extract_content_string(
    mocker: MockerFixture,
    content_data: object,
    expected_output: str | None,
    expected_log: str | None,
) -> None:
    """様々な入力タイプと構造に対する_extract_content_stringの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        content_data: 関数への入力データ。
        expected_output: 期待される文字列出力またはNone。
        expected_log: 期待される警告ログメッセージまたはNone。

    """
    mock_logger_warning = mocker.patch("util.logger.warning")

    result = _extract_content_string(content_data)

    assert result == expected_output
    if expected_log:
        mock_logger_warning.assert_called_once_with(expected_log)
    else:
        mock_logger_warning.assert_not_called()


# --- Tests for get_recent_entries ---


@pytest.fixture
def mock_datetime_now(mocker: MockerFixture) -> datetime:
    """datetime.now をモックして固定の UTC 時刻を返すフィクスチャ。

    Args:
        mocker: pytest-mockフィクスチャ。

    Returns:
        固定のUTC時刻(2024-04-02 12:00:00+00:00)。

    """
    fixed_now = datetime(2024, 4, 2, 12, 0, 0, tzinfo=UTC)
    # パッチ適用前に元の datetime クラスへの参照を保持
    original_datetime = datetime

    # モックされた datetime クラスの side_effect を定義
    def datetime_side_effect(*args: object, **kwargs: object) -> datetime:
        # datetime(...) が呼び出された場合、元のクラスを使用
        return original_datetime(*args, **kwargs)

    # util モジュールでインポートされた datetime クラスをパッチ
    mock_dt = mocker.patch("util.datetime", autospec=True)
    # モックされたクラスの now() メソッドを設定
    mock_dt.now.return_value = fixed_now
    # コンストラクタ呼び出し(モック自体が呼び出された場合)の side_effect を設定
    mock_dt.side_effect = datetime_side_effect

    return fixed_now  # テスト用に固定時刻を返す


def test_get_recent_entries_default(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
    mock_datetime_now: datetime,
) -> None:
    """デフォルトの日数(7)と件数(20)でget_recent_entriesをテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。
        mock_datetime_now: datetime.nowをモックするフィクスチャ。

    """
    mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    cutoff_date = mock_datetime_now - timedelta(days=7)  # 2024-03-26 12:00:00+00:00

    entries = get_recent_entries()  # デフォルト days=7, limit=20

    # mock_datetime_now (2024-04-02) とエントリ時刻に基づく:
    # entry1: 2024-04-01 (7日以内)
    # entry2: 2024-03-28 (7日以内)
    # entry3: 2024-03-23 (7日外)
    assert len(entries) == 2  # noqa: PLR2004
    assert all(isinstance(e, WeeklyAWSJpUpdate) for e in entries)
    assert entries[0].title == "週刊AWS - 2024/04/01"
    assert entries[1].title == "週刊生成AI with AWS - 2024/03/25"
    assert entries[0].published >= cutoff_date
    assert entries[1].published >= cutoff_date


def test_get_recent_entries_custom_days(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
    mock_datetime_now: datetime,
) -> None:
    """カスタム日数でget_recent_entriesをテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。
        mock_datetime_now: datetime.nowをモックするフィクスチャ。

    """
    mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    custom_days = 3
    cutoff_date = mock_datetime_now - timedelta(days=custom_days)  # 2024-03-30 12:00:00+00:00

    entries = get_recent_entries(days=custom_days)

    # mock_datetime_now (2024-04-02) とエントリ時刻に基づく:
    # entry1: 2024-04-01 (3日以内)
    # entry2: 2024-03-28 (3日外)
    # entry3: 2024-03-23 (3日外)
    assert len(entries) == 1
    assert entries[0].title == "週刊AWS - 2024/04/01"
    assert entries[0].published >= cutoff_date


def test_get_recent_entries_custom_limit(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """カスタム件数制限でget_recent_entriesをテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。
        mock_datetime_now: datetime.nowをモックするフィクスチャ。

    """
    mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    custom_limit = 1

    # デフォルト日数 (7) を使用
    entries = get_recent_entries(limit=custom_limit)

    assert len(entries) == 1
    # フィクスチャではフィードは新しい順に並んでいる
    assert entries[0].title == "週刊AWS - 2024/04/01"


def test_get_recent_entries_empty_feed(
    mocker: MockerFixture,
    mock_feed_data_empty: FeedParserDict,
) -> None:
    """フィードにエントリがない場合のget_recent_entriesの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data_empty: 空のフィードを提供するフィクスチャ。
        mock_datetime_now: datetime.nowをモックするフィクスチャ。

    """
    mocker.patch("util.get_feed_entries", return_value=mock_feed_data_empty)

    entries = get_recent_entries()

    assert len(entries) == 0


def test_get_recent_entries_no_recent_entries(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """指定日数内にエントリがない場合のget_recent_entriesの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。
        mock_datetime_now: datetime.nowをモックするフィクスチャ。

    """
    mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    very_short_days = 0  # Effectively only today, none match

    entries = get_recent_entries(days=very_short_days)

    # mock_datetime_now (2024-04-02) に基づき、今日のエントリはない
    assert len(entries) == 0


# --- Tests for get_latest_weekly_aws_details ---


def test_get_latest_weekly_aws_details_success(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """get_latest_weekly_aws_detailsが正しく最新のエントリを取得できることをテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。

    """
    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    # _extract_content_string をモックして期待されるエントリに特定の値を返すようにする
    mock_extract = mocker.patch("util._extract_content_string", return_value="Extracted Weekly Content")
    mocker.patch("util.logger")  # 成功ケースでは必要ない限りログをチェックしない

    details = get_latest_weekly_aws_details()

    assert details is not None
    assert isinstance(details, WeeklyAWSJpDetailedUpdate)
    # mock_feed_data 内の最新の「週刊AWS」(「週刊生成AI」ではない)は entry1
    expected_entry = mock_feed_data.entries[0]
    assert details.title == expected_entry.title
    assert str(details.url) == expected_entry.link  # 文字列として比較
    assert details.published == datetime(*expected_entry.published_parsed[:6], tzinfo=UTC)
    assert details.summary == expected_entry.summary
    assert details.content == "Extracted Weekly Content"
    mock_get_feed.assert_called_once()
    # _extract_content_string が正しいエントリの content で呼び出されたことを確認
    mock_extract.assert_called_once_with(expected_entry.content)


def test_get_latest_weekly_aws_details_no_weekly_entry(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """「週刊AWS」エントリが存在しない場合のget_latest_weekly_aws_detailsの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。

    """
    # 標準の「週刊AWS」エントリを削除するようにフィードデータを変更
    feed_without_weekly = FeedParserDict()
    feed_without_weekly.bozo = 0
    feed_without_weekly.entries = [
        e for e in mock_feed_data.entries if "週刊AWS" not in e.title or "週刊生成AI" in e.title
    ]  # GenAI または他のエントリのみ保持
    assert len(feed_without_weekly.entries) == 1

    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=feed_without_weekly)
    mock_logger_info = mocker.patch("util.logger.info")

    details = get_latest_weekly_aws_details()

    assert details is None
    mock_get_feed.assert_called_once()
    mock_logger_info.assert_called_once_with("最新の「週刊AWS」記事が見つかりませんでした。")


def test_get_latest_weekly_aws_details_empty_feed(
    mocker: MockerFixture,
    mock_feed_data_empty: FeedParserDict,
) -> None:
    """フィードが空の場合のget_latest_weekly_aws_detailsの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data_empty: 空のフィードを提供するフィクスチャ。

    """
    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=mock_feed_data_empty)
    mocker.patch("util.logger")  # ここでは特定のログは期待せず、エラーを防ぐだけ

    details = get_latest_weekly_aws_details()

    assert details is None
    mock_get_feed.assert_called_once()


def test_get_latest_weekly_aws_details_extract_returns_none(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """_extract_content_stringがNoneを返す場合のget_latest_weekly_aws_detailsの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。

    """
    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    mock_extract = mocker.patch(
        "util._extract_content_string",
        return_value=None,
    )  # コンテンツ抽出失敗をシミュレート
    mocker.patch("util.logger")

    details = get_latest_weekly_aws_details()

    assert details is not None
    assert isinstance(details, WeeklyAWSJpDetailedUpdate)
    # 詳細情報は返されるべきだが、content は None になる
    assert details.content is None
    mock_get_feed.assert_called_once()
    mock_extract.assert_called_once()


def test_get_latest_weekly_aws_details_exception(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """処理中に例外が発生した場合のget_latest_weekly_aws_detailsの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。

    """
    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    # max() 呼び出し中または属性アクセス中にエラーをシミュレート
    mocker.patch("builtins.max", side_effect=ValueError("Test Exception"))
    mock_logger_error = mocker.patch("util.logger.error")

    details = get_latest_weekly_aws_details()

    assert details is None
    mock_get_feed.assert_called_once()
    mock_logger_error.assert_called_once()
    # ログメッセージに例外タイプ/メッセージが含まれていることを確認
    args, kwargs = mock_logger_error.call_args
    assert "最新の「週刊AWS」記事詳細の処理中にエラー" in args[0]
    assert "Test Exception" in args[0]
    assert kwargs.get("exc_info") is True


# --- Tests for get_latest_generative_ai_details ---


def test_get_latest_generative_ai_details_success(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """get_latest_generative_ai_detailsが正しく最新のエントリを取得できることをテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。

    """
    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    mock_extract = mocker.patch("util._extract_content_string", return_value="Extracted GenAI Content")
    mocker.patch("util.logger")

    details = get_latest_generative_ai_details()

    assert details is not None
    assert isinstance(details, WeeklyAWSJpDetailedUpdate)
    # The latest "週刊生成AI" in mock_feed_data is entry2
    expected_entry = mock_feed_data.entries[1]
    assert details.title == expected_entry.title
    assert str(details.url) == expected_entry.link  # Compare as strings
    assert details.published == datetime(*expected_entry.published_parsed[:6], tzinfo=UTC)
    assert details.summary == expected_entry.summary
    assert details.content == "Extracted GenAI Content"
    mock_get_feed.assert_called_once()
    mock_extract.assert_called_once_with(expected_entry.content)


def test_get_latest_generative_ai_details_no_genai_entry(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """「週刊生成AI」エントリが存在しない場合のget_latest_generative_ai_detailsの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。

    """
    # Modify feed data to remove "週刊生成AI" entries
    feed_without_genai = FeedParserDict()
    feed_without_genai.bozo = 0
    feed_without_genai.entries = [e for e in mock_feed_data.entries if "週刊生成AI" not in e.title]
    assert len(feed_without_genai.entries) == 2  # noqa: PLR2004

    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=feed_without_genai)
    mock_logger_info = mocker.patch("util.logger.info")

    details = get_latest_generative_ai_details()

    assert details is None
    mock_get_feed.assert_called_once()
    mock_logger_info.assert_called_once_with("最新の「週刊生成AI with AWS」記事が見つかりませんでした。")


def test_get_latest_generative_ai_details_empty_feed(
    mocker: MockerFixture,
    mock_feed_data_empty: FeedParserDict,
) -> None:
    """フィードが空の場合のget_latest_generative_ai_detailsの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data_empty: 空のフィードを提供するフィクスチャ。

    """
    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=mock_feed_data_empty)
    mocker.patch("util.logger")

    details = get_latest_generative_ai_details()

    assert details is None
    mock_get_feed.assert_called_once()


def test_get_latest_generative_ai_details_extract_returns_none(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """_extract_content_stringがNoneを返す場合のget_latest_generative_ai_detailsの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。

    """
    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    mock_extract = mocker.patch("util._extract_content_string", return_value=None)
    mocker.patch("util.logger")

    details = get_latest_generative_ai_details()

    assert details is not None
    assert isinstance(details, WeeklyAWSJpDetailedUpdate)
    assert details.content is None  # Content should be None
    mock_get_feed.assert_called_once()
    mock_extract.assert_called_once()


def test_get_latest_generative_ai_details_exception(
    mocker: MockerFixture,
    mock_feed_data: FeedParserDict,
) -> None:
    """処理中に例外が発生した場合のget_latest_generative_ai_detailsの動作をテストします。

    Args:
        mocker: pytest-mockフィクスチャ。
        mock_feed_data: モックフィードデータを提供するフィクスチャ。

    """
    mock_get_feed = mocker.patch("util.get_feed_entries", return_value=mock_feed_data)
    mocker.patch("builtins.max", side_effect=TypeError("Another Test Exception"))  # Simulate different error
    mock_logger_error = mocker.patch("util.logger.error")

    details = get_latest_generative_ai_details()

    assert details is None
    mock_get_feed.assert_called_once()
    mock_logger_error.assert_called_once()
    args, kwargs = mock_logger_error.call_args
    assert "最新の「週刊生成AI with AWS」記事詳細の処理中にエラー" in args[0]
    assert "Another Test Exception" in args[0]
    assert kwargs.get("exc_info") is True
