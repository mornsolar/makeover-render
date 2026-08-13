"""Per-template build recipes: how a ``SceneSpec`` becomes wall panels.

This is deliberately separate from ``capabilities/manifest.py``, which lists
template *metadata* for callers (label, description, which material slots
exist). This module is the internal registry of *how to build one* - concrete
panel sizes and placements, in metres, derived from the storefront dimensions.

Kept dependency-free (dataclasses and stdlib only, no ``makeover_contracts``)
so it can be imported both by this service's own venv and by the Blender
build script running inside Blender's bundled interpreter, which has neither
this service's virtualenv nor ``pydantic`` on its path. Material slots are
therefore plain strings here, matching the wire values of
``makeover_contracts.scene.MaterialSlot`` rather than importing that enum.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from makeover_render.domain.errors import UnknownTemplateError
from makeover_render.domain.model.geometry import Dimensions, Vec3

GROUND_THICKNESS_M = 0.1
FACADE_THICKNESS_M = 0.2
TRIM_DEPTH_M = 0.25
GLAZING_THICKNESS_M = 0.05
SIGN_THICKNESS_M = 0.1

FACADE = "facade"
TRIM = "trim"
SIGN = "sign"
GLAZING = "glazing"
AWNING = "awning"
GROUND = "ground"


@dataclass(frozen=True)
class ResolvedPanel:
    """One wall panel, sized and centred in world-space metres."""

    slot: str
    size: Vec3
    center: Vec3

    def __post_init__(self) -> None:
        if any(dimension <= 0.0 for dimension in self.size):
            raise ValueError(f"a {self.slot} panel must have a positive size, got {self.size}")


@dataclass(frozen=True)
class TemplateGeometry:
    """Everything ``build_scene.py`` needs to construct one template.

    ``resolve`` takes the caller's actual dimensions rather than the template
    baking in fixed ones, so one recipe serves every storefront that chooses
    this template regardless of its footprint.
    """

    template_id: str
    required_slots: frozenset[str]
    resolve: Callable[[Dimensions], tuple[ResolvedPanel, ...]]
    signage_anchor: Callable[[Dimensions], Vec3]
    camera_target: Callable[[Dimensions], Vec3]
    camera_distance: Callable[[Dimensions], float]


def _shophouse_narrow(d: Dimensions) -> tuple[ResolvedPanel, ...]:
    trim_height = min(0.5, d.height_m * 0.15)
    glazing_height = d.height_m * 0.45
    glazing_top = GROUND_THICKNESS_M + glazing_height
    awning_depth = min(1.2, d.depth_m * 0.6)
    awning_height = 0.3
    sign_height = 0.6

    return (
        ResolvedPanel(
            GROUND,
            size=(d.width_m, d.depth_m, GROUND_THICKNESS_M),
            center=(d.width_m / 2, d.depth_m / 2, -GROUND_THICKNESS_M / 2),
        ),
        ResolvedPanel(
            FACADE,
            size=(d.width_m, FACADE_THICKNESS_M, d.height_m),
            center=(d.width_m / 2, FACADE_THICKNESS_M / 2, d.height_m / 2),
        ),
        ResolvedPanel(
            TRIM,
            size=(d.width_m, TRIM_DEPTH_M, trim_height),
            center=(d.width_m / 2, TRIM_DEPTH_M / 2, d.height_m - trim_height / 2),
        ),
        ResolvedPanel(
            GLAZING,
            size=(d.width_m * 0.7, GLAZING_THICKNESS_M, glazing_height),
            center=(d.width_m / 2, 0.0, GROUND_THICKNESS_M + glazing_height / 2),
        ),
        ResolvedPanel(
            AWNING,
            size=(d.width_m * 0.85, awning_depth, awning_height),
            center=(d.width_m / 2, awning_depth / 2, glazing_top + awning_height / 2),
        ),
        ResolvedPanel(
            SIGN,
            size=(d.width_m * 0.5, SIGN_THICKNESS_M, sign_height),
            center=(d.width_m / 2, -SIGN_THICKNESS_M / 2, d.height_m - trim_height / 2),
        ),
    )


def _unit_storefront(d: Dimensions) -> tuple[ResolvedPanel, ...]:
    trim_height = min(0.4, d.height_m * 0.12)
    glazing_height = d.height_m - trim_height - GROUND_THICKNESS_M
    sign_height = 0.5

    return (
        ResolvedPanel(
            GROUND,
            size=(d.width_m, d.depth_m, GROUND_THICKNESS_M),
            center=(d.width_m / 2, d.depth_m / 2, -GROUND_THICKNESS_M / 2),
        ),
        ResolvedPanel(
            FACADE,
            size=(d.width_m, FACADE_THICKNESS_M, d.height_m),
            center=(d.width_m / 2, FACADE_THICKNESS_M / 2, d.height_m / 2),
        ),
        ResolvedPanel(
            TRIM,
            size=(d.width_m, TRIM_DEPTH_M, trim_height),
            center=(d.width_m / 2, TRIM_DEPTH_M / 2, d.height_m - trim_height / 2),
        ),
        # A single full-width glazed bay, per the template's own description -
        # the defining difference from the narrower shophouse frontage.
        ResolvedPanel(
            GLAZING,
            size=(d.width_m * 0.9, GLAZING_THICKNESS_M, glazing_height),
            center=(d.width_m / 2, 0.0, GROUND_THICKNESS_M + glazing_height / 2),
        ),
        ResolvedPanel(
            SIGN,
            size=(d.width_m * 0.6, SIGN_THICKNESS_M, sign_height),
            center=(d.width_m / 2, -SIGN_THICKNESS_M / 2, d.height_m - trim_height / 2),
        ),
    )


def _facade_center_signage_anchor(d: Dimensions) -> Vec3:
    return (d.width_m / 2, -SIGN_THICKNESS_M, d.height_m * 0.85)


def _center_of_facade(d: Dimensions) -> Vec3:
    return (d.width_m / 2, 0.0, d.height_m / 2)


def _framing_distance(d: Dimensions) -> float:
    # Wide enough to keep the whole width in frame at a natural focal length,
    # independent of how tall or deep this particular storefront happens to be.
    return max(d.width_m, d.height_m) * 1.8 + 2.0


_REGISTRY: dict[str, TemplateGeometry] = {
    "shophouse-narrow": TemplateGeometry(
        template_id="shophouse-narrow",
        required_slots=frozenset({FACADE, TRIM, SIGN, GLAZING, AWNING, GROUND}),
        resolve=_shophouse_narrow,
        signage_anchor=_facade_center_signage_anchor,
        camera_target=_center_of_facade,
        camera_distance=_framing_distance,
    ),
    "unit-storefront": TemplateGeometry(
        template_id="unit-storefront",
        required_slots=frozenset({FACADE, TRIM, SIGN, GLAZING, GROUND}),
        resolve=_unit_storefront,
        signage_anchor=_facade_center_signage_anchor,
        camera_target=_center_of_facade,
        camera_distance=_framing_distance,
    ),
}


def geometry_for(template_id: str) -> TemplateGeometry:
    """The build recipe for ``template_id``, or a clear error if there is none.

    A template the ``CapabilityManifest`` advertises but this registry cannot
    build would be a worse failure than a loud one here: Repo A would compose
    a ``SceneSpec`` in good faith and only discover the gap when the build
    fails, with a much less specific error.
    """
    geometry = _REGISTRY.get(template_id)
    if geometry is None:
        known = ", ".join(sorted(_REGISTRY))
        raise UnknownTemplateError(f"no build recipe for template {template_id!r}; known: {known}")
    return geometry


def known_template_ids() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))
