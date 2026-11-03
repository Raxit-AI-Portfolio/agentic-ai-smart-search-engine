import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from integration.operation.api.auth_client import CurrentUser, get_current_user
from integration.operation.api.authz import require_manager_dep, require_self_or_staff
from integration.operation.api.db import get_pool
from integration.operation.api.schemas import CompleteOrderOut, OrderLineItemOut, OrderOut, OrderStatusOut

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
async def get_orders(
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[OrderOut]:
    """ALL orders for ALL customers — no filter, no params. Manager only. For a customer's own orders, use GET /orders/me instead."""
    rows = await pool.fetch("SELECT * FROM ss.get_orders()")
    return [OrderOut(**row) for row in rows]


@router.get("/customer/{customer_id}", response_model=list[OrderOut])
async def get_orders_by_customer(
    customer_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[OrderOut]:
    """ALL orders for ONE customer, given their known customer_id. Self-scoped: a customer can only pass their own customer_id."""
    require_self_or_staff(current_user, customer_id)
    rows = await pool.fetch("SELECT * FROM ss.get_orders_by_customer($1)", customer_id)
    return [OrderOut(**row) for row in rows]


@router.get("/me", response_model=list[OrderOut])
async def get_my_orders(
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[OrderOut]:
    """ALL orders for the calling customer — no id/params needed, resolved from the caller's own verified identity. Customer role only; use GET /orders/customer/{customer_id} for staff looking up a specific customer."""
    if current_user.customer_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Caller has no associated customer_id")
    rows = await pool.fetch("SELECT * FROM ss.get_orders_by_customer($1)", current_user.customer_id)
    return [OrderOut(**row) for row in rows]


async def _get_owned_order(pool: asyncpg.Pool, current_user: CurrentUser, order_id: int) -> asyncpg.Record:
    row = await pool.fetchrow("SELECT * FROM ss.get_order($1)", order_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    require_self_or_staff(current_user, row["customer_id"])
    return row


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> OrderOut:
    """ONE order, given its known order_id. Does not include payment/invoice info — those are separate resources referencing the same order_id."""
    row = await _get_owned_order(pool, current_user, order_id)
    return OrderOut(**row)


@router.get("/{order_id}/complete", response_model=CompleteOrderOut)
async def get_complete_order(
    order_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> CompleteOrderOut:
    """ONE order plus its product line items (with unit prices), given its known order_id."""
    order_row = await _get_owned_order(pool, current_user, order_id)
    line_item_rows = await pool.fetch("SELECT * FROM ss.get_order_line_items($1)", order_id)
    return CompleteOrderOut(
        order=OrderOut(**order_row),
        products=[OrderLineItemOut(**row) for row in line_item_rows],
    )


@router.get("/{order_id}/status", response_model=OrderStatusOut)
async def get_order_status(
    order_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> OrderStatusOut:
    """Just the status of ONE order, given its known order_id."""
    row = await pool.fetchrow("SELECT * FROM ss.get_order_status($1)", order_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    require_self_or_staff(current_user, row["customer_id"])
    return OrderStatusOut(order_id=row["order_id"], order_status=row["order_status"])
