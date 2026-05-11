import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx

from app.connectors.gdelt import GdeltDocConnector


class GdeltConnectorTest(unittest.IsolatedAsyncioTestCase):
    async def test_retries_rate_limit_until_success(self) -> None:
        connector = GdeltDocConnector(timeout_seconds=10)
        request = httpx.Request(
            "GET",
            "https://api.gdeltproject.org/api/v2/doc/doc",
        )
        client = Mock()
        client.get = AsyncMock(
            side_effect=[
                httpx.Response(429, text="rate limit", request=request),
                httpx.Response(429, text="rate limit", request=request),
                httpx.Response(200, json={"articles": []}, request=request),
            ]
        )

        with patch("app.connectors.gdelt.asyncio.sleep", new=AsyncMock()) as sleep:
            response = await connector._get_with_rate_limit_retry(
                client,
                "https://api.gdeltproject.org/api/v2/doc/doc",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get.await_count, 3)
        self.assertEqual(sleep.await_count, 2)
        sleep.assert_any_await(6)
        sleep.assert_any_await(10)


if __name__ == "__main__":
    unittest.main()
