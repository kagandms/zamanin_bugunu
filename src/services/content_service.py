import asyncio
import httpx
import random
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from src.core.logger import logger
from src.core.config import settings
from typing import Optional, List, Tuple


SOURCE_REQUEST_TIMEOUT_SECONDS = 2.0
SOURCE_FETCH_BUDGET_SECONDS = 18.0
SOURCE_MAX_ATTEMPTS = 2
SOURCE_MAX_RETRY_AFTER_SECONDS = 1.0
WIKIMEDIA_USER_AGENT = "TarihBot/4.0 (https://github.com/kagandms/zamanin_bugunu)"


class ContentSourceFetchError(RuntimeError):
    """Raised when every event category fails before returning a valid response."""


@dataclass(frozen=True)
class CategoryFetchResult:
    events: list[dict]
    succeeded: bool
    status_code: int | None
    elapsed_ms: int
    error_class: str
    attempts: int
    retry_after_seconds: float | None = None
from src.services.source_context import select_event_source

TOPIC_KEYWORDS = {
    "SIYASET": [
        "darbe", "seçim", "hükümet", "başbakan", "cumhurbaşkanı", "meclis", "parti", "chp", "akp",
        "antlaşma", "anlaşma", "protokol", "istifa", "sadrazam", "padişah", "parlamento", "anayasa",
        "kanun", "milletvekili", "bakan", "siyasi", "kongre", "cumhuriyet"
    ],
    "AFET_DEPREM": [
        "deprem", "zelzele", "sel", "tsunami", "yangın", "fırtına", "kasırga", "heyelan",
        "salgın", "veba", "kolera", "taşkın", "afet", "facia", "enkaz"
    ],
    "BILIM_TEKNOLOJI": [
        "icat", "keşif", "roket", "uzay", "luna", "nasa", "fizik", "kimya", "matematik",
        "tıp", "aşı", "bilim", "deney", "astronomi", "bilgisayar", "internet", "barometre",
        "teleskop", "nobel", "laboratuvar"
    ],
    "SAVAS_ASKERI": [
        "savaş", "muharebe", "taarruz", "cephe", "kuşatma", "ordu", "donanma", "asker",
        "işgal", "katliam", "gerilla", "bombardıman", "komutan", "askeri", "harekat", "zafer",
        "yenilgi", "tabur", "tümen", "hava kuvvetleri"
    ],
    "KULTUR_SANAT": [
        "roman", "şair", "yazar", "tiyatro", "sinema", "film", "sanat", "ressam", "müzik",
        "konser", "albüm", "beste", "opera", "kitap", "edebiyat", "şiir", "oyuncu"
    ]
}


