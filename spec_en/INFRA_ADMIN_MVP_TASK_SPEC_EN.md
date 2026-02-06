# INFRA — Admin MVP Task Spec (EN)

**Date:** 2026-02-07 (GMT+4)  
**Repo:** `danilasabaev708-star/INFRA`  
**Scope:** Finish an MVP-ready **separate Web Admin site** (not Telegram WebApp) + backend admin auth + Financials MVP + CORP org/invites + PRO-only Jobs gating + Alerts RESOLVED bugfix.

---

## 0) Core Product Rule: “Great Divide”

- **Web = Admin Panel only.** No user-facing client functionality on the web.
- **Client UX lives only in Telegram:** Telegram Bot + Telegram Mini App (TMA).

This must be reflected in both routing/UI and backend security.

---

## 1) Non-Functional Requirements (NFR)

### 1.1 Security boundaries
- **Public/TMA endpoints** must require `X-Init-Data` and validate Telegram `initData` using HMAC-SHA256.
  - Use the existing validator in `backend/app/core/security.py`.
- **Admin endpoints (`/api/admin/*`) must NOT use Telegram initData** because web-admin is a separate website.
  - Admin endpoints must require **admin session authentication** (see §2).

### 1.2 Admin identity
- `ADMIN_IDS` (Telegram `tg_id`s) remains the canonical “who is a Telegram admin”, for bot-side/admin notifications if any.
- For **web-admin login**: use a separate auth mechanism (username/password + session token).

### 1.3 Docker healthchecks
- Healthchecks must use `127.0.0.1`, not `localhost`.

### 1.4 Language
- Any text that can be shown to **end-users or editors** must be **Russian**.
- Web-admin UI labels can be English or RU (prefer RU if easy), but API error messages should be RU where user-facing.

### 1.5 Jobs policy
- **Jobs are PRO-only**.
- Additionally, user must explicitly enable `jobs_enabled=true`.
- CORP has **no Jobs**.

### 1.6 AI rate limits accounting (already partially implemented)
- Count by calendar day **Europe/Moscow** (00:00–23:59 MSK).
- Count only user-triggered purposes: `qa` and `deepdive`.
- Throttles: PRO 5 sec, CORP 2 sec.

---

## 2) Web Admin Authentication (separate website)

### 2.1 Goals
Implement minimal but solid admin authentication for `/api/admin/*` that works for a standalone web-admin site.

### 2.2 Recommended approach (MVP)
- **JWT session in HttpOnly cookie** (preferred) OR Bearer token.
- If cookie-based, add a basic CSRF defense.

#### Cookie-based auth requirements
- Cookie settings:
  - `HttpOnly: true`
  - `Secure: true` in production
  - `SameSite: Strict` (or `Lax` if needed for dev)
  - Path `/`
- CORS:
  - Restrict `allow_origins` to the web-admin origin.
  - Set `allow_credentials=true`.

#### CSRF (MVP acceptable)
One of:
- **Double-submit cookie**: backend sets `csrf_token` cookie (non-HttpOnly) and requires `X-CSRF-Token` header matching it for state-changing requests.
- Alternatively: custom header token stored in memory/localStorage (less ideal).

### 2.3 Environment variables
Add to `.env.example` and document:
- `ADMIN_PANEL_USERNAME`
- `ADMIN_PANEL_PASSWORD_HASH` (bcrypt hash) **preferred**
  - If too heavy for MVP: `ADMIN_PANEL_PASSWORD` (plain) but mark as temporary.
- `ADMIN_JWT_SECRET`
- `ADMIN_JWT_TTL_MIN` (e.g. `120`)
- `WEB_ADMIN_ORIGIN` (e.g. `https://admin.example.com` or `http://localhost:8080`)

### 2.4 Backend API
Create admin auth endpoints:
- `POST /api/admin/auth/login`
  - Input: `{ "username": string, "password": string }`
  - Output: `{ "ok": true }`
  - Side effects: set `admin_session` cookie (JWT) and set `csrf_token` cookie (if using double-submit).
- `POST /api/admin/auth/logout`
  - Clears cookies.
- `GET /api/admin/auth/me`
  - Returns `{ "authenticated": true, "username": string }`.

### 2.5 Authorization dependency
Add a dependency (e.g. `require_admin_session`) and apply it to all `/api/admin/*` except `/auth/*`:
- Validate JWT signature + expiry.
- Enforce CSRF header on state-changing requests if cookie auth is used.

---

## 3) Financials MVP (Web Admin)

### 3.1 Philosophy
No payment provider integration in this task.
**Admin manually assigns subscriptions** and the system provides reporting.

### 3.2 Database model
The Alembic migration already creates `subscriptions`.
Ensure there is an SQLAlchemy model, e.g. `backend/app/models/subscription.py`.

Minimum fields expected (from migration):
- `id: int`
- `user_id: int (FK users.id)`
- `plan_tier: str` (`free|pro|corp`)
- `status: str` (define a small set)
- `amount_rub: int`
- `started_at: datetime`
- `expires_at: datetime | null`
- `created_at: datetime`

### 3.3 Business rules
- Creating a subscription should optionally update user’s plan:
  - Set `users.plan_tier` to subscription tier.
  - Set `users.plan_expires_at` to `expires_at`.
- Status rules:
  - `active`: currently valid
  - `canceled`: manually canceled
  - `expired`: end date passed
  - (Optional) `trial`

### 3.4 Admin API
All endpoints require admin auth from §2.

