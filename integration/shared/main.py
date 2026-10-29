from contextlib import asynccontextmanager

from fastapi import FastAPI

from integration.shared.cache.client import close_client, open_client
from integration.shared.cache.router import router as cache_router
from integration.shared.documents.router import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_client()
    yield
    await close_client()


app = FastAPI(title="Shared API", lifespan=lifespan)

app.include_router(cache_router, prefix="/shared")
app.include_router(documents_router, prefix="/shared")
