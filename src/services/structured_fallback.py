"""Code-built fallback for events whose model attempts all failed.

Nothing here is generated: the header and hashtag come from code, the event sentence and the one
summary sentence are copied verbatim from the source, and the closing question comes from a fixed bank.
"""
from __future__ import annotations

from src.services.content_guard import EventRewriteRequest, source_summary_sentences
from src.services.source_context import _matches, _words, normalize_fact_text

FALLBACK_QUESTIONS: tuple[str, ...] = (
    "Bu olayı daha önce duymuş muydunuz?",
    "Bu olayı bugün nasıl okuyorsunuz?",
    "Bu tarihte olanlar hakkında ne düşünüyorsunuz?",
    "Bu olayın izlerini bugün hâlâ görmek mümkün mü?",
    "Bu konuda daha önce bir bilginiz var mıydı?",
    "Sizce bu olay tarih kitaplarında nasıl anlatılıyor?",
)
_STOP = {"bir", "ile", "olan", "olarak", "hakkinda", "bilgi", "ve", "bu", "icin", "daha", "kadar", "gibi"}


def choose_fallback_question(recent_texts: list[str] | tuple[str, ...]) -> str:
    """The least-used question in recent published texts; first in bank order on ties."""
    recent = normalize_fact_text("\n".join(recent_texts))
    counts = [recent.count(normalize_fact_text(question.rstrip("?"))) for question in FALLBACK_QUESTIONS]
    return FALLBACK_QUESTIONS[counts.index(min(counts))]


def best_overlap_sentence(event_text: str, sentences: tuple[str, ...]) -> str | None:
    """The source sentence sharing the most meaningful words with the event; verbatim, or None."""
    event_words = [word for word in _words(event_text) if len(word) >= 4 and word not in _STOP]
    event_norm = normalize_fact_text(event_text).strip(" .")
    best: tuple[int, str] | None = None
    for sentence in sentences:
        if normalize_fact_text(sentence).strip(" .") == event_norm:
            continue
        overlap = len({word for word in _words(sentence) if _matches(word, event_words)})
        if overlap >= 1 and (best is None or overlap > best[0]):
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
    return [first, choose_fallback_question(recent_texts)], best
