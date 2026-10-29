import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from integration.operation.api.auth_client import CurrentUser, get_current_user
from integration.operation.api.authz import require_manager_dep, require_self_or_staff
from integration.operation.api.db import get_pool
from integration.operation.api.schemas import OrderOut, OrderProductOut

router = APIRouter(prefix="/order-products", tags=["order-products"])


@router.get("", response_model=list[OrderProductOut])
async def get_order_products(
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[OrderProductOut]:
    """ALL order-product line rows across ALL orders — no filter, no params. Manager only."""
    rows = await pool.fetch("SELECT * FROM ss.get_order_products()")
    return [OrderProductOut(**row) for row in rows]


@router.get("/by-product/{product_id}", response_model=list[OrderOut])
async def get_orders_by_product(
    product_id: int,
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[OrderOut]:
    """ALL orders (any customer) that contain ONE product, given its known product_id. Manager only."""
    rows = await pool.fetch("SELECT * FROM ss.get_orders_by_product($1)", product_id)
    return [OrderOut(**row) for row in rows]


@router.get("/by-order/{order_id}", response_model=list[OrderProductOut])
async def get_products_by_order(
    order_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[OrderProductOut]:
    """ALL product line items for ONE order, given its known order_id."""
    order_row = await pool.fetchrow("SELECT * FROM ss.get_order($1)", order_id)
    if order_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    require_self_or_staff(current_user, order_row["customer_id"])
    rows = await pool.fetch("SELECT * FROM ss.get_order_product_by_order($1)", order_id)
    return [OrderProductOut(customer_id=order_row["customer_id"], **row) for row in rows]


@router.get("/{order_product_id}", response_model=OrderProductOut)
async def get_order_product(
    order_product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> OrderProductOut:
    """ONE order-product line row, given its known order_product_id (not an order_id or product_id)."""
    row = await pool.fetchrow("SELECT * FROM ss.get_order_product($1)", order_product_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order product not found")
    require_self_or_staff(current_user, row["customer_id"])
    return OrderProductOut(**row)
