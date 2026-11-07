"""Source-bound generation for events without a curated fact profile (event-rewrite-v5)."""
from __future__ import annotations

import asyncio
import time

import pytest

from src.core.config import Settings
from src.event_preparation import _used_source_sentences
from src.services.ai_service import AIService
from src.services.content_guard import EventRewriteRequest, validate_source_bound_content
from src.services.content_service import ContentService
from src.services.source_context import select_event_summary

ANKARA_TEXT = "Ankara Antlaşması imzalandı."
ANKARA_SUMMARY = "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı."
RICH_SUMMARY = (
    "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı. "
    "Antlaşma metninde güney sınırının taslak olarak belirlenmesi kararı yer alır. "
    "Ankara Antlaşması, Türk-Fransız Cephesi'ndeki faaliyetleri durdurmuştur. "
    "Sınırın kesin çizgisi ise daha sonraki bir düzenlemeye bırakılmıştır."
)
GOOD_BLOCK_ONE = "1921'de TBMM ile Fransa arasında imzalanan Ankara Antlaşması, bu tarihte imzalandı."
GOOD_QUESTION = "Bu olayı daha önce duymuş muydunuz?"


def _request(source_context: str | None = ANKARA_SUMMARY) -> EventRewriteRequest:
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


LAST_REQUESTS: list[dict[str, object]] = []


