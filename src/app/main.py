from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from app.api.analysis import router as analysis_router
from app.api.health import router as health_router
from app.api.sources import router as sources_router
from app.api.topics import router as topics_router
from app.core.container import create_container
from app.core.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)
    app.include_router(health_router)
    app.include_router(sources_router)
    app.include_router(topics_router)
    app.include_router(analysis_router)
    setup_dishka(create_container(), app)
    return app


app = create_app()
