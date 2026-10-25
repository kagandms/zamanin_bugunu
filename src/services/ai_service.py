import httpx
import re
from src.core.config import settings
from src.core.logger import logger
from src.services.content_guard import (
    CONTENT_GUARD_VERSION,
    EventRewriteRequest,
    get_source_fact_status,
    get_relevant_source_sentences,
    has_relevant_source_context,
    resolve_fact_profile,
    validate_event_content,
)
from src.utils.text_utils import (
    clean_twitter_text,
    sanitize_http_header_value,
    smart_split_text,
)
from typing import Tuple, List, Optional


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
    def __init__(self) -> None:
        self.api_key = settings.OPENROUTER_API_KEY.get_secret_value() if settings.OPENROUTER_API_KEY else ""
        self.last_generation_model: Optional[str] = None
        self.last_generation_type = "unknown"
        self.last_validation_reason: Optional[str] = None
        self.last_language_format_status = "unknown"
        self.last_source_fact_status = "not_checked"
        self.last_source_id: Optional[str] = None
        self.last_source_url: Optional[str] = None
        self.prompt_version = f"event-rewrite-v4+{CONTENT_GUARD_VERSION}"
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

        sections = [s.strip() for s in clean_text.split("---") if s.strip()]
        if len(sections) > 3:
            logger.warning(f"⚠️ Content validation FAILED: Invalid section count ({len(sections)}). Expected 1-3.")
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

    async def rewrite_event(self, request: EventRewriteRequest) -> Tuple[List[str], List[str], Optional[str]]:
        """Generate and validate a complete post before any platform publishes it."""
        profile = resolve_fact_profile(request)
        if profile is None:
            raise ValueError("unprofiled_claims_unverified")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required for AI rewriting.")
        source_context = " ".join(get_relevant_source_sentences(request)) or None
        self.last_source_fact_status = get_source_fact_status(profile)
        self.last_language_format_status = "unknown"
        system_prompt = self._build_system_prompt(request, profile.facts if profile else ())
        year_context = f" ({request.year} yılında gerçekleşti)" if request.year else ""

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"Kaynak olay: {request.original_text}{year_context}\n"
                    f"İlgili kaynak sayfası özeti: {source_context or 'Sağlanmadı.'}"
                )}
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

        model_attempt_limit = min(2, len(models)) if profile else len(models)
        self.last_validation_reason = None
        async with httpx.AsyncClient(timeout=35.0) as client:
            for model, label in zip(models[:model_attempt_limit], model_names[:model_attempt_limit]):
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

                    generated_parts, poll_options, image_prompt = self._parse_ai_response(
                        content, request.original_text, request.formatted_date
                    )
                    reasons = validate_event_content(generated_parts, request, profile)
                    if reasons:
                        self.last_validation_reason = ",".join(reasons)
                        logger.warning("Content rejected by source guard: {}", self.last_validation_reason)
                        continue

                    self.last_language_format_status = "passed"
                    if profile:
                        logger.info("Content passed language, format, and scoped source checks ({})", label)
                    else:
                        logger.info("Content passed language and format; source facts were not checked ({})", label)
                    self.last_generation_model = result.get("model") or model
                    self.last_generation_type = "ai_validated" if profile else "ai_language_format_only"
                    self.last_validation_reason = None
                    self.last_source_id = profile.source_id if profile else None
                    self.last_source_url = profile.source_url if profile else request.source_url
                    return generated_parts, poll_options, image_prompt

                except Exception as e:
                    logger.warning(f"⚠️ {label} Model ({model}) exception: {e}")
                    continue

            logger.error("❌ No AI candidate passed generation and source checks.")
            raise RuntimeError(self.last_validation_reason or "all_models_failed")

    @staticmethod
    def _build_system_prompt(request: EventRewriteRequest, trusted_facts: tuple[str, ...]) -> str:
        fact_context = "\n".join(f"- {fact}" for fact in trusted_facts)
        return (
            "Türkçe tarih içerikleri yaz. Yalnızca kullanıcı mesajındaki kaynak olay, ilgili kaynak sayfası özeti "
            "ve aşağıdaki doğrulanmış olguların açıkça desteklediği iddiaları kullan; kaynakta olmayan kişi, yer, "
            "sayı, tarih, alıntı, neden veya taraf ekleme. "
            "Bir cepheye ait sonucu savaşın tamamına genelleme. Çarpıcı ama karşı iddia uydurmayan bir anlatım kullan. "
            "İlk bölüm olayı kısa ve doğru anlatsın. İkinci bölümü yalnız kaynakta veya doğrulanmış olgularda bulunan tarihsel bağlam veya sonuç "
            "ekliyorsa üret; gerekirse doğal bir soru ekle. Kaynakta neyin bulunmadığına veya tarih başlığının kaynağına "
            "ilişkin açıklama yapma; tarih başlığı uygulama tarafından olay listesinden sağlanır ve bağlantılı sayfa özetiyle "
            "aynı kanıt değildir. Tarihi sembolik olarak niteleme. Genel takip çağrısı veya başka bir tanıtım metnini ayrı bölüm yapma. Bölümleri --- ile ayır; "
            "HTML veya açıklama ekleme. GORSEL_PROMPT yalnız kaynakça desteklenen görsel ayrıntılarını içerebilir.\n"
            f"Tarih başlığı: 🕊️ Tarihte Bugün ({request.formatted_date})\n"
            f"Doğrulanmış olay olguları:\n{fact_context or '- Ek doğrulanmış olgu sağlanmadı.'}"
        )

    def generate_source_fallback(self, request: EventRewriteRequest, reason: str) -> Tuple[List[str], List[str], Optional[str]]:
        """Build a fallback only from source text or curated, cited event facts."""
        profile = resolve_fact_profile(request)
        if profile:
            self.last_source_id = profile.source_id
            self.last_source_url = profile.source_url
            self.last_source_fact_status = get_source_fact_status(profile)
            self.last_language_format_status = "fallback_template"
            self.last_generation_type = f"source_fallback:{reason}"
            if profile.profile_id == "ii-kosovo-1448":
                return [
                    f"🕊️ Tarihte Bugün ({request.formatted_date})\n\n{profile.fallback_context[0]}",
                    profile.fallback_context[1],
                ], [], None
            parts = [
                f"🕊️ Tarihte Bugün ({request.formatted_date}) Kars Antlaşması, 13 Ekim 1921'de Kars'ta imzalandı.",
                "Türk Tarih Kurumu Kütüphanesi kaydı Türkiye, Ermenistan, Azerbaycan ve Gürcistan hükümetlerini taraf olarak listeliyor.",
                "Türk Tarih Kurumu özeti, Batı Cephesi'ndeki mücadelenin Eylül 1922'ye kadar sürdüğünü kaydediyor.",
            ]
            validation_reasons = validate_event_content(parts, request, profile)
            if validation_reasons:
                raise RuntimeError(f"curated_fallback_rejected:{','.join(validation_reasons)}")
            return parts, [], None
        self.last_source_id = request.source_title
        self.last_source_url = request.source_url
        self.last_source_fact_status = get_source_fact_status(profile)
        self.last_language_format_status = "fallback_template"
        self.last_generation_type = f"source_fallback:{reason}:thin_source"
        source_event = request.original_text.strip()
        header = f"🕊️ Tarihte Bugün ({request.formatted_date})\n\n"
        source_sentences = get_relevant_source_sentences(request)
        source_context = source_sentences or None
        context_prefix = "Kaynak özeti: "
        source_excerpt = self._source_excerpt(
            source_context, settings.MAX_THREAD_LENGTH - len(context_prefix)
        )
        if source_excerpt:
            main_part = f"{header}{source_event}"
            available_length = settings.MAX_THREAD_LENGTH
            if len(main_part) > available_length:
                main_part = main_part[:available_length - 3].rstrip() + "..."
            context_part = f"{context_prefix}{source_excerpt}"
            self.last_generation_type = f"source_fallback:{reason}:source_context"
            return [main_part, context_part], [], None
        main_part = f"{header}{source_event}"
        if len(main_part) > settings.MAX_THREAD_LENGTH:
            main_part = main_part[:settings.MAX_THREAD_LENGTH - 3].rstrip() + "..."
        return [main_part], [], None

    @staticmethod
    def _source_excerpt(source_sentences: Optional[Tuple[str, ...]], max_chars: int) -> Optional[str]:
        if not source_sentences:
            return None
        selected: list[str] = []
        for sentence in source_sentences[:2]:
            candidate = " ".join((*selected, sentence))
            if len(candidate) > max_chars:
                break
            selected.append(sentence)
        return " ".join(selected) or None

    async def rewrite_event_safe(self, request: EventRewriteRequest) -> Tuple[List[str], List[str], Optional[str]]:
        """Return a fully validated generation or a factual source-only fallback."""
        if resolve_fact_profile(request) is None:
            reason = "unprofiled_claims_unverified"
            self.last_generation_model = None
            self.last_validation_reason = reason
            self.last_source_fact_status = "not_checked"
            return self.generate_source_fallback(request, reason)

        reason = "model_generation_failed"
        try:
            result = await self.rewrite_event(request)
            tweets, poll_options, image_prompt = result
            validation_reasons = validate_event_content(tweets, request, resolve_fact_profile(request))
            if len("".join(tweets)) >= 80 and not validation_reasons:
                return result
            reason = self.last_validation_reason or ",".join(validation_reasons) or "output_too_short"
            logger.warning("AI output rejected by final source guard: {}", reason)
        except Exception as error:
            reason = str(error)[:80] or "model_generation_failed"
            logger.warning("AI rewrite failed ({}); using source-backed fallback.", reason)
        self.last_generation_model = None
        self.last_validation_reason = reason
        self.last_source_fact_status = get_source_fact_status(resolve_fact_profile(request))
        return self.generate_source_fallback(request, reason)

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
