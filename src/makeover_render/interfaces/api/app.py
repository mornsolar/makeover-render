"""FastAPI application factory for the render service."""

from __future__ import annotations

from fastapi import FastAPI
from makeover_contracts.version import CONTRACT_VERSION

from makeover_render.interfaces.api.routers import capabilities, health


def create_app() -> FastAPI:
    app = FastAPI(
        title="makeover-render",
        version=CONTRACT_VERSION,
        summary="SceneSpec in, animation and GLTF out. Domain-free by design.",
    )
    app.include_router(health.router)
    app.include_router(capabilities.router)
    return app


app = create_app()
