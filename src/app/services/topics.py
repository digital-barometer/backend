from uuid import UUID

from app.core.slug import make_slug
from app.repositories.topics import TopicRepository
from db.models import Topic


class TopicService:
    def __init__(self, topic_repository: TopicRepository) -> None:
        self._topic_repository = topic_repository

    async def create(self, name: str, keywords: list[str]) -> Topic:
        name = normalize_topic_name(name)
        slug = make_slug(name)
        keywords = normalize_topic_keywords(keywords)

        topic = await self._topic_repository.get_by_slug(slug)
        if topic is not None:
            raise ValueError(f"Topic already exists: {slug}")

        topic = Topic(name=name, slug=slug, keywords=keywords, is_active=True)
        return await self._topic_repository.add(topic)

    async def get_active_by_id(self, topic_id: UUID) -> Topic | None:
        return await self._topic_repository.get_active_by_id(topic_id)

    async def update_keywords(self, topic_id: UUID, keywords: list[str]) -> Topic:
        topic = await self._topic_repository.get_active_by_id(topic_id)
        if topic is None:
            raise LookupError("topic not found")
        topic.keywords = normalize_topic_keywords(keywords)
        return topic

    async def list_active(self) -> list[Topic]:
        return await self._topic_repository.list_active()


def normalize_topic_name(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_topic_keywords(keywords: list[str]) -> list[str]:
    values = [
        item
        for item in keywords
        if item and item.strip()
    ]
    normalized = [" ".join(item.strip().split()) for item in values]
    return list(dict.fromkeys(normalized))
