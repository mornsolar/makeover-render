"""The per-template build recipe registry."""

from __future__ import annotations

import pytest

from makeover_render.domain.errors import UnknownTemplateError
from makeover_render.domain.model.geometry import Dimensions
from makeover_render.domain.model.template_geometry import (
    AWNING,
    ResolvedPanel,
    geometry_for,
    known_template_ids,
)

DIMENSIONS = Dimensions(width_m=6.0, height_m=3.2, depth_m=4.0)


@pytest.mark.parametrize("template_id", known_template_ids())
def test_every_registered_template_resolves_a_panel_for_each_required_slot(template_id):
    geometry = geometry_for(template_id)

    resolved_slots = {panel.slot for panel in geometry.resolve(DIMENSIONS)}

    assert resolved_slots == geometry.required_slots


@pytest.mark.parametrize("template_id", known_template_ids())
def test_every_panel_has_a_positive_size(template_id):
    for panel in geometry_for(template_id).resolve(DIMENSIONS):
        assert all(component > 0.0 for component in panel.size)


def test_only_the_narrow_shophouse_has_an_awning():
    assert AWNING in geometry_for("shophouse-narrow").required_slots
    assert AWNING not in geometry_for("unit-storefront").required_slots


def test_rejects_an_unknown_template():
    with pytest.raises(UnknownTemplateError, match="unobtainium-template"):
        geometry_for("unobtainium-template")


def test_the_unknown_template_error_names_what_is_available():
    with pytest.raises(UnknownTemplateError, match="unit-storefront"):
        geometry_for("does-not-exist")


def test_panel_geometry_scales_with_the_storefront_width():
    narrow = Dimensions(width_m=4.0, height_m=3.0, depth_m=3.0)
    wide = Dimensions(width_m=12.0, height_m=3.0, depth_m=3.0)

    narrow_facade = _facade_of("unit-storefront", narrow)
    wide_facade = _facade_of("unit-storefront", wide)

    assert wide_facade.size[0] > narrow_facade.size[0]


def test_camera_framing_backs_off_for_a_taller_storefront():
    short = Dimensions(width_m=6.0, height_m=3.0, depth_m=4.0)
    tall = Dimensions(width_m=6.0, height_m=10.0, depth_m=4.0)
    geometry = geometry_for("unit-storefront")

    assert geometry.camera_distance(tall) > geometry.camera_distance(short)


def test_a_resolved_panel_rejects_a_non_positive_size():
    with pytest.raises(ValueError, match="positive size"):
        ResolvedPanel(slot="facade", size=(1.0, 1.0, 0.0), center=(0.0, 0.0, 0.0))


def _facade_of(template_id, dimensions):
    panels = geometry_for(template_id).resolve(dimensions)
    return next(panel for panel in panels if panel.slot == "facade")
