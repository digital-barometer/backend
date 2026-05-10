import enum


class SourceType(enum.StrEnum):
    SEARCH_TREND = "search_trend"
    SOCIAL = "social"
    VIDEO = "video"
    NEWS = "news"
    REVIEW = "review"
    MARKETPLACE = "marketplace"
    FORUM = "forum"
    STATISTICS = "statistics"
    MAP_REVIEW = "map_review"


class AnalysisStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class SentimentLabel(enum.StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ReportFormat(enum.StrEnum):
    PDF = "pdf"
    XLSX = "xlsx"
    CSV = "csv"


class ReportStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
