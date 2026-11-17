# 16 – Haiku Brifi #5: 3. slot (D-04), watchdog uyarısı, AI düşüşü, haftalık rapor scripti

Önce `strategy/15-HAFTALIK-ANALIZ-2026-11-17.md`, `strategy/04-DENEY-PLANI.md` (D-04 kuralı) ve `strategy/14-UYGULAMA-NOTU-BRIF-04.md` dosyalarını oku. Tek dal `main`; her görev ayrı commit; push'tan önce `git pull --rebase origin main`. **Push yasak pencereler (TSİ): 09:10–10:40, 12:00–12:40 (D-04 başladıktan sonra), 20:10–21:40.** `bot_data.db`'ye dokunma. Gizli anahtar/token yazma, loglama, isteme yok. Ücretli model yok.

Bu brifte, aşağıda açıkça belirtilen yerde `schedule.yml` ve yeni bir workflow dosyası değiştirilebilir (önceki brifler "workflow'a dokunma" diyordu; burada izin var, yalnızca belirtilenler).

## Bağlam (kısa)

- 14–16 Kasım'da 5 slot kaçtı: Cloudflare Worker'ın GitHub'a `workflow_dispatch` atmak için kullandığı token'ın süresi dolmuştu; Worker kimse fark etmeden hata alıyordu. Düzeltildi (17 Kasım), ama aynı şey tekrar olabilir.
- Veri (n=53): görüntüleme hit odaklı (medyan 246, ortalama ~1.700); yayın sayısı = bilet sayısı. Akşam medyanı sabahın ~1,8 katı. Insights tepe saatleri: Per 21–00, Cts 21–00, Cum 12–15.
- Slotlar `src/publication_policy.py` içinde (`SLOT_HOURS = {"morning": 9, "evening": 20}`, 2 saatlik pencere, yarı açık `[hh:07, hh+2:07)`). Tetikleyiciler: GitHub native cron (`17 6,7,17,18 * * *`) yedek; ana tetikleyici Cloudflare Worker (repo dışında yönetiliyor olabilir; kaynağı repo'da bul: `docs/task04/` ve çevresi).

## Görevler (her biri ayrı commit)

### T1 – D-04: öğle slotu (Per/Cum/Paz, 12:07–14:07)
- Yeni slot anahtarı `noon`: yalnızca İstanbul'da **Perşembe, Cuma, Pazar**; pencere `[12:07, 14:07)`. Diğer günler yok. Takvim/DB mantığı (publication_slots, missed/published durumları, rezervasyon) mevcut iki slotla aynı çalışmalı; `noon` için `slot_attempts`/metrikler de aynı şemayı kullanmalı. DB şeması değişmesin (yalnız yeni `slot_key` değeri).
- `prompt_version`/deney izlenebilirliği: `post_history.experiment_id = "D-04"` ve `variant = "noon"` yaz (kolonlar zaten var). Sabah/akşam gönderileri aynı günlerde `D-04` / `base` yazsın (karşılaştırma için).
- GitHub native cron'a öğle yedeği ekle: 12:17 TSİ = 09:17 UTC ve 10:17 UTC (`17 6,7,9,10,17,18 * * *`). Diğer cron satırlarını bozma.
- Cloudflare Worker: pencere kontrolü Worker'da da tanımlı olabilir (allowlist). Worker kaynağı repo'daysa gerekli değişikliği yap **ama dağıtma**; repo'da değilse notta tam olarak neyin değişmesi gerektiğini yaz (nominal kontrol saatleri, hangi gün/pencere). Dağıtımı kullanıcı yapar.
- Testler: Per/Cum/Paz'da 3 slot, diğer günlerde 2; yarı açık pencere sınırları; kaçan öğle slotu `missed`; üç gönderi sonrası mevcut kısıtlar (günlük üst sınır var mı bak ve D-04 için uyarla, yoksa dokunma).
- Karar kuralı (04): 2 hafta, medyan ≥ %80 ve diğer slotlar %20'den fazla düşmemeli. Kural koda yazılmaz, sadece T4 raporu hesaplar.

### T2 – Watchdog (yayın çıkmazsa uyarı, sır kullanmadan)
- Yeni workflow `.github/workflows/watchdog.yml`: günde iki kez (TSİ 11:37 ve 22:37 civarı; UTC'ye çevir, GitHub gecikmesine karşı tolerans) çalışsın. Sadece okur: `origin/main`'deki `bot_data.db`'den o günün `publication_slots` satırlarına bakar. Kural: sabah kontrolünde (11:37) o günkü `morning` slotu `published` değilse, akşam kontrolünde (22:37) `evening` slotu `published` değilse (ve Per/Cum/Paz öğle 14:37 benzeri kontrol, isteğe bağlı) **workflow başarısız olsun** (exit 1) ve nedeni (slot durumu, reason) log'a yazsın.
- Mantık: GitHub, başarısız zamanlanmış workflow için hesap sahibine e-posta gönderir; ayrı sır/bot gerekmez. Bu tasarımı notta açıkça yaz ve e-posta bildirimlerinin açık olması gerektiğini belirt (kullanıcı ayarı).
- Hiçbir şey commit etmesin, DB'ye yazmasın, secret kullanmasın. Test: DB fixture ile "published → 0", "missed → 1", "pending ve pencere hâlâ açık → 0".

### T3 – AI düşüşünü kök nedene indir (fallback oranı ~%90)
- Son 20 gönderinin `generation_type` ret nedenlerini tablola (`exception`, `length`, `unsupported_words`, `unsupported_number`, `rate_limited`, `http_error`, `loaded_term`, `truncated`…): kaç gönderide hangi neden, hangi model.
- `exception` gerçekte hangi istisna? Log/kod yolunu bul. Hata ise düzelt (örn. yanıt ayrıştırma, None/boş çıktı, zaman aşımı). 
- `length` (uzunluk) reddi: model çıktısı sınırı neden aşıyor? Prompt'a uzunluk hedefi ekle veya cümle sınırında güvenli kısaltma uygula (yeni bilgi eklemeden); ikisinden hangisinin uygun olduğunu notta gerekçelendir, uygula.
- `unsupported_words` (kök koruması): reddedilen sözcükleri (artık loglanıyor) topla; sistematik masum sözcükler (çekimli tarih/unvan sözcükleri vb.) varsa izinli listeye ekle ya da eşiği ayarla; **doğruluk korumasını gevşetme riskini notta ölç** (ör. önceki 10 çıktıyla çevrimdışı karşılaştır).
- Hedef: fallback oranı ölçülebilir azalsın (çevrimdışı örneklerle hedef ≥ %50 AI). Gerçek API çağrısı gerekmez; gerekirse DRY_RUN + Gemini-only küçük kontrol (≤ 6 olay, anahtar yazdırma yok).

### T4 – Haftalık rapor scripti (salt okunur)
- `scripts/weekly_report.py` (yoksa oluştur): `bot_data.db`'yi **salt okunur** açıp son N günü (varsayılan 7) şu çıktılarla yazdırsın: gönderi başına (id, tarih/slot, yıl, konu, generation_type, 24h/72h/7d görüntüleme, beğeni, **gerçek yorum = `verified_external_replies`**, repost), medyan/ortalama/p90; dilimler: konu, dönem (<1900, 1900–1999, 2000+), üretim türü, slot (`morning/evening/noon`); D-04 başladıktan sonra kural hesabı (öğle medyanı / aynı gün sabah-akşam medyanı, %80 ve −%20 kontrolü, örnek sayısı < 4 ise "belirsiz"). Çıktı düz metin tablo; `strategy/15` ile uyumlu sayılar.
- Test: küçük sentetik DB.

## Kabul kriterleri
1. `pytest -q` yeşil; yeni testler T1, T2, T4 için.
2. T3: ret nedeni tablosu + kök neden + düzeltme + çevrimdışı karşılaştırma notta.
3. T1: Worker tarafında değişmesi gerekenler (repo'daysa diff, değilse tarif) notta; dağıtma.
4. Uygulama notu: `strategy/17-UYGULAMA-NOTU-BRIF-05.md`.
5. Push yasak pencerelerin dışında; ben kontrol ederim. **Öğle slotu ilk kez Cuma 20 Kasım 12:07'de çalışacak;** o güne kadar push'lar bitmiş olsun (en geç 19 Kasım).

## Yapma
- Gönderi içeriği/hook prompt'u (yalnız T3'te uzunluk için gereken), görsel mantığı, konu puanları, DB şeması, yeni model/bağımlılık.
- Cloudflare dağıtımı, secret değişikliği.
