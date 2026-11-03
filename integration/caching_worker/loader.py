from integration.caching_worker.db import customer_pool, operations_pool
from integration.customer.api.main import app as customer_app
from integration.operation.api.main import app as operations_app
from integration.shared.permissions import extract_permissions
from integration.shared.cache.service import set_cache


async def load_all() -> None:
    await _load_locations()
    await _load_products()
    await _load_statuses()
    await _load_api_permissions()


async def _load_locations() -> None:
    rows = await customer_pool().fetch("SELECT city, state, country FROM ss.address_locations")
    await set_cache("lookup:cities", sorted({r["city"] for r in rows}))
    await set_cache("lookup:states", sorted({r["state"] for r in rows if r["state"] is not None}))
    await set_cache("lookup:countries", sorted({r["country"] for r in rows}))


async def _load_products() -> None:
    products = await operations_pool().fetch("SELECT * FROM ss.get_products()")
    await set_cache("lookup:products", [dict(row) for row in products])

    categories = await operations_pool().fetch("SELECT * FROM ss.get_categories()")
    await set_cache("lookup:categories", [row["category"] for row in categories])

    sub_categories = await operations_pool().fetch("SELECT * FROM ss.get_sub_categories()")
    await set_cache("lookup:sub_categories", [row["sub_category"] for row in sub_categories])


async def _load_statuses() -> None:
    order_statuses = await operations_pool().fetch("SELECT * FROM ss.get_order_statuses()")
    await set_cache("lookup:order_statuses", [row["order_status"] for row in order_statuses])

    delivery_statuses = await operations_pool().fetch("SELECT * FROM ss.get_delivery_statuses()")
    await set_cache("lookup:delivery_statuses", [row["delivery_status"] for row in delivery_statuses])


# Reflects customer-api's and operations-api's route tables (imported here purely
# for their FastAPI `app` objects — no DB pool of theirs is ever opened by this
# process) so the API MCP server's permission manifest can't drift from what each
# route's own require_staff_dep/require_manager_dep dependency actually enforces.
async def _load_api_permissions() -> None:
    await set_cache("api-permissions:customer", extract_permissions(customer_app))
    await set_cache("api-permissions:operations", extract_permissions(operations_app))
