# 17 – Uygulama notu: Brif #5 (öğle slotu, watchdog, AI düşüşü, haftalık rapor)

Uygulama: agy (Gemini Hydrogen) agent'ları, her biri kendi worktree ve görev dalında; orkestrasyon ve testler Claude tarafında. Testler: `pytest -q` 355 geçti; Worker testleri (`node --test tests/*.test.mjs`, `tsc` derlemesiyle) 53 geçti.

## T1 – D-04 öğle slotu
- Slot anahtarı `noon`: yalnızca İstanbul Per/Cum/Paz (ISO 4, 5, 7), pencere `[12:07, 14:07)`. Diğer günler iki slot kalıyor (`src/publication_policy.py`, `build_windows`).
- Günlük üst sınır: öğle günlerinde 3 (`max_daily_events`), diğerlerinde 2. `publication_slots.py` bu sınırı kullanıyor.
- Deney alanları: öğle günlerinde gönderi `experiment_id = "D-04"`, öğle slotu `variant = "noon"`, sabah/akşam `variant = "base"`. Yazım tek yerde: `SlotStore` bind (`src/data/publication_slots.py`).
- Native cron (`schedule.yml`): `17 6,7,9,10,17,18 * * *` (09:17 ve 10:17 UTC = 12:17 ve 13:17 TSİ). Diğer satırlar aynı.
- Worker (`workers/workflow-trigger/src/policy.ts`): `findSlot` öğle anahtarını Per/Cum/Paz'da 727–847 dakika aralığında döndürüyor; `planDispatch` cron dakikaları `[7,27,47]` değişmedi (mevcut `7,27,47 * * * *` cron'u öğle penceresini zaten kapsıyor, `wrangler.jsonc` değişmedi).
- **Worker dağıtılmadı.** Dağıtım `wrangler deploy` ile sizin yapmanız gereken adım. Dağıtım olmadan Worker öğle tetiklemesi göndermez; native cron yedeği çalışır.
- Karar notu: Per/Cum/Paz (brif ve `04-DENEY-PLANI.md`'nin güncel hâli). Önceki sürümde yalnızca Per/Paz yazıyordu; plan dosyası Cuma'yı ekleyecek şekilde güncellendi (sizin değişikliğiniz, commit'lenmedi).

## T2 – Watchdog
- `.github/workflows/watchdog.yml`: cron `37 8 * * *` (11:37 TSİ) ve `37 19 * * *` (22:37 TSİ), yalnızca okur, secret kullanmaz, DB'ye yazmaz (`contents: read`).
- `scripts/watchdog_check.py`: sabah kontrolü `morning`, akşam kontrolü `evening` slotunun `published` olmasını bekler; `pending` ve pencere hâlâ açıksa geçer, satır yoksa veya diğer durumlarda çıkış kodu 1 ve nedeni log'a yazılır. DB `mode=ro` ile açılır.
- GitHub başarısız zamanlanmış workflow için hesap sahibine e-posta gönderir. Bu bildirimler hesap ayarlarında açık olmalı.
- Ertelenen: öğle kontrolü (14:37) uygulanmadı.

## T3 – AI düşüşü
Son 20 gönderi (id 264–283): 14'ü fallback. 9–17 Kasım arası 12 gönderide fallback 7, AI 5.

| Neden | Kanıt | Durum |
|---|---|---|
| `exception` | 17 Kasım 07:08 UTC: Gemini 503 → 5 sn bekleme → 07:08:06'da yeniden istek → 07:08:46'da `ReadTimeout` (40 sn). Zaman aşımı zaten 40 sn'ydi. | Kod hatası değil, Gemini yanıt gecikmesi. Zaman aşımını artırmak ilk düzeltmeydi ama yetmedi. Karar: sizinle. |
| `length` | 17 Kasım 07:08:49: nemotron `rejected: length numbers=[] roots=[]` | **Kod değişti**: `_trim_overlong_blocks` (`ai_service.py`). Model bloğu sınırı aşarsa sondaki cümleler kesilir; ilk cümle kesilmez; kaynak metnin birebir alt kümesi. Yeni bilgi eklenmez. Testler: `tests/test_brief05_length_trim.py`. |
| `rate_limited` | gemma 429, 2 tekrar (brif #4 ek değişikliğiyle) | Değişiklik yok; öncelik sırası nedeniyle gemma son sırada. |
| `unsupported_words` | Bu iki çalışmada görülmedi; ret ayrıntısı artık loglanıyor | **Değişiklik yok.** Kök korumasını gevşetmek için en az 2–3 günlük ret ayrıntısı gerekiyor. |

- Hedef `≥ %50 AI`: bu değişikliklerle tahmin edilemez; Gemini zaman aşımı ve kök koruması hâlâ açık. Canlı günlüklerden ölçülmeli.
- Çevrimdışı karşılaştırma: model çıktıları saklanmadığı için 10 eski çıktıyla karşılaştırma yapılamadı. Uzunluk kesimi için yalnızca birim testleri var.

## T4 – Haftalık rapor
- `scripts/weekly_report.py`: `bot_data.db`'yi `mode=ro` açar; son N gün (varsayılan 7) gönderileri; `verified_external_replies` (gerçek yanıt), 24sa/72sa/7g görüntülemeler, medyan/ortalama/p90; konu, dönem, üretim türü ve slot dilimleri; D-04 kuralı (%80 ve −%20; 4'ten az öğle gönderisinde "belirsiz").
- Test: `tests/test_weekly_report.py` (sentetik DB).

## Açık kalanlar
1. Worker dağıtımı (`wrangler deploy` in `workers/workflow-trigger`) — kullanıcı.
2. Gemini zaman aşımı: 40 sn yetmiyor mu, yoksa bütçe mi artırılmalı? — karar sizde.
3. `unsupported_words` için veri toplanacak.
4. Worktree'ler (`zamanin-wt-noon`, `-watchdog`, `-report`, `-length`) ve dalları (`task/brief05-*`) silinmedi; silme onayınızla.
5. `strategy/04-DENEY-PLANI.md` değişikliğiniz commit'lenmedi.
