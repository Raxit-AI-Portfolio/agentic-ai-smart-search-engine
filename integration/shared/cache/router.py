from fastapi import APIRouter, HTTPException, status

from integration.shared.cache.schemas import CacheGetResponse, CacheSetRequest
from integration.shared.cache.service import get_cache, set_cache

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/{key}", response_model=CacheGetResponse)
async def get_cache_entry(key: str) -> CacheGetResponse:
    value = await get_cache(key)
    if value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return CacheGetResponse(key=key, value=value)


@router.post("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def set_cache_entry(key: str, request: CacheSetRequest) -> None:
    await set_cache(key, request.value, request.ttl_seconds)
