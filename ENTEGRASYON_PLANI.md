# Zamanın Bugünü – Sistem İyileştirme ve Entegrasyon Planı

## 1. Yönetici Özeti ve Mevcut Durum Analizi

Bu entegrasyon planı, "Zamanın Bugünü" Telegram ve Threads otomasyon botunun içerik kalitesini, algoritmik etkileşim oranını, çalışma hızını ve veri takip yeteneklerini artırmak amacıyla hazırlanmıştır. 

### Mevcut Durum Bulguları
1. **Günlük Gönderi Dağılımı:**
   - **Hedef:** `.github/workflows/schedule.yml` üzerindeki cron (`7 6,10,14,18 * * *`) uyarınca Türkiye saatiyle günde 4 paylaşım (09:07, 13:07, 17:07, 21:07).
   - **Gerçekleşen:** `bot_data.db` üzerindeki geçmiş analizinde günde ortalama 2–3 (bazen 1) paylaşım yapıldığı, neredeyse hiçbir gün 4 paylaşıma ulaşılamadığı tespit edilmiştir.
   - **Nedenler:** OpenRouter ücretsiz modellerindeki anlık rate-limit'ler (429), GitHub Actions cron gecikmeleri ve API zaman aşımı durumunda döngünün doğrudan sonlandırılması.
2. **Kitle & Etkileşim:**
   - Son 1–2 günde takipçi sayısı 25'ten 37-38'e çıkmıştır (+%50 artış).
   - Veritabanındaki paylaşımlar incelendiğinde; 12 Eylül Askeri Darbesi ve 1509 "Küçük Kıyamet" Büyük İstanbul Depremi gibi yüksek toplumsal ve tarihsel duyarlılık içeren olayların Threads algoritmasında (For You akışı) etkileşim dalgası yarattığı görülmektedir.
3. **Mevcut Mimari Darboğazlar:**
   - Paylaşılan Threads gönderi ID'leri kaydedilmemektedir (`tweet_id="RESERVED"` olarak kalmaktadır).
   - Gönderi istatistikleri (görüntülenme, beğeni, yanıt) otomatik takip edilememektedir.
   - Threads görsel yüklemesinde 30 saniyelik kör bekleme (`asyncio.sleep(30)`) botu yavaşlatmaktadır.
   - Wikipedia sayfa görüntülenme API'sinde tarih aralığı 2025 yılına sabitlenmiştir (`20250101/20250630`).
   - Olaylar tematik (Siyaset, Bilim, Afet vb.) kategorilere ayrılmamaktadır.

---

## 2. Yüksek Mühendislik İncelemesi (Architecture & Safety Review)

Mevcut sistemin üretimde (production) çalıştığı ve GitHub Actions üzerinde sürekli tetiklendiği göz önüne alınarak şu kritik mühendislik prensipleri benimsenmiştir:

1. **Sıfır Kesinti ve Geriye Dönük Uyumluluk (Zero-Downtime & Backward Compatibility):**
   - SQLite veritabanında `Base.metadata.create_all`, halihazırda var olan tablolara yeni kolon eklemez. Bu nedenle doğrudan model değiştirmek mevcut veritabanında `no such column` hatasına yol açar.
   - **Çözüm:** `init_db()` aşamasında otomatik ve güvenli bir migration fonksiyonu (`PRAGMA table_info` + `ALTER TABLE ... ADD COLUMN`) eklenerek eski veriler %100 korunacaktır.
2. **Asenkron Hata İzolasyonu (Graceful Degradation):**
   - Threads Insights API veya Wikipedia Pageviews sorgusu başarısız olursa, botun asıl görevi olan "zamanında paylaşım yapma" akışı asla sekteye uğramayacaktır.
3. **Deterministik ve Test Edilebilir Kod:**
   - Her modül izole fonksiyonlarla tasarlanacak, kural tabanlı motorlar ile AI çıktıları birbirini doğrulayacaktır.

---

## 3. Beş Özellik İçin Detaylı Entegrasyon Tasarımı

### Özellik 1: Dinamik Wikipedia Pageviews Hesaplama
* **Problem:** `src/services/content_service.py` içinde `_get_pageviews` fonksiyonu `20250101/20250630` tarihine sabitlenmiştir. 2026 yılında eski verileri baz almaktadır.
* **Mühendislik Çözümü:**
  - `datetime.now()` üzerinden dinamik tarih aralığı hesaplanır: Başlangıç olarak son 3 ay öncesinin ilk günü (`YYYYMM01`), bitiş olarak bir önceki ayın son günü (`YYYYMMDD`).
  - Hata durumunda (sayfa bulunamadı / 404 / Wikimedia API zaman aşımı), 0 dönülür; diğer ağırlık sinyalleriyle seçim devam eder.
* **Etkilenen Dosya:** `src/services/content_service.py`

