from typing import Any

from pydantic import BaseModel


class CacheSetRequest(BaseModel):
    value: Any
    ttl_seconds: int | None = None


class CacheGetResponse(BaseModel):
    key: str
    value: Any
