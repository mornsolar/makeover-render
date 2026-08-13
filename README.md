# makeover-render

**SceneSpec in, animation and GLTF out.** Repo B of two.

This repository is deliberately **domain-free**: it knows about storefronts,
materials, lighting, and cameras — never about postcodes or businesses. Anything
able to produce a `SceneSpec` can drive it.

## Status

**Phase 0 — foundations.** Toolchain, `/health`, `/capabilities`, and the
out-of-process Blender bridge are in place. Scene building, rendering, and the
job API arrive in Phases 4-5.

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
infrastructure/blender/scripts/      <- the only bpy code
```

## Verified Blender 5.2 behaviour

- `--factory-startup` leaves **Cycles disabled**; the entrypoint must call
  `addon_utils.enable("cycles")` before setting `scene.render.engine = "CYCLES"`.
- Engine and view-transform RNA enums populate dynamically — introspecting
  `enum_items` is misleading. Assign the string and catch the error instead.
- `AgX`, `Filmic`, `Standard`, and `Khronos PBR Neutral` are all available.

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
