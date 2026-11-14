"""API-level dependencies and route composition."""

from fastapi import APIRouter, Depends

from app.api.v1.router import router as v1_router
from app.modules.auth.router import router as auth_router
from app.platform.dependencies import require_api_key

router = APIRouter()
router.include_router(auth_router, prefix="/v1")

private_router = APIRouter(dependencies=[Depends(require_api_key)])
private_router.include_router(v1_router, prefix="/v1")
private_router.include_router(v1_router, include_in_schema=False)
router.include_router(private_router)
