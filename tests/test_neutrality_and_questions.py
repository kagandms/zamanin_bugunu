"""Brief #2: neutral wording, question choice and copied-source rejection, shown on the Şuşa 2020 source text.

Offline: scripted model outputs only, no API calls.
"""
from __future__ import annotations

import pytest

from src.event_preparation import _rewrite_rejection
from src.services.ai_service import SOURCE_BOUND_FEW_SHOT, AIService
from src.services.content_guard import EventRewriteRequest, unattributed_loaded_terms, validate_source_bound_content
from src.services.structured_fallback import (
    DETAIL_QUESTION, GENERAL_QUESTIONS, OPEN_QUESTIONS, best_overlap_sentence, choose_fallback_question,
    question_bank,
)

SUSA_EVENT = ("İkinci Dağlık Karabağ Savaşı'nda Azerbaycan güçleri Şuşa şehrini Ermeni işgalinden kurtardı. "
              "Bu tarih daha sonra Zafer Bayramı ilan edildi.")
SUSA_SUMMARY = ("2020 yılında yaşanan ve 44 Günlük Savaş olarak da bilinen İkinci Dağlık Karabağ Savaşı, Dağlık Karabağ'da "
                "gerçekleşti. Çatışmalar; Türkiye destekli Azerbaycan ile Ermenistan ve onun desteklediği tanınmayan "
                "Dağlık Karabağ Cumhuriyeti arasında yaşanmış silahlı çatışmalardır.")
QUESTION = "Bu olayı bugün nasıl okuyorsunuz?"


def _request() -> EventRewriteRequest:
    return EventRewriteRequest(SUSA_EVENT, "8.11.2020", "2020", "İkinci Dağlık Karabağ Savaşı",
                               "https://tr.wikipedia.org/wiki/%C4%B0kinci_Da%C4%9Fl%C4%B1k_Karaba%C4%9F_Sava%C5%9F%C4%B1",
                               SUSA_SUMMARY)


def _reasons(*blocks: str) -> tuple[str, ...]:
    return validate_source_bound_content(list(blocks), _request(), True, 480)


def test_unattributed_loaded_term_is_rejected() -> None:
    reasons = _reasons(
        "Azerbaycan güçleri İkinci Dağlık Karabağ Savaşı'nda Şuşa şehrini Ermeni işgalinden kurtardı.", QUESTION,
    )

    assert "loaded_term" in reasons


def test_attributed_loaded_term_passes() -> None:
    reasons = _reasons(
        "Azerbaycan'a göre, İkinci Dağlık Karabağ Savaşı'nda Azerbaycan güçleri Şuşa şehrini Ermeni işgalinden kurtardı.",
        QUESTION,
    )

    assert "loaded_term" not in reasons


@pytest.mark.parametrize("text", [
    'Ermenistan\'ın bu duruma "işgal" dediği aktarıldı.',
    "Azerbaycan tarafından zafer olarak adlandırılan olay yaşandı.",
])
def test_quoted_and_named_loaded_terms_count_as_attributed(text: str) -> None:
    assert unattributed_loaded_terms(text) == ()


@pytest.mark.parametrize("text", ["Zafer Bayramı ilan edildi.", "Kahramanmaraş'ta bir toplantı yapıldı."])
def test_proper_names_with_loaded_roots_are_exempt(text: str) -> None:
    assert unattributed_loaded_terms(text) == ()


def test_neutral_few_shot_for_susa_passes_the_validator() -> None:
    assistant = next(reply for user, reply in SOURCE_BOUND_FEW_SHOT if "Şuşa" in user)
    present, _, blocks, _ = AIService._parse_source_bound_response(assistant)

    assert validate_source_bound_content(blocks, _request(), present, 480) == ()
    assert "kurtardı" not in assistant and "işgal" not in assistant


