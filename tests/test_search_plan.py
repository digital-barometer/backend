import unittest
from uuid import uuid4

from app.schemas.analysis import AnalysisRunRequest
from app.services.search_plan import QueryBuilder, build_source_query, normalize_keywords
from db.enums import SourceType
from db.models import Source


def source(connector: str | None) -> Source:
    config = {"connector": connector} if connector else {"rss_url_template": "https://example.com?q={query}"}
    return Source(
        name=connector or "rss",
        source_type=SourceType.NEWS,
        base_url="https://example.com",
        config=config,
        is_active=True,
    )


class SearchPlanTest(unittest.TestCase):
    def test_analysis_payload_requires_topic_id(self) -> None:
        topic_id = uuid4()
        payload = AnalysisRunRequest(
            topic_id=topic_id,
            date_from="2026-01-01T00:00:00Z",
            date_to="2026-01-02T00:00:00Z",
        )

        self.assertEqual(payload.topic_id, topic_id)

    def test_keyword_coverage_deduplicates_query_and_keywords(self) -> None:
        self.assertEqual(
            normalize_keywords("OpenAI", [" ChatGPT ", "OpenAI", "", "GPT-5"]),
            ["OpenAI", "ChatGPT", "GPT-5"],
        )

    def test_newsapi_query_uses_or_coverage(self) -> None:
        self.assertEqual(
            build_source_query(source("newsapi"), "OpenAI", ["OpenAI", "ChatGPT"]),
            "OpenAI OR ChatGPT",
        )

    def test_rss_query_uses_or_coverage(self) -> None:
        self.assertEqual(
            build_source_query(source(None), "OpenAI", ["OpenAI", "ChatGPT"]),
            "OpenAI OR ChatGPT",
        )

    def test_gdelt_query_quotes_phrases_and_filters_invalid_terms(self) -> None:
        self.assertEqual(
            build_source_query(
                source("gdelt_doc"),
                "OpenAI",
                ["OpenAI", "ChatGPT", "bad:term", "искусственный интеллект"],
            ),
            '(OpenAI OR ChatGPT OR "искусственный интеллект")',
        )

    def test_google_trends_query_uses_main_query_only(self) -> None:
        self.assertEqual(
            build_source_query(source("pytrends_modern"), "OpenAI", ["OpenAI", "ChatGPT"]),
            "OpenAI",
        )

    def test_query_builder_returns_per_source_queries(self) -> None:
        plan = QueryBuilder().build(
            "OpenAI",
            ["ChatGPT"],
            [source("gdelt_doc"), source("newsapi"), source("pytrends_modern")],
        )

        self.assertEqual(plan.query, "OpenAI")
        self.assertEqual(plan.keywords, ["OpenAI", "ChatGPT"])
        self.assertEqual(
            [item.query for item in plan.source_queries],
            ["(OpenAI OR ChatGPT)", "OpenAI OR ChatGPT", "OpenAI"],
        )


if __name__ == "__main__":
    unittest.main()
