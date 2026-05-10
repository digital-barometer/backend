from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(slots=True)
class ParsedMention:
    external_id: str | None
    title: str | None
    text: str | None
    url: str | None
    published_at: datetime | None
    author_name: str | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    reposts: int | None = None
    rating: Decimal | None = None
    region: str | None = None
    source_metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class ParsedTrendPoint:
    metric_at: datetime
    value: Decimal
    keyword: str | None = None
    region: str | None = None
    scale: str | None = None
    metrics: dict = field(default_factory=dict)


@dataclass(slots=True)
class ConnectorResult:
    raw_payload: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    mentions: list[ParsedMention] = field(default_factory=list)
    trend_points: list[ParsedTrendPoint] = field(default_factory=list)


class SourceConnector(Protocol):
    async def fetch(self, query: str, date_from: datetime, date_to: datetime) -> ConnectorResult:
        ...
