# makeover-render

**SceneSpec in, animation and GLTF out.** Repo B of two.

This repository is deliberately **domain-free**: it knows about storefronts,
materials, lighting, and cameras — never about postcodes or businesses. Anything
able to produce a `SceneSpec` can drive it.

## Status

**Phase 4 complete — Blender engine core.** `SceneSpec → .glb` works end to
end, verified against real Blender 5.2 LTS: a template registry (two
storefront templates, geometry derived from the caller's own dimensions so
one recipe fits any footprint), procedural materials from `MaterialAssignment`
(sRGB hex converted to linear before it reaches the Principled BSDF), a
Blender text curve converted to mesh for signage, a lighting rig per
`LightingPreset` with physical colour temperature, and a static camera framed
on the storefront. `uv run makeover-render build examples/cafe.json --out
./out` is usable standalone. Rendering pixels and the job API arrive in
Phase 5, which is also where `CameraSpec.move` starts doing something — Phase
4's camera is framed but static, since nothing renders frames yet.

**Golden GLTF tests** (`tests/integration/test_build_scene_golden.py`, marked
`blender`) build a real `.glb` and check it structurally — node names,
material names, bounding box — using a dependency-free `.glb` reader
(`infrastructure/gltf/reader.py`) rather than a third-party glTF library, so
the parser itself has its own unit tests independent of Blender.

## The bpy quarantine

Blender bundles its own interpreter — **3.13.13 for Blender 5.2 LTS** — which
cannot share this service's 3.12 virtualenv. So `bpy` is confined to
`infrastructure/blender/scripts/`, executed *inside* Blender via
`blender --background --factory-startup --python`.

Everything else is ordinary Python with no Blender import, which is why most of
this repo is unit-testable on a machine that has never installed Blender.

```
domain/                              pure scene concepts, no bpy
application/                         ports + use cases, no bpy
infrastructure/blender/runtime.py    subprocess launcher, no bpy
infrastructure/blender/scene_builder.py  drives runtime.py, no bpy
infrastructure/blender/scripts/      <- the only bpy code
```

**`domain/model/template_geometry.py` and `domain/model/geometry.py` use
plain strings and stdlib dataclasses, not `makeover_contracts` types.**
That is not a style choice — Blender's bundled interpreter has no `pydantic`
installed, and importing `makeover_contracts.scene` pulls it in as a side
effect of the module load, regardless of which name is used from it. These
two modules are imported both by this service's own venv and by
`infrastructure/blender/scripts/entrypoint.py` running inside Blender (which
adds this repo's `src/` to `sys.path` itself, since Blender has no notion of
this service's virtualenv), so they stay dependency-free.

## Verified Blender 5.2 behaviour

- `--factory-startup` leaves **Cycles disabled**; the entrypoint must call
  `addon_utils.enable("cycles")` before setting `scene.render.engine = "CYCLES"`.
- Engine and view-transform RNA enums populate dynamically — introspecting
  `enum_items` is misleading. Assign the string and catch the error instead.
- `AgX`, `Filmic`, `Standard`, and `Khronos PBR Neutral` are all available.
- **Confirmed in Phase 4:** `Standard` is the correct view transform for GLTF
  export, not `AgX` — AgX's tone map shifts exported base colours away from
  the sRGB hex a caller specified. `export.py` sets it explicitly before
  every export; `AgX` stays reserved for Phase 5's pixel renders.

## Determinism

Fixed seed, `--factory-startup`, pinned Blender version, pinned AgX view
transform, fixed frame range. Golden tests assert **GLTF structure** — node
names, counts, materials, bounding box — not pixels.

## Quickstart

```bash
make install
```

```bash
make check
```

```bash
curl -s localhost:8081/capabilities
```

Build a `.glb` from a `SceneSpec` (needs a real Blender install; the CLI finds
it via `RENDER_BLENDER_EXECUTABLE` or the usual install locations):

```bash
uv run makeover-render build examples/cafe.json --out ./out
```

The full suite includes real-Blender integration tests, marked `blender` and
skipped by `make test-fast` (what CI runs):

```bash
make test-fast   # unit + integration, no Blender required
make test        # everything, including the golden GLTF tests
```
