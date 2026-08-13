from __future__ import annotations

from makeover_contracts.capability import validate_against_manifest
from makeover_contracts.scene import (
    CameraMove,
    CameraSpec,
    LightingPreset,
    LightingSpec,
    MaterialAssignment,
    MaterialSlot,
    RenderEngine,
    RenderSpec,
    SceneSpec,
    SignageSpec,
    StorefrontDimensions,
)
from makeover_contracts.version import CONTRACT_VERSION

from makeover_render.capabilities.manifest import MATERIAL_FAMILIES, build_manifest

MANIFEST = build_manifest(engine_version="5.2.0")


def make_scene(**overrides) -> SceneSpec:
    defaults = {
        "template_id": "shophouse-narrow",
        "seed": 7,
        "dimensions": StorefrontDimensions(width_m=8.0, height_m=4.5, depth_m=6.0),
        "palette": ("#1B4D3E",),
        "materials": (
            MaterialAssignment(slot=MaterialSlot.FACADE, family="timber", base_color="#1B4D3E"),
        ),
        "signage": SignageSpec(text="KEDAI KOPI"),
        "lighting": LightingSpec(preset=LightingPreset.WARM_EVENING),
        "camera": CameraSpec(move=CameraMove.ORBIT, duration_s=5.0, fps=24),
    }
    return SceneSpec(**{**defaults, **overrides})


class TestBuildManifest:
    def test_reports_the_engine_version_it_was_built_for(self):
        assert MANIFEST.engine_version == "5.2.0"

    def test_reports_the_contract_version_it_speaks(self):
        assert MANIFEST.contract_version == CONTRACT_VERSION

    def test_advertises_both_render_engines(self):
        assert set(MANIFEST.engines) == {RenderEngine.EEVEE, RenderEngine.CYCLES}

    def test_every_template_declares_at_least_a_facade_and_a_sign(self):
        for template in MANIFEST.templates:
            assert MaterialSlot.FACADE in template.material_slots
            assert MaterialSlot.SIGN in template.material_slots

    def test_template_ids_are_unique(self):
        ids = [template.id for template in MANIFEST.templates]
        assert len(ids) == len(set(ids))


class TestManifestAcceptsWhatWeAdvertise:
    def test_a_scene_built_from_advertised_values_validates(self):
        # Guards the contract both ways: anything we say we support must
        # actually pass the shared validator.
        assert validate_against_manifest(make_scene(), MANIFEST) == ()

    def test_every_advertised_material_family_is_accepted(self):
        for family in MATERIAL_FAMILIES:
            scene = make_scene(
                materials=(
                    MaterialAssignment(
                        slot=MaterialSlot.FACADE, family=family, base_color="#1B4D3E"
                    ),
                )
            )
            assert validate_against_manifest(scene, MANIFEST) == ()

    def test_a_scene_at_the_advertised_limits_validates(self):
        scene = make_scene(
            camera=CameraSpec(move=CameraMove.ORBIT, duration_s=10.0, fps=30),
            render=RenderSpec(resolution_x=1920, resolution_y=1080, samples=256),
        )
        assert validate_against_manifest(scene, MANIFEST) == ()

    def test_a_scene_beyond_the_limits_is_rejected(self):
        scene = make_scene(render=RenderSpec(samples=4096))
        assert validate_against_manifest(scene, MANIFEST) != ()
