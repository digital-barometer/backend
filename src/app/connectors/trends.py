from datetime import UTC, datetime
from decimal import Decimal
from pytrends_modern import TrendReq
import asyncio

from app.connectors.base import ConnectorResult, ParsedTrendPoint


class PytrendsModernConnector:
    def __init__(self, geo: str = "RU") -> None:
        self._geo = geo

    async def fetch(self, query: str, date_from: datetime, date_to: datetime) -> ConnectorResult:
        return await self._fetch_in_thread(query, date_from, date_to)

    async def _fetch_in_thread(
        self,
        query: str,
        date_from: datetime,
        date_to: datetime,
    ) -> ConnectorResult:

        return await asyncio.to_thread(self._fetch_sync, query, date_from, date_to)

    def _fetch_sync(self, query: str, date_from: datetime, date_to: datetime) -> ConnectorResult:

        pytrends = TrendReq(hl="ru-RU", tz=180)
        timeframe = f"{date_from.date().isoformat()} {date_to.date().isoformat()}"
        pytrends.build_payload(
            kw_list=[query],
            timeframe=timeframe,
            geo=self._geo,
        )
        data_frame = pytrends.interest_over_time()

        points: list[ParsedTrendPoint] = []
        if not data_frame.empty:
            for index, row in data_frame.iterrows():
                if "isPartial" in row and bool(row["isPartial"]):
                    continue
                metric_at = index.to_pydatetime()
                if metric_at.tzinfo is None:
                    metric_at = metric_at.replace(tzinfo=UTC)
                points.append(
                    ParsedTrendPoint(
                        metric_at=metric_at,
                        keyword=query,
                        region=self._geo,
                        value=Decimal(str(row[query])),
                        scale="0_100",
                    )
                )

        return ConnectorResult(
            raw_payload={
                "provider": "pytrends-modern",
                "geo": self._geo,
                "timeframe": timeframe,
            },
            metrics={"points_returned": len(points)},
            trend_points=points,
        )
