from datetime import datetime

from pydantic import AnyUrl, BaseModel


class WeeklyAWSJpUpdate(BaseModel):
    title: str
    url: AnyUrl
    published: datetime
    summary: str | None = None


class WeeklyAWSJpDetailedUpdate(BaseModel):
    title: str
    url: AnyUrl
    published: datetime
    summary: str | None = None
    content: str | None = None
