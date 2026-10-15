# Görev 04 — tasarım ve kararlar

Onay: kullanıcının Görev04 belgesini uygulama talebi. Kapsam yerel kod, test, inceleme ZIP'i. Üretim entegrasyonu sonraki ayrı onaya bağlıdır.

## Sözleşme

- Worker yalnız `kagandms/zamanin_bugunu` repo, `main` ref, `schedule.yml`/`analytics.yml` hedefleri için Cron handler'dan dispatch eder. Public HTTP404/405; workers.dev/preview kapalı, route/domain yok.
- İstanbul iki olay/gün, yarı açık09:07–11:07 ve20:07–22:07 değişmez. Python/DB/runner Actions'ta kalır. Native cron yedek kalır.
- Worker secret `GITHUB_DISPATCH_TOKEN`; `DISPATCH_ENABLED=false` varsayılan. Threads/Telegram/AI/DB secret yok. Account/domain config devralınmaz.
- Performans: kısa handler, GET polling yok, POST başına5sn timeout, yalnız429 sayısal Retry-After≤2sn için bir retry. Her retry öncesi amaçlanan+gerçek saat tekrar kontrol edilir. 5xx/timeout/belirsiz kabulde POST tekrarı yok; bir sonraki nominal kontrol beklenir. Bu kısa bekleme yalnız açık429 backoff'udur, yarış/slot kapatma için sleep değildir.
- Aynı Cloudflare event birden fazla gelebilir. Correlation deterministik; Worker'da tam exactly-once veya hard günlük maliyet sayacı iddiası yok. Kalıcı DB slottransaction'ı, ortak Actions kilidi ve uzak API öncesi reservation checkpoint'i tek kökü korur. KV/D1/DO eklenmedi.
- Yerel testler sahte saat ve mock network kullanır. Kabul, job başlangıcı, rezervasyon, gerçek yayın, sonuç kalıcılığı ayrı gerçeklerdir; canlı external cron ve T0 bu teslimde yoktur.

## Karar günlüğü

1. **Durumsuz Worker seçildi.** KV/DO ile dedupe alternatifi maliyet ve ikinci gerçeklik yaratır; bot DB replay koruması zaten kalıcıdır. Correlation birden fazla attempt'e bağlanabilir; slot/event tek kalır.
2. **Sabit hedefler kodda allowlist.** Repo/ref/URL ortamdan veya HTTP'den seçilemez. Bunlar değişken müşteri endpoint'i değil güvenlik sözleşmesidir.
3. **Clock çift doğrulaması.** Worker event yaşı0–10dk ve intended/observed aynı açık slot; Python kuyruk sonrası aynı İstanbul gün/slotunu yeniden doğrular. İş ertesi günün veya akşamın slotuna taşınmaz. Yerel manual boşinput gerçek saat guard'ından geçer, metadata yetkilendirme değildir.
4. **Dar retry.** Yalnız açık429+≤2sn numeric Retry-After bir kez. HTTP-date/uzun Retry-After ve5xx ertelenir; timeout sonrasındaki mutation belirsizliği otomatik replay edilmez. Daha agresif retry yerine sonraki20dk kontrol seçildi.
5. **Additive nullable metadata.** `slot_attempts` içine trigger_source, correlation_id, intended_at, intended_day, intended_slot eklendi. Eski satırlar NULL kalır; silme/backfill yok. İki kez migration ve tüm eski sütun değerhash'leri korunur. Analytics metadata yalnız kendi CLI/log/run-title bağlantısında, yayınledger'ına yazılmaz.
6. **API version2026-03-10.** Güncel resmî dispatch sözleşmesi200 ile workflow_run_id/URL döndürüyor; ayrıca204 uyumluluk kabul edilir.200 bozuk/eksik ayrıntıda kabul edilir ama runID unknown kalır, replay yapılmaz. Güncel belgede olmayan `return_run_details` parametresi gönderilmez.
7. **Aşamalı gözlem.** GET-only observer en son100 external run'ı tam run-name+event+branch ile eşler; tüm duplicate run'ları gösterir. Liste dışında kanıt yokluğu unknown'dır. Gerçek checkout SHA logdan, DB checkpoint commit/provenance ayrı doğrulanır; head_sha aynı varsayılmaz.

## Sınırlar

Cloudflare cron/API kabulü GitHub runner/queue'nun pencereye yetişmesini garanti etmez. Pencereye yetişmeyen external job da skip/missed olur. Kesin eski cron/drop kök nedeni kanıtlanmadı; bu kod root-cause-solved iddiası değildir. Tekrarlayan kaçırmada bir sonraki seçenek yürütmeyi Actions dışına taşımaktır; burada yapılmadı. source_fact_validation_status=not_checked, AI404/429 ve görseller ayrı backlog; iki gönderi/üç snapshot büyüme stratejisi kanıtı değildir.
