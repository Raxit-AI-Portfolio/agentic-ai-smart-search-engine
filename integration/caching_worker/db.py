import asyncpg

from integration.caching_worker.config import worker_settings

_customer_pool: asyncpg.Pool | None = None
_operations_pool: asyncpg.Pool | None = None


async def open_pools() -> None:
    global _customer_pool, _operations_pool
    _customer_pool = await asyncpg.create_pool(worker_settings.customerdb_worker_url)
    _operations_pool = await asyncpg.create_pool(worker_settings.operationsdb_worker_url)


async def close_pools() -> None:
    global _customer_pool, _operations_pool
    if _customer_pool is not None:
        await _customer_pool.close()
        _customer_pool = None
    if _operations_pool is not None:
        await _operations_pool.close()
        _operations_pool = None


def customer_pool() -> asyncpg.Pool:
    assert _customer_pool is not None, "customerdb pool not initialized — call open_pools() during startup"
    return _customer_pool


def operations_pool() -> asyncpg.Pool:
    assert _operations_pool is not None, "operationsdb pool not initialized — call open_pools() during startup"
    return _operations_pool
