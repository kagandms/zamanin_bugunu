"""Shared test setup."""
from types import SimpleNamespace

import pytest


class _OfflineHttpClient:
    """Stands in for httpx.AsyncClient so no test can reach a model provider by accident.

    The project's .env may hold a live OpenRouter key; source-bound generation now
    calls the model for profile-less events, so every model attempt must fail offline.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def __aenter__(self) -> "_OfflineHttpClient":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def post(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError("offline_test_client")


@pytest.fixture(autouse=True)
def _block_live_model_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.services.ai_service.httpx", SimpleNamespace(AsyncClient=_OfflineHttpClient))
