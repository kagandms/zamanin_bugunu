from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


CONTENT_GUARD_VERSION = "fact-guard-v3"
KARS_SOURCE_URL = "https://kutuphane.ttk.gov.tr/details?id=541556&materialType=NE&query=G%C3%BCrcistan+_+T%C3%BCrkiye."
KARS_SCOPE_SOURCE_URL = "https://ttk.gov.tr/istiklal-harbi/"
II_MURAD_SOURCE_URL = "https://tr.wikipedia.org/wiki/II._Murad"
II_KOSOVO_SOURCE_URL = "https://tr.wikipedia.org/wiki/II._Kosova_Muharebesi"


@dataclass(frozen=True)
class EventRewriteRequest:
    original_text: str
    formatted_date: str
    year: Optional[str] = None
    source_title: Optional[str] = None
    source_url: Optional[str] = None


@dataclass(frozen=True)
class EventFactProfile:
    profile_id: str
    source_id: str
    source_url: str
    facts: tuple[str, ...]
    event_years: tuple[str, ...]
    context_years: tuple[str, ...]
    fallback_context: tuple[str, ...] = ()


def normalize_fact_text(text: str) -> str:
    """Normalize Turkish text for deterministic, accent-insensitive checks."""
    decomposed = unicodedata.normalize("NFKD", text.casefold().replace("ı", "i"))
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def resolve_fact_profile(request: EventRewriteRequest) -> Optional[EventFactProfile]:
    """Return curated source facts only for an explicitly recognized event."""
    source_text = normalize_fact_text(request.original_text)
    has_kars_treaty = "kars antlasmas" in source_text or "kars muahedenames" in source_text
    has_1921 = "1921" in source_text or request.year == "1921"
    if not has_kars_treaty or not has_1921:
        return _resolve_ii_kosovo_profile(request)
    return EventFactProfile(
        profile_id="kars-treaty-1921",
        source_id="ttk-library-541556+ttk-istiklal-harbi",
        source_url=KARS_SOURCE_URL,
        facts=(
            "Kars Muahedenâmesi 13 Ekim 1921 tarihinde Kars'ta imzalandı.",
            "Türk Tarih Kurumu Kütüphanesi kaydı Türkiye, Ermenistan, Azerbaycan ve Gürcistan hükümetlerini taraf olarak listeler.",
            "Türk Tarih Kurumu İstiklal Harbi özeti, Batı Cephesi'ndeki mücadelenin Eylül 1922'ye kadar sürdüğünü kaydeder.",
        ),
        event_years=("1921",),
        context_years=("1922",),
    )


def _resolve_ii_kosovo_profile(request: EventRewriteRequest) -> Optional[EventFactProfile]:
    source_url = (request.source_url or "").rstrip("/")
    source_text = normalize_fact_text(request.original_text)
    is_ii_murad_source = source_url == II_MURAD_SOURCE_URL
    mentions_kosovo = "kosova" in source_text
    if not (is_ii_murad_source and mentions_kosovo and request.year == "1448"):
        return None
    return EventFactProfile(
        profile_id="ii-kosovo-1448",
        source_id="tr-wikipedia-II-Murad+II-Kosova-Muharebesi",
        source_url=II_KOSOVO_SOURCE_URL,
        facts=(
            "II. Kosova Muharebesi'nde 19 Ekim sabahı son barikatlar aşıldı ve savaş kesin Osmanlı zaferiyle sonuçlandı.",
            "Kaynak, yenilginin Balkanlar'ı geri alma girişimlerini uzun süre durdurduğunu ve İstanbul'a batıdan gelebilecek askerî tehdidi azalttığını belirtiyor.",
        ),
        event_years=("1448",),
        context_years=(),
        fallback_context=(
            "II. Murad'ın yönettiği II. Kosova Muharebesi'nde son barikatlar aşıldı; savaş kesin Osmanlı zaferiyle sonuçlandı.",
            "Kaynağa göre bu yenilgi, Balkanlar'ı geri alma girişimlerini uzun süre durdurdu; batıdan İstanbul'a gelebilecek askerî tehdit de azaldı.",
        ),
    )


