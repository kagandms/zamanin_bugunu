import httpx
import re
from src.core.config import settings
from src.core.logger import logger
from src.utils.text_utils import (
    clean_twitter_text,
    sanitize_http_header_value,
    smart_split_text,
)
from typing import Tuple, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential


# Prompt leak indicator phrases — if AI echoes these, the output is corrupted
_LEAK_PHRASES = [
    "we need to produce",
    "must follow format",
    "must not use html",
    "let me draft",
    "let's draft",
    "lets draft",
    "here is the content",
    "here's the content",
    "here is the revised",
    "section1:",
    "section 1:",
    "section2:",
    "section 2:",
    "section3:",
    "~120 char",
    "~200 char",
    "opening ~",
    "must be under 800",
    "must split into blocks",
    "gorsel_prompt line",
    "each block <=",
    "each block is <=",
    "we must not use",
    "we should",
    "i will",
    "i'll create",
    "let me create",
    "for threads,",
    "for telegram,",
    "within constraints",
    "must start with an engaging",
    "provide three sections",
    "we need to ensure",
    "we need to include",
    "plain text",
    "engaging opening with emojis",
]

# Turkish-specific characters — at least some should be present in genuine Turkish text
_TURKISH_CHARS = set("çÇşŞğĞüÜöÖıİ")


