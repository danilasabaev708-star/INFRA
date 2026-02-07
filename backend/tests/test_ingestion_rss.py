from __future__ import annotations

import time

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

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


@pytest.mark.asyncio
async def test_ingest_rss_source_marks_jobs(session, monkeypatch):
    source = Source(
        name="jobs",
        source_type="rss",
        url="http://example.com/jobs",
        job_keywords=["вакансия", "hiring"],
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)

    entries = [
        {
            "title": "Hiring backend engineer",
            "link": "http://example.com/jobs/1",
            "summary": "Открыта вакансия в команде.",
            "id": "job-1",
            "published_parsed": time.gmtime(1_700_000_100),
        }
    ]
    feed = DummyFeed(entries, feed={"language": "ru"})
    monkeypatch.setattr(ingestion.feedparser, "parse", lambda url: feed)

    added = await ingestion.ingest_rss_source(session, source)
    assert added == 1
    await session.commit()

    item = (await session.execute(select(Item).order_by(Item.id.desc()))).scalars().first()
    assert item is not None
    assert item.is_job is True


@pytest.mark.asyncio
async def test_ingest_rss_handles_integrity_error(session, monkeypatch):
    source = Source(name="rss", source_type="rss", url="http://example.com/rss")
    session.add(source)
    await session.commit()
    await session.refresh(source)

    entries = [
        {
            "title": "First entry",
            "link": "http://example.com/1",
            "summary": "Body",
            "id": "1",
            "published_parsed": time.gmtime(1_700_000_000),
        },
        {
            "title": "Second entry",
            "link": "http://example.com/2",
            "summary": "Body",
            "id": "2",
            "published_parsed": time.gmtime(1_700_000_100),
        },
    ]
    feed = DummyFeed(entries, feed={"language": "en"})
    monkeypatch.setattr(ingestion.feedparser, "parse", lambda url: feed)

    original_flush = session.flush
    call_count = 0

    async def flaky_flush(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise IntegrityError("stmt", "params", None)
        return await original_flush(*args, **kwargs)

    monkeypatch.setattr(session, "flush", flaky_flush)

    added = await ingestion.ingest_rss_source(session, source)
    assert added == 1
