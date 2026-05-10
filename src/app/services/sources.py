from db.models import Source
from app.repositories.sources import SourceRepository
from uuid import UUID


class SourceService:
    def __init__(self, source_repository: SourceRepository) -> None:
        self._source_repository = source_repository

    async def list_active(self) -> list[Source]:
        return await self._source_repository.list_active()

    async def get_by_ids(self, source_ids: list[UUID]) -> list[Source]:
        return await self._source_repository.get_active_by_ids(source_ids)
