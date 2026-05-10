from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter

from app.api.mappers import to_source_response
from app.schemas.analysis import SourceResponse
from app.services.sources import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
@inject
async def list_sources(source_service: FromDishka[SourceService]) -> list[SourceResponse]:
    sources = await source_service.list_active()
    return [to_source_response(source) for source in sources]
