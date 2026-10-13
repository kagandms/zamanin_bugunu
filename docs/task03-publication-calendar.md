# Görev 03 — Yayın takvimi ve DB kalıcılığı

Bu paket yerel uygulama ve mock doğrulamadır. Üretime gönderilmedi; doğal scheduling garantisi ve T0/baseline başlangıcı değildir. Taban: `1c0863533d4ab4ba6b86ba6d1325a52feac4a9f8`.

## Politika ve kararlar

| Karar | Uygulama / gerekçe |
|---|---|
| İki ana olay/gün | Europe/Istanbul günü. Platformlar ve zincir parçaları aynı event_id’ye bağlıdır; ayrı ana içerik sayılmaz. |
| Sabah | Hedef 09:07; uygun pencere [09:07, 11:07). |
| Akşam | Hedef 20:07; uygun pencere [20:07, 22:07). |
| Dört yayın kontrolü | UTC `17 6,7,17,18 * * *`: TSİ 09:17, 10:17, 20:17, 21:17. İlk nominal kontrol hedefin 10 dakika sonrasıdır; gecikmiş run pencere dışında telafi yapmaz. |
| Saatlik analitik | UTC dakika 37. `src.analytics` yayın giriş noktasını çağırmaz; Telegram credential’ı gerektirmez. |
| Tek rezervasyon | `(local_day, slot_key)` unique; `BEGIN IMMEDIATE` altında slot ve günlük bütçe birlikte kontrol edilir. Check/insert/write başka writer’a açık bırakılmaz. |
| Uzak rezervasyon | Seçilmiş olay, iki platform rezervasyonu ve slotun reconciliation_required durumu sosyal auth/refresh/yayın çağrısından önce Git’e kaydedilir ve remote HEAD doğrulanır. |
| Muhafazakâr crash davranışı | Uzak rezervasyon sonrası API öncesi crash bile otomatik replay edilmez. Provider idempotency/reconciliation API’si eklenmediği için kaçırılan slot, olası çift köke tercih edilir. |
| Yayın gerçeği | PlatformPublication ve PublicationPart korunur; slot ledger yalnız karar/rezervasyon ilişkisi ve özet durumu tutar. Gerçek zamanlar API/UTC kaynaklarıyla kalır. |
| Ortak kilit | Her iki workflow `zamanin-bugunu-db`, `queue: max`, `cancel-in-progress: false` kullanır. Kilit alındıktan sonra main fetch ve detached checkout yapılır. |
| Git conflict | Non-force HEAD:main push; başarısız push veya remote SHA uyuşmazlığında fail closed. Rebase, binary merge, ours/theirs ve force push yoktur. |

## Bütçe ve slot durumları

`pending`: henüz olay seçilmedi. Pencere kapanınca yalnız bu durum `missed` olur; analytics de bu geçişi yapabilir. `skip_daily_limit`: aynı günün iki olaylık bütçesi tüketilmiş. `preparing`: atomik claim, henüz dış etki yok; diğer eşzamanlı rezervasyonlar bu bütçeyi görür. `reconciliation_required`: olay bağlıdır ve dış etki olasılığı için no-replay koruması etkin; süre dolması bu durumu açmaz. `published` ve `partial`, mevcut platform sonuçlarından türetilir. `failed`, hazırlık tamamlanamadığı veya checkpoint sonrasında pencere kapanıp hiç yayın başlatılmadığı durumdur; seçilmiş olay başka olayla değiştirilmez.

Bütçe, bilinen gerçek ana parçası o İstanbul gününde yayımlanmış tekil olayları ve aynı günün consuming slotlarını event_id üzerinden birleştirir. Henüz event_id’si olmayan preparing slot da bir yer tutar. Yeni metadata’ya sahip eski reserved/unknown platform girişimleri gün içi belirsiz bütçe olarak dikkate alınır. Legacy unknown kayıtların bilinmeyen yayın zamanı bugüne uydurulmaz. Aynı olayın Telegram ve Threads başarısı tek içerik; reply ve fotoğraf/metin parçaları ek içerik değildir.

Güvenli otomatik yeniden deneme bu sürümde yoktur. Aynı slot tekrar kontrol edildiğinde yeni olay seçilmez. Günlük iki içerik hedef ve üst sınırdır; hizmet kesintisinde iki yayını garanti etmez.

## Crash matrisi

| Nokta | Uzak kayıtta ne var? | Sonraki run |
|---|---|---|
| Yerel claim/olay hazırlığından önce | Dış etki yok | Pencere açıksa normal claim mümkün. |
| Yerel claim sonrası, reservation push başarısız | Sosyal auth/refresh/yayın çağrısı sıfır | Otomatik binary conflict çözümü yok; workflow hata verir. Final save de başarısız olabilir. Uzak kayıtta rezervasyon yoksa yeni run güvenle başlayabilir çünkü dış etki yapılmadı. |
| Reservation push doğrulandı, API başlamadı | Seçili olay ve reconciliation_required | Otomatik replay yok; eksik slot raporlanır. |
| API sırasında timeout/crash | Aynı uzak rezervasyon | Reconciliation required; yeni kök veya yeni olay yok. |
| API onayı sonrası, sonuç push başarısız | Aynı uzak rezervasyon, son parçalar kaybolabilir | Kör yeniden yayın yok; platform/DB uzlaştırması gerekir. |
| Sonuç push doğrulandı | Gerçek platform/parça sonuçları | Result SHA receipt’i kaydedilir; workflow’un final DB save’i receipt’i de taşır. Receipt save hatası doğrulanmış önceki sonuç commit’ini silmez. |

