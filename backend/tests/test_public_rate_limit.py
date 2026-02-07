from __future__ import annotations

import pytest

from app.core.public_rate_limit import InMemoryRateLimiter


@pytest.mark.asyncio
async def test_public_rate_limit_exceeded():
    limiter = InMemoryRateLimiter()
    key = "ip:127.0.0.1"
    assert await limiter.allow(key, limit=2, window_seconds=60)
    assert await limiter.allow(key, limit=2, window_seconds=60)
    assert not await limiter.allow(key, limit=2, window_seconds=60)
