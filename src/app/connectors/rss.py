from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from html import unescape
import re
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx

from app.connectors.base import ConnectorResult, ParsedMention


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(" ".join(self._parts).split())


class RssSearchConnector:
    def __init__(
        self,
        url_template: str,
        timeout_seconds: float,
        filter_locally: bool = False,
        proxy_url: str | None = None,
    ) -> None:
        self._url_template = url_template
        self._timeout_seconds = timeout_seconds
        self._filter_locally = filter_locally
        self._proxy_url = proxy_url

    async def fetch(self, query: str, date_from: datetime, date_to: datetime) -> ConnectorResult:
        url = self._url_template.format(query=quote_plus(query))
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            trust_env=False,
            proxy=self._proxy_url,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        mentions = self._parse_items(response.text, query, date_from, date_to)
        return ConnectorResult(
            raw_payload={"url": url, "status_code": response.status_code},
            metrics={"items_returned": len(mentions)},
            mentions=mentions,
        )

    def _parse_items(
        self,
        xml_text: str,
        query: str,
        date_from: datetime,
        date_to: datetime,
    ) -> list[ParsedMention]:
        root = ElementTree.fromstring(xml_text)
        items = root.findall(".//item")
        mentions: list[ParsedMention] = []
        query_terms = _query_terms(query)

        for item in items:
            title = self._text(item, "title")
            description = self._text(item, "description")
            link = self._text(item, "link")
            published_at = self._parse_date(self._text(item, "pubDate"))
            text = self._clean_text(description)

            if published_at and not (date_from <= published_at <= date_to):
                continue
            if self._filter_locally and not _matches_any_term(
                f"{title or ''} {text or ''}",
                query_terms,
            ):
                continue

            mentions.append(
                ParsedMention(
                    external_id=link,
                    title=title,
                    text=text,
                    url=link,
                    published_at=published_at,
                )
            )

        return mentions

    @staticmethod
    def _text(item: ElementTree.Element, tag: str) -> str | None:
        child = item.find(tag)
        if child is None or child.text is None:
            return None
        return unescape(child.text.strip())

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if not value:
            return None
        parser = _HTMLTextExtractor()
        parser.feed(unescape(value))
        text = parser.get_text()
        return text or " ".join(unescape(value).split())

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)


def _query_terms(query: str) -> list[str]:
    ignored = {"and", "or", "not"}
    quoted = re.findall(r'"([^"]+)"', query.lower())
    tokens = re.findall(r"[a-zа-яё0-9][a-zа-яё0-9._-]*", query.lower())
    terms = [term.strip() for term in quoted if term.strip()]
    terms.extend(token for token in tokens if token not in ignored and len(token) > 1)
    return list(dict.fromkeys(terms))


def _matches_any_term(text: str, terms: list[str]) -> bool:
    if not terms:
        return True
    lower_text = text.lower()
    return any(term in lower_text for term in terms)
