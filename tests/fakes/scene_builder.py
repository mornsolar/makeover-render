"""A ``SceneBuilder`` double that never launches Blender."""

from __future__ import annotations

from pathlib import Path

from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.scene_builder import BuildArtifact


class FakeSceneBuilder:
    """Records every spec it was asked to build and returns a scripted result."""

    def __init__(self, glb_path: Path = Path("scene.glb"), size_bytes: int = 1_024) -> None:
        self.artifact = BuildArtifact(glb_path=glb_path, size_bytes=size_bytes)
        self.builds: list[SceneSpec] = []

    def build(self, spec: SceneSpec, out_dir: Path) -> BuildArtifact:
        self.builds.append(spec)
        return self.artifact
