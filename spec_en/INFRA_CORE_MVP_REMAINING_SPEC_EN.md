# INFRA — Core MVP Remaining Work Spec (EN)

**Date:** 2026-02-07 (GMT+4)  
**Repo:** `danilasabaev708-star/INFRA`  
**This document:** Remaining functional scope to turn the repo into a working INFRA product (beyond Admin MVP).

> **Great Divide rule:** Web = Admin only. All client UX lives in **Telegram Bot + Telegram Mini App (TMA)**.

---

## 0) Current status snapshot (what already exists)

### Already implemented (do not break)
- Backend FastAPI app with routers: `/api/public`, `/api/admin`, `/api/admin/auth`, `/health`.
- Telegram initData validation for TMA via `X-Init-Data` (HMAC-SHA256).
- Admin separate website auth: JWT in HttpOnly cookie + CSRF double-submit (cookie + `X-CSRF-Token`).
- DB tables & models for: users, topics, sources, alerts, metrics, ai_usage, orgs/org_members/org_invites, subscriptions.
- Financials endpoints (admin) + CORP org/invite endpoints (admin) + accept-invite endpoints (public).
- Jobs gating logic: PRO-only + `jobs_enabled` toggle.

### Missing / incomplete
- Ingestion pipeline (Telegram channels, Reddit, RSS).
- Core feed storage model (news items) + dedup.
- Autotagging pipeline (1–3 topics, admin lock override).
- Sentinel 4-layer system (Cross-Check, Logic Audit, Entity Verify, Trust Ledger).
- Telegram Bot: Smart Card canon, reactions (👍/👎/📌), Q&A and DeepDive flows.
- Delivery engine (digest/instant, quiet hours, only-important filter).
- Jobs ingestion & delivery (PRO only).
- CORS config currently allows only `WEB_ADMIN_ORIGIN` → breaks TMA.

---

## 1) Non-functional requirements (NFR)

### 1.1 Security
- **Public endpoints**: require valid `X-Init-Data` for any user-specific action.
- **Admin endpoints**: require admin session cookie; must not accept `X-Init-Data` as auth.
- Do not log initData, bot tokens, user session strings.

### 1.2 UX language & canon
- User-visible strings (bot messages, error texts) must be **Russian**.
- Smart Card canon (Telegram Bot):
  - Minimal emoji (0–2 max).
  - Signal bar format: `Доверие 0–100 | Статус (ПОДТВЕРЖДЕНО/СМЕШАННО/НЕЯСНО/ХАЙП) | Влияние (НИЗКОЕ/СРЕДНЕЕ/ВЫСОКОЕ)`.
  - No “Почему тебе”.
  - Q&A answers are bullet list only (2–6 bullets), **no signal bar**.
  - Like/dislike via Telegram reactions `👍` / `👎` mutually exclusive toggle.
  - Favorite via reaction `📌` with optional note support.

### 1.3 Rate limits (already implemented, must remain)
- MSK calendar-day usage counting (Europe/Moscow 00:00–23:59), only purposes `qa` and `deepdive`.

### 1.4 Jobs policy
- Jobs available only for **PRO** users, and only when `jobs_enabled=true`.
- CORP explicitly has no jobs.

---

## 2) Fix CORS for both Web Admin and TMA

### Problem
Backend CORS currently allows only `WEB_ADMIN_ORIGIN`. TMA runs on different origin and will be blocked.

### Requirement
- Add env vars:
  - `WEB_ADMIN_ORIGIN` (already exists)
  - `TMA_ORIGIN` (or `TMA_ORIGINS` as CSV)
- Configure CORS to allow both origins.
- Keep `allow_credentials=true` because admin cookie needs it.
- For TMA, we do not rely on cookies, but allowing credentials doesn’t hurt; still restrict origins.

**Acceptance:** browser-based TMA calls to `/api/public/*` succeed without CORS errors.

---

## 3) Data model additions (core content)

### 3.1 Add a News Item / Content model
Create SQLAlchemy model + Alembic migration.

**Table:** `items`
- `id` int pk
- `source_id` fk → sources
- `external_id` string nullable (message id / reddit id / rss guid)
- `url` text nullable
- `title` text not null
- `text` text not null (cleaned body)
- `published_at` datetime tz
- `content_hash` string unique (dedup key)
- `lang` string(8) default `ru`
- `is_job` bool default false
- `impact` enum/string: `low|medium|high` (maps to RU labels)
- `trust_score` int 0–100
- `trust_status` string: `confirmed|mixed|unclear|hype`
- `sentinel_json` JSON nullable (artifacts)
- `created_at` datetime

### 3.2 Topic assignment
Add `item_topics` many-to-many:
- `item_id`, `topic_id`, `locked` bool default false, `score` float nullable, `assigned_by` string (`auto|admin`).

**Rule:** If any topic assignment is `locked=true`, autotagging must not overwrite locked topics.

### 3.3 User feedback (reactions)
Store user feedback for training/weights & favorites.

**Table:** `item_feedback`
- `id` pk
- `user_id` fk
- `item_id` fk
- `vote` enum/string: `like|dislike` nullable
- `pinned` bool default false
- `pin_note` text nullable
- `updated_at` datetime

Mutual exclusion: `vote` can be like or dislike, not both.

---

## 4) Ingestion pipeline (MVP)

### 4.1 Sources model usage
Use existing `sources` table:
- `source_type`: `telegram|reddit|rss`
- `url` or identifier fields
- `trust_manual` 0–100
- optional `job_keywords` and `job_regex` to detect jobs.