def _use_scripted_responses(
    monkeypatch: pytest.MonkeyPatch,
    script: list[tuple[int, str]],
    extra: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    """Each HTTP attempt gets the next scripted (status, content); every request body is recorded."""
    settings_kwargs: dict[str, object] = {
        "OPENROUTER_API_KEY": "mock-key", "AI_MODEL": "model-1", "BACKUP_MODEL": "model-2",
        "GEMINI_API_KEY": None, "MAX_THREAD_LENGTH": 500,
    }
    settings_kwargs.update(extra or {})
    monkeypatch.setattr("src.services.ai_service.settings", Settings(**settings_kwargs))
    payloads: list[dict[str, object]] = []
    LAST_REQUESTS.clear()

    class Response:
        def __init__(self, status: int, content: str) -> None:
            self.status_code = status
            self._content = content
            self.text = content

        def json(self) -> dict[str, object]:
            return {
                "model": "scripted", "modelVersion": "scripted-gemini",
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
            LAST_REQUESTS.append({"url": url, "headers": kwargs.get("headers", {})})
            status, content = script[min(len(payloads) - 1, len(script) - 1)]
            return Response(status, content)

    monkeypatch.setattr("src.services.ai_service.httpx.AsyncClient", Client)
    return payloads


def _use_fake_models(monkeypatch: pytest.MonkeyPatch, contents: list[str]) -> list[dict[str, object]]:
    """Each model attempt returns the next scripted content with HTTP 200."""
    return _use_scripted_responses(monkeypatch, [(200, content) for content in contents])


@pytest.mark.asyncio
async def test_profileless_event_uses_model_output_with_code_owned_header_and_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_fake_models(monkeypatch, [_body(GOOD_BLOCK_ONE, GOOD_QUESTION)])
    service = AIService()

    parts, _, _ = await service.rewrite_event_safe(_request())

    assert parts[0].startswith("🏛️ Tarihte Bugün (20.10.1921)\n\n")
    assert parts[0].rstrip().endswith("#tarih")
    assert parts[1] == GOOD_QUESTION
    assert len(parts) == 2
    assert service.last_generation_type == "ai_source_bound"
    assert service.last_source_fact_status == "not_checked"
    assert service.last_source_url == _request().source_url
    assert service.prompt_version.startswith("event-rewrite-v5+")


@pytest.mark.asyncio
async def test_unsupported_year_is_rejected_and_next_model_is_tried(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = _use_fake_models(monkeypatch, [
        _body("Ankara Antlaşması 1923 yılında imzalandı ve masaya bir karar getirdi.", GOOD_QUESTION),
        _body(GOOD_BLOCK_ONE, GOOD_QUESTION),
    ])
    service = AIService()

    parts, _, _ = await service.rewrite_event_safe(_request())

    assert len(payloads) == 2
    assert service.last_generation_type == "ai_source_bound"
    assert "1923" not in "\n".join(parts)


@pytest.mark.asyncio
async def test_all_models_failing_validation_falls_back_to_source(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = _body("Ankara Antlaşması 1923 yılında imzalandı ve masaya bir karar getirdi.", GOOD_QUESTION)
    payloads = _use_fake_models(monkeypatch, [bad, bad])
    service = AIService()

    parts, _, _ = await service.rewrite_event_safe(_request())

    assert len(payloads) == 2
    assert service.last_generation_type.startswith("source_fallback:unsupported_number")
    assert "1923" not in "\n".join(parts)


@pytest.mark.parametrize(("block_one", "accepted"), [
    ("Ankara Antlaşması 1921'de TBMM ile Fransa arasında imzalandı.", True),
    ("Buzlu bir sabahta, sessizce ve nadir bir tesadüfle, 1921'de TBMM ile Fransa arasında imzalandı.", False),
    ("Bu tartışmalı ve korkunç olay, ülke tarihindeki en çarpıcı anlaşmaydı; 1921'de imzalandı.", False),
])
def test_unsupported_word_roots_are_rejected_beyond_two(block_one: str, accepted: bool) -> None:
    reasons = validate_source_bound_content([block_one, GOOD_QUESTION], _request(), True, 480)

    assert ("unsupported_words" not in reasons) is accepted


def test_unsupported_name_is_rejected() -> None:
    reasons = validate_source_bound_content(
        ["1921'de TBMM ile Londra arasında Ankara Antlaşması imzalandı.", GOOD_QUESTION],
        _request(),
        True,
        480,
    )

    assert reasons == ("unsupported_name",)


def test_question_must_end_the_output_and_format_is_checked() -> None:
    reasons = validate_source_bound_content(
        [GOOD_BLOCK_ONE, "Bu olayı daha önce duymuş muydunuz."], _request(), True, 480,
    )

    assert "format" in reasons


def test_missing_emoji_line_is_a_format_rejection() -> None:
    reasons = validate_source_bound_content([GOOD_BLOCK_ONE, GOOD_QUESTION], _request(), False, 480)

    assert reasons == ("format",)


@pytest.mark.asyncio
async def test_unapproved_emoji_becomes_default(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_fake_models(monkeypatch, [_body(GOOD_BLOCK_ONE, GOOD_QUESTION, emoji="🎉")])
    service = AIService()

    parts, _, _ = await service.rewrite_event_safe(_request())

    assert parts[0].startswith("🕊️ Tarihte Bugün")


@pytest.mark.asyncio
async def test_thin_source_accepts_two_blocks_and_rich_source_accepts_three(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    middle = "Antlaşma metninde güney sınırının taslak olarak belirlenmesi kararı yer alır."
    payloads = _use_fake_models(monkeypatch, [
        _body(GOOD_BLOCK_ONE, GOOD_QUESTION),
        _body(GOOD_BLOCK_ONE, middle, GOOD_QUESTION),
    ])
    service = AIService()

    thin_parts, _, _ = await service.rewrite_event_safe(_request(ANKARA_SUMMARY))
    rich_parts, _, _ = await service.rewrite_event_safe(_request(RICH_SUMMARY))

    assert len(thin_parts) == 2
    assert len(rich_parts) == 3
    assert "Kaynak zengin mi: hayır" in payloads[0]["messages"][-1]["content"]
    assert "Kaynak zengin mi: evet" in payloads[1]["messages"][-1]["content"]


def test_summary_keeps_anchor_sentences_and_drops_conflicting_years() -> None:
    candidate = {
        "text": ANKARA_TEXT,
        "year": 1921,
        "pages": [{
            "title": "Ankara Antlaşması",
            "extract": (
                "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı. "
                "Ankara sınırı Lozan'da kesinleşti. "
                "Ankara 1923'te yeniden tartışıldı. "
                "Paris, Fransa'nın başkentidir."
            ),
            "content_urls": {"desktop": {"page": "https://tr.wikipedia.org/wiki/Ankara"}},
        }],
    }

    source = select_event_summary(candidate)

    assert source is not None
    assert source.context == "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı. Ankara sınırı Lozan'da kesinleşti."


def test_summary_is_bounded_to_800_characters() -> None:
    sentence = "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı. "
    candidate = {
        "text": ANKARA_TEXT,
        "year": 1921,
        "pages": [{"title": "Ankara Antlaşması", "extract": sentence * 60}],
    }

    source = select_event_summary(candidate)

    assert source is not None
    assert len(source.context) <= 800


def test_thin_summary_costs_ten_fame_points_without_excluding_the_event(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.services.source_context import SelectedSource

    event = {"text": ANKARA_TEXT, "year": 1921, "_category": "events", "pages": []}
    service = ContentService()
    thin_score = service._calculate_fame_score(event)
    monkeypatch.setattr(
        "src.services.content_service.select_event_summary",
        lambda item: SelectedSource("Ankara Antlaşması", None, "x" * 150, 1),
    )

    assert service._calculate_fame_score(event) - thin_score == 10


def test_source_bound_evidence_uses_the_summary_sentences_actually_given_to_the_model() -> None:
    request = _request(RICH_SUMMARY)

    used = _used_source_sentences(request, "ai_source_bound")

    assert used[0] == "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı."
    assert len(used) == 4


@pytest.mark.asyncio
async def test_rate_limited_model_is_retried_in_the_same_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.services.ai_service.RATE_LIMIT_BACKOFF_SECONDS", 0)
    payloads = _use_scripted_responses(monkeypatch, [
        (429, ""), (429, ""), (429, ""), (200, _body(GOOD_BLOCK_ONE, GOOD_QUESTION)),
    ])
    service = AIService()

    await service.rewrite_event_safe(_request())

    assert [p["model"] for p in payloads] == ["model-1"] * 4
    assert service.last_generation_type == "ai_source_bound"


def test_model_time_budget_is_about_ninety_seconds() -> None:
    from src.services import ai_service as module

    assert module.SOURCE_BOUND_TIME_BUDGET_SECONDS == 90
    assert module.RATE_LIMIT_BACKOFF_SECONDS == 5


@pytest.mark.asyncio
async def test_reasoning_parameter_is_omitted_only_for_configured_models(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = _body("Ankara Antlaşması 1923 yılında imzalandı ve masaya bir karar getirdi.", GOOD_QUESTION)
    payloads = _use_scripted_responses(
        monkeypatch,
        [(200, bad), (200, _body(GOOD_BLOCK_ONE, GOOD_QUESTION))],
        extra={"MODELS_WITHOUT_REASONING_PARAM": "model-2"},
    )

    await AIService().rewrite_event_safe(_request())

    assert "reasoning" in payloads[0]
    assert "reasoning" not in payloads[1]
    assert payloads[1]["model"] == "model-2"


@pytest.mark.asyncio
async def test_time_budget_stops_the_cascade_and_uses_structured_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.services.ai_service.SOURCE_BOUND_TIME_BUDGET_SECONDS", -1)
    payloads = _use_fake_models(monkeypatch, [_body(GOOD_BLOCK_ONE, GOOD_QUESTION)])
    service = AIService()

    parts, _, _ = await service.rewrite_event_safe(_request())

    assert payloads == []
    assert service.last_generation_type.endswith(":structured")
    assert "time_budget" in service.last_generation_type


@pytest.mark.asyncio
async def test_few_shot_pairs_precede_the_real_request(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads = _use_fake_models(monkeypatch, [_body(GOOD_BLOCK_ONE, GOOD_QUESTION)])

    await AIService().rewrite_event_safe(_request())

    roles = [message["role"] for message in payloads[0]["messages"]]
    assert roles == ["system", "user", "assistant", "user", "assistant", "user"]


@pytest.mark.asyncio
async def test_all_models_failing_gives_code_built_fallback_without_model_text(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.services.structured_fallback import FALLBACK_QUESTIONS

    bad = _body("Ankara Antlaşması 1923 yılında imzalandı ve masaya bir karar getirdi.", GOOD_QUESTION)
    _use_fake_models(monkeypatch, [bad, bad])
    service = AIService()

    parts, _, _ = await service.rewrite_event_safe(_request())

    assert parts[0] == (
        "🕊️ Tarihte Bugün (20.10.1921)\n\n"
        "Ankara Antlaşması imzalandı. Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı. #tarih"
    )
    assert parts[1] in FALLBACK_QUESTIONS
    assert "1923" not in "\n".join(parts)
    assert "masaya" not in "\n".join(parts)
    assert service.last_generation_type.startswith("source_fallback:unsupported_number")
    assert service.last_generation_type.endswith(":structured")


def test_fallback_question_bank_has_at_least_five_questions_and_avoids_recent_repeats() -> None:
    from src.services.structured_fallback import FALLBACK_QUESTIONS, choose_fallback_question

    assert len(FALLBACK_QUESTIONS) >= 5
    first = choose_fallback_question([])
    second = choose_fallback_question([f"Bir metin. {first}"])
    assert second != first


def test_gemini_is_skipped_when_key_is_absent() -> None:
    service = AIService()
    service.api_key = "openrouter-key"
    settings_without_gemini = Settings(OPENROUTER_API_KEY="openrouter-key", GEMINI_API_KEY=None)
    import src.services.ai_service as module

    original = module.settings
    module.settings = settings_without_gemini
    try:
        providers = [provider for provider, _, _ in service._source_bound_cascade()]
    finally:
        module.settings = original
    assert "gemini" not in providers
    assert providers == ["openrouter", "openrouter"]


@pytest.mark.asyncio
async def test_gemini_is_first_when_configured_and_key_stays_out_of_url_and_body(monkeypatch: pytest.MonkeyPatch) -> None:
    key = "test-gemini-key-value"
    payloads = _use_scripted_responses(
        monkeypatch,
        [(200, _body(GOOD_BLOCK_ONE, GOOD_QUESTION))],
        extra={"GEMINI_API_KEY": key, "GEMINI_MODEL": "gemini-test-model"},
    )
    service = AIService()

    await service.rewrite_event_safe(_request())

    assert LAST_REQUESTS[0]["url"].endswith("/gemini-test-model:generateContent")
    assert LAST_REQUESTS[0]["headers"]["x-goog-api-key"] == key
    assert key not in LAST_REQUESTS[0]["url"]
    assert key not in str(payloads[0])
    assert service.last_generation_model == "scripted-gemini"
    assert service.last_generation_type == "ai_source_bound"
    assert payloads[0]["systemInstruction"]["parts"][0]["text"].startswith("Sen Türkçe")


def test_fallback_questions_cover_event_and_person_kinds_with_rotation() -> None:
    from src.services.structured_fallback import (
        EVENT_QUESTIONS, FALLBACK_QUESTIONS, PERSON_QUESTIONS, choose_fallback_question, event_kind,
    )

    assert len(FALLBACK_QUESTIONS) >= 8
    assert event_kind("Kâzım Koyuncu, Türk müzisyen (ö. 2005)") == "person"
    assert event_kind("Türk ordusu, Gümrü'yü ele geçirdi.") == "event"
    assert choose_fallback_question([], "Kâzım Koyuncu, Türk müzisyen (ö. 2005)") in PERSON_QUESTIONS
    first = choose_fallback_question([], "Türk ordusu, Gümrü'yü ele geçirdi.")
    assert first in EVENT_QUESTIONS
    assert choose_fallback_question([f"Metin. {first}"], "Türk ordusu, Gümrü'yü ele geçirdi.") != first


def test_summary_sentence_that_repeats_the_event_is_dropped() -> None:
    from src.services.structured_fallback import best_overlap_sentence

    event = "Türk ordusu, Gümrü'yü ele geçirdi."
    repeats = "Türk ordusu Gümrü'yü ele geçirdi."
    adds = "Gümrü, Ermenistan sınırına yakın bir şehirdi."

    assert best_overlap_sentence(event, (repeats,)) is None
    assert best_overlap_sentence(event, (repeats, adds)) == adds


def test_gemini_is_skipped_when_model_id_is_empty() -> None:
    import src.services.ai_service as module

    service = AIService()
    original = module.settings
    module.settings = Settings(OPENROUTER_API_KEY="openrouter-key", GEMINI_API_KEY="gemini-key", GEMINI_MODEL="")
    try:
        providers = [provider for provider, _, _ in service._source_bound_cascade()]
    finally:
        module.settings = original
    assert "gemini" not in providers


def test_gemini_request_uses_timeout_and_minimal_thinking(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.services.ai_service as module

    seen: list[dict[str, object]] = []

    class Response:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {"candidates": [{"content": {"parts": [{"text": "Merhaba."}]}}], "modelVersion": "gemini-3.8-flash"}

    class Client:
        async def post(self, url: str, **kwargs: object) -> Response:
            seen.append(kwargs)
            return Response()

    service = AIService()
    _, url, body = None, None, None
    url, headers, body = service._gemini_request("gemini-3.8-flash", [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}])
    assert body["generationConfig"]["thinkingConfig"] == {"thinkingLevel": module.settings.GEMINI_THINKING_LEVEL}
    assert body["generationConfig"]["maxOutputTokens"] == 1200
    assert service._gemini_request("gemini-2.5-flash", [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}])[2]["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}
    status, text, model = asyncio.run(service._call_with_backoff(
        Client(), "gemini", "gemini-3.8-flash", [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
        {}, time.monotonic() + 60, "Gemini",
    ))
    assert (status, text) == (200, "Merhaba.")
    assert seen[0]["timeout"] == module.GEMINI_TIMEOUT_SECONDS == 25.0
