"""Drives Blender to render frames, then ffmpeg to encode them.

The one adapter that crosses both subprocess boundaries this repo has: a
Blender process renders PNGs, then an ordinary ffmpeg process (no bpy
involved at all) turns them into an mp4. Thumbnail and stills are just
copies of frames Blender already produced - ffmpeg has nothing to add to a
still image that is already a PNG.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Final

from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.animation_renderer import AnimationArtifact
from makeover_render.domain.errors import BuildFailedError
from makeover_render.domain.model.build_output import FRAME_FILENAME_PATTERN
from makeover_render.infrastructure.blender.runtime import BlenderInvocationError, BlenderRuntime
from makeover_render.infrastructure.encoding.ffmpeg import FfmpegEncoder, FfmpegInvocationError

_ENTRYPOINT = Path(__file__).parent / "scripts" / "entrypoint_animation.py"
_FRAME_GLOB = "frame_*.png"

VIDEO_FILENAME: Final = "animation.mp4"
THUMBNAIL_FILENAME: Final = "thumbnail.png"
DEFAULT_MAX_STILLS: Final = 3


class BlenderAnimationRenderer:
    """The ``AnimationRenderer`` port, implemented by Blender plus ffmpeg."""

    def __init__(
        self,
        runtime: BlenderRuntime,
        encoder: FfmpegEncoder,
        *,
        max_stills: int = DEFAULT_MAX_STILLS,
    ) -> None:
        self._runtime = runtime
        self._encoder = encoder
        self._max_stills = max_stills

    def render(self, spec: SceneSpec, out_dir: Path) -> AnimationArtifact:
        frames_dir = out_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="makeover-spec-") as tmp:
            spec_path = Path(tmp) / "spec.json"
            spec_path.write_text(json.dumps(spec.model_dump(mode="json")), encoding="utf-8")
            try:
                self._runtime.run_script(
                    _ENTRYPOINT, ["--spec", str(spec_path), "--out", str(frames_dir)]
                )
            except BlenderInvocationError as exc:
                raise BuildFailedError(str(exc)) from exc

        frame_paths = sorted(frames_dir.glob(_FRAME_GLOB))
        if not frame_paths:
            raise BuildFailedError(f"Blender exited without rendering any frames into {frames_dir}")

        video_path = out_dir / VIDEO_FILENAME
        try:
            self._encoder.encode_mp4(
                frames_dir / FRAME_FILENAME_PATTERN, spec.camera.fps, video_path
            )
        except FfmpegInvocationError as exc:
            raise BuildFailedError(str(exc)) from exc

        thumbnail_path = out_dir / THUMBNAIL_FILENAME
        shutil.copyfile(frame_paths[0], thumbnail_path)

        return AnimationArtifact(
            video_path=video_path,
            thumbnail_path=thumbnail_path,
            still_paths=self._select_stills(frame_paths, out_dir),
        )

    def _select_stills(self, frame_paths: list[Path], out_dir: Path) -> tuple[Path, ...]:
        count = min(self._max_stills, len(frame_paths))
        # Evenly spaced across the whole take, not just the first few frames -
        # a still of only the opening frame would defeat the point of picking
        # more than one.
        indices = {round(i * (len(frame_paths) - 1) / max(1, count - 1)) for i in range(count)}
        stills = []
        for position, index in enumerate(sorted(indices)):
            dest = out_dir / f"still_{position}.png"
            shutil.copyfile(frame_paths[index], dest)
            stills.append(dest)
        return tuple(stills)
