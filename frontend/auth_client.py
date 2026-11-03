"""Talks to the real auth-api the same way a standalone login page/logout
button would — no shortcuts through agentic_core, which only ever consumes an
already-issued JWT."""

import httpx
from pydantic import BaseModel

from frontend.config import settings


class LoginResult(BaseModel):
    token: str
    role: str
    customer_id: int | None
    username: str


def login(username: str, password: str) -> LoginResult:
    with httpx.Client(base_url=settings.auth_api_base_url, timeout=10) as client:
        response = client.post("/auth/token", json={"username": username, "password": password})
        response.raise_for_status()
        body = response.json()
    return LoginResult(token=body["access_token"], role=body["role"], customer_id=body.get("customer_id"), username=username)


def logout(token: str) -> None:
    with httpx.Client(base_url=settings.auth_api_base_url, timeout=10) as client:
        client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
