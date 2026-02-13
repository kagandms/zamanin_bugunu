import tweepy
from tweepy.errors import TooManyRequests
import requests
import os
import random
import re
import time
import mimetypes
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# --- GLOBAL CONSTANTS ---
TURKEY_TZ = ZoneInfo("Europe/Istanbul")
MAX_TWEET_LENGTH = 280
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

load_dotenv()

# --- 1. OPENROUTER (DEEPSEEK) İLE METİN YAZARLIĞI ---

def smart_split_text(text, limit=200):
    """
    Metni anlam bütünlüğünü koruyarak parçalara böler.
    Öncelik sırası:
    1. Satır sonları (\\n)
    2. Cümle bitişleri (.!?)
    3. Kelime boşlukları
    4. Zorla kesme (Hard truncation)
    """
    parts = []
    
    while text:
        # Eğer metin limitten kısaysa direkt ekle
        if len(text) <= limit:
            parts.append(text)
            break
            
        # Kesme noktası bul
        split_index = -1
        
        # 1. Satır sonu ara (limit içinde)
        newline_index = text.rfind('\n', 0, limit)
        if newline_index != -1:
            split_index = newline_index
        
        # 2. Cümle sonu ara (limit içinde)
        if split_index == -1:
            for char in ['. ', '! ', '? ']:
                idx = text.rfind(char, 0, limit)
                if idx != -1:
                    if idx + 1 > split_index:
                        split_index = idx + 1
        
        # 3. Boşluk ara (En son çare)
        if split_index == -1:
            space_index = text.rfind(' ', 0, limit)
            if space_index != -1:
                split_index = space_index
                
        # 4. Hiçbiri yoksa (kelime çok uzunsa) zorla kes
        if split_index == -1:
            split_index = limit
            
        # Parçayı ekle
        chunk = text[:split_index].strip()
        if chunk:
            parts.append(chunk)
        
        # Kalan metni hazırla
        text = text[split_index:].strip()
        
    return parts