def test_second_part_copying_the_summary_is_rejected_but_a_rewrite_passes() -> None:
    first = "Azerbaycan'da bu tarih Zafer Bayramı ilan edildi: Şuşa şehri Azerbaycan güçlerinin denetimine geçti."
    copied = ("Çatışmalar; Türkiye destekli Azerbaycan ile Ermenistan ve onun desteklediği tanınmayan "
              "Dağlık Karabağ Cumhuriyeti arasında yaşanmış silahlı çatışmalardır.")
    rewritten = "Dağlık Karabağ'da Azerbaycan ile Ermenistan arasında silahlı çatışmalar yaşandı."

    assert "copied_source" in _reasons(first, copied, QUESTION)
    assert "copied_source" not in _reasons(first, rewritten, QUESTION)


def test_fallback_skips_a_summary_sentence_with_an_unattributed_loaded_term() -> None:
    loaded = "Azerbaycan güçleri Şuşa'yı işgalden kurtardı ve ardından birçok yeni yerleşim kurdu."
    attributed = "Azerbaycan'a göre güçleri Şuşa'yı işgalden kurtardı ve ardından birçok yeni yerleşim kurdu."

    assert best_overlap_sentence(SUSA_EVENT, (loaded,)) is None
    assert best_overlap_sentence(SUSA_EVENT, (attributed,)) == attributed


def test_event_selection_skips_a_fallback_that_carries_a_loaded_event_sentence() -> None:
    # The structured fallback copies the Wikipedia event sentence verbatim ("... işgalinden kurtardı").
    loaded_blocks = [f"⚔️ Tarihte Bugün (8.11.2020)\n\n{SUSA_EVENT} #tarih", QUESTION]
    neutral_blocks = ["🕊️ Tarihte Bugün (8.11.1923)\n\nTürk ordusu Gümrü'ye girdi. #tarih", QUESTION]
    fallback = "source_fallback:unsupported_words:structured"

    assert _rewrite_rejection({"pages": []}, loaded_blocks, fallback) == "loaded_term"
    assert _rewrite_rejection({"pages": []}, neutral_blocks, fallback) is None


@pytest.mark.parametrize("context", ["", "Çatışmalar bir süre devam etti."])
def test_detail_question_is_not_offered_without_a_concrete_detail(context: str) -> None:
    assert DETAIL_QUESTION not in question_bank(SUSA_EVENT, context)
    assert choose_fallback_question([], SUSA_EVENT, context) != DETAIL_QUESTION


def test_detail_question_is_offered_for_a_number_or_name_and_rotates_in() -> None:
    context = "Çatışmalar 44 gün sürdü."
    all_general = [f"Metin. {question}" for question in GENERAL_QUESTIONS]

    assert DETAIL_QUESTION in question_bank(SUSA_EVENT, context)
    assert choose_fallback_question(all_general, SUSA_EVENT, context) == DETAIL_QUESTION


def test_conflict_and_politics_events_get_no_opinion_questions() -> None:
    bank = question_bank(SUSA_EVENT, "Çatışmalar 44 gün sürdü.")

    assert not set(OPEN_QUESTIONS) & set(bank)
    assert set(OPEN_QUESTIONS) & set(question_bank("Montana ABD'nin 41. eyaleti oldu.", ""))


@pytest.mark.asyncio
async def test_ai_path_uses_a_general_question_when_the_second_part_has_no_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.services.ai_service as module
    from src.core.config import Settings

    monkeypatch.setattr(module, "settings", Settings(
        OPENROUTER_API_KEY="", GEMINI_API_KEY="unused", GEMINI_MODEL="gemini-test", MAX_THREAD_LENGTH=500,
    ))
    content = ("EMOJI: ⚔️\n---\nAzerbaycan'da bu tarih Zafer Bayramı ilan edildi: Şuşa şehri Azerbaycan güçlerinin "
               "denetimine geçti.\n---\nBu ayrıntıyı daha önce duymuş muydunuz?")

    class Response:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {"candidates": [{"content": {"parts": [{"text": content}]}}]}

    class Client:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr(module.httpx, "AsyncClient", Client)
    request = EventRewriteRequest(SUSA_EVENT, "8.11.2020", "2020", None, None, None)

    parts, _, _ = await AIService().rewrite_event_safe(request)

    assert parts[-1] in GENERAL_QUESTIONS
    assert parts[-1] != DETAIL_QUESTION
