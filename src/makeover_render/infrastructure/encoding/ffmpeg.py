"""Subprocess bridge to ffmpeg.

Mirrors ``infrastructure/blender/runtime.py`` deliberately: same shape
(dataclass, resolved executable, timeout, translated exceptions), because
encoding is the same kind of problem - drive an external binary, capture its
failure, and never leak a raw ``CalledProcessError`` past this module.

Frame encoding only. Extracting a thumbnail or a still is just picking one of
the PNG frames Blender already rendered - ffmpeg has nothing to add there.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT_S = 120
PIXEL_FORMAT = "yuv420p"
"""Every consumer-grade video player and browser decodes this; anything else
risks a file that encodes fine and then won't play somewhere."""


class FfmpegInvocationError(RuntimeError):
    """ffmpeg exited non-zero, timed out, or produced no output file."""


@dataclass(frozen=True)
class FfmpegEncoder:
    executable: Path
    timeout_s: int = DEFAULT_TIMEOUT_S

    def encode_mp4(self, frame_glob: Path, fps: int, out_path: Path) -> None:
        """Encode a sequential PNG frame pattern (e.g. ``frame_%04d.png``) to
        an mp4 at ``out_path``."""
        args = [
            str(self.executable),
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frame_glob),
            "-pix_fmt",
            PIXEL_FORMAT,
            "-movflags",
            "+faststart",
            str(out_path),
        ]
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=self.timeout_s, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise FfmpegInvocationError(f"ffmpeg exceeded {self.timeout_s}s") from exc
        except OSError as exc:
            raise FfmpegInvocationError(f"Could not launch {self.executable}") from exc

        if result.returncode != 0:
            raise FfmpegInvocationError(
                f"ffmpeg exited {result.returncode}: {result.stderr[-2000:]}"
            )
        if not out_path.exists():
            raise FfmpegInvocationError(f"ffmpeg exited 0 but did not produce {out_path}")
