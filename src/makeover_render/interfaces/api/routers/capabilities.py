"""Capability advertisement.

Repo A calls this to learn the renderer's vocabulary before asking an LLM to
produce a brief, which is what keeps the dependency one-directional.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from makeover_contracts.capability import CapabilityManifest

from makeover_render.capabilities.manifest import build_manifest
from makeover_render.infrastructure.blender.runtime import (
    BlenderInvocationError,
    BlenderRuntime,
)
from makeover_render.interfaces.api.deps import BlenderRuntimeDep

router = APIRouter(tags=["capabilities"])


def _manifest_for(runtime: BlenderRuntime) -> CapabilityManifest:
    return build_manifest(engine_version=runtime.probe_version())


@router.get(
    "/capabilities",
    response_model=CapabilityManifest,
    summary="What this renderer can produce",
)
async def capabilities(runtime: BlenderRuntimeDep) -> CapabilityManifest:
    try:
        return _manifest_for(runtime)
    except (BlenderInvocationError, FileNotFoundError) as exc:
        # A renderer that cannot reach Blender is unavailable, not broken input.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
