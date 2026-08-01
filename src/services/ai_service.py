import httpx
import json
from src.core.config import settings
from src.core.logger import logger
from src.utils.text_utils import (
    clean_twitter_text,
    sanitize_http_header_value,
    smart_split_text,
)
from typing import Tuple, List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=30, max=60))
    async def rewrite_event(self, original_text: str, formatted_date: str, year: Optional[str] = None) -> Tuple[List[str], List[str], Optional[str]]:
        """
        Rewrites the event text using DeepSeek to be viral and suitable for Twitter.
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
            "model": settings.AI_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Olay: {original_text}{year_context}\nRevize et."}
            ],
            "stream": False,
            "temperature": 0.3,
            "max_tokens": 1000
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            # 1. Try Primary Model
            try:
                payload["model"] = settings.AI_MODEL
                response = await client.post(self.url, headers=self.headers, json=payload)
                
                if response.status_code != 200:
                    logger.warning(f"Primary Model ({settings.AI_MODEL}) failed: {response.status_code} - BODY: {response.text}")
                    raise Exception(f"Primary model failure: {response.text}")
                    
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                logger.info(f"✅ Success with Primary Model: {settings.AI_MODEL}")
                return self._parse_ai_response(content, original_text)

            except Exception as e:
                logger.warning(f"⚠️ Primary Model Failed: {e}. Switching to Backup Model...")
                
                # 2. Try Backup Model
                try:
                    payload["model"] = settings.BACKUP_MODEL
                    response = await client.post(self.url, headers=self.headers, json=payload)
                    
                    if response.status_code != 200:
                        logger.warning(f"Backup Model ({settings.BACKUP_MODEL}) failed: {response.status_code} - BODY: {response.text}")
                        raise Exception(f"Backup model failure: {response.text}")
                    
                    result = response.json()
                    content = result['choices'][0]['message']['content'].strip()
                    logger.info(f"✅ Success with Backup Model: {settings.BACKUP_MODEL}")
                    return self._parse_ai_response(content, original_text)
                    
                except Exception as backup_e:
                    logger.warning(f"⚠️ Backup Model also failed: {backup_e}. Trying Last Resort...")
                    
                    # 3. Try Last Resort Model (openrouter/free auto-router)
                    try:
                        payload["model"] = settings.LAST_RESORT_MODEL
                        response = await client.post(self.url, headers=self.headers, json=payload)
                        
                        if response.status_code != 200:
                            logger.error(f"Last Resort Model ({settings.LAST_RESORT_MODEL}) failed: {response.status_code} - BODY: {response.text}")
                            raise Exception(f"Last resort failure: {response.text}")
                        
                        result = response.json()
                        content = result['choices'][0]['message']['content'].strip()
                        logger.info(f"✅ Success with Last Resort Model: {settings.LAST_RESORT_MODEL}")
                        return self._parse_ai_response(content, original_text)
                        
                    except Exception as last_e:
                        logger.error(f"❌ All 3 models failed. Last error: {last_e}")
                        raise  # Retries from tenacity will catch this

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
