# Runbook VPS

1. Подготовьте сервер и установите Docker + Compose + Git.
2. Клонируйте репозиторий в `/root/INFRA`.
3. Создайте `.env` из `.env.example`.
4. Запустите стек:

```bash
docker compose build --no-cache
docker compose up -d
```

5. Проверьте состояние сервисов и примените миграции:

```bash
docker compose ps
docker compose exec backend alembic upgrade head
```

Healthchecks используют `127.0.0.1`. Torch устанавливается через CPU‑индекс.
