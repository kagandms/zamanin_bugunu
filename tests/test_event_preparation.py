from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.event_preparation import PreparationServices, _select_event


OBSERVED_AT = datetime(2026, 10, 22)


def candidate(text: str = "Ankara Antlaşması 1921'de imzalandı.") -> dict[str, object]:
    return {"text": text, "year": 1921, "pages": [{"title": "Ankara Antlaşması"}]}


def services_for(
    candidates: list[dict[str, object]],
    rewrite: AsyncMock,
    selector: AsyncMock | None = None,
) -> PreparationServices:
    content = SimpleNamespace(
        fetch_events=AsyncMock(return_value=candidates),
        select_best_event=selector or AsyncMock(return_value=candidates[0] if candidates else None),
    )
    return PreparationServices(content=content, ai=rewrite, image=SimpleNamespace())


class HistoryStub:
    def __init__(self, used: list[str] | None = None) -> None:
        self.used = used or []

    async def get_todays_posts(self) -> list[str]:
        return list(self.used)

    async def exists(self, text: str) -> bool:
        return text in self.used


@pytest.mark.asyncio
async def test_accepts_meaningful_short_source_fallback_without_padding() -> None:
    event = candidate()
    ai = SimpleNamespace(
        rewrite_event_safe=AsyncMock(return_value=(
            ["🕊️ Tarihte Bugün (22.10.1921)\n\nAnkara Antlaşması 1921'de imzalandı."], [], None,
        )),
        last_generation_type="source_fallback:unprofiled_claims_unverified:thin_source",
        last_validation_reason="unprofiled_claims_unverified",
    )
    services = services_for([event], ai.rewrite_event_safe)
    services = PreparationServices(services.content, ai, services.image)

    result = await _select_event(services, HistoryStub(), OBSERVED_AT)

    assert result.blocks[0].endswith("Ankara Antlaşması 1921'de imzalandı.")
    assert len("".join(result.blocks)) < 80
    ai.rewrite_event_safe.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("blocks", "reason"),
    [([], "empty_output"), (["  "], "empty_output"),
     (["🕊️ Tarihte Bugün (22.10.1921)"], "header_only"),
     (["🕊️ Tarihte Bugün (22.10.1921)\n\nAnkara Antlaşması"], "title_only")],
)
async def test_rejects_empty_header_and_title_only_output(
    blocks: list[str], reason: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = candidate("Ankara Antlaşması")
    ai = SimpleNamespace(
        rewrite_event_safe=AsyncMock(return_value=(blocks, [], None)),
        last_generation_type="source_fallback:unprofiled_claims_unverified:thin_source",
        last_validation_reason="unprofiled_claims_unverified",
    )
    selector = AsyncMock(side_effect=[event, None])
    diagnostic_logger = Mock()
    monkeypatch.setattr("src.event_preparation.logger", diagnostic_logger)
    services = PreparationServices(SimpleNamespace(fetch_events=AsyncMock(return_value=[event]),
        select_best_event=selector), ai, SimpleNamespace())

    with pytest.raises(RuntimeError, match="No event candidate passed"):
        await _select_event(services, HistoryStub(), OBSERVED_AT)

    assert reason in str(diagnostic_logger.info.call_args)


@pytest.mark.asyncio
async def test_used_candidate_is_not_rewritten_and_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    event = candidate()
    ai = SimpleNamespace(rewrite_event_safe=AsyncMock())
    selector = AsyncMock(side_effect=lambda items, used: next(
        (item for item in items if item["text"] not in used), None,
    ))
    diagnostic_logger = Mock()
    monkeypatch.setattr("src.event_preparation.logger", diagnostic_logger)
    services = PreparationServices(SimpleNamespace(fetch_events=AsyncMock(return_value=[event]),
        select_best_event=selector), ai, SimpleNamespace())

    with pytest.raises(RuntimeError, match="No event candidate passed"):
        await _select_event(services, HistoryStub([event["text"]]), OBSERVED_AT)

    ai.rewrite_event_safe.assert_not_awaited()
    assert "all_candidates_used" in str(diagnostic_logger.warning.call_args)


@pytest.mark.asyncio
async def test_advances_to_another_candidate_after_short_non_fallback_rejection() -> None:
    first = candidate("İlk Antlaşma imzalandı.")
    second = candidate("İkinci Antlaşma 1921'de imzalandı.")
    outputs = iter([
        (["Kısa model çıktısı."], [], None),
        (["🕊️ Tarihte Bugün (22.10.1921)\n\nİkinci Antlaşma 1921'de imzalandı."], [], None),
    ])
    call_count = 0

    async def rewrite(*_: object) -> tuple[list[str], list[str], None]:
        nonlocal call_count
        call_count += 1
        ai.last_generation_type = (
            "model" if call_count == 1 else "source_fallback:unprofiled_claims_unverified:thin_source"
        )
        return next(outputs)

    ai = SimpleNamespace(
        rewrite_event_safe=AsyncMock(side_effect=rewrite),
        last_generation_type="model",
        last_validation_reason="output_too_short",
    )
    seen_used: list[list[str]] = []

    async def select(items: list[dict[str, object]], used: list[str]) -> dict[str, object] | None:
        seen_used.append(list(used))
        return next((item for item in items if item["text"] not in used), None)

    services = PreparationServices(SimpleNamespace(fetch_events=AsyncMock(return_value=[first, second]),
        select_best_event=AsyncMock(side_effect=select)), ai, SimpleNamespace())

    result = await _select_event(services, HistoryStub(), OBSERVED_AT)

    assert result.candidate["text"] == second["text"]
    assert seen_used[1] == [first["text"]]


@pytest.mark.asyncio
async def test_reports_when_selector_returns_no_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    event = candidate()
    ai = SimpleNamespace(rewrite_event_safe=AsyncMock())
    selector = AsyncMock(return_value=None)
    diagnostic_logger = Mock()
    monkeypatch.setattr("src.event_preparation.logger", diagnostic_logger)
    services = PreparationServices(SimpleNamespace(fetch_events=AsyncMock(return_value=[event]),
        select_best_event=selector), ai, SimpleNamespace())

    with pytest.raises(RuntimeError, match="No event candidate passed"):
        await _select_event(services, HistoryStub(), OBSERVED_AT)

    assert "selector_returned_none" in str(diagnostic_logger.warning.call_args)
    ai.rewrite_event_safe.assert_not_awaited()


@pytest.mark.asyncio
async def test_reports_empty_candidate_list_separately(monkeypatch: pytest.MonkeyPatch) -> None:
    ai = SimpleNamespace(rewrite_event_safe=AsyncMock())
    selector = AsyncMock(return_value=None)
    diagnostic_logger = Mock()
    monkeypatch.setattr("src.event_preparation.logger", diagnostic_logger)
    services = PreparationServices(SimpleNamespace(fetch_events=AsyncMock(return_value=[]),
        select_best_event=selector), ai, SimpleNamespace())

    with pytest.raises(RuntimeError, match="No event candidate passed"):
        await _select_event(services, HistoryStub(), OBSERVED_AT)

    assert "no_candidates" in str(diagnostic_logger.warning.call_args)
    ai.rewrite_event_safe.assert_not_awaited()
