"""initial barometer schema

Revision ID: 0001_initial_barometer_schema
Revises: None
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001_initial_barometer_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


source_type = postgresql.ENUM(
    "search_trend",
    "social",
    "video",
    "news",
    "review",
    "marketplace",
    "forum",
    "statistics",
    "map_review",
    name="sourcetype",
    create_type=False,
)
analysis_status = postgresql.ENUM(
    "pending",
    "running",
    "success",
    "failed",
    "partial",
    "cancelled",
    name="analysisstatus",
    create_type=False,
)
sentiment_label = postgresql.ENUM(
    "positive",
    "neutral",
    "negative",
    "mixed",
    "unknown",
    name="sentimentlabel",
    create_type=False,
)
report_format = postgresql.ENUM("pdf", "xlsx", "csv", name="reportformat", create_type=False)
report_status = postgresql.ENUM(
    "pending",
    "running",
    "success",
    "failed",
    name="reportstatus",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    bind = op.get_bind()
    source_type.create(bind, checkfirst=True)
    analysis_status.create(bind, checkfirst=True)
    sentiment_label.create(bind, checkfirst=True)
    report_format.create(bind, checkfirst=True)
    report_status.create(bind, checkfirst=True)

    op.create_table(
        "topics",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("keywords", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "sources",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """
        INSERT INTO sources (name, source_type, base_url, config, is_active)
        VALUES
            ('Google Trends', 'search_trend', 'https://trends.google.com', '{"connector": "pytrends_modern", "geo": "RU"}'::jsonb, true),
            (
                'Google News',
                'news',
                'https://news.google.com',
                '{"rss_url_template": "https://news.google.com/rss/search?q={query}&hl=ru&gl=RU&ceid=RU:ru"}'::jsonb,
                true
            ),
            (
                'Habr',
                'forum',
                'https://habr.com',
                '{"rss_url_template": "https://habr.com/ru/rss/search/?q={query}", "filter_locally": true, "proxy_url": ""}'::jsonb,
                true
            ),
            (
                'GDELT Project',
                'news',
                'https://www.gdeltproject.org',
                '{"connector": "gdelt_doc", "max_records": 100}'::jsonb,
                true
            ),
            (
                'NewsAPI',
                'news',
                'https://newsapi.org',
                '{"connector": "newsapi", "language": "ru", "page_size": 100, "sort_by": "publishedAt"}'::jsonb,
                false
            )
        """
    )
    op.create_table(
        "analysis_runs",
        sa.Column("topic_id", sa.UUID(), nullable=False),
        sa.Column("status", analysis_status, server_default="pending", nullable=False),
        sa.Column("date_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "source_results",
        sa.Column("analysis_run_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("status", analysis_status, server_default="pending", nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("items_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("items_saved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", "source_id", name="uq_source_results_analysis_run_source"),
    )
    op.create_table(
        "mentions",
        sa.Column("analysis_run_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author_name", sa.Text(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("reposts", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("sentiment", sentiment_label, nullable=True),
        sa.Column("sentiment_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("emotion", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("source_metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", "source_id", "content_hash", name="uq_mentions_run_source_content_hash"),
    )
    op.create_table(
        "trend_points",
        sa.Column("analysis_run_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("metric_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("keyword", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("scale", sa.Text(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("point_hash", sa.String(length=64), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", "source_id", "point_hash", name="uq_trend_points_run_source_point_hash"),
    )
    op.create_table(
        "reports",
        sa.Column("analysis_run_id", sa.UUID(), nullable=False),
        sa.Column("format", report_format, nullable=False),
        sa.Column("status", report_status, server_default="pending", nullable=False),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id", "format", name="uq_reports_analysis_run_format"),
    )
    op.create_table(
        "analysis_metrics",
        sa.Column("analysis_run_id", sa.UUID(), nullable=False),
        sa.Column("total_texts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("positive_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("neutral_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("negative_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("joy_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("irritation_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fear_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("trust_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("surprise_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("anger_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sentiment_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("barometer_value", sa.Numeric(6, 2), nullable=True),
        sa.Column("barometer_label", sa.Text(), nullable=True),
        sa.Column("summary_short", sa.Text(), nullable=True),
        sa.Column("summary_detailed", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_run_id"),
    )

    op.create_index("ix_analysis_runs_topic_date", "analysis_runs", ["topic_id", "date_from", "date_to"])
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"])
    op.create_index("ix_source_results_analysis_run_id", "source_results", ["analysis_run_id"])
    op.create_index("ix_source_results_source_id", "source_results", ["source_id"])
    op.create_index("ix_source_results_status", "source_results", ["status"])
    op.create_index("ix_mentions_analysis_run_id", "mentions", ["analysis_run_id"])
    op.create_index("ix_mentions_source_date", "mentions", ["source_id", "published_at"])
    op.create_index("ix_mentions_region", "mentions", ["region"])
    op.create_index(
        "ix_mentions_text_search",
        "mentions",
        ["title", "text"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops", "text": "gin_trgm_ops"},
    )
    op.create_index("ix_trend_points_analysis_run_date", "trend_points", ["analysis_run_id", "metric_at"])
    op.create_index("ix_trend_points_source_date", "trend_points", ["source_id", "metric_at"])
    op.create_index("ix_trend_points_region", "trend_points", ["region"])
    op.create_index("ix_reports_analysis_run_id", "reports", ["analysis_run_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_analysis_run_id", table_name="reports")
    op.drop_index("ix_trend_points_region", table_name="trend_points")
    op.drop_index("ix_trend_points_source_date", table_name="trend_points")
    op.drop_index("ix_trend_points_analysis_run_date", table_name="trend_points")
    op.drop_index("ix_mentions_text_search", table_name="mentions", postgresql_using="gin")
    op.drop_index("ix_mentions_region", table_name="mentions")
    op.drop_index("ix_mentions_source_date", table_name="mentions")
    op.drop_index("ix_mentions_analysis_run_id", table_name="mentions")
    op.drop_index("ix_source_results_status", table_name="source_results")
    op.drop_index("ix_source_results_source_id", table_name="source_results")
    op.drop_index("ix_source_results_analysis_run_id", table_name="source_results")
    op.drop_index("ix_analysis_runs_status", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_topic_date", table_name="analysis_runs")

    op.drop_table("analysis_metrics")
    op.drop_table("reports")
    op.drop_table("trend_points")
    op.drop_table("mentions")
    op.drop_table("source_results")
    op.drop_table("analysis_runs")
    op.drop_table("sources")
    op.drop_table("topics")

    bind = op.get_bind()
    report_status.drop(bind, checkfirst=True)
    report_format.drop(bind, checkfirst=True)
    sentiment_label.drop(bind, checkfirst=True)
    analysis_status.drop(bind, checkfirst=True)
    source_type.drop(bind, checkfirst=True)
