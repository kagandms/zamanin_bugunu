from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.core.config import Settings
from src.event_preparation import PreparationServices, prepare_event
from src.services.ai_service import AIService
from src.services.content_guard import (
    EventRewriteRequest,
    II_MURAD_SOURCE_URL,
    TDV_MURAD_II_SOURCE_URL,
    get_source_fact_status,
    resolve_fact_profile,
)


II_MURAD_EVENT = "Osmanlı padişahı II. Murat, Kosova Zaferi'ni kazandı."
II_MURAD_REQUEST = EventRewriteRequest(
    II_MURAD_EVENT,
    "19.10.1448",
    "1448",
    "II. Murad",
    II_MURAD_SOURCE_URL,
)


def test_ii_kosovo_profile_requires_matching_source_and_year() -> None:
    profile = resolve_fact_profile(II_MURAD_REQUEST)

    assert profile is not None
    assert profile.profile_id == "ii-kosovo-1448"
    assert profile.source_url == TDV_MURAD_II_SOURCE_URL
    assert get_source_fact_status(profile) == "checked_scoped"
    assert "17-20 Ekim 1448" in profile.facts[0]
    assert "üç gün süren çetin muharebeden sonra Macarlar yenildi" in profile.facts[0]
    assert "19 Ekim sabahı" not in profile.facts[0]
    assert "son barikatlar aşıldı" not in profile.facts[0]
    assert "Balkanlar'da yayılmasının ve yerleşmesinin kesinleştiğini" in profile.facts[1]


def test_ii_kosovo_profile_does_not_match_an_unrelated_source() -> None:
    request = EventRewriteRequest(II_MURAD_EVENT, "19.10.1448", "1448", "II. Murad")

    assert resolve_fact_profile(request) is None


@pytest.mark.asyncio
async def test_generation_failure_uses_curated_ii_kosovo_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.services.ai_service.settings",
        Settings(OPENROUTER_API_KEY="test-key", MAX_THREAD_LENGTH=500),
    )
    service = AIService()

    async def failed_generation(request: EventRewriteRequest) -> tuple[list[str], list[str], None]:
        raise RuntimeError("all_models_failed")

    service.rewrite_event = failed_generation

    parts, _, _ = await service.rewrite_event_safe(II_MURAD_REQUEST)

    assert len(parts) == 2
    assert "19.10.1448" in parts[0]
    assert "17-20 Ekim 1448'te yapıldı" in parts[0]
    assert "Macarlar yenildi" in parts[0]
    assert "Balkanlar'da yayılmasının ve yerleşmesinin kesinleştiğini" in parts[1]
    assert service.last_source_fact_status == "checked_scoped"
    assert service.last_source_url == TDV_MURAD_II_SOURCE_URL


@pytest.mark.asyncio
async def test_unprofiled_generation_fallback_states_missing_context_in_one_part(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.services.ai_service.settings",
        Settings(OPENROUTER_API_KEY="test-key", MAX_THREAD_LENGTH=500),
    )
    service = AIService()

    async def failed_generation(request: EventRewriteRequest) -> tuple[list[str], list[str], None]:
        raise RuntimeError("all_models_failed")

    service.rewrite_event = failed_generation
    request = EventRewriteRequest("Bir karar alındı.", "19.10.2026")

    parts, _, _ = await service.rewrite_event_safe(request)

    assert len(parts) == 1
    assert "Kaynakta ek tarihsel bağlam doğrulanamadı." in parts[0]
    assert service.last_generation_type.endswith(":thin_source")
    assert service.last_source_fact_status == "not_checked"


def test_single_section_source_content_passes_format_validation() -> None:
    service = AIService()
    content = (
        "🕊️ Tarihte Bugün (19.10.2026)\n"
        "Kaynakta doğrulanan olay budur; ek bilgi yok."
    )

    assert service._validate_turkish_content(content)


@pytest.mark.asyncio
async def test_generic_follow_call_is_not_a_second_threads_part() -> None:
    candidate = {
        "text": II_MURAD_EVENT,
        "year": "1448",
        "pages": [{
            "title": "II. Murad",
            "titles": {"canonical": "II. Murad"},
            "content_urls": {"desktop": {"page": II_MURAD_SOURCE_URL}},
            "thumbnail": {"source": "https://example.test/image.jpg"},
        }],
    }

    class Content:
        async def fetch_events(self, month: int, day: int) -> list[dict[str, object]]:
            return [candidate]

        async def select_best_event(
            self, candidates: list[dict[str, object]], used_texts: list[str]
        ) -> dict[str, object]:
            return candidate

        @staticmethod
        def classify_topic(text: str) -> str:
            return "SIYASET"

    class AI:
        last_generation_type = "ai_validated"
        last_validation_reason = None
        last_generation_model = "test-model"
        last_source_fact_status = "checked_scoped"
        last_language_format_status = "passed"
        last_source_id = "curated-test-source"
        last_source_url = TDV_MURAD_II_SOURCE_URL
        prompt_version = "event-rewrite-v4+fact-guard-v4"

        async def rewrite_event_safe(
            self, request: EventRewriteRequest
        ) -> tuple[list[str], list[str], None]:
            return ["Ana tarihsel bölüm." + " x" * 40, "Kaynaklı tarihsel sonuç."], [], None

    class Image:
        @staticmethod
        async def download_image(url: str) -> None:
            return None

    class History:
        @staticmethod
        async def get_todays_posts() -> list[str]:
            return []

        @staticmethod
        async def exists(text: str) -> bool:
            return False

    prepared = await prepare_event(
        PreparationServices(Content(), AI(), Image()),
        History(),
        datetime(2026, 10, 19, 9, 0, tzinfo=ZoneInfo("Europe/Istanbul")),
    )

    assert prepared.threads == ("Ana tarihsel bölüm." + " x" * 40, "Kaynaklı tarihsel sonuç.")
    assert all("takip edin" not in part.lower() for part in prepared.threads)
    assert "kanalımıza katılın" in prepared.telegram_text
    assert "takip edin" not in prepared.reservation.metadata.published_text.lower()
