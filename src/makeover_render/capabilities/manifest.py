"""The renderer's self-description.

Repo A reads this to learn what vocabulary the LLM may use and to validate a
SceneSpec before submitting it. It is the reason Repo B never needs to know what
a business is.
"""

from __future__ import annotations

from makeover_contracts.capability import (
    CapabilityManifest,
    RenderLimits,
    TemplateDescriptor,
)
from makeover_contracts.scene import (
    CameraMove,
    LightingPreset,
    MaterialSlot,
    RenderEngine,
)

MATERIAL_FAMILIES = ("timber", "brass", "render", "terrazzo", "steel", "glass")

TEMPLATES = (
    TemplateDescriptor(
        id="shophouse-narrow",
        label="Narrow shophouse",
        description="Two-storey shophouse frontage with awning and hanging sign.",
        material_slots=(
            MaterialSlot.FACADE,
            MaterialSlot.TRIM,
            MaterialSlot.SIGN,
            MaterialSlot.GLAZING,
            MaterialSlot.AWNING,
            MaterialSlot.GROUND,
        ),
    ),
    TemplateDescriptor(
        id="unit-storefront",
        label="Single-unit storefront",
        description="Flat modern shopfront with a full-width glazed bay.",
        material_slots=(
            MaterialSlot.FACADE,
            MaterialSlot.TRIM,
            MaterialSlot.SIGN,
            MaterialSlot.GLAZING,
            MaterialSlot.GROUND,
        ),
    ),
)

# Ceilings sized so one job stays within a few minutes of CPU rendering. Raised
# in Phase 7 once GPU workers exist.
LIMITS = RenderLimits(
    max_duration_s=10.0,
    max_fps=30,
    max_frame_count=300,
    max_resolution_x=1920,
    max_resolution_y=1080,
    max_samples=256,
)


def build_manifest(engine_version: str) -> CapabilityManifest:
    """Assemble the manifest for a concrete Blender build."""
    return CapabilityManifest(
        renderer_name="makeover-render",
        engine_version=engine_version,
        templates=TEMPLATES,
        material_families=MATERIAL_FAMILIES,
        lighting_presets=tuple(LightingPreset),
        camera_moves=tuple(CameraMove),
        engines=(RenderEngine.EEVEE, RenderEngine.CYCLES),
        limits=LIMITS,
    )
