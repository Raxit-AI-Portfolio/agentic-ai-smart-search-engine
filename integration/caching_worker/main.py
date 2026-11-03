import asyncio
import logging

from integration.caching_worker.db import close_pools, open_pools
from integration.caching_worker.loader import load_all
from integration.shared.cache.client import close_client, open_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("caching-worker")


async def main() -> None:
    await open_pools()
    await open_client()
    try:
        await load_all()
        logger.info("Startup cache load complete")
        # MVP scope loads once at startup; stay alive as a long-running
        # container instead of exiting (real deployments would add periodic
        # refresh / invalidation here).
        await asyncio.Event().wait()
    finally:
        await close_client()
        await close_pools()


if __name__ == "__main__":
    asyncio.run(main())
