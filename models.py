from datetime import datetime

from pydantic import AnyUrl, BaseModel


class WeeklyAWSJpUpdate(BaseModel):
    title: str
    url: AnyUrl
    published: datetime
    summary: str | None


class WeeklyAWSJpDetailedUpdate(WeeklyAWSJpUpdate):
    content: str | None = None
    author: str | None = None
    tags: list[str] = []
    published_date: datetime | None = None
