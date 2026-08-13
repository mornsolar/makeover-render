"""The golden GLTF test: a real Blender build, checked structurally.

Marked ``blender`` so the default CI job can skip it - the rest of the build
pipeline is exercised through ``FakeSceneBuilder`` in the unit suite, so this
is specifically what proves the real subprocess, the real scripts, and the
real exporter agree with what the domain layer promised.
"""

from __future__ import annotations

import pytest
from makeover_contracts.scene import MaterialAssignment, MaterialSlot

from makeover_render.application.use_cases.build_scene import BuildScene
from makeover_render.composition import build_blender_runtime
from makeover_render.config.settings import Settings
from makeover_render.infrastructure.blender.scene_builder import BlenderSceneBuilder
from makeover_render.infrastructure.gltf.reader import read_glb
from tests.fakes.specs import DIMENSIONS, make_spec

pytestmark = pytest.mark.blender


@pytest.fixture
def build_scene() -> BuildScene:
    try:
        runtime = build_blender_runtime(Settings())
    except FileNotFoundError as exc:
        pytest.skip(str(exc))
    return BuildScene(BlenderSceneBuilder(runtime))


def test_produces_a_node_for_every_panel_and_the_signage(build_scene, tmp_path):
    artifact = build_scene.execute(make_spec(), tmp_path)

    doc = read_glb(artifact.glb_path)

    for slot in ("facade", "trim", "sign", "glazing", "ground"):
        assert f"panel.{slot}" in doc.node_names
    assert "signage_text" in doc.node_names


def test_produces_a_material_for_every_assigned_family(build_scene, tmp_path):
    artifact = build_scene.execute(make_spec(), tmp_path)

    doc = read_glb(artifact.glb_path)

    for family in ("render", "timber", "brass", "glass", "terrazzo"):
        assert family in doc.material_names


def test_the_bounding_box_reflects_the_storefront_width(build_scene, tmp_path):
    spec = make_spec()
    artifact = build_scene.execute(spec, tmp_path)

    minimum, maximum = read_glb(artifact.glb_path).accessor_bounds
    # Blender's exporter reorders axes to glTF's Y-up convention, so the
    # width - unambiguous regardless of which axis is "up" - is the one
    # dimension safe to assert on without decoding that remapping here.
    width_axis_size = max(maximum[axis] - minimum[axis] for axis in range(3))

    assert width_axis_size == pytest.approx(spec.dimensions.width_m, abs=0.05)


def test_the_awning_only_appears_on_the_shophouse_template(build_scene, tmp_path):
    materials = (
        MaterialAssignment(slot=MaterialSlot.FACADE, family="render", base_color="#E8DCC4"),
        MaterialAssignment(slot=MaterialSlot.TRIM, family="timber", base_color="#1B4D3E"),
        MaterialAssignment(slot=MaterialSlot.SIGN, family="brass", base_color="#C87941"),
        MaterialAssignment(slot=MaterialSlot.GLAZING, family="glass", base_color="#CFE8E0"),
        MaterialAssignment(slot=MaterialSlot.AWNING, family="steel", base_color="#333333"),
        MaterialAssignment(slot=MaterialSlot.GROUND, family="terrazzo", base_color="#D9D2C4"),
    )
    spec = make_spec(template_id="shophouse-narrow", dimensions=DIMENSIONS, materials=materials)

    artifact = build_scene.execute(spec, tmp_path)

    assert "panel.awning" in read_glb(artifact.glb_path).node_names


def test_is_deterministic_across_two_runs_with_the_same_spec(build_scene, tmp_path):
    spec = make_spec()

    first = build_scene.execute(spec, tmp_path / "a")
    second = build_scene.execute(spec, tmp_path / "b")

    first_doc = read_glb(first.glb_path)
    second_doc = read_glb(second.glb_path)
    assert first_doc.node_names == second_doc.node_names
    assert first_doc.accessor_bounds == second_doc.accessor_bounds
