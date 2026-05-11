from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, HTTPException

from app.api.mappers import to_topic_response
from app.schemas.analysis import TopicCreateRequest, TopicResponse, TopicUpdateRequest
from app.services.topics import TopicService

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("", response_model=TopicResponse)
@inject
async def create_topic(
    payload: TopicCreateRequest,
    topic_service: FromDishka[TopicService],
) -> TopicResponse:
    try:
        topic = await topic_service.create(payload.name, payload.keywords)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return to_topic_response(topic)


@router.patch("/{topic_id}", response_model=TopicResponse)
@inject
async def update_topic(
    topic_id: UUID,
    payload: TopicUpdateRequest,
    topic_service: FromDishka[TopicService],
) -> TopicResponse:
    try:
        topic = await topic_service.update_keywords(topic_id, payload.keywords)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return to_topic_response(topic)


@router.get("", response_model=list[TopicResponse])
@inject
async def list_topics(topic_service: FromDishka[TopicService]) -> list[TopicResponse]:
    topics = await topic_service.list_active()
    return [to_topic_response(topic) for topic in topics]
