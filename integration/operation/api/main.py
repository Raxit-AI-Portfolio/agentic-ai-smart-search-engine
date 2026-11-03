from contextlib import asynccontextmanager

from fastapi import FastAPI

from integration.operation.api.db import close_pools, open_pools
from integration.operation.api.routers import deliveries, invoices, order_products, orders, payments, products

# Auth is verified by calling the Auth API (see integration.operation.api.auth_client)
# instead of decoding the JWT / checking revocation in this process.


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pools()
    yield
    await close_pools()


app = FastAPI(title="Operations API", lifespan=lifespan)

app.include_router(products.router)
app.include_router(orders.router)
app.include_router(order_products.router)
app.include_router(payments.router)
app.include_router(invoices.router)
app.include_router(deliveries.router)
