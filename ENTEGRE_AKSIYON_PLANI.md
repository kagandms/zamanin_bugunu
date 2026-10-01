# Zamanın Bugünü – Veri Odaklı Entegre Büyüme ve Optimizasyon Planı

## 1. Veri Analizi ve Teşhis Özeti (Gerçek Metrik Bulguları)

1 Ekim 2026 tarihli Threads İstatistikler paneli ve veritabanı kayıtları incelendiğinde sistemin mevcut durumu şöyledir:

| Metrik | Gerçekleşen Değer | Anlamı ve Çıkarım |
| :--- | :--- | :--- |
| **İzleyici Türü** | **9.856 Takipçi Olmayan (%99.7)** / 27 Takipçi (%0.3) | Algoritma kapısı sonuna kadar açık; hesap cezasız ve viral dağıtımda. |
| **Görüntüleme Kaynağı** | **Ana Sayfa / For You (%99.2)** | Trafiğin tamamına yakını organik keşfet akışından geliyor. |
| **Kitle Yaş Piramidi** | **%67.6'sı 35 Yaş ve Üzeri** (%24.9'u 35–44, %23.8'i 25–34) | Kitle Z kuşağı değil; Türkiye yakın siyasi tarihini ve 80/90'ları bilen olgun kitle. |
| **Zirve Saat Kuşağı** | **21:00 – 00:00 (GMT+3)** | Salı, Çarşamba, Perşembe geceleri 3.200 – 3.700 izleyici akışta aktif. |
| **En Yüksek Gönderi** | **Kenan Evren / 12 Eylül (1.890 İzlenme)** | Yakın siyasi tarih ve tartışmalı askeri liderler dwell time ve merak tavanı yapıyor. |
| **En Düşük Gönderi** | **Nazi / Polonya (13 İzlenme)** | Türkiye dışı küresel tarih konuları algoritmada ölü doğuyor. |
| **Kritik Darboğaz** | **51 Profil Ziyareti -> 0 Takipçi** | İçerik merak uyandırıyor fakat profil vitrini (bio/pin) takipçiye dönüştüremiyor. |
| **Algoritmik Tıkanma** | **Yanıt Oranı: %0.16 (Daha Düşük)** | Dışarıdan organik yorum gelmediği için algoritma gönderileri 1.800 bandında kesiyor. |

---

## 2. 5 Fazlı Entegre Eylem Planı

```
+-----------------------------------------------------------------------------------+
|                           ENTEGRE DÖNÜŞÜM DÖNGÜSÜ                                 |
+-----------------------------------------------------------------------------------+
|  [1. Skorlama]      -> 1919-1999 Türk Siyasi Tarihi & Yüz Portreli Olaylar        |
|  [2. Hook & Prompt] -> Merak Uyandıran İlk Cümle + Bölücü Kapanış Sorusu          |
|  [3. Prime-Time]    -> Zirve İçeriğin 21:00-00:00 Arasında Paylaşılması           |
|  [4. Profil Dönüş.] -> Bio Vaadi + Pin Post ile 51 Ziyaretçiyi Takipçiye Çevirme  |
|  [5. Analitik Geri] -> Otomatik GitHub Actions ile Gerçek Organik Yorum Takibi   |
+-----------------------------------------------------------------------------------+
```

---

### FAZ 1: Profil ve Vitrin Dönüşüm Optimizasyonu (Acil / Manuel Aksiyon)
*Amaç: Kenan Evren gibi gönderilerden profile gelen her 50 kişiden en az 5-10'unu kalıcı takipçiye dönüştürmek.*

1. **Biyografi (Bio) Revizyonu:**
   * *Mevcut Zayıf Durum:* Genel veya boş "Tarihte bugün" tanımı.
   * *Uygulanacak Güçlü Bio:*
     > *"Türkiye'nin ve dünyanın perde arkasında kalan dönüm noktaları. Resmi tarihin ötesi, belgeler ve unutulan kararlar. Her gün 4 özel tarihi dosya. 🕊️"*
2. **Sabitlenmiş Gönderi (Pinned Post):**
   * Profilin en tepesine **Kenan Evren / 12 Eylül** gönderisi sabitlenmelidir. Profile ilk giren kişi doğrudan 1.890 izlenmiş, yüksek kaliteli bir dosyayla karşılaşmalıdır.
3. **Kalıcı Link:**
   * Profil link alanına varsa Telegram kanalı (`t.me/zamaninbugunu`) veya arşiv bağlantısı eklenmelidir.

---

### FAZ 2: İçerik Mimarisi ve AI Prompt Mühendisliği (Kod Seviyesi)
*Amaç: Threads'in "Yanıt oranı düşük" uyarısını kırmak ve organik kullanıcı tartışması başlatmak.*

