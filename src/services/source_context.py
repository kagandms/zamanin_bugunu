from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from collections.abc import Iterable
from dataclasses import dataclass, replace

MAX_SOURCE_CHARS = 3000
SUMMARY_MAX_CHARS = 800
_EVENT_KINDS = {
    "antlas": "treaty", "anlas": "treaty", "saldir": "combat", "catis": "combat",
    "muhareb": "battle", "savas": "war", "deprem": "earthquake", "isyan": "revolt",
    "devrim": "revolution", "suikast": "assassination", "katliam": "massacre",
}
_STOPWORDS = {"bir", "ile", "olan", "olarak", "hakkinda", "bilgi", "silahli", "bu", "ve", "nin", "nda"}
_MONTHS = {"ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz", "agustos", "eylul", "ekim", "kasim", "aralik"}
_FACT_STEMS = ("imzala", "durdur", "belirle", "duzenle", "gercekles", "yapil", "kurul", "yenil", "kazan", "karar", "cekil", "kesinles")
_BIO_STEMS = ("dog", "oldu", "uye", "gitarist", "vokal", "sair", "yazar", "besteci", "sanatci")
_OCCURRENCE_STEMS = ("imzala", "basla", "gercekles", "duzenle", "yapil", "saldir", "catis", "muhareb")
_OUTCOME_STEMS = ("ardindan", "sonras", "sonuc", "etki", "yolac", "sagla", "kesinles", "sonaer", "surdu")
_YEAR_PATTERN = r"\b[1-9][0-9]{2,3}\b"


@dataclass(frozen=True)
class SourceContextInput:
    event_text: str
    year: str | None = None
    title: str | None = None
    extract: str | None = None
    linked_titles: tuple[str, ...] = ()


@dataclass(frozen=True)
class SelectedSource:
    title: str
    url: str | None
    context: str
    specificity: int


def normalize_fact_text(text: str) -> str:
    """Return accent-insensitive text for comparison; preserve source copy separately."""
    decomposed = unicodedata.normalize("NFKD", text.casefold().replace("ı", "i"))
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize_fact_text(text))


def _kind(word: str) -> str | None:
    return next((kind for stem, kind in _EVENT_KINDS.items() if word.startswith(stem)), None)


def _matches(word: str, candidates: list[str]) -> bool:
    return any(word == other or (min(len(word), len(other)) >= 5 and word[:5] == other[:5]) for other in candidates)


def _title_identity(title: str) -> tuple[tuple[str, ...], str] | None:
    words = _words(re.sub(r"\([^)]*\)", "", title))
    kind = next((_kind(word) for word in words if _kind(word)), None)
    anchors = tuple(word for word in words if not _kind(word) and not word.isdigit()
                    and word not in _MONTHS | _STOPWORDS)
    return (anchors, kind) if kind and anchors else None


def _event_identities(evidence: SourceContextInput) -> tuple[tuple[tuple[str, ...], str], ...]:
    words = _words(evidence.event_text)
    identities = []
    for title in (*evidence.linked_titles, evidence.title or ""):
        identity = _title_identity(title)
        if identity and all(_matches(anchor, words) for anchor in identity[0]):
            identities.append(identity)
    # Named event phrases also work inside otherwise general linked pages.
    original = re.findall(r"[^\W_]+", evidence.event_text, re.UNICODE)
    for index, token in enumerate(original):
        if index and _kind(normalize_fact_text(token)) and original[index - 1][0].isupper():
            anchors = [normalize_fact_text(original[index - 1])]
            if len(anchors[0]) <= 3 and index > 1 and original[index - 2][0].isupper():
                anchors.insert(0, normalize_fact_text(original[index - 2]))
            identities.append((tuple(anchors), _kind(normalize_fact_text(token))))
    return tuple(dict.fromkeys(identities))


# Dots that do not end a sentence: initials ("George H."), Roman numerals ("II."), common abbreviations.
_ABBREVIATION_DOT = re.compile(
    r"\b(?:[A-ZÇĞİÖŞÜ]|[IVXLCDM]{1,4}|Dr|Prof|Doç|Bkz|St|Mr|Mrs|Ms|Jr|Sr|Ltd|vb|vs|örn|Dk|Sn|Mö)\.",
)


def _complete_sentences(extract: str) -> tuple[str, ...]:
    bounded = extract[:MAX_SOURCE_CHARS]
    protected = _ABBREVIATION_DOT.sub(lambda match: match.group(0)[:-1] + "∯", bounded)
    sentences = re.findall(r"\S.*?[.!?](?:[\"”’)]*)(?=\s|$)", protected, re.DOTALL)
    return tuple(sentence.replace("∯", ".").strip() for sentence in sentences
                 if not re.search(r"(?:\.\.\.|…)", sentence) and not sentence.endswith(".."))


