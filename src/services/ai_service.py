import asyncio
import httpx
import re
import time
from src.core.config import settings
from src.core.logger import logger
from src.services.content_guard import (
    CONTENT_GUARD_VERSION,
    SOURCE_RICH_MIN_CHARS,
    EventRewriteRequest,
    get_source_fact_status,
    get_relevant_source_sentences,
    has_relevant_source_context,
    resolve_fact_profile,
    source_summary_sentences,
    validate_event_content,
    validate_source_bound_content,
)
from src.services.structured_fallback import build_structured_parts
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

_TURKISH_COMMON_WORDS = {
    "ve", "bir", "bu", "ile", "için", "olan", "tarihte", "bugün", "yılında",
    "sonra", "olarak", "savaş", "büyük", "tarafından", "etti", "oldu", "sonuç",
    "günümüzde", "tarihin", "önemli", "devlet", "imparatorluk", "türk", "osmanlı",
    "halk", "asker", "gün", "yıl", "dönem", "karar", "dünya"
}

# Source-bound generation (events without a curated fact profile)
EMOJI_CHOICES = ("🕊️", "⚔️", "🏛️", "🔬", "🎭", "🌍")
DEFAULT_EMOJI = "🕊️"
PROMPT_VERSION_PROFILED = f"event-rewrite-v4+{CONTENT_GUARD_VERSION}"
PROMPT_VERSION_SOURCE_BOUND = f"event-rewrite-v5+{CONTENT_GUARD_VERSION}"
_EMOJI_LINE = re.compile(r"^[ \t]*EMOJI:[ \t]*(\S+)", re.MULTILINE)
_ECHOED_HEADER = re.compile(r"^\S{0,3}\s*Tarihte Bugün\s*\([^)]*\)\s*", re.IGNORECASE)
_TAG_TARIH = re.compile(r"#tarih\b", re.IGNORECASE)
RATE_LIMIT_BACKOFF_SECONDS = 5
SOURCE_BOUND_TIME_BUDGET_SECONDS = 90
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_TIMEOUT_SECONDS = 25.0

