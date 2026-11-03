import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from integration.operation.api.auth_client import CurrentUser, get_current_user
from integration.operation.api.authz import require_manager_dep, require_self_or_staff
from integration.operation.api.db import get_pool
from integration.operation.api.schemas import InvoiceOut

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.get("", response_model=list[InvoiceOut])
async def get_invoices(
    current_user: CurrentUser = Depends(require_manager_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[InvoiceOut]:
    """ALL invoices for ALL orders — no filter, no params. Manager only."""
    rows = await pool.fetch("SELECT * FROM ss.get_invoices()")
    return [InvoiceOut(**row) for row in rows]


@router.get("/by-order/{order_id}", response_model=InvoiceOut)
async def get_invoice_by_order(
    order_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> InvoiceOut:
    """The invoice for ONE order, given its known order_id — this is how to find an order's payment_id (invoice.payment_id), since there is no direct get-payment-by-order."""
    row = await pool.fetchrow("SELECT * FROM ss.get_invoice_by_order($1)", order_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    require_self_or_staff(current_user, row["customer_id"])
    return InvoiceOut(**row)


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> InvoiceOut:
    """ONE invoice, given its known invoice_id (not an order_id — use by-order/{order_id} for that)."""
    row = await pool.fetchrow("SELECT * FROM ss.get_invoice($1)", invoice_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    require_self_or_staff(current_user, row["customer_id"])
    return InvoiceOut(**row)