Başarılı Threads kökü ve başarısız reply, veya Telegram başarısı ve Threads hatası slotu yeniden açmaz. Adapters mevcut readiness, partial/unknown ve kaynak fallback davranışlarını korur. Auth uyarısı için slot dışı Telegram gönderimi kaldırıldı; auth problemi workflow logunda kalır. Mevcut opportunistic Threads refresh, uzak reservation doğrulamasından sonraya taşındı; bu yerel görevde gerçek auth/refresh çağrısı yapılmadı.

Pencere hazırlık/checkpoint sonrası ve gerçek adapter çağrısı öncesinde yeniden denetlenir. Threads readiness beklemesi sonrası kök publish boundary’sinde de kontrol vardır; Telegram her HTTP gönderim denemesinde kontrol eder. Başlamış bir Threads zincirinin reply’ları aynı olaydır; bunların tamamlanması yeni bir eski slot/kök oluşturmaz. Provider’ın request sonrası gerçek yayın zamanını değiştirme garantisi yoktur; API yayın zamanı ayrı kaydedilir.

## Analitik, maliyet ve gözlem

Saatlik workflow günde 24 nominal runner fırsatı ve dependency/setup maliyeti getirir. SQL geçmiş taraması yapılır; Insights/reply API çağrıları yalnız due, bilinen zamanlı ve terminal canonical sonucu bulunmayan pencereler içindir. Başarılı/late/missed_late canonical kayıtlar yeniden sorgulanmaz. Uygun zaman penceresindeki başarısız attempts mevcut politika ile sonraki saatte denenebilir. Snapshot tekilliği, immutable metric attempts, null/0, optional replies ve 0/2/3 exit kodları değiştirilmedi.

Yayın kapalı/limit dolu olsa da analytics ölçüm ve missed-slot bakımı yapar. Rapor, gerçek ana olay sayısı, en az bir doğrulanmış parçası olan platform sayısı, parça sayısı ve slot bütçesini ayrı gösterir; platformun full/partial/unknown sonucu mevcut analytics raporunda ayrıca yer alır. DB checkpoint receipt’leri ve verified SHA logları kalıcılık kanıtıdır; yeşil workflow tek başına tam platform yayını değildir.

[GitHub concurrency dokümanı](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency) doğrultusunda max queue kullanılır. Kuyruk kapasitesi sınırlıdır; FIFO beklemeye giriş sırasındadır. [Schedule gecikmesi/drop ihtimali](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) sürer. Ortak kilit veri kaybını önlemeye yöneliktir; tam zamanında tetikleme garantisi değildir. Uzun işler nedeniyle pencere kaçarsa yayın skipped/missed olur.

İki mevcut ana parçanın kesin hedefleri:

| Olay / Threads parça | Gerçek yayın TSİ | 24h TSİ | 72h TSİ | 7d TSİ |
|---|---|---|---|---|
| 229 / 17893985652438381 | 13 Ekim 02:34:12 | 14 Ekim 02:34:12 | 16 Ekim 02:34:12 | 20 Ekim 02:34:12 |
| 230 / 18124547869786062 | 13 Ekim 16:59:54 | 14 Ekim 16:59:54 | 16 Ekim 16:59:54 | 20 Ekim 16:59:54 |

Her ikisi threads_media_timestamp kaynaklıdır. Bunların reply parçaları da mevcut collection kurallarıyla kendi gerçek zamanlarında izlenir. Pencere/grace kuralları değişmedi; geçmişe sahte snapshot yazılmadı.

## Devreye alma ve geri dönüş

1. Ayrı üretime geçiş onayı ve güncel main/DB tekrar doğrulaması gerekir. İnceleme patch’i yalnız bu görev dosyalarını içerir; tracked bot_data.db içermez.
2. Görev 02 source/readiness korumaları korunarak güncel tabana entegre edilir. İki workflow birlikte geçer; eski DB writer run’ları queued/in_progress durumundayken geçiş yapılmaz. Eski workflow’lar farklı concurrency grubu kullandığından geçişi ortak kilit varsayımıyla sürmek güvenli değildir.
3. Üretim migration uygulama tarafından additive yapılır. Bu görev yalnız kopyada migration çalıştırdı. Workflow ref main, serialization ve contents:write gereksinimleri önceden kontrol edilir.
4. İlk doğal uygun run’da source/checkout SHA, slot kararı, reservation remote SHA, platform parçaları ve sonuç/receipt commit’i ayrı doğrulanır. Pencere dışındaki doğal run yalnız skip üretebilir; manuel dispatch doğal scheduling kanıtı olmaz.
5. Geri dönüşte DB snapshot/slot/attempt kayıtları silinmez ve eski bot_data.db checkout’u geri koyulmaz. Writer’lar durdurulduktan ve açık reconciliation_required slotlar incelendikten sonra yalnız kod/workflow değişikliği geri alınabilir. Eski dört/gün botu kör biçimde tekrar etkinleştirmek iki/gün korumasını kaldırır; bu operasyon ayrıca onay ve limit koruması gerektirir.

## Ayrı backlog ve sınırlamalar

- Görsel kalite ve AI/provider 404/429 düzeltmeleri bu patch kapsamında değildir; mevcut seçim/fallback davranışı korunmuştur. İçerik hazırlama kodu küçük fonksiyonlara taşındı; üretim promptu değiştirilmedi.
- Kayıp onayların platform reconciliation işlemi manuel inceleme gerektirir; yeni reconciliation API veya haricî scheduler kurulmadı.
- Yeni slot/DB politika akışı üretimde doğrulanmadı. İki/gün gerçek yayın garantisi, kesin cron kök nedeni çözümü ve T0 iddiası yoktur.
