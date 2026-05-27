from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalysisRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic_id: UUID
    date_from: datetime
    date_to: datetime
    source_ids: list[UUID] = Field(default_factory=list)


class TopicResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    keywords: list[str]
    is_active: bool


class TopicCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    keywords: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if len(normalized) < 2:
            raise ValueError("name must contain at least 2 non-space characters")
        return normalized

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        normalized = [
            item
            for item in (" ".join(keyword.strip().split()) for keyword in value)
            if item
        ]
        return list(dict.fromkeys(normalized))


class TopicUpdateRequest(BaseModel):
    keywords: list[str]

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, value: list[str]) -> list[str]:
        normalized = [
            item
            for item in (" ".join(keyword.strip().split()) for keyword in value)
            if item
        ]
        return list(dict.fromkeys(normalized))


class SourceResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    base_url: str | None
    is_active: bool


class SourceResultResponse(BaseModel):
    source_id: UUID
    source_name: str
    status: str
    items_found: int
    items_saved: int
    metrics: dict
    error_message: str | None = None


class MentionResponse(BaseModel):
    id: UUID
    source_id: UUID
    source_name: str
    title: str | None
    text: str | None
    url: str | None
    published_at: datetime | None
    views: int | None
    likes: int | None
    comments: int | None
    reposts: int | None
    rating: Decimal | None
    sentiment: str | None


class TrendPointResponse(BaseModel):
    source_id: UUID
    source_name: str
    metric_at: datetime
    keyword: str | None
    region: str | None
    value: Decimal
    scale: str | None
    metrics: dict


class AnalysisMetricsResponse(BaseModel):
    total_texts: int
    positive_count: int
    neutral_count: int
    negative_count: int
    unknown_count: int
    joy_count: int
    irritation_count: int
    fear_count: int
    trust_count: int
    surprise_count: int
    anger_count: int
    sentiment_score: Decimal | None
    barometer_value: Decimal | None
    barometer_label: str | None
    summary_short: str | None
    summary_detailed: str | None


class AnalysisRunResponse(BaseModel):
    id: UUID
    topic: TopicResponse
    status: str
    date_from: datetime
    date_to: datetime
    error_message: str | None
    metrics: AnalysisMetricsResponse | None
    source_results: list[SourceResultResponse]
    mentions: list[MentionResponse]
    trend_points: list[TrendPointResponse]


class DailyMentionPoint(BaseModel):
    date: str
    mentions_count: int
    views_sum: int
    likes_sum: int
    comments_sum: int
    reposts_sum: int
    positive: int
    neutral: int
    negative: int
    mixed: int
    unknown: int


class SentimentPoint(BaseModel):
    sentiment: str
    count: int


class EmotionPoint(BaseModel):
    emotion: str
    label: str
    count: int
    percent: float


class ChartDataResponse(BaseModel):
    trend_points: list[TrendPointResponse]
    mentions_by_day: list[DailyMentionPoint]
    sentiment: list[SentimentPoint]
    emotions: list[EmotionPoint]
