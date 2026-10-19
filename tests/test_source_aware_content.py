from datetime import datetime

import pytest

from src.core.config import Settings
from src.event_preparation import _rewrite_request
from src.services.ai_service import AIService
from src.services.content_guard import EventRewriteRequest, validate_event_content
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
    assert len(request.source_context) == 3000


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


def test_source_context_score_rewards_more_available_context() -> None:
    sparse = {"pages": [{"extract": "Kısa kayıt."}]}
    rich = {"pages": [{
        "extract": ("Birinci bağlam. İkinci sonuç. Üçüncü ayrıntı. " * 20),
        "description": "Tarihsel olay",
    }]}

    assert ContentService._source_context_score(rich) > ContentService._source_context_score(sparse)


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

    assert reasons == ("unsupported_year",)


def test_unprofiled_generation_accepts_year_from_relevant_extract() -> None:
    request = EventRewriteRequest(
        original_text="Kars Antlaşması imzalandı.",
        formatted_date="19.10",
        source_title="Kars Antlaşması",
        source_context="Kars Antlaşması 1923 yılında imzalandı.",
    )

    assert validate_event_content(["Antlaşma 1923 yılında imzalandı."], request, None) == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_context", "source_title", "should_use_context"),
    [
        (None, None, False),
        ("", "Kars Antlaşması", False),
        ("Roma İmparatorluğu hakkında bir özet.", "Kars Antlaşması", False),
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
    assert "Kaynakta ek tarihsel bağlam doğrulanamadı." in parts[0]
    assert service.last_generation_type.endswith(":thin_source")
