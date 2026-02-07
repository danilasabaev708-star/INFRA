from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.config import get_settings
from app.core.replay_cache import replay_cache
from app.core.security import validate_init_data


def _build_init_data(bot_token: str, auth_date: int | None = None) -> str:
    data = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "AAE",
        "user": json.dumps({"id": 123, "username": "admin"}),
    }
    data_check_string = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode({**data, "hash": calculated_hash})


@pytest.fixture(autouse=True)
def _clear_replay_cache():
    replay_cache.clear()
    yield
    replay_cache.clear()


def test_validate_init_data():
    token = "TEST_TOKEN"
    get_settings.cache_clear()
    init_data = _build_init_data(token)
    parsed = validate_init_data(init_data, token)
    assert parsed.user_id == 123


def test_invalid_init_data():
    get_settings.cache_clear()
    with pytest.raises(ValueError):
        validate_init_data("auth_date=1&hash=bad", "token")


def test_expired_init_data(monkeypatch):
    monkeypatch.setenv("INIT_DATA_MAX_AGE_SECONDS", "10")
    get_settings.cache_clear()
    token = "TEST_TOKEN"
    init_data = _build_init_data(token, auth_date=int(time.time()) - 20)
    with pytest.raises(ValueError):
        validate_init_data(init_data, token)
    get_settings.cache_clear()


def test_replay_init_data_rejected():
    token = "TEST_TOKEN"
    get_settings.cache_clear()
    init_data = _build_init_data(token)
    validate_init_data(init_data, token)
    with pytest.raises(ValueError):
        validate_init_data(init_data, token)


def test_future_init_data_rejected():
    token = "TEST_TOKEN"
    get_settings.cache_clear()
    init_data = _build_init_data(token, auth_date=int(time.time()) + 120)
    with pytest.raises(ValueError):
        validate_init_data(init_data, token)
