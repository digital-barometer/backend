from app.services.llm import LLMService
from db.models import Mention


class SentimentAnalyzer:
    def __init__(self, llm_service: LLMService) -> None:
        self._llm_service = llm_service

    async def apply(self, topic_name: str, mentions: list[Mention]) -> None:
        sentiment_results = await self._llm_service.analyze_mentions(topic_name, mentions)
        for mention, sentiment_result in zip(mentions, sentiment_results, strict=True):
            mention.sentiment = sentiment_result.sentiment
            mention.sentiment_score = sentiment_result.sentiment_score
            mention.emotion = sentiment_result.emotion
