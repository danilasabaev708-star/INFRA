from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.item import Item
from app.models.source import Source

settings = get_settings()
logger = logging.getLogger(__name__)
_TAG_RE = re.compile(r"<[^>]+>")
_HASH_TEXT_LIMIT = 500


@dataclass
class IngestionResult:
    source: str
    items_processed: int


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _strip_html(value: str) -> str:
    return _TAG_RE.sub(" ", value)


def _normalize_lang(value: str | None) -> str:
    if not value:
        return "ru"
    normalized = value.split(",")[0].strip()
    return normalized[:8] if normalized else "ru"


def compute_content_hash(title: str, url: str | None, text: str) -> str:
    normalized_title = _normalize_text(title).lower()
    normalized_url = _normalize_text(url or "").lower()
    normalized_text = _normalize_text(text).lower()[:_HASH_TEXT_LIMIT]
    raw = f"{normalized_title}|{normalized_url}|{normalized_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _extract_entry_text(entry: dict) -> str:
    text = entry.get("summary") or entry.get("description")
    if not text and entry.get("content"):
        content_value = entry.get("content")[0]
        if isinstance(content_value, dict):
            text = content_value.get("value")
    if not text:
        return ""
    return html.unescape(_strip_html(str(text)))


def _parse_entry_datetime(entry: dict) -> datetime | None:
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return None
    return datetime.fromtimestamp(time.mktime(published), tz=timezone.utc)


async def ingest_telegram() -> IngestionResult:
    return IngestionResult(source="telegram", items_processed=0)


async def ingest_reddit() -> IngestionResult:
    return IngestionResult(source="reddit", items_processed=0)


async def ingest_rss_source(session: AsyncSession, source: Source) -> int:
    if not source.url:
        return 0
    feed = await asyncio.to_thread(feedparser.parse, source.url)
    entries = list(getattr(feed, "entries", []) or [])
    feed_meta = getattr(feed, "feed", {}) or {}
    feed_lang = None
    if isinstance(feed_meta, dict):
        feed_lang = feed_meta.get("language") or feed_meta.get("lang")
    else:
        feed_lang = getattr(feed_meta, "language", None) or getattr(feed_meta, "lang", None)
    lang = _normalize_lang(str(feed_lang) if feed_lang else None)
    state = dict(source.state or {})
    last_published_at = None
    if state.get("last_published_at"):
        try:
            last_published_at = datetime.fromisoformat(state["last_published_at"])
        except ValueError:
            last_published_at = None
    if last_published_at and last_published_at.tzinfo is None:
        last_published_at = last_published_at.replace(tzinfo=timezone.utc)
    newest_seen = last_published_at
    added = 0
    for entry in entries:
        title = str(entry.get("title") or "").strip()
        if not title:
            continue
        published_at = _parse_entry_datetime(entry)
        if last_published_at and published_at and published_at <= last_published_at:
            continue
        text = _extract_entry_text(entry).strip()
        if not text:
            text = title
        url = entry.get("link")
        content_hash = compute_content_hash(title, url, text)
        exists = await session.execute(select(Item.id).where(Item.content_hash == content_hash))
        if exists.scalar_one_or_none():
            continue
        item = Item(
            source_id=source.id,
            external_id=entry.get("id") or entry.get("guid"),
            url=url,
            title=title,
            text=text,
            published_at=published_at,
            content_hash=content_hash,
            lang=lang,
            is_job=False,
        )
        session.add(item)
        added += 1
        if published_at and (newest_seen is None or published_at > newest_seen):
            newest_seen = published_at
    state["last_ingested_at"] = datetime.now(timezone.utc).isoformat()
    if newest_seen:
        state["last_published_at"] = newest_seen.isoformat()
    source.state = state
    return added


async def ingest_rss(session: AsyncSession) -> IngestionResult:
    result = await session.execute(select(Source).where(Source.source_type == "rss"))
    sources = result.scalars().all()
    processed = 0
    for source in sources:
        processed += await ingest_rss_source(session, source)
    return IngestionResult(source="rss", items_processed=processed)


async def ingestion_loop(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        async with SessionLocal() as session:
            try:
                await ingest_rss(session)
                await session.commit()
            except Exception:
                logger.exception("RSS ingestion failed")
                await session.rollback()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.ingestion_interval_seconds)
        except asyncio.TimeoutError:
            continue
