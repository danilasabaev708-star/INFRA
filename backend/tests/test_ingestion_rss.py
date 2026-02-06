from __future__ import annotations

import time

import pytest
from sqlalchemy import func, select

from app.models.item import Item
from app.models.source import Source
from app.services import ingestion


class DummyFeed:
    def __init__(self, entries: list[dict], feed: dict | None = None):
        self.entries = entries
        self.feed = feed or {}


@pytest.mark.asyncio
async def test_ingest_rss_source_inserts_items(session, monkeypatch):
    source = Source(name="rss", source_type="rss", url="http://example.com/rss")
    session.add(source)
    await session.commit()
    await session.refresh(source)

    entries = [
        {
            "title": "Test entry",
            "link": "http://example.com/1",
            "summary": "Body",
            "id": "1",
            "published_parsed": time.gmtime(1_700_000_000),
        }
    ]
    feed = DummyFeed(entries, feed={"language": "en"})
    monkeypatch.setattr(ingestion.feedparser, "parse", lambda url: feed)

    added = await ingestion.ingest_rss_source(session, source)
    assert added == 1
    await session.commit()

    count = (await session.execute(select(func.count()).select_from(Item))).scalar_one()
    assert count == 1
    await session.refresh(source)
    assert source.state and source.state.get("last_published_at")

    added_again = await ingestion.ingest_rss_source(session, source)
    assert added_again == 0
