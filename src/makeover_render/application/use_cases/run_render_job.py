"""Produces the full ``ArtifactBundle`` a ``RenderJob`` needs.

Composes the two build steps - the static ``.glb`` (``BuildScene``, Phase 4)
and the animated render (``AnimationRenderer``, Phase 5) - and turns their
output files into hashed ``ArtifactRef``s. This is what the arq worker task
calls; the HTTP job endpoints never touch it directly, since the whole point
of the job API is that a render happens off the request thread.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from makeover_contracts.jobs import ArtifactBundle, ArtifactKind, ArtifactRef
from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.animation_renderer import AnimationRenderer
from makeover_render.application.use_cases.build_scene import BuildScene


class RunRenderJob:
    def __init__(self, build_scene: BuildScene, animation_renderer: AnimationRenderer) -> None:
        self._build_scene = build_scene
        self._animation_renderer = animation_renderer

    def execute(self, spec: SceneSpec, out_dir: Path) -> ArtifactBundle:
        glb = self._build_scene.execute(spec, out_dir)
        animation = self._animation_renderer.render(spec, out_dir)

        return ArtifactBundle(
            gltf=_hashed_ref(glb.glb_path, ArtifactKind.GLTF, "model/gltf-binary"),
            video=_hashed_ref(animation.video_path, ArtifactKind.VIDEO, "video/mp4"),
            thumbnail=_hashed_ref(animation.thumbnail_path, ArtifactKind.THUMBNAIL, "image/png"),
            stills=tuple(
                _hashed_ref(path, ArtifactKind.STILL, "image/png") for path in animation.still_paths
            ),
        )


def _hashed_ref(path: Path, kind: ArtifactKind, media_type: str) -> ArtifactRef:
    # A caller across the process boundary can only trust what it can verify -
    # the URI alone could be swapped out under it, especially once this points
    # at a presigned object-storage link rather than a local path.
    data = path.read_bytes()
    return ArtifactRef(
        kind=kind,
        uri=str(path),
        media_type=media_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
