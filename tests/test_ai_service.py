"""Tests for the AI service prompt leak detection and content validation."""
import pytest
from src.services.ai_service import AIService


@pytest.fixture
def ai_service(monkeypatch):
    """Creates an AIService instance with dummy credentials."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-dummy-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy:token")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@test")
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "dummy_threads_token")
    monkeypatch.setenv("THREADS_USER_ID", "12345")
    # Re-import to pick up the env vars
    from src.core.config import Settings
    settings_instance = Settings()
    monkeypatch.setattr("src.services.ai_service.settings", settings_instance)
    return AIService()


class TestPromptLeakDetection:
    """Tests for _detect_prompt_leak method."""

    def test_detects_english_reasoning(self, ai_service):
        """Should detect when AI echoes back the prompt instructions."""
        leaked_text = (
            "We need to produce a revised content: viral, catchy, true, Turkish, "
            "within constraints. Must follow format:\n"
            "🕊️ Tarihte Bugün (4.8.1791)\n"
            "[İlgi çekici giriş cümlesi]\n"
            "tarih #tarihteneoldu"
        )
        assert ai_service._detect_prompt_leak(leaked_text) is True

    def test_detects_reasoning_with_sections(self, ai_service):
        """Should detect when AI includes Section1/Section2 reasoning."""
        leaked_text = (
            "for Threads, each block <=400 characters. Must not use HTML tags. "
            "Must start with an engaging opening with emojis. "
            "Provide three sections: opening, details, conclusion.\n"
            "Section1: opening ~120 chars."
        )
        assert ai_service._detect_prompt_leak(leaked_text) is True

    def test_detects_lets_draft(self, ai_service):
        """Should detect when AI starts reasoning with 'Let me/Let's draft'."""
        leaked_text = (
            "Let me draft the content for this historical event.\n"
            "We need to ensure total characters <800.\n"
            "🕊️ Tarihte Bugün (3.8.1936)"
        )
        assert ai_service._detect_prompt_leak(leaked_text) is True

    def test_accepts_clean_turkish_content(self, ai_service):
        """Should NOT flag legitimate Turkish content as a leak."""
        clean_text = (
            "🕊️ Tarihte Bugün (3.8.1936)\n"
            "Berlinin soğuk havasında, Hitlerin Aryan ırk üstünlüğü hayali 10.3 saniyede "
            "toprağa yıkıldı. Jesse Owens, nefesleri kesilmiş bir stadyumda pistten fırladı ve "
            "sadece bir yarış değil, bir ideolojiyi de geride bıraktı. 🏃💨\n"
            "tarih #tarihteneoldu #jesseowens #olimpiyat"
        )
        assert ai_service._detect_prompt_leak(clean_text) is False

    def test_detects_english_starter(self, ai_service):
        """Should detect content that starts with English reasoning."""
        leaked_text = (
            "Here is the revised content for the historical event:\n\n"
            "🕊️ Tarihte Bugün (2.8.1492)\n"
            "Kolomb yola çıktı..."
        )
        assert ai_service._detect_prompt_leak(leaked_text) is True

    def test_single_phrase_not_enough(self, ai_service):
        """A single accidental match should NOT trigger the leak detector."""
        text_with_one_match = (
            "🕊️ Tarihte Bugün (5.8.1945)\n"
            "Hiroşimada dünya tarihinin en yıkıcı silahı kullanıldı. "
            "Bu olay, barış için yeni bir not oluşturdu. 📚\n"
            "#tarih #tarihteneoldu"
        )
        assert ai_service._detect_prompt_leak(text_with_one_match) is False


