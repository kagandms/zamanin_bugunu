# 06 – Prompt v2 Taslağı (`event-rewrite-v5`)

Durum: **TASLAK, onay bekliyor.** Kod yazılmadı. Bu belge onaylanınca Haiku'ya brif olarak verilir.

## Karar özeti (kullanıcı onaylı)

- Serbestlik: **Seviye 1**. Model yeni bilgi **eklemez**; verilen olay cümlesini ve kaynak özetini **yorumlayıp ilgi çekici hale getirir** (çerçeveleme, sıra, ritim, vurgu, soru).
- Tek cümlelik ölü, soğuk başlıklar kabul edilmez.
- Ücretli model yok; ücretsiz kaskad.
- Tarafsız; kışkırtıcı değil, merak uyandırıcı.
- Başlık metni sabit: `Tarihte Bugün (G.A.YYYY)`; emoji içeriğe göre.
- `#tarih` her gönderide; içeriğe özgü anahtar kelimeler metinde doğal geçer (etiket değil).

## "Yorumlamak" ne demek, ne demek değil

| İzinli (yorum) | Yasak (ekleme) |
|---|---|
| Aynı bilgiyi daha çarpıcı sırayla yazmak ("Oy birliğiyle" → "oylamada karşı oy çıkmadı") | Kaynakta olmayan sayı, tarih, isim, yer, alıntı |
| Kaynaktaki karşıtlığı veya şaşırtıcı yanı öne çıkarmak | Neden, niyet, duygu, sonuç uydurmak ("korkmuştu", "bu yüzden") |
| Retorik giriş ve açık uçlu soru | "İlk kez", "en büyük", "tek" gibi kaynakta yazmayan üstünlük iddiası |
| Kaynaktaki bilgiyi güncel okuyucuya bağlamak, **iddia katmadan** ("Bugün aynı caddeden geçenler…" hayır; "O gün …" evet) | Günümüzle bağ kurarken yeni olgu söylemek |
| Sıfatlar: yalnızca kaynaktaki olguyu taşıyan, nötr olanlar | Değer yargısı: "vahim", "kahraman", "hain", "korkunç", "utanç verici" |

Ölçüt: Çıktıdaki **her olgusal cümle** kaynak metinde bir karşılığa sahip olmalı. Kalan her şey çerçeve, ritim veya soru olmalı.

## Çıktı biçimi

Model **yalnızca gövdeyi** üretir. Başlığı kod yazar (mevcut deterministik başlık davranışı korunur).

```
EMOJI: 🕊️
---
[Bölüm 1: hook + olay]  #tarih
---
[Bölüm 2: kaynak zenginse yorumlu bağlam; değilse bu bölüm yok]
---
[Kapanış sorusu]
GORSEL_PROMPT: [yalnızca Vikipedi görseli yoksa; kaynakta olmayan öğe yok]
```

- Bölüm sayısı **uyarlanır**: kaynak özeti zayıfsa 2 bölüm (hook+olay, soru), zenginse 3 bölüm.
- Her bölüm Threads sınırının altında; hedef: bölüm 1 ≈ 180-320 karakter, bölüm 2 ≈ 150-300, soru ≈ 60-140.
- Takip çağrısı (footer) modelin işi değildir; kod ekler (mevcut davranış).
- Emoji: yalnızca onaylı küme:
  🕊️ varsayılan · ⚔️ savaş/muharebe · 🏛️ siyaset/devlet/antlaşma · 🔬 bilim/keşif · 🎭 kültür/sanat · 🌍 doğa/afet
  Trajedilerde (afet, katliam, terör) ⚔️ ve neşeli emoji kullanılmaz; 🕊️ veya 🌍.
  Kod, kümede olmayan emojiyi 🕊️'ye çevirir.

## Sistem prompt'u (taslak metin)

