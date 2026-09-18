"""Authentication and signed-link helpers for the private quote workspace."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time

from fastapi import HTTPException, Request, Response


SESSION_COOKIE_NAME = "dinheiro_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 30
_CLOCK_SKEW_SECONDS = 300


def _access_pin() -> str:
    return os.getenv("APP_ACCESS_PIN", "").strip()


def is_auth_configured() -> bool:
    return bool(_access_pin())


def _auth_required() -> bool:
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    return is_auth_configured() or os.getenv("VERCEL") == "1" or environment in {
        "production",
        "prod",
    }


def _session_secret() -> bytes:
    configured_secret = os.getenv("APP_SESSION_SECRET", "").strip()
    if configured_secret:
        return configured_secret.encode("utf-8")

    # This fallback keeps local development simple while still avoiding a
    # secret in the frontend bundle. Production should always set the secret.
    pin = _access_pin()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "dinheiro")
    if not pin:
        return b""
    return hashlib.sha256(
        f"dinheiro-session:{project_id}:{pin}".encode("utf-8"),
    ).digest()


def _signature(value: str) -> str:
    secret = _session_secret()
    if not secret:
        return ""
    digest = hmac.new(secret, value.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def create_session_token() -> str:
    timestamp = str(int(time.time()))
    return f"{timestamp}.{_signature(timestamp)}"


def _valid_session_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False

    timestamp, signature = token.split(".", 1)
    try:
        issued_at = int(timestamp)
    except ValueError:
        return False

    age = int(time.time()) - issued_at
    if age < -_CLOCK_SKEW_SECONDS or age > SESSION_TTL_SECONDS:
        return False

    expected = _signature(timestamp)
    return bool(expected) and hmac.compare_digest(signature, expected)


def request_is_authenticated(request: Request) -> bool:
    return _valid_session_token(request.cookies.get(SESSION_COOKIE_NAME))


def auth_status(request: Request) -> dict[str, bool]:
    return {
        "configured": is_auth_configured(),
        "authenticated": request_is_authenticated(request) or not _auth_required(),
    }


def verify_access_pin(pin: str) -> bool:
    configured_pin = _access_pin()
    return bool(configured_pin) and hmac.compare_digest(pin.strip(), configured_pin)


def require_authenticated_user(request: Request) -> bool:
    if not _auth_required() or request_is_authenticated(request):
        return True
    raise HTTPException(
        status_code=401,
        detail="Sessão inválida ou expirada. Faça login novamente.",
    )


def set_session_cookie(response: Response, request: Request) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https" or os.getenv("VERCEL") == "1",
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
        path="/",
    )


def make_share_token(quote_id: str) -> str:
    return _signature(f"share:{quote_id}")


def verify_share_token(quote_id: str, token: str | None) -> bool:
    expected = make_share_token(quote_id)
    return bool(expected and token) and hmac.compare_digest(token or "", expected)
