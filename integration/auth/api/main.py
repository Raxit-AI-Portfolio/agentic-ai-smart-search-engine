from contextlib import asynccontextmanager

from fastapi import FastAPI

from integration.auth.api.db import close_pool, open_pool
from integration.auth.api.router import router as auth_router
from integration.shared.cache.client import close_client, open_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pool()
    await open_client()
    yield
    await close_client()
    await close_pool()


app = FastAPI(title="Auth API", lifespan=lifespan)

app.include_router(auth_router)
