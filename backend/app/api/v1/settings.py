"""Provider configuration surfaces that never echo secrets."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_app_settings
from app.core.config import Settings
from app.schemas.provider import ProviderListResponse, ProviderTestResponse
from app.services.provider_registry import list_provider_statuses

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("/providers", response_model=ProviderListResponse)
def providers(settings: Annotated[Settings, Depends(get_app_settings)]) -> ProviderListResponse:
    return ProviderListResponse(items=list_provider_statuses(settings))


@router.post("/providers/{provider_code}/test", response_model=ProviderTestResponse)
def test_provider(
    provider_code: str,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ProviderTestResponse:
    providers_by_code = {item.provider_code: item for item in list_provider_statuses(settings)}
    provider = providers_by_code.get(provider_code)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    if not provider.enabled:
        raise HTTPException(status_code=409, detail="Provider is disabled")
    if provider.health_status != "healthy":
        raise HTTPException(status_code=503, detail="Provider health check failed")
    return ProviderTestResponse(
        provider_code=provider.provider_code,
        status="healthy",
        message="Offline provider is available.",
    )
