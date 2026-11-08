"""Summary sentence splitting, general-topic pages, and code-owned closing questions.

Pure unit tests: no network, no model calls. Texts mirror the live-check evidence in strategy/evidence/ilk-10-cikti.md.
"""
from __future__ import annotations

import pytest

from src.services.ai_service import AIService
from src.services.content_guard import EventRewriteRequest
from src.services.source_context import _complete_sentences, select_event_summary
from src.services.structured_fallback import FALLBACK_QUESTIONS


@pytest.mark.parametrize(("extract", "expected"), [
    ("George H. W. Bush 1989'da başkan oldu. Dr. Ali geldi.", ("George H. W. Bush 1989'da başkan oldu.", "Dr. Ali geldi.")),
    ("II. Dünya Savaşı sona erdi. Bu bir not.", ("II. Dünya Savaşı sona erdi.", "Bu bir not.")),
    ("Birinci cümle bitti. Son cümle St.", ("Birinci cümle bitti.",)),
    ("Kısa not vb. ve uzun bir cümle bitti.", ("Kısa not vb. ve uzun bir cümle bitti.",)),
    ("Bu cümle sona erdi. Ardından Ahmet X. Kaya geldi.", ("Bu cümle sona erdi.", "Ardından Ahmet X. Kaya geldi.")),
])
def test_abbreviations_and_initials_do_not_end_sentences(extract: str, expected: tuple[str, ...]) -> None:
    assert _complete_sentences(extract) == expected


def test_summary_ending_in_abbreviation_is_dropped_as_incomplete() -> None:
    candidate = {"text": "Ankara Antlaşması imzalandı.", "year": 1921, "pages": [{
        "title": "Ankara Antlaşması", "extract": "Ankara Antlaşması 1921'de imzalandı. Ankara Dr.",
    }]}

    source = select_event_summary(candidate)

    assert source is not None
    assert source.context == "Ankara Antlaşması 1921'de imzalandı."


def test_page_titled_with_the_event_label_is_a_general_topic_and_gives_no_summary() -> None:
    # Evidence #1 (8 Kasım): the label "II. Dünya Savaşı" is the broad war, not the Algeria/Morocco operation.
    candidate = {
        "text": "II. Dünya Savaşı: Britanya İmparatorluğu ve ABD, Kuzey Afrika'da Cezayir ve Fas'ı işgal ettiler.",
        "year": 1942,
        "pages": [{"title": "II. Dünya Savaşı", "extract": (
            "II. Dünya Savaşı, 1939'da başlayan ve 1945'te sona eren küresel bir savaştır. "
            "Britanya ve ABD Kuzey Afrika'da Cezayir ve Fas'ı işgal etti.")}],
    }

    assert select_event_summary(candidate) is None


def test_model_question_is_discarded_and_a_bank_question_is_appended() -> None:
    # Evidence #3 (Birahane Darbesi): the model wrote a question; the code replaces it with a bank question.
    blocks = [
        "Adolf Hitler ve yandaşları, Bavyera eyaletinin yönetimini ele geçirmek için ayaklandı.",
        "Bu darbe girişimini daha önce duymuş muydunuz?",
    ]

    parts = AIService._assemble_source_bound_parts("⚔️", blocks, "8.11.1923", "Bu olayı bugün nasıl okuyorsunuz?")

    assert parts[0].startswith("⚔️ Tarihte Bugün (8.11.1923)\n\nAdolf Hitler")
    assert parts[0].rstrip().endswith("#tarih")
    assert parts[-1] == "Bu olayı bugün nasıl okuyorsunuz?"
    assert all("duymuş muydunuz" not in part for part in parts)


@pytest.mark.asyncio
async def test_ai_path_output_ends_with_a_bank_question(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.core.config import Settings
    import src.services.ai_service as module

    monkeypatch.setattr(module, "settings", Settings(
        OPENROUTER_API_KEY="", GEMINI_API_KEY="unused-in-test", GEMINI_MODEL="gemini-test",
        MAX_THREAD_LENGTH=500,
    ))
    content = "EMOJI: 🏛️\n---\nAnkara Antlaşması 1921'de TBMM ile Fransa arasında bir anlaşma olarak imzalandı.\n---\nModelin yazdığı soru?"

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
    request = EventRewriteRequest("Ankara Antlaşması imzalandı.", "20.10.1921", "1921", "Ankara Antlaşması",
                                  "https://tr.wikipedia.org/wiki/Ankara_Antla%C5%9Fmas%C4%B1",
                                  "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı.")
    service = AIService()

    parts, _, _ = await service.rewrite_event_safe(request)

    assert parts[-1] in FALLBACK_QUESTIONS
    assert all("Modelin" not in part for part in parts)
    assert service.last_generation_type == "ai_source_bound"
