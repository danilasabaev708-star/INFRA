from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs


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

    user_payload = json.loads(data["user"])
    user_id = int(user_payload["id"])
    auth_date = int(data.get("auth_date", "0"))
    return InitData(
        user_id=user_id,
        auth_date=auth_date,
        user=user_payload,
        query_id=data.get("query_id"),
    )
