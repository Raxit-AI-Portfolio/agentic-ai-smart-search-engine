from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    customer_id: int | None


class CurrentUser(BaseModel):
    username: str
    email: str
    role: str
    customer_id: int | None
