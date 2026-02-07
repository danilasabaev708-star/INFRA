from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs

from app.core.config import get_settings

_MAX_INIT_DATA_FUTURE_SKEW_SECONDS = 60


@dataclass(frozen=True)
class InitData:
    user_id: int
    auth_date: int
    user: dict[str, Any]
    query_id: str | None


def _data_check_string(data: dict[str, str]) -> str:
    pairs = [f"{key}={data[key]}" for key in sorted(data.keys())]
    return "\n".join(pairs)


def validate_init_data(init_data: str, bot_token: str) -> InitData:
    if not init_data:
        raise ValueError("Пустые данные авторизации.")
    if not bot_token:
        raise ValueError("Не задан токен бота.")

    settings = get_settings()
    parsed = parse_qs(init_data, strict_parsing=True)
    received_hash_list = parsed.pop("hash", None)
    if not received_hash_list:
        raise ValueError("Отсутствует hash.")
    received_hash = received_hash_list[0]

    data: dict[str, str] = {}
    for key, value in parsed.items():
        if not value:
            continue
        data[key] = value[0]

    data_check_string = _data_check_string(data)
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Некорректная подпись initData.")

    if "user" not in data:
        raise ValueError("Отсутствуют данные пользователя.")

    auth_date_raw = data.get("auth_date")
    if not auth_date_raw:
        raise ValueError("Отсутствует auth_date.")
    try:
        auth_date = int(auth_date_raw)
    except ValueError as exc:
        raise ValueError("Некорректный auth_date.") from exc
    now_ts = int(time.time())
    if auth_date <= 0 or auth_date > now_ts + _MAX_INIT_DATA_FUTURE_SKEW_SECONDS:
        raise ValueError("Некорректный auth_date.")
    if now_ts - auth_date > settings.init_data_max_age_seconds:
        raise ValueError("Истёк срок действия initData.")

    user_payload = json.loads(data["user"])
    user_id = int(user_payload["id"])
    return InitData(
        user_id=user_id,
        auth_date=auth_date,
        user=user_payload,
        query_id=data.get("query_id"),
    )