class AIService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY.get_secret_value()
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        header_title = sanitize_http_header_value(settings.APP_NAME)
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/kagandms/tarihte-bugun-botu",
            "X-Title": header_title
        }

    def _detect_prompt_leak(self, text: str) -> bool:
        """
        Detects whether the AI output contains leaked prompt/reasoning text.
        Returns True if a leak is detected.
        """
        lower_text = text.lower()

        # Check 1: Known leak phrases
        matches = [phrase for phrase in _LEAK_PHRASES if phrase in lower_text]
        if len(matches) >= 2:
            logger.warning(
                f"🚨 PROMPT LEAK DETECTED! Matched {len(matches)} phrases: {matches[:5]}"
            )
            return True

        # Check 2: If the text starts with an English reasoning sentence
        # (genuine output should start with emoji + Turkish header)
        first_line = text.split("\n")[0].strip().lower()
        english_starters = [
            "we need", "i need", "let me", "let's", "here is",
            "here's", "okay", "sure", "the event", "this is",
            "i'll", "i will", "first,", "now,",
        ]
        for starter in english_starters:
            if first_line.startswith(starter):
                logger.warning(
                    f"🚨 PROMPT LEAK: Output starts with English reasoning: '{first_line[:60]}'"
                )
                return True

        return False

    def _validate_turkish_content(self, text: str) -> bool:
        """
        Validates that the AI output is genuine Turkish content, not English
        reasoning or prompt echoing.
        Returns True if valid.
        """
        # Strip out GORSEL_PROMPT line (which is legitimately English)
        clean_text = text
        if "GORSEL_PROMPT:" in text:
            clean_text = text.split("GORSEL_PROMPT:")[0]

        # Check 1: Must contain at least some Turkish characters
        has_turkish_chars = any(c in _TURKISH_CHARS for c in clean_text)
        if not has_turkish_chars:
            logger.warning("⚠️ Content validation FAILED: No Turkish characters found.")
            return False

        # Check 2: Must contain the expected header format (relaxed check)
        has_header = (
            "tarihte bugün" in clean_text.lower()
            or "tarihte bugun" in clean_text.lower()
            or "🕊️" in clean_text
            or "📢" in clean_text
        )
        if not has_header:
            logger.warning("⚠️ Content validation FAILED: Missing 'Tarihte Bugün' header.")
            return False

        # Check 3: Must contain at least one relevant hashtag
        has_hashtag = (
            "#tarih" in clean_text.lower()
            or "#tarihteneoldu" in clean_text.lower()
        )
        if not has_hashtag:
            # Soft warning — some models might skip hashtags
            logger.info("ℹ️ Content missing hashtags — will be accepted but not ideal.")

        return True

    def _clean_meta_text(self, text: str) -> str:
        """
        Removes AI reasoning/meta-text artifacts from the output.
        """
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip().lower()

            # Skip empty lines at the start
            if not cleaned_lines and not stripped:
                continue

            # Skip lines that are clearly AI meta-reasoning
            skip_patterns = [
                "here is the", "here's the", "here is my",
                "i've created", "i have created", "let me",
                "below is", "note:", "note that",
                "```", "---",  # Markdown artifacts (but --- is our separator)
            ]

            # Only skip --- if it appears as a standalone formatting artifact
            # at the very beginning or very end
            is_meta = False
            for pattern in skip_patterns:
                if stripped.startswith(pattern):
                    is_meta = True
                    break

            # Don't skip "---" as it's our legitimate separator
            if stripped == "---":
                is_meta = False

            if is_meta:
                logger.debug(f"Stripped meta-line: '{line.strip()[:60]}'")
                continue

            cleaned_lines.append(line)

        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        return "\n".join(cleaned_lines)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=30, max=60))
    async def rewrite_event(self, original_text: str, formatted_date: str, year: Optional[str] = None) -> Tuple[List[str], List[str], Optional[str]]:
        """
        Rewrites the event text using AI to be viral and suitable for social media.
        Returns: (tweet_parts, poll_options, image_prompt)
        """
        year_context = f" ({year} yılında gerçekleşti)" if year else ""

        system_prompt = (
            "Sen profesyonel bir tarihçi ve sosyal medya uzmanısın. Görevin: "
            "Verilen tarihi olayı Threads ve Telegram kanalları için VİRAL, İLGİ ÇEKİCİ ve DOĞRU bir içerik haline getirmektir."
            "\n\nKURALLAR:"
            "\n- Metnin GORSEL_PROMPT haricindeki tamamı KESİNLİKLE Türkçe (Turkish) olmalıdır. Diğer dilleri (İngilizce, Rusça vb.) kesinlikle kullanma."
            "\n- Toplam metin 800 karakteri ASLA geçmemelidir (Telegram limitleri için)."
            "\n- Threads limitleri için 400 karakteri geçmeyen anlamlı bloklar oluştur (--- işareti ile ayır)."
            "\n- İlk paragrafta vurucu bir giriş yap ve emojiler kullan."
            "\n- Hikaye anlatıcılığı (storytelling) kullan."
            "\n- ASLA ve ASLA HTML etiketleri (<b>, <i>, <todaydate> vb.) KULLANMA. Sadece temiz düz metin üret."
            "\n- ASLA İngilizce açıklama, yorum veya meta-metin ekleme. Sadece son içeriği üret."
            "\n- Cevabına doğrudan içerikle başla, öncesinde hiçbir açıklama yapma."
            "\n\nISTENEN FORMAT:"
            f"\n🕊️ Tarihte Bugün ({formatted_date})"
            "\n[İlgi çekici giriş cümlesi]"
            "\n#tarih #tarihteneoldu"
            "\n---"
            "\n[Olayın detayları ve gelişimi]"
            "\n---"
            "\n[Sonuç ve günümüze etkisi] 📚"
            "\nGORSEL_PROMPT: [English Image Prompt]"
        )

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Olay: {original_text}{year_context}\nRevize et."}
            ],
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 1000
        }

        models = [settings.AI_MODEL, settings.BACKUP_MODEL, settings.LAST_RESORT_MODEL]
        model_names = ["Primary", "Backup", "Last Resort"]

        async with httpx.AsyncClient(timeout=45.0) as client:
            for idx, (model, label) in enumerate(zip(models, model_names)):
                try:
                    payload["model"] = model
                    response = await client.post(self.url, headers=self.headers, json=payload)

                    if response.status_code != 200:
                        logger.warning(
                            f"{label} Model ({model}) failed: {response.status_code} - "
                            f"BODY: {response.text}"
                        )
                        continue

                    result = response.json()
                    content = result['choices'][0]['message']['content'].strip()
                    logger.info(f"✅ Got response from {label} Model: {model}")

                    # === PROMPT LEAK GUARD ===
                    if self._detect_prompt_leak(content):
                        logger.warning(
                            f"🚨 {label} Model ({model}) leaked the prompt! "
                            f"Rejecting and trying next model..."
                        )
                        logger.debug(f"Leaked content preview: {content[:200]}")
                        continue

                    # === CLEAN META-TEXT ===
                    content = self._clean_meta_text(content)

                    # === TURKISH CONTENT VALIDATION ===
                    if not self._validate_turkish_content(content):
                        logger.warning(
                            f"⚠️ {label} Model ({model}) produced non-Turkish content! "
                            f"Rejecting and trying next model..."
                        )
                        logger.debug(f"Invalid content preview: {content[:200]}")
                        continue

                    logger.info(f"✅ Content passed all validation checks ({label} Model).")
                    return self._parse_ai_response(content, original_text)

                except Exception as e:
                    logger.warning(f"⚠️ {label} Model ({model}) exception: {e}")
                    if idx < len(models) - 1:
                        logger.info(f"Switching to {model_names[idx + 1]} Model...")
                    continue

            # All models failed
            logger.error("❌ All 3 models failed to produce valid content.")
            raise RuntimeError("All AI models failed or produced invalid content.")

    async def rewrite_event_safe(self, original_text: str, formatted_date: str, year: Optional[str] = None):
        """Wrapper ensuring fallback if retries fail."""
        try:
            result = await self.rewrite_event(original_text, formatted_date, year)
            tweets, poll_options, image_prompt = result

            # Quality Gate: If AI returned text shorter than 100 chars total, reject it
            total_text = "".join(tweets)
            if len(total_text) < 100:
                logger.warning(f"AI output too short ({len(total_text)} chars). Rejecting low-quality content.")
                return [], [], None

            return result
        except Exception as e:
            logger.critical(f"AI Service Failed after retries: {e}")
            # DO NOT post raw fallback text — it produces low-quality content
            # Return empty so main.py skips this cycle gracefully
            logger.warning("Skipping this cycle to avoid low-quality post.")
            return [], [], None

    def _parse_ai_response(self, content: str, original_text: str):
        """Parses the structured response from AI."""
        # 1. Clean
        content = clean_twitter_text(content)

        # 2. Extract Components
        image_prompt = None
        poll_options = []

        if "GORSEL_PROMPT:" in content:
            parts = content.split("GORSEL_PROMPT:")
            content = parts[0].strip()
            image_prompt = parts[1].strip()

        if "ANKET:" in content:
            parts = content.split("ANKET:")
            content = parts[0].strip()
            raw_poll = parts[1].strip()
            poll_options = [x.strip()[:25] for x in raw_poll.split("|") if x.strip()][:4]

        # 3. Split Chain
        if "---" in content:
            tweets = [p.strip() for p in content.split("---") if p.strip()]
        else:
            tweets = [content]

        # 4. Safety Check (Length)
        final_threads = []
        for thread_part in tweets:
            if len(thread_part) > settings.MAX_THREAD_LENGTH - 20:
                final_threads.extend(smart_split_text(thread_part, settings.MAX_THREAD_LENGTH - 50))
            else:
                final_threads.append(thread_part)

        return final_threads, poll_options, image_prompt
