from __future__ import annotations

import os

import jwt
from fastapi import HTTPException, Request, Response

_ALGORITHM = "HS256"
_AUDIENCE = "authenticated"
_COOKIE_SESSION = "session"
_COOKIE_REFRESH = "refresh"
_COOKIE_MAX_AGE_SESSION = 3600
_COOKIE_MAX_AGE_REFRESH = 604800

CurrentUser = dict

_DEV_USER: CurrentUser = {"sub": "dev-user-local", "email": "arnaud@local"}


def _jwt_secret() -> str:
    return os.getenv("SUPABASE_JWT_SECRET", "")


def validate_access_token(token: str) -> CurrentUser:
    """Decode and validate a Supabase access token. Raises HTTPException(401) if invalid."""
    secret = _jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=500, detail="SUPABASE_JWT_SECRET is not configured"
        )
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM], audience=_AUDIENCE)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    return {"sub": payload["sub"], "email": payload.get("email", "")}


def get_current_user(request: Request) -> CurrentUser:
    if os.getenv("DEV_AUTO_LOGIN") == "true":
        return _DEV_USER
    token = request.cookies.get(_COOKIE_SESSION)
    if not token:
        raise HTTPException(status_code=302, headers={"location": "/login"})
    secret = _jwt_secret()
    if not secret:
        raise HTTPException(
            status_code=500, detail="SUPABASE_JWT_SECRET is not configured"
        )
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM], audience=_AUDIENCE)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=302, headers={"location": "/login"})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=302, headers={"location": "/login"})
    return {"sub": payload["sub"], "email": payload.get("email", "")}


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    response.set_cookie(
        _COOKIE_SESSION,
        access_token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=_COOKIE_MAX_AGE_SESSION,
        secure=secure,
    )
    response.set_cookie(
        _COOKIE_REFRESH,
        refresh_token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=_COOKIE_MAX_AGE_REFRESH,
        secure=secure,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(_COOKIE_SESSION, path="/")
    response.delete_cookie(_COOKIE_REFRESH, path="/")
