from app.services.llm import LLMService
from db.models import AnalysisRun, Mention, TrendPoint


class SummaryService:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def build_metrics(
        self,
        analysis_run: AnalysisRun,
        mentions: list[Mention],
        trend_points: list[TrendPoint],
    ):
        return await self._llm_service.build_analysis_metrics(
            topic_name=analysis_run.topic.name,
            mentions=mentions,
            trend_points=trend_points,
        )
