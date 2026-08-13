"""The dependency-free ``.glb`` reader, against hand-built fixtures.

Building the bytes by hand rather than via Blender is the point: this reader
has to be correct against the public glTF binary spec on its own, so the
golden tests (which build real files with Blender) are checking the builder,
not silently also re-deriving the parser's correctness.
"""

from __future__ import annotations

import json
import struct

import pytest

from makeover_render.infrastructure.gltf.reader import (
    GLB_MAGIC,
    JSON_CHUNK_TYPE,
    GlbParseError,
    read_glb,
)


def _glb_bytes(document: dict) -> bytes:
    json_bytes = json.dumps(document).encode("utf-8")
    padding = (-len(json_bytes)) % 4  # glTF pads each chunk to a 4-byte boundary
    json_bytes += b" " * padding

    chunk_header = struct.pack("<II", len(json_bytes), JSON_CHUNK_TYPE)
    total_length = 12 + len(chunk_header) + len(json_bytes)
    header = struct.pack("<III", GLB_MAGIC, 2, total_length)
    return header + chunk_header + json_bytes


SAMPLE_DOCUMENT = {
    "asset": {"version": "2.0"},
    "nodes": [{"name": "panel.facade"}, {"name": "panel.ground"}, {"name": "signage_text"}],
    "meshes": [
        {"primitives": [{"attributes": {"POSITION": 0}}]},
        {"primitives": [{"attributes": {"POSITION": 1}}]},
    ],
    "materials": [{"name": "render"}, {"name": "terrazzo"}],
    "accessors": [
        {"min": [-3.0, 0.0, -0.1], "max": [3.0, 3.2, 0.1]},
        {"min": [-3.0, -2.0, -0.1], "max": [3.0, 0.0, 0.0]},
    ],
}


def test_reads_node_names(tmp_path):
    path = tmp_path / "scene.glb"
    path.write_bytes(_glb_bytes(SAMPLE_DOCUMENT))

    doc = read_glb(path)

    assert doc.node_names == ("panel.facade", "panel.ground", "signage_text")


def test_counts_meshes(tmp_path):
    path = tmp_path / "scene.glb"
    path.write_bytes(_glb_bytes(SAMPLE_DOCUMENT))

    assert read_glb(path).mesh_count == 2


def test_reads_material_names(tmp_path):
    path = tmp_path / "scene.glb"
    path.write_bytes(_glb_bytes(SAMPLE_DOCUMENT))

    assert read_glb(path).material_names == ("render", "terrazzo")


def test_combines_position_accessor_bounds_across_every_mesh(tmp_path):
    path = tmp_path / "scene.glb"
    path.write_bytes(_glb_bytes(SAMPLE_DOCUMENT))

    minimum, maximum = read_glb(path).accessor_bounds

    assert minimum == (-3.0, -2.0, -0.1)
    assert maximum == (3.0, 3.2, 0.1)


def test_bounds_are_none_when_there_are_no_meshes(tmp_path):
    path = tmp_path / "scene.glb"
    path.write_bytes(_glb_bytes({"asset": {"version": "2.0"}}))

    assert read_glb(path).accessor_bounds is None


def test_handles_a_node_with_no_name(tmp_path):
    path = tmp_path / "scene.glb"
    path.write_bytes(_glb_bytes({"asset": {"version": "2.0"}, "nodes": [{}]}))

    assert read_glb(path).node_names == ("",)


def test_rejects_a_file_too_short_to_have_a_header(tmp_path):
    path = tmp_path / "scene.glb"
    path.write_bytes(b"short")

    with pytest.raises(GlbParseError, match="too short"):
        read_glb(path)


def test_rejects_a_file_without_the_glb_magic_number(tmp_path):
    path = tmp_path / "scene.glb"
    path.write_bytes(struct.pack("<III", 0xDEADBEEF, 2, 12) + b"\x00" * 20)

    with pytest.raises(GlbParseError, match="magic number"):
        read_glb(path)


def test_rejects_a_length_longer_than_the_actual_file(tmp_path):
    path = tmp_path / "scene.glb"
    path.write_bytes(struct.pack("<III", GLB_MAGIC, 2, 10_000) + b"\x00" * 20)

    with pytest.raises(GlbParseError, match="declares"):
        read_glb(path)


def test_rejects_a_first_chunk_that_is_not_json(tmp_path):
    body = b"\x00" * 8
    chunk_header = struct.pack("<II", len(body), 0x004E4942)  # b"BIN\0"
    header = struct.pack("<III", GLB_MAGIC, 2, 12 + len(chunk_header) + len(body))
    path = tmp_path / "scene.glb"
    path.write_bytes(header + chunk_header + body)

    with pytest.raises(GlbParseError, match="JSON chunk"):
        read_glb(path)


def test_rejects_malformed_json_in_the_json_chunk(tmp_path):
    bad_json = b"{not valid json"
    chunk_header = struct.pack("<II", len(bad_json), JSON_CHUNK_TYPE)
    header = struct.pack("<III", GLB_MAGIC, 2, 12 + len(chunk_header) + len(bad_json))
    path = tmp_path / "scene.glb"
    path.write_bytes(header + chunk_header + bad_json)

    with pytest.raises(GlbParseError, match="not valid JSON"):
        read_glb(path)