SOURCE_BOUND_SYSTEM_PROMPT = """Sen Türkçe tarih içeriği yazan bir editörsün. Okuyucu: Türkiye'de tarihe meraklı, 25-55 yaş arası yetişkinler.

GÖREVİN
Kullanıcı mesajındaki "Kaynak olay" ve "Kaynak özeti"ni, aynı bilgiyi koruyarak, akışta okuyucuyu durduracak
ilgi çekici bir metne dönüştürmek. YENİ BİLGİ EKLEMEZSİN; yalnızca verilen bilgiyi yorumlayıp çerçevelersin.

KESİN KURALLAR
1. Yalnızca kaynak olay ve kaynak özetindeki olgulara dayan. Kaynakta olmayan kişi, yer, sayı, tarih,
   alıntı, neden, niyet, duygu, sonuç veya "ilk/en/tek" gibi üstünlük iddiası yazma.
2. Tarafsızsın. Değer yargısı ve duygusal sıfat kullanma (vahim, kahraman, hain, korkunç, utanç vb.).
   Birden fazla taraf varsa "kimine göre … kimine göre …" gibi dengeli yaz; yalnızca kaynakta varsa.
3. Başlık yazma, tarih başlığı ekleme, takip çağrısı yazma. Bunları sistem ekler.
4. HTML, markdown, madde işareti, açıklama, düşünce notu yazma. Yalnızca istenen biçimi ver.
5. Yalnızca kaynaktaki sözcükleri kullan. Kaynakta geçmeyen sıfat, betimleme, sahne ayrıntısı ve değerlendirme yazma.
6. Kaynak özeti "Sağlanmadı." ise yalnızca 1-2 cümlelik yeniden ifade ve bir soru yaz; başka hiçbir şey ekleme.
7. Yalnızca kaynak cümlelerini yeniden sırala: öne çıkan olguyu başa al. Yeni sıfat, betimleme, sahne, duygu, neden
   veya sonuç ekleme. Kaynakta geçmeyen bir sözcük kullanma.
   Yasak örnek: "Bir cami, başka bir çağın izini de taşıyormuş." (çağ, iz, taşımak kaynakta yok.)

NASIL İLGİ ÇEKİCİ YAPARSIN
- Bölüm 1'in ilk cümlesi okuyucuyu durdurmalı: kaynaktaki en şaşırtıcı, en çarpıcı veya en insani olguyla aç.
  "X tarihinde Y oldu" gibi ansiklopedi girişi YASAK. 1-2 cümle.
- Ritim: kısa cümleler, bir uzun cümle. Gereksiz süs yok. Belgesel anlatıcısı sakinliği.
- Kaynak zengin ise ikinci bölümde aynı bilgileri bağlamla ilişkilendir; zayıfsa ikinci bölüm üretme.
- Kapanış: tek, açık uçlu, yargısız bir soru. Taraf seçtiren soru yazma ("doğru muydu yanlış mıydı" gibi).
  Soru, olayın kendi somut ayrıntısına bağlı, kısa ve doğal konuşma dilinde olmalı; kalıp/şablon hissi vermemeli.
  "Ailenizde … oldu mu?" gibi genel aile-anı kalıpları YASAK (yapay duruyor; kullanıcı kararı).
  Tercih edilen türler: (a) bilgi yoklaması: "Bunu biliyor muydunuz?" / "Bu olayı daha önce duymuş muydunuz?",
  (b) somut merak sorusu: olayın içindeki ayrıntıya dair ("Sizce o gün … nasıl karşılandı?" yalnızca kaynak uygunsa),
  (c) açık uçlu okuma: "Bu olayı bugün nasıl okuyorsunuz?". Her gönderide aynı soruyu kullanma.
  "Beğenin, takip edin, yorum yapın" gibi doğrudan istek yazma.
- Konuya uygun TEK emoji seç (aşağıdaki listeden) ve EMOJI: satırına yaz.

ÇIKTI BİÇİMİ (tam olarak)
EMOJI: <🕊️|⚔️|🏛️|🔬|🎭|🌍>
---
<bölüm 1; sonuna " #tarih" ekle>
---
<bölüm 2 (yalnızca kaynak özeti yeterliyse)>
---
<kapanış sorusu>
GORSEL_PROMPT: <yalnızca istenirse; kaynakta desteklenen ayrıntılarla, İngilizce>"""

