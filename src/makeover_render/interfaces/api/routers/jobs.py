"""Render job lifecycle: submit a ``SceneSpec``, poll for its outcome.

The actual render happens off the request thread, in a separate arq worker
process (see ``interfaces/worker``) - this router only ever enqueues and
reads back state that arq's own Redis-backed job records already hold.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from makeover_contracts.jobs import JobStatus, RenderJob
from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.job_queue import QueuedJobInfo, QueuedJobStatus
from makeover_render.application.use_cases.build_scene import check_buildable
from makeover_render.domain.errors import RenderError
from makeover_render.interfaces.api.deps import JobQueueDep

router = APIRouter(tags=["jobs"])

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
        artifacts=info.result,
    )