```
Sen Türkçe tarih içeriği yazan bir editörsün. Okuyucu: Türkiye'de tarihe meraklı, 25-55 yaş arası yetişkinler.

GÖREVİN
Kullanıcı mesajındaki "Kaynak olay" ve "Kaynak özeti"ni, aynı bilgiyi koruyarak, akışta okuyucuyu durduracak
ilgi çekici bir metne dönüştürmek. YENİ BİLGİ EKLEMEZSİN; yalnızca verilen bilgiyi yorumlayıp çerçevelersin.

KESİN KURALLAR
1. Yalnızca kaynak olay ve kaynak özetindeki olgulara dayan. Kaynakta olmayan kişi, yer, sayı, tarih,
   alıntı, neden, niyet, duygu, sonuç veya "ilk/en/tek" gibi üstünlük iddiası yazma.
2. Tarafsızsın. Değer yargısı ve duygusal sıfat kullanma (vahim, kahraman, hain, korkunç, utanç vb.).
   Birden fazla taraf varsa "kimine göre … kimine göre …" gibi dengeli yaz; yalnızca kaynakta varsa.
3. Başlık yazma, tarih başlığı ekleme, takip çağrısı yazma. Bunları sistem ekler.
4. HTML, markdown, madde işareti, açıklama, düşünce notu yazma. Yalnızca istenen biçimi ver.

NASIL İLGİ ÇEKİCİ YAPARSIN
- Bölüm 1'in ilk cümlesi okuyucuyu durdurmalı: kaynaktaki en şaşırtıcı, en çarpıcı veya en insani olguyla aç.
  "X tarihinde Y oldu" gibi ansiklopedi girişi YASAK. 1-2 cümle.
- Ritim: kısa cümleler, bir uzun cümle. Gereksiz süs yok. Belgesel anlatıcısı sakinliği.
- Kaynak zengin ise ikinci bölümde aynı bilgileri bağlamla ilişkilendir; zayıfsa ikinci bölüm üretme.
- Kapanış: tek, açık uçlu, yargısız bir soru. Taraf seçtiren soru yazma ("doğru muydu yanlış mıydı" gibi).
  Soru, olayın kendi somut ayrıntısına bağlı, kısa ve doğal konuşma dilinde olmalı; kalıp/şablon hissi vermemeli.
  "Ailenizde … oldu mu?" gibi genel aile-anı kalıpları YASAK (yapay duruyor; kullanıcı kararı).
  Tercih edilen türler: (a) bilgi yoklaması: "Bunu biliyor muydunuz?" / "Bu olayı daha önce duymuş muydunuz?",
  (b) somut merak sorusu: olayın içindeki ayrıntıya dair ("Sizce o gün … nasıl karşılandı?" yalnızca kaynak uygunsa),
  (c) açık uçlu okuma: "Bu olayı bugün nasıl okuyorsunuz?". Her gönderide aynı soruyu kullanma.
  "Beğenin, takip edin, yorum yapın" gibi doğrudan istek yazma.
- Konuya uygun TEK emoji seç (aşağıdaki listeden) ve EMOJI: satırına yaz.

ÇIKTI BİÇİMİ (tam olarak)
EMOJI: <🕊️|⚔️|🏛️|🔬|🎭|🌍>
---
<bölüm 1; sonuna " #tarih" ekle>
---
<bölüm 2 (yalnızca kaynak özeti yeterliyse)>
---
<kapanış sorusu>
GORSEL_PROMPT: <yalnızca istenirse; kaynakta desteklenen ayrıntılarla, İngilizce>
```

Kullanıcı mesajı şablonu:

```
Kaynak olay: {olay metni} ({yıl})
Kaynak özeti: {bağlantılı sayfa özeti, ilk ~800 karakter | "Sağlanmadı."}
Kaynak zengin mi: {evet|hayır}   # karakter sayısı eşiğine göre kod belirler
```

## İki örnek (model davranışı için; few-shot olarak eklenebilir)

**Örnek 1 – ince kaynak (7 Kas 1953, gerçek olay metni)**
Kaynak olay: "İstanbul Zeyrek Camii'nde Bizans dönemi'nden kalma mozaikler bulundu." / Kaynak özeti: Sağlanmadı.

İyi çıktı:
```
EMOJI: 🏛️
---
İstanbul'daki Zeyrek Camii'nde Bizans döneminden kalma mozaikler bulundu. Bir cami, başka bir çağın izini de taşıyormuş. #tarih
---
Sizce şehirlerimiz, içlerinde başka hangi dönemlerin izlerini taşıyor?
```
Neden iyi: olgu aynı (Zeyrek, Bizans, mozaik); ekleme yok; soru yargısız.
Kötü çıktı (yasak): "…1000 yıldır duvarların altında gizli kalan mozaikler…" ("1000 yıl", "gizli kaldı" kaynakta yok).

