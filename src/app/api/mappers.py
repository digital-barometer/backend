from app.schemas.analysis import (
    AnalysisMetricsResponse,
    AnalysisRunResponse,
    ChartDataResponse,
    DailyMentionPoint,
    EmotionPoint,
    MentionResponse,
    SentimentPoint,
    SourceResponse,
    SourceResultResponse,
    TopicResponse,
    TrendPointResponse,
)
from db.models import AnalysisMetric, AnalysisRun, Mention, Source, SourceResult, Topic, TrendPoint


def to_topic_response(topic: Topic) -> TopicResponse:
    return TopicResponse(
        id=topic.id,
        name=topic.name,
        slug=topic.slug,
        keywords=topic.keywords,
        is_active=topic.is_active,
    )


def to_source_response(source: Source) -> SourceResponse:
    return SourceResponse(
        id=source.id,
        name=source.name,
        source_type=source.source_type.value,
        base_url=source.base_url,
        is_active=source.is_active,
    )


def to_analysis_run_response(analysis_run: AnalysisRun) -> AnalysisRunResponse:
    return AnalysisRunResponse(
        id=analysis_run.id,
        topic=to_topic_response(analysis_run.topic),
        status=analysis_run.status.value,
        date_from=analysis_run.date_from,
        date_to=analysis_run.date_to,
        error_message=analysis_run.error_message,
        metrics=to_metrics_response(analysis_run.metrics),
        source_results=[
            to_source_result_response(item) for item in analysis_run.source_results
        ],
        mentions=[to_mention_response(item) for item in analysis_run.mentions],
        trend_points=[to_trend_point_response(item) for item in analysis_run.trend_points],
    )


def to_chart_response(chart_data: dict) -> ChartDataResponse:
    return ChartDataResponse(
        trend_points=[to_trend_point_response(item) for item in chart_data["trend_points"]],
        mentions_by_day=[DailyMentionPoint(**item) for item in chart_data["mentions_by_day"]],
        sentiment=[SentimentPoint(**item) for item in chart_data["sentiment"]],
        emotions=[EmotionPoint(**item) for item in chart_data["emotions"]],
    )


def to_source_result_response(source_result: SourceResult) -> SourceResultResponse:
    return SourceResultResponse(
        source_id=source_result.source.id,
        source_name=source_result.source.name,
        status=source_result.status.value,
        items_found=source_result.items_found,
        items_saved=source_result.items_saved,
        metrics=source_result.metrics,
        error_message=source_result.error_message,
    )


def to_mention_response(mention: Mention) -> MentionResponse:
    return MentionResponse(
        id=mention.id,
        source_id=mention.source.id,
        source_name=mention.source.name,
        title=mention.title,
        text=mention.text,
        url=mention.url,
        published_at=mention.published_at,
        views=mention.views,
        likes=mention.likes,
        comments=mention.comments,
        reposts=mention.reposts,
        rating=mention.rating,
        sentiment=mention.sentiment.value if mention.sentiment else None,
    )


def to_trend_point_response(trend_point: TrendPoint) -> TrendPointResponse:
    return TrendPointResponse(
        source_id=trend_point.source.id,
        source_name=trend_point.source.name,
        metric_at=trend_point.metric_at,
        keyword=trend_point.keyword,
        region=trend_point.region,
        value=trend_point.value,
        scale=trend_point.scale,
        metrics=trend_point.metrics,
    )


def to_metrics_response(metrics: AnalysisMetric | None) -> AnalysisMetricsResponse | None:
    if metrics is None:
        return None
    return AnalysisMetricsResponse(
        total_texts=metrics.total_texts,
        positive_count=metrics.positive_count,
        neutral_count=metrics.neutral_count,
        negative_count=metrics.negative_count,
        unknown_count=metrics.unknown_count,
        joy_count=metrics.joy_count,
        irritation_count=metrics.irritation_count,
        fear_count=metrics.fear_count,
        trust_count=metrics.trust_count,
        surprise_count=metrics.surprise_count,
        anger_count=metrics.anger_count,
        sentiment_score=metrics.sentiment_score,
        barometer_value=metrics.barometer_value,
        barometer_label=metrics.barometer_label,
        summary_short=metrics.summary_short,
        summary_detailed=metrics.summary_detailed,
    )
