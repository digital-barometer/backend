from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.types import pg_enum

from .database import Base
from .enums import AnalysisStatus, ReportFormat, ReportStatus, SentimentLabel, SourceType


class Topic(Base):
    __tablename__ = "topics"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    analysis_runs: Mapped[list[AnalysisRun]] = relationship(back_populates="topic")


class Source(Base):
    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[SourceType] = mapped_column(pg_enum(SourceType), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    results: Mapped[list[SourceResult]] = relationship(back_populates="source")
    mentions: Mapped[list[Mention]] = relationship(back_populates="source")
    trend_points: Mapped[list[TrendPoint]] = relationship(back_populates="source")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        Index("ix_analysis_runs_topic_date", "topic_id", "date_from", "date_to"),
        Index("ix_analysis_runs_status", "status"),
    )

    topic_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        pg_enum(AnalysisStatus),
        default=AnalysisStatus.PENDING,
        server_default=AnalysisStatus.PENDING.value,
        nullable=False,
    )
    date_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    error_message: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    topic: Mapped[Topic] = relationship(back_populates="analysis_runs")
    source_results: Mapped[list[SourceResult]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    mentions: Mapped[list[Mention]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    trend_points: Mapped[list[TrendPoint]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    metrics: Mapped[AnalysisMetric | None] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list[Report]] = relationship(
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )


class SourceResult(Base):
    __tablename__ = "source_results"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "source_id",
            name="uq_source_results_analysis_run_source",
        ),
        Index("ix_source_results_analysis_run_id", "analysis_run_id"),
        Index("ix_source_results_source_id", "source_id"),
        Index("ix_source_results_status", "status"),
    )

    analysis_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[AnalysisStatus] = mapped_column(
        pg_enum(AnalysisStatus),
        default=AnalysisStatus.PENDING,
        server_default=AnalysisStatus.PENDING.value,
        nullable=False,
    )
    raw_payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    items_found: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    items_saved: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="source_results")
    source: Mapped[Source] = relationship(back_populates="results")


class Mention(Base):
    __tablename__ = "mentions"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "source_id",
            "content_hash",
            name="uq_mentions_run_source_content_hash",
        ),
        Index("ix_mentions_analysis_run_id", "analysis_run_id"),
        Index("ix_mentions_source_date", "source_id", "published_at"),
        Index("ix_mentions_region", "region"),
        Index(
            "ix_mentions_text_search",
            "title",
            "text",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops", "text": "gin_trgm_ops"},
        ),
    )

    analysis_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    author_name: Mapped[str | None] = mapped_column(Text)
    views: Mapped[int | None] = mapped_column(Integer)
    likes: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[int | None] = mapped_column(Integer)
    reposts: Mapped[int | None] = mapped_column(Integer)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    sentiment: Mapped[SentimentLabel | None] = mapped_column(pg_enum(SentimentLabel))
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    emotion: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    source_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="mentions")
    source: Mapped[Source] = relationship(back_populates="mentions")


class TrendPoint(Base):
    __tablename__ = "trend_points"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "source_id",
            "point_hash",
            name="uq_trend_points_run_source_point_hash",
        ),
        Index("ix_trend_points_analysis_run_date", "analysis_run_id", "metric_at"),
        Index("ix_trend_points_source_date", "source_id", "metric_at"),
        Index("ix_trend_points_region", "region"),
    )

    analysis_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    keyword: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    scale: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    point_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="trend_points")
    source: Mapped[Source] = relationship(back_populates="trend_points")


class AnalysisMetric(Base):
    __tablename__ = "analysis_metrics"

    analysis_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    total_texts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    positive_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    neutral_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    negative_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    unknown_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    joy_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    irritation_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    fear_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    trust_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    surprise_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    anger_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    barometer_value: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    barometer_label: Mapped[str | None] = mapped_column(Text)
    summary_short: Mapped[str | None] = mapped_column(Text)
    summary_detailed: Mapped[str | None] = mapped_column(Text)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="metrics")


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("analysis_run_id", "format", name="uq_reports_analysis_run_format"),
        Index("ix_reports_analysis_run_id", "analysis_run_id"),
    )

    analysis_run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    format: Mapped[ReportFormat] = mapped_column(pg_enum(ReportFormat), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(
        pg_enum(ReportStatus),
        default=ReportStatus.PENDING,
        server_default=ReportStatus.PENDING.value,
        nullable=False,
    )
    file_url: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="reports")
