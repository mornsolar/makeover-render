"""Builders for ``SceneSpec`` fixtures."""

from __future__ import annotations

from makeover_contracts.scene import (
    CameraMove,
    CameraSpec,
    LightingPreset,
    LightingSpec,
    MaterialAssignment,
    MaterialSlot,
    SceneSpec,
    SignageSpec,
    StorefrontDimensions,
)

DIMENSIONS = StorefrontDimensions(width_m=6.0, height_m=3.2, depth_m=4.0)

UNIT_STOREFRONT_MATERIALS = (
    MaterialAssignment(slot=MaterialSlot.FACADE, family="render", base_color="#E8DCC4"),
    MaterialAssignment(slot=MaterialSlot.TRIM, family="timber", base_color="#1B4D3E"),
    MaterialAssignment(slot=MaterialSlot.SIGN, family="brass", base_color="#C87941"),
    MaterialAssignment(slot=MaterialSlot.GLAZING, family="glass", base_color="#CFE8E0"),
    MaterialAssignment(slot=MaterialSlot.GROUND, family="terrazzo", base_color="#D9D2C4"),
)


def make_spec(
    *,
    template_id: str = "unit-storefront",
    dimensions: StorefrontDimensions = DIMENSIONS,
    materials: tuple[MaterialAssignment, ...] = UNIT_STOREFRONT_MATERIALS,
    signage_text: str = "Kedai Kopi Ali",
    seed: int = 7,
) -> SceneSpec:
    return SceneSpec(
        template_id=template_id,
        seed=seed,
        dimensions=dimensions,
        palette=("#1B4D3E", "#E8DCC4", "#C87941"),
        materials=materials,
        signage=SignageSpec(text=signage_text, emissive_strength=2.0),
        lighting=LightingSpec(preset=LightingPreset.WARM_EVENING),
        camera=CameraSpec(move=CameraMove.ORBIT),
    )
