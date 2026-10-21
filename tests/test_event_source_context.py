from __future__ import annotations

from copy import deepcopy
from datetime import datetime

import pytest

from src.event_preparation import _rewrite_request
from src.services.ai_service import AIService
from src.services.content_guard import resolve_fact_profile
from src.services.content_service import ContentService

# Sanitized current-feed examples reviewed on 2026-10-21, not archived production inputs.
ANKARA_EVENT = (
    "Fransızlar'ın Anadolu'dan çekilmesi. TBMM ile Fransa hükûmeti arasında Ankara Anlaşması imzalandı. "
    "Fransa adına Henry Franklin-Bouillon'un sürdürdüğü görüşmeler sonrasında, Fransa işgal ettiği Anadolu topraklarından çekildi."
)
DAGLICA_EVENT = (
    "Saat 00:20 sıralarında, Irak'ın kuzeyinden Türkiye'ye sızan PKK mensupları tarafından, "
    "Türk Silahlı Kuvvetleri'nin Dağlıca'da konuşlu piyade taburunun emniyet unsuru olan bir bölüğe "
    "kalabalık bir grupla üç ayrı bölgeden silahlı saldırıda bulunuldu. Genelkurmay çıkan çatışmada "
    "12 şehit, 16 yaralı verildiğini ve 32 PKK'lının da öldürüldüğünü açıkladı. "
    "Bkz. 21 Ekim 2007 Hakkâri PKK çatışması maddesi."
)
FRENCH_INTRO = (
    "Fransızlar, Fransa'da yaşayan, Fransa'nın vatandaşlığına sahip veya bir Cermen kavmi olan Frank kökenli bir halktır. "
    '"Francia" sözcüğünün kökü de bu kelimeden gelmektedir, Frenklerin yurdu ve yaşadıkları bölge anlamına gelir.'
)
IRAQ_INTRO = (
    "Irak, resmî adıyla Irak Cumhuriyeti, Batı Asya'da yer alan bir ülkedir. "
    "Güneyde Suudi Arabistan, kuzeyde Türkiye, doğuda İran, güneydoğuda Basra Körfezi ve Kuveyt, "
    "güneybatıda Ürdün ve batıda Suriye ile komşudur."
)
ANKARA_CONTEXT = (
    "Ankara Antlaşması, TBMM ve Fransız Hükûmeti arasında Türk-Fransız Cephesi'ndeki faaliyetleri durdurmuştur. "
    "TBMM yönetimindeki bölgenin güney sınırının taslak olarak belirlenmesine karar verilmiştir, "
    "ama asıl politik kararları Lozan Antlaşması'na bırakmıştır."
)
DAGLICA_CONTEXT = (
    "21 Ekim 2007 Dağlıca saldırısı, 21 Ekim 2007 tarihinde saat 00.20'de PKK'nın Hakkâri ilinin "
    "Yüksekova ilçesine bağlı Dağlıca köyünde konuşlu Türk Silahlı Kuvvetleri Komando Taburuna "
    "karşı ağır silahlarla düzenlediği saldırıdır."
)


def page(title: str, extract: str) -> dict[str, object]:
    return {"title": title, "extract": extract,
            "content_urls": {"desktop": {"page": f"https://example.test/{title}"}}}


def candidate(event: str, pages: list[dict[str, object]], year: int | None = None) -> dict[str, object]:
    event_year = year if year is not None else (1921 if "Ankara" in event else 2007)
    return {"text": event, "year": event_year, "pages": pages}


@pytest.fixture(autouse=True)
def forbid_external_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_client(*args: object, **kwargs: object) -> None:
        raise AssertionError("No external clients may be used in source-selection tests")

    monkeypatch.setattr("httpx.AsyncClient", unexpected_client)


@pytest.mark.parametrize(("event", "title", "intro"), [
    (ANKARA_EVENT, "Fransızlar", FRENCH_INTRO),
    (DAGLICA_EVENT, "Irak", IRAQ_INTRO),
])
@pytest.mark.asyncio
async def test_general_introductions_produce_only_the_original_event(
    event: str, title: str, intro: str,
) -> None:
    request = _rewrite_request(candidate(event, [page(title, intro)]), datetime(2026, 10, 20))

    parts, _, _ = await AIService().rewrite_event_safe(request)

    assert parts == [f"🕊️ Tarihte Bugün ({request.formatted_date})\n\n{event}"]
    assert request.source_context is None
    assert request.source_url is None


