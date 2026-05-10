import unittest
from uuid import uuid4

from app.services.metrics import final_status, sentiment_counts
from app.services.source_fetch import mark_source_failed, redact_sensitive_text
from db.enums import AnalysisStatus, SentimentLabel
from db.models import Mention, SourceResult


class MetricsAndSourceFetchTest(unittest.TestCase):
    def test_unknown_count_includes_missing_sentiment(self) -> None:
        mentions = [
            Mention(sentiment=SentimentLabel.POSITIVE),
            Mention(sentiment=SentimentLabel.UNKNOWN),
            Mention(sentiment=None),
        ]

        self.assertEqual(sentiment_counts(mentions), {"positive": 1, "unknown": 2})

    def test_source_failure_with_success_is_partial(self) -> None:
        results = [
            SourceResult(status=AnalysisStatus.SUCCESS),
            SourceResult(status=AnalysisStatus.FAILED),
        ]

        self.assertEqual(final_status(results), AnalysisStatus.PARTIAL)

    def test_all_failed_sources_keep_analysis_failed(self) -> None:
        results = [
            SourceResult(status=AnalysisStatus.FAILED),
            SourceResult(status=AnalysisStatus.FAILED),
        ]

        self.assertEqual(final_status(results), AnalysisStatus.FAILED)

    def test_source_failure_redacts_api_key_markers(self) -> None:
        source_result = SourceResult(
            analysis_run_id=uuid4(),
            source_id=uuid4(),
            status=AnalysisStatus.RUNNING,
        )

        mark_source_failed(
            source_result,
            ValueError("provider failed: apiKey=secret-token authorization: Bearer abc"),
        )

        self.assertEqual(source_result.status, AnalysisStatus.FAILED)
        self.assertNotIn("secret-token", source_result.error_message or "")
        self.assertNotIn("Bearer abc", source_result.error_message or "")
        self.assertIn("apiKey=***", source_result.error_message or "")

    def test_redact_sensitive_text_handles_header_style(self) -> None:
        self.assertEqual(
            redact_sensitive_text("X-Api-Key: abc123 request failed"),
            "X-Api-Key: *** request failed",
        )


if __name__ == "__main__":
    unittest.main()
