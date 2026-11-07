"""Code-built fallback for events whose model attempts all failed.

Nothing here is generated: the header and hashtag come from code, the event sentence and the one
summary sentence are copied verbatim from the source, and the closing question comes from a fixed bank.
"""
from __future__ import annotations

import re

from src.services.content_guard import EventRewriteRequest, source_summary_sentences
from src.services.source_context import _matches, _words, normalize_fact_text

EVENT_QUESTIONS: tuple[str, ...] = (
    "Bu ayrıntıyı daha önce duymuş muydunuz?",
    "Bu olayı bugün nasıl okuyorsunuz?",
    "Bu olayın izlerini bugün hâlâ görmek mümkün mü?",
    "Bu konuda daha önce bir bilginiz var mıydı?",
    "Sizce bu olay tarih kitaplarında nasıl anlatılıyor?",
)
PERSON_QUESTIONS: tuple[str, ...] = (
    "Bu ismi tanıyor muydunuz?",
    "Bu kişiyi daha önce duymuş muydunuz?",
    "Bu isim hakkında ne biliyorsunuz?",
)
FALLBACK_QUESTIONS: tuple[str, ...] = EVENT_QUESTIONS + PERSON_QUESTIONS
_MIN_NEW_WORDS = 2  # a summary sentence must add at least this many meaningful words the event lacks
_REPEAT_SHARE = 0.5  # share of meaningful words already in the event at which a sentence counts as a repeat
_STOP = {"bir", "ile", "olan", "olarak", "hakkinda", "bilgi", "ve", "bu", "icin", "daha", "kadar", "gibi"}


_PERSON_EVENT = re.compile(r"\((?:d|ö)\.\s*\d|doğdu|öldü|hayatını kaybet", re.IGNORECASE)


def event_kind(event_text: str) -> str:
    """'person' for birth/death records, otherwise 'event' (battles, treaties, decisions, etc.)."""
    return "person" if _PERSON_EVENT.search(event_text or "") else "event"


def choose_fallback_question(recent_texts: list[str] | tuple[str, ...], event_text: str = "") -> str:
    """The least-used question of the event's kind in recent published texts; bank order on ties."""
    bank = PERSON_QUESTIONS if event_kind(event_text) == "person" else EVENT_QUESTIONS
    recent = normalize_fact_text("\n".join(recent_texts))
    counts = [recent.count(normalize_fact_text(question.rstrip("?"))) for question in bank]
    return bank[counts.index(min(counts))]


def best_overlap_sentence(event_text: str, sentences: tuple[str, ...]) -> str | None:
    """The source sentence sharing the most meaningful words with the event; verbatim, or None."""
    event_words = [word for word in _words(event_text) if len(word) >= 4 and word not in _STOP]
    event_norm = normalize_fact_text(event_text).strip(" .")
    best: tuple[int, str] | None = None
    for sentence in sentences:
        if normalize_fact_text(sentence).strip(" .") == event_norm:
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
    header = f"{header_emoji} Tarihte Bugün ({request.formatted_date})"
    body = f"{event} {best} #tarih" if best else f"{event} #tarih"
    first = f"{header}\n\n{body}"
    if len(first) > block_limit and best:
        best = None
        first = f"{header}\n\n{event} #tarih"
    if len(first) > block_limit:
        first = first[:block_limit - 3].rstrip() + "..."
    return [first, choose_fallback_question(recent_texts, request.original_text)], best
