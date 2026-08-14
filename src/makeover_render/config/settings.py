"""Typed configuration for the render service."""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MACOS_BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")


def _default_blender_path() -> Path | None:
    """Best-effort discovery of a Blender executable.

    Checked at import of settings rather than at render time so a misconfigured
    host fails at startup instead of halfway through a job.
    """
    found = shutil.which("blender")
    if found:
        return Path(found)
    return MACOS_BLENDER if MACOS_BLENDER.exists() else None


def _default_ffmpeg_path() -> Path | None:
    found = shutil.which("ffmpeg")
    return Path(found) if found else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RENDER_", env_file=".env", extra="ignore")

    environment: Literal["local", "test", "production"] = "local"
    service_name: str = "makeover-render"
    log_level: str = "INFO"
    blender_executable: Path | None = None
    ffmpeg_executable: Path | None = None
    artifact_dir: Path = Path("var/artifacts")

    redis_url: str = "redis://localhost:6379"
    """A plain Redis process, not a container - Docker itself stays deferred
    to Phase 7 per the roadmap; arq's queue only needs Redis reachable."""
    job_timeout_s: float = Field(default=600.0, gt=0.0)

    def resolve_blender(self) -> Path:
        """Return the Blender executable, or explain why there isn't one."""
        candidate = self.blender_executable or _default_blender_path()
        if candidate is None:
            raise FileNotFoundError(
                "No Blender executable found. Install Blender or set "
                "RENDER_BLENDER_EXECUTABLE to its full path."
            )
        if not candidate.exists():
            raise FileNotFoundError(f"Blender executable not found at {candidate}")
        return candidate

    def resolve_ffmpeg(self) -> Path:
        """Return the ffmpeg executable, or explain why there isn't one."""
        candidate = self.ffmpeg_executable or _default_ffmpeg_path()
        if candidate is None:
            raise FileNotFoundError(
                "No ffmpeg executable found. Install ffmpeg or set "
                "RENDER_FFMPEG_EXECUTABLE to its full path."
            )
        if not candidate.exists():
            raise FileNotFoundError(f"ffmpeg executable not found at {candidate}")
        return candidate


@lru_cache
def get_settings() -> Settings:
    return Settings()
