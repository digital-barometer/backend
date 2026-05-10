from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Topic


class TopicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_slug(self, slug: str) -> Topic | None:
        result = await self._session.execute(select(Topic).where(Topic.slug == slug))
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Topic]:
        result = await self._session.execute(
            select(Topic).where(Topic.is_active.is_(True)).order_by(Topic.name)
        )
        return list(result.scalars().all())

    async def add(self, topic: Topic) -> Topic:
        self._session.add(topic)
        await self._session.flush()
        return topic