1. **Giriş Kancası (Hook):**
   * Ansiklopedik girişler yasaklandı: *"30 Eylül 1980'de Kenan Evren konuştu..."* yerine:
   * *"12 Eylül darbesinin hemen ardından yapılan bu konuşma, Türkiye'nin sonraki 40 yılını nasıl belirledi? İşte perde arkası 👇"*
2. **Kapanış Tartışma Sorusu (Debate Trigger):**
   * 3. bölümün sonuna okuyucuyu ikiye bölecek net bir soru eklendi:
     * *“Sizce o günün şartlarında alınan bu karar tarihi bir zorunluluk muydu, yoksa vahim bir hata mıydı? Fikrinizi yorumlarda paylaşın 👇”*
3. **Takip Çağrısı (Conversion CTA):**
   * 4. parça (footer) metni:
     * *“Tarihin karanlıkta kalan dosyalarını ve kırılma noktalarını her gün keşfetmek için takipte kalın 👉 @zamaninbugunu”*

---

### FAZ 3: İçerik Seçim ve Skorlama Algoritması (Algorithm Tuning)
*Amaç: 13 izlenmede kalan yabancı olayları eleyip, 1.800+ izlenen yerli yakın tarihi garantilemek.*

1. **1919 – 1999 Türk Siyasi Tarihi Bonusu:**
   * `content_service.py` içinde puan **+40'tan +60'a** çıkarıldı.
   * Atatürk dönemi, darbeler (1960, 1971, 1980, 1997), Menderes, Demirel, Ecevit, Özal dönemi olayları en yüksek önceliği alır.
2. **Yabancı / Küresel Tarih Cezası:**
   * Türkiye ile doğrudan bağı olmayan küresel olaylara uygulanan negatif puan **-15'ten -60'a** düşürüldü. Böylece Nazi Almanyası, Malta bağımsızlığı gibi konular elendi.
3. **Görsel / Portre Önceliği:**
   * Wikipedia'da portresi veya tarihi fotoğrafı bulunan olaylara (+25 puan) öncelik verilerek akışta durdurma gücü (stop-rate) maksimize edildi.

---

### FAZ 4: Zamanlama ve Dağıtım Matrisi (Prime-Time Kuşağı)
*Amaç: En aktif saat olan 21:00 – 00:00 aralığını en güçlü içerikle vurmak.*

* **Mevcut Cron:** `7 6,11,17,19 * * *`
  * 09:07 TSİ (Sabah Açılışı): Kültür / Bilim / Osmanlı tarihi.
  * 14:07 TSİ (Öğle Molası): Milli Mücadele / Askeri tarih.
  * 20:07 TSİ (Akşam Girişi): Önemli Türkiye gündemi / Olaylar.
  * **22:07 TSİ (Prime-Time Gece Zirvesi - 3.700 İzleyici Kuşağı):** Günün en sansasyonel, 1919-1999 yakın siyasi tarih / darbe konusu.

---

### FAZ 5: Otomatik Metrik Takibi ve Organik Geri Bildirim Döngüsü
*Amaç: Botun her çalışmasında canlı verileri toplayıp raporlamak.*

1. **GitHub Actions Otomasyonu:**
   * `.github/workflows/schedule.yml` içine `Sync Analytics Metrics` eklendi.
   * Her paylaşım döngüsünde Meta Graph API üzerinden `views, likes, replies, reposts` çekilip veritabanına işleniyor.
2. **Gerçek Organik Yorum Ayrıştırması:**
   * Formül: `Organik Yanıt = max(0, Toplam Yanıt - 3)`
   * Kendi zincir yanıtlarımız elenerek gerçek kullanıcı katılımı net olarak ölçülüyor.
3. **Sürekli İyileştirme:**
   * Haftalık olarak `python3 src/analytics.py` çıktısı incelenerek ortalama izlenmesi 1.000'in altında kalan konuların katsayıları düşürülür, 2.000'i aşan konuların katsayıları artırılır.

---

## 3. Başarı Kriterleri (Hedef KPI'lar - 30 Gün)

| Metrik | Başlangıç (1 Ekim 2026) | 30 Günlük Hedef |
| :--- | :--- | :--- |
| **Takipçi Sayısı** | 38 | **150+** |
| **Profil Ziyareti -> Takip Oranı** | %0 (51'de 0) | **%8 - %12** (Her 50 ziyarette 4-6 takipçi) |
| **Ortalama Gönderi İzlenmesi** | ~400 | **1.500+** |
| **Organik Yorum Sayısı / Gönderi** | 0 | **3 – 8 gerçek kullanıcı yorumu** |
| **Gönderi Tabanı (En Düşük İzlenme)**| 13 (Yabancı olaylar) | **200+** (Tüm yabancı zayıf içerikler elenerek) |
