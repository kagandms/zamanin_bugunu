from __future__ import annotations

from collections import deque
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest

from src.core.logger import logger
from src.services import content_service as content_module
from src.services.content_service import ContentService, ContentSourceFetchError


CATEGORIES = ("selected", "events", "births", "deaths")


class FakeResponse:
    def __init__(self, status_code: int, payload: Any = None, headers: dict[str, str] | None = None,
                 json_error: Exception | None = None) -> None:
        self.status_code = status_code
        self.headers = httpx.Headers(headers or {})
        self._payload = payload
        self._json_error = json_error

    def json(self) -> Any:
        if self._json_error:
            raise self._json_error
        return self._payload


class FakeAsyncClient:
    def __init__(self, responses: list[Any]) -> None:
        self.headers: dict[str, str] = {}
        self.responses = deque(responses)
        self.calls: list[tuple[str, float]] = []

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get(self, url: str, timeout: float) -> FakeResponse:
        self.calls.append((url.rsplit("/", 3)[-3], timeout))
        response = self.responses.popleft()
        if isinstance(response, Exception):
            raise response
        return response


def empty_response(category: str) -> FakeResponse:
    return FakeResponse(200, {category: []})


def install_client(monkeypatch: pytest.MonkeyPatch, client: FakeAsyncClient) -> None:
    monkeypatch.setattr(content_module.httpx, "AsyncClient", lambda: client)
    monkeypatch.setattr(content_module.asyncio, "sleep", AsyncMock())


@pytest.mark.asyncio
async def test_fetch_events_retries_429_then_keeps_successful_category(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = {"text": "A source-backed event."}
    client = FakeAsyncClient([
        FakeResponse(429, headers={"Retry-After": "0"}),
        FakeResponse(200, {"selected": [candidate]}),
        *[empty_response(category) for category in CATEGORIES[1:]],
    ])
    install_client(monkeypatch, client)

    events = await ContentService().fetch_events(10, 22)

    assert len(events) == 1
    assert events[0]["text"] == candidate["text"]
    assert events[0]["_category"] == "selected"
    assert [call[0] for call in client.calls] == ["selected", "selected", "events", "births", "deaths"]


@pytest.mark.asyncio
async def test_fetch_events_retries_timeout_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = {"text": "A source-backed event."}
    client = FakeAsyncClient([
        httpx.ReadTimeout("timed out"),
        FakeResponse(200, {"selected": [candidate]}),
        *[empty_response(category) for category in CATEGORIES[1:]],
    ])
    install_client(monkeypatch, client)

    events = await ContentService().fetch_events(10, 22)

    assert len(events) == 1
    assert len(client.calls) == 5


@pytest.mark.asyncio
async def test_fetch_events_stops_after_retry_limit_when_all_categories_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeAsyncClient([FakeResponse(503) for _ in range(len(CATEGORIES) * 2)])
    install_client(monkeypatch, client)

    with pytest.raises(ContentSourceFetchError, match="All event categories failed"):
        await ContentService().fetch_events(10, 22)

    assert len(client.calls) == len(CATEGORIES) * 2


@pytest.mark.asyncio
async def test_fetch_events_preserves_partial_success(monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = {"text": "An event returned by one valid category."}
    client = FakeAsyncClient([
        FakeResponse(200, {"selected": [candidate]}),
        FakeResponse(500), FakeResponse(500),
        empty_response("births"), empty_response("deaths"),
    ])
    install_client(monkeypatch, client)

    events = await ContentService().fetch_events(10, 22)

    assert [event["text"] for event in events] == [candidate["text"]]


@pytest.mark.asyncio
async def test_fetch_events_distinguishes_valid_empty_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeAsyncClient([empty_response(category) for category in CATEGORIES])
    install_client(monkeypatch, client)
    records: list[str] = []
    sink_id = logger.add(lambda message: records.append(str(message)), level="INFO")
    try:
        events = await ContentService().fetch_events(10, 22)
    finally:
        logger.remove(sink_id)

    assert events == []
    assert any("outcome=empty successful_categories=4" in record for record in records)


@pytest.mark.asyncio
async def test_fetch_events_classifies_malformed_json_and_schema_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeAsyncClient([
        FakeResponse(200, json_error=ValueError("invalid json")),
        FakeResponse(200, {"events": None}),
        empty_response("births"), empty_response("deaths"),
    ])
    install_client(monkeypatch, client)
    records: list[str] = []
    sink_id = logger.add(lambda message: records.append(str(message)), level="INFO")
    try:
        events = await ContentService().fetch_events(10, 22)
    finally:
        logger.remove(sink_id)

    assert events == []
    assert len(client.calls) == len(CATEGORIES)
    assert any("category=selected" in record and "error_class=invalid_json" in record for record in records)
    assert any("category=events" in record and "error_class=invalid_schema" in record for record in records)
    assert any("outcome=empty_partial" in record for record in records)


@pytest.mark.asyncio
async def test_fetch_events_does_not_retry_permanent_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeAsyncClient([
        FakeResponse(404),
        empty_response("events"), empty_response("births"), empty_response("deaths"),
    ])
    install_client(monkeypatch, client)

    events = await ContentService().fetch_events(10, 22)

    assert events == []
    assert len(client.calls) == len(CATEGORIES)


@pytest.mark.asyncio
async def test_fetch_events_does_not_exceed_retry_after_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeAsyncClient([
        FakeResponse(429, headers={"Retry-After": "30"}),
        empty_response("events"), empty_response("births"), empty_response("deaths"),
    ])
    install_client(monkeypatch, client)

    events = await ContentService().fetch_events(10, 22)

    assert events == []
    assert len(client.calls) == len(CATEGORIES)
