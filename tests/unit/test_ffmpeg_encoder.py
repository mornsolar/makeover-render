from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from makeover_render.infrastructure.encoding import ffmpeg as ffmpeg_module
from makeover_render.infrastructure.encoding.ffmpeg import FfmpegEncoder, FfmpegInvocationError

ENCODER = FfmpegEncoder(executable=Path("/fake/ffmpeg"))
OUT_PATH = Path("/fake/out/animation.mp4")


def completed(stdout: str = "", stderr: str = "", code: int = 0):
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr=stderr)


class TestEncodeMp4:
    def test_raises_when_ffmpeg_exits_non_zero(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            ffmpeg_module.subprocess, "run", lambda *a, **k: completed(stderr="boom", code=1)
        )
        with pytest.raises(FfmpegInvocationError, match="boom"):
            ENCODER.encode_mp4(Path("frame_%04d.png"), fps=24, out_path=tmp_path / "out.mp4")

    def test_raises_when_ffmpeg_exits_zero_but_wrote_nothing(self, monkeypatch, tmp_path):
        # A codec that silently no-ops on an empty frame glob is a real
        # failure mode - exit 0 alone is not proof of a usable video.
        monkeypatch.setattr(ffmpeg_module.subprocess, "run", lambda *a, **k: completed())
        missing = tmp_path / "out.mp4"
        with pytest.raises(FfmpegInvocationError, match="did not produce"):
            ENCODER.encode_mp4(Path("frame_%04d.png"), fps=24, out_path=missing)

    def test_succeeds_when_ffmpeg_exits_zero_and_the_file_exists(self, monkeypatch, tmp_path):
        monkeypatch.setattr(ffmpeg_module.subprocess, "run", lambda *a, **k: completed())
        out_path = tmp_path / "out.mp4"
        out_path.write_bytes(b"fake video")
        ENCODER.encode_mp4(Path("frame_%04d.png"), fps=24, out_path=out_path)

    def test_passes_fps_as_the_input_framerate(self, monkeypatch, tmp_path):
        seen: dict[str, list[str]] = {}

        def capture(args, **kwargs):
            seen["args"] = args
            out = tmp_path / "out.mp4"
            out.write_bytes(b"x")
            return completed()

        monkeypatch.setattr(ffmpeg_module.subprocess, "run", capture)
        ENCODER.encode_mp4(Path("frame_%04d.png"), fps=30, out_path=tmp_path / "out.mp4")
        args = seen["args"]
        assert args[args.index("-framerate") + 1] == "30"

    def test_translates_a_timeout(self, monkeypatch):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="ffmpeg", timeout=1)

        monkeypatch.setattr(ffmpeg_module.subprocess, "run", boom)
        with pytest.raises(FfmpegInvocationError, match="exceeded"):
            ENCODER.encode_mp4(Path("frame_%04d.png"), fps=24, out_path=OUT_PATH)

    def test_translates_a_missing_executable(self, monkeypatch):
        def boom(*a, **k):
            raise OSError("no such file")

        monkeypatch.setattr(ffmpeg_module.subprocess, "run", boom)
        with pytest.raises(FfmpegInvocationError, match="Could not launch"):
            ENCODER.encode_mp4(Path("frame_%04d.png"), fps=24, out_path=OUT_PATH)
