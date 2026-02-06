# INFRA — VPS Rebuild & Deploy Runbook (EN copy)
Date: 2026-02-07

This is an English copy of the clean-slate deploy runbook.

## 0) Preconditions
- SSH: `ssh -i id_infra_ed25519 root@213.148.15.252`
- Docker + Docker Compose + Git installed

## 1) Clone repo
```bash
mkdir -p /root/INFRA
cd /root/INFRA
# git clone <REPO_URL> .
```

## 2) Configure env
Create `/root/INFRA/.env` from `.env.example`.

Critical rules:
- Healthchecks use `127.0.0.1`.
- CPU-only torch.
- Robust `ADMIN_IDS` parsing.

## 3) Telegram alerts group
- Create one group `INFRA Admin Alerts`.
- Add bot and admins.
- Set env `ALERTS_TG_GROUP_ID` to the numeric chat_id.

## 4) Start stack
```bash
cd /root/INFRA
docker compose pull || true
docker compose build --no-cache
docker compose up -d
```

## 5) Verify
```bash
docker compose ps
docker compose logs -f --tail 200 backend
```

## 6) DB migrations (if not auto)
```bash
docker compose exec backend alembic upgrade head
```

## 7) Seed
No preset list of sources. Sources are added manually after deploy.

## 8) E2E checks
- content pipeline: ingestion → autotagging → sentinel → bot delivery
- PRO jobs: ingestion → dedup → notification → TMA list
- alerts: trigger an alert → ACK/Mute → recovery → RESOLVED
