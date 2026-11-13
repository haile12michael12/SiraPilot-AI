"""First-generation feature routes."""

from fastapi import APIRouter

from app.modules.application_workflows.router import router as application_workflows_router
from app.modules.blocked.router import router as blocked_router
from app.modules.documents.router import router as documents_router
from app.modules.events.router import router as events_router
from app.modules.form_fill.router import router as form_fill_router
from app.modules.jobs.router import router as jobs_router
from app.modules.listings.router import router as listings_router
from app.modules.meta.router import router as meta_router
from app.modules.notifications.router import router as notifications_router
from app.modules.preferences.router import router as preferences_router
from app.modules.search_log.router import router as search_log_router
from app.modules.stats.router import router as stats_router

router = APIRouter()
for feature_router in (
    jobs_router,
    application_workflows_router,
    listings_router,
    events_router,
    documents_router,
    stats_router,
    search_log_router,
    meta_router,
    blocked_router,
    form_fill_router,
    preferences_router,
    notifications_router,
):
    router.include_router(feature_router)
