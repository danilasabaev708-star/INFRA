from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt


class AdminAuthError(Exception):
    pass


@dataclass(frozen=True)
class AdminSession:
    username: str


def _b64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("utf-8")


def _b64url_decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)


def create_admin_token(username: str, secret: str, ttl_minutes: int) -> str:
    if not secret:
        raise AdminAuthError("JWT secret is not configured.")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_minutes)).timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_admin_token(token: str, secret: str) -> dict[str, Any]:
    if not secret:
        raise AdminAuthError("JWT secret is not configured.")
    parts = token.split(".")
    if len(parts) != 3:
        raise AdminAuthError("Invalid token format.")
    header_b64, payload_b64, signature_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_signature = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise AdminAuthError("Invalid token signature.")
    payload = json.loads(_b64url_decode(payload_b64))
    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise AdminAuthError("Invalid token payload.")
    now_ts = datetime.now(timezone.utc).timestamp()
    if now_ts > exp:
        raise AdminAuthError("Token expired.")
    return payload


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(16)


def verify_admin_password(password: str, password_hash: str | None, password_plain: str | None) -> bool:
    if password_hash:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            return False
    if password_plain:
        return secrets.compare_digest(password, password_plain)
    return False
