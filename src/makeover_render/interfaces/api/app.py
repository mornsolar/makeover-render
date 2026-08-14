"""FastAPI application factory for the render service."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from makeover_contracts.version import CONTRACT_VERSION

from makeover_render.config.settings import get_settings
from makeover_render.interfaces.api.routers import capabilities, health, jobs


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        yield
    finally:
        await app.state.arq_pool.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="makeover-render",
        version=CONTRACT_VERSION,
        summary="SceneSpec in, animation and GLTF out. Domain-free by design.",
        lifespan=_lifespan,
    )
    app.include_router(health.router)
    app.include_router(capabilities.router)
    app.include_router(jobs.router)
    return app


app = create_app()
