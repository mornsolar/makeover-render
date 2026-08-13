"""Scene-building port.

The one seam between ordinary Python and Blender. Everything above this port
is unit-testable without Blender installed; everything below it is exercised
by the slow, real-Blender integration suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from makeover_contracts.scene import SceneSpec


@dataclass(frozen=True)
class BuildArtifact:
    """What one successful ``SceneSpec → .glb`` build produced."""

    glb_path: Path
    size_bytes: int


class SceneBuilder(Protocol):
    """Turns a validated ``SceneSpec`` into a glTF binary on disk."""

    def build(self, spec: SceneSpec, out_dir: Path) -> BuildArtifact: ...
