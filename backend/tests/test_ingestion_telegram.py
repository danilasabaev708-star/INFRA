from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.models.item import Item
from app.models.source import Source
from app.services import ingestion


class DummyEntity:
    username = "demo"
    title = "Demo Channel"


class DummyMessage:
    def __init__(self, message_id: int, text: str, date: datetime):
        self.id = message_id
        self.message = text
        self.text = text
        self.date = date


@pytest.mark.asyncio
async def test_ingest_telegram_inserts_items(session, monkeypatch):
    source = Source(name="telegram", source_type="telegram", url="@demo")
    session.add(source)
    await session.commit()

    messages = [
        DummyMessage(1, "First message", datetime(2024, 1, 1, tzinfo=timezone.utc)),
        DummyMessage(2, "Second message", datetime(2024, 1, 2, tzinfo=timezone.utc)),
    ]

    class DummyTelegramClient:
        def __init__(self, *args, **kwargs):
            self._messages = messages

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get_entity(self, identifier):
            return DummyEntity()

        def iter_messages(self, entity, min_id=0, reverse=True, limit=100):
            async def generator():
                for message in self._messages:
                    if min_id and message.id <= min_id:
                        continue
                    yield message

            return generator()

    monkeypatch.setattr(ingestion, "TelegramClient", DummyTelegramClient)
    ingestion.settings.telethon_api_id = 123
    ingestion.settings.telethon_api_hash = "hash"
    ingestion.settings.telethon_session = "session"

    result = await ingestion.ingest_telegram(session)
    assert result.items_processed == 2
    await session.commit()

    count = (await session.execute(select(func.count()).select_from(Item))).scalar_one()
    assert count == 2
    await session.refresh(source)
    assert source.state and source.state["last_message_id"] == 2

    result_again = await ingestion.ingest_telegram(session)
    assert result_again.items_processed == 0
    count_again = (await session.execute(select(func.count()).select_from(Item))).scalar_one()
    assert count_again == 2