# Few-shot pairs (from strategy/06), adjusted to the source-words-only rule.
SOURCE_BOUND_FEW_SHOT: tuple[tuple[str, str], ...] = (
    (
        "Kaynak olay: İstanbul Zeyrek Camii'nde Bizans dönemi'nden kalma mozaikler bulundu.\n"
        "Kaynak özeti: Sağlanmadı.\nKaynak zengin mi: hayır",
        "EMOJI: 🏛️\n---\nBizans dönemi'nden kalma mozaikler, İstanbul Zeyrek Camii'nde bulundu. #tarih\n---\n"
        "Bu olayı daha önce duymuş muydunuz?",
    ),
    (
        "Kaynak olay: Türkiye Cumhuriyeti kuruldu ve TBMM'deki oylamada Mustafa Kemal Atatürk oy birliğiyle "
        "ilk cumhurbaşkanı seçildi.\nKaynak özeti: Sağlanmadı.\nKaynak zengin mi: hayır",
        "EMOJI: 🏛️\n---\nMustafa Kemal Atatürk, TBMM'deki oylamada oy birliğiyle ilk cumhurbaşkanı seçildi; "
        "Türkiye Cumhuriyeti de kuruldu. #tarih\n---\nBu ayrıntıyı daha önce duymuş muydunuz?",
    ),
)


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
        self.last_used_source_sentence: Optional[str] = None
        self.recent_published_texts: list[str] = []
        self.prompt_version = PROMPT_VERSION_PROFILED
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
        words = set(re.findall(r'\b[a-zA-ZçÇşŞğĞüÜöÖıİ]{2,}\b', clean_text.lower()))
        matched_words = words.intersection(_TURKISH_COMMON_WORDS)
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
            return await self._rewrite_source_bound(request)
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

        cascade = self._model_cascade()
        models = [model for model, _ in cascade]
        model_names = [label for _, label in cascade]

        model_attempt_limit = min(2, len(models))
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
    def _model_cascade() -> List[Tuple[str, str]]:
        """Profiled events: the first two models of the OpenRouter cascade."""
        return [
            (settings.AI_MODEL, "Primary"),
            (settings.BACKUP_MODEL, "Secondary"),
        ]

    def _gemini_api_key(self) -> str:
        key = settings.GEMINI_API_KEY
        return key.get_secret_value() if key else ""

    def _source_bound_cascade(self) -> List[Tuple[str, str, str]]:
        """(provider, model, label) in order: Gemini (if configured), then the OpenRouter free models."""
        cascade: List[Tuple[str, str, str]] = []
        if self._gemini_api_key() and settings.GEMINI_MODEL.strip():
            cascade.append(("gemini", settings.GEMINI_MODEL.strip(), "Gemini"))
        if self.api_key:
            cascade.append(("openrouter", settings.AI_MODEL, "Primary"))
            cascade.append(("openrouter", settings.BACKUP_MODEL, "Secondary"))
        return cascade

    @staticmethod
    def _models_without_reasoning() -> set[str]:
        return {m.strip() for m in settings.MODELS_WITHOUT_REASONING_PARAM.split(",") if m.strip()}

    def _openrouter_body(self, model: str, messages: list[dict[str, str]], base: dict[str, object]) -> dict[str, object]:
        body = {key: value for key, value in base.items() if key != "reasoning" or model not in self._models_without_reasoning()}
        body["messages"] = messages
        body["model"] = model
        return body

    def _gemini_request(self, model: str, messages: list[dict[str, str]]) -> tuple[str, dict[str, str], dict[str, object]]:
        """Google AI Studio generateContent. The key goes in a header, never in the URL."""
        system_text = messages[0]["content"]
        contents = [
            {"role": "model" if message["role"] == "assistant" else "user", "parts": [{"text": message["content"]}]}
            for message in messages[1:]
        ]
        url = f"{GEMINI_ENDPOINT}/{model}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self._gemini_api_key()}
        body = {
            "systemInstruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.25,
                "maxOutputTokens": 1200,
                "thinkingConfig": self._gemini_thinking_config(model),
            },
        }
        return url, headers, body

    @staticmethod
    def _gemini_thinking_config(model: str) -> dict[str, object]:
        """Keep thinking to a minimum: Gemini 3.x takes a thinkingLevel, Gemini 2.x a zero thinkingBudget."""
        if model.startswith("gemini-3"):
            return {"thinkingLevel": settings.GEMINI_THINKING_LEVEL}
        return {"thinkingBudget": 0}

    @staticmethod
    def _gemini_text(result: dict[str, object]) -> Optional[str]:
        candidates = result.get("candidates") or []
        if not candidates or not isinstance(candidates[0], dict):
            return None
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        return text or None

    async def _call_with_backoff(
        self, client, provider: str, model: str, messages: list[dict[str, str]],
        base: dict[str, object], deadline: float, label: str,
    ) -> tuple[int, Optional[str], Optional[str]]:
        """One model, retried on HTTP 429 after a short backoff until this model's time share ends."""
        while True:
            if provider == "gemini":
                url, headers, body = self._gemini_request(model, messages)
            else:
                url, headers, body = self.url, self.headers, self._openrouter_body(model, messages, base)
            if provider == "gemini":
                response = await client.post(url, headers=headers, json=body, timeout=GEMINI_TIMEOUT_SECONDS)
            else:
                response = await client.post(url, headers=headers, json=body)
            if response.status_code != 429:
                break
            if time.monotonic() + RATE_LIMIT_BACKOFF_SECONDS > deadline:
                break
            logger.warning(f"{label} Model ({model}) rate-limited; retrying after {RATE_LIMIT_BACKOFF_SECONDS}s")
            await asyncio.sleep(RATE_LIMIT_BACKOFF_SECONDS)
        if response.status_code != 200:
            return response.status_code, None, None
        result = response.json()
        if provider == "gemini":
            return 200, self._gemini_text(result), result.get("modelVersion") or model
        if "error" in result:
            return 200, None, None
        choices = result.get("choices")
        if not choices or not choices[0].get("message"):
            return 200, None, None
        raw = choices[0]["message"].get("content")
        if not raw or not isinstance(raw, str):
            return 200, None, None
        return 200, raw, result.get("model") or model

    async def _rewrite_source_bound(self, request: EventRewriteRequest) -> Tuple[List[str], List[str], Optional[str]]:
        """Interpret the event sentence and its source summary; no curated facts are required."""
        cascade = self._source_bound_cascade()
        if not cascade:
            raise ValueError("No AI provider configured (OPENROUTER_API_KEY or GEMINI_API_KEY).")
        summary = " ".join(source_summary_sentences(request))
        rich_source = len(summary) >= SOURCE_RICH_MIN_CHARS
        self.last_source_fact_status = get_source_fact_status(None)
        self.last_language_format_status = "unknown"
        messages = [
            {"role": "system", "content": SOURCE_BOUND_SYSTEM_PROMPT},
            *[message for pair in SOURCE_BOUND_FEW_SHOT for message in (
                {"role": "user", "content": pair[0]},
                {"role": "assistant", "content": pair[1]},
            )],
            {"role": "user", "content": self._build_source_bound_user_message(request, summary, rich_source)},
        ]
        base = {"stream": False, "temperature": 0.25, "max_tokens": 1200, "reasoning": {"effort": "none"}}
        block_limit = settings.MAX_THREAD_LENGTH - 20
        rejections: list[str] = []
        self.last_validation_reason = None
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=35.0) as client:
            for attempt, (provider, model, label) in enumerate(cascade, start=1):
                if time.monotonic() - started > SOURCE_BOUND_TIME_BUDGET_SECONDS:
                    rejections.append("time_budget")
                    break
                try:
                    # Each provider gets an equal share of the event's model time budget.
                    share = SOURCE_BOUND_TIME_BUDGET_SECONDS / len(cascade)
                    deadline = min(time.monotonic() + share, started + SOURCE_BOUND_TIME_BUDGET_SECONDS)
                    status, raw_text, responded_model = await self._call_with_backoff(
                        client, provider, model, messages, base, deadline, label,
                    )
                    if status != 200:
                        logger.warning(f"{label} Model ({model}) returned HTTP {status}")
                        rejections.append("rate_limited" if status == 429 else "http_error")
                        continue
                    if not raw_text:
                        rejections.append("empty_response")
                        continue
                    content = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
                    if self._detect_prompt_leak(content):
                        rejections.append("prompt_leak")
                        continue
                    content = self._clean_meta_text(content)
                    emoji_line_present, emoji, blocks, image_prompt = self._parse_source_bound_response(content)
                    reasons = list(validate_source_bound_content(
                        blocks, request, emoji_line_present, max_block_chars=block_limit,
                        summary_present=bool(summary),
                    ))
                    if not self._has_turkish_vocabulary("\n".join(blocks)):
                        reasons.append("language")
                    if reasons:
                        rejections.extend(reasons)
                        logger.warning(f"{label} Model ({model}) rejected: {','.join(reasons)}")
                        continue
                    parts = self._assemble_source_bound_parts(emoji, blocks, request.formatted_date)
                    if any(len(part) > block_limit for part in parts):
                        rejections.append("length")
                        continue
                    self.last_generation_model = responded_model or model
                    self.last_generation_type = "ai_source_bound"
                    self.last_language_format_status = "passed"
                    self.last_source_id = None
                    self.last_source_url = request.source_url
                    self.last_validation_reason = None
                    logger.info(
                        f"Source-bound generation accepted: provider={provider} attempt={attempt} "
                        f"rich_source={rich_source} blocks={len(parts)}"
                    )
                    logger.info(f"Source-bound sample: {' | '.join(parts)[:400]}")
                    return parts, [], image_prompt
                except Exception as error:
                    rejections.append("exception")
                    logger.warning(f"⚠️ {label} Model ({model}) exception: {type(error).__name__}")
        unique_reasons = ",".join(dict.fromkeys(rejections)) or "all_models_failed"
        self.last_validation_reason = unique_reasons
        logger.error(f"Source-bound generation failed after {len(cascade)} attempts: {unique_reasons}")
        raise RuntimeError(unique_reasons)

    @staticmethod
    def _build_source_bound_user_message(request: EventRewriteRequest, summary: str, rich_source: bool) -> str:
        year = f" ({request.year})" if request.year else ""
        return (
            f"Kaynak olay: {request.original_text}{year}\n"
            f"Kaynak özeti: {summary or 'Sağlanmadı.'}\n"
            f"Kaynak zengin mi: {'evet' if rich_source else 'hayır'}"
        )

    @staticmethod
    def _parse_source_bound_response(content: str) -> Tuple[bool, str, List[str], Optional[str]]:
        """Split the model output into emoji, body blocks and optional image prompt. Header is not expected."""
        image_prompt = None
        if "GORSEL_PROMPT:" in content:
            content, _, image_part = content.partition("GORSEL_PROMPT:")
            image_prompt = image_part.strip() or None
        emoji_match = _EMOJI_LINE.search(content)
        emoji_line_present = emoji_match is not None
        raw_emoji = emoji_match.group(1) if emoji_match else ""
        if emoji_match:
            content = content[:emoji_match.start()] + content[emoji_match.end():]
        blocks: list[str] = []
        for section in content.split("---"):
            text = _ECHOED_HEADER.sub("", section.strip(), count=1).strip()
            if text:
                blocks.append(text)
        return emoji_line_present, AIService._canonical_emoji(raw_emoji), blocks, image_prompt

    @staticmethod
    def _canonical_emoji(raw: str) -> str:
        """Return an approved emoji; anything outside the approved set becomes the default."""
        stripped = raw.replace("️", "")
        for choice in EMOJI_CHOICES:
            if choice.replace("️", "") == stripped:
                return choice
        return DEFAULT_EMOJI

    @staticmethod
    def _assemble_source_bound_parts(emoji: str, blocks: List[str], formatted_date: Optional[str]) -> List[str]:
        """Code owns the header and the #tarih tag; the model only writes body text."""
        body = list(blocks)
        if not _TAG_TARIH.search(body[0]):
            body[0] = f"{body[0].rstrip()} #tarih"
        header = f"{emoji} Tarihte Bugün ({formatted_date})" if formatted_date else f"{emoji} Tarihte Bugün"
        return [f"{header}\n\n{body[0]}", *body[1:]]

    @staticmethod
    def _has_turkish_vocabulary(text: str) -> bool:
        words = set(re.findall(r'\b[a-zA-ZçÇşŞğĞüÜöÖıİ]{2,}\b', text.lower()))
        return len(words.intersection(_TURKISH_COMMON_WORDS)) >= 2

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
        profile = resolve_fact_profile(request)
        self.prompt_version = PROMPT_VERSION_PROFILED if profile else PROMPT_VERSION_SOURCE_BOUND
        reason = "model_generation_failed"
        try:
            result = await self.rewrite_event(request)
            tweets, poll_options, image_prompt = result
            if profile is None:
                # Source-bound output was already validated inside rewrite_event.
                return result
            validation_reasons = validate_event_content(tweets, request, profile)
            if len("".join(tweets)) >= 80 and not validation_reasons:
                return result
            reason = self.last_validation_reason or ",".join(validation_reasons) or "output_too_short"
            logger.warning("AI output rejected by final source guard: {}", reason)
        except Exception as error:
            reason = str(error)[:80] or "model_generation_failed"
            logger.warning("AI rewrite failed ({}); using source-backed fallback.", reason)
        self.last_generation_model = None
        self.last_validation_reason = reason
        self.last_source_fact_status = get_source_fact_status(profile)
        if profile is None:
            return self.generate_structured_fallback(request, reason)
        return self.generate_source_fallback(request, reason)

    def generate_structured_fallback(self, request: EventRewriteRequest, reason: str) -> Tuple[List[str], List[str], Optional[str]]:
        """Code-built output for profile-less events whose model attempts failed; nothing is model-written."""
        self.last_source_fact_status = get_source_fact_status(None)
        self.last_language_format_status = "fallback_template"
        self.last_source_id = request.source_title
        self.last_source_url = request.source_url
        parts, used_sentence = build_structured_parts(
            request, self.recent_published_texts, DEFAULT_EMOJI, settings.MAX_THREAD_LENGTH - 20,
        )
        self.last_generation_type = f"source_fallback:{reason}:structured"
        self.last_used_source_sentence = used_sentence
        return parts, [], None

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
