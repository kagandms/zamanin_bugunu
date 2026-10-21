from datetime import datetime

import pytest

from src.core.config import Settings
from src.event_preparation import _rewrite_request
from src.services.ai_service import AIService
from src.services.content_guard import EventRewriteRequest, resolve_fact_profile, validate_event_content
from src.services.content_service import ContentService


def test_rewrite_request_carries_bounded_relevant_extract() -> None:
    candidate = {
        "text": "Kars Antlaşması imzalandı.",
        "year": 1921,
        "pages": [{
            "title": "Kars Antlaşması",
            "extract": ("Kars Antlaşması 1921'de imzalandı. " * 200),
            "content_urls": {"desktop": {"page": "https://tr.wikipedia.org/wiki/Kars"}},
        }],
    }

    request = _rewrite_request(candidate, datetime(2026, 10, 19))

    assert request.source_url == "https://tr.wikipedia.org/wiki/Kars"
    assert request.source_context is not None
    assert request.source_context == "Kars Antlaşması 1921'de imzalandı."


def test_off_topic_extract_is_removed_before_generation() -> None:
    candidate = {
        "text": "Kars Antlaşması imzalandı.",
        "year": 1921,
        "pages": [{
            "title": "Kars Antlaşması",
            "extract": "Roma İmparatorluğu hakkında bir özet.",
        }],
    }

    request = _rewrite_request(candidate, datetime(2026, 10, 19))

    assert request.source_context is None


def test_source_context_score_ignores_unrelated_long_extracts() -> None:
    event = "Kars Antlaşması imzalandı."
    short = {"text": event, "pages": [{"title": "Fransızlar", "extract": "Kısa kayıt."}]}
    long = {"text": event, "pages": [{
        "title": "Fransızlar", "extract": "Kars Antlaşması " + "ayrıntı " * 200 + ".",
    }]}

    assert ContentService._source_context_score(long) == 0
    assert ContentService._source_context_score(short) == 0


def test_popularity_bonus_is_capped_at_thirty() -> None:
    assert ContentService._popularity_bonus(100_000_000) == 30
    assert ContentService._popularity_bonus(4_999) == 0


def test_unprofiled_generation_rejects_year_absent_from_source_evidence() -> None:
    request = EventRewriteRequest(
        original_text="Kars Antlaşması imzalandı.",
        formatted_date="19.10",
        source_title="Kars Antlaşması",
        source_context="Antlaşma bu iki ülke arasında imzalandı.",
    )

    reasons = validate_event_content(["Olay 1923 yılında yaşandı."], request, None)

    assert reasons == ("unprofiled_claims_unverified", "unsupported_year")


def test_unprofiled_generation_accepts_year_from_relevant_extract() -> None:
    request = EventRewriteRequest(
        original_text="Kars Antlaşması imzalandı.",
        formatted_date="19.10",
        source_title="Kars Antlaşması",
        source_context="Kars Antlaşması 1923 yılında imzalandı.",
    )

    assert validate_event_content(["Antlaşma 1923 yılında imzalandı."], request, None) == (
        "unprofiled_claims_unverified",
    )


def test_published_burak_claims_are_not_accepted_without_a_fact_profile() -> None:
    request = EventRewriteRequest(
        "Burak Güven, Türk bas gitarist, şarkı sözü yazarı ve Mor ve Ötesi grubu üyesi",
        "19.10.1975",
        "1975",
        "Burak Güven",
        "https://tr.wikipedia.org/wiki/Burak_G%C3%BCven",
        "Burak Güven, Mor ve Ötesi grubu üyesidir.",
    )
    published_candidate = [
        "Burak Güven, Mor ve Ötesi grubunun founding üyesi olarak yer alır. "
        "Gruba katkıları alternatif rock alanında önemli bir yer tutar.",
        "Not: Gün ve ay (19.10) doğrudan kaynakta yer almamaktadır; tarih sembolik kullanılmıştır.",
    ]

    reasons = validate_event_content(published_candidate, request, resolve_fact_profile(request))

    assert reasons == ("unprofiled_claims_unverified",)


def test_profiled_output_rejects_model_authored_source_absence_note() -> None:
    request = EventRewriteRequest(
        "II. Kosova Muharebesi gerçekleşti.",
        "19.10.1448",
        "1448",
        "II. Murad",
        "https://tr.wikipedia.org/wiki/II._Murad",
    )
    profile = resolve_fact_profile(request)

    reasons = validate_event_content(
        ["Kaynakta gün ve ay bulunmadığı için 19.10 tarihi sembolik kullanıldı."], request, profile
    )

    assert reasons == ("unverified_source_commentary",)


