# Görev 04 — devreye alma, izinler, maliyet ve kabul

## Yapılandırma ve kullanıcı adımları (bu görevde uygulanmadı)

| Öğe | Değer / kapsam |
|---|---|
| Worker | zamanin-bugunu-workflow-trigger; ayrı config `workers/workflow-trigger/wrangler.jsonc` |
| Değişken | DISPATCH_ENABLED=false; yalnız sonraki üretim adımında true |
| Secret binding | GITHUB_DISPATCH_TOKEN; süreli fine-grained PAT, yalnız kagandms/zamanin_bugunu seçili |
| Asgari GitHub yetkisi | Actions:write (dispatch); read bunun içinde. GitHub otomatik Metadata:read verir. Contents write/admin/secrets/workflows kapsamı eklenmez. |
| Ayrı GET observer token | İsteğe bağlı GITHUB_OBSERVER_TOKEN, Actions:read; public GET anonim de yapılabilir. .env okunmaz. |
| Cloudflare account | Kullanıcı ilgili hesabı sonraki adımda seçer; ayrı Worker deploy/secret yetkisi. Diğer sitelerin hesap/config/domain'leri kullanılmaz. |

Mevcut uygun GitHub App installation credential da API tarafından desteklenir; bu kod PAT/installation token secret'ını tüketir, App private key/JWT mint/refresh altyapısı eklemez. Expiry/401 olduğunda secret gelecekte güvenli terminal/dashboard üzerinden güncellenir; değer sohbete veya dosyaya yazılmaz. Süre/rotation hesabın sahibine aittir. Repo GITHUB_TOKEN'ını Worker'a çıkarmayın. Yerel .dev.vars*, .env.*, node_modules/.wrangler Git dışında; teslimde token yok.

## Sonraki onaylı devreye alma sırası

