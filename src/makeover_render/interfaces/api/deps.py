"""Composition root for the render service."""

from __future__ import annotations

from typing import Annotated

from arq import ArqRedis
from fastapi import Depends, Request

from makeover_render.application.ports.job_queue import JobQueue
from makeover_render.composition import build_blender_runtime, build_job_queue
from makeover_render.config.settings import Settings, get_settings
from makeover_render.infrastructure.blender.runtime import BlenderRuntime

SettingsDep = Annotated[Settings, Depends(get_settings)]


def provide_blender_runtime(settings: SettingsDep) -> BlenderRuntime:
    return build_blender_runtime(settings)


BlenderRuntimeDep = Annotated[BlenderRuntime, Depends(provide_blender_runtime)]


def provide_arq_pool(request: Request) -> ArqRedis:
    # Created once in the app's lifespan, not per-request - a fresh
    # connection pool per request would defeat the point of pooling.
    return request.app.state.arq_pool  # type: ignore[no-any-return]


def provide_job_queue(pool: Annotated[ArqRedis, Depends(provide_arq_pool)]) -> JobQueue:
    return build_job_queue(pool)


JobQueueDep = Annotated[JobQueue, Depends(provide_job_queue)]
