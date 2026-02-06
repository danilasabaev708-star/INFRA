# API Public (Bot/TMA)

Базовый URL: `/api/public`

## Авторизация

`POST /auth/telegram`

```json
{ "init_data": "<initData>" }
```

Возвращает профиль пользователя.

## Профиль
- `GET /me`
- `PATCH /me/settings`
- `PUT /me/topics`

## Темы
- `GET /topics`

## Jobs (PRO)
- `GET /jobs` — возвращает список вакансий (только PRO и включённый toggle).

## AI
- `POST /ai/ask` — purpose: `qa` или `deepdive`, лимиты по тарифам.

## CORP Studio
- `GET /studio`
- `POST /corp/invites/{token}`
