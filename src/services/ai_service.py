import httpx
import json
from src.core.config import settings
from src.core.logger import logger
from src.utils.text_utils import smart_split_text, clean_twitter_text
from typing import Tuple, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

class AIService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY.get_secret_value()
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/kagandms/tarihte-bugun-botu",
            "X-Title": settings.APP_NAME
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def rewrite_event(self, original_text: str, year: Optional[str] = None) -> Tuple[List[str], List[str], Optional[str]]:
        """
        Rewrites the event text using DeepSeek to be viral and suitable for Twitter.
        Returns: (tweet_parts, poll_options, image_prompt)
        """
        year_context = f" ({year} yılında gerçekleşti)" if year else ""
        
        system_prompt = (
            "Sen profesyonel bir tarihçi ve sosyal medya uzmanısın. Görevin: "
            "Verilen tarihi olayı Twitter için VİRAL, İLGİ ÇEKİCİ ve DOĞRU bir flood (zincir) haline getirmektir."
            "\n\nKURALLAR:"
            "\n- Her tweet < 220 karakter olmalı (güvenlik payı ile)."
            "\n- Türkçe dil bilgisi kusursuz olmalı."
            "\n- Asla halüsinasyon görme (uydurma bilgi yok)."
            "\n\nFORMAT:"
            "\n[Tweet 1]"
            "\n---"
            "\n[Tweet 2]"
            "\nANKET: [Soru] | [Seçenek 1] | [Seçenek 2]"
            "\nGORSEL_PROMPT: [English Image Prompt]"
        )

        payload = {
            "model": settings.AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Olay: {original_text}{year_context}\nRevize et."}
            ],
            "stream": False
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.url, headers=self.headers, json=payload)
                
                if response.status_code != 200:
                    logger.error(f"AI API Error {response.status_code}: {response.text}")
                    response.raise_for_status()
                    
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                return self._parse_ai_response(content, original_text)

            except Exception as e:
                logger.error(f"AI Service Exception: {e}")
                raise # Re-raise for tenacity to catch

    async def rewrite_event_safe(self, original_text: str, year: Optional[str] = None):
        """Wrapper ensuring fallback if retries fail."""
        try:
            return await self.rewrite_event(original_text, year)
        except Exception as e:
            logger.critical(f"AI Service Failed after retries: {e}")
            # Fallback: Split original text
            return smart_split_text(original_text, settings.MAX_TWEET_LENGTH - 60), [], None

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
        final_tweets = []
        for tweet in tweets:
            if len(tweet) > settings.MAX_TWEET_LENGTH - 20:
                final_tweets.extend(smart_split_text(tweet, settings.MAX_TWEET_LENGTH - 50))
            else:
                final_tweets.append(tweet)
                
        return final_tweets, poll_options, image_prompt
