# Görev 04 — yerel uygulama teslim raporu

## Sonuç

Yerel uygulama hazır. Cloudflare Cron mevcut iki GitHub workflow’unu uyandıracak; Python botu ve DB Actions üzerinde kalıyor. Worker varsayılan olarak dispatch kapalı teslim edildi. Bu paket canlı cron veya yayın doğrulaması değildir; T0 başlatılmadı.

- Taban SHA: `cca092ef2e57cc5140b766384134491495cb4979`. Origin/main başlangıçta ve teslim öncesinde fetch ile doğrulandı.
- Dal: `codex/task04-external-trigger`.
- Worktree: `/Users/kagansmtdms/.codex/worktrees/task04-external-trigger`.
- Sonuç commit’i ve paket hash’leri ZIP kökündeki manifestte yer alır. Commit kendi SHA’sını içermez.

## Uygulanan kapsam

Worker yalnız bu reponun `schedule.yml` ve `analytics.yml` dosyalarına, `ref=main` ile erişir. HTTP dispatch yüzeyi yoktur. Eksik secret veya `DISPATCH_ENABLED=false` durumunda mutation yapılmaz.

Worker amaçlanan cron zamanı ile gerçek saati ayrı kaydeder. Yayın için her iki saatin de aynı İstanbul gününün aynı açık slotuna ait olması gerekir. Geciken event en fazla 10 dakika yaşında olabilir. Python, Actions kuyruğundan çıktıktan sonra amaçlanan gün/slotu yeniden doğrular; eski tetik başka slotun hakkını alamaz.

Optional workflow input’ları correlation, tetik kaynağı, amaçlanan UTC zaman, İstanbul günü ve slot anahtarını taşır. Shell script içine input gömülmez. Metadata yetkilendirme olarak kullanılmaz. Boş input’lu manuel çağrı ve native cron mevcut gerçek saat guard’ını korur.

SlotAttempt’e beş nullable metadata sütunu eklendi. Eski kayıtlar değiştirilmez. Mevcut ortak DB kilidi, queue politikası, güncel main checkout’u ve sosyal auth/refresh/yayın öncesi uzak reservation checkpoint’i korunur.

GET-only gözlem komutu; dispatch kabulü, ilişkilendirilen run, job başlangıcı ve DB aşamalarını ayrı gösterir. Gerçek checkout SHA’sı ve DB provenance ayrıca doğrulanır. Analytics yayın koduna girmez ve Telegram credential istemez.

## Yerel doğrulama

| Kontrol | Sonuç |
|---|---|
| Tüm Python testleri | 164 passed, 5.54 saniye |
| Worker testleri | 34 passed, 0 failed |
| TypeScript strict typecheck / build | Başarılı |
| Wrangler yerel dry-run | Başarılı; yalnız dispatch kapalı binding; deploy yok |
| İki kez geçici DB migration | Tüm eski sütun değerleri, satır sayıları ve kaynak hash’i korundu |
| compileall / git diff --check | Başarılı |

Ham test çıktıları ve migration hash’leri `evidence/` altında bulunur. Worker paketi 6.56 KiB, gzip 2.33 KiB olarak derlendi. Gerçek API POST’u veya sosyal çağrı yapılmadı.

Testler pencere sınırlarını, UTC/TSİ gece yarısını, geciken ve ertesi güne sarkan tetikleri, native/external çakışmasını, aynı correlation tekrarında tek kökü, rezervasyon hatasında sıfır sosyal çağrıyı ve mevcut partial/unknown replay korumalarını kapsar. Ayrıca sabit hedef/ref, HTTP engeli, eksik secret, 200/204, eksik response ayrıntısı, 401/403/404/422/429/5xx/timeout, sınırlı Retry-After, log redaksiyonu, analytics’in sıfır yayını ve observer’ın GET-only davranışı doğrulandı.

## Korunan kapsam ve kalan doğrulamalar

Korunan checkout `codex/analytics-foundation`, HEAD `60763c357c450d4da8323b14d8d29dd2b2351229`. Başlangıç DB SHA-256 değeri `e12fcc66819f3ab59727be750e04183bfd796faed2c2b5a6f651180fc906b40c`; son kontrol manifestte yer alır.

Push, PR, merge, Cloudflare deploy, credential oluşturma/değiştirme, gerçek dispatch ve T0 yapılmadı. Mevcut otomasyonlar değiştirilmedi; 72h/7d takibi ayrı devam ediyor. Token istenmedi. Gelecekte gereken hesap, secret ve izin adımları `operations.md` içinde.

14 Ekim’de iki yayın slotunun rezervasyonsuz missed olması kesin cron kök nedenini açıklamıyor. Bu Worker GitHub native schedule bağımlılığını azaltır; runner ve queue gecikmesini ortadan kaldırmaz. Dispatch kabulü paylaşım başarısı değildir. Pencereye yetişmeyen external job da skip/missed olur. Duplicate event ek workflow oluşturabilir; kalıcı slot guard’ı ikinci kökü engeller. Nominal sayılar global maliyet kotası değildir.

İki ana gönderinin ölçümleri bir büyüme stratejisi sonucu olarak sunulmadı. `source_fact_validation_status=not_checked`, AI/provider 404/429 ve görseller ayrı backlog olarak kalıyor.

Tasarım ve kararlar: `design.md`. İzinler, nominal maliyet, deploy/rollback sırası ve en az bir tam günlük canlı kabul listesi: `operations.md`. Güncel resmî kaynaklar: `sources.md`.