def rewrite_with_deepseek(original_text, year=None):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("UYARI: API Key bulunamadı, orijinal metin kullanılacak.")
        return [original_text], [], None
    
    # Key temizliği (boşluk varsa)
    api_key = api_key.strip()
    print("✅ OpenRouter API Key mevcut.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    
    year_context = f" ({year} yılında gerçekleşti)" if year else ""
    
    # Fallback durumunda da akıllı bölme kullanmak için helper
    def return_with_fallback(text):
        if len(text) > MAX_TWEET_LENGTH - 60: # Biraz daha pay bırakalım
            print(f"⚠️ Fallback metni çok uzun, akıllı bölme uygulanıyor...")
            return smart_split_text(text, MAX_TWEET_LENGTH - 60), [], None
        return [text], [], None

    system_prompt = (
        "Sen profesyonel bir tarihçi, editör ve sosyal medya uzmanısın. Görevin, sana verilen tarihi olayı "
        "Twitter (X) platformu için EKSİKSİZ, DOĞRU ve ÇOK İLGİ ÇEKİCİ bir formata dönüştürmektir."
        "\n\n⚠️ KRİTİK KARAKTER LİMİTİ:"
        "\n- Her tweet MUTLAKA 200 karakterden KISA olmalı (başlık ve hashtagler için yer bırak)."
        "\n- 200 karakteri aşan tweetler REDDEDİLİR. Kısa, öz ve vurucu yaz."
        "\n\nGENEL İÇERİK POLİTİKASI:"
        "\n- Sadece savaşları değil; BİLİM, SANAT, FUTBOL, FİNANS, EKONOMİ ve SİYASET tarihini de anlat."
        "\n- Takipçilerin ilgisini çekecek detayları öne çıkar."
        "\n\nKESİN KURALLAR:"
        "\n1. DİL ve GRAMER: Türkçe yazım kurallarına %100 uy."
        "\n2. TARİHSEL DOĞRULUK: Yılı asla karıştırma."
        "\n3. ÜSLUP: Hikayeleştirici ve samimi yaz."
        "\n4. EMOJİ: 1-2 emoji kullan."
        "\n5. ZİNCİR: Konu derinse '---' ile böl. Her parça MAX 200 karakter!"
        "\n6. ANKET: Zincir sonunda akıllı bir anket sor."
        "\n7. GÖRSEL PROMPT: En sona İngilizce görsel promptu yaz."
        "\n8. HALÜSINASYON: Metinde olmayan bilgiyi ekleme."
        "\n\nFORMAT:"
        "\n[Tweet 1 - max 200 karakter]"
        "\n---"
        "\n[Tweet 2 - max 200 karakter]"
        "\nANKET: [Soru] | [Seçenek 1] | [Seçenek 2] | [Seçenek 3]"
        "\nGORSEL_PROMPT: [English Image Prompt]"
    )

    payload = {
        "model": "deepseek/deepseek-chat", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Olay: {original_text}{year_context}\nBu tarihi olayı viral olacak, hatasız ve akıcı bir Türkçe ile revize et."}
        ],
        "stream": False
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/kagandms/tarihte-bugun-botu",
        "X-Title": "Tarihte Bugun Botu"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"⚠️ OpenRouter API Hatası ({response.status_code}): {response.text}")
            if response.status_code == 401:
                 print("❗ HATA: API Key geçersiz veya bakiye yetersiz. Lütfen OPENROUTER_API_KEY secret'ını kontrol edin.")
            return return_with_fallback(original_text)
            
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content'].strip()
            
            # İçerik Temizliği
            content = content.replace('"', '').replace("'", "")
            
            # AI Prefix Temizliği ("[Tweet 1]", "Tweet 1:", "Tweet 1 -" vb.)
            content = re.sub(r'\[?Tweet\s*\d+\]?[:\-–—]?\s*', '', content, flags=re.IGNORECASE)
            content = content.strip()
            
            # Değişkenler
            tweet_parts = []
            poll_options = []
            image_prompt = None
            
            # 1. Görsel Prompt Ayrıştırma
            if "GORSEL_PROMPT:" in content:
                parts = content.split("GORSEL_PROMPT:")
                content = parts[0].strip() # Tweet kısmı
                image_prompt = parts[1].strip()
            
            # 2. Anket Ayrıştırma
            if "ANKET:" in content:
                split_poll = content.split("ANKET:")
                content_text = split_poll[0].strip()
                raw_poll = split_poll[1].strip()
                poll_options = [opt.strip() for opt in raw_poll.split("|") if opt.strip()]
                poll_options = poll_options[:4]  # Twitter max 4 seçenek destekler
                # Twitter anket seçenekleri max 25 karakter
                poll_options = [opt[:25] for opt in poll_options]
            else:
                content_text = content
            
            # 3. Zincir Ayrıştırma
            if "---" in content_text:
                tweet_parts = [part.strip() for part in content_text.split("---") if part.strip()]
            else:
                tweet_parts = [content_text]
            
            # 4. Akıllı Bölme (Truncation yerine Splitting)
            final_parts = []
            for part in tweet_parts:
                # Header ve hashtagler için yaklaşık 80 karakter pay bırakıyoruz
                limit = MAX_TWEET_LENGTH - 80 
                if len(part) > limit:
                     print(f"⚠️ Parça çok uzun ({len(part)} > {limit}), akıllı bölme uygulanıyor...")
                     split_chunks = smart_split_text(part, limit)
                     final_parts.extend(split_chunks)
                else:
                     final_parts.append(part)
            
            processed_parts = final_parts

            print(f"Yapay Zeka metni revize etti! ({len(processed_parts)} parça zincir) 🤖")
            return processed_parts, poll_options, image_prompt
        else:
            print("API yanıtı beklendiği gibi değil.")
            return return_with_fallback(original_text)
            
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")
        return return_with_fallback(original_text)

# --- 2. TWITTER BAĞLANTILARI ---
def get_twitter_api_v1():
    auth = tweepy.OAuthHandler(
        os.getenv("API_KEY"),
        os.getenv("API_SECRET")
    )
    auth.set_access_token(
        os.getenv("ACCESS_TOKEN"),
        os.getenv("ACCESS_TOKEN_SECRET")
    )
    return tweepy.API(auth)

def get_twitter_client_v2():
    return tweepy.Client(
        consumer_key=os.getenv("API_KEY"),
        consumer_secret=os.getenv("API_SECRET"),
        access_token=os.getenv("ACCESS_TOKEN"),
        access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
    )

# --- 2.5 TARİHÇE KONTROLÜ (DUPLICATE PREVENTION) ---
def get_turkey_now():
    """Türkiye saatini döndürür (yaz/kış otomatik)."""
    return datetime.now(TURKEY_TZ)