@pytest.mark.parametrize(("event", "general", "related"), [
    (ANKARA_EVENT, page("Fransızlar", FRENCH_INTRO), page("Ankara_Antlaşması_(1921)", ANKARA_CONTEXT)),
    (DAGLICA_EVENT, page("Irak", IRAQ_INTRO), page("Ekim_2007_Dağlıca_saldırısı", DAGLICA_CONTEXT)),
])
@pytest.mark.asyncio
async def test_later_event_page_supplies_consistent_source_metadata(
    event: str, general: dict[str, object], related: dict[str, object],
) -> None:
    selected = candidate(event, [general, related])
    original = deepcopy(selected)
    request = _rewrite_request(selected, datetime(2026, 10, 20))
    service = AIService()

    parts, _, _ = await service.rewrite_event_safe(request)

    assert request.source_title == related["title"]
    assert request.source_url == related["content_urls"]["desktop"]["page"]
    assert parts[1].startswith("Kaynak özeti: " + related["extract"].split(". ")[0])
    assert service.last_source_url == request.source_url
    assert service.last_source_id == request.source_title
    assert service.last_generation_model is None
    assert selected == original


@pytest.mark.parametrize(("event", "pages", "related"), [
    (ANKARA_EVENT, [
        page("Fransızlar", FRENCH_INTRO), page("Anadolu", "Anadolu, Asya ve Avrupa arasında bir yarımadadır."),
        page("Türkiye Büyük Millet Meclisi", "TBMM, Türkiye'nin yasama organıdır."),
        page("Fransa", "Fransa, Batı Avrupa'da bir ülkedir."),
        page("Ankara_Antlaşması_(1921)", ANKARA_CONTEXT),
    ], "Ankara_Antlaşması_(1921)"),
    (DAGLICA_EVENT, [
        page("Irak", IRAQ_INTRO), page("Türkiye", "Türkiye, Avrupa ve Asya'da toprakları bulunan ülkedir."),
        page("PKK", "PKK, 1978'de kurulmuş silahlı bir örgüttür."),
        page("Türk Silahlı Kuvvetleri", "Türk Silahlı Kuvvetleri, Türkiye'nin askerî kuvvetleridir."),
        page("Dağlıca, Yüksekova", "Dağlıca, Hakkâri ilinin Yüksekova ilçesinde bir köydür."),
        page("Ekim_2007_Dağlıca_saldırısı", DAGLICA_CONTEXT),
    ], "Ekim_2007_Dağlıca_saldırısı"),
])
def test_event_page_is_selected_after_unrelated_linked_pages(
    event: str, pages: list[dict[str, object]], related: str,
) -> None:
    request = _rewrite_request(candidate(event, pages), datetime(2026, 10, 20))

    assert request.source_title == related


def test_generic_page_can_supply_an_explicit_event_sentence_but_not_its_intro() -> None:
    sentence = "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı."
    selected = candidate(ANKARA_EVENT, [page("Fransızlar", FRENCH_INTRO + " " + sentence)])

    request = _rewrite_request(selected, datetime(2026, 10, 20))

    assert request.source_title == "Fransızlar"
    assert request.source_context == sentence


def test_canonical_page_titles_are_kept_for_sentence_validation() -> None:
    sentence = "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı."
    generic = {"titles": {"canonical": "Fransızlar"}, "extract": sentence}
    linked_event = {"titles": {"canonical": "Ankara Antlaşması (1921)"}, "extract": ""}
    request = _rewrite_request(candidate(ANKARA_EVENT, [generic, linked_event]), datetime(2026, 10, 20))

    assert request.source_title == "Fransızlar"
    assert request.source_context == sentence


def test_shared_person_or_country_does_not_validate_a_different_biographical_claim() -> None:
    event = "Ankara Antlaşması imzalandı. Henry Franklin-Bouillon görüşmeleri sürdürdü."
    page_extract = "Henry Franklin-Bouillon, Fransız bir diplomattı. Fransa Batı Avrupa'da bir ülkedir."
    request = _rewrite_request(candidate(event, [page("Henry Franklin-Bouillon", page_extract)]), datetime(2026, 10, 20))

    assert request.source_context is None


