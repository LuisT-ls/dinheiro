"""Personal PIN authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from ..rate_limit import enforce_rate_limit
from ..schemas import AuthLoginRequest, AuthStatusResponse
from ..security import (
    auth_status,
    clear_session_cookie,
    is_auth_configured,
    set_session_cookie,
    verify_access_pin,
)


router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.get("/me", response_model=AuthStatusResponse)
def get_auth_status(request: Request) -> AuthStatusResponse:
    return AuthStatusResponse.model_validate(auth_status(request))


@router.post("/login", response_model=AuthStatusResponse)
def login(
    payload: AuthLoginRequest,
    request: Request,
    response: Response,
) -> AuthStatusResponse:
    enforce_rate_limit(request, "auth-login", limit=5, window_seconds=15 * 60)

    if not is_auth_configured():
        raise HTTPException(
            status_code=503,
            detail="APP_ACCESS_PIN não está configurada no backend.",
        )
    if not verify_access_pin(payload.pin):
        raise HTTPException(status_code=401, detail="PIN incorreto.")

    set_session_cookie(response, request)
    return AuthStatusResponse(configured=True, authenticated=True)


@router.post("/logout", response_model=AuthStatusResponse)
def logout(response: Response) -> AuthStatusResponse:
    clear_session_cookie(response)
    return AuthStatusResponse(
        configured=is_auth_configured(),
        authenticated=False,
    )
