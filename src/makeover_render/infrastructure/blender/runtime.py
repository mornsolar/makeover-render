"""Subprocess bridge to Blender.

This module runs under the service's own Python 3.12 and **never imports bpy**.
Blender ships its own interpreter (3.13 for 5.2 LTS), so the only safe way to
drive it is out-of-process. Everything that touches bpy lives in
``infrastructure/blender/scripts/`` and is executed *inside* Blender.

Keeping the boundary here is what lets the rest of this repository be unit
tested on an ordinary Python without Blender installed.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

VERSION_PATTERN = re.compile(r"Blender\s+(\d+\.\d+\.\d+)")
DEFAULT_TIMEOUT_S = 600


class BlenderInvocationError(RuntimeError):
    """Blender exited non-zero, timed out, or produced unreadable output."""


@dataclass(frozen=True)
class BlenderRuntime:
    """Launches Blender in background mode.

    ``--factory-startup`` is not optional: it ignores whatever add-ons and
    preferences the host user happens to have, which is what makes a render
    reproducible on a laptop and in CI alike.
    """

    executable: Path
    timeout_s: int = DEFAULT_TIMEOUT_S

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                [str(self.executable), "--background", "--factory-startup", *args],
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise BlenderInvocationError(f"Blender exceeded {self.timeout_s}s") from exc
        except OSError as exc:
            raise BlenderInvocationError(f"Could not launch {self.executable}") from exc

    def probe_version(self) -> str:
        """Return Blender's version string, e.g. ``5.2.0``.

        Used by the capability manifest so callers can see exactly which engine
        produced an artifact.
        """
        result = self._run(["--version"])
        match = VERSION_PATTERN.search(result.stdout)
        if match is None:
            raise BlenderInvocationError(f"Unrecognised version output: {result.stdout[:200]!r}")
        return match.group(1)

    def run_script(self, script: Path, script_args: list[str]) -> str:
        """Execute a script inside Blender and return its stdout.

        Arguments after ``--`` are passed through to the script rather than
        consumed by Blender itself.
        """
        result = self._run(["--python", str(script), "--", *script_args])
        if result.returncode != 0:
            raise BlenderInvocationError(
                f"Blender exited {result.returncode}: {result.stderr[-2000:]}"
            )
        return result.stdout
