import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError


class RateLimiter:
    def __init__(self, redis_client: Redis | None, *, local: bool = False) -> None:
        self._redis = redis_client
        self._local = local
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        if self._local:
            now = time.monotonic()
            window = self._hits[key]
            while window and now - window[0] >= window_seconds:
                window.popleft()
            if len(window) >= limit:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests")
            window.append(now)
            return

        if self._redis is None:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Service unavailable")
        try:
            pipeline = self._redis.pipeline(transaction=True)
            pipeline.incr(key)
            pipeline.expire(key, window_seconds)
            count, _ = pipeline.execute()
        except RedisError as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Service unavailable"
            ) from exc
        if count > limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests")


def rate_limit(scope: str, limit: int | None = None) -> Callable:
    def dependency(request: Request) -> None:
        settings = request.app.state.settings
        remote = request.client.host if request.client else "unknown"
        request.app.state.rate_limiter.check(
            f"rate-limit:{scope}:{remote}",
            limit or settings.auth_rate_limit,
            settings.auth_rate_limit_window_seconds,
        )

    return dependency