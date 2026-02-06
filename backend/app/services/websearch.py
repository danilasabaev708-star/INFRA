from __future__ import annotations

import asyncio
import random
import time
from typing import Any

import httpx

from app.core.config import get_settings

settings = get_settings()


class WebSearchError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class WebSearchClient:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()
        self._timestamps: list[float] = []

    def _purge_timestamps(self) -> None:
        cutoff = time.time() - 60
        self._timestamps = [ts for ts in self._timestamps if ts >= cutoff]

    async def search(self, query: str) -> list[dict[str, Any]]:
        async with self._lock:
            now = time.time()
            cached = self._cache.get(query)
            if cached and cached[0] > now:
                return cached[1]

            self._purge_timestamps()
            if len(self._timestamps) >= settings.global_rate_limit_per_minute:
                raise WebSearchError("Лимит запросов поиска исчерпан.")

            self._timestamps.append(now)
            results = await self._fetch(query)
            ttl_minutes = random.randint(settings.web_search_cache_minutes_min, settings.web_search_cache_minutes_max)
            ttl = ttl_minutes * 60
            self._cache[query] = (now + ttl, results)
            return results

    async def _fetch(self, query: str) -> list[dict[str, Any]]:
        if not settings.openserp_url:
            return []
        payload = {"q": query}
        backoff = 1
        async with httpx.AsyncClient(timeout=15) as client:
            for _ in range(3):
                response = await client.post(settings.openserp_url.rstrip("/") + "/search", json=payload)
                if response.status_code == 429:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])
        raise WebSearchError("Поиск временно недоступен.")


web_search_client = WebSearchClient()