@pytest.mark.parametrize(("title", "extract"), [
    (
        "Ankara_Antlaşması_(1923)",
        "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı.",
    ),
    (
        "Ankara_Antlaşması_(1921)",
        "Ankara Antlaşması, 1923'te TBMM ile Fransa arasında imzalandı.",
    ),
    (
        "Ankara Antlaşması",
        "Ankara Antlaşması, 1923'te taraflar arasında yeni bir karar belirledi.",
    ),
    (
        "Ankara Antlaşması",
        "Ankara Antlaşması 1921'de imzalandı; 1923'te aynı adla imzalanıp sonuçları değişti.",
    ),
])
@pytest.mark.asyncio
async def test_explicit_other_year_rejects_same_named_wrong_event(
    title: str, extract: str,
) -> None:
    request = _rewrite_request(
        candidate("Ankara Antlaşması imzalandı.", [page(title, extract)], year=1921),
        datetime(2026, 10, 20),
    )

    parts, _, _ = await AIService().rewrite_event_safe(request)

    assert request.source_context is None
    assert len(parts) == 1
    assert "Kaynak özeti:" not in parts[0]


def test_different_year_for_a_later_outcome_remains_valid() -> None:
    result_sentence = (
        "Ankara Antlaşması'nın ardından güney sınırı 1923'te Lozan Antlaşması ile kesinleşti."
    )
    request = _rewrite_request(
        candidate("Ankara Antlaşması imzalandı.", [page("Ankara_Antlaşması_(1921)", result_sentence)], year=1921),
        datetime(2026, 10, 20),
    )

    assert request.source_context == result_sentence


@pytest.mark.parametrize("extract", [
    "", "Ankara Antlaşması", "Ankara Antlaşması imzalanırken...",
    "Ankara Antlaşması çok önemliydi.",
    "Fransa 1921 yılında önemli bir adım attı.",
    "Ankara Antlaşması hakkında bilgi.",
])
@pytest.mark.asyncio
async def test_empty_incomplete_or_ambiguous_context_does_not_add_a_second_part(extract: str) -> None:
    request = _rewrite_request(candidate(ANKARA_EVENT, [page("Ankara Antlaşması", extract)]), datetime(2026, 10, 20))

    parts, _, _ = await AIService().rewrite_event_safe(request)

    assert len(parts) == 1
    assert "Kaynak özeti" not in parts[0]
    assert "Bu paylaşımda" not in parts[0]


def test_unrelated_tail_is_not_copied_after_a_relevant_sentence() -> None:
    sentence = "Ankara Antlaşması, 1921'de TBMM ile Fransa arasında imzalandı."
    selected = candidate(ANKARA_EVENT, [page("Ankara Antlaşması", sentence + " Paris, Fransa'nın başkentidir.")])

    request = _rewrite_request(selected, datetime(2026, 10, 20))

    assert request.source_context == sentence


def test_context_scoring_does_not_reward_a_long_unrelated_intro() -> None:
    unrelated = candidate(ANKARA_EVENT, [page("Fransızlar", FRENCH_INTRO * 20)])
    related = candidate(ANKARA_EVENT, [page("Ankara Antlaşması", ANKARA_CONTEXT)])

    assert ContentService._source_context_score(unrelated) == 0
    assert ContentService._source_context_score(related) > 0
    assert ContentService()._calculate_fame_score(unrelated) == ContentService()._calculate_fame_score(
        candidate(ANKARA_EVENT, [page("Fransızlar", "")])
    )


def test_biography_uses_subject_and_event_relationship_together() -> None:
    selected = {"text": "Burak Güven, Türk bas gitarist ve Mor ve Ötesi grubu üyesi.", "year": 1975,
                "pages": [page("Burak Güven", "Burak Güven, Mor ve Ötesi grubu üyesidir. Burak Güven Fransa'ya seyahat etti.")]}

    request = _rewrite_request(selected, datetime(2026, 10, 19))

    assert request.source_context == "Burak Güven, Mor ve Ötesi grubu üyesidir."


def test_curated_profile_identity_survives_without_usable_page_context() -> None:
    selected = {"text": "Osmanlı padişahı II. Murat, Kosova Zaferi'ni kazandı.", "year": 1448,
                "pages": [page("Irak", IRAQ_INTRO), {"title": "II. Murad", "extract": "",
                "content_urls": {"desktop": {"page": "https://tr.wikipedia.org/wiki/II._Murad"}}}]}

    request = _rewrite_request(selected, datetime(2026, 10, 19))

    assert resolve_fact_profile(request).profile_id == "ii-kosovo-1448"
