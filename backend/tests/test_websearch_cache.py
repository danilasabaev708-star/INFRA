from __future__ import annotations

import pytest

from app.services import websearch
from app.services.websearch import WebSearchClient


@pytest.mark.asyncio
async def test_websearch_cache_eviction(monkeypatch):
    client = WebSearchClient()
    websearch.settings.web_search_cache_max_entries = 2
    websearch.settings.web_search_cache_minutes_min = 1
    websearch.settings.web_search_cache_minutes_max = 1

    async def fake_fetch(query: str):
        return [{"title": query, "url": f"http://example.com/{query}"}]

    monkeypatch.setattr(client, "_fetch", fake_fetch)

    await client.search("first")
    await client.search("second")
    await client.search("third")

    assert len(client._cache) == 2
    assert "first" not in client._cache
