"""The one filename convention shared across the subprocess boundary.

Both sides need to agree on it - the Blender-side script that writes the file
and the ordinary-Python side that looks for it afterwards - so it lives in a
module with zero imports of its own, importable from either side without
pulling in ``bpy`` or ``pydantic``.
"""

from __future__ import annotations

from typing import Final

GLB_FILENAME: Final = "scene.glb"
FRAME_FILENAME_PATTERN: Final = "frame_%04d.png"
