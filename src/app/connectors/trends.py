from datetime import UTC, datetime
from decimal import Decimal

import httpx

from app.connectors.base import ConnectorResult, ParsedTrendPoint

_SERPAPI_URL = "https://serpapi.com/search"

_TRENDS_CONNECTORS = {"pytrends_modern", "dataforseo_trends", "serpapi_trends"}


class SerpApiTrendsConnector:
    def __init__(
        self,
        api_key: str | None,
        geo: str = "RU",
        timeout_seconds: float = 30.0,
        proxy_url: str | None = None,
    ) -> None:
        self._api_key = api_key
        self._geo = geo
        self._timeout_seconds = timeout_seconds
        self._proxy_url = proxy_url

    async def fetch(self, query: str, date_from: datetime, date_to: datetime) -> ConnectorResult:
        if not self._api_key:
            raise ValueError("SERPAPI_API_KEY is required for Google Trends source")

        date_range = f"{date_from.date().isoformat()} {date_to.date().isoformat()}"
        params = {
            "engine": "google_trends",
            "q": query,
            "geo": self._geo,
            "date": date_range,
            "data_type": "TIMESERIES",
            "api_key": self._api_key,
        }

        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=True,
            trust_env=False,
            headers={"User-Agent": "digital-barometer/0.1"},
            proxy=self._proxy_url,
        ) as client:
            try:
                response = await client.get(_SERPAPI_URL, params=params)
            except httpx.RequestError as exc:
                raise ValueError(f"SerpApi request failed: {exc}") from exc
            _raise_for_status(response)

        data = response.json()
        points = _parse_trend_points(data, query, self._geo)
        return ConnectorResult(
            raw_payload={
                "provider": "serpapi-trends",
                "geo": self._geo,
                "date": date_range,
                "status_code": response.status_code,
            },
            metrics={"points_returned": len(points)},
            trend_points=points,
        )


def _parse_trend_points(data: object, query: str, geo: str) -> list[ParsedTrendPoint]:
    points: list[ParsedTrendPoint] = []
    if not isinstance(data, dict):
        return points
    iot = data.get("interest_over_time")
    if not isinstance(iot, dict):
        return points
    for entry in iot.get("timeline_data") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("is_partial"):
            continue
        timestamp = entry.get("timestamp")
        if timestamp is None:
            continue
        for val in entry.get("values") or []:
            if not isinstance(val, dict):
                continue
            extracted = val.get("extracted_value")
            if extracted is None:
                continue
            points.append(
                ParsedTrendPoint(
                    metric_at=datetime.fromtimestamp(int(timestamp), tz=UTC),
                    keyword=query,
                    region=geo,
                    value=Decimal(str(extracted)),
                    scale="0_100",
                )
            )
    return points


def _raise_for_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = " ".join(response.text.split())[:500]
        raise ValueError(f"SerpApi returned HTTP {response.status_code}: {body}") from exc