from contextlib import asynccontextmanager

from fastapi import FastAPI

from integration.customer.api.db import close_pools, open_pools
from integration.customer.api.routers import addresses, payment_methods, users

# Auth is verified by calling the Auth API (see integration.customer.api.auth_client)
# instead of decoding the JWT / checking revocation in this process.


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pools()
    yield
    await close_pools()


app = FastAPI(title="Customer API", lifespan=lifespan)

app.include_router(users.router)
app.include_router(addresses.router)
app.include_router(payment_methods.router)
