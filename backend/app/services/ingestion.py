from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IngestionResult:
    source: str
    items_processed: int


async def ingest_telegram() -> IngestionResult:
    return IngestionResult(source="telegram", items_processed=0)


async def ingest_reddit() -> IngestionResult:
    return IngestionResult(source="reddit", items_processed=0)


async def ingest_rss() -> IngestionResult:
    return IngestionResult(source="rss", items_processed=0)