### 4.2 Implement scrapers
- Telegram: **Telethon** (MTProto user session) — read from configured channels.
- Reddit: **AsyncPRAW**.
- RSS: `feedparser`.

### 4.3 Ingestion loop
Implement a background loop/service that:
1) Selects active sources.
2) Fetches new posts since last cursor.
3) Normalizes into Item(title/text/url/published_at/source_id).
4) Computes dedup hash (e.g. sha256 of normalized title+url+firstN text).
5) Inserts new items (ignore duplicates).
6) Runs autotagging.
7) Runs Sentinel.
8) Schedules delivery.

Store cursors per source:
- Add `source_state` table or fields on `sources` (JSON `state`). MVP acceptable: `sources.state JSON`.

**Acceptance:** With 1 RSS source configured, new items appear in DB within 1–2 minutes.

---

## 5) Autotagging (mandatory)

### 5.1 Topic schema
Topics must support:
- `name`
- `description`
- `keywords` (array)
- `order` int

If current Topic model lacks these fields, extend it + migration.

### 5.2 Algorithm
For each new item:
- Compute keyword match scores per topic.
- If a clear leader exists, assign 1–3 topics.
- Otherwise call LLM (via existing provider factory) to pick 1–3 topics.

Respect admin locks:
- If an item already has any locked topic assignment(s), do not overwrite locked ones.

---

## 6) Sentinel 4-layer (as designed)

Implement full pipeline and store artifacts in `items.sentinel_json`.

Layers:
1) **Cross-Check**: compare claims vs other sources (lightweight heuristics + optional web search).
2) **Logic Audit**: check internal consistency, obvious fallacies.
3) **Entity Verify**: validate named entities (companies, people, tickers) if possible.
4) **Trust Ledger**: update trust score/status using source trust + checks.

Outputs (must map to bot canon):
- `trust_score` 0–100
- `trust_status`: `confirmed|mixed|unclear|hype`
- `impact`: `low|medium|high`

MVP: allow simplified implementations, but keep structure and JSON artifacts.

---

## 7) Delivery engine (digest/instant)

Use existing user settings:
- `delivery_mode`: digest/instant
- `batch_interval_hours`
- quiet hours (`quiet_hours_start/end`)
- `only_important` (means **impact == high only**)

### 7.1 Digest scheduler
- For each user, every `batch_interval_hours` assemble items matching their topics.
- Respect quiet hours.

### 7.2 Instant delivery
- On new item, deliver to users for whom the item matches topics.
- Respect quiet hours.

### 7.3 Telegram delivery
Implement bot send:
- Smart Card message per item.
- Add inline button `🔎 DeepDive` (opens DeepDive composer route or asks user to type).

**Acceptance:** One user with selected topics receives digest/instant correctly.

---

## 8) Telegram Bot (upgrade from prototype)

### 8.1 Replace current minimal bot loop
Current `app.bot` is minimal getUpdates.
Replace with a proper framework (aiogram or python-telegram-bot) and implement:
- `/start` onboarding
- Topic selection CTA to open TMA
- Reaction handling (update `item_feedback` for 👍/👎/📌)
- DeepDive trigger
- Q&A command (e.g. `/ask` or button)

### 8.2 Reactions behavior
- 👍 sets vote=like and clears dislike.
- 👎 sets vote=dislike and clears like.
- 📌 toggles pinned; optionally ask for note and store in `pin_note`.

---

## 9) AI Q&A and DeepDive

### 9.1 Q&A
- Endpoint: `POST /api/public/ai/ask` already exists but returns placeholder.
Implement actual LLM call and return immediate answer.
- Must record usage via `check_and_record_usage(session, user, purpose)`.
- Response format: 2–6 bullet points in RU.

### 9.2 DeepDive
- Triggered from item context.
- Always ask **one short clarification question**, then produce 1500–2500 chars structured report.
- Count as `deepdive` usage.

---

## 10) Jobs ingestion (PRO-only) — MVP

- Detect job posts during ingestion (via `sources.job_keywords` and/or `job_regex`).
- Store items with `is_job=true`.
- `/api/public/jobs` should list actual job items, but only for PRO+jobs_enabled.
- Delivery: optionally push job alerts in instant mode.

---

## 11) Admin panel extensions (optional, nice-to-have)
Not required for core MVP, but helpful:
- Admin page to view items + their Sentinel/autotagging results.
- Admin ability to lock item topics.

---

## 12) Definition of Done (DoD)

1) **CORS fixed**: web-admin and TMA both work in browser.
2) DB migrations include new models (`items`, `item_topics`, `item_feedback`, topic schema changes).
3) Ingestion loop works for at least RSS and creates new items.
4) Autotagging assigns 1–3 topics and respects locks.
5) Sentinel runs and fills trust_score/status/impact + artifacts.
6) Delivery works (digest or instant) and respects quiet hours + only_important.
7) Bot sends Smart Cards in RU with correct signal bar.
8) Reactions update DB state and enforce mutual exclusion.
9) Q&A returns real LLM answer (bullets) and enforces MSK daily limits.
10) DeepDive flow implemented per canon.
11) Jobs list returns real results for PRO users and is blocked otherwise.

---

## 13) Implementation notes
- Prefer background tasks via asyncio loops already used (see `metrics_loop`).
- Keep components modular: `services/ingestion.py`, `services/delivery.py`, `services/autotagging.py`, `services/sentinel.py`, `bot/` package.
- Add smoke test docs: `docs/SMOKE_core_mvp.md`.
