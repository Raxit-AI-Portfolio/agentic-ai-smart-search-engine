import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from integration.operation.api.config import settings

_bearer_scheme = HTTPBearer()


class CurrentUser(BaseModel):
    username: str
    email: str
    role: str
    customer_id: int | None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)) -> CurrentUser:
    async with httpx.AsyncClient(base_url=settings.auth_api_base_url) as client:
        try:
            response = await client.post("/auth/verify", headers={"Authorization": f"Bearer {credentials.credentials}"})
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Auth API unavailable") from exc
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=response.json().get("detail"))
    response.raise_for_status()
    return CurrentUser(**response.json())
