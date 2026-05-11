from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import re
from uuid import UUID

from app.connectors.base import ConnectorResult, ParsedMention, ParsedTrendPoint
from app.connectors.factory import ConnectorFactory
from app.services.sentiment import SentimentAnalyzer
from db.enums import AnalysisStatus
from db.models import Mention, Source, SourceResult, TrendPoint


@dataclass(slots=True)
class SourceFetchArtifacts:
    source_result: SourceResult
    mentions: list[Mention]
    trend_points: list[TrendPoint]


class SourceFetchService:
    def __init__(
        self,
        connector_factory: ConnectorFactory,
        sentiment_analyzer: SentimentAnalyzer,
    ) -> None:
        self._connector_factory = connector_factory
        self._sentiment_analyzer = sentiment_analyzer

    async def fetch(
        self,
        analysis_run_id: UUID,
        topic_name: str,
        source: Source,
        source_result: SourceResult,
        query: str,
        date_from: datetime,
        date_to: datetime,
    ) -> SourceFetchArtifacts:
        try:
            connector = self._connector_factory.create(source)
            result = await connector.fetch(query, date_from, date_to)
            mentions = [
                to_mention(analysis_run_id, source.id, item)
                for item in result.mentions
            ]
            await self._sentiment_analyzer.apply(topic_name, mentions)

            trend_points = [
                to_trend_point(analysis_run_id, source.id, item)
                for item in result.trend_points
            ]
            mark_source_success(source_result, result, mentions, trend_points)
            return SourceFetchArtifacts(source_result, mentions, trend_points)
        except Exception as exc:
            mark_source_failed(source_result, exc)
            return SourceFetchArtifacts(source_result, [], [])


def mark_source_success(
    source_result: SourceResult,
    result: ConnectorResult,
    mentions: list[Mention],
    trend_points: list[TrendPoint],
) -> None:
    source_result.status = AnalysisStatus.SUCCESS
    source_result.raw_payload = result.raw_payload
    source_result.metrics = result.metrics
    source_result.items_found = len(result.mentions) + len(result.trend_points)
    source_result.items_saved = len(mentions) + len(trend_points)
    source_result.finished_at = datetime.now(UTC)


def mark_source_failed(source_result: SourceResult, exc: Exception) -> None:
    source_result.status = AnalysisStatus.FAILED
    source_result.error_message = redact_sensitive_text(_exception_message(exc))[:1000]
    source_result.finished_at = datetime.now(UTC)


def redact_sensitive_text(value: str) -> str:
    redacted = re.sub(
        r"\b(api[_-]?key|apikey|x-api-key)(\s*[=:]\s*)[^\s&;,]+",
        lambda match: f"{match.group(1)}{match.group(2)}***",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"\b(authorization)(\s*:\s*)[^\n\r,;]+",
        lambda match: f"{match.group(1)}{match.group(2)}***",
        redacted,
        flags=re.IGNORECASE,
    )


def _exception_message(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__


def to_mention(analysis_run_id: UUID, source_id: UUID, item: ParsedMention) -> Mention:
    content_hash = sha256(
        f"{item.external_id}:{item.url}:{item.title}:{item.text}".encode()
    ).hexdigest()
    return Mention(
        analysis_run_id=analysis_run_id,
        source_id=source_id,
        external_id=item.external_id,
        url=item.url,
        title=item.title,
        text=item.text,
        published_at=item.published_at,
        author_name=item.author_name,
        views=item.views,
        likes=item.likes,
        comments=item.comments,
        reposts=item.reposts,
        rating=item.rating,
        region=item.region,
        source_metadata=item.source_metadata,
        content_hash=content_hash,
    )


def to_trend_point(analysis_run_id: UUID, source_id: UUID, item: ParsedTrendPoint) -> TrendPoint:
    point_hash = sha256(
        f"{item.metric_at.isoformat()}:{item.keyword}:{item.region}:{item.value}".encode()
    ).hexdigest()
    return TrendPoint(
        analysis_run_id=analysis_run_id,
        source_id=source_id,
        metric_at=item.metric_at,
        keyword=item.keyword,
        region=item.region,
        value=item.value,
        scale=item.scale,
        metrics=item.metrics,
        point_hash=point_hash,
    )
