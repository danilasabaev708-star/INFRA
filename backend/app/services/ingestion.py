from __future__ import annotations

import asyncio
import hashlib
import html
import logging
import re
import time
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import datetime, timezone

import asyncpraw
import feedparser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.item import Item
from app.models.source import Source
from app.services.autotagging import assign_topics
from app.services.alerts import create_alert
from app.services.delivery import enqueue_instant_delivery
from app.services.sentinel import apply_sentinel

settings = get_settings()
logger = logging.getLogger(__name__)
_TAG_RE = re.compile(r"<[^>]+>")
_HASH_TEXT_LIMIT = 500
_FLOODWAIT_MAX_SECONDS = 300


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


def _is_job_post(source: Source, title: str, text: str) -> bool:
    keywords = [keyword.strip().lower() for keyword in (source.job_keywords or []) if keyword]
    content = f"{title}\n{text}".lower()
    if keywords and any(keyword in content for keyword in keywords):
        return True
    if source.job_regex:
        try:
            if re.search(source.job_regex, content, flags=re.IGNORECASE):
                return True
        except re.error:
            logger.warning("Invalid job regex on source %s", source.id)
    return False


def compute_content_hash(title: str, url: str | None, text: str) -> str:
    normalized_title = _normalize_text(title).lower()
    normalized_url = _normalize_text(url or "").lower()
    normalized_text = _normalize_text(text).lower()[:_HASH_TEXT_LIMIT]
    raw = f"{normalized_title}|{normalized_url}|{normalized_text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _extract_entry_text(entry: dict) -> str:
    text = entry.get("summary") or entry.get("description")
    content_list = entry.get("content")
    if not text and content_list:
        content_value = content_list[0]
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


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _parse_telegram_identifier(raw_url: str) -> str | int:
    value = raw_url.strip()
    if value.startswith("@"):
        return value
    if "t.me" in value or "telegram.me" in value:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        path = parsed.path.strip("/")
        if not path:
            return value
        parts = [part for part in path.split("/") if part]
        candidate = ""
        if parts:
            candidate = parts[1] if parts[0] in {"c", "joinchat"} and len(parts) > 1 else parts[0]
        if candidate:
            return candidate if candidate.startswith("@") else f"@{candidate}"
        return value
    try:
        return int(value)
    except ValueError:
        return value


def _extract_reddit_subreddit(raw_url: str | None) -> str | None:
    if not raw_url:
        return None
    value = raw_url.strip()
    if value.startswith("r/"):
        slug = value.split("/", 1)[1].strip("/")
        return slug or None
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = parsed.netloc.lower()
    if host == "reddit.com" or host.endswith(".reddit.com"):
        parts = [part for part in parsed.path.split("/") if part]
        for idx, part in enumerate(parts):
            if part == "r" and idx + 1 < len(parts):
                return parts[idx + 1]
    if "/" not in value:
        return value
    return None


def _telegram_message_text(message: object) -> str:
    text = getattr(message, "text", None) or getattr(message, "message", None) or ""
    return str(text).strip()


def _telegram_message_title(message_text: str, fallback: str) -> str:
    if message_text:
        return message_text.splitlines()[0].strip()[:200]
    return fallback


