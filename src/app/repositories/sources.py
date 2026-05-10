from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from db.models import Source


class SourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_active(self) -> list[Source]:
        result = await self._session.execute(
            select(Source).where(Source.is_active.is_(True)).order_by(Source.name)
        )
        return list(result.scalars().all())

    async def get_active_by_ids(self, source_ids: list[UUID]) -> list[Source]:
        result = await self._session.execute(
            select(Source).where(Source.id.in_(source_ids), Source.is_active.is_(True))
        )
        return list(result.scalars().all())
