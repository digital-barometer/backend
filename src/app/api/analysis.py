from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, HTTPException

from app.api.mappers import to_analysis_run_response, to_chart_response
from app.schemas.analysis import (
    AnalysisRunRequest,
    AnalysisRunResponse,
    ChartDataResponse,
)
from app.services.analysis import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("", response_model=AnalysisRunResponse)
@inject
async def run_analysis(
    payload: AnalysisRunRequest,
    analysis_service: FromDishka[AnalysisService],
) -> AnalysisRunResponse:
    try:
        analysis_run = await analysis_service.run(
            topic_id=payload.topic_id,
            date_from=payload.date_from,
            date_to=payload.date_to,
            source_ids=payload.source_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_analysis_run_response(analysis_run)


@router.get("/{analysis_id}", response_model=AnalysisRunResponse)
@inject
async def get_analysis(
    analysis_id: UUID,
    analysis_service: FromDishka[AnalysisService],
) -> AnalysisRunResponse:
    analysis_run = await analysis_service.get(analysis_id)
    if analysis_run is None:
        raise HTTPException(status_code=404, detail="analysis run not found")
    return to_analysis_run_response(analysis_run)


@router.get("/{analysis_id}/charts", response_model=ChartDataResponse)
@inject
async def get_charts(
    analysis_id: UUID,
    analysis_service: FromDishka[AnalysisService],
) -> ChartDataResponse:
    try:
        chart_data = await analysis_service.charts(analysis_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return to_chart_response(chart_data)
