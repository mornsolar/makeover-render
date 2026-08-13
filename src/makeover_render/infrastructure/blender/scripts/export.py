"""GLTF export, with the colour-management fix Phase 0 found.

Runs inside Blender. ``--factory-startup`` leaves the view transform at
whatever the factory default is; Phase 0 found AgX is correct for pixel
renders but wrong for GLTF export, which wants ``Standard`` so exported base
colours match the sRGB hex the caller specified rather than AgX's tone map.
"""

from __future__ import annotations

from pathlib import Path

import bpy

GLTF_VIEW_TRANSFORM = "Standard"


def export_glb(out_path: Path) -> None:
    bpy.context.scene.view_settings.view_transform = GLTF_VIEW_TRANSFORM
    bpy.ops.export_scene.gltf(filepath=str(out_path), export_format="GLB")
