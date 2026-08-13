from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from makeover_contracts.version import CONTRACT_VERSION

from makeover_render.config.settings import Settings, get_settings
from makeover_render.infrastructure.blender.runtime import (
    BlenderInvocationError,
    BlenderRuntime,
)
from makeover_render.interfaces.api.app import create_app
from makeover_render.interfaces.api.deps import provide_blender_runtime


class FakeRuntime(BlenderRuntime):
    """Stands in for Blender so API tests never launch a 3D application."""

    def __init__(self, version: str = "5.2.0", fail: bool = False) -> None:
        super().__init__(executable=Path("/fake/blender"))
        object.__setattr__(self, "_version", version)
        object.__setattr__(self, "_fail", fail)

    def probe_version(self) -> str:
        if self._fail:  # type: ignore[attr-defined]
            raise BlenderInvocationError("Could not launch /fake/blender")
        return self._version  # type: ignore[attr-defined,no-any-return]


def build_client(runtime: BlenderRuntime | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(environment="test")
    app.dependency_overrides[provide_blender_runtime] = lambda: runtime or FakeRuntime()
    return TestClient(app)


class TestHealth:
    def test_returns_ok(self):
        response = build_client().get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_reports_the_contract_version(self):
        assert build_client().get("/health").json()["contract_version"] == CONTRACT_VERSION

    def test_stays_healthy_even_when_blender_is_unreachable(self):
        # Liveness must not depend on Blender, or a busy worker gets killed.
        response = build_client(FakeRuntime(fail=True)).get("/health")
        assert response.status_code == 200


class TestCapabilities:
    def test_advertises_the_probed_engine_version(self):
        response = build_client(FakeRuntime(version="5.2.0")).get("/capabilities")
        assert response.status_code == 200
        assert response.json()["engine_version"] == "5.2.0"

    def test_lists_templates_and_material_families(self):
        body = build_client().get("/capabilities").json()
        assert len(body["templates"]) >= 1
        assert "timber" in body["material_families"]

    def test_reports_503_when_blender_cannot_be_reached(self):
        # An unreachable renderer is unavailable, not a bad request.
        response = build_client(FakeRuntime(fail=True)).get("/capabilities")
        assert response.status_code == 503
