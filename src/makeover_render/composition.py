"""Object graph construction.

The HTTP API and the CLI need the same adapters wired the same way, so the
wiring lives here once - the same split the discovery repo uses, and for the
same reason: outside of tests, this is the only module that names concrete
adapter classes.
"""

from __future__ import annotations

from makeover_render.application.use_cases.build_scene import BuildScene
from makeover_render.config.settings import Settings
from makeover_render.infrastructure.blender.runtime import BlenderRuntime
from makeover_render.infrastructure.blender.scene_builder import BlenderSceneBuilder


def build_blender_runtime(settings: Settings) -> BlenderRuntime:
    return BlenderRuntime(executable=settings.resolve_blender())


def build_scene_use_case(settings: Settings) -> BuildScene:
    return BuildScene(BlenderSceneBuilder(build_blender_runtime(settings)))
