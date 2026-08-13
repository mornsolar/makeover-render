"""Liveness endpoint."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from makeover_contracts.version import CONTRACT_VERSION
from pydantic import BaseModel

from makeover_render.interfaces.api.deps import SettingsDep

router = APIRouter(tags=["ops"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str
    contract_version: str


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health(settings: SettingsDep) -> HealthResponse:
    # Deliberately does not shell out to Blender: liveness must stay cheap so a
    # busy render worker is never marked unhealthy by an orchestrator.
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.environment,
        contract_version=CONTRACT_VERSION,
    )
