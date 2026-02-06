from __future__ import annotations

import pytest

import bcrypt

from app.core.admin_auth import (
    AdminAuthError,
    create_admin_token,
    decode_admin_token,
    verify_admin_password,
)


def test_admin_jwt_roundtrip() -> None:
    token = create_admin_token("admin", "secret", 10)
    payload = decode_admin_token(token, "secret")
    assert payload["sub"] == "admin"


def test_admin_jwt_invalid_signature() -> None:
    token = create_admin_token("admin", "secret", 10)
    with pytest.raises(AdminAuthError):
        decode_admin_token(token, "wrong-secret")


def test_verify_admin_password_with_hash() -> None:
    hashed = bcrypt.hashpw(b"password", bcrypt.gensalt()).decode("utf-8")
    assert verify_admin_password("password", hashed, None)
    assert not verify_admin_password("wrong", hashed, None)


def test_verify_admin_password_with_plain() -> None:
    assert verify_admin_password("secret", None, "secret")
    assert not verify_admin_password("wrong", None, "secret")


def test_verify_admin_password_missing() -> None:
    assert not verify_admin_password("secret", None, None)
