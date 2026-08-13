"""Composition root for the render service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from makeover_render.config.settings import Settings, get_settings
from makeover_render.infrastructure.blender.runtime import BlenderRuntime

SettingsDep = Annotated[Settings, Depends(get_settings)]


def provide_blender_runtime(settings: SettingsDep) -> BlenderRuntime:
    return BlenderRuntime(executable=settings.resolve_blender())


BlenderRuntimeDep = Annotated[BlenderRuntime, Depends(provide_blender_runtime)]
