from collections import Counter
from decimal import Decimal

from db.enums import AnalysisStatus
from db.models import AnalysisMetric, Mention, SourceResult, TrendPoint


EMOTION_CHART_FIELDS = (
    ("joy", "Радость", "joy_count"),
    ("irritation", "Раздражение", "irritation_count"),
    ("fear", "Страх", "fear_count"),
    ("trust", "Доверие", "trust_count"),
    ("surprise", "Удивление", "surprise_count"),
    ("anger", "Злость", "anger_count"),
)


def sentiment_counts(mentions: list[Mention]) -> dict[str, int]:
    return dict(
        Counter(
            mention.sentiment.value if mention.sentiment is not None else "unknown"
            for mention in mentions
        )
    )


def emotion_counts(mentions: list[Mention]) -> dict[str, int]:
    return dict(Counter(mention.emotion for mention in mentions if mention.emotion is not None))


def emotion_distribution(metrics: AnalysisMetric | None) -> list[dict[str, int | float | str]]:
    if metrics is None:
        return []

    counts = [
        (emotion, label, getattr(metrics, field_name) or 0)
        for emotion, label, field_name in EMOTION_CHART_FIELDS
    ]
    total = sum(count for _, _, count in counts)
    if total <= 0:
        return []

    return [
        {
            "emotion": emotion,
            "label": label,
            "count": count,
            "percent": round((count / total) * 100, 2),
        }
        for emotion, label, count in counts
        if count > 0
    ]


def trend_context(trend_points: list[TrendPoint]) -> dict:
    if not trend_points:
        return {"points_count": 0, "has_data": False}
    sorted_points = sorted(trend_points, key=lambda item: item.metric_at)
    return {
        "has_data": True,
        "points_count": len(sorted_points),
        "first_value": float(sorted_points[0].value),
        "last_value": float(sorted_points[-1].value),
        "scale": sorted_points[-1].scale,
    }


def trend_phrase(trend_points: list[TrendPoint]) -> str:
    if not trend_points:
        return "данные по поисковому тренду отсутствуют"
    if len(trend_points) < 2:
        return "точек поискового тренда пока недостаточно для вывода"

    sorted_points = sorted(trend_points, key=lambda item: item.metric_at)
    first = sorted_points[0].value
    last = sorted_points[-1].value
    if last > first:
        return "поисковый интерес вырос"
    if last < first:
        return "поисковый интерес снизился"
    return "поисковый интерес остался стабильным"


def sentiment_score(
    total_texts: int,
    positive_count: int,
    negative_count: int,
) -> Decimal | None:
    if total_texts <= 0:
        return None
    return Decimal(positive_count - negative_count) / Decimal(total_texts)


def barometer_value(score: Decimal | None) -> Decimal | None:
    if score is None:
        return None
    return ((score + Decimal("1")) / Decimal("2")) * Decimal("100")


def barometer_label(value: Decimal | None) -> str:
    if value is None:
        return "нейтральная"
    if value < 40:
        return "негативная тенденция"
    if value > 60:
        return "позитивная"
    return "нейтральная"


def final_status(source_results: list[SourceResult]) -> AnalysisStatus:
    statuses = {item.status for item in source_results}
    if statuses == {AnalysisStatus.SUCCESS}:
        return AnalysisStatus.SUCCESS
    if AnalysisStatus.SUCCESS in statuses:
        return AnalysisStatus.PARTIAL
    return AnalysisStatus.FAILED
