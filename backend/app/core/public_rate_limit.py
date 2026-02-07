from __future__ import annotations

import asyncio
import time

from fastapi import Header, HTTPException, Request, status

from app.core.config import get_settings
from app.core.security import validate_init_data


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        if limit <= 0:
            return True
        now = time.time()
        cutoff = now - window_seconds
        async with self._lock:
            timestamps = [ts for ts in self._events.get(key, []) if ts >= cutoff]
            if len(timestamps) >= limit:
                self._events[key] = timestamps
                return False
            timestamps.append(now)
            self._events[key] = timestamps
            return True

    def clear(self) -> None:
        self._events.clear()


public_rate_limiter = InMemoryRateLimiter()


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


async def enforce_public_rate_limit(
    request: Request,
    init_data: str | None = Header(default=None, alias="X-Init-Data"),
) -> None:
    settings = get_settings()
    limit = settings.public_rate_limit_per_minute
    window_seconds = settings.public_rate_limit_window_seconds
    keys = [f"ip:{_client_ip(request)}"]
    if init_data:
        try:
            parsed = validate_init_data(init_data, settings.bot_token, check_replay=False)
        except ValueError:
            parsed = None
        if parsed:
            keys.append(f"user:{parsed.user_id}")
    for key in keys:
        allowed = await public_rate_limiter.allow(key, limit, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов. Попробуйте позже.",
            )
