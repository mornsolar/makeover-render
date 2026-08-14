from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from makeover_contracts.jobs import ArtifactBundle, ArtifactKind, ArtifactRef

from makeover_render.application.ports.job_queue import QueuedJobInfo, QueuedJobStatus
from makeover_render.interfaces.api.app import create_app
from makeover_render.interfaces.api.deps import provide_job_queue
from tests.fakes.job_queue import FakeJobQueue
from tests.fakes.specs import UNIT_STOREFRONT_MATERIALS, make_spec

FAKE_SHA256 = "a" * 64


def _succeeded(result: ArtifactBundle) -> QueuedJobInfo:
    return QueuedJobInfo(
        status=QueuedJobStatus.SUCCEEDED,
        spec=make_spec(),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
        error=None,
        result=result,
    )


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

    def test_rewrites_artifact_uris_to_downloadable_routes(self):
        # A client outside this process cannot open a path on this machine's
        # own disk - the uri it receives must be something it can fetch.
        queue = FakeJobQueue()
        queue.jobs["job-1"] = _succeeded(_bundle())

        body = build_client(queue).get("/jobs/job-1").json()

        assert body["artifacts"]["gltf"]["uri"] == "/jobs/job-1/artifacts/gltf"
        assert body["artifacts"]["video"]["uri"] == "/jobs/job-1/artifacts/video"
        assert body["artifacts"]["thumbnail"]["uri"] == "/jobs/job-1/artifacts/thumbnail"

    def test_rewrites_still_uris_by_index(self):
        stills = (_artifact_ref(ArtifactKind.STILL), _artifact_ref(ArtifactKind.STILL))
        bundle = ArtifactBundle(
            gltf=_artifact_ref(ArtifactKind.GLTF),
            video=_artifact_ref(ArtifactKind.VIDEO),
            thumbnail=_artifact_ref(ArtifactKind.THUMBNAIL),
            stills=stills,
        )
        queue = FakeJobQueue()
        queue.jobs["job-1"] = _succeeded(bundle)

        body = build_client(queue).get("/jobs/job-1").json()

        assert body["artifacts"]["stills"][0]["uri"] == "/jobs/job-1/artifacts/stills/0"
        assert body["artifacts"]["stills"][1]["uri"] == "/jobs/job-1/artifacts/stills/1"


class TestGetArtifact:
    def test_downloads_an_artifacts_bytes(self, tmp_path):
        video_path = tmp_path / "animation.mp4"
        video_path.write_bytes(b"fake-mp4-bytes")
        bundle = ArtifactBundle(
            gltf=_artifact_ref(ArtifactKind.GLTF),
            video=ArtifactRef(
                kind=ArtifactKind.VIDEO,
                uri=str(video_path),
                media_type="video/mp4",
                size_bytes=14,
                sha256=FAKE_SHA256,
            ),
            thumbnail=_artifact_ref(ArtifactKind.THUMBNAIL),
        )
        queue = FakeJobQueue()
        queue.jobs["job-1"] = _succeeded(bundle)

        response = build_client(queue).get("/jobs/job-1/artifacts/video")

        assert response.status_code == 200
        assert response.content == b"fake-mp4-bytes"
        assert response.headers["content-type"] == "video/mp4"

    def test_downloads_a_still_by_index(self, tmp_path):
        still_path = tmp_path / "still_0.png"
        still_path.write_bytes(b"fake-png-bytes")
        bundle = ArtifactBundle(
            gltf=_artifact_ref(ArtifactKind.GLTF),
            video=_artifact_ref(ArtifactKind.VIDEO),
            thumbnail=_artifact_ref(ArtifactKind.THUMBNAIL),
            stills=(
                ArtifactRef(
                    kind=ArtifactKind.STILL,
                    uri=str(still_path),
                    media_type="image/png",
                    size_bytes=14,
                    sha256=FAKE_SHA256,
                ),
            ),
        )
        queue = FakeJobQueue()
        queue.jobs["job-1"] = _succeeded(bundle)

        response = build_client(queue).get("/jobs/job-1/artifacts/stills/0")

        assert response.status_code == 200
        assert response.content == b"fake-png-bytes"

    def test_returns_404_for_an_out_of_range_still_index(self):
        queue = FakeJobQueue()
        queue.jobs["job-1"] = _succeeded(_bundle())

        response = build_client(queue).get("/jobs/job-1/artifacts/stills/0")

        assert response.status_code == 404

    def test_returns_404_when_the_job_has_not_succeeded(self):
        queue = FakeJobQueue()
        queue.jobs["job-1"] = QueuedJobInfo(
            status=QueuedJobStatus.RUNNING,
            spec=make_spec(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            finished_at=None,
            error=None,
            result=None,
        )

        response = build_client(queue).get("/jobs/job-1/artifacts/gltf")

        assert response.status_code == 404

    def test_returns_404_for_an_unknown_job(self):
        response = build_client(FakeJobQueue()).get("/jobs/does-not-exist/artifacts/gltf")
        assert response.status_code == 404

    def test_returns_404_when_the_file_is_missing_from_disk(self):
        # _bundle()'s uri ("/out/gltf") was never actually written anywhere.
        queue = FakeJobQueue()
        queue.jobs["job-1"] = _succeeded(_bundle())

        response = build_client(queue).get("/jobs/job-1/artifacts/gltf")

        assert response.status_code == 404
