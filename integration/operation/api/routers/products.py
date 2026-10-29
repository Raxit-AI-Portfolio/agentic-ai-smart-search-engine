import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from integration.operation.api.auth_client import CurrentUser, get_current_user
from integration.operation.api.authz import require_staff_dep
from integration.operation.api.db import get_pool
from integration.operation.api.schemas import ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def get_products(
    current_user: CurrentUser = Depends(require_staff_dep),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[ProductOut]:
    """ALL products in the catalog, including current inventory/stock level
    (the `quantity` field on each) — no filter, no params."""
    rows = await pool.fetch("SELECT * FROM ss.get_products()")
    return [ProductOut(**row) for row in rows]


@router.get("/category/{category}", response_model=list[ProductOut])
async def get_products_by_category(
    category: str,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> list[ProductOut]:
    """ALL products (including current inventory/stock level, the `quantity`
    field) in ONE exact category (case-sensitive equality, not fuzzy)."""
    rows = await pool.fetch("SELECT * FROM ss.get_products_by_category($1)", category)
    return [ProductOut(**row) for row in rows]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_pool),
) -> ProductOut:
    """ONE product, given its known product_id."""
    row = await pool.fetchrow("SELECT * FROM ss.get_product($1)", product_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return ProductOut(**row)
