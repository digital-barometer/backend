import re
from datetime import UTC, datetime

import httpx

from app.connectors.base import ConnectorResult, ParsedMention


class NewsApiConnector:
    def __init__(
        self,
        api_key: str | None,
        timeout_seconds: float,
        language: str = "ru",
        page_size: int = 100,
        sort_by: str = "publishedAt",
        proxy_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._language = language
        self._page_size = page_size
        self._sort_by = sort_by
        self._proxy_url = proxy_url

    async def fetch(self, query: str, date_from: datetime, date_to: datetime) -> ConnectorResult:
        if not self._api_key:
            raise ValueError("NEWSAPI_API_KEY is required for NewsAPI source")

        params = {
            "q": query,
            "from": date_from.astimezone(UTC).isoformat(),
            "to": date_to.astimezone(UTC).isoformat(),
            "language": self._language,
            "sortBy": self._sort_by,
            "pageSize": self._page_size,
        }
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": "digital-barometer/0.1",
                "X-Api-Key": self._api_key,
            },
            proxy=self._proxy_url,
        ) as client:
            try:
                response = await client.get("https://newsapi.org/v2/everything", params=params)
            except httpx.RequestError as exc:
                raise ValueError(f"NewsAPI request failed: {_exception_message(exc)}") from exc
            _raise_for_status("NewsAPI", response)

        payload = response.json()
        articles = payload.get("articles") if isinstance(payload, dict) else None
        parsed_mentions = self._parse_articles(articles if isinstance(articles, list) else [])
        mentions = _filter_mentions_by_visible_text(parsed_mentions, query)
        return ConnectorResult(
            raw_payload={
                "endpoint": "https://newsapi.org/v2/everything",
                "status_code": response.status_code,
                "total_results": payload.get("totalResults") if isinstance(payload, dict) else None,
            },
            metrics={
                "items_returned": len(mentions),
                "items_filtered": len(parsed_mentions) - len(mentions),
            },
            mentions=mentions,
        )

    @staticmethod
    def _parse_articles(articles: list) -> list[ParsedMention]:
        mentions: list[ParsedMention] = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            url = _string_or_none(article.get("url"))
            source = article.get("source")
            source_name = source.get("name") if isinstance(source, dict) else None
            mentions.append(
                ParsedMention(
                    external_id=url,
                    title=_string_or_none(article.get("title")),
                    text=_string_or_none(article.get("description"))
                    or _string_or_none(article.get("content")),
                    url=url,
                    published_at=_parse_datetime(_string_or_none(article.get("publishedAt"))),
                    author_name=_string_or_none(article.get("author")),
                    source_metadata={
                        "source": _string_or_none(source_name),
                        "image": _string_or_none(article.get("urlToImage")),
                    },
                )
            )
        return mentions


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _filter_mentions_by_visible_text(
    mentions: list[ParsedMention],
    query: str,
) -> list[ParsedMention]:
    terms = _query_terms(query)
    if not terms:
        return mentions
    return [
        mention
        for mention in mentions
        if _matches_any_term(f"{mention.title or ''} {mention.text or ''}", terms)
    ]


def _query_terms(query: str) -> list[str]:
    ignored = {"and", "or", "not"}
    quoted = re.findall(r'"([^"]+)"', query.lower())
    tokens = re.findall(r"[a-zа-яё0-9][a-zа-яё0-9._-]*", query.lower())
    terms = [term.strip() for term in quoted if term.strip()]
    terms.extend(token for token in tokens if token not in ignored and len(token) > 1)
    return list(dict.fromkeys(terms))


def _matches_any_term(text: str, terms: list[str]) -> bool:
    lower_text = text.lower()
    return any(term in lower_text for term in terms)


def _raise_for_status(provider: str, response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = " ".join(response.text.split())[:500]
        raise ValueError(f"{provider} returned HTTP {response.status_code}: {body}") from exc


def _exception_message(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__
