"""Everything both Blender entrypoints need before they diverge: the panels,
materials, signage, and lighting. Only the camera and the output step differ
between a static ``.glb`` export (Phase 4) and an animated render (Phase 5),
so this is the one place that construction logic lives.
"""

from __future__ import annotations

from typing import Any

import bpy

from makeover_render.domain.model.geometry import Dimensions
from makeover_render.domain.model.template_geometry import TemplateGeometry, geometry_for
from makeover_render.infrastructure.blender.scripts.lighting import add_lighting
from makeover_render.infrastructure.blender.scripts.materials import (
    apply_materials,
    build_materials,
)
from makeover_render.infrastructure.blender.scripts.signage import add_signage


def _clear_default_scene() -> None:
    # ``--factory-startup`` still ships the default cube, camera, and light;
    # every one of them would otherwise show up as an unexplained extra node
    # or contaminate a render with light no ``LightingSpec`` asked for.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def _build_panels(dims: Dimensions, template_id: str) -> dict[str, Any]:
    geometry = geometry_for(template_id)
    objects_by_slot: dict[str, Any] = {}
    for panel in geometry.resolve(dims):
        bpy.ops.mesh.primitive_cube_add(size=1, location=panel.center)
        obj = bpy.context.active_object
        obj.name = f"panel.{panel.slot}"
        obj.scale = panel.size
        objects_by_slot[panel.slot] = obj
    return objects_by_slot


def _apply_mesh_transforms() -> None:
    # Baking scale and location into vertex data - rather than leaving them as
    # node transforms - is what lets a structural test read true world-space
    # sizes straight off each mesh's own glTF accessor bounds.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.select_set(True)
    if bpy.context.selected_objects:
        bpy.context.view_layer.objects.active = bpy.context.selected_objects[0]
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def construct_scene(spec: dict[str, Any], dims: Dimensions) -> TemplateGeometry:
    """Build every panel, material, signage mesh, and light. Returns the
    template's geometry recipe so the caller can frame its own camera."""
    _clear_default_scene()
    geometry = geometry_for(spec["template_id"])

    objects_by_slot = _build_panels(dims, spec["template_id"])
    materials_by_family = build_materials(spec["materials"])
    apply_materials(objects_by_slot, spec["materials"], materials_by_family)

    add_signage(geometry.signage_anchor(dims), spec["signage"])
    _apply_mesh_transforms()

    add_lighting(spec["lighting"])
    return geometry
