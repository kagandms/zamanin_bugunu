# 18 – Haftalık analiz (16–22 Kasım 2026; 23 Kasım'da yazıldı)

Kaynak: `scripts/weekly_report.py` (DB `metric_snapshots`), slot/yayın tabloları, GitHub Actions koşuları.

## Güvenilirlik

- 17–22 Kasım: 12/12 sabah-akşam slotu `published`. Cloudflare dispatch (workflow_dispatch) :07/:27/:47'de düzgün çalışıyor. Watchdog workflow çalışıyor.
- **D-04 öğle slotu hiç çalışmadı:** 19, 20, 22 Kasım `noon = missed (window_closed_without_reservation)`. Neden: Worker'ın öğle penceresi dağıtılmadı (22 Kasım'da 09:07/09:27/09:47 UTC dispatch koşusu yok; yalnızca 06–07 ve 17–18 UTC). Native cron yedeği pencereye yetişmedi. Üç bilet kaybedildi. Çözüm: Worker dağıtımı (kullanıcı).
- 23 Kasım sabahı: Threads yayını `partial`: ana parça yayınlandı, 2. parça `publish_rejected` (kod 24, subcode 4279009, "The requested resource does not exist"). Telegram tam. Tarihçede 2 partial var. Muhtemel neden: ana gönderi henüz hazır değilken yanıt zincirinin kurulması (bekleme/yeniden deneme eksik).

## Erişim (n = 12 gönderi; 72h/7d yoksa 24h)

- Medyan 363 (7/12 ölçülü), ortalama 1.238, P90 2.842. Hit'ler: 283 (1922 SIYASET, 3.205), 287 (1975 GENEL, 2.600), 288 (1994 GENEL, 2.261).
- Slot (bu hafta): sabah medyan 1.370, akşam 363 → önceki haftanın tersi; **slot farkı gürültü.**
- Konu/dönem: örnek küçük, anlamlı örüntü yok.
- D-04 raporu: 0 öğle gönderisi → "belirsiz".

## AI mi, fallback mi? (id ≥ 200, n = 65, son görülen snapshot)

| Tür | n | Medyan | Ortalama | P75 |
|---|---|---|---|---|
| ai_source_bound | 16 | 148 | 706 | 838 |
| source_fallback (yapılandırılmış) | 49 | 280 | 1.691 | 1.161 |

Seçim API durumuna bağlı olduğu için yarı-rastgele, ama kuyruklar ağır ve n küçük: **AI yazımının erişimi artırdığına dair kanıt yok;** fallback en az eşit görünüyor. Sonuç: AI çalışmasının değeri erişim değil **tarafsızlık/biçim kalitesi ve markalaşma**; erişim için AI kalitesine daha fazla yatırım yapılmaz. Karar: AI'yı kapatmıyoruz (yüklü dil denetimi ve soru uyumu AI yolunda daha iyi), ama hook deneyi (D-02) kanıtlanana kadar "AI erişimi artırır" iddiası yok.

## Kararlar

- Önce **Worker dağıtımı** (öğle penceresi) → D-04 ilk gerçek öğle gönderisi (Per/Cum/Paz).
- Brif #6: Threads zincirinde 2. parça yeniden deneme (code 24/4279009); rapor scripti üretim türünü ailelere (AI/fallback) gruplasın.
- Hâlâ hit odaklı dağılım: bilet sayısı artıkça erişim artar; D-04 yürürlüğe girmeden sonuç yok.
