"""A ``JobQueue`` double backed by an in-memory dict instead of Redis."""

from __future__ import annotations

from makeover_contracts.scene import SceneSpec

from makeover_render.application.ports.job_queue import QueuedJobInfo, QueuedJobStatus

_NOT_FOUND = QueuedJobInfo(
    status=QueuedJobStatus.NOT_FOUND,
    spec=None,
    created_at=None,
    finished_at=None,
    error=None,
    result=None,
)


class FakeJobQueue:
    """Every enqueued job starts QUEUED; tests mutate ``jobs[job_id]`` to move
    a job through RUNNING/SUCCEEDED/FAILED without a real worker."""

    def __init__(self) -> None:
        self.jobs: dict[str, QueuedJobInfo] = {}
        self.enqueued: list[tuple[str, SceneSpec]] = []

    async def enqueue(self, job_id: str, spec: SceneSpec) -> None:
        self.enqueued.append((job_id, spec))
        self.jobs[job_id] = QueuedJobInfo(
            status=QueuedJobStatus.QUEUED,
            spec=spec,
            created_at=None,
            finished_at=None,
            error=None,
            result=None,
        )

    async def status(self, job_id: str) -> QueuedJobInfo:
        return self.jobs.get(job_id, _NOT_FOUND)
