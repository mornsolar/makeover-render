"""Procedural signage text.

Runs inside Blender. glTF has no text primitive, so the sign is built as a
Blender text curve and immediately converted to a mesh - the conversion is
what makes it exportable at all, not a style choice.
"""

from __future__ import annotations

from typing import Any

import bpy

SIGN_TEXT_HEIGHT_M = 0.35
SIGN_EXTRUDE_M = 0.02


def add_signage(anchor: tuple[float, float, float], signage: dict[str, Any]) -> Any:
    bpy.ops.object.text_add(location=anchor)
    text_obj = bpy.context.active_object
    text_obj.name = "signage_text"
    text_obj.data.body = signage["text"]
    text_obj.data.size = SIGN_TEXT_HEIGHT_M
    text_obj.data.extrude = SIGN_EXTRUDE_M
    text_obj.data.align_x = "CENTER"
    text_obj.data.align_y = "CENTER"

    emissive_strength = signage.get("emissive_strength", 0.0)
    if emissive_strength > 0.0:
        material = bpy.data.materials.new(name="signage_emissive")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Emission Strength"].default_value = emissive_strength
        text_obj.data.materials.append(material)

    bpy.ops.object.convert(target="MESH")
    return text_obj
