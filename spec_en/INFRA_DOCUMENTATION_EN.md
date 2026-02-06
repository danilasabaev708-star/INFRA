# INFRA — Documentation & Runbooks Spec (EN copy)
Date: 2026-02-07

Goal: documentation that lets any agent/dev deploy and operate the system.

## Required repo files
### README.md
Must include:
- INFRA summary + Great Divide
- architecture diagram (mermaid ok)
- local quickstart
- docker compose quickstart
- env vars + `.env.example`
- alembic migration commands
- how to run bot
- how to deploy to VPS

### docs/
Suggested structure:
- overview.md
- architecture.md
- api_public.md (Bot/TMA)
- api_admin.md
- security.md (initData validation, admin access)
- sentinel.md
- prompts.md (versioned)
- runbook_vps.md (clean reinstall + deploy)
- troubleshooting.md
- changelog.md

## UX documentation
- Smart Card canon
- DeepDive canon
- Jobs UX (PRO only)
- CORP Studio UX (A chat + B TMA)

## Operations
- alerts behavior (ACK/Mute/Resolved)
- metrics interval 1/min, retention 6 months
