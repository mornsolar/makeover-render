"""Job queue port.

Decouples the HTTP job endpoints from arq's own types: the router only needs
to enqueue a render and read back a job's current state, and a port here is
what lets tests substitute an in-memory fake instead of a real Redis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Final, Protocol

from makeover_contracts.jobs import ArtifactBundle
from makeover_contracts.scene import SceneSpec

RENDER_JOB_FUNCTION_NAME: Final = "render_job"
"""The arq function name the worker registers and the queue enqueues by.

Lives here, not in ``interfaces/worker/tasks.py``, so the arq adapter can
depend on it without an import edge back into the worker/composition layer.
"""


class QueuedJobStatus(Enum):
    QUEUED = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()
    NOT_FOUND = auto()


@dataclass(frozen=True)
class QueuedJobInfo:
    """One job's state as the queue currently sees it."""

    status: QueuedJobStatus
    spec: SceneSpec | None
    created_at: datetime | None
    finished_at: datetime | None
    error: str | None
    result: ArtifactBundle | None


class JobQueue(Protocol):
    async def enqueue(self, job_id: str, spec: SceneSpec) -> None: ...

    async def status(self, job_id: str) -> QueuedJobInfo: ...
