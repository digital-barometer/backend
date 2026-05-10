import asyncio
import logging
import re
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.settings import Settings
from app.services.llm_prompts import (
    METRICS_SYSTEM_PROMPT,
    SENTIMENT_SYSTEM_PROMPT,
    build_metrics_user_prompt,
    build_sentiment_user_prompt,
)
from app.services.metrics import (
    barometer_label,
    barometer_value,
    emotion_counts,
    sentiment_counts,
    sentiment_score,
    trend_context,
    trend_phrase,
)
from db.enums import SentimentLabel
from db.models import Mention, TrendPoint

logger = logging.getLogger(__name__)

NEGATIVE_PATTERNS = (
    r"\bдтп\b",
    r"\bавари[яи]",
    r"\bнаехал[аи]?\b",
    r"\bсбил[аио]?\b",
    r"\bстолкнул",
    r"\bпострадал",
    r"\bпогиб",
    r"\bтравм",
    r"\bбольниц",
    r"\bзапрет",
    r"\bогранич",
    r"\bисчез",
    r"\bштраф",
    r"\bзамедл",
    r"\bжестк\w*\s+контрол",
    r"\bнельзя\s+кататься",
    r"\bобязательн\w*\s+получени\w*\s+прав",
    r"\bукрад",
    r"\bвзлом",
    r"\bопасн",
    r"\bжалоб",
    r"\bнаруш",
    r"\bпроблем",
    r"\bскандал",
    r"\bконфликт",
    r"\bриск",
    r"\bcrash\b",
    r"\bbad\b",
    r"\bfail",
)
POSITIVE_PATTERNS = (
    r"\bхорош",
    r"\bотлич",
    r"\bуспех",
    r"\bдовер",
    r"\bпредставил",
    r"\bзапуск",
    r"\bпоявил",
    r"\bрасшир",
    r"\bобустро",
    r"\bпарков",
    r"\bрост\s+спрос",
    r"\bвырос\w*\s+спрос",
    r"\bустран",
    r"\bрешил[аи]?\s+проблем",
    r"\bgood\b",
    r"\bgreat\b",
    r"\bsuccess",
)


@dataclass(slots=True)
class SentimentResult:
    sentiment: SentimentLabel
    sentiment_score: float | None = None
    emotion: str | None = None


@dataclass(slots=True)
class AnalysisMetricsResult:
    total_texts: int
    positive_count: int
    neutral_count: int
    negative_count: int
    unknown_count: int
    joy_count: int
    irritation_count: int
    fear_count: int
    trust_count: int
    surprise_count: int
    anger_count: int
    sentiment_score: Decimal | None
    barometer_value: Decimal | None
    barometer_label: str | None
    summary_short: str
    summary_detailed: str | None


BarometerLabel = Literal["негативная тенденция", "нейтральная", "позитивная"]
ALLOWED_EMOTIONS = {
    "радость",
    "раздражение",
    "страх",
    "доверие",
    "удивление",
    "злость",
    "неопределено",
}
EMOTION_ALIASES = {
    "разочарование": "раздражение",
    "недовольство": "раздражение",
    "тревога": "страх",
    "опасение": "страх",
    "гнев": "злость",
}


class StructuredSentimentItem(BaseModel):
    index: int
    sentiment: str = Field(description="positive, neutral, negative, or unknown")
    sentiment_score: float | None = None
    emotion: str | None = None


class StructuredSentimentBatch(BaseModel):
    items: list[StructuredSentimentItem]


