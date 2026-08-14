"""Static build: construct the scene, add a fixed camera, export a ``.glb``.

Runs inside Blender. The animated path (Phase 5) shares ``scene_content.py``
with this one and diverges only after that point - a rendered mp4 has no use
for a glTF camera node, and this export has no use for per-frame positions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from makeover_render.domain.model.build_output import GLB_FILENAME
from makeover_render.domain.model.geometry import Dimensions
from makeover_render.infrastructure.blender.scripts.camera import add_camera
from makeover_render.infrastructure.blender.scripts.export import export_glb
from makeover_render.infrastructure.blender.scripts.scene_content import construct_scene


def build(spec: dict[str, Any], out_dir: Path) -> Path:
    dims = Dimensions(**spec["dimensions"])
    geometry = construct_scene(spec, dims)

    add_camera(geometry.camera_target(dims), geometry.camera_distance(dims), spec["camera"])

    out_path = out_dir / GLB_FILENAME
    export_glb(out_path)
    return out_path
