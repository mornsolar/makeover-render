"""Render job lifecycle: submit a ``SceneSpec``, poll for its outcome.

The actual render happens off the request thread, in a separate arq worker
process (see ``interfaces/worker``) - this router only ever enqueues and
reads back state that arq's own Redis-backed job records already hold.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from makeover_contracts.jobs import ArtifactBundle, ArtifactRef, JobStatus, RenderJob
from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.job_queue import JobQueue, QueuedJobInfo, QueuedJobStatus
from makeover_render.application.use_cases.build_scene import check_buildable
from makeover_render.domain.errors import RenderError
from makeover_render.interfaces.api.deps import JobQueueDep

router = APIRouter(tags=["jobs"])

_ArtifactKindPath = Literal["gltf", "video", "thumbnail"]

_KIND_ACCESSOR: dict[str, Callable[[ArtifactBundle], ArtifactRef]] = {
    "gltf": lambda bundle: bundle.gltf,
    "video": lambda bundle: bundle.video,
    "thumbnail": lambda bundle: bundle.thumbnail,
}

_STATUS_MAP = {
    QueuedJobStatus.QUEUED: JobStatus.QUEUED,
    QueuedJobStatus.RUNNING: JobStatus.RUNNING,
    QueuedJobStatus.SUCCEEDED: JobStatus.SUCCEEDED,
    QueuedJobStatus.FAILED: JobStatus.FAILED,
}


@router.post(
    "/jobs",
    response_model=RenderJob,
    status_code=status.HTTP_201_CREATED,
    summary="Enqueue a render",
)
async def create_job(spec: SceneSpec, job_queue: JobQueueDep) -> RenderJob:
    try:
        check_buildable(spec)
    except RenderError as exc:
        # A spec this registry already knows it cannot build shouldn't
        # occupy a worker slot just to fail there with the same error.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    job_id = uuid4().hex
    await job_queue.enqueue(job_id, spec)
    info = await job_queue.status(job_id)
    return _to_render_job(job_id, info)


@router.get("/jobs/{job_id}", response_model=RenderJob, summary="Poll a render job")
async def get_job(job_id: str, job_queue: JobQueueDep) -> RenderJob:
    info = await job_queue.status(job_id)
    return _to_render_job(job_id, info)


@router.get("/jobs/{job_id}/artifacts/{kind}", summary="Download one of a job's artifact files")
async def get_artifact(
    job_id: str, kind: _ArtifactKindPath, job_queue: JobQueueDep
) -> FileResponse:
    bundle = await _require_artifacts(job_id, job_queue)
    return _file_response(job_id, _KIND_ACCESSOR[kind](bundle))


@router.get(
    "/jobs/{job_id}/artifacts/stills/{index}", summary="Download one of a job's still frames"
)
async def get_still_artifact(job_id: str, index: int, job_queue: JobQueueDep) -> FileResponse:
    bundle = await _require_artifacts(job_id, job_queue)
    if index < 0 or index >= len(bundle.stills):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"no still {index} for job {job_id!r}"
        )
    return _file_response(job_id, bundle.stills[index])


async def _require_artifacts(job_id: str, job_queue: JobQueue) -> ArtifactBundle:
    info = await job_queue.status(job_id)
    if info.status is not QueuedJobStatus.SUCCEEDED or info.result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"no artifacts for job {job_id!r}"
        )
    return info.result


def _file_response(job_id: str, ref: ArtifactRef) -> FileResponse:
    # info.result still carries the worker's own local path here - only the
    # RenderJob a client receives back gets its uri rewritten to this route,
    # so this read is always relative to this process's own working
    # directory, exactly where RunRenderJob wrote the file.
    path = Path(ref.uri)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"artifact for job {job_id!r} is no longer on disk",
        )
    return FileResponse(path, media_type=ref.media_type)


def _to_render_job(job_id: str, info: QueuedJobInfo) -> RenderJob:
    if info.status is QueuedJobStatus.NOT_FOUND or info.spec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"no job {job_id!r}")
    return RenderJob(
        id=job_id,
        spec=info.spec,
        status=_STATUS_MAP[info.status],
        created_at=info.created_at or datetime.now(UTC),
        finished_at=info.finished_at,
        error=info.error,
        artifacts=_public_artifacts(job_id, info.result) if info.result is not None else None,
    )


def _public_artifacts(job_id: str, bundle: ArtifactBundle) -> ArtifactBundle:
    # A client outside this process cannot open a path on this machine's own
    # disk - hand back a URI it can actually fetch (this router's own
    # download routes) instead of the worker's local filesystem path.
    return ArtifactBundle(
        gltf=_public_ref(job_id, bundle.gltf, "gltf"),
        video=_public_ref(job_id, bundle.video, "video"),
        thumbnail=_public_ref(job_id, bundle.thumbnail, "thumbnail"),
        stills=tuple(
            _public_ref(job_id, still, f"stills/{index}")
            for index, still in enumerate(bundle.stills)
        ),
    )


def _public_ref(job_id: str, ref: ArtifactRef, path_suffix: str) -> ArtifactRef:
    return ref.model_copy(update={"uri": f"/jobs/{job_id}/artifacts/{path_suffix}"})