1. Görev patch'ini inceleyin; güncel main DB/commit'i koruyarak workflow input/CLI metadata desteğini önce main'e alın. Yeni workflow'ların ortak `zamanin-bugunu-db`, queue:max, cancel-in-progress:false ve kilit sonrası güncel checkout'u korunmalı. Bu teslimde push/PR/merge yok.
2. Temiz checkout'ta CI ve iki migration denetimini yineleyin. DB rollback için eski snapshot'ı main'e koymayın. Yeni alanlar nullable, eski veriler korunur.
3. Ayrı Worker'ı **dispatch kapalı** deploy edin, Worker adı/cron/env/account'u inceleyin; secret binding'i kullanıcı güvenli olarak girsin. Ardından inceleme/onayla DISPATCH_ENABLED=true yapın. Metadata desteği üretimde olmadan Worker'ı açmayın. Worker cron değişikliklerinin dağılımı anlık olmayabilir (resmî doküman15dk'ya kadar diyor).
4. Native cron'ları yedek bırakın. Manuel dispatch/rerun veya test gönderisi üretmeden ilk doğal Cloudflare cron'u izleyin.200/204 kabulünü başarıyla paylaşım diye sunmayın.
5. Asgari bir tam İstanbul gününün iki penceresini ve due analytics ölçümlerini gözleyin. Runner pencereye yetişmiyorsa missed raporlayın; otomatik telafi yok.

## Nominal iş hacmi ve maliyet sınırları

- Publication cron `7,27,47 * * * *`:72 Worker invocation/gün; yalnız2×2saat×3=12 dispatch/gün.60 pencere dışı no-op.
- Analytics `37 * * * *`:24 invocation/dispatch/gün. Toplam96 nominal Worker invocation,36 nominal POST/gün.429 retry dahil teslim başına en fazla2 POST; duplicate yoksa72 POST üst sınırı.429 ilk istek reddedilmiş olduğundan normal kabul sayısı36; timeout sonrası unknown kabul ayrıca gözlenir.
- Native cron4publication+24analytics=28 nominal iş/gün korunur. External ile toplam64 nominal workflow talebi/gün; teslim tekrarları bu sayıyı artırabilir. Bu tasarım hard global dispatch kotası değildir. DB en fazla2 farklı ana olay/gün ve tek slot kökü korur; her due olmayan analytics sosyal API çağırmaz.
- CPU limit10ms/invocation; HTTP timeout5sn, handler tek kısa429 backoff dahil nominal en fazla12sn ağ/bekleme bütçesi (gerçek runtime garantisi değil). Uzun polling/DB/KV/D1/DO yok.
- Resmî Workers Free100.000 request/gün ve10ms CPU sınırı; bu96 nominal iş bunun altında. Paid plan taban$5/ay ve hesap genel kullanımına bağlı aşım/Logs maliyetleri vardır. Bu repo özel faturanın garantisi değildir; account'un mevcut planı ve diğer kullanımı incelenmedi.
- GitHub ubuntu-latest public repo standart hosted runner politikası ve ücret/limitleri devreye almadan kontrol edilmeli.64 talep, job süresine bağlı runner dakikası ve queue yükü yaratır. Bounded retry/HTTP kapalı olması günlük global fatura hard cap'i değildir. Bütçe alarmı/Worker disable operasyonu hesap sahibindedir.

## GET-only gözlem

`python -m src.dispatch_observation --workflow schedule.yml --correlation cf-publication-<epoch_ms> --db /absolute/temporary-copy.db --receipt /absolute/sanitized-worker-receipt.json`

Analytics için analytics.yml ve cf-analytics prefix'i kullanılır. GET komutu son100 dispatch run/jobs bilgisi okur, social API/POST/migration yok. `--receipt` Worker dispatch_result tekJSON kaydı, `--db` **önceden commit/provenance doğrulanmış geçici immutable kopya** olmalıdır. DB dosyası verilmezse ilgili aşamalar unknown. Run title eşleşmesi authorization değildir. Receipt kabulü job başlangıcını; DB'deki receipt de tek başına sonraki checkout kalıcılığını kanıtlamaz. Zamanında başlangıç için jobs.started_at, gerçek yayın için Threads API timestamp'i kullanılmalıdır.

Aşamalar ayrı kaydedilir: dispatch accepted → correlated run(s) observed → actual job started → slot claimed → reservation checkpoint remote verified → main/reply published → result/receipt persisted → subsequent natural checkout preserved. Observer API workflow head_sha'yı raporlar; gerçek kilit sonrası SHA'yı güvenli job logundan ayrıca çıkarın. Worker logunda scheduled_time_ms, observed_time_ms, correlation, intended UTC/day/slot, HTTP status ve varsa runID bulunur; bearer token/raw response/error URL yok.

## En az bir tam gün canlı kabul kontrol listesi

- [ ] Worker dispatch enabled, secret varlığı/expiry kapsamı değer çıkarmadan doğrulandı; doğal cron scheduled/observed saatleri ayrı.
- [ ] Sabah/akşam her pencerenin nominal6 kontrolü ve gerçekleşenler, schedule/dispatch kaynakları ayrı; eksik run unknown/no_observed_run.
- [ ] Kabul200/204, correlationrunID, jobbaşlangıcı, workflow GITHUB_SHA ve locksonrası checkout SHA ayrı kanıtlandı.
- [ ] İki tetik türü aynı DB kilidinden geçti; native/external aynı slotta ikinci kök üretmedi. Stale ertesi gün/eski slot tetikleri sıfır sosyal çağrı verdi.
- [ ] Event/platform rezervasyonları ve reconciliation_required slot, **sosyal auth/refresh/yayından önce** uzak reservation commit'te mevcut ve doğrulama log sırası doğru.
- [ ] Gerçek Threads auth/API türü ayrı; her ana/reply ID, final text/media, API UTC timestamp/source, full/partial/unknown kaydedildi. Source fact validation not_checked görünür.
- [ ] Result commit+receipt save ve sonraki doğal checkout'ta slot/publication/part/attempt korunması doğrulandı.
- [ ] Analytics Telegram credential istemedi, sıfır publish; gerçek CLI exit ve due sonuç, snapshot tekilliği/immutable attempt, null/0/unknown reply ayrımı kanıtlandı.
- [ ] Mevcut229/part28 ve230/part31 +reply32 için24h/72h/7d gerçek yaş ve success/late/missed izlendi. Mevcut otomasyon değiştirilmedi.
- [ ] Günlük ana olay≤2, platform/parça sayısı ayrı. Pencere kaçarsa missed; runnergecikmesi çözülmüş diye ilan edilmedi. T0 kullanıcı kararı olarak ayrı kaldı.

## Geri dönüş / hata

Önce Worker DISPATCH_ENABLED=false veya cron disable ile yeni dış talepleri durdurun; bu kuyruktaki job'ları iptal etmez. Metadata guard/dailybudget/remotecheckpoint korumalarını bırakın. Native cron kalır, DB/slot/attempt silinmez veya resetlenmez. Credential hatasında yalnız tür/status raporlayın; token güncellemesi ayrı ihtiyaçtır. Rezervasyon/sonuç/finalsave hatasında blocked/failed, canlıwriter'ı kontrollü durdurma ihtiyacını raporlayın; replay, yeni kök, eskiDB üzerine yazma yok. Bu işlemler bu yerel görevde yapılmadı.
