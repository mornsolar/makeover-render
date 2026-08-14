"""The animated render loop: one PNG per frame.

Runs inside Blender. Positions come from the domain layer's pure
``camera_path.positions_for`` - this file's only job is to hand each position
to the camera, aim it (via ``camera.track_to_target``, the same aiming logic
the static build uses), advance the frame, and render.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import addon_utils
import bpy

from makeover_render.domain.model.build_output import FRAME_FILENAME_PATTERN
from makeover_render.domain.model.camera_path import positions_for
from makeover_render.infrastructure.blender.scripts.camera import new_camera, track_to_target


def frame_count_for(duration_s: float, fps: int) -> int:
    # Mirrors CameraSpec.frame_count in makeover_contracts.scene exactly:
    # round() is banker's rounding, which would turn 2.5s at 25fps into 62
    # frames rather than 63 - an off-by-one this file must not reintroduce.
    return max(1, math.floor(duration_s * fps + 0.5))


def _configure_render(render_spec: dict[str, Any]) -> None:
    scene = bpy.context.scene
    engine = render_spec["engine"]
    if engine == "CYCLES":
        # --factory-startup leaves Cycles disabled; the enum must be enabled
        # before scene.render.engine will accept "CYCLES".
        addon_utils.enable("cycles")
    scene.render.engine = engine
    scene.render.resolution_x = render_spec["resolution_x"]
    scene.render.resolution_y = render_spec["resolution_y"]
    scene.render.film_transparent = render_spec["film_transparent"]
    scene.render.image_settings.file_format = "PNG"
    if engine == "CYCLES":
        scene.cycles.samples = render_spec["samples"]
    else:
        scene.eevee.taa_render_samples = render_spec["samples"]


def render_frames(
    spec: dict[str, Any],
    target: tuple[float, float, float],
    distance: float,
    out_dir: Path,
) -> tuple[Path, ...]:
    _configure_render(spec["render"])
    camera_obj = new_camera(spec["camera"])

    frame_count = frame_count_for(spec["camera"]["duration_s"], spec["camera"]["fps"])
    positions = positions_for(spec["camera"]["move"], target, distance, frame_count)

    scene = bpy.context.scene
    frame_paths: list[Path] = []
    for index, position in enumerate(positions):
        camera_obj.location = position
        track_to_target(camera_obj, target)
        scene.frame_set(index)
        frame_path = out_dir / (FRAME_FILENAME_PATTERN % index)
        scene.render.filepath = str(frame_path)
        bpy.ops.render.render(write_still=True)
        frame_paths.append(frame_path)
    return tuple(frame_paths)
