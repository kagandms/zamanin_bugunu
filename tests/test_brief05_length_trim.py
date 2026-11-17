"""Tests for Brief #5 T3: trimming trailing sentences from over-long source-bound model blocks."""
from __future__ import annotations

import re

import pytest

from src.core.config import Settings
from src.core.logger import logger
from src.services.ai_service import AIService
from src.services.content_guard import EventRewriteRequest
from src.services.source_context import complete_sentences

ANKARA_TEXT = "Ankara Antlaşması imzalandı."
GOOD_BLOCK_ONE = "1921'de TBMM ile Fransa arasında imzalanan Ankara Antlaşması, bu tarihte imzalandı."
GOOD_QUESTION = "Bu olayı daha önce duymuş muydunuz?"

SENTENCE_1 = (
    "Ankara Antlaşması, 1921 yılında TBMM ile Fransa arasında imzalandı ve "
    "güney sınırının taslak olarak belirlenmesi kararını doğrudan metne yazdı."
)
SENTENCE_2 = (
    "Antlaşma metninde Türk-Fransız Cephesi'ndeki tüm faaliyetlerin durdurulması ile "
    "sınırın kesin çizgisinin daha sonraki bir düzenlemeye bırakılması açıkça yer alır."
)
SENTENCE_3 = (
    "Bu düzenleme ile birlikte güney cephesindeki tüm askeri hareketlilik tamamen sona ermiş ve "
    "iki taraf arasındaki resmi diplomatik görüşme süreci bu antlaşma üzerinden doğrudan başlamıştır."
)
LONG_SUMMARY = f"{SENTENCE_1} {SENTENCE_2} {SENTENCE_3}"


def _request(source_context: str | None = LONG_SUMMARY) -> EventRewriteRequest:
    return EventRewriteRequest(
        original_text=ANKARA_TEXT,
        formatted_date="20.10.1921",
        year="1921",
        source_title="Ankara Antlaşması",
        source_url="https://tr.wikipedia.org/wiki/Ankara_Antla%C5%9Fmas%C4%B1",
        source_context=source_context,
    )


def _body(*blocks: str, emoji: str = "🏛️") -> str:
    return f"EMOJI: {emoji}\n---\n" + "\n---\n".join(blocks)


