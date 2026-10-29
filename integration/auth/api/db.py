import asyncpg

from integration.auth.api.config import auth_settings

_pool: asyncpg.Pool | None = None


async def open_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(auth_settings.membership_db_url)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    assert _pool is not None, "membership DB pool not initialized — call open_pool() during app startup"
    return _pool
