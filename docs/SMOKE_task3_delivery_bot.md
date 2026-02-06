# SMOKE Task 3 — Delivery + Bot + AI

## Prereqs
- Docker + Docker Compose
- `.env` created from `.env.example`
- Telegram bot token in `BOT_TOKEN`
- LLM proxy in `LITELLM_URL` (+ `LITELLM_MODEL` if needed)

## Steps
1) Start services and apply migrations:
   ```bash
   cp .env.example .env
   docker compose up --build
   docker compose exec backend alembic upgrade head
   ```

2) Create topic + RSS source:
   ```bash
   docker compose exec db psql -U infra -d infra -c "insert into topics (name, description, keywords, created_at, updated_at) values ('Технологии', 'AI/ML', '[\"ai\", \"ml\", \"вакансия\"]', now(), now());"
   docker compose exec db psql -U infra -d infra -c \"insert into sources (name, source_type, url, trust_manual, job_keywords, created_at, updated_at) values ('rss-demo', 'rss', 'https://news.ycombinator.com/rss', 60, '[\\\"hiring\\\", \\\"вакансия\\\"]', now(), now());\"
   ```

3) Run bot:
   ```bash
   docker compose exec backend python -m app.bot
   ```

4) In Telegram:
   - Open the bot and send `/start`.
   - Ensure you receive the welcome message with TMA CTA.
   - (Optional) Set your account to PRO and enable Jobs:
     ```bash
     docker compose exec db psql -U infra -d infra -c \"update users set plan_tier='pro', jobs_enabled=true, delivery_mode='instant' where tg_id=<YOUR_TG_ID>;\"
     ```
   - Select the created topic in TMA.

5) Wait for RSS ingestion (1–2 min). Confirm:
   - You receive Smart Card messages (signal bar line).
   - Each message has the `🔎 DeepDive` button.

6) Reactions:
   - React with 👍 then 👎 and verify mutual exclusion in DB:
     ```bash
     docker compose exec db psql -U infra -d infra -c "select vote, pinned, pin_note from item_feedback order by updated_at desc limit 5;"
     ```
   - React with 📌, send a note, and verify `pinned=true` and `pin_note` saved.

7) AI Ask:
   - In bot, send `/ask Что нового по теме?`.
   - Ensure 2–6 bullet answer in RU.

8) DeepDive:
   - Press `🔎 DeepDive`, answer the clarification question, and confirm the 1500–2500 chars report.

9) Jobs API (PRO only):
   ```bash
   curl -H "X-Init-Data: <initData>" http://localhost:8000/api/public/jobs
   ```
   - PRO + jobs_enabled returns job items.
   - FREE/CORP receives a 403 with RU error text.
