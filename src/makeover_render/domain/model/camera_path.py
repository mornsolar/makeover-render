"""Per-frame camera positions for each ``CameraMove``.

Kept dependency-free like the rest of ``domain/model`` (see
``template_geometry``'s module docstring for why) and, crucially, kept
*rotation-free*: every path here is a sequence of positions only. The
Blender-side render loop derives each frame's rotation by pointing the camera
at the same fixed target used everywhere else in this repo, so a path can
never drift out of frame - it only has to move correctly, not aim correctly.
"""

from __future__ import annotations

import math
from typing import Final

from makeover_render.domain.model.geometry import Vec3

PAN_SWEEP_DEG: Final = 20.0
DOLLY_IN_END_FACTOR: Final = 0.5
CRANE_DOWN_START_ELEVATION_FACTOR: Final = 0.6


def positions_for(move: str, target: Vec3, distance: float, frame_count: int) -> tuple[Vec3, ...]:
    """The camera's world-space position at each of ``frame_count`` frames."""
    if frame_count < 1:
        raise ValueError(f"frame_count must be at least 1, got {frame_count}")
    builder = _BUILDERS.get(move)
    if builder is None:
        known = ", ".join(sorted(_BUILDERS))
        raise ValueError(f"unknown camera move {move!r}; known: {known}")
    return builder(target, distance, frame_count)


def _progress(index: int, frame_count: int) -> float:
    """0.0 at the first frame, 1.0 at the last - 0.0 for a single frame."""
    return index / (frame_count - 1) if frame_count > 1 else 0.0


def _lerp(start: float, end: float, t: float) -> float:
    return start + (end - start) * t


def _orbit(target: Vec3, distance: float, frame_count: int) -> tuple[Vec3, ...]:
    return tuple(
        (
            target[0] + distance * math.sin(2 * math.pi * i / frame_count),
            target[1] - distance * math.cos(2 * math.pi * i / frame_count),
            target[2],
        )
        for i in range(frame_count)
    )


def _dolly_in(target: Vec3, distance: float, frame_count: int) -> tuple[Vec3, ...]:
    end_distance = distance * DOLLY_IN_END_FACTOR
    return tuple(
        (
            target[0],
            target[1] - _lerp(distance, end_distance, _progress(i, frame_count)),
            target[2],
        )
        for i in range(frame_count)
    )


def _crane_down(target: Vec3, distance: float, frame_count: int) -> tuple[Vec3, ...]:
    start_elevation = distance * CRANE_DOWN_START_ELEVATION_FACTOR
    return tuple(
        (
            target[0],
            target[1] - distance,
            target[2] + _lerp(start_elevation, 0.0, _progress(i, frame_count)),
        )
        for i in range(frame_count)
    )


def _pan(target: Vec3, distance: float, frame_count: int) -> tuple[Vec3, ...]:
    sweep = math.radians(PAN_SWEEP_DEG)
    return tuple(
        (
            target[0] + distance * math.sin(_lerp(-sweep, sweep, _progress(i, frame_count))),
            target[1] - distance * math.cos(_lerp(-sweep, sweep, _progress(i, frame_count))),
            target[2],
        )
        for i in range(frame_count)
    )


_BUILDERS: Final = {
    "orbit": _orbit,
    "dolly_in": _dolly_in,
    "crane_down": _crane_down,
    "pan": _pan,
}


def known_moves() -> tuple[str, ...]:
    return tuple(sorted(_BUILDERS))
