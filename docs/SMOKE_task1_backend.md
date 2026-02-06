# SMOKE Task 1 — Backend (CORS + RSS)

## Prereqs
- Docker + Docker Compose
- `.env` created from `.env.example` (set `WEB_ADMIN_ORIGIN` + `TMA_ORIGIN` or `TMA_ORIGINS`)

## Steps
1) Build and start services:
   ```bash
   cp .env.example .env
   docker compose up --build
   ```

2) Apply migrations:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

3) Add an RSS source:
   ```bash
   docker compose exec db psql -U infra -d infra -c "insert into sources (name, source_type, url, trust_manual, created_at, updated_at) values ('rss-demo', 'rss', 'https://news.ycombinator.com/rss', 50, now(), now());"
   ```

4) Wait 1–2 minutes for the ingestion loop.

5) Verify items were created:
   ```bash
   docker compose exec db psql -U infra -d infra -c "select id, title, published_at from items order by id desc limit 5;"
   ```

Optional: if admin auth is configured, use `GET /api/admin/items?source_id=` to list items.
