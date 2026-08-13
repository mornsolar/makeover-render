"""The one test that launches the real Blender.

Marked ``blender`` so the default CI job can skip it. It proves the subprocess
quarantine works end to end: a Python 3.12 process driving Blender's own 3.13
interpreter with no shared virtualenv.
"""

from __future__ import annotations

import pytest

from makeover_render.config.settings import Settings
from makeover_render.infrastructure.blender.runtime import BlenderRuntime

pytestmark = pytest.mark.blender


@pytest.fixture
def runtime() -> BlenderRuntime:
    try:
        executable = Settings().resolve_blender()
    except FileNotFoundError as exc:
        pytest.skip(str(exc))
    return BlenderRuntime(executable=executable)


def test_probes_a_supported_blender_version(runtime: BlenderRuntime):
    version = runtime.probe_version()
    assert version.startswith("5."), f"expected Blender 5.x, got {version}"


def test_runs_python_inside_blenders_own_interpreter(runtime: BlenderRuntime, tmp_path):
    script = tmp_path / "probe.py"
    script.write_text(
        "import sys, bpy\nprint('INSIDE', bpy.app.version_string, sys.version_info[:2])\n",
        encoding="utf-8",
    )
    output = runtime.run_script(script, [])
    assert "INSIDE" in output
