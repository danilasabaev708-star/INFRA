# API Admin

Базовый URL: `/api/admin`, доступ только для ADMIN_IDS + initData.

## Overview
`GET /overview`

## Sources
- `GET /sources`
- `POST /sources`
- `PUT /sources/{id}`
- `DELETE /sources/{id}`

## Topics
- `GET /topics`
- `POST /topics`
- `PUT /topics/{id}`
- `DELETE /topics/{id}`

## Alerts
- `GET /alerts`
- `POST /alerts/{id}/ack`
- `POST /alerts/{id}/mute`

## Metrics
- `GET /metrics`

## Financials
- `GET /financials`
- `POST /financials/grant`
- `POST /financials/revoke`

## CORP
- `POST /corp/orgs`
- `POST /corp/orgs/{org_id}/invites`
