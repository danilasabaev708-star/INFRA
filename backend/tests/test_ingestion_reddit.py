from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.item import Item
from app.models.source import Source
from app.services import ingestion


class DummySubmission:
    def __init__(self, submission_id: str, title: str, text: str, url: str, created_utc: float):
        self.id = submission_id
        self.title = title
        self.selftext = text
        self.url = url
        self.created_utc = created_utc


@pytest.mark.asyncio
async def test_ingest_reddit_inserts_items(session, monkeypatch):
    source = Source(name="reddit", source_type="reddit", url="r/testsub")
    session.add(source)
    await session.commit()

    submissions = [
        DummySubmission("b", "Second post", "Body", "http://example.com/2", 200.0),
        DummySubmission("a", "First post", "", "http://example.com/1", 100.0),
    ]

    class DummySubreddit:
        def __init__(self, items):
            self._items = items

        def new(self, limit=100):
            async def generator():
                for item in self._items:
                    yield item

            return generator()

    class DummyReddit:
        def __init__(self, *args, **kwargs):
            self._items = submissions

        def subreddit(self, name):
            return DummySubreddit(self._items)

        async def close(self):
            return None

    monkeypatch.setattr(ingestion.asyncpraw, "Reddit", DummyReddit)
    ingestion.settings.reddit_client_id = "client"
    ingestion.settings.reddit_client_secret = "secret"
    ingestion.settings.reddit_user_agent = "agent"

    result = await ingestion.ingest_reddit(session)
    assert result.items_processed == 2
    await session.commit()

    count = (await session.execute(select(func.count()).select_from(Item))).scalar_one()
    assert count == 2
    await session.refresh(source)
    assert source.state and source.state["last_created_utc"] == 200.0
    assert source.state["last_post_id"] == "b"

    result_again = await ingestion.ingest_reddit(session)
    assert result_again.items_processed == 0
    count_again = (await session.execute(select(func.count()).select_from(Item))).scalar_one()
    assert count_again == 2
