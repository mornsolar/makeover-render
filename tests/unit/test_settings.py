from __future__ import annotations

from pathlib import Path

import pytest

from makeover_render.config.settings import Settings


class TestResolveBlender:
    def test_uses_an_explicitly_configured_executable(self, tmp_path):
        blender = tmp_path / "blender"
        blender.touch()
        assert Settings(blender_executable=blender).resolve_blender() == blender

    def test_raises_when_the_configured_path_is_absent(self, tmp_path):
        missing = tmp_path / "nope"
        with pytest.raises(FileNotFoundError, match="not found at"):
            Settings(blender_executable=missing).resolve_blender()

    def test_error_names_the_environment_variable_to_set(self, monkeypatch):
        # A missing Blender is an operator problem; the message must say how to
        # fix it rather than surfacing a bare path.
        monkeypatch.setattr("makeover_render.config.settings.shutil.which", lambda _: None)
        monkeypatch.setattr(
            "makeover_render.config.settings.MACOS_BLENDER", Path("/nonexistent/blender")
        )
        with pytest.raises(FileNotFoundError, match="RENDER_BLENDER_EXECUTABLE"):
            Settings().resolve_blender()

    def test_falls_back_to_the_executable_on_path(self, tmp_path, monkeypatch):
        blender = tmp_path / "blender"
        blender.touch()
        monkeypatch.setattr("makeover_render.config.settings.shutil.which", lambda _: str(blender))
        assert Settings().resolve_blender() == blender


class TestDefaults:
    def test_defaults_to_the_local_environment(self):
        assert Settings().environment == "local"

    def test_names_itself_for_health_reporting(self):
        assert Settings().service_name == "makeover-render"
