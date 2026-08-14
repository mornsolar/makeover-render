"""An ``AnimationRenderer`` double that never launches Blender or ffmpeg."""

from __future__ import annotations

from pathlib import Path

from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.animation_renderer import AnimationArtifact


class FakeAnimationRenderer:
    """Records every spec it was asked to render and returns a scripted result."""

    def __init__(self, artifact: AnimationArtifact) -> None:
        self.artifact = artifact
        self.renders: list[SceneSpec] = []

    def render(self, spec: SceneSpec, out_dir: Path) -> AnimationArtifact:
        self.renders.append(spec)
        return self.artifact
