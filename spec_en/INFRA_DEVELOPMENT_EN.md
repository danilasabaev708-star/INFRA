# INFRA — Development / Implementation Spec (EN copy)
Date: 2026-02-07

## 1) Architecture
- Backend: FastAPI (async)
- PostgreSQL (asyncpg)
- ChromaDB
- Frontends: Web Admin + TMA (React/Vite)
- Telegram Bot
- Optional OpenSERP container (web search)

## 2) Security
- Telegram WebApp `initData` must be validated via HMAC-SHA256.
- Strict admin access via `ADMIN_IDS`.
- Robust parsing: `ADMIN_IDS` may come as int/string/comma-separated; normalize to `list[int]`.
- Secrets only via env. Avoid logging secrets.

## 3) Ingestion
- Telegram: Telethon (MTProto user session)
- Reddit: AsyncPRAW
- RSS: feedparser

## 4) Web search
- Use OpenSERP (yandex + bing).
- Cache: 5–30 minutes.
- Safe default rate limit: 30 req/min for whole backend + exponential backoff on 429/errors.
- Proxy support optional.

## 5) AI
- LiteLLM as provider router.
- Track AI usage by purpose.
- Apply MSK daily accounting and tier limits.

## 6) Jobs
- PRO only.
- Pipeline: detect job posts via job_keywords/job_regex per Source → rule-based extraction → LLM fallback if missing critical fields → dedup (hard + fingerprint + semantic) → matching (embeddings + targeted LLM scoring).
- Bot sends only notifications; full list/cards in TMA.

## 7) Metrics (timeseries)
- Collection interval: **1 minute**.
- Retention: **6 months**.
- Minimum metric set (MVP):
  - system: cpu_percent, load_1/5/15, ram_used/total, disk_used/total, net_rx/tx
  - db: postgres_db_size_mb
  - docker/services: container_cpu_percent, container_ram_mb, container_restarts, container_health_status
- Implement a cleanup job for retention.

## 8) Alerts (Admin)
- Send alerts to Telegram + store in DB + show in Admin Web.
- Mute by `dedup_key`.
- ACK does not close.
- RESOLVED always emitted when condition clears.
- Throttle: 1 per 15 minutes per dedup_key.

## 9) CORP Editor Studio
- One org → one editor chat.
- Editors added via single-use invite link.
- Chat receives digest + follow-ups + deep-links to TMA Studio.

## 10) Docker / deployment
- Healthchecks: use **127.0.0.1** (NOT localhost).
- Ensure clean python imports (set `PYTHONPATH=/app` or equivalent).
- Torch: CPU-only wheel index to avoid CUDA downloads.
