"""The ``makeover-render build`` command."""

from __future__ import annotations

from pathlib import Path

import pytest

from makeover_render.application.use_cases.build_scene import BuildScene
from makeover_render.interfaces.cli import main as cli
from tests.fakes.scene_builder import FakeSceneBuilder
from tests.fakes.specs import make_spec

SPEC_JSON = make_spec().model_dump_json()


@pytest.fixture
def stub_use_case(monkeypatch):
    """Swap the composed use case, leaving argument parsing and output real."""

    def install(use_case: BuildScene) -> None:
        monkeypatch.setattr(cli, "build_scene_use_case", lambda settings: use_case)

    return install


def test_prints_the_produced_artifact(stub_use_case, tmp_path, capsys):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(SPEC_JSON, encoding="utf-8")
    builder = FakeSceneBuilder(glb_path=tmp_path / "out" / "scene.glb", size_bytes=137_456)
    stub_use_case(BuildScene(builder))

    exit_code = cli.main(["build", str(spec_path), "--out", str(tmp_path / "out")])

    output = capsys.readouterr().out
    assert exit_code == cli.EXIT_OK
    assert "scene.glb" in output
    assert "137,456 bytes" in output


def test_rejects_a_spec_that_is_not_well_formed(stub_use_case, tmp_path, capsys):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text('{"template_id": "x"}', encoding="utf-8")
    stub_use_case(BuildScene(FakeSceneBuilder()))

    exit_code = cli.main(["build", str(spec_path)])

    assert exit_code == cli.EXIT_USAGE
    assert "invalid SceneSpec" in capsys.readouterr().err


def test_reports_a_build_failure_without_a_traceback(stub_use_case, tmp_path, capsys):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        make_spec(template_id="does-not-exist").model_dump_json(), encoding="utf-8"
    )
    stub_use_case(BuildScene(FakeSceneBuilder()))

    exit_code = cli.main(["build", str(spec_path)])

    assert exit_code == cli.EXIT_BUILD_FAILED
    assert "build failed" in capsys.readouterr().err


def test_defaults_the_output_directory_to_out(stub_use_case, tmp_path):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(SPEC_JSON, encoding="utf-8")
    stub_use_case(BuildScene(FakeSceneBuilder()))

    args = cli.build_parser().parse_args(["build", str(spec_path)])

    assert args.out == Path("./out")
