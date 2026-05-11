from datetime import UTC, datetime
from decimal import Decimal

import httpx

from app.connectors.base import ConnectorResult, ParsedTrendPoint

_DATAFORSEO_BASE_URL = "https://api.dataforseo.com"

# Maps Google Trends 2-letter geo codes to DataForSEO location_name values
_GEO_TO_LOCATION_NAME: dict[str, str] = {
    "RU": "Russia",
    "US": "United States",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "UA": "Ukraine",
    "KZ": "Kazakhstan",
    "BY": "Belarus",
}


class DataForSeoTrendsConnector:
    def __init__(
        self,
        login: str | None,
        password: str | None,
        geo: str = "RU",
        language_code: str = "ru",
        timeout_seconds: float = 30.0,
        proxy_url: str | None = None,
    ) -> None:
        self._login = login
        self._password = password
        self._location_name = _GEO_TO_LOCATION_NAME.get(geo.upper(), geo)
        self._geo = geo
        self._language_code = language_code
        self._timeout_seconds = timeout_seconds
        self._proxy_url = proxy_url

    async def fetch(self, query: str, date_from: datetime, date_to: datetime) -> ConnectorResult:
        if not self._login or not self._password:
            raise ValueError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD are required")

        payload = [
            {
                "keywords": [query],
                "date_from": date_from.date().isoformat(),
                "date_to": date_to.date().isoformat(),
                "time_range": "custom_date",
                "location_name": self._location_name,
                "language_code": self._language_code,
                "type": "web",
                "category_code": 0,
            }
        ]

        async with httpx.AsyncClient(
            base_url=_DATAFORSEO_BASE_URL,
            timeout=self._timeout_seconds,
            follow_redirects=True,
            trust_env=False,
            headers={"User-Agent": "digital-barometer/0.1"},
            auth=(self._login, self._password),
            proxy=self._proxy_url,
        ) as client:
            try:
                response = await client.post(
                    "/v3/keywords_data/google_trends/explore/live",
                    json=payload,
                )
            except httpx.RequestError as exc:
                raise ValueError(f"DataForSEO request failed: {exc}") from exc
            _raise_for_status(response)

        data = response.json()
        _check_api_status(data)
        points = _parse_trend_points(data, query, self._geo)
        return ConnectorResult(
            raw_payload={
                "provider": "dataforseo-trends",
                "geo": self._geo,
                "location_name": self._location_name,
                "status_code": response.status_code,
            },
            metrics={"points_returned": len(points)},
            trend_points=points,
        )


def _parse_trend_points(data: object, query: str, geo: str) -> list[ParsedTrendPoint]:
    points: list[ParsedTrendPoint] = []
    if not isinstance(data, dict):
        return points
    for task in data.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        for result in task.get("result") or []:
            if not isinstance(result, dict):
                continue
            if result.get("type") != "google_trends_graph":
                continue
            for item in result.get("items") or []:
                if not isinstance(item, dict):
                    continue
                if item.get("is_partial"):
                    continue
                timestamp = item.get("timestamp")
                value = item.get("value")
                if timestamp is None or value is None:
                    continue
                metric_at = datetime.fromtimestamp(int(timestamp), tz=UTC)
                points.append(
                    ParsedTrendPoint(
                        metric_at=metric_at,
                        keyword=query,
                        region=geo,
                        value=Decimal(str(value)),
                        scale="0_100",
                    )
                )
    return points


def _raise_for_status(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = " ".join(response.text.split())[:500]
        raise ValueError(f"DataForSEO returned HTTP {response.status_code}: {body}") from exc


def _check_api_status(data: object) -> None:
    if not isinstance(data, dict):
        return
    status_code = data.get("status_code")
    if status_code is not None and int(status_code) != 20000:
        message = data.get("status_message", "unknown error")
        raise ValueError(f"DataForSEO API error {status_code}: {message}")