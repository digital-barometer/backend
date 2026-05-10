from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter

from app.api.mappers import to_topic_response
from app.schemas.analysis import TopicResponse
from app.services.topics import TopicService

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicResponse])
@inject
async def list_topics(topic_service: FromDishka[TopicService]) -> list[TopicResponse]:
    topics = await topic_service.list_active()
    return [to_topic_response(topic) for topic in topics]
