import json
from typing import Any

from integration.shared.cache.client import get_client


async def set_cache(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    # default=str covers Decimal/datetime values coming straight out of asyncpg rows.
    await get_client().set(key, json.dumps(value, default=str), ex=ttl_seconds)


async def get_cache(key: str) -> Any | None:
    raw = await get_client().get(key)
    return None if raw is None else json.loads(raw)


async def delete_cache(key: str) -> None:
    await get_client().delete(key)
