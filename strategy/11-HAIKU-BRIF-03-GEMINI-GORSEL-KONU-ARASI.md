# 11 – Haiku Brifi #3: Gemini düşüşü, çatışma görseli, konu soğuması

Önce `strategy/03-ICERIK-ILKELERI.md` ve `strategy/10-UYGULAMA-NOTU-BRIF-02.md` dosyalarını oku. Tek dal `main`; küçük ayrı commit'ler; push'tan önce `git pull --rebase origin main`. **Push yasak pencereler (TSİ): 09:10–10:40 ve 20:10–21:40.** `bot_data.db` ve workflow'lara dokunma. Anahtarları loga/dosyaya yazma. Ücretli model yok.

## Canlı gözlem (9 Kasım 09:08 gönderisi, DB id 272)

Olay: Dağlık Karabağ ateşkesi (2020). Metin tarafsız ve yüklü terimsiz (brif #2 işledi). Ama:

- **G1 Yazar Gemini değil:** `ai_model = nvidia/nemotron-3-ultra-550b-a55b:free`. Kaskad Gemini → nemotron → gemma. Gemini neden devre dışı kaldı bilmiyoruz.
- **G2 Görsel tek tarafın bayrağı:** `selected_image_url` = Azerbaycan bayrağı (Wikipedia thumbnail). Metin iki tarafı anlatıyor; görsel taraf tutuyor.
- **G3 Aynı konu üst üste:** 8 Kasım Şuşa, 9 Kasım ateşkes; ikisi de Karabağ 2020.
- **G4 Hook hâlâ ansiklopedik; 2. parça kaynağa çok yakın** (düşük öncelik, gözlem).

## Görevler (her biri ayrı commit)

### T1 – Gemini düşüşünü bul (önce araştır, sonra düzelt)
- Elinde 9 Kasım 06:08 UTC (09:08 TSİ) çalışmasının GitHub Actions logu yoksa erişimin olduğu yollardan (gh CLI) "Run Bot" adımının logunu oku: `gh run list` / `gh run view --log` (anahtar değerleri loga çıkmıyor, çıksa bile kopyalama).
- Gemini isteği hangi hata ile düştü? (429 kota / 503 / boş yanıt / zaman aşımı / guard reddi / süre bütçesi 90 sn). Kaskadın o çalışmadaki sırasını ve her modelin sonucunu kısa bir tabloya yaz.
- Nedeni koda göre düzelt: ör. kota ise günlük istek sayısını azalt (tek istek, tekrar deneme sınırı), 503 ise bir kez geri çekilip tekrar dene, guard reddi ise ret nedenini logla. Ücretli çözüm yok.
- Çıktı: `strategy/12-UYGULAMA-NOTU-BRIF-03.md` içinde neden + düzeltme + hâlâ bilinmeyen.

### T2 – Çatışma/siyaset görseli
- Bu konu/olay türlerinde (`SAVAS_ASKERI`, `SIYASET`; ayrıca ulusal simge içeren görseller) Wikipedia thumbnail'i olarak **bayrak, devlet başkanı/lider portresi ve propaganda afişi** kullanılmasın. Ayırt etme: dosya adı/başlık anahtarları (`Flag_of`, `Coat_of_arms`, `Emblem`, `Portrait`, `Poster`, `Propaganda`), ve kaynak sayfanın ana görseli bunlardan biriyse.
- Alternatif sırası: haritalar (`Map`, `map`), fotoğraf; hiçbiri yoksa görselsiz gönderi (mevcut yayın yolu görselsizliği destekliyorsa) — desteklemiyorsa nötr bir yedek görsel kullanıp bunu nota yaz, yeni görsel/model **üretme**.
- Test: bayrak URL'si → reddedilir; harita URL'si → kabul.

### T3 – Konu soğuması
- Aynı Wikipedia konu sayfası, aynı savaş/olay kümesi (ör. başlıkta ortak anahtar sözcük, aynı `source_url` kökü) veya aynı `topic_category` + aynı yıl için **son 7 günde yayın varsa** o aday puan cezası alsın (ör. -80, elenmesin; başka aday yoksa yine seçilebilsin).
- Hangi anahtarla "aynı konu" sayıldığını sade tut (örn. kaynak sayfa başlığının ilk iki anlamlı sözcüğü + yıl ±1) ve nota yaz. Aşırı karmaşıklık yok.
- Test: dün yayınlanmış "İkinci Dağlık Karabağ Savaşı" varsa bugün aynı sayfa/yıl adayı ceza alır.

### T4 – Hook (yalnızca gözlem notu, kod değişikliği yok)
- Son iki çıktıda 1. parçanın olay cümlesini ne kadar tekrar ettiğini ölç: olay cümlesiyle sözcük örtüşmesi (%). Sonucu notta ver; prompt değiştirme (karar bende).

## Kabul kriterleri
1. `pytest -q` yeşil.
2. Yeni testler T2 ve T3 için.
3. T1 için: hatanın nedeni ve kanıtı (log satırı, anahtarsız) notta.
4. Kısa uygulama notu: `strategy/12-UYGULAMA-NOTU-BRIF-03.md`. Push'u yasak pencereler dışında yap, ben haber alınca kontrol ederim.

## Yapma
- Slot/sıklık, workflow, DB, yeni model/bağımlılık, görsel üretimi.
- Hook prompt'unu bu brifte değiştirme.
