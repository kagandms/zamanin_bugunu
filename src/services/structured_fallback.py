"""Code-built fallback for events whose model attempts all failed.

Nothing here is generated: the header and hashtag come from code, the event sentence and the one
summary sentence are copied verbatim from the source, and the closing question comes from a fixed bank.
"""
from __future__ import annotations

import re

from src.services.content_guard import EventRewriteRequest, ends_with_ordinal_stub, source_summary_sentences, unattributed_loaded_terms
from src.services.source_context import _matches, _words, normalize_fact_text

# General questions: safe for every event, including conflicts and politics.
GENERAL_QUESTIONS: tuple[str, ...] = (
    "Bu olayı bugün nasıl okuyorsunuz?",
    "Bu olay hakkında ne biliyordunuz?",
    "Bu olayı daha önce duymuş muydunuz?",
    "Bu konuda daha önce bir bilginiz var mıydı?",
)
# Only when the second part carries a concrete number or name that "this detail" can point to.
DETAIL_QUESTION = "Bu ayrıntıyı daha önce duymuş muydunuz?"
# Open questions that invite an opinion; not used for conflict and politics events.
OPEN_QUESTIONS: tuple[str, ...] = (
    "Bu olayın izlerini bugün hâlâ görmek mümkün mü?",
    "Sizce bu olay tarih kitaplarında nasıl anlatılıyor?",
)
EVENT_QUESTIONS: tuple[str, ...] = GENERAL_QUESTIONS + (DETAIL_QUESTION,) + OPEN_QUESTIONS
# "Do you know this name?" is only for little-known people; leaders and famous figures get the neutral one.
KNOWN_PERSON_QUESTIONS: tuple[str, ...] = ("Bu kişi hakkında ne biliyordunuz?",)
PERSON_QUESTIONS: tuple[str, ...] = KNOWN_PERSON_QUESTIONS + ("Bu ismi tanıyor muydunuz?",)
LEADER_ROOTS: tuple[str, ...] = (
    "cumhurbaskan", "basbakan", "padisah", "halife", "kral", "imparator", "maresal", "baskomutan", "kurucu",
)
_MEMORIAL = re.compile(r"\böldü\b|vefat|hayatını kaybet|ulusal yas|\banma\b|ölümü|ölüm yıl", re.IGNORECASE)
FALLBACK_QUESTIONS: tuple[str, ...] = EVENT_QUESTIONS + PERSON_QUESTIONS
CONFLICT_ROOTS: tuple[str, ...] = (
    "savas", "muhareb", "catis", "saldir", "isgal", "darbe", "isyan", "katliam", "soykirim", "teror",
    "secim", "hukumet", "iktidar", "anayasa", "referandum", "devrim", "ihtilal", "cumhurbaskan", "basbakan", "parti",
)
_MIN_NEW_WORDS = 2  # a summary sentence must add at least this many meaningful words the event lacks
_REPEAT_SHARE = 0.5  # share of meaningful words already in the event at which a sentence counts as a repeat
_STOP = {"bir", "ile", "olan", "olarak", "hakkinda", "bilgi", "ve", "bu", "icin", "daha", "kadar", "gibi"}


_PERSON_EVENT = re.compile(r"\((?:d|ö)\.\s*\d|doğdu|öldü|hayatını kaybet", re.IGNORECASE)


def event_kind(event_text: str) -> str:
    """'person' for birth/death records, otherwise 'event' (battles, treaties, decisions, etc.)."""
    return "person" if _PERSON_EVENT.search(event_text or "") else "event"


def is_conflict_or_politics(event_text: str) -> bool:
    words = _words(event_text)
    return any(word.startswith(root) for word in words for root in CONFLICT_ROOTS)


def mentions_leader(*texts: str) -> bool:
    words = _words(" ".join(texts))
    return any(word.startswith(root) for word in words for root in LEADER_ROOTS)


def is_memorial_of_leader(event_text: str, context_text: str = "") -> bool:
    """A death/mourning record of a leader or political figure: no closing question, it would be off-tone."""
    joined = f"{event_text} {context_text}"
    return bool(_MEMORIAL.search(joined)) and (mentions_leader(joined) or is_conflict_or_politics(joined))


