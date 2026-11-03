from dataclasses import dataclass

from integration.auth.api.db import get_pool


@dataclass(frozen=True)
class Identity:
    username: str
    email: str
    role: str
    customer_id: int | None


async def authenticate(username: str, password: str) -> Identity | None:
    row = await get_pool().fetchrow("SELECT * FROM ss.authenticate($1, $2)", username, password)
    if row is None:
        return None
    return Identity(row["username"], row["email"], row["role"], row["customer_id"])
