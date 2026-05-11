import unittest
from uuid import uuid4

from app.services.metrics import emotion_distribution, final_status, sentiment_counts
from app.services.source_fetch import mark_source_failed, redact_sensitive_text
from db.enums import AnalysisStatus, SentimentLabel
from db.models import AnalysisMetric, Mention, SourceResult


class MetricsAndSourceFetchTest(unittest.TestCase):
    def test_unknown_count_includes_missing_sentiment(self) -> None:
        mentions = [
            Mention(sentiment=SentimentLabel.POSITIVE),
            Mention(sentiment=SentimentLabel.UNKNOWN),
            Mention(sentiment=None),
        ]

        self.assertEqual(sentiment_counts(mentions), {"positive": 1, "unknown": 2})

    def test_emotion_distribution_returns_chart_ready_percentages(self) -> None:
        metrics = AnalysisMetric(
            joy_count=2,
            irritation_count=1,
            fear_count=0,
            trust_count=1,
            surprise_count=0,
            anger_count=0,
        )

        self.assertEqual(
            emotion_distribution(metrics),
            [
                {
                    "emotion": "joy",
                    "label": "Радость",
                    "count": 2,
                    "percent": 50.0,
                },
                {
                    "emotion": "irritation",
                    "label": "Раздражение",
                    "count": 1,
                    "percent": 25.0,
                },
                {
                    "emotion": "trust",
                    "label": "Доверие",
                    "count": 1,
                    "percent": 25.0,
                },
            ],
        )

    def test_emotion_distribution_is_empty_without_known_emotions(self) -> None:
        self.assertEqual(emotion_distribution(AnalysisMetric()), [])

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

    def test_source_failure_uses_exception_type_when_message_is_empty(self) -> None:
        source_result = SourceResult(
            analysis_run_id=uuid4(),
            source_id=uuid4(),
            status=AnalysisStatus.RUNNING,
        )

        mark_source_failed(source_result, TimeoutError())

        self.assertEqual(source_result.error_message, "TimeoutError")

    def test_source_failure_truncates_long_messages(self) -> None:
        source_result = SourceResult(
            analysis_run_id=uuid4(),
            source_id=uuid4(),
            status=AnalysisStatus.RUNNING,
        )

        mark_source_failed(source_result, ValueError("x" * 1200))

        self.assertEqual(len(source_result.error_message or ""), 1000)

    def test_redact_sensitive_text_handles_header_style(self) -> None:
        self.assertEqual(
            redact_sensitive_text("X-Api-Key: abc123 request failed"),
            "X-Api-Key: *** request failed",
        )


if __name__ == "__main__":
    unittest.main()
