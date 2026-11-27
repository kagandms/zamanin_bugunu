"""A closing question the model writes as its own block is merged into the previous block."""

from src.services.ai_service import AIService, _is_question_only_block

HEADER = "🕊️ Tarihte Bugün (20.10.1921)"
QUESTION = "Siz bu konuda ne düşünüyorsunuz?"


def _parse(content: str) -> list[str]:
    threads, _poll, _image = AIService()._parse_ai_response(content, "orig", "20.10.1921")
    return threads


def test_question_only_block_is_merged_into_previous_block() -> None:
    content = f"{HEADER}\n\nİlk olay cümlesi.\n---\nİkinci blok.\n---\n{QUESTION}"
    threads = _parse(content)
    assert len(threads) == 2
    assert threads[-1].endswith(f"İkinci blok.\n\n{QUESTION}")


def test_normal_last_block_is_not_merged() -> None:
    content = f"{HEADER}\n\nİlk olay cümlesi.\n---\nİkinci blok.\n---\nSonuç cümlesi."
    threads = _parse(content)
    assert len(threads) == 3
    assert threads[-1].endswith("Sonuç cümlesi.")


def test_single_block_is_unchanged_by_merge() -> None:
    assert _is_question_only_block(QUESTION) is True
    assert len(_parse(f"{HEADER}\n\nTek blok.")) == 1


def test_long_question_is_not_merged() -> None:
    long_question = ("Bu çok uzun bir soru mu " * 6).strip() + "?"
    assert len(long_question) > 120
    assert _is_question_only_block(long_question) is False
    threads = _parse(f"{HEADER}\n\nİlk olay cümlesi.\n---\n{long_question}")
    assert len(threads) == 2
    assert threads[-1] == long_question
