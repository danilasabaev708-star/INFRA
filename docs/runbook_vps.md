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

После миграций убедитесь, что ревизии совпадают:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic heads
```

Healthchecks используют `127.0.0.1`. Torch устанавливается через CPU‑индекс.
Backend/Web Admin/TMA по умолчанию привязаны к `127.0.0.1`, публикуйте их через reverse proxy или firewall.