def get_history():
    today_str = get_turkey_now().strftime("%Y-%m-%d")
    history_file = "history.txt"
    
    if not os.path.exists(history_file):
        return []

    try:
        with open(history_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []
        
    if not lines:
        return []
        
    # İlk satır tarih mi?
    file_date = lines[0].strip()
    if file_date != today_str:
        return []  # Tarih değişmiş, hafıza temiz
        
    return [l.strip() for l in lines[1:]]

def save_to_history(text):
    today_str = get_turkey_now().strftime("%Y-%m-%d")
    history = get_history()
    history.append(text)
    
    with open("history.txt", "w", encoding="utf-8") as f:
        f.write(f"{today_str}\n")
        for item in history:
            f.write(f"{item}\n")

# --- 3. AKILLI VERİ ÇEKME ---

def turkish_lower(s):
    """Türkçe karakterleri doğru şekilde küçük harfe çevirir (İ→i, I→ı)."""
    s = unicodedata.normalize('NFKC', s)
    s = s.replace('İ', 'i').replace('I', 'ı')
    return s.lower()

# Türkiye ve Türklerle ilgili anahtar kelimeler
TURKISH_KEYWORDS = [
    # Ülke ve şehirler
    "türk", "türkiye", "osmanlı", "ottoman", "turkey", "turkish",
    "istanbul", "ankara", "izmir", "bursa", "antalya", "konya", "adana",
    "trabzon", "edirne", "sivas", "erzurum", "diyarbakır", "gaziantep",
    "konstantinopolis", "constantinople", "bizans", "byzantine",
    # Tarihi terimler
    "sultan", "padişah", "sadrazam", "vezir", "paşa", "bey", "han",
    "selçuklu", "seljuk", "göktürk", "hunlar", "anadolu", "anatolia",
    "boğaz", "bosphorus", "çanakkale", "gallipoli", "sakarya", "dumlupınar",
    # Önemli kişiler (soyadları)
    "atatürk", "mustafa kemal", "fatih", "kanuni", "süleyman", "mehmed",
    "abdülhamid", "enver", "talat", "cemal", "ismet", "inönü",
    # Kurumlar ve kavramlar  
    "tbmm", "meclis", "cumhuriyet", "republic of turkey",
    "kıbrıs", "cyprus", "ege", "aegean", "karadeniz", "black sea",
    "marmara", "akdeniz", "mediterranean",
    # Spor ve kültür
    "galatasaray", "fenerbahçe", "beşiktaş", "trabzonspor",
    "türk lirası", "borsa istanbul", "bist"
]

# Regex pattern'i önceden derle (performans için)
TURKISH_PATTERN = re.compile('|'.join(map(re.escape, TURKISH_KEYWORDS)), re.IGNORECASE)

def is_turkish_related(item):
    """Bir olayın Türkiye/Türklerle ilgili olup olmadığını kontrol eder."""
    # Tüm metinleri birleştir
    texts = [item.get("text", "")]
    
    for page in item.get("pages", []):
        texts.append(page.get("title", ""))
        texts.append(page.get("description", ""))
        texts.append(page.get("extract", ""))
    
    combined = turkish_lower(' '.join(texts))
    return bool(TURKISH_PATTERN.search(combined))

def get_smart_event():
    # TR Saati Ayarı
    today = get_turkey_now()
    month = today.month
    day = today.day
    
    print(f"Tarih (TR): {day}.{month}")
    
    # Geçmişi Oku
    used_events = get_history()
    print(f"Bugün paylaşılanlar: {len(used_events)} adet")
    
    # Tüm kategorilerden veri çekip havuz oluşturacağız
    # 'selected' kategorisi en bilinen olayları içerir
    categories = ["selected", "events", "births", "deaths"]
    all_turkish_items = []  # Türkiye ile ilgili olaylar (EN YÜKSEK ÖNCELİK)
    all_important_items = []
    all_items = []
    
    headers = {
        'User-Agent': 'TarihBot/3.0 (https://twitter.com/TarihteNeOldu; me@example.com)'
    }

    try:
        # Her kategori için API çağrısı
        for cat in categories:
            url = f"https://tr.wikipedia.org/api/rest_v1/feed/onthisday/{cat}/{month}/{day}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get(cat, [])
                if items:
                    for item in items:
                        # Kategori bilgisini öğeye ekle
                        item["_category"] = cat
                        
                        # Çakışma Kontrolü (Text üzerinden)
                        if item.get("text") in used_events:
                            continue
                            
                        # 'Selected' kategorisine öncelik veriyoruz (Daha popüler)
                        if cat == "selected":
                           item["_priority"] = 2
                        else:
                           item["_priority"] = 1
                           
                        all_items.append(item)
                        
                        # 🇹🇷 TÜRKİYE FİLTRESİ - En yüksek öncelik
                        if is_turkish_related(item):
                            all_turkish_items.append(item)
                            print(f"🇹🇷 Türkiye ile ilgili olay bulundu: {item.get('text', '')[:50]}...")
                        
                        # Önem Filtresi: Events için 4+, diğerleri için 2+ kaynak
                        min_pages = 4 if cat == "events" else 2
                        
                        # Selected zaten önemli olduğu için direkt ekle
                        if cat == "selected" or len(item.get("pages", [])) >= min_pages:
                            all_important_items.append(item)

        if not all_items:
            print("Uygun (paylaşılmamış) içerik kalmadı!")
            return None, None, [], None

        # Seçim Yapma - Öncelik Sırası:
        # 1. Türkiye ile ilgili olaylar (EN YÜKSEK)
        # 2. Önemli olaylar
        # 3. Genel havuz
        
        if all_turkish_items:
            print(f"🇹🇷 Toplam {len(all_turkish_items)} Türkiye ile ilgili içerik bulundu!")
            selected_item = random.choice(all_turkish_items)
        elif all_important_items:
            print(f"Türkiye ile ilgili içerik bulunamadı. {len(all_important_items)} önemli içerikten seçiliyor.")
            selected_item = random.choice(all_important_items)
        else:
            print("Önemli içerik bulunamadı, genel havuzdan seçiliyor.")
            selected_item = random.choice(all_items)

        # Veri Ayrıştırma
        category = selected_item.get("_category", "events")
        year = selected_item.get("year")
        raw_text = selected_item.get("text")
        
        # --- TARİHÇEYE KAYDET (Geçici değil, main'de başarılı olursa kaydedeceğiz ama burada text lazım) ---
        
        # --- YAPAY ZEKA DOKUNUŞU ---
        print(f"Seçilen Kategori: {category} | Orijinal: {raw_text} | Yıl: {year}")
        tweet_parts, poll_options, image_prompt = rewrite_with_deepseek(raw_text, year)
        
        # Emoji Seçimi
        emoji_map = {"selected": "🌟", "events": "📅", "births": "🎂", "deaths": "🕊️"}
        header_emoji = emoji_map.get(category, "📅")
        
        # Year kontrolü (None durumu için)
        year_str = str(year) if year else "?"
        
        final_tweets = []
        header = f"{header_emoji} Tarihte Bugün ({day}.{month}.{year_str})"
        hashtags = "#tarih #tarihteneoldu"
        
        if len(tweet_parts) == 1:
            # Tek Tweet
            text = f"{header}\n\n{tweet_parts[0]} {hashtags}"
            # Karakter limiti kontrolü
            if len(text) > MAX_TWEET_LENGTH:
                available = MAX_TWEET_LENGTH - len(header) - len(hashtags) - 4  # 4 = 2x\n + space + buffer
                tweet_parts[0] = tweet_parts[0][:available].rsplit(' ', 1)[0] + "…"
                text = f"{header}\n\n{tweet_parts[0]} {hashtags}"
            final_tweets.append(text)
        else:
            # Zincir (Thread)
            chain_suffix = f"(1/{len(tweet_parts)})"
            first_text = f"{header}\n\n{tweet_parts[0]} {hashtags} {chain_suffix}"
            # İlk tweet karakter limiti kontrolü
            if len(first_text) > MAX_TWEET_LENGTH:
                available = MAX_TWEET_LENGTH - len(header) - len(hashtags) - len(chain_suffix) - 5
                tweet_parts[0] = tweet_parts[0][:available].rsplit(' ', 1)[0] + "…"
                first_text = f"{header}\n\n{tweet_parts[0]} {hashtags} {chain_suffix}"
            final_tweets.append(first_text)
            
            # 2...N. Tweetler
            for i, part in enumerate(tweet_parts[1:], 2):
                chain_suffix = f"({i}/{len(tweet_parts)})"
                tweet_text = f"{part} {chain_suffix}"
                # Devam tweetleri karakter limiti kontrolü
                if len(tweet_text) > MAX_TWEET_LENGTH:
                    available = MAX_TWEET_LENGTH - len(chain_suffix) - 2
                    part = part[:available].rsplit(' ', 1)[0] + "…"
                    tweet_text = f"{part} {chain_suffix}"
                final_tweets.append(tweet_text)
                
        # Görsel Kontrolü (Wikipedia)
        final_image_url = None
        if selected_item.get("pages"):
            first_page = selected_item["pages"][0]
            if first_page.get("thumbnail"):
                final_image_url = first_page["thumbnail"]["source"]
            elif first_page.get("originalimage"):
                final_image_url = first_page["originalimage"]["source"]
                
        # Görsel Kontrolü (Yapay Zeka - Pollinations.ai)
        # Eğer wiki görseli yoksa VE yapay zeka bir prompt ürettiyse
        if not final_image_url and image_prompt:
            print(f"Wiki görseli yok, yapay zeka çizecek: {image_prompt}")
            # Promptu URL dostu hale getir
            safe_prompt = requests.utils.quote(image_prompt)
            # Pollinations URL'i oluştur
            final_image_url = f"https://pollinations.ai/p/{safe_prompt}?width=1024&height=1024&seed={random.randint(0, 999999)}&model=flux"
        
        return final_tweets, final_image_url, poll_options, raw_text

    except Exception as e:
        print(f"Hata oluştu: {e}")
        return None, None, [], None

# --- 4. ETKİLEŞİM YÖNETİMİ (Yanıt Verme) ---
# Ücretsiz sürümde mention okuma engellendiği için devre dışı bırakılmıştır.
def check_mentions_and_reply(client, api_v1):
     print("Mention kontrolü Free Tier API'de desteklenmiyor.")
     pass

def download_image(url):
    
    headers = {
        'User-Agent': 'TarihBot/3.0 (+https://github.com/kagandms/tarihte-bugun-botu)'
    }
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=15)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                extension = mimetypes.guess_extension(content_type) if content_type else None
                
                # Fallback uzantı kontrolü
                if not extension:
                    if content_type and ('jpeg' in content_type or 'jpg' in content_type):
                        extension = '.jpg'
                    elif content_type and 'png' in content_type:
                        extension = '.png'
                    elif content_type and 'webp' in content_type:
                        extension = '.webp'
                    else:
                        extension = '.jpg'  # Default fallback
                
                # Temizlik
                if extension == '.jpe': 
                    extension = '.jpg'

                filename = f"temp_image{extension}"
                
                # Boyut limiti kontrolü ile indirme
                total_size = 0
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        total_size += len(chunk)
                        if total_size > MAX_IMAGE_SIZE:
                            print(f"⚠️ Görsel çok büyük ({total_size // 1024 // 1024}MB > 5MB), indirme iptal.")
                            f.close()
                            os.remove(filename)
                            return None
                        f.write(chunk)
                        
                return filename
            
            elif response.status_code == 429:
                print(f"⚠️ Hata 429 (Too Many Requests) - Deneme {attempt+1}/{max_retries}. Bekleniyor...")
                time.sleep(2 * (attempt + 1)) # Artan bekleme süresi (2s, 4s...)
                continue
                
            else:
                print(f"Resim indirilemedi. Status Code: {response.status_code}")
                # 404 gibi ciddi hatalarda direkt çık
                if response.status_code in [404, 403]:
                    break
        
        except Exception as e:
            print(f"Resim indirme hatası (Deneme {attempt+1}): {e}")
            time.sleep(1)
            
    print("❌ Tüm denemeler başarısız. Görsel indirilemedi.")
    return None

