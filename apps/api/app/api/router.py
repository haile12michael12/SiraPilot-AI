"""API-level dependencies and route composition."""

from fastapi import APIRouter, Depends

from app.api.v1.router import router as v1_router
from app.platform.dependencies import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])
router.include_router(v1_router, prefix="/v1")
router.include_router(v1_router, include_in_schema=False)
