from pydantic import BaseModel, Field


class SqlResult(BaseModel):
    query: str
    rows: list[dict] = Field(default_factory=list)
    error: str | None = None
    retries: int = 0


class ApiResult(BaseModel):
    payload: dict | None = None
    error: str | None = None
