"""Camera placement, static and animated.

Runs inside Blender. Both this file's ``add_camera`` (Phase 4, one fixed
frame) and ``render_frames.py`` (Phase 5, one camera object repositioned per
frame) point the camera the same way - ``track_to_target`` is the one place
that "aim at the target" logic lives, so a static build and an animated
render can never disagree about which way the camera is facing.
"""

from __future__ import annotations

from typing import Any

import bpy
import mathutils


def track_to_target(camera_obj: Any, target: tuple[float, float, float]) -> None:
    location = camera_obj.location
    direction = mathutils.Vector(target) - mathutils.Vector(location)
    camera_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def new_camera(camera_spec: dict[str, Any]) -> Any:
    camera_data = bpy.data.cameras.new(name="makeover_camera")
    camera_data.lens = camera_spec["focal_length_mm"]

    camera_obj = bpy.data.objects.new(name="makeover_camera", object_data=camera_data)
    bpy.context.collection.objects.link(camera_obj)
    bpy.context.scene.camera = camera_obj
    return camera_obj


def add_camera(
    target: tuple[float, float, float],
    distance: float,
    camera_spec: dict[str, Any],
) -> Any:
    camera_obj = new_camera(camera_spec)
    camera_obj.location = (target[0], target[1] - distance, target[2])
    track_to_target(camera_obj, target)
    return camera_obj