class TestTurkishContentValidation:
    """Tests for _validate_turkish_content method."""

    def test_accepts_valid_turkish(self, ai_service):
        """Should accept properly formatted Turkish content."""
        valid = (
            "🕊️ Tarihte Bugün (3.8.1936)\n"
            "Berlinin soğuk havasında büyük bir olay yaşandı. "
            "Jesse Owens dünya rekorunu kırdı! 🏅\n"
            "#tarih #tarihteneoldu\n"
            "---\n"
            "Detaylı açıklama...\n"
        )
        assert ai_service._validate_turkish_content(valid) is True

    def test_rejects_pure_english(self, ai_service):
        """Should reject content that has no Turkish characters."""
        english_text = (
            "Today in History (3.8.1936)\n"
            "Jesse Owens won 4 gold medals at the Berlin Olympics.\n"
            "#history"
        )
        assert ai_service._validate_turkish_content(english_text) is False

    def test_rejects_missing_header(self, ai_service):
        """Should reject content without 'Tarihte Bugün' header."""
        no_header = (
            "Berlinin soğuk havasında büyük bir olay yaşandı. "
            "Jesse Owens dünya rekorunu kırdı! 🏅\n"
            "#tarih #tarihteneoldu"
        )
        assert ai_service._validate_turkish_content(no_header) is False


class TestCleanMetaText:
    """Tests for _clean_meta_text method."""

    def test_removes_here_is_prefix(self, ai_service):
        """Should remove 'Here is the...' prefix lines."""
        text = (
            "Here is the revised content:\n"
            "🕊️ Tarihte Bugün (3.8.1936)\n"
            "Büyük olay..."
        )
        result = ai_service._clean_meta_text(text)
        assert result.startswith("🕊️ Tarihte Bugün")

    def test_preserves_separator(self, ai_service):
        """Should preserve --- separator between sections."""
        text = (
            "🕊️ Tarihte Bugün (3.8.1936)\n"
            "Giriş...\n"
            "---\n"
            "Detaylar..."
        )
        result = ai_service._clean_meta_text(text)
        assert "---" in result

    def test_removes_markdown_code_blocks(self, ai_service):
        """Should remove stray markdown code block markers."""
        text = (
            "```\n"
            "🕊️ Tarihte Bugün (3.8.1936)\n"
            "Giriş...\n"
            "```"
        )
        result = ai_service._clean_meta_text(text)
        assert "```" not in result

    def test_removes_arithmetic_scratchpad(self, ai_service):
        """Should remove arithmetic calculation lines."""
        text = (
            "1912 => 214 space 1 => 217\n"
            "🕊️ Tarihte Bugün (3.8.1936)\n"
            "Giriş...\n"
            "yener, 6 => 216\n"
            "---\n"
            "Detaylar..."
        )
        result = ai_service._clean_meta_text(text)
        assert "1912 => 214" not in result
        assert "yener, 6 => 216" not in result
        assert "Giriş..." in result


class TestUnknownTokenAndScratchpadGuard:
    """Tests for <unk> token rejection and reasoning scratchpad prevention."""

    def test_rejects_unk_token_in_leak_detection(self, ai_service):
        """Should immediately detect <unk> tokens as leak/corrupted output."""
        garbage = "<unk><unk><unk> (this is getting messy). This is too time-consuming."
        assert ai_service._detect_prompt_leak(garbage) is True

    def test_rejects_character_counting_arithmetic(self, ai_service):
        """Should detect character counting arithmetic scratchpad."""
        garbage = "yener, 6 => 216 space 1 => 217 1912ye 7 => 217"
        assert ai_service._detect_prompt_leak(garbage) is True

    def test_rejects_unk_in_turkish_validation(self, ai_service):
        """Should reject content containing <unk> in Turkish validation."""
        garbage = (
            "🕊️ Tarihte Bugün (29.9.1911)\n"
            "<unk><unk><unk> Osmanlı ordusu savaşa girdi.\n"
            "---\n"
            "Sonuç ve detaylar..."
        )
        assert ai_service._validate_turkish_content(garbage) is False

    def test_parse_response_caps_at_3_blocks(self, ai_service):
        """Should never produce more than 3 blocks from AI response."""
        many_blocks = (
            "🕊️ Tarihte Bugün (29.9.1911)\nBlok 1\n---\n"
            "Blok 2\n---\n"
            "Blok 3\n---\n"
            "Blok 4\n---\n"
            "Blok 5\n"
            "GORSEL_PROMPT: A painting of historical war."
        )
        threads, _, _ = ai_service._parse_ai_response(many_blocks, "test", "29.9.1911")
        assert len(threads) <= 3