def _use_scripted_responses(
    monkeypatch: pytest.MonkeyPatch,
    script: list[tuple[int, str]],
    extra: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    """Each HTTP attempt gets the next scripted (status, content); every request body is recorded."""
    settings_kwargs: dict[str, object] = {
        "OPENROUTER_API_KEY": "mock-key",
        "AI_MODEL": "model-1",
        "BACKUP_MODEL": "model-2",
        "GEMINI_API_KEY": None,
        "MAX_THREAD_LENGTH": 500,
    }
    settings_kwargs.update(extra or {})
    monkeypatch.setattr("src.services.ai_service.settings", Settings(**settings_kwargs))
    payloads: list[dict[str, object]] = []

    class Response:
        def __init__(self, status: int, content: str) -> None:
            self.status_code = status
            self._content = content
            self.text = content

        def json(self) -> dict[str, object]:
            return {
                "model": "scripted",
                "modelVersion": "scripted-gemini",
                "choices": [{"message": {"content": self._content}}],
                "candidates": [{"content": {"parts": [{"text": self._content}]}}],
            }

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> Response:
            payloads.append(kwargs["json"])
            status, content = script[min(len(payloads) - 1, len(script) - 1)]
            return Response(status, content)

    monkeypatch.setattr("src.services.ai_service.httpx.AsyncClient", Client)
    return payloads


@pytest.mark.asyncio
async def test_block_one_with_extra_third_sentence_over_limit_is_trimmed_and_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_block_one = f"{SENTENCE_1} {SENTENCE_2} {SENTENCE_3} #tarih"
    assert len(original_block_one) > 480
    payloads = _use_scripted_responses(
        monkeypatch,
        [(200, _body(original_block_one, GOOD_QUESTION))],
    )
    logs: list[str] = []
    sink_id = logger.add(lambda message: logs.append(str(message)), level="INFO")
    try:
        service = AIService()
        parts, _, _ = await service.rewrite_event_safe(_request())
    finally:
        logger.remove(sink_id)

    assert len(payloads) == 1
    assert service.last_generation_type == "ai_source_bound"
    assert len(parts[0]) <= 480
    assert SENTENCE_1 in parts[0]
    assert SENTENCE_3 not in parts[0]
    assert parts[0].rstrip().endswith("#tarih")

    body_after_header = parts[0].split("\n\n", 1)[1]
    body_without_tag = re.sub(r"\s*#tarih\b", "", body_after_header).strip()
    kept_sentences = complete_sentences(body_without_tag)
    assert kept_sentences
    assert all(sentence in original_block_one for sentence in kept_sentences)
    assert any("Source-bound trimmed: block=1 dropped_sentences=1" in entry for entry in logs)


@pytest.mark.asyncio
async def test_block_one_first_sentence_alone_over_limit_is_rejected_and_next_model_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oversized_first_sentence = (
        "Ankara Antlaşması, 1921 yılında TBMM ile Fransa arasında imzalandı ve "
        "güney sınırının taslak olarak belirlenmesi kararını doğrudan metne yazdı, "
        "Türk-Fransız Cephesi'ndeki tüm faaliyetlerin durdurulması ile sınırın kesin "
        "çizgisinin daha sonraki bir düzenlemeye bırakılması açıkça yer aldı ve "
        "cephedeki askeri hareketlilik tamamen sona ermiş olup iki taraf arasındaki "
        "diplomatik süreç bu antlaşma üzerinden doğrudan başlamış oldu ve sınırın "
        "kesin çizgisi daha sonraki bir düzenlemeye bırakıldı."
    )
    assert len(oversized_first_sentence) > 480
    overlong_block = f"{oversized_first_sentence} {SENTENCE_2}"
    payloads = _use_scripted_responses(
        monkeypatch,
        [
            (200, _body(overlong_block, GOOD_QUESTION)),
            (200, _body(GOOD_BLOCK_ONE, GOOD_QUESTION)),
        ],
    )
    logs: list[str] = []
    sink_id = logger.add(lambda message: logs.append(str(message)), level="INFO")
    try:
        service = AIService()
        parts, _, _ = await service.rewrite_event_safe(_request())
    finally:
        logger.remove(sink_id)

    assert len(payloads) == 2
    assert service.last_generation_type == "ai_source_bound"
    assert GOOD_BLOCK_ONE in parts[0]
    assert not any("Source-bound trimmed:" in entry for entry in logs)

    # When every model returns an oversized first sentence, fallback records the "length" rejection.
    _use_scripted_responses(
        monkeypatch,
        [
            (200, _body(overlong_block, GOOD_QUESTION)),
            (200, _body(overlong_block, GOOD_QUESTION)),
        ],
    )
    fallback_service = AIService()
    await fallback_service.rewrite_event_safe(_request())
    assert fallback_service.last_generation_type.startswith("source_fallback:length")


@pytest.mark.asyncio
async def test_block_within_limit_is_unchanged_and_logs_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_scripted_responses(
        monkeypatch,
        [(200, _body(GOOD_BLOCK_ONE, GOOD_QUESTION))],
    )
    logs: list[str] = []
    sink_id = logger.add(lambda message: logs.append(str(message)), level="INFO")
    try:
        service = AIService()
        parts, _, _ = await service.rewrite_event_safe(_request())
    finally:
        logger.remove(sink_id)

    assert service.last_generation_type == "ai_source_bound"
    assert GOOD_BLOCK_ONE in parts[0]
    assert not any("Source-bound trimmed:" in entry for entry in logs)


def test_trimming_never_touches_question_block() -> None:
    overlong_question = (
        "Bu antlaşma hakkında ne düşünüyorsunuz? "
        + " ".join(["Bu soruyu daha önce duymuş muydunuz?"] * 15)
    )
    assert len(overlong_question) > 480
    logs: list[str] = []
    sink_id = logger.add(lambda message: logs.append(str(message)), level="INFO")
    try:
        trimmed = AIService._trim_overlong_blocks(
            [GOOD_BLOCK_ONE, overlong_question],
            "🏛️",
            "20.10.1921",
            480,
        )
    finally:
        logger.remove(sink_id)

    assert trimmed[0] == GOOD_BLOCK_ONE
    assert trimmed[1] == overlong_question
    assert not any("Source-bound trimmed:" in entry for entry in logs)
