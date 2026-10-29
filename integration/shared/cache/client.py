import redis.asyncio as redis

from integration.shared.cache.config import cache_settings

_client: redis.Redis | None = None


async def open_client() -> None:
    global _client
    _client = redis.from_url(cache_settings.redis_url, decode_responses=True)


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_client() -> redis.Redis:
    assert _client is not None, "redis client not initialized — call open_client() during app startup"
    return _client
