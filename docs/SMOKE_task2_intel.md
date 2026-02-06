# SMOKE Task 2 — Autotagging + Sentinel

## Prereqs
- Docker + Docker Compose
- `.env` created from `.env.example`

## Steps
1) Start services and apply migrations:
   ```bash
   cp .env.example .env
   docker compose up --build
   docker compose exec backend alembic upgrade head
   ```

2) Insert at least one topic with keywords:
   ```bash
   docker compose exec db psql -U infra -d infra -c "insert into topics (name, description, keywords, created_at, updated_at)
   values ('Технологии', 'AI/ML', '[\"ai\", \"ml\", \"искусственный интеллект\"]', now(), now());"
   ```

3) Add an RSS source and wait 1–2 minutes:
   ```bash
   docker compose exec db psql -U infra -d infra -c "insert into sources (name, source_type, url, trust_manual, created_at, updated_at) values ('rss-demo', 'rss', 'https://news.ycombinator.com/rss', 60, now(), now());"
   ```

4) Verify autotagging created 1–3 topic links:
   ```bash
   docker compose exec db psql -U infra -d infra -c "select item_id, topic_id, locked, score, assigned_by from item_topics order by item_id desc limit 5;"
   ```

5) Verify Sentinel fields are filled:
   ```bash
   docker compose exec db psql -U infra -d infra -c "select id, trust_score, trust_status, impact from items order by id desc limit 5;"
   ```

6) Verify artifacts JSON is stored:
   ```bash
   docker compose exec db psql -U infra -d infra -c "select id, sentinel_json->'cross_check', sentinel_json->'trust_ledger' from items order by id desc limit 3;"
   ```

Optional: with admin auth, call `GET /api/admin/items/{id}` to see `sentinel_json` + topics in one response.
