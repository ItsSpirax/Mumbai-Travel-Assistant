from contextlib import asynccontextmanager
from typing import Optional

import httpx
from redis.asyncio import Redis as AsyncRedis

from fastmcp import FastMCP
from utils import config


class AppState:
    http_client: Optional[httpx.AsyncClient] = None
    redis_client: Optional[AsyncRedis] = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastMCP):
    app_state.http_client = httpx.AsyncClient(timeout=30.0)

    if config.REDIS_HOST:
        try:
            redis_client = AsyncRedis(
                host=config.REDIS_HOST,
                port=int(config.REDIS_PORT),
                db=int(config.REDIS_DB),
                decode_responses=False,
            )
            await redis_client.ping()
            app_state.redis_client = redis_client
        except Exception as e:
            print(f"Redis connection error: {e}")

    try:
        from tools import get_penalty_details

        await get_penalty_details.ensure_penalty_embeddings()
    except Exception as exc:
        print(f"Penalty embedding warmup failed: {exc}")

    try:
        yield
    finally:
        if app_state.http_client:
            await app_state.http_client.aclose()
        print("Cleanup complete")


mcp = FastMCP("travel-assistant-mcp", lifespan=lifespan)
