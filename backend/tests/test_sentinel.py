from __future__ import annotations

import pytest

from app.models.item import Item
from app.models.source import Source
from app.services.ingestion import compute_content_hash
from app.services.sentinel import apply_sentinel


@pytest.mark.asyncio
async def test_sentinel_populates_fields(session):
    source = Source(name="rss", source_type="rss", url="http://example.com/rss", trust_manual=70)
    session.add(source)
    await session.commit()
    await session.refresh(source)

    item = Item(
        source_id=source.id,
        external_id="1",
        url="http://example.com/1",
        title="Сделка на миллиард",
        text="Компания объявила о сделке на миллиард рублей.",
        published_at=None,
        content_hash=compute_content_hash("Сделка на миллиард", "http://example.com/1", "Компания"),
        lang="ru",
        is_job=False,
    )
    session.add(item)
    await session.flush()

    artifacts = await apply_sentinel(item, source)
    await session.commit()

    assert item.trust_score is not None
    assert item.trust_status in {"confirmed", "mixed", "unclear", "hype"}
    assert item.impact in {"low", "medium", "high"}
    assert artifacts.get("cross_check") is not None
    assert artifacts.get("logic_audit") is not None
    assert artifacts.get("entity_verify") is not None
    assert artifacts.get("trust_ledger") is not None