async def ingest_telegram_source(
    session: AsyncSession, client: TelegramClient, source: Source
) -> int:
    if not source.url:
        return 0
    identifier = _parse_telegram_identifier(source.url)
    state = dict(source.state or {})
    last_message_id = state.get("last_message_id")
    if isinstance(last_message_id, str):
        try:
            last_message_id = int(last_message_id)
        except ValueError:
            last_message_id = None
    if not isinstance(last_message_id, int):
        last_message_id = None
    last_message_date = None
    raw_date = state.get("last_message_date") or state.get("last_date")
    if raw_date:
        try:
            last_message_date = _ensure_utc(datetime.fromisoformat(raw_date))
        except ValueError:
            last_message_date = None
    try:
        entity = await client.get_entity(identifier)
        messages: list[object] = []
        async for message in client.iter_messages(
            entity, min_id=last_message_id or 0, reverse=True, limit=100
        ):
            if last_message_id and getattr(message, "id", 0) <= last_message_id:
                continue
            message_date = _ensure_utc(getattr(message, "date", None))
            if last_message_date and message_date and message_date <= last_message_date:
                continue
            messages.append(message)
    except FloodWaitError as exc:
        sleep_seconds = min(exc.seconds, _FLOODWAIT_MAX_SECONDS)
        logger.warning("Telegram FloodWait for source %s: %s seconds", source.id, sleep_seconds)
        await asyncio.sleep(sleep_seconds)
        return 0
    except Exception as exc:
        logger.exception("Telegram ingestion failed for source %s", source.id)
        await create_alert(
            session,
            dedup_key=f"ingestion_telegram_{source.id}",
            title="Telegram ingestion failed",
            message=str(exc),
        )
        return 0

    added = 0
    newest_id = last_message_id
    newest_date = last_message_date
    lang = _normalize_lang(None)
    channel_title = getattr(entity, "title", None) or source.name
    channel_username = getattr(entity, "username", None)
    for message in messages:
        message_text = _telegram_message_text(message)
        title = _telegram_message_title(message_text, channel_title)
        if not title:
            continue
        if not message_text:
            message_text = title
        url = None
        if channel_username:
            url = f"https://t.me/{channel_username}/{getattr(message, 'id', '')}"
        content_hash = compute_content_hash(title, url, message_text)
        exists = await session.execute(select(Item.id).where(Item.content_hash == content_hash))
        if exists.scalar_one_or_none():
            continue
        published_at = _ensure_utc(getattr(message, "date", None))
        is_job = _is_job_post(source, title, message_text)
        item = Item(
            source_id=source.id,
            external_id=str(getattr(message, "id", "")) or None,
            url=url,
            title=title,
            text=message_text,
            published_at=published_at,
            content_hash=content_hash,
            lang=lang,
            is_job=is_job,
        )
        session.add(item)
        await session.flush()
        try:
            await assign_topics(session, item)
            await apply_sentinel(item, source)
            await enqueue_instant_delivery(session, item)
        except Exception:
            logger.exception(
                "Post-ingestion pipeline failed for telegram item %s; continuing ingestion",
                item.title,
            )
        added += 1
        message_id = getattr(message, "id", None)
        if isinstance(message_id, int) and (newest_id is None or message_id > newest_id):
            newest_id = message_id
        message_date = _ensure_utc(getattr(message, "date", None))
        if message_date and (newest_date is None or message_date > newest_date):
            newest_date = message_date
    state["last_ingested_at"] = datetime.now(timezone.utc).isoformat()
    if newest_id is not None:
        state["last_message_id"] = int(newest_id)
    if newest_date:
        state["last_message_date"] = newest_date.isoformat()
    source.state = state
    return added


async def ingest_telegram(session: AsyncSession) -> IngestionResult:
    result = await session.execute(select(Source).where(Source.source_type == "telegram"))
    sources = result.scalars().all()
    if not sources:
        return IngestionResult(source="telegram", items_processed=0)
    if not (settings.telethon_api_id and settings.telethon_api_hash and settings.telethon_session):
        for source in sources:
            await create_alert(
                session,
                dedup_key=f"ingestion_telegram_{source.id}",
                title="Telegram ingestion misconfigured",
                message="Missing TELETHON_API_ID/TELETHON_API_HASH/TELETHON_SESSION",
            )
        return IngestionResult(source="telegram", items_processed=0)
    processed = 0
    async with TelegramClient(
        StringSession(settings.telethon_session),
        int(settings.telethon_api_id),
        settings.telethon_api_hash,
    ) as client:
        for source in sources:
            processed += await ingest_telegram_source(session, client, source)
    return IngestionResult(source="telegram", items_processed=processed)


