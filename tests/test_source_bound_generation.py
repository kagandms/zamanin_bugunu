"""Source-bound generation for events without a curated fact profile (event-rewrite-v5)."""
from __future__ import annotations

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
GOOD_BLOCK_ONE = "1921'de TBMM ile Fransa arasında imzalanan Ankara Antlaşması, masadaki bir kararı belgeye dönüştürdü."
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


def _use_fake_models(monkeypatch: pytest.MonkeyPatch, contents: list[str]) -> list[dict[str, object]]:
    """Each model attempt returns the next scripted content; every request payload is recorded."""
    monkeypatch.setattr("src.services.ai_service.settings", Settings(
        OPENROUTER_API_KEY="mock-key", AI_MODEL="model-1", BACKUP_MODEL="model-2",
        TERTIARY_MODEL="model-3", LAST_RESORT_MODEL="model-4",
        MAX_THREAD_LENGTH=500,
    ))
    payloads: list[dict[str, object]] = []

    class Response:
        status_code = 200

        def __init__(self, content: str) -> None:
            self._content = content

        def json(self) -> dict[str, object]:
            return {"model": "scripted", "choices": [{"message": {"content": self._content}}]}

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> Client:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> Response:
            payloads.append(kwargs["json"])
            return Response(contents[len(payloads) - 1])

    monkeypatch.setattr("src.services.ai_service.httpx.AsyncClient", Client)
    return payloads


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
    payloads = _use_fake_models(monkeypatch, [bad, bad, bad, bad])
    service = AIService()

    parts, _, _ = await service.rewrite_event_safe(_request())

    assert len(payloads) == 4
    assert service.last_generation_type.startswith("source_fallback:unsupported_number")
    assert "1923" not in "\n".join(parts)


@pytest.mark.parametrize("block_one", [
    "Bu korkunç bir olay 1921'de TBMM ile Fransa arasında imzalandı.",
    "Ankara Antlaşması 1921'de ilk kez imzalandı ve TBMM ile Fransa arasında bir karar oldu.",
    "Ailenizde bu anlaşmayı hatırlayan var mı, 1921'de TBMM ile Fransa arasında imzalandı?",
    "Takip edin ve 1921'de TBMM ile Fransa arasında imzalanan Ankara Antlaşması'nı öğrenin.",
])
def test_banned_phrases_are_rejected(block_one: str) -> None:
    reasons = validate_source_bound_content([block_one, GOOD_QUESTION], _request(), True, 480)

    assert "banned_phrase" in reasons


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
    assert "Kaynak zengin mi: hayır" in payloads[0]["messages"][1]["content"]
    assert "Kaynak zengin mi: evet" in payloads[1]["messages"][1]["content"]


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
