import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from integration.customer.api.auth_client import CurrentUser, get_current_user
from integration.customer.api.authz import require_manager_dep, require_self_or_staff
from integration.customer.api.db import get_pool
from integration.customer.api.schemas import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def get_users(
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[UserOut]:
    """ALL customer profiles (name, email, phone) — no filter, no params. Manager only."""
    rows = await pool.fetch("SELECT * FROM ss.customer_profile")
    return [UserOut(**row) for row in rows]


@router.get("/{customer_id}", response_model=UserOut)
async def get_user(
    customer_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> UserOut:
    """ONE customer's profile, given their known customer_id."""
    require_self_or_staff(current_user, customer_id)
    row = await pool.fetchrow("SELECT * FROM ss.customer_profile WHERE customer_id = $1", customer_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return UserOut(**row)
