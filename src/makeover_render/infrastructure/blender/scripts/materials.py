"""Turns ``MaterialAssignment`` entries into Principled BSDF materials.

Runs inside Blender. One material per distinct ``family`` name, shared across
every panel assigned that family - a "timber" facade and a "timber" trim get
the same material data-block, which is both cheaper and more physically
honest than two near-identical materials.
"""

from __future__ import annotations

from typing import Any

import bpy

from makeover_render.domain.model.color import hex_to_linear_rgb


def build_materials(assignments: list[dict[str, Any]]) -> dict[str, Any]:
    """Create one material per family, keyed by family name."""
    by_family: dict[str, Any] = {}
    for assignment in assignments:
        family = assignment["family"]
        if family in by_family:
            continue
        material = bpy.data.materials.new(name=family)
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        red, green, blue = hex_to_linear_rgb(assignment["base_color"])
        bsdf.inputs["Base Color"].default_value = (red, green, blue, 1.0)
        bsdf.inputs["Roughness"].default_value = assignment["roughness"]
        bsdf.inputs["Metallic"].default_value = assignment["metallic"]
        by_family[family] = material
    return by_family


def apply_materials(
    objects_by_slot: dict[str, Any],
    assignments: list[dict[str, Any]],
    materials_by_family: dict[str, Any],
) -> None:
    for assignment in assignments:
        obj = objects_by_slot.get(assignment["slot"])
        if obj is None:
            continue  # a spec may assign a slot this template does not build
        material = materials_by_family[assignment["family"]]
        obj.data.materials.clear()
        obj.data.materials.append(material)
