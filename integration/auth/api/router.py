from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from integration.auth.api.schemas import CurrentUser, LoginRequest, TokenResponse
from integration.auth.api.security import create_access_token, revoke_token, verify_token
from integration.auth.api.service import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer_scheme = HTTPBearer()


@router.post("/token", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    identity = await authenticate(request.username, request.password)
    if identity is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token = await create_access_token(identity.username, identity.email, identity.role, identity.customer_id)
    return TokenResponse(access_token=token, role=identity.role, customer_id=identity.customer_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)) -> None:
    await revoke_token(credentials.credentials)


@router.post("/verify", response_model=CurrentUser)
async def verify(credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)) -> CurrentUser:
    return await verify_token(credentials.credentials)
