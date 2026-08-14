"""Object graph construction.

The HTTP API, the CLI, and the arq worker all need the same adapters wired
the same way, so the wiring lives here once - the same split the discovery
repo uses, and for the same reason: outside of tests, this is the only
module that names concrete adapter classes.
"""

from __future__ import annotations

from arq import ArqRedis

from makeover_render.application.ports.job_queue import JobQueue
from makeover_render.application.use_cases.build_scene import BuildScene
from makeover_render.application.use_cases.run_render_job import RunRenderJob
from makeover_render.config.settings import Settings
from makeover_render.infrastructure.blender.animation_renderer import BlenderAnimationRenderer
from makeover_render.infrastructure.blender.runtime import BlenderRuntime
from makeover_render.infrastructure.blender.scene_builder import BlenderSceneBuilder
from makeover_render.infrastructure.encoding.ffmpeg import FfmpegEncoder
from makeover_render.infrastructure.jobs.arq_job_queue import ArqJobQueue


def build_blender_runtime(settings: Settings) -> BlenderRuntime:
    return BlenderRuntime(
        executable=settings.resolve_blender(), timeout_s=int(settings.job_timeout_s)
    )


def build_ffmpeg_encoder(settings: Settings) -> FfmpegEncoder:
    return FfmpegEncoder(executable=settings.resolve_ffmpeg())


def build_scene_use_case(settings: Settings) -> BuildScene:
    return BuildScene(BlenderSceneBuilder(build_blender_runtime(settings)))


def build_run_render_job(settings: Settings) -> RunRenderJob:
    runtime = build_blender_runtime(settings)
    return RunRenderJob(
        build_scene=BuildScene(BlenderSceneBuilder(runtime)),
        animation_renderer=BlenderAnimationRenderer(runtime, build_ffmpeg_encoder(settings)),
    )


def build_job_queue(pool: ArqRedis) -> JobQueue:
    return ArqJobQueue(pool)
