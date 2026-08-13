"""Drives Blender to build one ``.glb``, on the ordinary-Python side of the
subprocess boundary."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.scene_builder import BuildArtifact
from makeover_render.domain.errors import BuildFailedError
from makeover_render.domain.model.build_output import GLB_FILENAME
from makeover_render.infrastructure.blender.runtime import BlenderInvocationError, BlenderRuntime

_ENTRYPOINT = Path(__file__).parent / "scripts" / "entrypoint.py"


class BlenderSceneBuilder:
    """The ``SceneBuilder`` port, implemented by shelling out to Blender."""

    def __init__(self, runtime: BlenderRuntime) -> None:
        self._runtime = runtime

    def build(self, spec: SceneSpec, out_dir: Path) -> BuildArtifact:
        with tempfile.TemporaryDirectory(prefix="makeover-spec-") as tmp:
            spec_path = Path(tmp) / "spec.json"
            spec_path.write_text(json.dumps(spec.model_dump(mode="json")), encoding="utf-8")
            try:
                self._runtime.run_script(
                    _ENTRYPOINT, ["--spec", str(spec_path), "--out", str(out_dir)]
                )
            except BlenderInvocationError as exc:
                raise BuildFailedError(str(exc)) from exc

        glb_path = out_dir / GLB_FILENAME
        if not glb_path.exists():
            # Blender exited 0 but did not leave a file where entrypoint.py
            # says it always writes one - a bug worth its own message rather
            # than surfacing as a generic "file not found" from the caller.
            raise BuildFailedError(f"Blender exited without producing {glb_path}")
        return BuildArtifact(glb_path=glb_path, size_bytes=glb_path.stat().st_size)