**Örnek 2 – ince kaynak (29 Ekim 1923)**
Kaynak olay: "Türkiye Cumhuriyeti kuruldu ve TBMM'deki oylamada Mustafa Kemal Atatürk oy birliğiyle ilk cumhurbaşkanı seçildi."

İyi çıktı:
```
EMOJI: 🏛️
---
TBMM'deki oylamada karşı oy çıkmadı: Mustafa Kemal Atatürk, oy birliğiyle Türkiye Cumhuriyeti'nin ilk cumhurbaşkanı seçildi. #tarih
---
Bu ayrıntıyı daha önce duymuş muydunuz?
```
Neden iyi: "oy birliği" → "oylamada karşı oy çıkmadı" yorum, yeni olgu değil. Soru kısa, doğal, evet/hayır ile bile cevaplanabilir (yanıt eşiğini düşürür).
Not: "oylamada karşı oy çıkmadı" ifadesinin "oy birliği"ne eşdeğerliği kabul edilebilir; "çekimser oy yoktu" gibi **ek** iddia olsaydı yasak olurdu.

## Otomatik doğrulama (Seviye 1 koruması, Haiku'ya brif)

Üretilen metin ayrıştırıldıktan sonra, yayından önce:

1. **Sayı/yıl kontrolü:** Çıktıdaki her yıl ve sayı (rakam ve yazıyla yaygın sayılar) kaynak olay + kaynak özeti içinde geçmeli. Geçmiyorsa reddet.
2. **Özel ad kontrolü:** Büyük harfle başlayan, cümle başı olmayan her sözcük (kişi/yer) kaynakta geçmeli (ek/çekim farkları normalize edilir, mevcut `normalize_fact_text` kullanılabilir).
3. **Yasak kelime listesi:** değer yargısı sıfatları (bkz. kurallar), "ilk kez/en büyük/tek" kaynak dışı üstünlükler, "doğru muydu/yanlış mıydı" kalıpları.
4. **Biçim:** `EMOJI:` satırı, `---` ayırıcılar, kapanışın soru işareti ile bitmesi, bölüm uzunlukları.
5. **Dil:** mevcut Türkçe kontrolleri ve sızıntı korumaları korunur.
6. Reddedilirse sonraki ücretsiz modele; hepsi başarısızsa mevcut kaynak-fallback'e (davranış kaybı yok).
7. `prompt_version` = `event-rewrite-v5`; ret nedenleri `last_validation_reason` ile kaydedilir (deney analizi için).

Mevcut elle "fact profile" şartı kalkar; elle profili olan olaylar (Kars, Kosova) eskisi gibi çalışabilir.

## Zengin kaynak için kod gereksinimi (Haiku brifi)

- Bağlantılı Vikipedi sayfasının özetini (ilk ~800 karakter) `Kaynak özeti` olarak ver (eski kodda vardı: `extract[:800]`).
- Olay seçiminde özet uzunluğu çok kısa olanlara hafif ceza ver (olayı elemeden; puanlama düzeyinde).
- Kaynak zengin mi eşiği: özet ≥ 200 karakter (başlangıç değeri; veriyle ayarlanır).

## Kabul testi (Haiku bitirince)

Geçmiş 20 olay (DB'den, farklı dönemler/konular) çalıştırılır; her çıktı için kontrol listesi:
- [ ] Her olgusal cümle kaynakta var.
- [ ] İlk cümle ansiklopedik değil.
- [ ] Değer yargısı yok; soru tarafsız.
- [ ] Emoji kümeden ve tona uygun.
- [ ] Uzunluk sınırları, `#tarih` var.
- [ ] 20'den en az 15'i ilk veya ikinci modelde geçti (kalan fallback; oran kaydedilir).
İnsan gözü (kullanıcı) 10 çıktıyı okuyup tonu onaylar, sonra üretim açılır.

## Açık noktalar

- Bölüm sayısı uyarlanması D-03 (zincir deneyi) ile çakışır; ilk aşamada uyarlanır 2/3 bölüm kalsın, D-03'te ayrıca ölçeriz.
- Soru türü çeşitliliği: ayrı bir soru havuzu (kod tarafında) mı, modelin seçimi mi? Öneri: model seçsin; tekrarı `published_text` geçmişinden yasaklayarak kod denetlesin (sonraki sürüm).
- Hafta sonu özel serisi (Q-09) bu prompt'a dahil değil; ayrı bir prompt şablonu olacak.
