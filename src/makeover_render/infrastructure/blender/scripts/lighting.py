"""Lighting rigs, one per ``LightingPreset``.

Runs inside Blender. The preset chooses light type and direction; the numeric
energy and colour temperature always come from ``LightingSpec`` itself, so a
caller can dial a mood without waiting on this repo to add a new preset.
"""

from __future__ import annotations

import math
from typing import Any

import bpy

from makeover_render.domain.model.color import kelvin_to_rgb

_ELEVATION_AZIMUTH_DEG: dict[str, tuple[float, float]] = {
    "warm_evening": (15.0, 225.0),
    "bright_daylight": (55.0, 135.0),
    "neon_night": (20.0, 0.0),
    "soft_overcast": (70.0, 0.0),
}
_LIGHT_TYPE: dict[str, str] = {
    "warm_evening": "SUN",
    "bright_daylight": "SUN",
    "neon_night": "AREA",
    "soft_overcast": "SUN",
}


def add_lighting(lighting: dict[str, Any]) -> Any:
    preset = lighting["preset"]
    elevation_deg, azimuth_deg = _ELEVATION_AZIMUTH_DEG[preset]
    light_type = _LIGHT_TYPE[preset]

    light_data = bpy.data.lights.new(name="key_light", type=light_type)
    light_data.energy = lighting["key_energy_w"]
    light_data.color = kelvin_to_rgb(lighting["color_temperature_k"])

    light_obj = bpy.data.objects.new(name="key_light", object_data=light_data)
    bpy.context.collection.objects.link(light_obj)
    light_obj.rotation_euler = (
        math.radians(90.0 - elevation_deg),
        0.0,
        math.radians(azimuth_deg),
    )
    return light_obj
