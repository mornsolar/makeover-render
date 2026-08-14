# makeover-render

**SceneSpec in, animation and GLTF out.** Repo B of two.

This repository is deliberately **domain-free**: it knows about storefronts,
materials, lighting, and cameras — never about postcodes or businesses. Anything
able to produce a `SceneSpec` can drive it.

## Status

**Phase 5 complete — animation & job service.** `SceneSpec → {.glb, .mp4,
thumbnail, stills}` works end to end through the real HTTP job API, verified
against a real Blender 5.2 LTS render, a real ffmpeg encode, and a real local
Redis + arq worker — not just green tests. `POST /jobs` validates the spec
against this renderer's own build recipes *before* enqueuing (a spec missing
a required material gets a 400 immediately, never occupies a worker), then
enqueues onto arq; `GET /jobs/{id}` reads straight back from arq's own
Redis-backed job record rather than a second, parallel job store — one
source of truth, so the API process and the worker process can never
disagree about a job's state. `CameraSpec.move` now does something: four
camera paths (`orbit`, `dolly_in`, `crane_down`, `pan`) are pure position
math in `domain/model/camera_path.py`, aimed every frame by the same
`track_to_target` helper the Phase 4 static camera uses, so a path can move
incorrectly but never drift out of frame. Blender renders one PNG per frame;
ffmpeg (a plain subprocess, no Blender involvement) encodes them to an
H.264 mp4; the thumbnail and stills are just copies of frames Blender
already produced.

Live-verified via `redis-server` (a plain local process — Docker itself
stays deferred to Phase 7) plus a real `uv run arq
makeover_render.interfaces.worker.settings.WorkerSettings` and a real
`uvicorn` process: a tiny spec (64×64, 4 samples, 12 frames) went from
`POST /jobs` → `queued` → `running` → `succeeded` in under 10 seconds, with
`ffprobe` confirming the produced mp4 was a genuine 64×64/12fps/12-frame
H.264 stream, and every `ArtifactRef.sha256` in the response matched the
actual file bytes on disk. The 400-before-enqueue and 404-unknown-job paths
were checked against the live server too. **Not verified this phase:**
retry/backoff behaviour under a crashed worker, and the Docker image itself
(the `Dockerfile`'s `ffmpeg` install already anticipated this phase and
needed no changes, but building or running the container is Phase 7's job,
and there is currently no container command for the worker — only the API's
`CMD` exists).

**Golden GLTF tests** (`tests/integration/test_build_scene_golden.py`, marked
`blender`) build a real `.glb` and check it structurally — node names,
material names, bounding box — using a dependency-free `.glb` reader
(`infrastructure/gltf/reader.py`) rather than a third-party glTF library, so
the parser itself has its own unit tests independent of Blender. A parallel
live-Redis suite (`tests/integration/test_arq_job_queue.py`, marked `redis`)
spins up an ephemeral `redis-server` and exercises the arq adapter for real,
since a fake queue can only prove the router's logic, not that the adapter's
assumptions about arq's `Job.status`/`Job.info`/`Job.result_info` API still
hold.

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
  every export.
- **Confirmed in Phase 5:** the animated render path (`render_frames.py`)
  leaves the view transform at Blender's factory default (`AgX`) rather than
  forcing `Standard` — pixel renders are meant to look like a rendered
  photo, and `Standard`'s job was specifically to protect glTF's exported
  material colours, which don't apply to a PNG frame.

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

Run the full animated job pipeline (needs Blender, ffmpeg, and a Redis
reachable at `RENDER_REDIS_URL`, default `redis://localhost:6379` — Redis as
a plain local process, no Docker required for this):

```bash
redis-server &
uv run arq makeover_render.interfaces.worker.settings.WorkerSettings &
uv run uvicorn makeover_render.interfaces.api.app:app --port 8081 &
curl -X POST localhost:8081/jobs -H "Content-Type: application/json" -d @examples/cafe.json
curl localhost:8081/jobs/<id-from-the-response-above>
```

The full suite includes real-Blender integration tests, marked `blender`,
and a real-Redis integration test, marked `redis` (skips itself if
`redis-server` isn't installed). `make test-fast` (what CI runs) skips only
the Blender ones:

```bash
make test-fast   # unit + integration, no Blender required
make test        # everything, including the golden GLTF tests
```
