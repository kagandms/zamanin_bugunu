import tweepy
import requests
import os
import random
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# --- 1. OPENROUTER (DEEPSEEK) İLE METİN YAZARLIĞI ---
def rewrite_with_deepseek(original_text):
    api_key = os.getenv("OPENROUTER_API_KEY") # GitHub'daki anahtarı alır
    if not api_key:
        print("UYARI: API Key bulunamadı, orijinal metin kullanılacak.")
        return original_text, []

    # ADRES DEĞİŞTİ: Artık OpenRouter'a gidiyoruz
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    system_prompt = (
        "Sen profesyonel bir sosyal medya yöneticisisin. Görevin, sana verilen tarihi olayı "
        "Twitter (X) platformu için viral olacak, merak uyandırıcı ve etkileşim alacak bir formata dönüştürmektir. "
        "\n\nKURALLAR:"
        "\n1. Cevabın SADECE atılacak tweet metninden oluşmalıdır."
        "\n2. ASLA 'İşte tweetiniz:', 'Revize edilmiş hali:' gibi giriş veya bitiş cümleleri yazma."
        "\n3. Ansiklopedik dili bırak, samimi ve heyecanlı konuş."
        "\n4. 1-2 adet emoji kullan."
        "\n5. ZİNCİR (FLOOD) KURALI: Eğer konu tek tweete sığmayacak kadar derinse veya anlatılacak çok şey varsa, "
        "tweetleri '---' (üç tire) işareti ile ayırarak birden fazla parça halinde yaz."
        "\n6. Sadece ZİNCİRİN EN SON TWEETİNE takipçilerle etkileşim kuracak 2 veya 3 şıklı bir anket sorusu ekle."
        "\n7. GÖRSEL PROMPT: En sona (metinden tamamen ayrı) bu olayı betimleyen, yapay zeka resim çizim aracı için İngilizce bir prompt yaz."
        "\nFORMAT:"
        "\n[Tweet 1]"
        "\n---"
        "\n[Tweet 2]"
        "\nANKET: [Seçenek 1] | [Seçenek 2]"
        "\nGORSEL_PROMPT: [English Image Description]"
        "\n8. Her tweet parçasının uzunluğu (hashtagler dahil) 280 karakteri geçmesin."
    )

    payload = {
        "model": "deepseek/deepseek-chat", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Metin: {original_text}"}
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
            print(f"OpenRouter API Hatası: {response.text}")
            return [original_text], [], None
            
        result = response.json()
        
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content'].strip()
            
            # İçerik Temizliği
            content = content.replace('"', '').replace("'", "")
            
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
                poll_options = poll_options[:3]
            else:
                content_text = content
            
            # 3. Zincir Ayrıştırma
            if "---" in content_text:
                tweet_parts = [part.strip() for part in content_text.split("---") if part.strip()]
            else:
                tweet_parts = [content_text]

            print(f"Yapay Zeka metni revize etti! ({len(tweet_parts)} parça zincir) 🤖")
            return tweet_parts, poll_options, image_prompt
        else:
            print("API yanıtı beklendiği gibi değil.")
            return [original_text], [], None
            
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")
        return [original_text], [], None

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

# --- 3. AKILLI VERİ ÇEKME ---
# --- 2.5 TARİHÇE KONTROLÜ (DUPLICATE PREVENTION) ---
def get_history():
    today_str = (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d")
    history_file = "history.txt"
    
    if not os.path.exists(history_file):
        return []

    with open(history_file, "r") as f:
        lines = f.readlines()
        
    if not lines:
        return []
        
    # İlk satır tarih mi?
    file_date = lines[0].strip()
    if file_date != today_str:
        return [] # Tarih değişmiş, hafıza temiz
        
    return [l.strip() for l in lines[1:]]

def save_to_history(text):
    today_str = (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d")
    history = get_history()
    history.append(text)
    
    with open("history.txt", "w") as f:
        f.write(f"{today_str}\n")
        for item in history:
            f.write(f"{item}\n")

# --- 3. AKILLI VERİ ÇEKME ---
def get_smart_event():
    # TR Saati Ayarı
    today = datetime.now() + timedelta(hours=3)
    month = today.month
    day = today.day
    
    print(f"Tarih (TR): {day}.{month}")
    
    # Geçmişi Oku
    used_events = get_history()
    print(f"Bugün paylaşılanlar: {len(used_events)} adet")
    
    # Tüm kategorilerden veri çekip havuz oluşturacağız
    categories = ["events", "births", "deaths"]
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
                            
                        all_items.append(item)
                        
                        # Önem Filtresi: Events için 4+, diğerleri için 2+ kaynak
                        min_pages = 4 if cat == "events" else 2
                        if len(item.get("pages", [])) >= min_pages:
                            all_important_items.append(item)

        if not all_items:
            print("Uygun (paylaşılmamış) içerik kalmadı!")
            return None, None, []

        # Seçim Yapma
        if all_important_items:
            print(f"Toplam {len(all_important_items)} önemli içerik bulundu.")
            selected_item = random.choice(all_important_items)
        else:
            print("Önemli içerik bulunamadı, genel havuzdan seçiliyor.")
            selected_item = random.choice(all_items)

        # Veri Ayrıştırma
        category = selected_item.get("_category", "events")
        year = selected_item.get("year")
        raw_text = selected_item.get("text")
        
        # --- TARİHÇEYE KAYDET (Geçici değil, main'de başarılı olursa kaydedeceğiz ama burada text lazım) ---
        # Tasarım kararı: get_smart_event sadece seçer. Kaydetme işi main'de tweet atılınca yapılır.
        # Bu fonksiyon seçilen 'item'ı değil 'raw_text'i döndürüyor. Main raw_text'i de bilmeli mi? 
        # Hayır, yapay zeka rewrite ediyor.
        # Biz history'ye 'raw_text'i kaydetmeliyiz ki bir sonraki fetch'te duplicate'i bulabilelim.
        # O yüzden return değerine raw_text'i de eklemeliyiz.
        
        # --- YAPAY ZEKA DOKUNUŞU ---
        print(f"Seçilen Kategori: {category} | Orijinal: {raw_text} | Yıl: {year}")
        tweet_parts, poll_options, image_prompt = rewrite_with_deepseek(raw_text, year)
        
        # Emoji Seçimi
        emoji_map = {"events": "📅", "births": "🎂", "deaths": "🕊️"}
        header_emoji = emoji_map.get(category, "📅")
        
        final_tweets = []
        
        if len(tweet_parts) == 1:
            # Tek Tweet
            text = f"{header_emoji} Tarihte Bugün ({day}.{month}.{year})\n\n{tweet_parts[0]} #tarih #tarihteneoldu"
            final_tweets.append(text)
        else:
            # Zincir (Thread)
            # 1. Tweet: Başlık + İlk Parça + Hashtagler
            first_tweet = f"{header_emoji} Tarihte Bugün ({day}.{month}.{year})\n\n{tweet_parts[0]} #tarih #tarihteneoldu (1/{len(tweet_parts)})"
            final_tweets.append(first_tweet)
            
            # Diğer Tweetler
            for idx, part in enumerate(tweet_parts[1:], start=2):
                next_tweet = f"{part} ({idx}/{len(tweet_parts)})"
                final_tweets.append(next_tweet)
        
        # Görsel Kontrolü
        image_url = None
        # Görsel Kontrolü
        image_url = None
        if selected_item.get("pages"):
            first_page = selected_item["pages"][0]
            if "originalimage" in first_page:
                image_url = first_page["originalimage"]["source"]
            elif "thumbnail" in first_page:
                image_url = first_page["thumbnail"]["source"]

        return final_tweets, image_url, poll_options, raw_text

    except Exception as e:
        print(f"Veri çekme hatası: {e}")
        return [], None, [], None

# --- 4. ETKİLEŞİM (MENTION CEVAPLAMA) ---
def generate_ai_reply(text):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key: return "Teşekkürler! 🤖"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    system_prompt = (
        "Sen samimi bir tarih botusun. Takipçinin mentionuna kısa, nazik ve esprili bir cevap ver. "
        "Eğer bir tarih sorusuysa kısaca cevapla. Değilse teşekkür et."
        "Maksimum 2 cümle."
    )
    
    payload = {
        "model": "deepseek/deepseek-chat",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
    }
    headers = {"Authorization": f"Bearer {api_key}", "HTTP-Referer": "https://github.com/kagandms", "X-Title": "TarihBot"}
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            content = r.json()['choices'][0]['message']['content'].strip()
            return content.replace('"', '')
    except:
        pass
    return "Teşekkürler! Tarihle kalın. 📜"

def check_mentions_and_reply(client_v2, my_user_id):
    print("🔔 Etkileşimler kontrol ediliyor...")
    start_id = None
    
    # Son kalınan ID'yi oku
    if os.path.exists("last_mention_id.txt"):
        with open("last_mention_id.txt", "r") as f:
            start_id = f.read().strip()
            
    try:
        # Pagination param
        params = {"id": my_user_id, "max_results": 10, "tweet_fields": ["id", "text", "author_id"]}
        if start_id:
            params["since_id"] = start_id
            
        mentions = client_v2.get_users_mentions(**params)
        
        if mentions.data:
            new_last_id = start_id
            for mention in reversed(mentions.data): # Eskiden yeniye
                print(f"Yanıtlanıyor: {mention.id} - {mention.text}")
                reply_text = generate_ai_reply(mention.text)
                
                try:
                    client_v2.create_tweet(text=f"@{mention.author_id} {reply_text}", in_reply_to_tweet_id=mention.id)
                    new_last_id = mention.id
                    print("Yanıt gönderildi.")
                except Exception as e:
                    print(f"Yanıt hatası: {e}")
            
            # Yeni ID'yi kaydet
            if new_last_id:
                with open("last_mention_id.txt", "w") as f:
                    f.write(str(new_last_id))
        else:
            print("Yeni etkileşim yok.")
            
    except Exception as e:
        print(f"Etkileşim işlem hatası: {e}")

def download_image(url):
    filename = "temp_image.jpg"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return filename
        else:
            print(f"Resim indirilemedi. Status Code: {response.status_code}")
    except Exception as e:
        print(f"Resim indirme hatası: {e}")
    return None

def main():
    api_v1 = get_twitter_api_v1()
    client_v2 = get_twitter_client_v2()
    
    print("Bot başlatılıyor...")
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
                    media = api_v1.media_upload(filename)
                    media_id = media.media_id_string # String olarak alalım
                    print(f"Görsel yüklendi! Media ID: {media_id}")
                    os.remove(filename)
                except Exception as e:
                    print(f"Görsel yüklenemedi: {e}")
        
        # Zincir Gönderimi
        sent_successfully = False
        for i, text in enumerate(tweet_thread):
            # Tweet Parametrelerini Hazırla
            tweet_params = {"text": text}
            
            # İlk tweet ise görsel ekle
            if i == 0 and media_id:
                tweet_params["media_ids"] = [media_id]
                print(f"Tweet parametrelerine visual eklendi: {tweet_params['media_ids']}")
            
            # Zincirleme mantığı
            if last_tweet_id:
                tweet_params["in_reply_to_tweet_id"] = last_tweet_id
            
            # Son tweet ise anket
            if i == len(tweet_thread) - 1:
                if poll_options and len(poll_options) >= 2:
                    tweet_params["poll_options"] = poll_options
                    tweet_params["poll_duration_minutes"] = 1440

            # --- GÜVENLİ GÖNDERİM (FALLBACK MEPKANİZMASI) ---
            # 1. Deneme: Her şey dahil
            try:
                response = client_v2.create_tweet(**tweet_params)
                last_tweet_id = response.data['id']
                print(f"Tweet {i+1}/{len(tweet_thread)} gönderildi! (Tam)")
                sent_successfully = True
                continue # Başarılı, sonraki tweete geç
            except Exception as e:
                print(f"Hata (Tam): {e}")

            # 2. Deneme: Anketsiz
            if "poll_options" in tweet_params:
                print("Anketsiz deneniyor...")
                del tweet_params["poll_options"]
                if "poll_duration_minutes" in tweet_params:
                    del tweet_params["poll_duration_minutes"]
                
                try:
                    response = client_v2.create_tweet(**tweet_params)
                    last_tweet_id = response.data['id']
                    print(f"Tweet {i+1}/{len(tweet_thread)} gönderildi! (Anketsiz)")
                    sent_successfully = True
                    continue # Başarılı
                except Exception as e:
                    print(f"Hata (Anketsiz): {e}")

            # 3. Deneme: Medyasız (Sadece Metin)
            if "media_ids" in tweet_params:
                print("Medyasız deneniyor...")
                del tweet_params["media_ids"]
                
                try:
                    response = client_v2.create_tweet(**tweet_params)
                    last_tweet_id = response.data['id']
                    print(f"Tweet {i+1}/{len(tweet_thread)} gönderildi! (Metin)")
                    sent_successfully = True
                    continue # Başarılı
                except Exception as e:
                    print(f"Hata (Metin): {e}")

            # Buraya geldiyse tüm denemeler başarısız olmuştur
            print("Tüm denemeler başarısız. Zincir kırıldı.")
            break

        # Başarıyla atıldıysa geçmişe kaydet
        if sent_successfully and raw_text:
            save_to_history(raw_text)
            print("İçerik geçmişe kaydedildi. ✅")
                
    else:
        print("İçerik bulunamadı.")
        
    # Etkileşim Kontrolü (Devre dışı)
    # try:
    #     me = client_v2.get_me()
    # except Exception as e:
    #     pass

if __name__ == "__main__":
    main()