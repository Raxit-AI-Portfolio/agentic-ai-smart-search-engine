import json

import httpx
import redis.asyncio as redis

from agentic_core.configs.config import settings

_BASE_URLS = {
    "customer": settings.customer_api_base_url,
    "operations": settings.operations_api_base_url,
}

# resource ids are "service:METHOD /path" — a bare "METHOD /path" can't say
# which of the two APIs to call, since both are reflected into one flat dict.
_SERVICE_CACHE_KEYS = {"customer": "api-permissions:customer", "operations": "api-permissions:operations"}

_redis_client: redis.Redis | None = None


def _get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def call_api(
    service: str,
    method: str,
    path: str,
    authorization_header: str,
    params: dict | None = None,
    json: dict | None = None,
) -> dict:
    async with httpx.AsyncClient(base_url=_BASE_URLS[service]) as client:
        response = await client.request(
            method, path, params=params, json=json, headers={"Authorization": authorization_header}
        )
        response.raise_for_status()
        return response.json()


async def _get_route_entries() -> dict[str, dict]:
    # Written by integration/caching_worker/loader.py's _load_api_permissions
    # (via integration/shared/permissions.py's extract_permissions), which
    # reflects customer-api's and operations-api's own route tables — roles
    # AND each endpoint's docstring — at startup. This just reads what they
    # already published; resource ids are "service:METHOD /path" since a bare
    # "METHOD /path" can't say which of the two APIs to call.
    client = _get_redis_client()
    entries: dict[str, dict] = {}
    for service, key in _SERVICE_CACHE_KEYS.items():
        raw = await client.get(key)
        if raw is not None:
            for route, entry in json.loads(raw).items():
                entries[f"{service}:{route}"] = entry
    return entries


async def list_permissions() -> dict[str, list[str]]:
    return {resource_id: entry["roles"] for resource_id, entry in (await _get_route_entries()).items()}


async def describe_objects() -> dict[str, str]:
    """Each endpoint's own docstring, keyed the same way as list_permissions —
    used to give the planning LLM a real idea of what an API resource does
    instead of just its route string."""
    return {
        resource_id: entry["description"]
        for resource_id, entry in (await _get_route_entries()).items()
        if entry["description"]
    }
