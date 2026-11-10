# 14 – Uygulama notu: Brif #4 (sıra sayısı, kişi/anma sorusu, AI düşüşleri, tanım cümlesi)

## T1 – "36." sıra sayısı (düzeltildi)
- Neden: `_ABBREVIATION_DOT` yalnızca baş harf, Romen rakamı ve kısaltmaları koruyordu; `36. ve` cümle sonu sayıldı.
- Kural (`source_context._ORDINAL_DOT`): rakam(lar) + `.` + boşluk + **küçük harf** → bölme yok. Büyük harfle devam eden (`1938'de öldü. 10 Kasım…`) bölünür.
- Ek koruma: `content_guard.ends_with_ordinal_stub` — blok `\d+\.\s*(#tarih)?$` ile bitiyorsa model çıktısı `truncated` nedeniyle reddedilir; yapılandırılmış fallback aynı biten özet cümlesini kullanmaz.

## T2 – Kişi ve anma sorusu (düzeltildi)
- `Bu kişiyi daha önce duymuş muydunuz?` ve `Bu isim hakkında ne biliyorsunuz?` bankadan çıktı. Yeni kişi bankası: `Bu kişi hakkında ne biliyordunuz?` + `Bu ismi tanıyor muydunuz?`.
- Metinde `cumhurbaşkanı|başbakan|padişah|halife|kral|imparator|mareşal|başkomutan|kurucu` varsa yalnızca `Bu kişi hakkında ne biliyordunuz?` kalır (`Bu ismi tanıyor muydunuz?` yalnızca lider olmayan kişide).
- Anma kuralı: metinde `öldü|vefat|hayatını kaybet|ulusal yas|anma|ölümü` **ve** lider ya da siyaset/çatışma kökü varsa soru **yok**; yayın tek parça + `#tarih`. Hem yapılandırılmış fallback hem AI yolu (`_assemble_source_bound_parts`) için geçerli.
- Not: `öldü` kelime sınırlı; `öldürüldüğünü` kuralı tetiklemiyor (ilk denemede mevcut bir testi kırmıştı, düzeltildi).

## T3 – AI neden düştü (log kanıtı, anahtarsız)

