# 12 – Brif #3 uygulama notu (Gemini düşüşü, çatışma görseli, konu soğuması)

Brif: `strategy/11-HAIKU-BRIF-03-GEMINI-GORSEL-KONU-ARASI.md`.

## T1 – Gemini neden devre dışı kaldı

Kaynak: 9 Kasım 06:07 UTC "publication slots" çalışması (GitHub Actions run `42571178652`), `gh run view --log`. Anahtar logda maskeli (`GEMINI_API_KEY: ***`).

| Sıra | Sağlayıcı / model | Sonuç |
|---|---|---|
| 1 | Gemini `gemini-3.5-flash` | **HTTP 503** (06:08:05; yaklaşık 1 sn) |
| 2 | OpenRouter `nvidia/nemotron-3-ultra-550b-a55b:free` | Kabul edildi (06:08:08, `attempt=2`, `rich_source=True`) |

Log satırları (anahtarsız): `Gemini Model (gemini-3.5-flash) returned HTTP 503` → `Source-bound generation accepted: provider=openrouter attempt=2`.

**Neden:** Gemini geçici aşırı yoğunluk (503) döndürdü. Kodda 429 için yeniden deneme vardı, 503 için yoktu; kaskad hemen bir sonraki sağlayıcıya geçti. Kota (429), zaman aşımı, boş yanıt veya guard reddi değil.

**Düzeltme:** 503'te aynı model bir kez (`OVERLOAD_RETRIES = 1`) 5 sn geri çekilip tekrar denenir (modelin süre payı içinde). Sağlayıcı hata metni (ilk 160 karakter, anahtar `***` ile maskeli) artık logda. Testler: 503→200 Gemini'de kalır; iki 503 sonraki sağlayıcıya geçer.

**Hâlâ bilinmeyen:** 503'ün Google tarafındaki süresi; 5 sn'lik tek geri çekilme yetmeyebilir. İlk 503'ün gövde metni o çalışmada loglanmadığı için ayrıntısı yok (artık loglanıyor).

## T2 – Çatışma/siyaset görseli

`SAVAS_ASKERI` ve `SIYASET` konularında `Flag_of`, `Coat_of_arms`, `Emblem`, `Portrait`, `Poster`, `Propaganda` içeren görseller seçilmez. Sıra: harita (`map`) → diğer sayfaların fotoğrafları; hiçbiri yoksa **görselsiz** gönderi (Threads `TEXT`, Telegram metin; her ikisi de destekliyor). Yeni görsel üretilmez; bu konularda AI görsel yedeği de kapalı. Diğer konularda eski davranış aynı.

Not: 9 Kasım gönderisindeki Azerbaycan bayrağı bu kuralla elenir. Sınır: yalnızca dosya adı/URL anahtarlarına bakılır; anahtarsız adlı bir bayrak görseli geçebilir.

## T3 – Konu soğuması

Anahtar: kaynak sayfa başlığının ilk iki anlamlı (4+ harf) sözcüğü eşleşir ve yıl ±1 içindedir. Son 7 gündeki yayınların başlığı `source_url` slug'ından (yoksa `source_id`) alınır. Eşleşen aday −80 puan alır; elenmez. Adayın başlığı olarak ilk bağlantılı sayfa ve özetin geldiği sayfa kullanılır. Brifin ek ölçütü "aynı `topic_category` + aynı yıl" bilerek eklenmedi (sade tutma kuralı).

Sınır: genel sayfalar ("Amerika Birleşik Devletleri" gibi) yılı yakın başka olaylara ceza verebilir; yalnızca ilk iki sözcük karşılaştırıldığı için "İkinci Dağlık Karabağ Savaşı" ile "İkinci Dünya Savaşı" ayrılır (ikinci sözcük farklı).

## T4 – Hook (yalnızca ölçüm)

| Gönderi | 1. parçadaki anlamlı sözcüklerin olay cümlesinde bulunan payı | Olay sözcüklerinin 1. parçada kullanılan payı |
|---|---|---|
| 271 – Şuşa (8 Kasım, Gemini) | %100 | %100 |
| 272 – Ateşkes (9 Kasım, nemotron) | %43 | %60 |

271'de 1. parça olay cümlesinin yeniden sıralanmış hâli; 272'de özetten tarih ve saat eklenmiş, daha az tekrar. Prompt değiştirilmedi.
