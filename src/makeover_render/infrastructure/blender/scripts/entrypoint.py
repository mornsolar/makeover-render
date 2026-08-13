"""The one file ``BlenderRuntime.run_script`` invokes.

Runs inside Blender via ``blender --background --factory-startup --python
entrypoint.py -- --spec spec.json --out ./out``. Adds this repo's own ``src``
to ``sys.path`` before importing anything from it - Blender's bundled
interpreter has no notion of this service's virtualenv - then hands a plain
dict (never a reconstructed ``SceneSpec``: no ``pydantic`` here) to
``build_scene.build``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[4]
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from makeover_render.infrastructure.blender.scripts.build_scene import build


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main() -> None:
    # Blender passes its own args before "--"; only what follows is ours.
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    args = _parse_args(argv)

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    args.out.mkdir(parents=True, exist_ok=True)
    glb_path = build(spec, args.out)
    print(f"BUILD_OK {glb_path}")


if __name__ == "__main__":
    main()
