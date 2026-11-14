"""Compose the configured API, runtime resources and built dashboard."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI

from app.api.router import router as api_router
from app.config import Settings, get_settings
from app.core.build_info import installed_info
from app.core.paths import settings_paths
from app.core.version import PRODUCT_VERSION
from app.infra.postgres.config import AuthSettings, load_postgres_settings
from app.infra.postgres.sessions import PostgresDatabase
from app.infra.periodic import PeriodicWorker
from app.infra.transactions import transaction
from app.infra.web_push import WebPushSender
from app.modules.notifications.worker import cycle as notification_cycle
from app.modules.preferences.schemas import ApplicationStaleness
from app.modules.preferences.service import initialize_staleness
from app.modules.staleness import service as staleness
from app.platform.errors import ErrorResponse
from app.platform.http import DashboardStaticFiles, configure_http
from app.platform.logging import configure_logging
from app.platform.runtime import RuntimeResources, open_runtime


def create_app(settings: Settings, *, resources: RuntimeResources | None = None) -> FastAPI:
    """Build an isolated app; its lifespan owns the selected profile's resources."""
    resources = resources or RuntimeResources(settings_paths(settings))
    paths = resources.paths
    build_info = installed_info(paths.app_dir, packaged=paths.profile == "packaged")
    auth_settings = AuthSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging()
        postgres_settings = load_postgres_settings()
        postgres_database: PostgresDatabase | None = None
        if postgres_settings.database_url is not None:
            auth_settings.require_ready()
            postgres_database = PostgresDatabase(postgres_settings)
        app.state.postgres_database = postgres_database
        try:
            with open_runtime(settings, resources, build_info):
                with transaction(resources.database()) as conn:
                    initialize_staleness(
                        conn,
                        ApplicationStaleness(
                            applied_days=settings.attention_applied_days,
                            in_process_days=settings.attention_in_process_days,
                            timezone=settings.stale_notification_timezone,
                        ),
                    )
                    staleness.reconcile(conn)

                def committed() -> None:
                    if resources.push_scheduler is not None:
                        resources.push_scheduler.notify_write()

                committed()
                resources.web_push = (
                    WebPushSender(
                        paths.state_dir / "web-push-private.pem", settings.web_push_subject
                    )
                    if settings.web_push_enabled
                    else None
                )
                resources.notification_worker = PeriodicWorker(
                    partial(
                        notification_cycle,
                        resources.database(),
                        resources.notification_hub,
                        committed,
                        scheduler_enabled=settings.notification_scheduler_enabled,
                        known={},
                        push_sender=resources.web_push,
                    )
                )
                resources.notification_worker.start()
                yield
        finally:
            app.state.postgres_database = None
            if postgres_database is not None:
                postgres_database.close()

    app = FastAPI(
        title="Job Tracker API",
        version=PRODUCT_VERSION,
        lifespan=lifespan,
        responses={
            status: {"model": ErrorResponse}
            for status in (400, 401, 403, 404, 405, 409, 413, 422, 429, 500, 503)
        },
    )
    app.state.settings = settings
    app.state.resources = resources
    app.state.auth_settings = auth_settings
    app.state.postgres_database = None
    app.state.build_info = build_info
    configure_http(app, settings)

    # Keep the existing public /api path while routing ownership moves to app.api.
    app.include_router(api_router, prefix="/api")

    # API and identity routes win over the optional dashboard.
    if paths.web_dist.is_dir():
        app.mount("/", DashboardStaticFiles(directory=paths.web_dist, html=True), name="dashboard")
    return app


app = create_app(get_settings())
