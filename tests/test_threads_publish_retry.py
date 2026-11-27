from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import src.services.threads_service as threads_module
from src.services.threads_service import ThreadsService


def _ready_state() -> SimpleNamespace:
    return SimpleNamespace(is_ready=True, status="finished", error_detail=None)


@pytest.mark.asyncio
async def test_publish_retries_once_on_4279009_and_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_mock = AsyncMock()
    monkeypatch.setattr(threads_module.asyncio, "sleep", sleep_mock)

    service = ThreadsService.__new__(ThreadsService)
    publish_mock = AsyncMock(
        side_effect=[
            (None, False, 'publish_rejected:{"code": 24, "error_subcode": 4279009}'),
            ("post-123", False, None),
        ]
    )
    monkeypatch.setattr(service, "_publish_container", publish_mock)

    readiness, post_id, is_uncertain, error = await service._publish_container_when_ready(
        "container-1",
        readiness=_ready_state(),
    )

    assert readiness.is_ready is True
    assert post_id == "post-123"
    assert is_uncertain is False
    assert error is None
    assert publish_mock.await_count == 2
    sleep_mock.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_publish_does_not_retry_on_other_subcode(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_mock = AsyncMock()
    monkeypatch.setattr(threads_module.asyncio, "sleep", sleep_mock)

    service = ThreadsService.__new__(ThreadsService)
    publish_mock = AsyncMock(
        return_value=(None, False, 'publish_rejected:{"code": 24, "error_subcode": 9999999}')
    )
    monkeypatch.setattr(service, "_publish_container", publish_mock)

    _, post_id, is_uncertain, error = await service._publish_container_when_ready(
        "container-1",
        readiness=_ready_state(),
    )

    assert post_id is None
    assert is_uncertain is False
    assert error == 'publish_rejected:{"code": 24, "error_subcode": 9999999}'
    assert publish_mock.await_count == 1
    sleep_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_does_not_retry_on_uncertain_result(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_mock = AsyncMock()
    monkeypatch.setattr(threads_module.asyncio, "sleep", sleep_mock)

    service = ThreadsService.__new__(ThreadsService)
    publish_mock = AsyncMock(return_value=(None, True, "publish_timeout"))
    monkeypatch.setattr(service, "_publish_container", publish_mock)

    _, post_id, is_uncertain, error = await service._publish_container_when_ready(
        "container-1",
        readiness=_ready_state(),
    )

    assert post_id is None
    assert is_uncertain is True
    assert error == "publish_timeout"
    assert publish_mock.await_count == 1
    sleep_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_skips_retry_when_authorize_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep_mock = AsyncMock()
    monkeypatch.setattr(threads_module.asyncio, "sleep", sleep_mock)

    service = ThreadsService.__new__(ThreadsService)
    publish_mock = AsyncMock(
        return_value=(None, False, 'publish_rejected:{"code": 24, "error_subcode": 4279009}')
    )
    monkeypatch.setattr(service, "_publish_container", publish_mock)
    authorize_mock = AsyncMock(side_effect=[True, False])

    readiness, post_id, is_uncertain, error = await service._publish_container_when_ready(
        "container-1",
        readiness=_ready_state(),
        authorize=authorize_mock,
    )

    assert readiness.status == "window_closed"
    assert post_id is None
    assert is_uncertain is False
    assert error == "skip_window_closed"
    assert publish_mock.await_count == 1
    assert authorize_mock.await_count == 2
    sleep_mock.assert_awaited_once_with(5)
