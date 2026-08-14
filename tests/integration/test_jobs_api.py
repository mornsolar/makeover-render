from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from makeover_contracts.jobs import ArtifactBundle, ArtifactKind, ArtifactRef

from makeover_render.application.ports.job_queue import QueuedJobInfo, QueuedJobStatus
from makeover_render.interfaces.api.app import create_app
from makeover_render.interfaces.api.deps import provide_job_queue
from tests.fakes.job_queue import FakeJobQueue
from tests.fakes.specs import UNIT_STOREFRONT_MATERIALS, make_spec


def build_client(job_queue: FakeJobQueue) -> TestClient:
    app = create_app()
    app.dependency_overrides[provide_job_queue] = lambda: job_queue
    return TestClient(app)


def _artifact_ref(kind: ArtifactKind) -> ArtifactRef:
    return ArtifactRef(
        kind=kind,
        uri=f"/out/{kind.value}",
        media_type="application/octet-stream",
        size_bytes=1,
        sha256="a" * 64,
    )


def _bundle() -> ArtifactBundle:
    return ArtifactBundle(
        gltf=_artifact_ref(ArtifactKind.GLTF),
        video=_artifact_ref(ArtifactKind.VIDEO),
        thumbnail=_artifact_ref(ArtifactKind.THUMBNAIL),
    )


class TestCreateJob:
    def test_enqueues_and_returns_a_queued_job(self):
        queue = FakeJobQueue()
        response = build_client(queue).post("/jobs", json=make_spec().model_dump(mode="json"))
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "queued"
        assert body["spec"]["template_id"] == "unit-storefront"
        assert len(queue.enqueued) == 1

    def test_rejects_a_spec_missing_a_required_material_before_enqueuing(self):
        queue = FakeJobQueue()
        incomplete = tuple(a for a in UNIT_STOREFRONT_MATERIALS if a.slot.value != "ground")
        spec = make_spec(materials=incomplete)

        response = build_client(queue).post("/jobs", json=spec.model_dump(mode="json"))

        assert response.status_code == 400
        assert "ground" in response.json()["detail"]
        assert queue.enqueued == []

    def test_rejects_an_unknown_template_before_enqueuing(self):
        queue = FakeJobQueue()
        spec = make_spec(template_id="does-not-exist")

        response = build_client(queue).post("/jobs", json=spec.model_dump(mode="json"))

        assert response.status_code == 400
        assert queue.enqueued == []


class TestGetJob:
    def test_returns_404_for_an_unknown_job(self):
        response = build_client(FakeJobQueue()).get("/jobs/does-not-exist")
        assert response.status_code == 404

    def test_reports_a_running_job(self):
        queue = FakeJobQueue()
        queue.jobs["job-1"] = QueuedJobInfo(
            status=QueuedJobStatus.RUNNING,
            spec=make_spec(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            finished_at=None,
            error=None,
            result=None,
        )

        response = build_client(queue).get("/jobs/job-1")

        assert response.status_code == 200
        assert response.json()["status"] == "running"
        assert response.json()["finished_at"] is None

    def test_reports_a_succeeded_job_with_its_artifacts(self):
        queue = FakeJobQueue()
        queue.jobs["job-1"] = QueuedJobInfo(
            status=QueuedJobStatus.SUCCEEDED,
            spec=make_spec(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            finished_at=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
            error=None,
            result=_bundle(),
        )

        response = build_client(queue).get("/jobs/job-1")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "succeeded"
        assert body["artifacts"]["gltf"]["kind"] == "gltf"

    def test_reports_a_failed_job_with_its_error(self):
        queue = FakeJobQueue()
        queue.jobs["job-1"] = QueuedJobInfo(
            status=QueuedJobStatus.FAILED,
            spec=make_spec(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            finished_at=datetime(2026, 1, 1, 0, 1, tzinfo=UTC),
            error="Blender exited 1",
            result=None,
        )

        response = build_client(queue).get("/jobs/job-1")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "failed"
        assert body["error"] == "Blender exited 1"
