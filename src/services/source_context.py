from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

MAX_SOURCE_CHARS = 3000
_EVENT_KINDS = {
    "antlas": "treaty", "anlas": "treaty", "saldir": "combat", "catis": "combat",
    "muhareb": "battle", "savas": "war", "deprem": "earthquake", "isyan": "revolt",
    "devrim": "revolution", "suikast": "assassination", "katliam": "massacre",
}
_STOPWORDS = {"bir", "ile", "olan", "olarak", "hakkinda", "bilgi", "silahli", "bu", "ve", "nin", "nda"}
_MONTHS = {"ocak", "subat", "mart", "nisan", "mayis", "haziran", "temmuz", "agustos", "eylul", "ekim", "kasim", "aralik"}
_FACT_STEMS = ("imzala", "durdur", "belirle", "duzenle", "gercekles", "yapil", "kurul", "yenil", "kazan", "karar", "cekil")
_BIO_STEMS = ("dog", "oldu", "uye", "gitarist", "vokal", "sair", "yazar", "besteci", "sanatci")


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


def _complete_sentences(extract: str) -> tuple[str, ...]:
    bounded = extract[:MAX_SOURCE_CHARS]
    protected = re.sub(r"\b(II|III|IV|Dr|Prof|Doç|Bkz)\.", r"\1∯", bounded)
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
            return True
    if identities:
        return False
    return _is_biographical_sentence(words, evidence)


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
