"""``ArqJobQueue`` against a real, ephemeral redis-server.

Marked ``redis`` so the default CI job can skip it. Fakes prove the router's
own logic; this proves the arq API surface this adapter was written against
(``Job.status``/``Job.info``/``Job.result_info``) still behaves the way the
adapter assumes.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import time
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from arq import create_pool
from arq.connections import RedisSettings

from makeover_render.application.ports.job_queue import QueuedJobStatus
from makeover_render.infrastructure.jobs.arq_job_queue import ArqJobQueue
from tests.fakes.specs import make_spec

pytestmark = pytest.mark.redis


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def redis_port() -> int:
    if shutil.which("redis-server") is None:
        pytest.skip("redis-server not installed")
    return _free_port()


@pytest.fixture(scope="module", autouse=True)
def redis_server(redis_port: int):
    proc = subprocess.Popen(
        ["redis-server", "--port", str(redis_port), "--save", "", "--daemonize", "no"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", redis_port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.05)
        else:
            proc.terminate()
            pytest.fail(f"redis-server did not start listening on {redis_port}")
        yield
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest_asyncio.fixture
async def queue(redis_port: int) -> AsyncIterator[ArqJobQueue]:
    pool = await create_pool(RedisSettings(host="127.0.0.1", port=redis_port))
    try:
        yield ArqJobQueue(pool)
    finally:
        await pool.aclose()


class TestArqJobQueue:
    async def test_an_unenqueued_job_id_is_not_found(self, queue: ArqJobQueue):
        info = await queue.status("does-not-exist")
        assert info.status is QueuedJobStatus.NOT_FOUND

    async def test_an_enqueued_job_is_queued_before_a_worker_picks_it_up(self, queue: ArqJobQueue):
        spec = make_spec()
        await queue.enqueue("job-1", spec)

        info = await queue.status("job-1")

        assert info.status is QueuedJobStatus.QUEUED
        assert info.spec == spec
        assert info.created_at is not None