class StructuredAnalysisMetrics(BaseModel):
    barometer_label: BarometerLabel
    summary_short: str
    summary_detailed: str


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sentiment_model = self._build_model(
            settings,
            settings.SENTIMENT_MODEL or settings.LANGCHAIN_MODEL or "gpt-4o-mini",
        )
        self._analysis_model = self._build_model(
            settings,
            settings.ANALYSIS_MODEL or settings.LANGCHAIN_MODEL or "gpt-4o-mini",
        )
        self._sentiment_semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENCY)

    async def analyze_mentions(
        self,
        topic_name: str,
        mentions: list[Mention],
    ) -> list[SentimentResult]:
        if not mentions:
            return []
        if self._sentiment_model is None:
            return [self._fallback_sentiment(topic_name, mention) for mention in mentions]

        batch_size = self._settings.LLM_SENTIMENT_BATCH_SIZE
        indexed_mentions = list(enumerate(mentions))
        batches = [
            indexed_mentions[index : index + batch_size]
            for index in range(0, len(indexed_mentions), batch_size)
        ]
        batch_results = await asyncio.gather(
            *[
                self._analyze_mentions_batch(topic_name, batch)
                for batch in batches
            ]
        )
        results = [SentimentResult(sentiment=SentimentLabel.UNKNOWN) for _ in mentions]
        for batch_result in batch_results:
            for index, sentiment_result in batch_result.items():
                results[index] = sentiment_result
        return results

    async def _analyze_mentions_batch(
        self,
        topic_name: str,
        indexed_mentions: list[tuple[int, Mention]],
    ) -> dict[int, SentimentResult]:
        payload = self._sentiment_payload(indexed_mentions)
        messages = [
            SystemMessage(content=SENTIMENT_SYSTEM_PROMPT),
            HumanMessage(content=build_sentiment_user_prompt(topic_name, payload)),
        ]

        async with self._sentiment_semaphore:
            try:
                structured_model = self._with_structured_output(
                    self._sentiment_model,
                    StructuredSentimentBatch,
                )
                response = await structured_model.ainvoke(messages)
                return self._map_sentiment_response(
                    response=response,
                    expected_indexes=[index for index, _ in indexed_mentions],
                )
            except Exception:
                logger.warning(
                    "LLM sentiment batch analysis failed, using keyword fallback",
                    exc_info=True,
                )
                return {
                    index: self._fallback_sentiment(topic_name, mention)
                    for index, mention in indexed_mentions
                }

    async def build_analysis_metrics(
        self,
        topic_name: str,
        mentions: list[Mention],
        trend_points: list[TrendPoint],
    ) -> AnalysisMetricsResult:
        fallback = self._fallback_metrics(topic_name, mentions, trend_points)
        if self._analysis_model is None:
            return fallback

        context = self._metrics_context(topic_name, mentions, trend_points)
        messages = [
            SystemMessage(content=METRICS_SYSTEM_PROMPT),
            HumanMessage(content=build_metrics_user_prompt(context)),
        ]

        try:
            structured_model = self._with_structured_output(
                self._analysis_model,
                StructuredAnalysisMetrics,
            )
            response = await structured_model.ainvoke(messages)
            return self._map_metrics_response(response=response, fallback=fallback)
        except Exception:
            return fallback

    def _with_structured_output(self, model: ChatOpenAI | None, schema: type[BaseModel]):
        if model is None:
            raise RuntimeError("LLM model is not configured")
        return model.with_structured_output(
            schema,
            method=self._settings.LLM_STRUCTURED_OUTPUT_METHOD,
        )

    @staticmethod
    def _build_model(settings: Settings, model_name: str) -> ChatOpenAI | None:
        if not settings.OPENAI_API_KEY:
            return None
        return ChatOpenAI(
            model=model_name,
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
        )

    @staticmethod
    def _map_sentiment_response(
        response: StructuredSentimentBatch,
        expected_indexes: list[int],
    ) -> dict[int, SentimentResult]:
        by_index = {item.index: item for item in response.items}
        results: dict[int, SentimentResult] = {}
        for index in expected_indexes:
            item = by_index.get(index)
            if item is None:
                results[index] = SentimentResult(sentiment=SentimentLabel.UNKNOWN)
                continue
            results[index] = SentimentResult(
                sentiment=LLMService._coerce_sentiment(item.sentiment),
                sentiment_score=LLMService._coerce_sentiment_score(item.sentiment_score),
                emotion=LLMService._coerce_emotion(item.emotion),
            )
        return results

    @staticmethod
    def _coerce_sentiment(value: object) -> SentimentLabel:
        if not isinstance(value, str):
            return SentimentLabel.UNKNOWN
        try:
            return SentimentLabel(value)
        except ValueError:
            return SentimentLabel.UNKNOWN

    @staticmethod
    def _coerce_sentiment_score(value: object) -> float | None:
        if not isinstance(value, int | float):
            return None
        return max(-1.0, min(1.0, float(value)))

    @staticmethod
    def _coerce_emotion(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        normalized = EMOTION_ALIASES.get(normalized, normalized)
        if normalized in ALLOWED_EMOTIONS:
            return normalized
        return "неопределено"

    @staticmethod
    def _fallback_sentiment(topic_name: str, mention: Mention) -> SentimentResult:
        text = f"{mention.title or ''} {mention.text or ''}".lower()

        if not text.strip():
            return SentimentResult(SentimentLabel.UNKNOWN)
        if not LLMService._is_topic_related(topic_name, text):
            return SentimentResult(SentimentLabel.UNKNOWN)

        if LLMService._matches_any(text, NEGATIVE_PATTERNS):
            return SentimentResult(SentimentLabel.NEGATIVE, -0.6, "раздражение")
        if LLMService._matches_any(text, POSITIVE_PATTERNS):
            return SentimentResult(SentimentLabel.POSITIVE, 0.5, "доверие")
        return SentimentResult(SentimentLabel.NEUTRAL, 0.0, "неопределено")

    @staticmethod
    def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _is_topic_related(topic_name: str, text: str) -> bool:
        topic_tokens = re.findall(r"[a-zа-яё0-9]+", topic_name.lower())
        if not topic_tokens:
            return False

        for token in LLMService._topic_alias_tokens(topic_tokens):
            candidates = {token}
            if len(token) > 5:
                candidates.add(token[:-1])
            if len(token) > 7:
                candidates.add(token[:-2])
                candidates.add(token[:-3])
            if any(
                LLMService._contains_topic_candidate(text, candidate)
                for candidate in candidates
            ):
                return True
        return False

    @staticmethod
    def _contains_topic_candidate(text: str, candidate: str) -> bool:
        if not candidate:
            return False
        if len(candidate) <= 4:
            return re.search(rf"\b{re.escape(candidate)}\b", text) is not None
        return candidate in text

    @staticmethod
    def _topic_alias_tokens(topic_tokens: list[str]) -> set[str]:
        aliases = set(topic_tokens)
        if any("электросамокат" in token for token in topic_tokens):
            aliases.update(
                {
                    "самокат",
                    "самокаты",
                    "сим",
                    "средство",
                    "средства",
                    "индивидуальной",
                    "мобильности",
                }
            )
        return aliases

    @staticmethod
    def _sentiment_payload(
        indexed_mentions: list[tuple[int, Mention]],
    ) -> list[dict[str, object]]:
        return [
            {
                "index": index,
                "title": mention.title,
                "text": mention.text,
            }
            for index, mention in indexed_mentions
        ]

    @staticmethod
    def _metrics_context(
        topic_name: str,
        mentions: list[Mention],
        trend_points: list[TrendPoint],
    ) -> dict[str, object]:
        return {
            "topic": topic_name,
            "mentions_count": len(mentions),
            "sentiment_counts": sentiment_counts(mentions),
            "trend": trend_context(trend_points),
        }

    @staticmethod
    def _fallback_metrics(
        topic_name: str,
        mentions: list[Mention],
        trend_points: list[TrendPoint],
    ) -> AnalysisMetricsResult:
        search_trend_phrase = trend_phrase(trend_points)
        counts = sentiment_counts(mentions)
        positive_count = counts.get("positive", 0)
        neutral_count = counts.get("neutral", 0)
        negative_count = counts.get("negative", 0)
        unknown_count = counts.get("unknown", 0)
        total_texts = len(mentions)
        score = sentiment_score(total_texts, positive_count, negative_count)
        value = barometer_value(score)
        label = barometer_label(value)

        emotions = emotion_counts(mentions)
        summary_short = (
            f"Анализ по теме «{topic_name}» выявил: {search_trend_phrase}, "
            f"найдено {total_texts} упоминаний, тенденция: {label}."
        )
        return AnalysisMetricsResult(
            total_texts=total_texts,
            positive_count=positive_count,
            neutral_count=neutral_count,
            negative_count=negative_count,
            unknown_count=unknown_count,
            joy_count=emotions.get("радость", 0),
            irritation_count=emotions.get("раздражение", 0),
            fear_count=emotions.get("страх", 0),
            trust_count=emotions.get("доверие", 0),
            surprise_count=emotions.get("удивление", 0),
            anger_count=emotions.get("злость", 0),
            sentiment_score=score,
            barometer_value=value,
            barometer_label=label,
            summary_short=summary_short,
            summary_detailed=summary_short,
        )

    @staticmethod
    def _map_metrics_response(
        response: StructuredAnalysisMetrics,
        fallback: AnalysisMetricsResult,
    ) -> AnalysisMetricsResult:
        return replace(
            fallback,
            summary_short=response.summary_short or fallback.summary_short,
            summary_detailed=response.summary_detailed or fallback.summary_detailed,
        )
