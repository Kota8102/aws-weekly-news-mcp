from datetime import UTC, datetime

from pydantic import AnyUrl

from models import WeeklyAWSJpDetailedUpdate, WeeklyAWSJpUpdate


class TestWeeklyAWSJpUpdate:
    """Tests for WeeklyAWSJpUpdate model."""

    def test_weekly_aws_jp_update_without_optional_fields(self) -> None:
        """Test creation of WeeklyAWSJpUpdate"""
        now = datetime.now(UTC)
        update = WeeklyAWSJpUpdate(
            title="週刊AWSニュース 2024/07/22",
            url=AnyUrl("https://aws.amazon.com/jp/blogs/news/weekly-aws-news-20240722/"),
            published=now,
            summary="test",
        )
        assert update.title == "週刊AWSニュース 2024/07/22"
        assert str(update.url) == "https://aws.amazon.com/jp/blogs/news/weekly-aws-news-20240722/"
        assert update.published == now
        assert update.summary == "test"

    def test_weekly_aws_jp_update_without_summary(self) -> None:
        """Test creation of WeeklyAWSJpUpdate without optional summary."""
        now = datetime.now(UTC)
        update = WeeklyAWSJpUpdate(
            title="週刊AWSニュース 2024/07/22",
            url=AnyUrl("https://aws.amazon.com/jp/blogs/news/weekly-aws-news-20240722/"),
            published=now,
        )
        assert update.title == "週刊AWSニュース 2024/07/22"
        assert str(update.url) == "https://aws.amazon.com/jp/blogs/news/weekly-aws-news-20240722/"
        assert update.published == now
        assert update.summary is None


class TestWeeklyAWSJpDetailedUpdate:
    """Tests for WeeklyAWSJpDetailedUpdate model."""

    def test_detailed_update(self) -> None:
        """Test creation of WeeklyAWSJpDetailedUpdate"""
        now = datetime.now(UTC)
        update = WeeklyAWSJpDetailedUpdate(
            title="詳細な週刊AWSニュース 2024/07/22",
            url=AnyUrl("https://aws.amazon.com/jp/blogs/news/detailed-weekly-aws-news-20240722/"),
            published=now,
            summary="test",
            content="test",
        )
        assert update.title == "詳細な週刊AWSニュース 2024/07/22"
        assert str(update.url) == "https://aws.amazon.com/jp/blogs/news/detailed-weekly-aws-news-20240722/"
        assert update.published == now
        assert update.summary == "test"
        assert update.content == "test"

    def test_detailed_update_without_optional_fields(self) -> None:
        """Test creation of WeeklyAWSJpDetailedUpdate without optional fields."""
        now = datetime.now(UTC)
        update = WeeklyAWSJpDetailedUpdate(
            title="詳細な週刊AWSニュース 2024/07/22",
            url=AnyUrl("https://aws.amazon.com/jp/blogs/news/detailed-weekly-aws-news-20240722/"),
            published=now,
        )
        assert update.title == "詳細な週刊AWSニュース 2024/07/22"
        assert str(update.url) == "https://aws.amazon.com/jp/blogs/news/detailed-weekly-aws-news-20240722/"
        assert update.published == now
        assert update.summary is None
        assert update.content is None
