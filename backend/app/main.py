from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.engine import Engine

from app.api.v1.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.database import create_db_engine
from app.core.logging import configure_logging

logger = structlog.get_logger(__name__)


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    config = settings or get_settings()
    configure_logging(config.log_level)
    db_engine = engine or create_db_engine(config.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        db_engine.dispose()

    application = FastAPI(
        title=config.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.db_engine = db_engine
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.include_router(health_router, prefix=config.api_v1_prefix)

    @application.get("/health/live", include_in_schema=False)
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", include_in_schema=False)
    def readiness(request: Request) -> JSONResponse:
        return health_router.endpoint(request)

    @application.exception_handler(Exception)
    async def unhandled_exception(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "unhandled_application_error",
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return application


app = create_app()
