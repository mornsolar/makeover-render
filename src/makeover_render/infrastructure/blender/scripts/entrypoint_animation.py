"""The Blender entrypoint for an animated render.

Runs via ``blender --background --factory-startup --python
entrypoint_animation.py -- --spec spec.json --out ./out``. Sibling to
``entrypoint.py`` (the static ``.glb`` build) - see that file's docstring for
why ``sys.path`` is patched by hand and why the spec stays a plain dict.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[4]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from makeover_render.domain.model.geometry import Dimensions
from makeover_render.infrastructure.blender.scripts.render_frames import render_frames
from makeover_render.infrastructure.blender.scripts.scene_content import construct_scene


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = _parse_args(argv)

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)

    dims = Dimensions(**spec["dimensions"])
    geometry = construct_scene(spec, dims)
    frame_paths = render_frames(
        spec, geometry.camera_target(dims), geometry.camera_distance(dims), args.out
    )
    print(f"RENDER_OK {len(frame_paths)} frames in {args.out}")


if __name__ == "__main__":
    main()
