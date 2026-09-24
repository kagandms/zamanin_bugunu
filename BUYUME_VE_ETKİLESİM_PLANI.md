# Zamanın Bugünü – Büyüme, Etkileşim ve Sistem İyileştirme Planı

## 1. Veri Analizi ve Kanıtlanmış İçerik Başarıları

Kullanıcı tarafından sağlanan Threads Insights (Son 7, 14, 30 gün) verileri incelendiğinde net desenler ortaya çıkmıştır:

### A. En Çok Yanıt (Yorum) Alan Gönderiler:
1. **22 Eylül 1964:** Cumhurbaşkanı Cemal Gürsel & Yassıada (4 yanıt, 10 beğeni, 3 repost, 3.9B izlenme)
2. **25 Ağustos 1925:** Atatürk ve Şapka Devrimi (İnebolu) (4 yanıt, 6 beğeni)
3. **13 Eylül 1959:** Luna 2 Sovyet Uzay Roketi (4 yanıt, 2 beğeni)
4. **2 Eylül 1826:** Osmanlı Vaka-i Hayriye sonrası dönüşüm (4 yanıt, 1 beğeni)

### B. En Çok Beğeni ve Yeniden Paylaşım Alan Gönderiler:
1. **22 Eylül 1964:** Cemal Gürsel / Yassıada (10 Beğeni)
2. **25 Ağustos 1925:** Atatürk / Şapka Devrimi (6 Beğeni)
3. **7 Ağustos 1982:** ASALA Esenboğa Havalimanı Terör Saldırısı (6 Beğeni)
4. **1 Ağustos 1975:** Helsinki Nihai Senedi / Soğuk Savaş (6 Beğeni)

### C. En Çok Görüntülenme Alan Gönderiler:
1. **Cemal Gürsel / Yassıada:** 3.900 görüntüleme
2. **Finlandiya Kauhajoki Trajedisi:** 1.900 görüntüleme
3. **Fransa Rainbow Warrior Skandalı:** 1.000 görüntüleme
4. **Helsinki Senedi:** 967 görüntüleme

---

## 2. Mühendislik Çözümleri ve Uygulama Maddeleri

### Madde 1: Keşfet Trafiğini Takipçiye Çevirme (Platform Ayrışımlı CTA)
* **Threads:** `@zamaninbugunu` etiketi ile doğal, merak uyandırıcı takip çağrısı:
  `Tarihin perde arkasını ve unutulan dönüm noktalarını her gün keşfetmek için takipte kalın 👉 @zamaninbugunu`
* **Telegram:** `https://t.me/zamaninbugunu` bağlantısı içeren zengin davet formatı.

### Madde 2: Kanıtlanmış Konulara Öncelik Veren Skorlama Algoritması
* **1919 – 1999 Türk Yakın Tarihi (Atatürk, Darbeler, ASALA, Kıbrıs, Liderler):** +40 puan.
* **Osmanlı & Milli Mücadele:** +25 puan.
* **Soğuk Savaş & Büyük Diplomatik/Uzay Olayları:** +20 puan.
* **Türkiye ile Bağı Olmayan Zayıf Olaylar (Örn: Malta bağımsızlığı):** -15 puan ceza.

### Madde 3: Prime-Time Gece Zirvesi Zamanlaması (Cron)
* **Eski:** 09:07, 13:07, 17:07, 21:07 TSİ
* **Yeni:** 
  * 09:07 TSİ (06:07 UTC) - Sabah güne başlama
  * 14:07 TSİ (11:07 UTC) - Öğle molası
  * 20:07 TSİ (17:07 UTC) - Akşam dinlenme başlangıcı
  * 22:07 TSİ (19:07 UTC) - **Gece Zirvesi (4.500 aktif izleyici kuşağı)**
* Cron: `7 6,11,17,19 * * *`

### Madde 4: Tarih Tutarsızlığının Kod Düzeyinde Engellenmesi (Deterministic Header Override)
* `ai_service.py` içinde `_parse_ai_response` aşamasında, ilk tweet'in ilk satırı ne olursa olsun zorunlu olarak `🕊️ Tarihte Bugün ({formatted_date})` ile değiştirilir. LLM halüsinasyonları kod düzeyinde sıfırlanır.

### Madde 5: Threads 60 Günlük Token Sağlık Takibi & Erken Uyarı Sistemi
* Meta Graph API `refresh_access_token` uç noktası ile token ömrü otomatik uzatılır.
* Token geçersiz olduğunda veya hata aldığında Telegram yöneticisine acil durum bildirim mesajı iletilir.
