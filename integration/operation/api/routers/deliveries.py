import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from integration.operation.api.auth_client import CurrentUser, get_current_user
from integration.operation.api.authz import require_manager_dep, require_self_or_staff
from integration.operation.api.db import get_pool
from integration.operation.api.schemas import DeliveryOut, DeliveryStatusOut

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("", response_model=list[DeliveryOut])
async def get_deliveries(
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[DeliveryOut]:
    """ALL deliveries for ALL orders — no filter, no params. Manager only."""
    rows = await pool.fetch("SELECT * FROM ss.get_deliveries()")
    return [DeliveryOut(**row) for row in rows]


@router.get("/by-order/{order_id}/status", response_model=DeliveryStatusOut)
async def get_delivery_status_by_order(
    order_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> DeliveryStatusOut:
    """Delivery status and date for ONE order, given its known order_id."""
    row = await pool.fetchrow("SELECT * FROM ss.get_delivery_status_by_order($1)", order_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    require_self_or_staff(current_user, row["customer_id"])
    return DeliveryStatusOut(order_id=row["order_id"], delivery_status=row["delivery_status"], delivery_date=row["delivery_date"])


@router.get("/{delivery_id}", response_model=DeliveryOut)
async def get_delivery(
    delivery_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> DeliveryOut:
    """ONE delivery, given its known delivery_id (not an order_id — use by-order/{order_id}/status for that)."""
    row = await pool.fetchrow("SELECT * FROM ss.get_delivery($1)", delivery_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    require_self_or_staff(current_user, row["customer_id"])
    return DeliveryOut(**row)
