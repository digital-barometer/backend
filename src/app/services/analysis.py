import asyncio
from collections import Counter, defaultdict
from datetime import UTC, datetime
from uuid import UUID

from app.repositories.analysis import AnalysisRepository
from app.services.metrics import final_status
from app.services.search_plan import QueryBuilder, SearchPlan, SourceSearchQuery
from app.services.sources import SourceService
from app.services.source_fetch import SourceFetchArtifacts, SourceFetchService
from app.services.summary import SummaryService
from app.services.topics import TopicService
from db.enums import AnalysisStatus
from db.models import AnalysisMetric, AnalysisRun, Mention, Source, SourceResult, Topic, TrendPoint


class AnalysisService:
    def __init__(
        self,
        analysis_repository: AnalysisRepository,
        topic_service: TopicService,
        source_service: SourceService,
        summary_service: SummaryService,
        query_builder: QueryBuilder,
        source_fetch_service: SourceFetchService,
    ) -> None:
        self._analysis_repository = analysis_repository
        self._topic_service = topic_service
        self._source_service = source_service
        self._summary_service = summary_service
        self._query_builder = query_builder
        self._source_fetch_service = source_fetch_service

    async def run(
        self,
        query: str,
        keywords: list[str],
        date_from: datetime,
        date_to: datetime,
        source_ids: list[UUID],
    ) -> AnalysisRun:
        self._validate_period(date_from, date_to)
        topic = await self._topic_service.get_or_create(query)
        sources = await self._resolve_sources(source_ids)
        search_plan = self._query_builder.build(query, keywords, sources)
        analysis_run = await self._create_run(topic, date_from, date_to, sources)

        saved_mentions: list[Mention] = []
        saved_trends: list[TrendPoint] = []
        source_results: list[SourceResult] = []

        started_sources = await self._start_source_results(analysis_run.id, search_plan)
        source_tasks = [
            self._process_source(
                analysis_run=analysis_run,
                source_query=source_query,
                source_result=source_result,
                search_plan=search_plan,
                date_from=date_from,
                date_to=date_to,
            )
            for source_query, source_result in started_sources
        ]

        for artifacts in await asyncio.gather(*source_tasks):
            source_results.append(artifacts.source_result)
            saved_mentions.extend(artifacts.mentions)
            saved_trends.extend(artifacts.trend_points)

        self._analysis_repository.add_mentions(saved_mentions)
        self._analysis_repository.add_trend_points(saved_trends)
        await self._save_metrics(analysis_run, saved_mentions, saved_trends)
        analysis_run.status = final_status(source_results)
        analysis_run.finished_at = datetime.now(UTC)

        loaded = await self.get(analysis_run.id)
        if loaded is None:
            raise RuntimeError("analysis run was not saved")
        return loaded

    async def get(self, analysis_id: UUID) -> AnalysisRun | None:
        return await self._analysis_repository.get_with_details(analysis_id)

    async def charts(self, analysis_id: UUID) -> dict:
        analysis_run = await self.get(analysis_id)
        if analysis_run is None:
            raise LookupError("analysis run not found")

        mentions_by_day: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "mentions_count": 0,
                "views_sum": 0,
                "likes_sum": 0,
                "comments_sum": 0,
                "reposts_sum": 0,
            }
        )
        sentiment_counter: Counter[str] = Counter()

        for mention in analysis_run.mentions:
            if mention.published_at is None:
                continue
            day = mention.published_at.date().isoformat()
            bucket = mentions_by_day[day]
            bucket["mentions_count"] += 1
            bucket["views_sum"] += mention.views or 0
            bucket["likes_sum"] += mention.likes or 0
            bucket["comments_sum"] += mention.comments or 0
            bucket["reposts_sum"] += mention.reposts or 0
            if mention.sentiment:
                sentiment_counter[mention.sentiment.value] += 1

        return {
            "trend_points": analysis_run.trend_points,
            "mentions_by_day": [
                {"date": day, **metrics}
                for day, metrics in sorted(mentions_by_day.items())
            ],
            "sentiment": [
                {"sentiment": sentiment, "count": count}
                for sentiment, count in sentiment_counter.items()
            ],
        }

    async def _resolve_sources(self, source_ids: list[UUID]) -> list[Source]:
        sources = (
            await self._source_service.get_by_ids(source_ids)
            if source_ids
            else await self._source_service.list_active()
        )
        found_ids = {source.id for source in sources}
        missing_ids = [str(source_id) for source_id in source_ids if source_id not in found_ids]
        if missing_ids:
            raise ValueError(f"Inactive or unknown sources: {', '.join(missing_ids)}")
        return sources

    async def _create_run(
        self,
        topic: Topic,
        date_from: datetime,
        date_to: datetime,
        sources: list[Source],
    ) -> AnalysisRun:
        analysis_run = AnalysisRun(
            topic=topic,
            status=AnalysisStatus.RUNNING,
            date_from=date_from,
            date_to=date_to,
            params={"source_ids": [str(source.id) for source in sources]},
        )
        return await self._analysis_repository.add_run(analysis_run)

    async def _start_source_results(
        self,
        analysis_run_id: UUID,
        search_plan: SearchPlan,
    ) -> list[tuple[SourceSearchQuery, SourceResult]]:
        return [
            (
                source_query,
                await self._start_source_result(analysis_run_id, source_query.source.id),
            )
            for source_query in search_plan.source_queries
        ]

    async def _process_source(
        self,
        analysis_run: AnalysisRun,
        source_query: SourceSearchQuery,
        source_result: SourceResult,
        search_plan: SearchPlan,
        date_from: datetime,
        date_to: datetime,
    ) -> SourceFetchArtifacts:
        return await self._source_fetch_service.fetch(
            analysis_run_id=analysis_run.id,
            topic_name=search_plan.query,
            source=source_query.source,
            source_result=source_result,
            query=source_query.query,
            date_from=date_from,
            date_to=date_to,
        )

    async def _start_source_result(
        self,
        analysis_run_id: UUID,
        source_id: UUID,
    ) -> SourceResult:
        source_result = SourceResult(
            analysis_run_id=analysis_run_id,
            source_id=source_id,
            status=AnalysisStatus.RUNNING,
        )
        return await self._analysis_repository.add_source_result(source_result)

    async def _save_metrics(
        self,
        analysis_run: AnalysisRun,
        mentions: list[Mention],
        trend_points: list[TrendPoint],
    ) -> None:
        metrics_result = await self._summary_service.build_metrics(
            analysis_run,
            mentions,
            trend_points,
        )
        self._analysis_repository.add_metrics(
            AnalysisMetric(
                analysis_run_id=analysis_run.id,
                total_texts=metrics_result.total_texts,
                positive_count=metrics_result.positive_count,
                neutral_count=metrics_result.neutral_count,
                negative_count=metrics_result.negative_count,
                unknown_count=metrics_result.unknown_count,
                joy_count=metrics_result.joy_count,
                irritation_count=metrics_result.irritation_count,
                fear_count=metrics_result.fear_count,
                trust_count=metrics_result.trust_count,
                surprise_count=metrics_result.surprise_count,
                anger_count=metrics_result.anger_count,
                sentiment_score=metrics_result.sentiment_score,
                barometer_value=metrics_result.barometer_value,
                barometer_label=metrics_result.barometer_label,
                summary_short=metrics_result.summary_short,
                summary_detailed=metrics_result.summary_detailed,
            )
        )

    @staticmethod
    def _validate_period(date_from: datetime, date_to: datetime) -> None:
        if date_from > date_to:
            raise ValueError("date_from must be earlier than date_to")
