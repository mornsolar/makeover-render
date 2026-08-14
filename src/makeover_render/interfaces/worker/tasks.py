"""The arq task that performs one render job.

Runs in a separate ``arq`` worker process; the API process only ever
enqueues and polls. ``RunRenderJob`` does blocking subprocess calls (Blender,
ffmpeg), so it runs in a thread rather than blocking the worker's event loop.
"""

from __future__ import annotations

import asyncio
from typing import Any

from makeover_contracts.jobs import ArtifactBundle
from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.job_queue import RENDER_JOB_FUNCTION_NAME
from makeover_render.composition import build_run_render_job
from makeover_render.config.settings import get_settings


async def render_job(ctx: dict[str, Any], spec: SceneSpec) -> ArtifactBundle:
    settings = get_settings()
    out_dir = settings.artifact_dir / ctx["job_id"]
    use_case = build_run_render_job(settings)
    return await asyncio.to_thread(use_case.execute, spec, out_dir)


# arq registers this function under its own ``__qualname__`` (there's no
# separate "name" arg in ``WorkerSettings.functions``); this assertion is
# what keeps that name from silently drifting away from the constant
# ``ArqJobQueue.enqueue`` calls by.
assert render_job.__name__ == RENDER_JOB_FUNCTION_NAME
