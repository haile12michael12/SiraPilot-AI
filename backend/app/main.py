from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy.engine import Engine

from app.api.v1.auth import router as auth_router
from app.api.v1.career_profile import router as career_profile_router
from app.api.v1.cv import router as cv_router
from app.api.v1.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.database import create_db_engine, create_session_factory
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimiter

logger = structlog.get_logger(__name__)


def create_app(
    settings: Settings | None = None,
    engine: Engine | None = None,
) -> FastAPI:
    config = settings or get_settings()
    configure_logging(config.log_level)
    db_engine = engine or create_db_engine(config.database_url)
    redis_client = (
        None
        if config.app_env == "test"
        else Redis.from_url(config.redis_url, decode_responses=True)
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        db_engine.dispose()
        if redis_client is not None:
            redis_client.close()

    application = FastAPI(
        title=config.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.db_engine = db_engine
    application.state.session_factory = create_session_factory(db_engine)
    application.state.settings = config
    application.state.rate_limiter = RateLimiter(
        redis_client,
        local=config.app_env == "test",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
    application.include_router(health_router, prefix=config.api_v1_prefix)
    application.include_router(auth_router, prefix=config.api_v1_prefix)
    application.include_router(career_profile_router, prefix=config.api_v1_prefix)
    application.include_router(cv_router, prefix=config.api_v1_prefix)

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