### Özellik 2: Meta Threads Görsel Durumu Kontrolü (Polling & Exponential Backoff)
* **Problem:** `ThreadsService.post_thread` içinde `await asyncio.sleep(30)` kör beklemesi vardır. Meta container'ı bazen 4 saniyede hazır ederken bot 26 saniye boşuna beklemekte; bazen de container hata alsa bile 30 saniye sonra fark edilmektedir.
* **Mühendislik Çözümü:**
  - Meta API endpoint: `GET https://graph.threads.net/v1.0/{container_id}?fields=status,error_message&access_token={token}`
  - `_wait_for_container_status(container_id, max_timeout=45, poll_interval=3)` fonksiyonu geliştirilir.
  - Durum `FINISHED` olduğunda anında yayınlama aşamasına geçilir (ortalama 20+ saniye tasarruf).
  - Durum `ERROR` olduğunda beklemeden metin fallback moduna geçilir.
  - Beklenmedik ağ hatalarında güvenli bekleme ile sistem dayanıklılığı korunur.
* **Etkilenen Dosya:** `src/services/threads_service.py`

### Özellik 3: Algoritmik Etkileşim ve Yorum (Call-to-Action) Optimizasyonu
* **Problem:** Threads algoritmasında gönderinin "Senin İçin" akışına düşmesini sağlayan en büyük sinyal yorum (reply) etkileşimidir. Mevcut metinler salt bilgilendiricidir.
* **Mühendislik Çözümü:**
  - `AIService` system prompt'u güncellenerek son bloğun (3. bölüm) sonuna okuyucunun fikrini soran, tarafsız ve merak uyandırıcı 1 adet soru cümlesi ekletilir.
  - Örnek: *"Sizce bu tarihi karar dönemin şartlarında farklı sonuçlanabilir miydi?"*
  - Metin uzunluğu güvenlik sınırları (`MAX_THREAD_LENGTH` - 400 karakter) korunur. Model CTA üretmese bile akış bozulmaz.
* **Etkilenen Dosya:** `src/services/ai_service.py`

### Özellik 4: Kural Tabanlı ve Yapay Zeka Destekli Konu Sınıflandırması (Tagging)
* **Problem:** Hangi tür konuların (siyaset, bilim, afet, kültür, savaş) daha fazla etkileşim getirdiği bilinememektedir.
* **Mühendislik Çözümü:**
  - 5 temel kategori tanımlanır:
    1. `SIYASET` (darbe, antlaşma, meclis, seçim, cumhuriyet, hükümet...)
    2. `AFET_DEPREM` (deprem, sel, fırtına, salgın, yangın...)
    3. `BILIM_TEKNOLOJI` (roket, keşif, icat, tıp, fizik, uzay...)
    4. `SAVAS_ASKERI` (muharebe, taarruz, ordu, kuşatma, cephe...)
    5. `KULTUR_SANAT` (roman, şair, edebiyat, tiyatro, sinema, müzik...)
    - Eşleşmeyenler: `GENEL`
  - `ContentService` içine deterministik `classify_topic(text)` motoru eklenir.
  - Tespit edilen kategori hem veritabanına kaydedilir hem de analitik sorgulara baz teşkil eder.
* **Etkilenen Dosyalar:** `src/services/content_service.py`, `src/data/models.py`, `src/data/repository.py`, `src/main.py`

### Özellik 5: Threads Post ID Kalıcılığı ve Otomatik Metrik Analiz Servisi
* **Problem:** Paylaşım sonrasında `threads_post_id` kaydedilmediği için Threads Graph API üzerinden metrikler (views, likes, replies, reposts) çekilememektedir.
* **Mühendislik Çözümü:**
  1. `PostHistory` tablosuna `threads_post_id`, `topic_category`, `views`, `likes`, `replies`, `reposts`, `last_synced_at` alanları eklenir.
  2. `init_db()` içine otomatik `PRAGMA table_info` kontrolü ve `ALTER TABLE` eklenerek şema güncellenir.
  3. `threads_service.post_thread` başarılı olunca paylaşılan ana post ID'sini döner: `(success: bool, post_id: Optional[str])`.
  4. `main.py` başarılı paylaşım sonrası veritabanındaki rezervasyonu gerçek ID ile günceller (`repo.update_threads_post_id`).
  5. `src/services/analytics_service.py` ve `src/analytics.py` CLI aracı eklenir:
     - `GET /{post_id}/insights?metric=views,likes,replies,reposts,quotes` sorgusunu yapar.
     - Veritabanındaki metrikleri günceller.
     - Terminalde kategori bazlı etkileşim raporu sunar (Örn: *Siyaset: Ort. 420 izlenme, Bilim: Ort. 110 izlenme*).
* **Etkilenen Dosyalar:** `src/data/models.py`, `src/data/database.py`, `src/data/repository.py`, `src/services/threads_service.py`, `src/main.py`, `src/services/analytics_service.py`, `src/analytics.py`.

---

## 4. Doğrulama ve Test Protokolü

1. **Birim ve Mantık Doğrulaması:**
   - Tarih hesaplama fonksiyonu test edilir.
   - Konu etiketleme fonksiyonu geçmiş 20 gönderi üzerinde test edilir.
   - Veritabanı şema göçünün (migration) mevcut `bot_data.db` verilerini bozmadığı doğrulanır.
2. **Dry-Run Entegrasyon Testi:**
   - `DRY_RUN=True` modunda bot baştan sona çalıştırılarak tüm adımların (tarih seçimi, konu tespiti, AI içerik üretimi, veritabanı rezervasyonu ve güncellemesi) hatasız tamamlandığı teyit edilir.