@pytest.mark.asyncio
async def test_unprofiled_burak_output_uses_source_fallback_without_calling_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.services.ai_service.settings",
        Settings(OPENROUTER_API_KEY="test-key", MAX_THREAD_LENGTH=500),
    )
    service = AIService()

    async def unexpected_model_call(request: EventRewriteRequest) -> tuple[list[str], list[str], None]:
        raise AssertionError("unprofiled claims cannot be accepted from a model")

    service.rewrite_event = unexpected_model_call
    request = EventRewriteRequest(
        original_text=(
            "Burak Güven, Türk bas gitarist, şarkı sözü yazarı ve Mor ve Ötesi grubu üyesi"
        ),
        formatted_date="19.10.1975",
        year="1975",
        source_title="Burak Güven",
        source_url="https://tr.wikipedia.org/wiki/Burak_G%C3%BCven",
        source_context=(
            "Burak Güven (19 Ekim 1975, İstanbul), Türk bas gitarist, şarkı sözü yazarı, "
            "geri vokal/vokal ve Mor ve Ötesi grubu üyesidir."
        ),
    )

    parts, _, _ = await service.rewrite_event_safe(request)

    rendered = "\n".join(parts)
    assert "19.10.1975" in rendered
    assert "Kaynak özeti: Burak Güven (19 Ekim 1975" in rendered
    assert "founding" not in rendered.casefold()
    assert "önemli bir yer" not in rendered.casefold()
    assert "sembolik" not in rendered.casefold()
    assert "doğrudan kaynakta yer almamaktadır" not in rendered.casefold()
    assert service.last_generation_type == "source_fallback:unprofiled_claims_unverified:source_context"
    assert service.last_source_fact_status == "not_checked"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_context", "expected_context"),
    [
        ("Burak Güven, Mor ve Ötesi'nin kurucu üyelerindendir.", "kurucu üyelerindendir"),
        ("Burak Güven, Mor ve Ötesi grubu üyesidir.", "grubu üyesidir"),
    ],
)
async def test_unprofiled_fallback_preserves_source_supported_member_distinction(
    monkeypatch: pytest.MonkeyPatch,
    source_context: str,
    expected_context: str,
) -> None:
    monkeypatch.setattr(
        "src.services.ai_service.settings",
        Settings(OPENROUTER_API_KEY="test-key", MAX_THREAD_LENGTH=500),
    )
    service = AIService()
    request = EventRewriteRequest(
        "Burak Güven, Mor ve Ötesi grubu üyesi.",
        "19.10.1975",
        "1975",
        "Burak Güven",
        "https://tr.wikipedia.org/wiki/Burak_G%C3%BCven",
        source_context,
    )

    parts, _, _ = await service.rewrite_event_safe(request)

    assert expected_context in "\n".join(parts)


@pytest.mark.asyncio
async def test_year_only_extract_does_not_make_event_list_date_symbolic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.services.ai_service.settings",
        Settings(OPENROUTER_API_KEY="test-key", MAX_THREAD_LENGTH=500),
    )
    service = AIService()
    request = EventRewriteRequest(
        "Burak Güven, Mor ve Ötesi grubu üyesi.",
        "19.10.1975",
        "1975",
        "Burak Güven",
        source_context="Burak Güven 1975 yılında doğdu.",
    )

    parts, _, _ = await service.rewrite_event_safe(request)

    rendered = "\n".join(parts)
    assert "19.10.1975" in rendered
    assert "sembolik" not in rendered.casefold()
    assert "gün ve ay" not in rendered.casefold()
    assert "kaynakta yer almamaktadır" not in rendered.casefold()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_context", "source_title", "should_use_context"),
    [
        (None, None, False),
        ("", "Kars Antlaşması", False),
        ("Roma İmparatorluğu hakkında bir özet.", "Kars Antlaşması", False),
        (("Kars Antlaşması " + "ayrıntı " * 80 + "."), "Kars Antlaşması", False),
        (("Kars Antlaşması 1921'de imzalandı. " * 200), "Kars Antlaşması", True),
    ],
)
async def test_fallback_uses_only_relevant_bounded_source_context(
    monkeypatch: pytest.MonkeyPatch,
    source_context: str | None,
    source_title: str | None,
    should_use_context: bool,
) -> None:
    monkeypatch.setattr(
        "src.services.ai_service.settings",
        Settings(OPENROUTER_API_KEY="test-key", MAX_THREAD_LENGTH=180),
    )
    service = AIService()

    async def failed_generation(request: EventRewriteRequest) -> tuple[list[str], list[str], None]:
        raise RuntimeError("all_models_failed")

    service.rewrite_event = failed_generation
    request = EventRewriteRequest(
        "Kars Antlaşması hakkında bir kayıt.", "19.10", None, source_title,
        "https://tr.wikipedia.org/wiki/Kars", source_context,
    )

    parts, _, _ = await service.rewrite_event_safe(request)

    if should_use_context:
        assert len(parts) == 2
        assert parts[1].startswith("Kaynak özeti:")
        assert len(parts[1]) <= 180
        assert service.last_generation_type.endswith(":source_context")
        return
    assert len(parts) == 1
    assert "Bu paylaşımda" not in parts[0]
    assert service.last_generation_type.endswith(":thin_source")
