# 07 – Haiku Brifi #1: AI yazımını yeniden aç (Seviye 1, kaynağa bağlı yorum)

Bu brif Haiku oturumuna **olduğu gibi** verilebilir. Önce `strategy/06-PROMPT-V2-TASLAK.md`, `strategy/03-ICERIK-ILKELERI.md` ve `strategy/05-KARAR-GUNLUGU.md` dosyalarını oku.

## Bağlam (kısa)

- Proje: Threads/Telegram "Tarihte Bugün" botu. Tek dal: `main`. Yeni dal açma, worktree açma. Küçük, ayrı commit'ler at; push'tan önce `git pull --rebase origin main` (bot DB commit'leri atıyor, `bot_data.db`'ye dokunma).
- Sorun: 20 Ekim'den beri 34/34 gönderi AI'sız, ham Vikipedi cümlesi. Sebep: `AIService.rewrite_event_safe` (`src/services/ai_service.py`) `resolve_fact_profile(request)` `None` ise AI'yı hiç çağırmıyor ve `generate_source_fallback` kullanıyor. Elle profili yalnızca Kars 1921 ve II. Murad/Kosova 1448 için var.
- Hedef: AI, verilen kaynak metni **yorumlayıp ilgi çekici** yazsın; **yeni bilgi eklemesin**. Ücretli model **yok**; mevcut ücretsiz model kaskadı (`settings.AI_MODEL` … `LAST_RESORT_MODEL`) kalır.
- Aşırı koruma istemiyoruz ama doğruluk marka için önemli: kaynakta olmayan yıl/sayı/özel ad yayımlanmamalı.

## Değişecek / dokunulacak yerler

- `src/services/ai_service.py`: `_build_system_prompt`, `rewrite_event`, `rewrite_event_safe`, `_parse_ai_response`, `_validate_turkish_content`, `prompt_version`.
- `src/services/content_guard.py`: `resolve_fact_profile` yolu, `validate_event_content`, `EventRewriteRequest`.
- `src/services/source_context.py` ve `src/event_preparation.py`: kaynak özetinin nasıl seçildiği (`select_event_source`, `_rewrite_request`, `get_relevant_source_sentences`), `_rewrite_rejection`, `_used_source_sentences` (bunlar `generation_type` metinlerine bağlı; yeni tipler bunları bozmamalı).
- `src/services/content_service.py`: olay puanlamasına özet uzunluğu cezası.
- Testler: `tests/test_ai_service.py`, `tests/test_source_aware_content.py`, `tests/test_event_source_context.py`, `tests/test_content_quality.py`, `tests/test_event_preparation.py` — bozulanları güncelle, yenilerini ekle.

## Görevler (sırayla; her biri ayrı commit)

### G1 – Elle profil şartını kaldır

- `rewrite_event_safe`: profil yoksa doğrudan fallback'e gitme. Profil varsa mevcut davranış (profil doğrulaması) korunur. Profil yoksa yeni "kaynağa bağlı yorum" yolu çalışır (G2-G4).
- `generation_type` yeni değeri: `ai_source_bound`. Eski `ai_validated` / `ai_language_format_only` davranışı bozulmasın.
- `model_attempt_limit`: profil yoksa da kaskadın ilk 3 modelini dene (şimdi profil varsa 2); süre/timeout makul kalsın.
- Uyarı: `unprofiled_claims_unverified` ret nedeni artık bu yolda kullanılmaz.

### G2 – Yeni prompt (`event-rewrite-v5`)

- Sistem prompt'u ve kullanıcı mesajı şablonu: `strategy/06-PROMPT-V2-TASLAK.md` içindeki metin. Türkçe metinleri değiştirme; sadece Python string'e çevir.
- Çıktı biçimi: `EMOJI:` satırı + `---` ile bölümler + `GORSEL_PROMPT:` (isteğe bağlı). Başlığı (`<emoji> Tarihte Bugün (G.A.YYYY)`) **kod** yazar; emoji onaylı kümede değilse 🕊️.
- Bölüm sayısı: kaynak özeti zayıfsa 2, zenginse 3. Kaynak zengin eşiği: özet ≥ 200 karakter (sabit olarak tanımla, ayarlanabilir).
- `#tarih` ilk bölümün sonunda (modele söylenir; kod eksikse ekler).
- Footer (takip çağrısı) mevcut gibi kodla eklenir; modele yazdırma.
- `prompt_version = "event-rewrite-v5+" + CONTENT_GUARD_VERSION` (guard sürümünü güncelle: ör. `fact-guard-v7`).

### G3 – Zengin kaynak metni

