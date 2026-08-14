"""``RunRenderJob``, against fake build and animation adapters."""

from __future__ import annotations

import hashlib

from makeover_contracts.jobs import ArtifactKind

from makeover_render.application.ports.animation_renderer import AnimationArtifact
from makeover_render.application.use_cases.build_scene import BuildScene
from makeover_render.application.use_cases.run_render_job import RunRenderJob
from tests.fakes.animation_renderer import FakeAnimationRenderer
from tests.fakes.scene_builder import FakeSceneBuilder
from tests.fakes.specs import make_spec


def _write(path, content: bytes):
    path.write_bytes(content)
    return path


def _run_render_job(tmp_path):
    glb_path = _write(tmp_path / "scene.glb", b"glb-bytes")
    video_path = _write(tmp_path / "animation.mp4", b"video-bytes")
    thumbnail_path = _write(tmp_path / "thumbnail.png", b"thumb-bytes")
    still_path = _write(tmp_path / "still_0.png", b"still-bytes")

    scene_builder = FakeSceneBuilder(glb_path=glb_path, size_bytes=len(b"glb-bytes"))
    animation_renderer = FakeAnimationRenderer(
        AnimationArtifact(
            video_path=video_path, thumbnail_path=thumbnail_path, still_paths=(still_path,)
        )
    )
    use_case = RunRenderJob(
        build_scene=BuildScene(scene_builder), animation_renderer=animation_renderer
    )
    bundle = use_case.execute(make_spec(), tmp_path)
    return (
        bundle,
        scene_builder,
        animation_renderer,
        {
            "glb": glb_path,
            "video": video_path,
            "thumbnail": thumbnail_path,
            "still": still_path,
        },
    )


class TestRunRenderJob:
    def test_calls_both_adapters_with_the_same_spec(self, tmp_path):
        _, scene_builder, animation_renderer, _ = _run_render_job(tmp_path)
        assert len(scene_builder.builds) == 1
        assert len(animation_renderer.renders) == 1
        assert scene_builder.builds[0] == animation_renderer.renders[0]

    def test_bundle_carries_the_right_artifact_kinds(self, tmp_path):
        bundle, *_ = _run_render_job(tmp_path)
        assert bundle.gltf.kind is ArtifactKind.GLTF
        assert bundle.video.kind is ArtifactKind.VIDEO
        assert bundle.thumbnail.kind is ArtifactKind.THUMBNAIL
        assert len(bundle.stills) == 1
        assert bundle.stills[0].kind is ArtifactKind.STILL

    def test_hashes_and_sizes_match_the_actual_file_bytes(self, tmp_path):
        bundle, *_, paths = _run_render_job(tmp_path)
        for ref, path in (
            (bundle.gltf, paths["glb"]),
            (bundle.video, paths["video"]),
            (bundle.thumbnail, paths["thumbnail"]),
            (bundle.stills[0], paths["still"]),
        ):
            data = path.read_bytes()
            assert ref.size_bytes == len(data)
            assert ref.sha256 == hashlib.sha256(data).hexdigest()

    def test_uri_points_at_the_produced_file(self, tmp_path):
        bundle, *_, paths = _run_render_job(tmp_path)
        assert bundle.gltf.uri == str(paths["glb"])
