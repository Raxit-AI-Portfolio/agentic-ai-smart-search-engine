import asyncpg
from fastapi import Depends

from integration.customer.api.auth_client import CurrentUser, get_current_user
from integration.customer.api.config import settings

_DB_URL_BY_ROLE = {
    "customer": settings.customerdb_customer_url,
    "worker": settings.customerdb_worker_url,
    "manager": settings.customerdb_manager_url,
}

_pools: dict[str, asyncpg.Pool] = {}


async def open_pools() -> None:
    for role, url in _DB_URL_BY_ROLE.items():
        _pools[role] = await asyncpg.create_pool(url)


async def close_pools() -> None:
    for pool in _pools.values():
        await pool.close()
    _pools.clear()


async def get_pool(current_user: CurrentUser = Depends(get_current_user)) -> asyncpg.Pool:
    return _pools[current_user.role]
