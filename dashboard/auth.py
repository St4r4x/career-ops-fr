from __future__ import annotations

import os

import jwt
from fastapi import HTTPException, Request

_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
_ALGORITHM = "HS256"
_AUDIENCE = "authenticated"

CurrentUser = dict


def get_current_user(request: Request) -> CurrentUser:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(
            token,
            _JWT_SECRET,
            algorithms=[_ALGORITHM],
            audience=_AUDIENCE,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")
    return {"sub": payload["sub"], "email": payload.get("email", "")}
