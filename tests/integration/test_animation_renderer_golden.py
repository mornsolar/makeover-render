"""The golden animation test: a real Blender render, encoded by real ffmpeg.

Marked ``blender`` so the default CI job can skip it - mirrors
``test_build_scene_golden.py``, but for the Phase 5 pixel-render path this
service's fakes and the arq adapter's own tests cannot exercise: the actual
Blender frame loop and the actual ffmpeg encode.
"""

from __future__ import annotations

import pytest
from makeover_contracts.scene import CameraMove, CameraSpec, RenderEngine, RenderSpec

from makeover_render.composition import build_blender_runtime, build_ffmpeg_encoder
from makeover_render.config.settings import Settings
from makeover_render.infrastructure.blender.animation_renderer import BlenderAnimationRenderer
from tests.fakes.specs import make_spec

pytestmark = pytest.mark.blender

_TINY_RENDER = RenderSpec(engine=RenderEngine.EEVEE, samples=4, resolution_x=64, resolution_y=64)
_TINY_CAMERA = CameraSpec(move=CameraMove.ORBIT, duration_s=1.0, fps=12, focal_length_mm=35.0)


@pytest.fixture
def animation_renderer() -> BlenderAnimationRenderer:
    settings = Settings()
    try:
        runtime = build_blender_runtime(settings)
        encoder = build_ffmpeg_encoder(settings)
    except FileNotFoundError as exc:
        pytest.skip(str(exc))
    return BlenderAnimationRenderer(runtime, encoder)


def test_renders_a_video_thumbnail_and_stills(animation_renderer, tmp_path):
    spec = make_spec(render=_TINY_RENDER, camera=_TINY_CAMERA)

    artifact = animation_renderer.render(spec, tmp_path)

    assert artifact.video_path.exists()
    assert artifact.video_path.stat().st_size > 0
    assert artifact.thumbnail_path.exists()
    assert len(artifact.still_paths) >= 1
    assert all(path.exists() for path in artifact.still_paths)


def test_frame_count_matches_duration_and_fps(animation_renderer, tmp_path):
    spec = make_spec(render=_TINY_RENDER, camera=_TINY_CAMERA)

    animation_renderer.render(spec, tmp_path)

    frames_dir = tmp_path / "frames"
    assert len(list(frames_dir.glob("frame_*.png"))) == spec.camera.frame_count