def main():
    api_v1 = get_twitter_api_v1()
    client_v2 = get_twitter_client_v2()
    
    print("Bot başlatılıyor...")

    # --- DEBUG: Kimlik Doğrulama Kontrolü ---
    try:
        user = api_v1.verify_credentials()
        print(f"✅ Giriş Başarılı: {user.screen_name}")
        # Not: tweepy API v1.1 objesinde 'access_level' özelliği olmayabilir, ama testi geçmesi bile önemli.
        # Manuel kontrol için hata verirse göreceğiz.
    except Exception as e:
        print(f"❌ KİMLİK DOĞRULAMA HATASI: {e}")
        print("Lütfen API Key, Secret ve Access Token'larınızı kontrol edin.")
        return
    # -------------------------------------------

    tweet_thread, image_url, poll_options, raw_text = get_smart_event()
    
    if tweet_thread:
        last_tweet_id = None
        
        # Görsel Hazırlığı (Sadece ilk tweet için)
        media_id = None
        if image_url:
            print(f"Görsel indiriliyor: {image_url}")
            filename = download_image(image_url)
            if filename:
                try:
                    try:
                        media = api_v1.media_upload(filename)
                        media_id = media.media_id_string # String olarak alalım
                        print(f"Görsel yüklendi! Media ID: {media_id}")
                    except Exception as e:
                        print(f"Görsel yüklenemedi: {e}")
                finally:
                    if os.path.exists(filename):
                        os.remove(filename)
                        print(f"Geçici görsel silindi: {filename}")
        
        # Zincir Gönderimi
        all_tweets_sent = True # Başarı bayrağı
        
        for i, text in enumerate(tweet_thread):
            # Tweet Parametrelerini Hazırla
            tweet_params = {"text": text}
            
            # İlk tweet ise görsel ekle
            if i == 0 and media_id:
                tweet_params["media_ids"] = [media_id]
            
            # Zincirleme mantığı
            if last_tweet_id:
                tweet_params["in_reply_to_tweet_id"] = last_tweet_id
            
            # Son tweet ise anket
            if i == len(tweet_thread) - 1:
                if poll_options and len(poll_options) >= 2:
                    tweet_params["poll_options"] = poll_options
                    tweet_params["poll_duration_minutes"] = 1440

            # --- GÜVENLİ GÖNDERİM VE RETRY MEKANİZMASI ---
            max_retries = 3
            tweet_sent = False
            
            for attempt in range(max_retries):
                try:
                    print(f"Tweet {i+1}/{len(tweet_thread)} gönderiliyor (Deneme {attempt+1})...")
                    response = client_v2.create_tweet(**tweet_params)
                    last_tweet_id = response.data['id']
                    print(f"✅ Tweet {i+1} başarıyla gönderildi!")
                    tweet_sent = True
                    break # Başarılıysa döngüden çık
                    
                except TooManyRequests as e:
                    print(f"⚠️ RATE LIMIT (429) - Deneme {attempt+1}/{max_retries}")
                    reset_timestamp = None
                    if e.response is not None and 'x-rate-limit-reset' in e.response.headers:
                        reset_timestamp = int(e.response.headers['x-rate-limit-reset'])
                        wait_time = reset_timestamp - int(time.time()) + 5 # 5sn tampon
                        if wait_time > 0:
                            print(f"⏳ {wait_time} saniye bekleniyor...")
                            time.sleep(min(wait_time, 60)) # Max 60sn bekle, çok uzunsa pes et
                        else:
                            time.sleep(10)
                    else:
                        time.sleep(15)
                        
                except Exception as e:
                    error_str = str(e)
                    print(f"❌ Hata (Deneme {attempt+1}): {error_str}")
                    
                    if "403 Forbidden" in error_str:
                        if "duplicate" in error_str.lower():
                            print("👉 DUPLICATE CONTENT: Bu tweet zaten atılmış. Zincire devam ediliyor.")
                            # Duplicate ise atılmış sayıp devam edelim (belki crash sonrası tekrar çalıştı)
                            tweet_sent = True 
                            break
                        else:
                            # Diğer 403 hataları (suspended vs) kalıcıdır
                            break
                    
                    # Anketsiz veya Medyasız tekrar deneme stratejileri
                    if attempt == 0:
                        # İlk hatada varsa anketi/medyayı kaldırıp bir sonraki denemeye temiz girelim
                        if "poll_options" in tweet_params:
                            print("🔄 Strateji: Anket kaldırılıyor...")
                            del tweet_params["poll_options"]
                            if "poll_duration_minutes" in tweet_params:
                                del tweet_params["poll_duration_minutes"]
                            continue
                            
                        if "media_ids" in tweet_params:
                            print("🔄 Strateji: Medya kaldırılıyor...")
                            del tweet_params["media_ids"]
                            continue
                    
                    time.sleep(2 * (attempt + 1)) # Exponential backoff

            if not tweet_sent:
                print(f"🚨 KRİTİK: Tweet {i+1} gönderilemedi! Zincir kırıldı.")
                all_tweets_sent = False
                break
        
        # Başarıyla atıldıysa geçmişe kaydet
        if all_tweets_sent and raw_text:
            save_to_history(raw_text)
            print("İçerik geçmişe kaydedildi. ✅")
        else:
            print("⚠️ Zincir tamamlanamadığı için geçmişe kaydedilmedi (Tekrar denenebilmesi için).")
                
    else:
        print("İçerik bulunamadı.")
        
    # Etkileşim Kontrolü (Devre dışı)
    # try:
    #     me = client_v2.get_me()
    # except Exception as e:
    #     pass

if __name__ == "__main__":
    main()