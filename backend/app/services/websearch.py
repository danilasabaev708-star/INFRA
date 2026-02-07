from __future__ import annotations

import asyncio
import random
import time
from urllib.parse import urlparse
from typing import Any

import httpx

from app.core.config import get_settings

settings = get_settings()


class WebSearchError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class WebSearchClient:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()
        self._timestamps: list[float] = []

    def _purge_timestamps(self) -> None:
        cutoff = time.time() - 60
        self._timestamps = [ts for ts in self._timestamps if ts >= cutoff]

    def _purge_cache(self, now: float) -> None:
        expired = [query for query, (expires_at, _) in self._cache.items() if expires_at <= now]
        for query in expired:
            self._cache.pop(query, None)

    def _openserp_base_url(self) -> str | None:
        if not settings.openserp_url:
            return None
        parsed = urlparse(settings.openserp_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise WebSearchError("Некорректный URL поиска.")
        return settings.openserp_url.rstrip("/")

    async def search(self, query: str) -> list[dict[str, Any]]:
        async with self._lock:
            now = time.time()
            self._purge_cache(now)
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
        base_url = self._openserp_base_url()
        if not base_url:
            return []
        payload = {"q": query}
        backoff = 1
        timeout = httpx.Timeout(settings.openserp_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            for _ in range(3):
                try:
                    response = await client.post(f"{base_url}/search", json=payload)
                except httpx.RequestError:
                    await asyncio.sleep(backoff + random.random())
                    backoff *= 2
                    continue
                status_code = response.status_code
                if 200 <= status_code < 300:
                    data = response.json()
                    return data.get("results", [])
                if status_code == 429 or status_code >= 500:
                    await asyncio.sleep(backoff + random.random())
                    backoff *= 2
                    continue
                if 300 <= status_code < 400:
                    raise WebSearchError("Поиск вернул редирект.")
                response.raise_for_status()
        raise WebSearchError("Поиск временно недоступен.")


web_search_client = WebSearchClient()
