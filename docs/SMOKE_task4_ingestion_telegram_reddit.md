# SMOKE: Telegram + Reddit ingestion

## Telegram
1. Set env vars in `.env`:
   - `TELETHON_API_ID`
   - `TELETHON_API_HASH`
   - `TELETHON_SESSION` (StringSession)
2. Start backend (`uvicorn app.main:app --reload` or `docker compose up`).
3. Create a source with `source_type="telegram"` and a URL like `@channel`, `https://t.me/channel`, or numeric id.
4. Wait 1–2 minutes for the ingestion loop.
5. Verify:
   - `GET /api/admin/items?source_id={id}` returns new items.
   - `GET /api/admin/sources/{id}/state` shows `last_message_id` or `last_message_date`.

## Reddit
1. Set env vars in `.env`:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USER_AGENT`
2. Create a source with `source_type="reddit"` and URL `r/subreddit` or full Reddit URL.
3. Wait 1–2 minutes for the ingestion loop.
4. Verify:
   - `GET /api/admin/items?source_id={id}` returns new items.
   - `GET /api/admin/sources/{id}/state` shows `last_created_utc`.

## Alerts
- Break credentials (empty env vars) or provide invalid source URLs.
- `GET /api/admin/alerts` should contain a new alert and ingestion should continue for other sources.
