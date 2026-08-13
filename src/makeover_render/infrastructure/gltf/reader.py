"""Minimal, dependency-free reader for the glTF binary (``.glb``) container.

Exists so the golden tests can assert on *structure* - node names, mesh and
material counts, bounding box - without either a third-party glTF library or a
real Blender process on the reading side. The format is a public, stable
binary spec (a 12-byte header, a JSON chunk, an optional binary chunk), so
parsing just the JSON chunk is a few dozen lines and needs no dependency.

This does not interpret geometry data (accessors, buffer views) - only the
JSON scene graph, which is all the golden tests check.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

GLB_MAGIC: Final = 0x46546C67  # b"glTF" as a little-endian uint32
JSON_CHUNK_TYPE: Final = 0x4E4F534A  # b"JSON"
HEADER_FORMAT: Final = "<III"  # magic, version, total length
CHUNK_HEADER_FORMAT: Final = "<II"  # chunk length, chunk type


class GlbParseError(ValueError):
    """The file is not a well-formed ``.glb`` binary."""


@dataclass(frozen=True)
class GltfDocument:
    """The parsed JSON chunk of a ``.glb``, with a few convenience readers."""

    raw: dict[str, Any]

    @property
    def node_names(self) -> tuple[str, ...]:
        return tuple(node.get("name", "") for node in self.raw.get("nodes", []))

    @property
    def mesh_count(self) -> int:
        return len(self.raw.get("meshes", []))

    @property
    def material_names(self) -> tuple[str, ...]:
        return tuple(material.get("name", "") for material in self.raw.get("materials", []))

    @property
    def accessor_bounds(self) -> tuple[tuple[float, ...], tuple[float, ...]] | None:
        """Combined min/max across every ``POSITION`` accessor, if any exist.

        glTF accessors carry their own bounding box per the spec, so a scene's
        overall extent can be read straight off the JSON chunk without ever
        touching the binary buffer.
        """
        position_indices = {
            attrs["POSITION"]
            for mesh in self.raw.get("meshes", [])
            for primitive in mesh.get("primitives", [])
            for attrs in (primitive.get("attributes", {}),)
            if "POSITION" in attrs
        }
        accessors = self.raw.get("accessors", [])
        boxes = [
            (tuple(accessors[i]["min"]), tuple(accessors[i]["max"]))
            for i in position_indices
            if i < len(accessors) and "min" in accessors[i] and "max" in accessors[i]
        ]
        if not boxes:
            return None
        mins = tuple(min(box[0][axis] for box in boxes) for axis in range(3))
        maxes = tuple(max(box[1][axis] for box in boxes) for axis in range(3))
        return mins, maxes


def read_glb(path: Path) -> GltfDocument:
    data = path.read_bytes()
    if len(data) < 12:
        raise GlbParseError(f"{path} is too short to be a .glb file")

    magic, _version, total_length = struct.unpack_from(HEADER_FORMAT, data, 0)
    if magic != GLB_MAGIC:
        raise GlbParseError(f"{path} does not start with the glTF magic number")
    if total_length > len(data):
        raise GlbParseError(f"{path} declares {total_length} bytes but only has {len(data)}")

    chunk_length, chunk_type = struct.unpack_from(CHUNK_HEADER_FORMAT, data, 12)
    if chunk_type != JSON_CHUNK_TYPE:
        raise GlbParseError(f"{path}'s first chunk is not the required JSON chunk")

    json_bytes = data[20 : 20 + chunk_length]
    try:
        return GltfDocument(raw=json.loads(json_bytes))
    except json.JSONDecodeError as exc:
        raise GlbParseError(f"{path}'s JSON chunk is not valid JSON") from exc
