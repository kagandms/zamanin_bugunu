# 04 – Deney Planı ve Sürekli İyileştirme Döngüsü

## Haftalık döngü

1. **Pazartesi:** Önceki haftanın verisini topla (DB raporu + PDF'ten profil ziyareti, takipçi).
2. Her gönderi için 24h/72h değerlerine bak; deney koluna göre **medyan** hesapla.
3. Karar kuralını uygula (aşağıda); sonucu `05-KARAR-GUNLUGU.md`'ye yaz.
4. Sonraki hafta için tek yeni deney seç (eskisi bitmeden yenisi başlamasın).
5. Prompt/kod değişikliğini `prompt_version` değerini değiştirerek yap; böylece gönderi hangi sürümle üretildi bilinir.

## Karar kuralları (genel)

- Bir deney kolunda en az ~10 gönderi olmadan sonuç ilan edilmez (uç durum: açık bir bozulma varsa erken durdurulur).
- Kollar günlere/slotlara dönüşümlü dağıtılır (saat ve gün etkisini dengelemek için).
- Ana metrik: 24h **medyan** görüntüleme. Yardımcı: etkileşim oranı, yorum sayısı. Marka metriği: takipçi dönüşümü (haftalık).
- Bir kol, ana metrikte en az %20 daha iyi ve etkileşim oranı kötüleşmediyse kazanır; aksi halde mevcut kalır.
- Viral outlier (> 10× medyan) ayrı not edilir, kararda dışlanır.

## Deney sırası (öneri)

| # | Hipotez | Kollar | Süre |
|---|---|---|---|
| D-01 | Yargılayıcı kapanış sorusu yerine tarafsız soru (bilgi yoklaması / somut merak / açık uçlu okuma) daha çok yorum üretir | mevcut ↔ tarafsız soru | ~2 hafta |
| D-02 | Şaşırtıcı detayla açılan hook daha çok durdurur | düz anlatım ↔ şaşırtıcı detay | ~2 hafta |
| D-03 | Zincirin 2./3./footer parçaları çoğu kişiye ulaşmıyor; footer'ı daha erkene almak takibi artırır | 3+1 ↔ 2+CTA ↔ tek parça | 2-3 hafta |
| D-04 | Öğle slotu (Per/Paz 12:07) ek değer katar ve diğerlerini bozmaz | 2/gün ↔ 3/gün (yalnız Per/Paz) | 2 hafta |
| D-05 | Görsel çerçeve/tutarlılık hatırlanırlığı artırır | mevcut görsel ↔ marka çerçevesi | 2-3 hafta |
| D-06 | Etiket kullanımı etkisiz/zararlı | iki etiket ↔ tek ↔ etiketsiz | 2 hafta |

## D-04 karar kuralı (öğle slotu)

- Süre: 2 hafta, yalnızca Perşembe ve Pazar (yaklaşık 4 öğle gönderisi + normal 2'li akış).
- 3. slot kalır, eğer: öğle gönderilerinin medyan 24h görüntülemesi aynı günlerdeki sabah/akşam medyanının en az %80'i **ve** sabah/akşam gönderilerinin medyanı deney öncesine göre %20'den fazla düşmediyse.
- Örnek küçük (4 gönderi); belirsizse deney 2 hafta daha uzatılır.

## Ölçüm hijyeni

- Karar ölçülemeyen şeye dayanmaz; metrik boşluğu varsa önce ölçümü düzeltiriz.
- Eksik veri `NULL`, sıfır değil (mevcut analytics politikası).
- Ek ölçüm ihtiyacı: zincir parçası bazlı görüntüleme (mevcut `metric_snapshots` parça bazlı); haftalık özet raporu; konu sınıflandırıcı doğruluğu.

## Konu seçimi (sonraki aşama)

Mevcut puanlamadaki +60 (1919-1999 TR) ve −60 (yabancı) çarpanları az veriye dayanıyor. Yeterli gönderi birikince (≥ 40 ölçümlü gönderi) konu/dönem bazında medyanlara göre yeniden ayarlanacak. Sınıflandırıcıdaki hatalar (ör. Akyar → KULTUR_SANAT) düzeltilecek.
