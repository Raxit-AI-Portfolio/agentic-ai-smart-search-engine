import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Request, status

from integration.operation.api.auth_client import CurrentUser, get_current_user
from integration.operation.api.authz import require_manager_dep, require_self_or_staff
from integration.operation.api.customer_api_client import get_payment_method_ids_by_type
from integration.operation.api.db import get_pool
from integration.operation.api.schemas import PaymentOut
from integration.shared.enums import PaymentType

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentOut])
async def get_payments(
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[PaymentOut]:
    """ALL payments for ALL orders — no filter, no params. Manager only."""
    rows = await pool.fetch("SELECT * FROM ss.get_payments()")
    return [PaymentOut(**row) for row in rows]


@router.get("/type/{payment_type}", response_model=list[PaymentOut])
async def get_payments_by_type(
    payment_type: PaymentType,
    request: Request,
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[PaymentOut]:
    """ALL payments (any customer) made with ONE exact payment_type ("Debit Card" or "Credit Card"). Manager only. Resolves the type to payment methods via the customer-api first."""
    authorization_header = request.headers["authorization"]
    payment_method_ids = await get_payment_method_ids_by_type(payment_type, authorization_header)
    if not payment_method_ids:
        return []
    rows = await pool.fetch("SELECT * FROM ss.get_payments_by_method_ids($1)", payment_method_ids)
    return [PaymentOut(**row) for row in rows]


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> PaymentOut:
    """ONE payment, given its known payment_id (not an order_id — there is no get-payment-by-order; fetch the order's invoice first, which carries payment_id)."""
    row = await pool.fetchrow("SELECT * FROM ss.get_payment($1)", payment_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    require_self_or_staff(current_user, row["customer_id"])
    return PaymentOut(**row)
