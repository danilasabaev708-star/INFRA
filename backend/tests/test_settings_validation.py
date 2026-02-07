from __future__ import annotations

import bcrypt
import pytest

from app.core.config import get_settings, validate_settings


def _bcrypt_hash(value: str) -> str:
    return bcrypt.hashpw(value.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _base_prod_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("WEB_ADMIN_ORIGIN", "http://localhost:8080")
    monkeypatch.setenv("ADMIN_PANEL_PASSWORD_HASH", _bcrypt_hash("secret"))
    monkeypatch.setenv("ADMIN_JWT_SECRET", "x" * 32)
    monkeypatch.delenv("ADMIN_PANEL_PASSWORD", raising=False)


def test_validate_settings_rejects_wildcard_cors(monkeypatch):
    _base_prod_env(monkeypatch)
    monkeypatch.setenv("WEB_ADMIN_ORIGIN", "*")
    get_settings.cache_clear()
    settings = get_settings()
    with pytest.raises(ValueError):
        validate_settings(settings)
    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("env_name", "env_value"),
    [
        ("ADMIN_PANEL_PASSWORD_HASH", ""),
        ("ADMIN_JWT_SECRET", "short"),
    ],
)
def test_validate_settings_rejects_bad_admin_config(monkeypatch, env_name, env_value):
    _base_prod_env(monkeypatch)
    monkeypatch.setenv(env_name, env_value)
    get_settings.cache_clear()
    settings = get_settings()
    with pytest.raises(ValueError):
        validate_settings(settings)
    get_settings.cache_clear()