def get_source_fact_status(profile: Optional[EventFactProfile]) -> str:
    """Distinguish scoped source checks from events with no fact profile."""
    return "checked_scoped" if profile is not None else "not_checked"


def validate_event_content(
    parts: list[str], request: EventRewriteRequest, profile: Optional[EventFactProfile]
) -> tuple[str, ...]:
    """Reject known source contradictions without treating keywords as global bans."""
    if profile is None:
        return ()

    normalized = normalize_fact_text("\n".join(parts))
    reasons: list[str] = []
    if _claims_moscow_as_kars_signing_place(normalized):
        reasons.append("unsupported_signing_location")
    if _claims_unsupported_georgian_border_change(normalized):
        reasons.append("unsupported_border_claim")
    if _claims_national_war_ended_or_was_still_ongoing(normalized):
        reasons.append("unsupported_war_scope")
    if _contains_unsupported_year(normalized, profile):
        reasons.append("unsupported_year")
    return tuple(reasons)


def _claims_moscow_as_kars_signing_place(text: str) -> bool:
    for sentence in re.split(r"[.!?\n]+", text):
        mentions_kars_treaty = re.search(r"kars\s+(?:antlasmas\w*|muahedenames\w*)", sentence)
        moscow_location = re.search(r"moskova[\W_]*(?:da|de|ta|te)\b", sentence)
        has_signing_verb = re.search(
            r"imzala\w*|imza\s+at\w*|akdet\w*|akdedil\w*", sentence
        )
        kars_location = re.search(r"kars[\W_]*(?:ta|te|da|de|kentinde)\b", sentence)
        if (mentions_kars_treaty and moscow_location and has_signing_verb and not kars_location
                and not _negates_moscow_signing_claim(sentence, moscow_location.end())):
            return True
    return False


def _negates_moscow_signing_claim(sentence: str, location_end: int) -> bool:
    following_text = sentence[location_end:location_end + 35]
    denies_location = re.match(r"[\W_]*degil\b", following_text)
    denies_signing = re.search(r"imzala(?:n)?m(?:adi|amis|ayacak|az)\b", following_text)
    return bool(denies_location or denies_signing)


def _claims_national_war_ended_or_was_still_ongoing(text: str) -> bool:
    for sentence in re.split(r"[.!?\n]+", text):
        names_national_war = re.search(r"kurtulus savasi|istiklal harbi", sentence)
        asserts_end = re.search(r"sona er\w*|bitt\w*|tamamlan\w*", sentence)
        implies_ongoing = re.search(r"devam ed\w*.{0,35}(?:gibi|mis gibi)|hala sur\w*", sentence)
        front_scoped = _is_front_scoped_war_statement(sentence)
        denies_claim = _denies_war_claim(sentence)
        if names_national_war and (asserts_end or implies_ongoing) and not front_scoped and not denies_claim:
            return True
    return False


def _is_front_scoped_war_statement(sentence: str) -> bool:
    front = re.search(r"(?:dogu|bati)\s+cephes\w*", sentence)
    war = re.search(r"kurtulus savasi|istiklal harbi", sentence)
    if not front or not war or front.start() > war.start():
        return False
    return war.start() - front.end() <= 45


def _denies_war_claim(sentence: str) -> bool:
    return bool(re.search(r"sona ermed\w*|bitmed\w*|devam etmiyor\w*|surmed\w*", sentence))


def _claims_unsupported_georgian_border_change(text: str) -> bool:
    return bool(re.search(r"gurciles\w*.{0,40}sinir|sinir.{0,40}gurciles\w*", text))


def _contains_unsupported_year(text: str, profile: EventFactProfile) -> bool:
    for sentence in re.split(r"[.!?\n]+", text):
        for year in re.findall(r"\b(?:1[0-9]{3}|20[0-9]{2})\b", sentence):
            if year in profile.event_years:
                continue
            if year in profile.context_years and _is_supported_year_context(sentence, year):
                continue
            return True
    return False


def _is_supported_year_context(sentence: str, year: str) -> bool:
    if year != "1922":
        return False
    return bool(
        re.search(r"bati\s+cephes", sentence)
        and re.search(r"eylul", sentence)
        and re.search(r"mucadele", sentence)
        and re.search(r"sur\w*|uzan\w*", sentence)
    )