def _has_fact(words: list[str], stems: tuple[str, ...]) -> bool:
    return any(word.startswith(stem) for word in words for stem in stems)


def _is_event_sentence(sentence: str, evidence: SourceContextInput) -> bool:
    words = _words(sentence)
    if len(words) < 4:
        return False
    identities = _event_identities(evidence)
    for anchors, kind in identities:
        if (all(_matches(anchor, words) for anchor in anchors)
                and any(_kind(word) == kind for word in words)
                and _has_fact(words, _FACT_STEMS)):
            return not _has_conflicting_sentence_year(sentence, evidence)
    if identities:
        return False
    return _is_biographical_sentence(words, evidence)


def _expected_event_year(evidence: SourceContextInput) -> str | None:
    if evidence.year and re.fullmatch(_YEAR_PATTERN, evidence.year):
        return evidence.year
    years = tuple(dict.fromkeys(re.findall(_YEAR_PATTERN, evidence.event_text)))
    return years[0] if len(years) == 1 else None


def _has_conflicting_title_year(title: str, evidence: SourceContextInput) -> bool:
    title_years = set(re.findall(_YEAR_PATTERN, title))
    expected_year = _expected_event_year(evidence)
    return bool(title_years and (expected_year is None or expected_year not in title_years))


def _has_conflicting_sentence_year(sentence: str, evidence: SourceContextInput) -> bool:
    sentence_years = set(re.findall(_YEAR_PATTERN, sentence))
    expected_year = _expected_event_year(evidence)
    if not sentence_years:
        return False
    if expected_year is None:
        return True
    conflicting_years = sentence_years - {expected_year}
    if not conflicting_years:
        return False
    words = _words(sentence)
    has_occurrence = _has_fact(words, _OCCURRENCE_STEMS)
    has_outcome = _has_fact(words, _OUTCOME_STEMS)
    if has_outcome and not has_occurrence:
        return False
    return True


def _is_biographical_sentence(words: list[str], evidence: SourceContextInput) -> bool:
    subject = _words(re.sub(r"\([^)]*\)", "", evidence.title or ""))
    event = _words(evidence.event_text)
    if len(subject) < 2 or not all(_matches(word, event) and _matches(word, words) for word in subject):
        return False
    shared_roles = [stem for stem in _BIO_STEMS if any(word.startswith(stem) for word in event)
                    and any(word.startswith(stem) for word in words)]
    dated_life_fact = evidence.year in words and _has_fact(words, ("dog", "oldu"))
    return bool(shared_roles or dated_life_fact)


def relevant_source_sentences(evidence: SourceContextInput) -> tuple[str, ...]:
    """Return only complete, explicitly event-related sentences; no inference or rewriting."""
    return tuple(dict.fromkeys(sentence for sentence in _complete_sentences(evidence.extract or "")
                               if _is_event_sentence(sentence, evidence)))


def _read_page(page: Mapping[str, object], event: SourceContextInput) -> SelectedSource | None:
    title = (page.get("titles") or {}).get("canonical") or page.get("title")
    extract = page.get("extract")
    if not isinstance(title, str) or not isinstance(extract, str):
        return None
    if _has_conflicting_title_year(title, event):
        return None
    evidence = SourceContextInput(event.event_text, event.year, title, extract, event.linked_titles)
    sentences = relevant_source_sentences(evidence)
    if not sentences:
        return None
    url = ((page.get("content_urls") or {}).get("desktop") or {}).get("page")
    specificity = int(_title_identity(title) in _event_identities(evidence))
    return SelectedSource(title, url if isinstance(url, str) else None, " ".join(sentences), specificity)


def select_event_source(candidate: Mapping[str, object]) -> SelectedSource | None:
    """Choose one linked page and its related sentences, preferring an explicit event title."""
    pages = candidate.get("pages") or []
    titles = tuple(str((page.get("titles") or {}).get("canonical") or page.get("title") or "") for page in pages)
    year = str(candidate["year"]) if candidate.get("year") is not None else None
    event = SourceContextInput(str(candidate.get("text") or ""), year, linked_titles=titles)
    sources = [source for page in pages if (source := _read_page(page, event)) is not None]
    return max(sources, key=lambda source: (source.specificity, len(source.context)), default=None)


def complete_sentences(text: str) -> tuple[str, ...]:
    """Public view of the bounded, complete-sentence splitter used for source text."""
    return _complete_sentences(text)


def bounded_summary(sentences: Iterable[str], max_chars: int = SUMMARY_MAX_CHARS) -> tuple[str, ...]:
    """Keep unique sentences in source order while the joined text stays within max_chars."""
    selected: list[str] = []
    total = 0
    for sentence in dict.fromkeys(sentences):
        extra = len(sentence) + (1 if selected else 0)
        if total + extra > max_chars:
            break
        selected.append(sentence)
        total += extra
    return tuple(selected)


