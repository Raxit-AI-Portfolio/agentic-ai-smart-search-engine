import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from integration.customer.api.auth_client import CurrentUser, get_current_user
from integration.customer.api.authz import require_manager_dep, require_self_or_staff
from integration.customer.api.db import get_pool
from integration.customer.api.schemas import AddressOut

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressOut])
async def get_addresses(
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[AddressOut]:
    """ALL addresses for ALL customers — no filter, no params. Manager only."""
    rows = await pool.fetch("SELECT * FROM ss.customer_address")
    return [AddressOut(**row) for row in rows]


@router.get("/customer/{customer_id}", response_model=list[AddressOut])
async def get_addresses_by_customer(
    customer_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[AddressOut]:
    """ALL addresses for ONE customer, given their known customer_id."""
    require_self_or_staff(current_user, customer_id)
    rows = await pool.fetch("SELECT * FROM ss.customer_address WHERE customer_id = $1", customer_id)
    return [AddressOut(**row) for row in rows]


@router.get("/{customer_address_id}", response_model=AddressOut)
async def get_address(
    customer_address_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> AddressOut:
    """ONE address, given its known customer_address_id (not a customer_id)."""
    row = await pool.fetchrow(
        "SELECT * FROM ss.customer_address WHERE customer_address_id = $1", customer_address_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
    require_self_or_staff(current_user, row["customer_id"])
    return AddressOut(**row)
