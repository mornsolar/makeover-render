"""The ``BuildScene`` use case, against a fake builder."""

from __future__ import annotations

import pytest
from makeover_contracts.scene import MaterialAssignment, MaterialSlot

from makeover_render.application.use_cases.build_scene import BuildScene
from makeover_render.domain.errors import BuildFailedError, UnknownTemplateError
from tests.fakes.scene_builder import FakeSceneBuilder
from tests.fakes.specs import UNIT_STOREFRONT_MATERIALS, make_spec


def test_builds_a_spec_that_covers_every_required_slot(tmp_path):
    builder = FakeSceneBuilder()

    artifact = BuildScene(builder).execute(make_spec(), tmp_path)

    assert artifact.glb_path == builder.artifact.glb_path
    assert len(builder.builds) == 1


def test_creates_the_output_directory(tmp_path):
    out_dir = tmp_path / "nested" / "out"

    BuildScene(FakeSceneBuilder()).execute(make_spec(), out_dir)

    assert out_dir.is_dir()


def test_rejects_an_unknown_template(tmp_path):
    with pytest.raises(UnknownTemplateError):
        BuildScene(FakeSceneBuilder()).execute(make_spec(template_id="does-not-exist"), tmp_path)


def test_fails_before_launching_blender_when_a_required_slot_has_no_material(tmp_path):
    # A multi-second Blender subprocess is expensive to spend on a spec that
    # is already known to be incomplete.
    incomplete = tuple(a for a in UNIT_STOREFRONT_MATERIALS if a.slot != MaterialSlot.GROUND)
    builder = FakeSceneBuilder()

    with pytest.raises(BuildFailedError, match="ground"):
        BuildScene(builder).execute(make_spec(materials=incomplete), tmp_path)

    assert builder.builds == []


def test_names_every_missing_slot_at_once(tmp_path):
    sparse = (UNIT_STOREFRONT_MATERIALS[0],)

    with pytest.raises(BuildFailedError) as excinfo:
        BuildScene(FakeSceneBuilder()).execute(make_spec(materials=sparse), tmp_path)

    assert "trim" in str(excinfo.value)
    assert "sign" in str(excinfo.value)


def test_extra_materials_beyond_what_the_template_needs_are_harmless(tmp_path):
    # A spec assigning a slot this template does not build (e.g. an awning on
    # a unit-storefront) is not this use case's concern - the builder decides
    # what to do with an unused assignment.
    extra = (
        *UNIT_STOREFRONT_MATERIALS,
        MaterialAssignment(slot=MaterialSlot.AWNING, family="steel", base_color="#333333"),
    )
    builder = FakeSceneBuilder()

    BuildScene(builder).execute(make_spec(materials=extra), tmp_path)

    assert len(builder.builds) == 1
