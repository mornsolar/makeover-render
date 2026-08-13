"""Command-line entry point.

Exists so Repo B is demonstrable standalone, without a job queue or an HTTP
client - the same rationale as the discovery repo's CLI, and it exercises the
same object graph the API would use once Phase 5 adds one.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from makeover_contracts.scene import SceneSpec
from pydantic import ValidationError

from makeover_render.composition import build_scene_use_case
from makeover_render.config.settings import get_settings
from makeover_render.domain.errors import RenderError

EXIT_OK: Final = 0
EXIT_USAGE: Final = 2
EXIT_BUILD_FAILED: Final = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="makeover-render", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    build = subcommands.add_parser("build", help="Build a SceneSpec into a .glb")
    build.add_argument("spec", type=Path, help="Path to a SceneSpec JSON file")
    build.add_argument("--out", type=Path, default=Path("./out"))
    return parser


def run_build(spec_path: Path, out_dir: Path) -> str:
    spec = SceneSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))
    use_case = build_scene_use_case(get_settings())
    artifact = use_case.execute(spec, out_dir)
    return f"{artifact.glb_path}  ({artifact.size_bytes:,} bytes)"


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        print(run_build(args.spec, args.out))
        return EXIT_OK
    except ValidationError as exc:
        print(f"invalid SceneSpec: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except RenderError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return EXIT_BUILD_FAILED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
