"""arq ``WorkerSettings`` for the render job worker.

Run via ``uv run arq makeover_render.interfaces.worker.settings.WorkerSettings``.
A render is expensive to redo, so ``max_tries=1``: a failed job surfaces as
FAILED rather than silently retrying and doubling the render cost.
"""

from __future__ import annotations

from typing import ClassVar

from arq.connections import RedisSettings

from makeover_render.config.settings import get_settings
from makeover_render.interfaces.worker.tasks import render_job

_settings = get_settings()


class WorkerSettings:
    functions: ClassVar = [render_job]
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
    job_timeout = _settings.job_timeout_s
    max_tries = 1
