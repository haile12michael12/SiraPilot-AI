import structlog
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", summary="Check API and database readiness")
def endpoint(request: Request) -> JSONResponse:
    engine = request.app.state.db_engine
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("database_readiness_check_failed")
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unavailable"},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "database": "connected"},
    )
