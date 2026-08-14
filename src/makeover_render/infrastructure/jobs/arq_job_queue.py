"""arq-backed ``JobQueue`` adapter.

Deliberately keeps no state of its own: arq's own Redis-backed job hash and
result record are the single source of truth for a job's lifecycle. This
adapter's only job is translating arq's ``JobStatus``/``JobDef``/``JobResult``
into ``QueuedJobInfo``.
"""

from __future__ import annotations

from arq import ArqRedis
from arq.jobs import Job
from arq.jobs import JobStatus as ArqJobStatus
from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.job_queue import (
    RENDER_JOB_FUNCTION_NAME,
    QueuedJobInfo,
    QueuedJobStatus,
)

_STATUS_MAP = {
    ArqJobStatus.deferred: QueuedJobStatus.QUEUED,
    ArqJobStatus.queued: QueuedJobStatus.QUEUED,
    ArqJobStatus.in_progress: QueuedJobStatus.RUNNING,
}

_NOT_FOUND = QueuedJobInfo(
    status=QueuedJobStatus.NOT_FOUND,
    spec=None,
    created_at=None,
    finished_at=None,
    error=None,
    result=None,
)


class ArqJobQueue:
    def __init__(self, pool: ArqRedis) -> None:
        self._pool = pool

    async def enqueue(self, job_id: str, spec: SceneSpec) -> None:
        await self._pool.enqueue_job(RENDER_JOB_FUNCTION_NAME, spec, _job_id=job_id)

    async def status(self, job_id: str) -> QueuedJobInfo:
        job = Job(job_id, redis=self._pool)
        current = await job.status()
        if current is ArqJobStatus.not_found:
            return _NOT_FOUND
        if current is ArqJobStatus.complete:
            return await self._finished(job)

        info = await job.info()
        if info is None:
            return _NOT_FOUND
        spec = info.args[0] if info.args else None
        return QueuedJobInfo(
            status=_STATUS_MAP[current],
            spec=spec,
            created_at=info.enqueue_time,
            finished_at=None,
            error=None,
            result=None,
        )

    async def _finished(self, job: Job) -> QueuedJobInfo:
        result_info = await job.result_info()
        if result_info is None:
            # Completed, but the result already expired past arq's keep_result
            # window - indistinguishable from never having existed to a caller.
            return _NOT_FOUND
        spec = result_info.args[0] if result_info.args else None
        if result_info.success:
            return QueuedJobInfo(
                status=QueuedJobStatus.SUCCEEDED,
                spec=spec,
                created_at=result_info.enqueue_time,
                finished_at=result_info.finish_time,
                error=None,
                result=result_info.result,
            )
        return QueuedJobInfo(
            status=QueuedJobStatus.FAILED,
            spec=spec,
            created_at=result_info.enqueue_time,
            finished_at=result_info.finish_time,
            error=str(result_info.result),
            result=None,
        )