def has_concrete_detail(context_text: str, event_text: str = "") -> bool:
    """A number that is not a year, or a proper name the event sentence does not already carry."""
    if not context_text.strip():
        return False
    if any(len(number) < 4 for number in re.findall(r"\d+", context_text)):
        return True
    event_norm = normalize_fact_text(event_text)
    for sentence in re.split(r"[.!?\n]+", context_text):
        for token in re.findall(r"[^\W\d_]+", sentence)[1:]:
            if token[0].isupper() and normalize_fact_text(token)[:5] not in event_norm:
                return True
    return False


def question_bank(event_text: str, context_text: str = "") -> tuple[str, ...]:
    """Questions allowed for this event: kind, topic sensitivity and whether a concrete detail exists."""
    if event_kind(event_text) == "person":
        return KNOWN_PERSON_QUESTIONS if mentions_leader(event_text, context_text) else PERSON_QUESTIONS
    bank = list(GENERAL_QUESTIONS)
    if has_concrete_detail(context_text, event_text):
        bank.append(DETAIL_QUESTION)
    if not is_conflict_or_politics(event_text):
        bank.extend(OPEN_QUESTIONS)
    return tuple(bank)


def choose_fallback_question(
    recent_texts: list[str] | tuple[str, ...], event_text: str = "", context_text: str = "",
) -> str:
    """The least-used allowed question in recent published texts; bank order on ties; '' when none fits."""
    if is_memorial_of_leader(event_text, context_text):
        return ""
    bank = question_bank(event_text, context_text)
    recent = normalize_fact_text("\n".join(recent_texts))
    counts = [recent.count(normalize_fact_text(question.rstrip("?"))) for question in bank]
    return bank[counts.index(min(counts))]


_DEFINITION_END = re.compile(r"(?:d[ıiuü]r|t[ıiuü]r)\.?$|olarak da bilinir")


def is_definition_sentence(sentence: str, event_words: list[str]) -> bool:
    """'X, ... -dır': the encyclopedia definition of a person the event sentence already names."""
    head = re.match(r"([A-ZÇĞİÖŞÜ][^,]{2,70}),\s", sentence)
    if not head or not _DEFINITION_END.search(sentence.strip()):
        return False
    return any(_matches(word, event_words) for word in _words(head.group(1)) if len(word) >= 4)


def best_overlap_sentence(event_text: str, sentences: tuple[str, ...]) -> str | None:
    """The source sentence sharing the most meaningful words with the event; verbatim, or None."""
    event_words = [word for word in _words(event_text) if len(word) >= 4 and word not in _STOP]
    event_norm = normalize_fact_text(event_text).strip(" .")
    best: tuple[int, str] | None = None
    for sentence in sentences:
        if normalize_fact_text(sentence).strip(" .") == event_norm:
            continue
        if unattributed_loaded_terms(sentence) or is_definition_sentence(sentence, event_words):
            continue
        sentence_words = [word for word in _words(sentence) if len(word) >= 4 and word not in _STOP]
        matched = [word for word in sentence_words if _matches(word, event_words)]
        new_words = [word for word in sentence_words if not _matches(word, event_words)]
        if not matched or len(new_words) < _MIN_NEW_WORDS:
            # No event link, or the sentence only repeats what the event already says.
            continue
        if len(matched) / len(sentence_words) >= _REPEAT_SHARE:
            # Root overlap with the event is high: the sentence repeats the event's facts.
            continue
        overlap = len(set(matched))
        if best is None or overlap > best[0]:
            best = (overlap, sentence)
    return best[1] if best else None


def build_structured_parts(
    request: EventRewriteRequest,
    recent_texts: list[str] | tuple[str, ...],
    header_emoji: str,
    block_limit: int,
) -> tuple[list[str], str | None]:
    """Return [first block, question] and the summary sentence used (if any)."""
    event = request.original_text.strip()
    if event and event[-1] not in ".!?":
        event += "."
    best = best_overlap_sentence(request.original_text, source_summary_sentences(request))
    if best and ends_with_ordinal_stub(best):
        best = None
    header = f"{header_emoji} Tarihte Bugün ({request.formatted_date})"
    body = f"{event} {best} #tarih" if best else f"{event} #tarih"
    first = f"{header}\n\n{body}"
    if len(first) > block_limit and best:
        best = None
        first = f"{header}\n\n{event} #tarih"
    if len(first) > block_limit:
        first = first[:block_limit - 3].rstrip() + "..."
    question = choose_fallback_question(recent_texts, request.original_text, best or "")
    return ([first, question] if question else [first]), best
