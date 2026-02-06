from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.item import Item, ItemTopic
from app.models.source import Source
from app.models.topic import Topic
from app.services.autotagging import assign_topics
from app.services.ingestion import compute_content_hash


@pytest.mark.asyncio
async def test_autotagging_respects_locked_topics(session):
    source = Source(name="rss", source_type="rss", url="http://example.com/rss")
    topic_locked = Topic(name="Finance", keywords=["bank", "loan"])
    topic_auto = Topic(name="Tech", keywords=["ai", "ml"])
    session.add_all([source, topic_locked, topic_auto])
    await session.commit()
    await session.refresh(source)
    await session.refresh(topic_locked)
    await session.refresh(topic_auto)

    title = "AI banking update"
    text = "AI solutions help the bank to reduce risk."
    url = "http://example.com/1"
    item = Item(
        source_id=source.id,
        external_id="1",
        url=url,
        title=title,
        text=text,
        published_at=None,
        content_hash=compute_content_hash(title, url, text),
        lang="en",
        is_job=False,
    )
    session.add(item)
    await session.flush()

    locked_topic = ItemTopic(
        item_id=item.id,
        topic_id=topic_locked.id,
        locked=True,
        score=0.9,
        assigned_by="admin",
    )
    session.add(locked_topic)
    await session.commit()

    await assign_topics(session, item)
    await session.commit()

    rows = (
        await session.execute(select(ItemTopic).where(ItemTopic.item_id == item.id))
    ).scalars().all()
    locked_ids = {row.topic_id for row in rows if row.locked}
    assert topic_locked.id in locked_ids
    assert any(row.topic_id == topic_auto.id for row in rows)
