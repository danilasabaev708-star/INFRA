from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import psutil
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.metric import Metric

settings = get_settings()


async def collect_metrics(session: AsyncSession) -> None:
    cpu_percent = psutil.cpu_percent(interval=None)
    load_1, load_5, load_15 = psutil.getloadavg()
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()

    metrics = [
        Metric(name="system.cpu_percent", value=cpu_percent, labels=None),
        Metric(name="system.load_1", value=float(load_1), labels=None),
        Metric(name="system.load_5", value=float(load_5), labels=None),
        Metric(name="system.load_15", value=float(load_15), labels=None),
        Metric(name="system.ram_used", value=float(ram.used), labels=None),
        Metric(name="system.ram_total", value=float(ram.total), labels=None),
        Metric(name="system.disk_used", value=float(disk.used), labels=None),
        Metric(name="system.disk_total", value=float(disk.total), labels=None),
        Metric(name="system.net_rx", value=float(net.bytes_recv), labels=None),
        Metric(name="system.net_tx", value=float(net.bytes_sent), labels=None),
    ]

    result = await session.execute(text("SELECT pg_database_size(current_database())"))
    db_size = result.scalar() or 0
    metrics.append(Metric(name="db.postgres_db_size_mb", value=float(db_size) / 1024 / 1024, labels=None))

    session.add_all(metrics)


async def cleanup_metrics(session: AsyncSession) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.metrics_retention_days)
    await session.execute(delete(Metric).where(Metric.collected_at < cutoff))


async def metrics_loop(stop_event: asyncio.Event) -> None:
    next_cleanup = datetime.now(timezone.utc)
    while not stop_event.is_set():
        async with SessionLocal() as session:
            try:
                await collect_metrics(session)
                if datetime.now(timezone.utc) >= next_cleanup:
                    await cleanup_metrics(session)
                    next_cleanup = datetime.now(timezone.utc) + timedelta(days=1)
                await session.commit()
            except Exception:
                await session.rollback()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.metrics_interval_seconds)
        except asyncio.TimeoutError:
            continue
