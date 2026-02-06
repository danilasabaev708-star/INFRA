from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.core.security import validate_init_data


def _build_init_data(bot_token: str) -> str:
    data = {
        "auth_date": "1700000000",
        "query_id": "AAE",
        "user": json.dumps({"id": 123, "username": "admin"}),
    }
    data_check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode({**data, "hash": calculated_hash})


def test_validate_init_data():
    token = "TEST_TOKEN"
    init_data = _build_init_data(token)
    parsed = validate_init_data(init_data, token)
    assert parsed.user_id == 123


def test_invalid_init_data():
    with pytest.raises(ValueError):
        validate_init_data("auth_date=1&hash=bad", "token")