- `Kaynak özeti`: seçilen olayın bağlantılı Vikipedi sayfası `extract`'ının ilk ~800 karakteri (tam cümlede kes). Şu an `get_relevant_source_sentences` çok sıkı süzdüğü için çoğu olay "thin_source" oluyor; bu filtre profilsiz yolda **gevşetilmeli** (tüm özet kullanılabilir; yalnızca açıkça başka olaya ait ve yıl çelişkisi olan cümleler elenir — mevcut yıl-çelişki kontrolleri kalsın).
- Kaynak yoksa: `Sağlanmadı.` yazılır, model yalnızca olay cümlesini yorumlar, 2 bölüm üretir.
- `content_service._calculate_fame_score`: özet < 100 karakter ise hafif ceza (örn. −10); eleme yok.

### G4 – Otomatik doğrulama (Seviye 1 koruması)

Yeni fonksiyon (örn. `validate_source_bound_content(parts, source_text)`), `content_guard.py` içinde:

1. Çıktıdaki her yıl (3-4 haneli) ve sayı kaynak olay + kaynak özeti içinde geçmeli.
2. Cümle başı olmayan büyük harfli sözcükler (kişi/yer) kaynakta geçmeli (`normalize_fact_text` ve mevcut `_matches` benzeri çekim toleransı kullan).
3. Yasak kalıplar: değer yargısı sıfatları (vahim, kahraman, hain, korkunç, utanç, rezalet…), kaynak dışı üstünlükler ("ilk kez", "en büyük", "tek" — kaynak metinde geçiyorsa serbest), "doğru muydu/yanlış mıydı" kalıbı, "Ailenizde" ile başlayan soru, "beğenin/takip edin/yorum yapın" doğrudan istekleri.
4. Biçim: `EMOJI:` satırı, bölüm sayısı 2-3, son bölüm `?` ile biter, bölüm uzunlukları (taslaktaki hedefler; sert sınır `MAX_THREAD_LENGTH - 20`).
5. Reddedilirse sonraki modele; hepsi reddedilirse mevcut `generate_source_fallback`.
6. Ret nedenlerini `last_validation_reason` ile kaydet (virgülle, kısa kodlar: `unsupported_number`, `unsupported_name`, `banned_phrase`, `format`, …).

### G5 – İzlenebilirlik

- `post_history.generation_type` ve `prompt_version` yeni değerlerle yazılsın (mevcut metadata yolu).
- Her çalıştırmada kısa log: hangi model, kaç deneme, ret nedeni.
- (Ek, küçük) Çıktı örneklerini loga yaz (üretim açılınca ilk günlerde incelemek için).

## Kısıtlar

- Ücretli model/yeni bağımlılık ekleme.
- Kaynak metnin dışına çıkan bilgi üretimini **yasaklayan** kuralları gevşetme; sadece elle profil şartını kaldır.
- `bot_data.db` ve GitHub workflow dosyalarını değiştirme (bu brif kapsamında değil).
- Telegram ve Threads yayın yollarına dokunma.
- Gizli anahtarları/ortam değişkenlerini okuma, loga yazma.

## Kabul kriterleri

1. `pytest -q` yeşil (güncellenen/yeni testlerle).
2. Yeni testler:
   - Profilsiz olay + sahte model çıktısı (geçerli) → `ai_source_bound`, başlık kod tarafından doğru, `#tarih` var, footer ayrı.
   - Kaynakta olmayan yıl/sayı/ad içeren çıktı → ret → sonraki model → hepsi başarısızsa fallback.
   - Değer yargısı sıfatı, "Ailenizde…" sorusu, doğrudan "takip edin" isteği → ret.
   - Emoji küme dışı → 🕊️.
   - İnce kaynak → 2 bölüm; zengin kaynak → 3 bölüm kabul.
3. Çevrimdışı kabul testi (gerçek API çağırmadan, sahte yanıtlarla): son 20 olayı `post_history`'den al, kaynak metin yoksa olay cümlesiyle, `source_evidence` varsa özetle istek oluştur, akışın hata vermeden bitip bitmediğini göster.
4. Canlı doğrulama (ücretsiz modellerle, **yayın yok**): `DRY_RUN=true` ile 10 olay üret, çıktıları `strategy/evidence/ilk-10-cikti.md` dosyasına yaz (olay cümlesi, kaynak özeti, üretilen metin, hangi model, geçti/reddedildi ve neden). Bu dosyayı kullanıcı okuyup tonu onaylayacak; **onaydan önce üretimi açma**.
5. Değişiklikleri özetleyen kısa bir not: ne değişti, hangi dosyalar, bilinen riskler.

## Yapma

- Üretime push edip botu canlıda açma. Önce kabul kriterleri 1-4; kullanıcı onayı ayrı adım.
- Bir seferde çok değişiklik; her G ayrı commit.
- Yanıt/yorum botu, yeni platform, yeni slot gibi kapsam dışı işler.
