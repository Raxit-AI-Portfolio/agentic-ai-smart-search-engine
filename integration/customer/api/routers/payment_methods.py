import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from integration.customer.api.auth_client import CurrentUser, get_current_user
from integration.customer.api.authz import require_manager_dep, require_self_or_staff
from integration.customer.api.db import get_pool
from integration.customer.api.schemas import PaymentMethodOut
from integration.shared.enums import PaymentType

router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])


@router.get("", response_model=list[PaymentMethodOut])
async def get_payment_methods(
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[PaymentMethodOut]:
    """ALL payment methods for ALL customers — no filter, no params. Manager only."""
    rows = await pool.fetch("SELECT * FROM ss.customer_payment")
    return [PaymentMethodOut(**row) for row in rows]


@router.get("/customer/{customer_id}", response_model=list[PaymentMethodOut])
async def get_payment_methods_by_customer(
    customer_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[PaymentMethodOut]:
    """ALL payment methods for ONE customer, given their known customer_id."""
    require_self_or_staff(current_user, customer_id)
    rows = await pool.fetch("SELECT * FROM ss.customer_payment WHERE customer_id = $1", customer_id)
    return [PaymentMethodOut(**row) for row in rows]


@router.get("/type/{payment_type}", response_model=list[PaymentMethodOut])
async def get_payment_methods_by_type(
    payment_type: PaymentType,
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[PaymentMethodOut]:
    """ALL payment methods (any customer) of ONE exact payment_type ("Debit Card" or "Credit Card"). Manager only."""
    rows = await pool.fetch("SELECT * FROM ss.customer_payment WHERE payment_type = $1", payment_type.value)
    return [PaymentMethodOut(**row) for row in rows]


@router.get("/{payment_method_id}", response_model=PaymentMethodOut)
async def get_payment_method(
    payment_method_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> PaymentMethodOut:
    """ONE payment method, given its known payment_method_id."""
    row = await pool.fetchrow(
        "SELECT * FROM ss.customer_payment WHERE payment_method_id = $1", payment_method_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found")
    require_self_or_staff(current_user, row["customer_id"])
    return PaymentMethodOut(**row)
