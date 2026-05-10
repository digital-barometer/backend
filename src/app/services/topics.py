from app.core.slug import make_slug
from app.repositories.topics import TopicRepository
from db.models import Topic


class TopicService:
    def __init__(self, topic_repository: TopicRepository) -> None:
        self._topic_repository = topic_repository

    async def get_or_create(self, query: str) -> Topic:
        name = " ".join(query.strip().split())
        slug = make_slug(name)

        topic = await self._topic_repository.get_by_slug(slug)
        if topic is not None:
            return topic

        topic = Topic(name=name, slug=slug, keywords=[name])
        return await self._topic_repository.add(topic)

    async def list_active(self) -> list[Topic]:
        return await self._topic_repository.list_active()