class ContentService:
    def __init__(self):
        self.base_url = "https://tr.wikipedia.org/api/rest_v1/feed/onthisday"
        self.pageviews_url = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
        self.turkish_keywords = [
            "türk", "türkiye", "osmanlı", "ottoman", "istanbul", "ankara", "atatürk", 
            "selçuklu", "kıbrıs", "akdeniz", "karadeniz", "mehmed", "süleyman",
            "izmir", "antalya", "trabzon", "bursa", "cumhuriyet", "milli", "savaş",
            "galatasaray", "fenerbahçe", "beşiktaş", "futbol"
        ]
        self.pattern = re.compile('|'.join(map(re.escape, self.turkish_keywords)), re.IGNORECASE)

    def _is_turkish(self, text: str) -> bool:
        """Checks if the text is related to Turkey."""
        s = unicodedata.normalize('NFKC', text)
        s = s.replace('İ', 'i').replace('I', 'ı').lower()
        return bool(self.pattern.search(s))

    @staticmethod
    def classify_topic(text: str) -> str:
        """
        Classifies an event text into one of the main thematic topics:
        SIYASET, AFET_DEPREM, BILIM_TEKNOLOJI, SAVAS_ASKERI, KULTUR_SANAT, or GENEL.
        """
        if not text:
            return "GENEL"

        s = unicodedata.normalize('NFKC', text)
        s = s.replace('İ', 'i').replace('I', 'ı').lower()

        scores = {}
        for category, keywords in TOPIC_KEYWORDS.items():
            count = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw), s))
            if count > 0:
                scores[category] = count

        if scores:
            # Pick category with the highest hit count
            return max(scores.items(), key=lambda x: x[1])[0]

        return "GENEL"

    def _calculate_fame_score(self, item: dict) -> int:
        """
        Calculates a 'fame score' for an event based on Wikipedia signals.
        Higher score = more famous/notable event.
        """
        score = 0
        
        # 1. Category bonus — Wikipedia editors hand-pick 'selected' events
        if item.get('_category') == 'selected':
            score += 50
        elif item.get('_category') == 'events':
            score += 20
        elif item.get('_category') == 'births':
            score += 10
        elif item.get('_category') == 'deaths':
            score += 5

        # 1.5 Turkish content bonus & foreign penalty
        text = item.get('text', '')
        is_tr = self._is_turkish(text)
        if is_tr:
            score += 45
        else:
            # Strong penalty for non-Turkish events — Turkish audience rarely engages with foreign history
            score -= 60

        # 1.6 Proven High-Engagement Historical Eras (35+ Age Demographics):
        # 1919-1999 Turkish Era (Atatürk, Darbeler, Gürsel, Menderes, ASALA, Kıbrıs, vb.)
        year = item.get('year')
        if year:
            try:
                i_year = int(year)
                if is_tr and 1919 <= i_year <= 1999:
                    score += 60  # Proven #1 engagement category (e.g. Kenan Evren / 12 Eylül)
                elif is_tr and i_year < 1919:
                    score += 30  # Ottoman / Seljuk history
                elif not is_tr and i_year >= 1945 and any(w in text.lower() for w in ['sovyet', 'uzay', 'luna', 'savaş', 'nükleer', 'helsinki']):
                    score += 15  # Space / Cold War diplomacy milestones
            except (ValueError, TypeError):
                pass

        # 1.7 Topic Category Bonus (Based on Proven Views & Replies):
        topic = self.classify_topic(text)
        if topic in ('SIYASET', 'AFET_DEPREM'):
            score += 40
        elif topic == 'SAVAS_ASKERI':
            score += 30
        elif topic in ('KULTUR_SANAT', 'BILIM_TEKNOLOJI'):
            score += 15

        # 2. Linked pages count — more linked articles = more notable
        pages = item.get('pages', [])
        score += len(pages) * 8

        # 3. Has thumbnail/image — famous subjects always have images
        for page in pages:
            if page.get('thumbnail'):
                score += 15
                break

        # 4. Has original image (high-res) — very well-documented
        for page in pages:
            if page.get('originalimage'):
                score += 10
                break

        # 5. Has description — well-documented subjects
        for page in pages:
            if page.get('description') and len(page['description']) > 10:
                score += 5
                break

        # 7. Text length bonus — detailed event text = more substance
        text = item.get('text', '')
        if len(text) > 100:
            score += 10
        elif len(text) > 50:
            score += 5

        # 8. Year relevance — milestone years get bonus
        year = item.get('year')
        if year:
            try:
                current_year = datetime.now().year
                years_ago = current_year - int(year)
                # Round anniversaries (50, 100, 150, etc.) are more engaging
                if years_ago > 0 and years_ago % 100 == 0:
                    score += 30
                elif years_ago > 0 and years_ago % 50 == 0:
                    score += 20
                elif years_ago > 0 and years_ago % 25 == 0:
                    score += 10
            except (ValueError, TypeError):
                pass

        return score

    @staticmethod
    def _source_context_score(item: dict) -> int:
        """Prefer candidates whose linked page offers enough context to support richer copy."""
        source = select_event_source(item)
        if source is None:
            return 0
        score = sum(8 for threshold in (120, 300, 600) if len(source.context) >= threshold)
        return score + 8 * min(len(re.findall(r"[.!?](?=\s|$)", source.context)), 2)

    @staticmethod
    def _popularity_bonus(pageviews: int) -> int:
        """Keep pageviews useful without allowing them to dominate source depth."""
        return min(max(pageviews, 0) // 5000, 30)

    def _get_dynamic_date_range(self) -> Tuple[str, str]:
        """
        Calculates the last 3 completed calendar months for the Wikimedia pageviews API.
        Format: YYYYMM01 to YYYYMMDD
        """
        now = datetime.now()
        first_of_current = datetime(now.year, now.month, 1)
        last_month_end = first_of_current - timedelta(days=1)

        start_year = last_month_end.year
        start_month = last_month_end.month - 2
        if start_month <= 0:
            start_month += 12
            start_year -= 1

        start_str = f"{start_year}{start_month:02d}01"
        end_str = f"{last_month_end.year}{last_month_end.month:02d}{last_month_end.day:02d}"
        return start_str, end_str

    async def _get_pageviews(self, page_title: str, client: httpx.AsyncClient) -> int:
        """Fetches monthly page view count from Wikipedia as a fame proxy."""
        try:
            import urllib.parse
            encoded_title = urllib.parse.quote(page_title, safe='')
            start_date, end_date = self._get_dynamic_date_range()
            url = (
                f"{self.pageviews_url}/tr.wikipedia/all-access/all-agents/"
                f"{encoded_title}/monthly/{start_date}/{end_date}"
            )
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('items', [])
                total_views = sum(item.get('views', 0) for item in items)
                return total_views
        except Exception:
            pass  # Silently fail — pageviews is a bonus signal
        return 0

    async def fetch_events(self, month: int, day: int) -> list:
        """Fetch source event data within its own deadline, before downstream preparation."""
        categories = ["selected", "events", "births", "deaths"]
        raw_items = []
        deadline = time.monotonic() + SOURCE_FETCH_BUDGET_SECONDS
        successful_categories = 0
        active_category = None
        active_started = time.monotonic()
        budget_expired = False

        try:
            async with asyncio.timeout(SOURCE_FETCH_BUDGET_SECONDS):
                async with httpx.AsyncClient() as client:
                    client.headers.update({'User-Agent': WIKIMEDIA_USER_AGENT})
                    for cat in categories:
                        active_category = cat
                        active_started = time.monotonic()
                        result = await self._fetch_category(client, cat, month, day, deadline)
                        raw_items.extend(result.events)
                        successful_categories += int(result.succeeded)
                        active_category = None
        except TimeoutError:
            budget_expired = True
            if active_category is not None:
                logger.info("Event source category={} attempt=cancelled status=none elapsed_ms={} candidate_count=0 error_class=preparation_budget_exhausted",
                            active_category, int((time.monotonic() - active_started) * 1000))
            logger.info("Event source fetch budget exhausted elapsed_ms={} successful_categories={} candidate_count={}",
                        int((time.monotonic() - (deadline - SOURCE_FETCH_BUDGET_SECONDS)) * 1000),
                        successful_categories, len(raw_items))
        if not successful_categories:
            if budget_expired:
                raise ContentSourceFetchError("Source data fetch budget expired before a valid response")
            raise ContentSourceFetchError("All event categories failed to return valid data")
        outcome = ("empty" if successful_categories == len(categories) else "empty_partial") if not raw_items else (
            "partial" if successful_categories < len(categories) else "ok"
        )
        logger.info("Event source fetch outcome={} successful_categories={} candidate_count={}",
                    outcome, successful_categories, len(raw_items))
        return raw_items

    async def _fetch_category(
        self, client: httpx.AsyncClient, category: str, month: int, day: int, deadline: float
    ) -> CategoryFetchResult:
        started = time.monotonic()
        url = f"{self.base_url}/{category}/{month}/{day}"
        last_status = None
        error_class = "retry_budget_exhausted"
        attempts_made = 0
        for attempt in range(1, SOURCE_MAX_ATTEMPTS + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                error_class = "preparation_budget_exhausted"
                break
            attempts_made = attempt
            result = await self._request_category(client, url, category, attempt, remaining)
            last_status = result.status_code
            error_class = result.error_class
            self._log_category_attempt(category, attempt, result)
            if result.succeeded or not self._can_retry(result, attempt, deadline):
                return self._finish_category(started, last_status, result)
            await asyncio.sleep(self._retry_delay(result, attempt))
        logger.info("Event source category={} attempt={} status={} elapsed_ms={} candidate_count=0 error_class={}",
                    category, attempts_made, last_status if last_status is not None else "none",
                    int((time.monotonic() - started) * 1000), error_class)
        return CategoryFetchResult([], False, last_status, int((time.monotonic() - started) * 1000),
                                   error_class, attempts_made)

    async def _request_category(
        self, client: httpx.AsyncClient, url: str, category: str, attempt: int, remaining: float
    ) -> CategoryFetchResult:
        started = time.monotonic()
        status_code = None
        try:
            response = await client.get(url, timeout=min(SOURCE_REQUEST_TIMEOUT_SECONDS, remaining))
        except httpx.TimeoutException:
            return CategoryFetchResult([], False, None, self._elapsed_ms(started), "timeout", attempt)
        except httpx.RequestError:
            return CategoryFetchResult([], False, None, self._elapsed_ms(started), "network_error", attempt)
        status_code = response.status_code
        if status_code != 200:
            error_class = self._http_error_class(status_code)
            retry_after = self._retry_after_seconds(response.headers) if error_class in {"http_429", "http_5xx"} else None
            return CategoryFetchResult([], False, status_code, self._elapsed_ms(started), error_class,
                                       attempt, retry_after)
        try:
            items = self._decode_category_items(response.json(), category)
        except ValueError:
            return CategoryFetchResult([], False, status_code, self._elapsed_ms(started), "invalid_json", attempt)
        except TypeError:
            return CategoryFetchResult([], False, status_code, self._elapsed_ms(started), "invalid_schema", attempt)
        return CategoryFetchResult(items, True, status_code, self._elapsed_ms(started), "none", attempt)

    @staticmethod
    def _decode_category_items(payload: object, category: str) -> list[dict]:
        if not isinstance(payload, dict) or not isinstance(payload.get(category), list):
            raise TypeError("invalid event category schema")
        items = payload[category]
        if any(not isinstance(item, dict) or not isinstance(item.get("text"), str) for item in items):
            raise TypeError("invalid event item schema")
        return [{**item, "_category": category} for item in items]

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((time.monotonic() - started) * 1000)

    @staticmethod
    def _http_error_class(status_code: int) -> str:
        if status_code == 429:
            return "http_429"
        if 400 <= status_code < 500:
            return "http_4xx"
        if 500 <= status_code < 600:
            return "http_5xx"
        return "http_other"

    @staticmethod
    def _log_category_attempt(category: str, attempt: int, result: CategoryFetchResult) -> None:
        logger.info("Event source category={} attempt={} status={} elapsed_ms={} candidate_count={} error_class={}",
                    category, attempt, result.status_code if result.status_code is not None else "none",
                    result.elapsed_ms, len(result.events), result.error_class)

    @staticmethod
    def _finish_category(started: float, status_code: int | None, result: CategoryFetchResult) -> CategoryFetchResult:
        return CategoryFetchResult(result.events, result.succeeded, status_code,
                                   ContentService._elapsed_ms(started), result.error_class, result.attempts)

    @staticmethod
    def _can_retry(result: CategoryFetchResult, attempt: int, deadline: float) -> bool:
        is_transient = result.error_class in {"timeout", "network_error", "http_429", "http_5xx"}
        delay = result.retry_after_seconds
        if delay is not None and delay > SOURCE_MAX_RETRY_AFTER_SECONDS:
            return False
        retry_delay = delay if delay is not None else min(0.25 * attempt, SOURCE_MAX_RETRY_AFTER_SECONDS)
        return (is_transient and attempt < SOURCE_MAX_ATTEMPTS and
                deadline - time.monotonic() > retry_delay + SOURCE_REQUEST_TIMEOUT_SECONDS)

    @staticmethod
    def _retry_delay(result: CategoryFetchResult, attempt: int) -> float:
        if result.status_code == 429 or (result.status_code is not None and result.status_code >= 500):
            retry_after = result.retry_after_seconds
            if retry_after is not None:
                return retry_after
        return min(0.25 * attempt, SOURCE_MAX_RETRY_AFTER_SECONDS)

    @staticmethod
    def _retry_after_seconds(headers: httpx.Headers) -> float | None:
        value = headers.get("Retry-After")
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    async def select_best_event(self, items: list, used_texts: list) -> Optional[dict]:
        """
        Selects the MOST FAMOUS event using a multi-signal scoring algorithm:
        1. Filters duplicates
        2. Scores each event by fame signals (category, images, descriptions)
        3. For top candidates, fetches Wikipedia page views as the ultimate fame indicator
        4. Injects detected topic category into candidate dict
        5. Returns the highest-scoring unused event
        """
        # Filter duplicates
        candidates = [i for i in items if i.get('text') not in used_texts]
        
        if not candidates:
            return None

        pool = candidates
        turkish_count = sum(1 for i in pool if self._is_turkish(i.get('text', '')))
        logger.info(f"Event pool: {len(pool)} total ({turkish_count} Turkish, {len(pool) - turkish_count} Global)")

        # Step 2: Calculate fame scores for all candidates
        scored = []
        for item in pool:
            fame = self._calculate_fame_score(item)
            scored.append((fame, item))
        
        # Sort by fame score (highest first)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Step 3: For top 5 candidates, fetch real Wikipedia page views
        top_candidates = scored[:5]
        
        async with httpx.AsyncClient() as client:
            client.headers.update({'User-Agent': WIKIMEDIA_USER_AGENT})
            
            final_scored = []
            for base_score, item in top_candidates:
                pageview_score = 0
                pages = item.get('pages', [])
                if pages:
                    main_page_title = pages[0].get('titles', {}).get('canonical', '')
                    if main_page_title:
                        pageview_score = await self._get_pageviews(main_page_title, client)
                
                # Cap pageviews so popularity cannot overwhelm available source context.
                popularity_bonus = self._popularity_bonus(pageview_score)
                context_score = self._source_context_score(item)
                combined_score = base_score + popularity_bonus + context_score
                final_scored.append((combined_score, pageview_score, item))

            # Sort by combined score
            final_scored.sort(key=lambda x: x[0], reverse=True)

        # Log top 3 for transparency
        for i, (score, views, item) in enumerate(final_scored[:3]):
            logger.info(
                f"  #{i+1} (score={score}, views={views:,}): "
                f"{item.get('text', '')[:70]}"
            )
        
        # Weighted random selection from top 3 to avoid deterministic repeats
        top_n = final_scored[:3]
        if len(top_n) == 1:
            winner = top_n[0]
        else:
            scores = [max(entry[0], 1) for entry in top_n]
            total = sum(scores)
            weights = [s / total for s in scores]
            winner = random.choices(top_n, weights=weights, k=1)[0]

        selected = winner[2]
        # Auto-classify topic
        topic = self.classify_topic(selected.get('text', ''))
        selected['_topic_category'] = topic

        logger.info(
            f"🏆 Selected event (score={winner[0]}, pageviews={winner[1]:,}, topic={topic}) "
            f"from top {len(top_n)} candidates"
        )
        
        return selected
