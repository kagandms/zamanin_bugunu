# 15 – Haftalık analiz (10–16 Kasım 2026; 17 Kasım'da yazıldı)

Kaynaklar: Threads Insights PDF (10–16 Kas), DB `metric_snapshots` (ana parça, en son 72h/7d snapshot; n = 53 gönderi), 30 günlük profil ekranı.

## Hesap (haftalık)

| | Değer | Not |
|---|---|---|
| Görüntüleme | 15.186 (−%70) | Önceki hafta 30k ve 12k'lık iki viral gönderi (263, 267) vardı; düşüş büyük ölçüde onların çıkması |
| İzleyici | 10.859 (−%66) | |
| Etkileşim | 182 (−%27) | |
| Net takipçi | +3 | takipçi olan izleyici 28 |
| Ülke | TR %92,1; Azerbaycan %3,2 (önceki %0,9); Almanya %1,0 | Karabağ gönderileri Azerbaycan kitlesini çekti |
| Yaş | 35+ ≈ %71 (35-44 %26, 45-54 %21, 55-64 %13, 65+ %11); 25-34 %23 | önceki ay 35+ ≈ %48; kitle yaşlanıyor |
| Cinsiyet | Erkek %81,5 | |
| En aktif | Per 21–00, Cts 21–00, Cum 12–15 | akşam slotu (20:08) tepe saatinden biraz önce |

30 gün: 85.985 görüntüleme, 52.192 izleyici, 542 etkileşim (%0,63), net +12. İlk analiz (347k/175k/468/+25) viral 256k'lık gönderiyle şişikti; onu çıkarınca görüntüleme yatay, etkileşim oranı artmış.

## Gönderi bazlı (DB, n=53, 72h/7d)

- **Genel medyan 246, p90 3.151, max 30.006.** Ortalama ~1.7k: görüntülemenin büyük kısmı birkaç "hit" gönderiden geliyor (263: 30k, 267: 12k, 277: 7,4k, 242: 6,2k, 271: 4,8k).
- **Bu hafta en iyisi:** 277 (11.11.2008, Mustafa Şekip Birgöl, İstiklal Savaşı'nın son gazisi): 7.390 görüntüleme, 158 beğeni (%2,1), 4 repost, 2 paylaşım, 2 gerçek yanıt ("Ruhu şad olsun"). Tek parça, soru ve zincir yok, fallback. Ama profil ziyareti 13, takip 1: **ulaşım iyi, dönüşüm zayıf.**
- **Konuya göre medyan:** SIYASET 210 (n=32), GENEL 183 (7), SAVAS_ASKERI 155 (11), KULTUR_SANAT 3.245 (n=2). İlk izlenimim "savaş konuları iyi" idi; **veriyle doğrulanmadı.**
- **Döneme göre medyan:** 2000+ → 1.735 (n=5); 1900 öncesi → 734 (n=6); 1900–1999 → 158 (n=42). Ana yığın (1900–1999) ortalama gönderi; sapmalar az sayıda ama medyanları 5–10× yüksek. Seçim puanındaki +60 (1919–1999 TR) kararı zayıfça destekleniyor, henüz değiştirmeyecek kadar küçük örnek.
- **Üretim türü:** ai_source_bound medyan 1.735 (n=5), source_fallback 183 (n=45). Fark büyük ama AI'lı beşin hepsi 8 Kasım sonrası ve 2000+ ağırlıklı (karıştırıcı); sonuç ilan edilmez.
- **Slot:** akşam medyanı 284 (n=28), sabah 155 (n=25). Akşam ~1,8× iyi; Insights'taki 21–00 tepesi ile uyumlu.
- **Yeni format (7 Kas sonrası) medyanı 168** vs öncesi 280: henüz iyileşme yok; örnek 14 ve arada 5 slot kaçtı.
- Gerçek yorum: `verified_external_replies` kolonu var (`replies` kendi zincirimizi de sayar). Haftalık raporda bunu kullan.

## Yorum

1. Erişim **hit odaklı**: gönderilerin ~%10'u görüntülemenin çoğunu getiriyor. Hangi gönderinin hit olacağını konudan/saatten kestiremiyoruz. Bu durumda **bilet sayısı** (yayın sayısı) beklenen toplam erişimi doğrudan artırır; kaçan slot doğrudan kayıp.
2. **Güvenilirlik büyük kayıp kaynağı:** 14–16 Kasım'da 5 slot kaçtı (Cloudflare dispatch token süresi doldu; 17 Kasım'da düzeltildi). Beklenen kayıp yaklaşık 5 × ~1.7k ortalama.
3. **Dönüşüm sızıntısı:** hit gönderide bile 6,3k izleyiciden 13 profil ziyareti, 1 takip. Marka/profil ve sabitlenmiş gönderi, bio, tutarlı seri adı daha önemli; gönderi başı takipçi atfı ölçülemiyor (hesap düzeyi).
4. Kitle yaşlı, erkek ağırlıklı, Türkiye; Cuma öğle ve Per/Cts gece tepe saatleri.

## Kararlar

- **Konu ağırlığı ve dönem puanı değiştirilmez** (örnek küçük). Ölçüme devam; ≥40 gönderilik kovalara ulaşılınca yeniden bakılır. "Savaş konuları iyi" hipotezi çekildi.
- **Sıradaki deney: D-04 (3. slot).** Gerekçe: hit odaklı dağılımda bilet sayısı değer taşıyor; Cuma 12–15 ve Per/Paz öğle tepesi ek veri. Kural 04'teki gibi (Per/Cum/Paz, 2 hafta, medyan ≥ %80). Kod gerekir → brif #5.
- **Akşam slotunu 21:07'ye çekme** ikinci aday (Insights tepesi 21–00, akşam medyanı zaten daha yüksek); D-04 sonrası.
- **Uyarı:** 12+ saat gönderi çıkmazsa bildirim (brif #5). Token bitişi için takvim hatırlatması (kullanıcı).
- AI düşüşü (fallback oranı ~%90): ayrı iş, brif #5'e dahil (kök koruması ve uzunluk reddi nedenleri).
- Elle: hit gönderinin yorumlarına cevap (24 saat içinde), sabit gönderi ve bio'yu gözden geçir.
