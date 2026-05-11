import unittest

from app.connectors.factory import ConnectorFactory
from app.connectors.gdelt import GdeltDocConnector
from app.connectors.newsapi import NewsApiConnector
from app.connectors.rss import RssSearchConnector
from app.connectors.trends import PytrendsModernConnector
from app.core.settings import Settings
from db.enums import SourceType
from db.models import Source


def source(connector: str | None) -> Source:
    config = (
        {"connector": connector}
        if connector
        else {"rss_url_template": "https://example.com?q={query}"}
    )
    return Source(
        name=connector or "rss",
        source_type=SourceType.NEWS,
        base_url="https://example.com",
        config=config,
        is_active=True,
    )


class ConnectorFactoryTest(unittest.TestCase):
    def test_proxy_url_is_passed_to_external_connectors(self) -> None:
        proxy_url = "socks5h://tgproxy:123@144.48.10.151:1080"
        factory = ConnectorFactory(Settings(OUTBOUND_PROXY_URL=proxy_url))

        connectors = [
            factory.create(source("pytrends_modern")),
            factory.create(source("gdelt_doc")),
            factory.create(source("newsapi")),
            factory.create(source(None)),
        ]

        self.assertIsInstance(connectors[0], PytrendsModernConnector)
        self.assertIsInstance(connectors[1], GdeltDocConnector)
        self.assertIsInstance(connectors[2], NewsApiConnector)
        self.assertIsInstance(connectors[3], RssSearchConnector)
        self.assertTrue(all(connector._proxy_url == proxy_url for connector in connectors))

    def test_empty_proxy_url_keeps_connectors_direct(self) -> None:
        factory = ConnectorFactory(Settings(OUTBOUND_PROXY_URL=" "))

        connectors = [
            factory.create(source("pytrends_modern")),
            factory.create(source("gdelt_doc")),
            factory.create(source("newsapi")),
            factory.create(source(None)),
        ]

        self.assertTrue(all(connector._proxy_url is None for connector in connectors))

    def test_source_proxy_url_overrides_global_proxy(self) -> None:
        factory = ConnectorFactory(
            Settings(OUTBOUND_PROXY_URL="socks5h://global:1080")
        )
        source_without_proxy = source(None)
        source_without_proxy.config["proxy_url"] = ""

        connector = factory.create(source_without_proxy)

        self.assertIsNone(connector._proxy_url)


if __name__ == "__main__":
    unittest.main()
