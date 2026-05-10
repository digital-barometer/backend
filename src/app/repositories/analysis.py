from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import AnalysisMetric, AnalysisRun, Mention, SourceResult, TrendPoint


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_run(self, analysis_run: AnalysisRun) -> AnalysisRun:
        self._session.add(analysis_run)
        await self._session.flush()
        return analysis_run

    async def add_source_result(self, source_result: SourceResult) -> SourceResult:
        self._session.add(source_result)
        await self._session.flush()
        return source_result

    def add_mentions(self, mentions: list[Mention]) -> None:
        self._session.add_all(mentions)

    def add_trend_points(self, trend_points: list[TrendPoint]) -> None:
        self._session.add_all(trend_points)

    def add_metrics(self, metrics: AnalysisMetric) -> None:
        self._session.add(metrics)

    async def get_with_details(self, analysis_id: UUID) -> AnalysisRun | None:
        await self._session.flush()
        result = await self._session.execute(
            select(AnalysisRun)
            .where(AnalysisRun.id == analysis_id)
            .options(
                selectinload(AnalysisRun.topic),
                selectinload(AnalysisRun.source_results).selectinload(SourceResult.source),
                selectinload(AnalysisRun.mentions).selectinload(Mention.source),
                selectinload(AnalysisRun.trend_points).selectinload(TrendPoint.source),
                selectinload(AnalysisRun.metrics),
            )
        )
        return result.scalar_one_or_none()