_GENERIC_LEAD = re.compile(r"\b(?:ulke|halk|sehir|kent|yarimada|ilce|nehir|kita)\w*")
SUMMARY_TITLE_ROUTE_MIN_CHARS = 100


def _title_words(title: str) -> tuple[str, ...]:
    words = _words(re.sub(r"\([^)]*\)", "", title))
    return tuple(word for word in words
                 if len(word) >= 4 and not word.isdigit() and word not in _MONTHS | _STOPWORDS)


def _is_generic_lead(extract: str) -> bool:
    """True when the page opens by defining a broad country, people group, city or region."""
    sentences = _complete_sentences(extract)
    return bool(sentences) and _GENERIC_LEAD.search(normalize_fact_text(sentences[0])) is not None


def _event_detail_words(event_text: str, title: str | None) -> list[str]:
    subject = _title_words(title or "")
    return [word for word in _title_words(event_text) if not _matches(word, list(subject))] if subject else \
        list(_title_words(event_text))


def _page_summary(title: str | None, extract: str, evidence: SourceContextInput) -> tuple[str, ...]:
    """Page sentences that belong to the event: strictly related, or sharing the event's own anchor or detail."""
    generic = _is_generic_lead(extract)
    anchors = _title_identity(title or "")
    anchor_words = list(anchors[0]) if anchors else []
    details = [] if generic else _event_detail_words(evidence.event_text, title)
    strict = set(relevant_source_sentences(SourceContextInput(
        evidence.event_text, evidence.year, title, extract, evidence.linked_titles,
    )))
    kept: list[str] = []
    for sentence in _complete_sentences(extract):
        words = _words(sentence)
        shares_anchor = bool(anchor_words) and any(_matches(word, anchor_words) for word in words)
        # A shared country or common word is not enough; two distinct event details make it event-specific.
        shares_detail = bool(details) and len({word for word in words if _matches(word, details)}) >= 2
        if sentence not in strict and not (shares_anchor or shares_detail):
            continue
        if _has_conflicting_sentence_year(sentence, evidence):
            continue
        kept.append(sentence)
    return bounded_summary(kept)


def _title_routes_to_event(title: str, extract: str, event_text: str) -> bool:
    """A page whose own title names the event's subject, and whose lead is not a generic definition."""
    title_words = _title_words(title)
    event_words = _title_words(event_text)
    if not title_words or not event_words or _is_generic_lead(extract):
        return False
    return any(_matches(word, list(event_words)) for word in title_words)


def summary_sentences(title: str | None, extract: str, evidence: SourceContextInput) -> tuple[str, ...]:
    """Public helper: the bounded event-related summary of one page."""
    return _page_summary(title, extract, evidence)


def _is_event_label(title: str, event_text: str) -> bool:
    """True when the event text opens with a label equal to this page's title (a broad topic page)."""
    if ":" not in event_text:
        return False
    label = event_text.split(":", 1)[0]
    if len(label) > 80:
        return False
    return tuple(_words(label)) == tuple(_words(re.sub(r"\([^)]*\)", "", title)))


def select_event_summary(candidate: Mapping[str, object]) -> SelectedSource | None:
    """Choose the page that best describes the event and return its bounded summary.

    A page qualifies when it has strictly event-related sentences, or when its title names the
    event's subject, its lead is not a generic definition and its summary is substantial enough.
    """
    pages = candidate.get("pages") or []
    titles = tuple(str((page.get("titles") or {}).get("canonical") or page.get("title") or "") for page in pages)
    year = str(candidate["year"]) if candidate.get("year") is not None else None
    event_text = str(candidate.get("text") or "")
    event = SourceContextInput(event_text, year, linked_titles=titles)
    options: list[SelectedSource] = []
    for page in pages:
        title = str((page.get("titles") or {}).get("canonical") or page.get("title") or "")
        extract = page.get("extract")
        if not title or not isinstance(extract, str) or _has_conflicting_title_year(title, event):
            continue
        if _is_event_label(title, event_text):
            # "II. Dünya Savaşı: ..." – a page titled with the event's own label describes the broad topic.
            continue
        sentences = _page_summary(title, extract, event)
        if not sentences:
            continue
        page_evidence = SourceContextInput(event_text, year, title, extract, titles)
        strict = bool(relevant_source_sentences(page_evidence))
        substantial = len(" ".join(sentences)) >= SUMMARY_TITLE_ROUTE_MIN_CHARS
        if not strict and not (substantial and _title_routes_to_event(title, extract, event_text)):
            continue
        url = ((page.get("content_urls") or {}).get("desktop") or {}).get("page")
        specificity = int(_title_identity(title) in _event_identities(page_evidence))
        options.append(SelectedSource(title, url if isinstance(url, str) else None, " ".join(sentences), specificity))
    return max(options, key=lambda source: (source.specificity, len(source.context)), default=None)
