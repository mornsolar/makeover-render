"""Static camera placement for the ``.glb`` export.

Runs inside Blender. Animated camera moves (``CameraSpec.move``) are Phase 5's
job, once frames are actually rendered; a GLTF-only build just needs one
camera framed on the storefront so the export has something sensible in it.
"""

from __future__ import annotations

from typing import Any

import bpy
import mathutils


def add_camera(
    target: tuple[float, float, float],
    distance: float,
    camera_spec: dict[str, Any],
) -> Any:
    location = (target[0], target[1] - distance, target[2])

    camera_data = bpy.data.cameras.new(name="makeover_camera")
    camera_data.lens = camera_spec["focal_length_mm"]

    camera_obj = bpy.data.objects.new(name="makeover_camera", object_data=camera_data)
    bpy.context.collection.objects.link(camera_obj)
    camera_obj.location = location

    direction = mathutils.Vector(target) - mathutils.Vector(location)
    camera_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    bpy.context.scene.camera = camera_obj
    return camera_obj