#### Create subscription
- `POST /api/admin/subscriptions`
  - Input: `user_id` **or** `tg_id`, `plan_tier`, `amount_rub`, `status`, `expires_at`.
  - Output: subscription object.

#### List subscriptions
- `GET /api/admin/subscriptions`
  - Filters:
    - `from` (ISO datetime)
    - `to` (ISO datetime)
    - `plan_tier`
    - `status`
    - `user_id` or `tg_id` (optional)
  - Output: paginated list (or simple list for MVP).

#### Summary report
- `GET /api/admin/financials/summary?from=...&to=...`
  - Output:
    - `revenue_rub: int` (sum of amount_rub for created_at in range)
    - `payments_count: int`
    - `new_subscriptions_count: int`
    - `active_subscriptions_count: int` (active within range or at `to` boundary)
    - `by_tier: { free|pro|corp: { revenue_rub, count } }`

#### Set user plan directly (optional but useful)
- `POST /api/admin/users/{user_id}/plan`
  - Input: `plan_tier`, `plan_expires_at`
  - Output: updated user.

### 3.5 Web-admin UI requirements
Add/finish a Financials page:
- Login page (if not logged in)
- Financials page:
  - Date range picker
  - Summary cards
  - Subscriptions table
  - Form/modal “Assign subscription”

---

## 4) CORP MVP (Org / Members / Invites / Editor chat)

### 4.1 Goal
Support a CORP plan as a **team editorial plan**.

### 4.2 Data model
Repo already has:
- `Org` (`orgs`): `name`, `admin_user_id`, `editor_chat_id`
- `OrgMember` (`org_members`): `org_id`, `user_id`, `role` (default editor)
- `OrgInvite` (`org_invites`): `token`, `expires_at`, `used_by`, `used_at`

### 4.3 Invite rules
- Invite must be **single-use**:
  - if `used_at` exists → reject
- Invite must expire:
  - `expires_at < now` → reject

### 4.4 Admin API (web-admin)
All require admin auth (§2).
- `POST /api/admin/orgs`
  - Input: `{ name: string, admin_user_tg_id?: int, admin_user_id?: int }`
  - If `admin_user_tg_id` is provided and user doesn’t exist, create it.
- `GET /api/admin/orgs`
- `GET /api/admin/orgs/{org_id}/members`
- `POST /api/admin/orgs/{org_id}/invites`
  - Input: `{ expires_in_hours?: int }` default 24
  - Output: invite token + full invite URL (optional)
- `POST /api/admin/orgs/{org_id}/editor-chat`
  - Input: `{ editor_chat_id: int }`
  - Constraint: only one editor chat per org.

### 4.5 Public API (TMA)
All require Telegram initData auth.
- `POST /api/public/corp/accept-invite`
  - Input: `{ token: string }`
  - Uses initData user → maps to `users` row.
  - Adds to `org_members` as `editor`.
  - Returns org info.

---

## 5) Jobs gating (PRO-only)

### 5.1 Existing logic
`backend/app/services/jobs.py` already defines:
- PRO-only
- must have `jobs_enabled` toggle

### 5.2 Required updates
- Ensure all jobs endpoints call `ensure_jobs_access(user)`.
- Provide a profile update endpoint in public API:
  - `PATCH /api/public/profile` with `{ jobs_enabled?: bool, ... }`
- Return **Russian** error messages:
  - PRO missing toggle: `"Включите Jobs в профиле."`
  - Not PRO: `"Jobs доступны только на PRO."`

---

## 6) Alerts: RESOLVED emission bugfix

### 6.1 Current problem
If alerts are muted or throttled, `resolve_alert()` may fail to create/send a RESOLVED alert.

### 6.2 Required behavior
- **RESOLVED must always be recorded and sent**, regardless of:
  - mute state
  - throttle window
- ACK does not close an alert.

### 6.3 Admin endpoints
All require admin auth (§2):
- `GET /api/admin/alerts`
- `POST /api/admin/alerts/{id}/ack`
- `POST /api/admin/alerts/{id}/mute` (set `muted_until`)
- `POST /api/admin/alerts/{id}/resolve`

---

## 7) Implementation constraints
- Do **not** add payment integration.
- Do **not** add user-facing web pages.
- Do **not** change the stack.

---

## 8) Definition of Done (DoD)

### Backend
- `docker compose up --build` works.
- Alembic migration works on a clean DB.
- Admin auth works, and admin endpoints are protected.
- TMA endpoints are protected by `X-Init-Data` validation.
- Financials endpoints work and return correct aggregates.
- CORP invite acceptance works end-to-end.
- Jobs endpoints enforce PRO-only + toggle.
- RESOLVED alerts always emitted.

### Web-admin
- Login screen.
- Financials page with:
  - date range filter
  - summary cards
  - subscriptions table
  - assign subscription form

### Docs
- Add `docs/CHANGELOG_admin_mvp.md` with:
  - new env vars
  - manual smoke test steps

---

## 9) Smoke test checklist (manual)
1) Start stack: `docker compose up -d --build`.
2) Run migrations.
3) Open web-admin, login.
4) Create a subscription for a known user (by tg_id). Confirm `users.plan_tier` updated.
5) Open Financials summary for today and confirm revenue/counts reflect the new subscription.
6) Create a CORP org, create invite token.
7) From TMA (valid initData), call accept-invite. Verify `org_members` row created.
8) Try Jobs endpoint as FREE → must be denied.
9) Upgrade user to PRO, keep jobs_enabled=false → must be denied.
10) Set jobs_enabled=true → must pass.
11) Trigger an alert then resolve it while muted/throttled → RESOLVED must still appear.
