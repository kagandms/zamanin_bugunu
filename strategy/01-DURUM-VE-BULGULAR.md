# 01 – Durum ve Bulgular (7 Kasım 2026 baz çizgisi)

Kaynaklar: Threads Insights PDF (8 Eki – 6 Kas 2026, "Son 30 gün"), `origin/main` üzerindeki `bot_data.db` (7 Kas 2026 checkpoint), kod incelemesi.
Not: Yerel `codex/analytics-foundation` dalı main'in ~729 commit gerisinde. Analiz main'e göre yapıldı.

## Hesap özeti (PDF, 30 gün)

| Gösterge | Değer |
|---|---|
| Görüntüleme | 347.260 (+%677) |
| İzleyici | 175.031 (takipçi 73, takipçi olmayan 174.958) |
| Net takipçi | +25 (+%52) |
| Etkileşim | 468 (~%0,13 / görüntüleme) |
| Ülke | Türkiye %94,3; Almanya %1,0; Azerbaycan %0,9 |
| Şehir | İstanbul %17,4; Ankara %6,1; İzmir %5,8; Bursa %3,1; Antalya %2,1 |
| Yaş | 13-17 %1,2 · 18-24 %14,5 · 25-34 %36,0 · 35-44 %22,5 · 45-54 %13,8 · 55-64 %6,8 · 65+ %5,3 (35+ toplam ≈ %48) |
| Cinsiyet | Erkek %81,3 · Kadın %2,5 · Diğer %16,2 |
| En aktif zamanlar (GMT+3) | Perşembe 12-15 (16 B) · Pazar 12-15 (15 B) · Çarşamba 21-00 (14 B) |

## Veritabanı bulguları

- 10 Ekim'deki tek gönderi (1965 genel seçim, AP 240 milletvekili) **217.714** görüntüleme aldı = 30 günlük toplamın ~%63'ü. Geri kalan ~130 bin (günde ~4,3 bin).
- Gönderi başına tipik görüntüleme 300 – 6.000. Beğeni 2-4. Doğrulanmış organik yorum ≈ 0-1.
- Ekim başında Osmanlı savaş hikâyeleri 4-6 bin aldı; Ekim sonunda en yüksek 7g görüntüleme Kırım Savaşı/Akyar (6.169). "Yakın siyasi tarih her zaman kazanır" varsayımı **kanıtlanmış değil**.
- Konu sınıflandırıcısı (anahtar kelime) gürültülü: Akyar kuşatması `KULTUR_SANAT` etiketlenmiş.
- Slot sonuçları (50 slot): 38 yayımlandı, 8 kaçırıldı, 3 başarısız, 1 bekliyor (~%76).
- Günlük yayın 4'ten 2'ye indirilmiş (09:07 ve 20:07 TSİ penceresi). Öğle zirvesi kullanılmıyor.
- Metrik penceresi ortalamaları (başarılı snapshot): 24h ort. 669, 72h ort. 520, 7g ort. 608 görüntüleme (outlier hariç değerlendirilmeli).

## Kod durumu (özet)

- İçerik: Vikipedi "onthisday" → puanlama (Türkiye bonusu, 1919-1999 +60, yabancı −60, sayfa/görsel/uzunluk) → AI yeniden yazım (OpenRouter ücretsiz model kaskadı, temperature 0.3) → 3 bölüm + Threads footer zinciri.
- Footer her gönderide son zincir parçası: "…takip edin 👉 @zamaninbugunu".
- Kapanış sorusu promptta sabit: yargılayıcı "zorunluluk mu hata mı" kalıbı.
- Hashtag: her gönderide `#tarih #tarihteneoldu`.
- `prompt_version` sütunu var (deney izlemesi için temel).

## Varsayımlar / bilinmeyenler

- 10 Ekim gönderisinin neden patladığı bilinmiyor (konu mu, saat mi, görsel mi, şans mı). Tek örnek.
- Kitle %35+ oranı düşmüş görünüyor (Oct 1: %67,6 → şimdi ≈ %48). Viral dalgayla kitle karışmış olabilir.
- Zincir (2. ve 3. parça + footer) parçalarının gerçekte kaç kişiye gösterildiği/etkileşim aldığı ayrıştırılmadı.
- Hashtag/konu etiketinin etkisi doğrulanmadı.
