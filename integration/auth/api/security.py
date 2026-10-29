from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status

from integration.auth.api.config import auth_settings
from integration.auth.api.db import get_pool
from integration.auth.api.schemas import CurrentUser
from integration.shared.cache.service import delete_cache, get_cache, set_cache


async def create_access_token(username: str, email: str, role: str, customer_id: int | None) -> str:
    now = datetime.now(timezone.utc)
    jti = str(uuid4())
    payload = {
        "sub": username,
        "email": email,
        "role": role,
        "customer_id": customer_id,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(minutes=auth_settings.jwt_expire_minutes),
    }
    token = jwt.encode(payload, auth_settings.jwt_secret_key, algorithm=auth_settings.jwt_algorithm)
    # The cache entry is the source of truth for "is this token still valid" —
    # verify_token checks Redis, not membershipdb, so revocation/expiry both
    # just come down to whether auth:{jti} is still present.
    await set_cache(
        f"auth:{jti}",
        {"username": username, "email": email, "role": role, "customer_id": customer_id},
        ttl_seconds=auth_settings.jwt_expire_minutes * 60,
    )
    return token


async def revoke_token(token: str) -> None:
    payload = _decode(token)
    await get_pool().execute("SELECT ss.revoke_token($1)", UUID(payload["jti"]))
    await delete_cache(f"auth:{payload['jti']}")


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, auth_settings.jwt_secret_key, algorithms=[auth_settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


async def verify_token(token: str) -> CurrentUser:
    payload = _decode(token)
    cached = await get_cache(f"auth:{payload['jti']}")
    if cached is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been logged out")
    return CurrentUser(**cached)
