import asyncio
import re
from datetime import UTC, datetime
from urllib.parse import quote_plus

import httpx

from app.connectors.base import ConnectorResult, ParsedMention


class GdeltDocConnector:
    def __init__(
        self,
        timeout_seconds: float,
        max_records: int = 100,
        language: str | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_records = max_records
        self._language = language

    async def fetch(self, query: str, date_from: datetime, date_to: datetime) -> ConnectorResult:
        url = self._build_url(query, date_from, date_to)
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "digital-barometer/0.1"},
        ) as client:
            response = await self._get_with_rate_limit_retry(client, url)

        payload = _json_payload("GDELT Project", response)
        articles = payload.get("articles") if isinstance(payload, dict) else None
        parsed_mentions = self._parse_articles(articles if isinstance(articles, list) else [])
        mentions = _filter_mentions_by_title(parsed_mentions, query)
        return ConnectorResult(
            raw_payload={
                "url": url,
                "status_code": response.status_code,
                "articles_returned": len(articles) if isinstance(articles, list) else 0,
            },
            metrics={
                "items_returned": len(mentions),
                "items_filtered": len(parsed_mentions) - len(mentions),
            },
            mentions=mentions,
        )

    async def _get_with_rate_limit_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> httpx.Response:
        retry_delays = (6, 12, 18)
        for attempt in range(len(retry_delays) + 1):
            response = await client.get(url)
            if response.status_code == 429 and attempt < len(retry_delays):
                await asyncio.sleep(retry_delays[attempt])
                continue
            _raise_for_status("GDELT Project", response)
            return response
        raise RuntimeError("unreachable GDELT retry state")

    def _build_url(self, query: str, date_from: datetime, date_to: datetime) -> str:
        full_query = query
        if self._language:
            full_query = f"{full_query} sourcelang:{self._language}"

        params = {
            "query": quote_plus(full_query),
            "mode": "ArtList",
            "format": "json",
            "maxrecords": str(self._max_records),
            "sort": "datedesc",
            "startdatetime": self._format_gdelt_datetime(date_from),
            "enddatetime": self._format_gdelt_datetime(date_to),
        }
        query_string = "&".join(f"{key}={value}" for key, value in params.items())
        return f"https://api.gdeltproject.org/api/v2/doc/doc?{query_string}"

    @staticmethod
    def _format_gdelt_datetime(value: datetime) -> str:
        return value.astimezone(UTC).strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _parse_articles(articles: list) -> list[ParsedMention]:
        mentions: list[ParsedMention] = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            url = _string_or_none(article.get("url"))
            title = _string_or_none(article.get("title"))
            mentions.append(
                ParsedMention(
                    external_id=url,
                    title=title,
                    text=None,
                    url=url,
                    published_at=_parse_gdelt_date(_string_or_none(article.get("seendate"))),
                    region=_string_or_none(article.get("sourcecountry")),
                    source_metadata={
                        "domain": _string_or_none(article.get("domain")),
                        "language": _string_or_none(article.get("language")),
                        "source_country": _string_or_none(article.get("sourcecountry")),
                        "image": _string_or_none(article.get("socialimage")),
                    },
                )
            )
        return mentions


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_gdelt_date(value: str | None) -> datetime | None:
    if not value:
        return None
    digits = "".join(char for char in value if char.isdigit())
    if len(digits) < 14:
        return None
    try:
        return datetime.strptime(digits[:14], "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    except ValueError:
        return None


def _filter_mentions_by_title(mentions: list[ParsedMention], query: str) -> list[ParsedMention]:
    terms = _query_terms(query)
    if not terms:
        return mentions
    return [
        mention
        for mention in mentions
        if mention.title and _matches_any_term(mention.title, terms)
    ]


def _query_terms(query: str) -> list[str]:
    ignored = {"and", "or", "not", "near", "repeat", "sourcelang"}
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


def _json_payload(provider: str, response: httpx.Response) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        body = " ".join(response.text.split())[:500]
        raise ValueError(
            f"{provider} returned non-JSON response HTTP {response.status_code}: {body}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{provider} returned unexpected JSON payload")
    return payload
