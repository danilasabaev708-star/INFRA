# Admin MVP — Changelog

## Новые переменные окружения
- `ADMIN_PANEL_USERNAME` — логин для web-admin.
- `ADMIN_PANEL_PASSWORD_HASH` — bcrypt-хеш пароля (рекомендуется).
- `ADMIN_PANEL_PASSWORD` — временный plaintext пароль для MVP.
- `ADMIN_JWT_SECRET` — секрет для подписи JWT.
- `ADMIN_JWT_TTL_MIN` — TTL сессии в минутах.
- `WEB_ADMIN_ORIGIN` — origin web-admin (для CORS), например `http://localhost:8080`.

## Smoke test (manual)
1. Запустить стек: `docker compose up -d --build`.
2. Выполнить миграции: `cd backend && alembic upgrade head`.
3. Открыть web-admin и выполнить логин.
4. Создать подписку по `tg_id`, убедиться что `users.plan_tier` обновлён.
5. Проверить summary на странице Financials (выручка/счётчики).
6. Создать CORP org и инвайт в админке.
7. В TMA вызвать `POST /api/public/corp/accept-invite` с валидным initData.
8. Проверить: Jobs запрещены для FREE, затем для PRO без `jobs_enabled`.
9. Включить `jobs_enabled=true` через `PATCH /api/public/profile` — доступ разрешён.
10. Создать/замьютить алерт и убедиться, что RESOLVED всегда фиксируется.
