"""Animated-render port.

Separate from ``SceneBuilder`` (the ``.glb`` port) on purpose: a caller that
only wants a static model has no reason to pay for a multi-frame render, and
the two produce genuinely different artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from makeover_contracts.scene import SceneSpec


@dataclass(frozen=True)
class AnimationArtifact:
    """What one successful animated render produced."""

    video_path: Path
    thumbnail_path: Path
    still_paths: tuple[Path, ...]


class AnimationRenderer(Protocol):
    """Renders a ``SceneSpec``'s camera move to video, plus a thumbnail and
    a handful of still frames."""

    def render(self, spec: SceneSpec, out_dir: Path) -> AnimationArtifact: ...
