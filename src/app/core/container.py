from collections.abc import AsyncIterable

from dishka import Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.factory import ConnectorFactory
from app.core.settings import Settings, settings
from app.repositories.analysis import AnalysisRepository
from app.repositories.sources import SourceRepository
from app.repositories.topics import TopicRepository
from app.services.analysis import AnalysisService
from app.services.llm import LLMService
from app.services.search_plan import QueryBuilder
from app.services.sentiment import SentimentAnalyzer
from app.services.sources import SourceService
from app.services.source_fetch import SourceFetchService
from app.services.summary import SummaryService
from app.services.topics import TopicService
from db.database import async_session_maker


class AppProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return settings

    @provide(scope=Scope.APP)
    def connector_factory(self, settings: Settings) -> ConnectorFactory:
        return ConnectorFactory(settings)

    @provide(scope=Scope.REQUEST)
    async def session(self) -> AsyncIterable[AsyncSession]:
        async with async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            else:
                await session.commit()

    source_repository = provide(SourceRepository, scope=Scope.REQUEST)
    topic_repository = provide(TopicRepository, scope=Scope.REQUEST)
    analysis_repository = provide(AnalysisRepository, scope=Scope.REQUEST)

    llm_service = provide(LLMService, scope=Scope.APP)
    query_builder = provide(QueryBuilder, scope=Scope.APP)
    sentiment_analyzer = provide(SentimentAnalyzer, scope=Scope.REQUEST)
    source_fetch_service = provide(SourceFetchService, scope=Scope.REQUEST)
    source_service = provide(SourceService, scope=Scope.REQUEST)
    topic_service = provide(TopicService, scope=Scope.REQUEST)
    summary_service = provide(SummaryService, scope=Scope.REQUEST)
    analysis_service = provide(AnalysisService, scope=Scope.REQUEST)


def create_container():
    return make_async_container(AppProvider())
