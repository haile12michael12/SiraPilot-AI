from celery import Celery, Task

from app.core.config import get_settings

settings = get_settings()


class RetryableTask(Task):
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True
    max_retries = 3


celery_app = Celery(
    "sirapilot",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.Task = RetryableTask
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    enable_utc=True,
    timezone="UTC",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={},
)
