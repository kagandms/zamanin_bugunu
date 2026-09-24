import httpx
import random
import re
import unicodedata
from datetime import datetime, timedelta
from src.core.logger import logger
from src.core.config import settings
from typing import Optional, List, Tuple

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
            score += 30
        else:
            # Foreign event penalty unless global superpower milestone
            score -= 15

        # 1.6 Proven High-Engagement Historical Eras (35+ Age Demographics):
        # 1919-1999 Turkish Era (Atatürk, Darbeler, Gürsel, Menderes, ASALA, Kıbrıs, vb.)
        year = item.get('year')
        if year:
            try:
                i_year = int(year)
                if is_tr and 1919 <= i_year <= 1999:
                    score += 40  # Proven #1 engagement category
                elif is_tr and i_year < 1919:
                    score += 25  # Ottoman / Seljuk history
                elif not is_tr and i_year >= 1945 and any(w in text.lower() for w in ['sovyet', 'uzay', 'luna', 'savaş', 'nükleer', 'helsinki']):
                    score += 25  # Space / Cold War diplomacy milestones
            except (ValueError, TypeError):
                pass

        # 1.7 Topic Category Bonus (Based on Proven Views & Replies):
        topic = self.classify_topic(text)
        if topic in ('SIYASET', 'AFET_DEPREM'):
            score += 30
        elif topic == 'SAVAS_ASKERI':
            score += 25
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

        # 6. Has extract (longer = more notable)
        for page in pages:
            extract = page.get('extract', '')
            if len(extract) > 200:
                score += 15
            elif len(extract) > 100:
                score += 8
            elif len(extract) > 30:
                score += 3

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
        """Fetches events from Wikipedia for the given date."""
        categories = ["selected", "events", "births", "deaths"]
        raw_items = []
        
        async with httpx.AsyncClient() as client:
            client.headers.update({'User-Agent': 'TarihBot/4.0 (Elite Edition)'})
            
            for cat in categories:
                url = f"{self.base_url}/{cat}/{month}/{day}"
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get(cat, [])
                        for item in items:
                            item['_category'] = cat
                            raw_items.append(item)
                except Exception as e:
                    logger.error(f"Failed to fetch {cat}: {e}")
                    
        return raw_items

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
            client.headers.update({'User-Agent': 'TarihBot/4.0 (Elite Edition)'})
            
            final_scored = []
            for base_score, item in top_candidates:
                pageview_score = 0
                pages = item.get('pages', [])
                if pages:
                    main_page_title = pages[0].get('titles', {}).get('canonical', '')
                    if main_page_title:
                        pageview_score = await self._get_pageviews(main_page_title, client)
                
                # Combine: base score + normalized pageview bonus
                combined_score = base_score + (pageview_score // 100)
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