| Çalışma | Gemini `gemini-3.5-flash` | nemotron (Primary) | gemma-4-31b (Secondary) |
|---|---|---|---|
| 10 Kasım 06:07 UTC (274) | 06:08:00 HTTP 503 → 5 sn sonra yeniden deneme → **yine HTTP 503** ("high demand") | `rejected: unsupported_words` (06:08:11) | 5 kez 5 sn bekleyip `HTTP 429` (≈26 sn, 06:08:37) |
| 10 Kasım 17:07 UTC (275) | 17:08:25 **ReadTimeout** (istek 17:07:59'da başladı = 25 sn zaman aşımı) | `rejected: unsupported_number,unsupported_words` (17:08:34) | 5 kez 5 sn bekleyip `HTTP 429` (≈26 sn, 17:09:01) |

Sonuçlar:
- 503 yeniden denemesi çalıştı ama 5 sn yetmedi (iki 503 art arda). Akşam 503 değil, **25 sn zaman aşımı**.
- Gemma'nın 429'u her iki gün de 5 deneme × 5 sn bekleyerek ~26 sn harcıyor ve sonuç vermiyor.
- `unsupported_words` nemotron'u iki çalışmada da düşürdü. **Reddedilen sözcükler loglanmamıştı**, bu yüzden hangileri olduğu bilinmiyor; model çıktıları da saklanmıyor, geriye dönük çıkarılamaz.
- Yapılan: ret satırına artık kaynakta bulunmayan sayılar ve kökler yazılıyor (`numbers=[…] roots=[…]`, `content_guard.rejection_detail`). Anahtar veya kullanıcı verisi içermez, yalnızca model çıktısındaki sözcükler. Bir sonraki iki düşüşte neden net görülecek.

**Öneriler (kodda değiştirilmedi, karar sizde):**
1. Gemini zaman aşımı 25 sn → 40 sn. Bütçe 90 sn / 3 sağlayıcı = 30 sn pay; payı Gemini lehine (ör. 45 / 25 / 20) bölmek gerekir.
2. Gemma 429'da tekrar denemeyi 5 → 1-2'ye indirmek ~15-20 sn bütçe kazandırır, sonuç değişmez (iki günde de 5 denemenin hiçbiri geçmedi).
3. Kök korumasını gevşetme önerisi için veri yok; önce `roots=[…]` logu toplanmalı (en az 2-3 düşüş). Şimdilik gevşetmiyorum.
4. Gözlem: son 5 gönderiden 273 hariç ikisi (274, 275) fallback. Sebep nemotron'un guard'a takılması + Gemini yanıt vermemesi; Türkiye/anma olayları (yüksek izlenme) aynı anda en kırılgan tür.

## T4 – Tanım cümlesi (düzeltildi)
`structured_fallback.is_definition_sentence`: cümle büyük harfle başlayıp virgülle ayrılan bir baş kısmı içeriyor, baş kısımdaki sözcük olay cümlesinde geçiyor ve cümle `-dır/-dir/-dur/-dür/-tır…` ya da `olarak da bilinir` ile bitiyorsa özet cümlesi olarak seçilmez; sonraki cümle ya da yalnızca olay cümlesi kullanılır.

## Çevrimdışı çıktı (API çağrısı yok)
**Uyarı:** 274 ve 275'in gerçek Vikipedi özetleri elimde yok; kaynak metinler gönderilerde görünen cümlelerden ve brifteki alıntılardan kuruldu. 274'ün ikinci cümlesi (Selamlık töreni…) **gösterim için uydurulmuş örnek**, gerçek kaynakta bulunmayabilir.

274 (VI. Mehmed):
```
🕊️ Tarihte Bugün (10.11.1922)

Osmanlı padişahı VI. Mehmet Vahdettin, son Selamlık törenine katıldı. Selamlık töreni, padişahın cuma namazına çıkışını gösteren bir saray geleneğiydi. #tarih

Bu olayı bugün nasıl okuyorsunuz?
```
Tanım cümlesi ("…36. ve son padişahıdır.") bütün cümle olarak okunuyor ve atlanıyor; ikinci cümle yukarıdaki uydurma örnektir. Kişi-tanıma sorusu yok.

275 (Atatürk):
```
🕊️ Tarihte Bugün (10.11.1938)

Türkiye Cumhuriyeti'nin kurucu cumhurbaşkanı Mustafa Kemal Atatürk, Türkiye saati ile 9.05'te Dolmabahçe Sarayı'nda 57 yaşındayken öldü. Türkiye'de ulusal yas ilan edildi. #tarih
```
Soru yok, tanım cümlesi yok, tek parça.

## Testler
`tests/test_brief04_ordinal_question_definition.py`: 8 test (sıra sayısı bölünmemesi, yıl sonrası bölünme, kesik blok tespiti ve ret, tanım cümlesi atlama, Atatürk'te soru yok, Vahdettin'de kişi-tanıma sorusu yok, kişi bankası). Toplam 314 test geçiyor.

## Hâlâ bilinmeyen
- `unsupported_words`'a takılan gerçek sözcükler (log eklendi, veri bekliyor).
- 503'ün Google tarafında ne kadar sürdüğü; 5 sn yetersiz kalıyor, ama daha uzun bekleme bütçeyi yer.
- Anma kuralı `anma` kelimesine bağlı; "doğum yıl dönümü" gibi anmalarda soru kalır.
- `leader` sözcüğü (`kral`, `kurucu`) bir şirket kurucusu gibi lider olmayan kişilerde de soruyu kısıtlar; zararsız (daha az soru).
