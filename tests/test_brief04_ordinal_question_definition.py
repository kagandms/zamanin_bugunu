"""Brief #4: ordinal numbers do not end sentences, leader/memorial questions, definition sentences in fallback.

Pure unit tests: no network, no model calls. Texts mirror live posts 274 and 275.
"""
from __future__ import annotations

from src.services.content_guard import EventRewriteRequest, ends_with_ordinal_stub, validate_source_bound_content
from src.services.source_context import _complete_sentences
from src.services.structured_fallback import (
    best_overlap_sentence,
    build_structured_parts,
    choose_fallback_question,
    question_bank,
)

VAHDETTIN_EVENT = "Osmanlı padişahı VI. Mehmet Vahdettin, son Selamlık törenine katıldı."
VAHDETTIN_DEFINITION = (
    "VI. Mehmed ya da Mehmed Vahideddin, Osmanoğlu ailesinde Şahbaba olarak da bilinir, "
    "Osmanlı İmparatorluğu'nun 36. ve son padişahıdır."
)
VAHDETTIN_SECOND = "Selamlık töreni, padişahın cuma namazına çıkışını gösteren bir saray geleneğiydi."

ATATURK_EVENT = (
    "Türkiye Cumhuriyeti'nin kurucu cumhurbaşkanı Mustafa Kemal Atatürk, Türkiye saati ile 9.05'te "
    "Dolmabahçe Sarayı'nda 57 yaşındayken öldü."
)
ATATURK_DEFINITION = (
    "Mustafa Kemal Atatürk, Türk mareşal, devlet adamı, yazar, Türk Kurtuluş Savaşı'nın başkomutanı, "
    "Türkiye Cumhuriyeti'nin kurucusu ve ilk cumhurbaşkanıdır."
)
ATATURK_MOURNING = "Türkiye'de ulusal yas ilan edildi."


def test_ordinal_number_does_not_end_a_sentence() -> None:
    sentences = _complete_sentences("Osmanlı İmparatorluğu'nun 36. ve son padişahıdır.")
    assert sentences == ("Osmanlı İmparatorluğu'nun 36. ve son padişahıdır.",)


def test_year_followed_by_new_sentence_still_splits() -> None:
    assert _complete_sentences("1938'de öldü. 10 Kasım günü yas ilan edildi.") == (
        "1938'de öldü.", "10 Kasım günü yas ilan edildi.",
    )


def test_ordinal_stub_detection() -> None:
    assert ends_with_ordinal_stub("... Osmanlı İmparatorluğu'nun 36. #tarih")
    assert ends_with_ordinal_stub("... Osmanlı İmparatorluğu'nun 36.")
    assert not ends_with_ordinal_stub("... 1922'de sona erdi. #tarih")
    assert not ends_with_ordinal_stub("... 1922'de sona erdi.")


def test_model_output_cut_after_ordinal_is_rejected() -> None:
    request = EventRewriteRequest(VAHDETTIN_EVENT, "10.11.1922", "1922", "VI. Mehmed", None, VAHDETTIN_DEFINITION)
    reasons = validate_source_bound_content(
        ["Padişah son Selamlık törenine katıldı, Osmanlı İmparatorluğu'nun 36.", "Bu olay hakkında ne biliyordunuz?"],
        request, emoji_line_present=True, max_block_chars=450,
    )
    assert "truncated" in reasons


def test_definition_sentence_is_skipped_in_fallback() -> None:
    event_words = ATATURK_EVENT
    assert best_overlap_sentence(event_words, (ATATURK_DEFINITION,)) is None
    assert best_overlap_sentence(VAHDETTIN_EVENT, (VAHDETTIN_DEFINITION, VAHDETTIN_SECOND)) == VAHDETTIN_SECOND


def test_atatürk_death_has_no_closing_question() -> None:
    request = EventRewriteRequest(
        ATATURK_EVENT, "10.11.1938", "1938", "Mustafa Kemal Atatürk", None,
        f"{ATATURK_EVENT} {ATATURK_MOURNING} {ATATURK_DEFINITION}",
    )
    parts, used = build_structured_parts(request, [], "🕊️", 480)
    assert len(parts) == 1
    assert "?" not in parts[0]
    assert ATATURK_DEFINITION not in parts[0]
    assert parts[0].endswith("#tarih")
    assert choose_fallback_question([], ATATURK_EVENT, ATATURK_MOURNING) == ""


def test_vahdettin_has_no_person_recognition_question() -> None:
    request = EventRewriteRequest(
        VAHDETTIN_EVENT, "10.11.1922", "1922", "VI. Mehmed", None, f"{VAHDETTIN_EVENT} {VAHDETTIN_DEFINITION}",
    )
    parts, _ = build_structured_parts(request, [], "🕊️", 480)
    assert "36. #tarih" not in parts[0]
    assert all("duymuş" not in part and "tanıyor" not in part for part in parts)


def test_person_question_bank_excludes_recognition_for_leaders() -> None:
    leader_bank = question_bank("Kral III. Ahmet 1703'te tahta çıktı (d. 1673).", "")
    assert "Bu kişiyi daha önce duymuş muydunuz?" not in leader_bank
    assert "Bu ismi tanıyor muydunuz?" not in leader_bank
    assert "Bu kişi hakkında ne biliyordunuz?" in leader_bank
    plain_bank = question_bank("Karındeşen Jack cinayetleri işledi, doğdu.", "")
    assert "Bu ismi tanıyor muydunuz?" in plain_bank
    assert "Bu kişiyi daha önce duymuş muydunuz?" not in plain_bank
