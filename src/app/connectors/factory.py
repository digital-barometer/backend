from app.connectors.base import SourceConnector
from app.connectors.gdelt import GdeltDocConnector
from app.connectors.newsapi import NewsApiConnector
from app.connectors.rss import RssSearchConnector
from app.connectors.trends import PytrendsModernConnector
from app.core.settings import Settings
from db.enums import SourceType
from db.models import Source


class ConnectorFactory:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, source: Source) -> SourceConnector:
        proxy_url = _optional_str(self._settings.OUTBOUND_PROXY_URL)

        if source.config.get("connector") == "pytrends_modern":
            return PytrendsModernConnector(
                geo=str(source.config.get("geo", "RU")),
                proxy_url=proxy_url,
            )

        if source.config.get("connector") == "gdelt_doc":
            return GdeltDocConnector(
                timeout_seconds=self._settings.REQUEST_TIMEOUT_SECONDS,
                max_records=int(source.config.get("max_records", 100)),
                language=_optional_str(source.config.get("language")),
                proxy_url=proxy_url,
            )

        if source.config.get("connector") == "newsapi":
            return NewsApiConnector(
                api_key=self._settings.NEWSAPI_API_KEY,
                timeout_seconds=self._settings.REQUEST_TIMEOUT_SECONDS,
                language=str(source.config.get("language", "ru")),
                page_size=int(source.config.get("page_size", 100)),
                sort_by=str(source.config.get("sort_by", "publishedAt")),
                proxy_url=proxy_url,
            )

        if source.source_type in {SourceType.NEWS, SourceType.FORUM}:
            url_template = source.config.get("rss_url_template")
            if not isinstance(url_template, str):
                raise ValueError(f"Source {source.name} has no rss_url_template")
            return RssSearchConnector(
                url_template=url_template,
                timeout_seconds=self._settings.REQUEST_TIMEOUT_SECONDS,
                filter_locally=bool(source.config.get("filter_locally", False)),
                proxy_url=proxy_url,
            )

        raise ValueError(f"Source {source.name} is not supported yet")


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
