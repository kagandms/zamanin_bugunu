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


# Critical leak phrases — if AI contains ANY of these, it's an immediate leak/garbage output
_CRITICAL_LEAK_PHRASES = [
    "<unk>",
    "[unk]",
    "<pad>",
    "<s>",
    "</s>",
    "given constraints",
    "too time-consuming",
    "time consuming",
    "getting messy",
    "total <=",
    "lets count",
    "let's count",
    "we need to count",
    "count characters",
    "characters precisely",
    "character count",
    "is 1 character",
    "emoji counts",
    "count as 1",
    "lets approximate",
    "let's approximate",
    "block1",
    "block2",
    "block3",
    "we need to produce",
    "must follow format",
    "within constraints",
    "we need total",
    "user safety: safe",
    "chain of thought",
    "let me draft",
    "here is the revised",
]

# Secondary prompt leak indicator phrases — if AI echoes multiple of these, output is corrupted
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
        Detects whether the AI output contains leaked prompt/reasoning text,
        unknown tokens (<unk>), or English calculation scratchpad.
        Returns True if a leak/corruption is detected.
        """
        lower_text = text.lower()

        # Check 0: Unknown tokens (<unk>, [unk]) or model degenerate loops
        if "<unk>" in lower_text or "[unk]" in lower_text or "<pad>" in lower_text:
            logger.warning("🚨 CRITICAL LEAK: Output contains <unk> or special token artifacts!")
            return True

        # Check 1: Critical leak / scratchpad phrases (any 1 match = instant rejection)
        for critical in _CRITICAL_LEAK_PHRASES:
            if critical in lower_text:
                logger.warning(f"🚨 CRITICAL PROMPT LEAK: Matched '{critical}'")
                return True

        # Check 2: Arithmetic counting scratchpad (e.g. '1912 => 214 space 1 => 217')
        if re.search(r'\d+\s*=>\s*\d+', text):
            logger.warning("🚨 PROMPT LEAK: Detected character counting arithmetic scratchpad!")
            return True

        # Check 3: Repetitive word loops (e.g. token stuttering)
        if re.search(r'(\b\w+\b)(?:\s+\1){4,}', lower_text):
            logger.warning("🚨 DEGENERATE OUTPUT: Detected repetitive word loop!")
            return True

        # Check 4: Known secondary leak phrases (2 or more matches)
        matches = [phrase for phrase in _LEAK_PHRASES if phrase in lower_text]
        if len(matches) >= 2:
            logger.warning(
                f"🚨 PROMPT LEAK DETECTED! Matched {len(matches)} phrases: {matches[:5]}"
            )
            return True

        # Check 5: If the text starts with an English reasoning sentence
        first_line = text.split("\n")[0].strip().lower()
        english_starters = [
            "we need", "i need", "let me", "let's", "here is",
            "here's", "okay", "sure", "the event", "this is",
            "i'll", "i will", "first,", "now,", "given", "wait",
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
        reasoning, unknown tokens, or prompt echoing.
        Returns True if valid.
        """
        clean_text = text
        if "GORSEL_PROMPT:" in text:
            clean_text = text.split("GORSEL_PROMPT:")[0]

        # Check 0: Reject any unknown/special tokens
        if "<unk>" in clean_text.lower() or "[unk]" in clean_text.lower() or "<pad>" in clean_text.lower():
            logger.warning("⚠️ Content validation FAILED: Contains <unk> or special tokens.")
            return False

        # Check 1: Structure must contain '---' separator
        if "---" not in clean_text:
            logger.warning("⚠️ Content validation FAILED: Missing '---' section separator.")
            return False

        sections = [s.strip() for s in clean_text.split("---") if s.strip()]
        if len(sections) < 2 or len(sections) > 4:
            logger.warning(f"⚠️ Content validation FAILED: Invalid section count ({len(sections)}). Expected 2-4.")
            return False

        # Check 2: First section MUST have the date header or emoji
        first_section = sections[0].lower()
        if "tarihte bugün" not in first_section and "tarihte bugun" not in first_section and "🕊️" not in sections[0]:
            logger.warning("⚠️ Content validation FAILED: First section missing 'Tarihte Bugün' header.")
            return False

        # Check 3: Turkish vocabulary check (must match Turkish words, not just single chars)
        turkish_common_words = {
            "ve", "bir", "bu", "ile", "için", "olan", "tarihte", "bugün", "yılında",
            "sonra", "olarak", "savaş", "büyük", "tarafından", "etti", "oldu", "sonuç",
            "günümüzde", "tarihin", "önemli", "devlet", "imparatorluk", "türk", "osmanlı",
            "halk", "asker", "gün", "yıl", "dönem", "karar", "dünya"
        }
        words = set(re.findall(r'\b[a-zA-ZçÇşŞğĞüÜöÖıİ]{2,}\b', clean_text.lower()))
        matched_words = words.intersection(turkish_common_words)
        if len(matched_words) < 2:
            logger.warning(f"⚠️ Content validation FAILED: Insufficient Turkish vocabulary ({len(matched_words)} matched: {matched_words}).")
            return False

        # Check 4: English reasoning words ratio (should NOT have English words like constraints, characters, approximate)
        forbidden_reasoning_words = [
            "characters", "character", "constraints", "constraint", "approximate",
            "approx", "counting", "total", "block", "drafting", "separators"
        ]
        reasoning_hits = sum(1 for w in forbidden_reasoning_words if w in words)
        if reasoning_hits >= 2:
            logger.warning(f"⚠️ Content validation FAILED: Contains English reasoning terminology ({reasoning_hits} hits).")
            return False

        # Check 5: Length bounds (total text shouldn't be runaway 1500+ chars)
        if len(clean_text) > 1300:
            logger.warning(f"⚠️ Content validation FAILED: Content too long ({len(clean_text)} chars).")
            return False

        return True

    def _clean_meta_text(self, text: str) -> str:
        """
        Removes AI reasoning/meta-text artifacts from the output.
        """
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            stripped = line.strip().lower()

            if not cleaned_lines and not stripped:
                continue

            skip_patterns = [
                "here is the", "here's the", "here is my",
                "i've created", "i have created", "let me",
                "below is", "note:", "note that",
                "```", "wait block", "block1", "block2", "block3",
            ]

            is_meta = False
            for pattern in skip_patterns:
                if stripped.startswith(pattern):
                    is_meta = True
                    break

            # Filter out arithmetic scratchpad lines (e.g. '1912 => 214 space 1 => 217')
            if re.search(r'\d+\s*=>\s*\d+', stripped):
                is_meta = True

            # Don't skip "---" as it's our legitimate separator
            if stripped == "---":
                is_meta = False

            if is_meta:
                logger.debug(f"Stripped meta-line: '{line.strip()[:60]}'")
                continue

            cleaned_lines.append(line)

        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        return "\n".join(cleaned_lines)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1.5, min=5, max=15))
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
            "\n- Metnin GORSEL_PROMPT haricindeki tamamı KESİNLİKLE Türkçe (Turkish) olmalıdır. Diğer dilleri kesinlikle kullanma."
            "\n- Metin 3 kısa ve akıcı bölümden oluşmalıdır. Bölümleri mutlaka '---' işareti ile ayır."
            "\n- İlk paragrafta vurucu bir giriş yap ve emojiler kullan."
            "\n- Hikaye anlatıcılığı (storytelling) kullan."
            "\n- Son blokta olayın sonucunu anlattıktan sonra, okuyucuya merak uyandırıcı, kısa 1 soru cümlesi ekle."
            "\n- ASLA ve ASLA HTML etiketleri (<b>, <i> vb.) KULLANMA. Sadece temiz düz metin üret."
            "\n- ASLA düşünce (reasoning), scratchpad, karakter sayımı veya İngilizce açıklama yazma."
            "\n- Cevabına doğrudan içerikle başla, öncesinde hiçbir açıklama yapma."
            "\n\nISTENEN FORMAT:"
            f"\n🕊️ Tarihte Bugün ({formatted_date})"
            "\n[İlgi çekici giriş cümlesi]"
            "\n#tarih #tarihteneoldu"
            "\n---"
            "\n[Olayın detayları ve gelişimi]"
            "\n---"
            "\n[Sonuç ve günümüze etkisi] 📚"
            "\n[Okuyucuyu yorum yapmaya davet eden kısa soru]"
            "\nGORSEL_PROMPT: [English Image Prompt]"
        )

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Olay: {original_text}{year_context}\nRevize et."}
            ],
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 1200,
            "reasoning": {"effort": "none"}  # Disable OpenRouter reasoning/scratchpad
        }

        # 5-tier cascade of verified free models
        models = [
            settings.AI_MODEL, 
            settings.BACKUP_MODEL, 
            getattr(settings, "TERTIARY_MODEL", "google/gemma-4-31b-it:free"), 
            getattr(settings, "QUATERNARY_MODEL", "google/gemma-4-26b-a4b-it:free"),
            settings.LAST_RESORT_MODEL
        ]
        model_names = [
            "Primary (Ling 3.0)",
            "Secondary (Nemotron 3 Super)",
            "Tertiary (Gemma 4 31B)",
            "Quaternary (Gemma 4 26B)",
            "Last Resort (Qwen 3.8)"
        ]

        async with httpx.AsyncClient(timeout=35.0) as client:
            for idx, (model, label) in enumerate(zip(models, model_names)):
                try:
                    payload["model"] = model
                    response = await client.post(self.url, headers=self.headers, json=payload)

                    if response.status_code != 200:
                        logger.warning(
                            f"{label} Model ({model}) returned HTTP {response.status_code}: {response.text[:120]}"
                        )
                        continue

                    result = response.json()
                    if "error" in result:
                        logger.warning(f"{label} Model returned error in payload: {result['error']}")
                        continue

                    choices = result.get('choices')
                    if not choices or not choices[0].get('message'):
                        continue

                    msg = choices[0]['message']
                    raw_content = msg.get('content')
                    if not raw_content or not isinstance(raw_content, str):
                        logger.warning(f"{label} Model returned empty or non-string content")
                        continue

                    # Strip any <think> blocks
                    content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
                    logger.info(f"✅ Got response from {label} Model: {model}")

                    # === PROMPT LEAK GUARD ===
                    if self._detect_prompt_leak(content):
                        logger.warning(f"🚨 {label} Model leaked prompt/reasoning! Trying next model...")
                        continue

                    # === CLEAN META-TEXT ===
                    content = self._clean_meta_text(content)

                    # === TURKISH CONTENT VALIDATION ===
                    if not self._validate_turkish_content(content):
                        logger.warning(f"⚠️ {label} Model produced non-Turkish/invalid content! Trying next...")
                        continue

                    logger.info(f"✅ Content passed all validation checks ({label} Model).")
                    return self._parse_ai_response(content, original_text, formatted_date)

                except Exception as e:
                    logger.warning(f"⚠️ {label} Model ({model}) exception: {e}")
                    continue

            logger.error("❌ All AI models in cascade failed.")
            raise RuntimeError("All AI models in cascade failed.")

    def generate_template_fallback(
        self, 
        original_text: str, 
        formatted_date: str, 
        year: Optional[str] = None,
        extract: Optional[str] = None
    ) -> Tuple[List[str], List[str], Optional[str]]:
        """
        Deterministic, high-quality template fallback when external AI models are unreachable.
        Guarantees that a post is NEVER skipped due to external AI downtime.
        """
        part1 = (
            f"🕊️ Tarihte Bugün ({formatted_date})\n\n"
            f"{original_text}\n\n"
            f"#tarih #tarihteneoldu"
        )
        
        if extract and len(extract.strip()) > 30:
            clean_extract = extract.strip()
            if len(clean_extract) > settings.MAX_THREAD_LENGTH - 30:
                clean_extract = clean_extract[:settings.MAX_THREAD_LENGTH - 33] + "..."
            part2 = clean_extract
        else:
            part2 = "Tarihin bu önemli dönüm noktası, dönemin toplumsal ve siyasal dengelerini derinden etkileyen gelişmelere sahne oldu."

        part3 = (
            "Geçmişin izleri günümüz dünyasını şekillendirmeye devam ediyor. 📚\n\n"
            "Siz bu tarihi gelişme hakkında ne düşünüyorsunuz? Yorumlarda paylaşın."
        )

        tweets = [part1, part2, part3]
        return tweets, [], None

    async def rewrite_event_safe(
        self, 
        original_text: str, 
        formatted_date: str, 
        year: Optional[str] = None,
        extract: Optional[str] = None
    ) -> Tuple[List[str], List[str], Optional[str]]:
        """
        Wrapper ensuring AI rewrite with intelligent template fallback.
        Guarantees that output is NEVER empty.
        """
        try:
            result = await self.rewrite_event(original_text, formatted_date, year)
            tweets, poll_options, image_prompt = result

            total_text = "".join(tweets)
            if len(total_text) >= 100:
                return result
            logger.warning(f"AI output too short ({len(total_text)} chars). Activating smart template fallback.")
        except Exception as e:
            logger.warning(f"AI Service exception: {e}. Activating smart template fallback.")

        logger.info("🛡️ Using deterministic smart template fallback.")
        return self.generate_template_fallback(original_text, formatted_date, year, extract)

    def _parse_ai_response(self, content: str, original_text: str, formatted_date: Optional[str] = None):
        """Parses the structured response from AI and deterministically enforces the date header."""
        content = clean_twitter_text(content)

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

        if "---" in content:
            tweets = [p.strip() for p in content.split("---") if p.strip()]
        else:
            tweets = [content]

        # Enforce maximum 3 content blocks (Header, Story, Conclusion/Question)
        if len(tweets) > 3:
            logger.warning(f"AI produced {len(tweets)} blocks. Merging excess into 3 blocks.")
            part1 = tweets[0]
            part2 = "\n\n".join(tweets[1:-1])
            part3 = tweets[-1]
            tweets = [part1, part2, part3]

        # Zero-Tolerance Date Enforcement: Overwrite header with true wall-clock formatted_date
        if tweets and formatted_date:
            first_block = tweets[0]
            lines = first_block.split("\n")
            correct_header = f"🕊️ Tarihte Bugün ({formatted_date})"
            if "tarihte bugün" in lines[0].lower() or "tarihte bugun" in lines[0].lower() or "🕊️" in lines[0]:
                lines[0] = correct_header
                tweets[0] = "\n".join(lines)
            else:
                tweets[0] = f"{correct_header}\n\n{first_block}"

        final_threads = []
        for thread_part in tweets:
            if len(thread_part) > settings.MAX_THREAD_LENGTH - 20:
                final_threads.extend(smart_split_text(thread_part, settings.MAX_THREAD_LENGTH - 50))
            else:
                final_threads.append(thread_part)

        # Hard safety cap on thread count: never allow more than 3 content parts before footer
        if len(final_threads) > 3:
            logger.warning(f"final_threads exceeded 3 parts ({len(final_threads)}). Capping to 3.")
            final_threads = final_threads[:3]

        return final_threads, poll_options, image_prompt
