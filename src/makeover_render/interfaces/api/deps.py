"""Composition root for the render service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from makeover_render.composition import build_blender_runtime
from makeover_render.config.settings import Settings, get_settings
from makeover_render.infrastructure.blender.runtime import BlenderRuntime

SettingsDep = Annotated[Settings, Depends(get_settings)]


def provide_blender_runtime(settings: SettingsDep) -> BlenderRuntime:
    return build_blender_runtime(settings)


BlenderRuntimeDep = Annotated[BlenderRuntime, Depends(provide_blender_runtime)]