async def ingest_reddit_source(
    session: AsyncSession, reddit: asyncpraw.Reddit, source: Source
) -> int:
    subreddit_name = _extract_reddit_subreddit(source.url)
    if not subreddit_name:
        await create_alert(
            session,
            dedup_key=f"ingestion_reddit_{source.id}",
            title="Reddit ingestion failed",
            message="Invalid subreddit URL.",
        )
        return 0
    state = dict(source.state or {})
    last_created_utc = state.get("last_created_utc")
    try:
        last_created_utc = float(last_created_utc) if last_created_utc is not None else None
    except (TypeError, ValueError):
        last_created_utc = None
    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts: list[object] = []
        async for submission in subreddit.new(limit=100):
            created = float(getattr(submission, "created_utc", 0) or 0)
            if last_created_utc and created <= last_created_utc:
                break
            posts.append(submission)
    except Exception as exc:
        logger.exception("Reddit ingestion failed for source %s", source.id)
        await create_alert(
            session,
            dedup_key=f"ingestion_reddit_{source.id}",
            title="Reddit ingestion failed",
            message=str(exc),
        )
        return 0

    posts.sort(key=lambda item: getattr(item, "created_utc", 0) or 0)
    added = 0
    newest_created = last_created_utc
    newest_post_id: str | None = None
    lang = _normalize_lang(None)
    for submission in posts:
        title = str(getattr(submission, "title", "") or "").strip()
        if not title:
            continue
        text = str(getattr(submission, "selftext", "") or "").strip()
        if not text:
            text = title
        url = getattr(submission, "url", None)
        content_hash = compute_content_hash(title, url, text)
        exists = await session.execute(select(Item.id).where(Item.content_hash == content_hash))
        if exists.scalar_one_or_none():
            continue
        created_utc = float(getattr(submission, "created_utc", 0) or 0)
        published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None
        is_job = _is_job_post(source, title, text)
        item = Item(
            source_id=source.id,
            external_id=getattr(submission, "id", None),
            url=url,
            title=title,
            text=text,
            published_at=published_at,
            content_hash=content_hash,
            lang=lang,
            is_job=is_job,
        )
        session.add(item)
        await session.flush()
        try:
            await assign_topics(session, item)
            await apply_sentinel(item, source)
            await enqueue_instant_delivery(session, item)
        except Exception:
            logger.exception(
                "Post-ingestion pipeline failed for reddit item %s; continuing ingestion",
                item.title,
            )
        added += 1
        if created_utc and (newest_created is None or created_utc > newest_created):
            newest_created = created_utc
            newest_post_id = getattr(submission, "id", None)
    state["last_ingested_at"] = datetime.now(timezone.utc).isoformat()
    if newest_created is not None:
        state["last_created_utc"] = newest_created
    if newest_post_id:
        state["last_post_id"] = newest_post_id
    source.state = state
    return added


async def ingest_reddit(session: AsyncSession) -> IngestionResult:
    result = await session.execute(select(Source).where(Source.source_type == "reddit"))
    sources = result.scalars().all()
    if not sources:
        return IngestionResult(source="reddit", items_processed=0)
    if not (settings.reddit_client_id and settings.reddit_client_secret and settings.reddit_user_agent):
        for source in sources:
            await create_alert(
                session,
                dedup_key=f"ingestion_reddit_{source.id}",
                title="Reddit ingestion misconfigured",
                message="Missing REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET/REDDIT_USER_AGENT",
            )
        return IngestionResult(source="reddit", items_processed=0)
    processed = 0
    reddit = asyncpraw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )
    try:
        for source in sources:
            processed += await ingest_reddit_source(session, reddit, source)
    finally:
        await reddit.close()
    return IngestionResult(source="reddit", items_processed=processed)


async def ingest_rss_source(session: AsyncSession, source: Source) -> int:
    if not source.url:
        return 0
    try:
        feed = await asyncio.to_thread(feedparser.parse, source.url)
    except Exception:
        logger.exception("RSS fetch failed for source %s", source.id)
        return 0
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
        text = _extract_entry_text(entry).strip()
        if not text:
            text = title
        url = entry.get("link")
        content_hash = compute_content_hash(title, url, text)
        exists = await session.execute(select(Item.id).where(Item.content_hash == content_hash))
        if exists.scalar_one_or_none():
            continue
        is_job = _is_job_post(source, title, text)
        item = Item(
            source_id=source.id,
            external_id=entry.get("id") or entry.get("guid"),
            url=url,
            title=title,
            text=text,
            published_at=published_at,
            content_hash=content_hash,
            lang=lang,
            is_job=is_job,
        )
        session.add(item)
        await session.flush()
        try:
            await assign_topics(session, item)
            await apply_sentinel(item, source)
            await enqueue_instant_delivery(session, item)
        except Exception:
            logger.exception(
                "Post-ingestion pipeline failed for item %s; continuing ingestion",
                item.title,
            )
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
                await ingest_telegram(session)
                await session.commit()
            except Exception:
                logger.exception("Telegram ingestion failed")
                await session.rollback()
            try:
                await ingest_reddit(session)
                await session.commit()
            except Exception:
                logger.exception("Reddit ingestion failed")
                await session.rollback()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.ingestion_interval_seconds)
        except asyncio.TimeoutError:
            continue
