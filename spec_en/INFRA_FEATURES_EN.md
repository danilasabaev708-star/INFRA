# INFRA — Features Spec (EN copy)
Date: 2026-02-07

This is an English copy of the canonical product spec. **Keep all user-facing UI text in Russian**.

## 0) Product rule: The Great Divide
- Web UI is **Admin only**.
- Client product lives in **Telegram Bot + Telegram Mini App (TMA)**.

## 1) Client UX: Telegram Bot
### 1.1 Delivery modes
- **Batch (digest)** — grouped once per N hours (default 3h). Digest is **a single message**.
- **Instant** — send immediately on important signal (PRO).
- **Quiet hours** — complete silence window (no messages at all, even important).

**Only Important filter**
- When enabled: send only items with `Влияние: ВЫСОКОЕ`.

### 1.2 Smart Card canon (Bot)
- Minimal emoji (1–2 max)
- Signal bar: `Доверие 0–100 | Статус (ПОДТВЕРЖДЕНО/СМЕШАННО/НЕЯСНО/ХАЙП) | Влияние (НИЗКОЕ/СРЕДНЕЕ/ВЫСОКОЕ)`
- Main body: 3–5 bullet points, short, factual
- Proof links section

Reactions:
- 👍 / 👎 mutually exclusive toggle
- 📌 favorite toggle (+ optional note)

Q&A:
- Answers are bullets only (2–6). No signal bar.

DeepDive:
- Triggered by `🔎 DeepDive`.
- Ask exactly 1 clarification question, then return ~1500–2500 chars structured report.

## 2) Client UX: Telegram Mini App (TMA)
### 2.1 Bottom navigation (MVP)
1) Темы
2) Уведомления
3) Jobs (PRO only)
4) Избранное (news)
5) Профиль

### 2.2 Jobs (PRO only)
Availability:
- FREE: disabled
- PRO: enabled (toggle)
- CORP: disabled (CORP is editorial team plan)

Inside Jobs: top tabs
- `Вакансии` | `Избранное` | `Профиль`

Full job list and job cards are **only in Mini App**. Bot only sends "Найдено N вакансий".

Anti-spam defaults:
- fingerprint cooldown: 24h
- per-company cap: 2 notifications/hour

### 2.3 Favorites
- News favorites: separate screen/tab.
- Job favorites: separate screen **inside Jobs**.

### 2.4 Profile (MVP)
Editable:
- current tier + expiry
- topics
- delivery mode + batch interval
- quiet hours
- only-important
- Jobs toggle (PRO)

## 3) Admin Web (Admin-only)
MVP pages:
- Overview (system + content + AI usage)
- Sources CRUD (content/job) with trust_manual 0–100 and job_keywords/job_regex for job sources
- Topics/Categories CRUD
- Alerts page (ACK/Mute, history)
- Financials (subscriptions/payments overview + manual grant/revoke)

## 4) Sentinel Anti-Fake (as designed)
Implement full 4 layers:
1) Cross-Check (incl. web search)
2) Logic Audit (flags)
3) Entity Verify
4) Trust Ledger

## 5) AI usage limits
Count by calendar day MSK 00:00–23:59.
- FREE: 5/day
- PRO: 200/day + 1 req / 5 sec throttle
- CORP: unlimited + 1 req / 2 sec throttle
Only Q&A and DeepDive count. System calls do not.

## 6) Billing
- PRO: 250 ₽/month, 2250 ₽/year (year = 9 months)
- CORP: 2500 ₽/month, 22500 ₽/year (year = 9 months)
- Expiry: immediate downgrade to FREE (no grace)
- Refund/chargeback: immediate downgrade to FREE (even for yearly)

## 7) CORP: Team editorial plan (MVP)
- CORP is team-based: one org, one admin, multiple editors.
- Exactly **one editor chat** (telegram chat_id) per org.
- Admin adds editors via **single-use invite link** (1 use).
- Editors share org topics; their likes/dislikes update org-level interest weights.

Studio (A + B):
- (A) Telegram editor chat: daily/batch digest (single message), follow-up updates, and deep-links to open Studio in TMA.
- (B) TMA Studio screen: idea queue → one-click brief pack → headline suggestions → outline.
