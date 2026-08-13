from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from makeover_render.infrastructure.blender import runtime as runtime_module
from makeover_render.infrastructure.blender.runtime import (
    BlenderInvocationError,
    BlenderRuntime,
)

RUNTIME = BlenderRuntime(executable=Path("/fake/blender"))


def completed(stdout: str = "", stderr: str = "", code: int = 0):
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr=stderr)


class TestProbeVersion:
    def test_extracts_the_version_from_blender_output(self, monkeypatch):
        monkeypatch.setattr(
            runtime_module.subprocess,
            "run",
            lambda *a, **k: completed(stdout="Blender 5.2.0 LTS\n\tbuild date: 2026-07-14"),
        )
        assert RUNTIME.probe_version() == "5.2.0"

    def test_raises_on_unrecognised_output(self, monkeypatch):
        monkeypatch.setattr(
            runtime_module.subprocess, "run", lambda *a, **k: completed(stdout="???")
        )
        with pytest.raises(BlenderInvocationError, match="Unrecognised version output"):
            RUNTIME.probe_version()

    def test_always_passes_background_and_factory_startup(self, monkeypatch):
        # Reproducibility depends on ignoring host add-ons and preferences.
        seen: dict[str, list[str]] = {}

        def capture(args, **kwargs):
            seen["args"] = args
            return completed(stdout="Blender 5.2.0 LTS")

        monkeypatch.setattr(runtime_module.subprocess, "run", capture)
        RUNTIME.probe_version()
        assert "--background" in seen["args"]
        assert "--factory-startup" in seen["args"]


class TestFailureModes:
    def test_translates_a_timeout(self, monkeypatch):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="blender", timeout=1)

        monkeypatch.setattr(runtime_module.subprocess, "run", boom)
        with pytest.raises(BlenderInvocationError, match="exceeded"):
            RUNTIME.probe_version()

    def test_translates_a_missing_executable(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("no such file")

        monkeypatch.setattr(runtime_module.subprocess, "run", boom)
        with pytest.raises(BlenderInvocationError, match="Could not launch"):
            RUNTIME.probe_version()


class TestRunScript:
    def test_returns_stdout_on_success(self, monkeypatch):
        monkeypatch.setattr(
            runtime_module.subprocess, "run", lambda *a, **k: completed(stdout="DONE")
        )
        assert RUNTIME.run_script(Path("/s.py"), []) == "DONE"

    def test_raises_with_stderr_on_failure(self, monkeypatch):
        monkeypatch.setattr(
            runtime_module.subprocess,
            "run",
            lambda *a, **k: completed(stderr="traceback here", code=1),
        )
        with pytest.raises(BlenderInvocationError, match="traceback here"):
            RUNTIME.run_script(Path("/s.py"), [])

    def test_passes_script_arguments_after_a_double_dash(self, monkeypatch):
        # Blender consumes its own flags; everything after `--` reaches the script.
        seen: dict[str, list[str]] = {}

        def capture(args, **kwargs):
            seen["args"] = args
            return completed(stdout="")

        monkeypatch.setattr(runtime_module.subprocess, "run", capture)
        RUNTIME.run_script(Path("/s.py"), ["--spec", "spec.json"])
        assert seen["args"].index("--") < seen["args"].index("--spec")
