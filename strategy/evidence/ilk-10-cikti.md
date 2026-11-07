# İlk 10 canlı çıktı (7 Kasım, kaynağa bağlı yorum, yayın yok)

Bu dosya yalnızca inceleme içindir. Yayın yapılmadı, veritabanına yazılmadı. Üretim açılmadan önce onay bekler.

Kaskad: `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-26b-a4b-it:free` → `openrouter/free`. Çağrılar arasında 20 sn bekleme.

Sonuç: 0/10 olay model çıktısıyla üretildi, 10 olay fallback'e düştü.

**Bu çalıştırmanın durumu (yapılandırılmış fallback, model çıktısı yok):**

- `gemini-2.5-flash`: 404, "artık yeni kullanıcılara açık değil". Ortamda `GEMINI_API_KEY` tanımlı, `.env`'de yok; anahtar değeri kaydedilmedi. `gemini-2.5-flash-lite`: 404. `gemini-flash-latest`: istek zaman aşımına uğradı. Modeller listesi (`generateContent` destekleyen) alındı; `GEMINI_MODEL` ortam değişkeni ile çalışan bir kimlik seçilmeli.
- `nvidia/nemotron-3-ultra-550b-a55b:free` ve `google/gemma-4-31b-it:free`: "free-models-per-day" günlük kotası doldu (429). Bu geçici değil, günlük; yeniden deneme bu gün sonuç vermez.
- Sonuç: 10/10 yapılandırılmış fallback; model çıktısı yok.

| # | Olay | Durum | Model | Denemeler |
|---|---|---|---|---|
| 1 | Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti. | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |
| 2 | 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Ke | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |
| 3 | ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bus | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |
| 4 | Birleşik Devletler kuvvetleri ile Şavniler arasında Tippecanoe Muharebesi gerçekleşti. | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |
| 5 | Richard Nixon ABD Başkanı seçildi. | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |
| 6 | Brad Harris, Amerikalı oyuncu, dublör ve yapımcı (d. 1933) | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |
| 7 | Barbara Liskov, Amerikalı bilgisayar bilimcisi | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |
| 8 | Lev Troçki, Rus Bolşevik siyasetçi, devrimci ve Marksist teorisyen (1917 Rus devriminin ön | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |
| 9 | Ögeday Han, Moğol İmparatoru ve Cengiz Han'ın oğlu (ö. 1241) | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |
| 10 | Chaine Staelens, Hollandalı voleybolcu | fallback: http_error,rate_limited | - | gemini-2.5-flash=404, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429 |

## 1. Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti.

- Yıl: 656
- Kaynak özeti: Cemel Muharebesi, Cemel Vakası, Basra Savaşı ya da Deve Olayı 8 Aralık 656 tarihinde, Halife Ali bin Ebu Talib ile İslam Peygamberi Muhammed'in dul eşi Aişe'nin taraftarları arasında, Basra'da gerçekleşen muharebe. Müslümanlar arasındaki ilk iç savaştır. Cemel Savaşı, Ali'nin zaferiyle sonuçlandı.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.656)
> 
> Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti. Cemel Muharebesi, Cemel Vakası, Basra Savaşı ya da Deve Olayı 8 Aralık 656 tarihinde, Halife Ali bin Ebu Talib ile İslam Peygamberi Muhammed'in dul eşi Aişe'nin taraftarları arasında, Basra'da gerçekleşen muharebe. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?

## 2. 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Kenan Evren, Türkiye'nin 7. Cumhurbaşkanı oldu.

- Yıl: 1982
- Kaynak özeti: Dönemin Devlet Başkanı Kenan Evren, Anayasa'nın ilk üç maddesinin "değiştirilemeyeceğini ve değiştirilmesinin teklif edilemeyeceğini" dördüncü madde olarak taslağa ekletmiştir. Anayasa, 7 Kasım 1982 Pazar günü yapılan halk oylaması sonucu yüzde 91,37 oranında kabul oyu ile kabul edilmiştir.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1982)
> 
> 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Kenan Evren, Türkiye'nin 7. Cumhurbaşkanı oldu. Anayasa, 7 Kasım 1982 Pazar günü yapılan halk oylaması sonucu yüzde 91,37 oranında kabul oyu ile kabul edilmiştir. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?

## 3. ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bush'tan daha fazla oy almasına rağmen, hayli tartışmalı bir belirsizlik döneminden sonra, ABD Yüksek Mahkemesi'nin kararıyla, George W. Bush 12 Aralık 2000'de Başkan ilan edildi.

- Yıl: 2000
- Kaynak özeti: Bush'un en büyük oğlu olan Cumhuriyetçi aday Teksas Valisi George W. Bush, Demokrat Başkan Yardımcısı Al Gore'u ufak bir farkla yenerek ABD'nin 43. Seçimi kaybeden aday Al Gore, Yüksek Mahkemenin seçim hakkındaki kararını açıklamasından sonra 13 Aralık'ta Bush'u tebrik etti.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.2000)
> 
> ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bush'tan daha fazla oy almasına rağmen, hayli tartışmalı bir belirsizlik döneminden sonra, ABD Yüksek Mahkemesi'nin kararıyla, George W. Bush 12 Aralık 2000'de Başkan ilan edildi. Seçimi kaybeden aday Al Gore, Yüksek Mahkemenin seçim hakkındaki kararını açıklamasından sonra 13 Aralık'ta Bush'u tebrik etti. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?

## 4. Birleşik Devletler kuvvetleri ile Şavniler arasında Tippecanoe Muharebesi gerçekleşti.

- Yıl: 1811
- Kaynak özeti: Tippecanoe Muharebesi, 7 Kasım 1811 tarihinde Indiana Toprakları(Indiana Territory) Valisi William Henry Harrison kumandasındaki Birleşik Devletler kuvvetleri ve Shawnee kabilesinin lideri Tecumseh ile bağlantılı Kızılderili savaşçılar arasında yapılan bir muharebedir. Gerilim ve şiddet arttıkça, Vali Harrison konfederasyonun Prophetstown'daki merkezini dağıtmak için yaklaşık 1.000 kişilik bir orduyla Tippecanoe ve Wabash nehirlerinin birleştiği noktaya yürüdü.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1811)
> 
> Birleşik Devletler kuvvetleri ile Şavniler arasında Tippecanoe Muharebesi gerçekleşti. Tippecanoe Muharebesi, 7 Kasım 1811 tarihinde Indiana Toprakları(Indiana Territory) Valisi William Henry Harrison kumandasındaki Birleşik Devletler kuvvetleri ve Shawnee kabilesinin lideri Tecumseh ile bağlantılı Kızılderili savaşçılar arasında yapılan bir muharebedir. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?

## 5. Richard Nixon ABD Başkanı seçildi.

- Yıl: 1972
- Kaynak özeti: 1972 Amerika Birleşik Devletleri başkanlık seçimleri, 7 Kasım 1972 tarihinde Mevcut Cumhuriyetçi Başkan Richard Nixon ile Demokrat aday Güney Dakota Senatörü George McGovern arasında gerçekleşti. Seçimleri oyların büyük çoğunluğunu alan mevcut Cumhuriyetçi Başkan Richard Nixon kazandı.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1972)
> 
> Richard Nixon ABD Başkanı seçildi. 1972 Amerika Birleşik Devletleri başkanlık seçimleri, 7 Kasım 1972 tarihinde Mevcut Cumhuriyetçi Başkan Richard Nixon ile Demokrat aday Güney Dakota Senatörü George McGovern arasında gerçekleşti. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?

## 6. Brad Harris, Amerikalı oyuncu, dublör ve yapımcı (d. 1933)

- Yıl: 2017
- Kaynak özeti: Bradford Harris, Amerikalı oyuncu, dublör ve yapımcıdır. Harris önceleri dublörlük yapmış daha sonra André de Toth's Monkey on My Back ve Li'l Abner adlı filmlerle ilk defa beyazperdede yer alarak oyunculuğa adım attı.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.2017)
> 
> Brad Harris, Amerikalı oyuncu, dublör ve yapımcı (d. 1933). Harris önceleri dublörlük yapmış daha sonra André de Toth's Monkey on My Back ve Li'l Abner adlı filmlerle ilk defa beyazperdede yer alarak oyunculuğa adım attı. #tarih
>
> Bu ismi tanıyor muydunuz?

## 7. Barbara Liskov, Amerikalı bilgisayar bilimcisi

- Yıl: 1939
- Kaynak özeti: Barbara Liskov, Amerikalı bilgisayar bilimcisi. Massachusetts Teknoloji Enstitüsü'nde profesör olarak çalışan Liskov Amerika Birleşik Devletleri'nde bilgisayar bilimi doktorası sahibi ilk kadınlardan biridir.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1939)
> 
> Barbara Liskov, Amerikalı bilgisayar bilimcisi. Massachusetts Teknoloji Enstitüsü'nde profesör olarak çalışan Liskov Amerika Birleşik Devletleri'nde bilgisayar bilimi doktorası sahibi ilk kadınlardan biridir. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?

## 8. Lev Troçki, Rus Bolşevik siyasetçi, devrimci ve Marksist teorisyen (1917 Rus devriminin önde gelen isimlerinden) (ö. 1940)

- Yıl: 1879
- Kaynak özeti: Lev Davidoviç Bronştayn ya da yaygın bilinen adıyla Lev Troçki ; Rus devrimci, Sovyet siyasetçi ve siyasi teorisyendir. İdeolojik olarak bir Marksist ve Leninist olan Troçki'nin fikirleri, Troçkizm olarak bilinen bir Marksizm düşüncesine ilham oldu.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1879)
> 
> Lev Troçki, Rus Bolşevik siyasetçi, devrimci ve Marksist teorisyen (1917 Rus devriminin önde gelen isimlerinden) (ö. 1940). Lev Davidoviç Bronştayn ya da yaygın bilinen adıyla Lev Troçki ; Rus devrimci, Sovyet siyasetçi ve siyasi teorisyendir. #tarih
>
> Bu ismi tanıyor muydunuz?

## 9. Ögeday Han, Moğol İmparatoru ve Cengiz Han'ın oğlu (ö. 1241)

- Yıl: 1186
- Kaynak özeti: Ögeday, Moğol İmparatorluğu'nun ikinci hanı ve Cengiz Han'ın üçüncü oğluydu. 1186 yılında doğan Ögeday, babasının iktidara gelmesi sırasında birçok savaşta savaştı ve Moğolların Harzemşah İmparatorluğu'nu işgalinde önemli roller üstlendi.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1186)
> 
> Ögeday Han, Moğol İmparatoru ve Cengiz Han'ın oğlu (ö. 1241). Ögeday, Moğol İmparatorluğu'nun ikinci hanı ve Cengiz Han'ın üçüncü oğluydu. #tarih
>
> Bu ismi tanıyor muydunuz?

## 10. Chaine Staelens, Hollandalı voleybolcu

- Yıl: 1980
- Kaynak özeti: Chaïne Staelens Belçika kökenli Hollandalı voleybolcu. Belçikalı voleybolcu bir baba ve Hollandalı voleybolcu bir annenin çocuğu olarak voleybola Belçika’da başladı. Daha sonra voleybol kariyerini Hollanda’da sürdürdü.
- Üretim tipi: `source_fallback:http_error,rate_limited:structured`
- Model: -
- Ret nedeni: http_error,rate_limited

**Denemeler:**

- `gemini-2.5-flash` HTTP 404: { ⏎   "error": { ⏎     "code": 404, ⏎     "message": "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements. We recommend you to use the Interactions API (https://aistudio.google.com/doc
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1980)
> 
> Chaine Staelens, Hollandalı voleybolcu. Chaïne Staelens Belçika kökenli Hollandalı voleybolcu. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?

## Tam akış kuru çalıştırması (DRY_RUN, kopya veritabanı)

Akış: olay seçimi → hazırlama → rezervasyon → yapılandırılmış fallback → kuru yayın. OpenRouter anahtarı boş bırakıldı (OpenRouter'a çağrı yok). Yayın adaptörleri kuru sahte; kapı sahte (Git'e commit/push yok). Gerçek `bot_data.db` değişmedi (sha aynı); kopyaya bir kayıt eklendi (event_id 270).

```
[PREP] event: ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bus
[PREP] generation_type: source_fallback:http_error:structured | parts: 2
[DRY] gate authorized event_id=270 (no git checkpoint)
[DRY] telegram would post 470 chars, image=yes
[DRY] threads would post 2 parts
[PUBLISH] stopped: No platform main artifact was confirmed; reconciliation required
```

- Üretim tipi: `source_fallback:http_error:structured`; görsel: `wikipedia_thumbnail`.
- Yayın sonucu: `stopped: No platform main artifact was confirmed; reconciliation required`. Kuru adaptörler `dry_run` döndürdüğü için kod bunu onaylı ana gönderi saymadı; beklenen davranış.
- Kuru çıktı (Telegram/Threads kısmı):

> 🕊️ Tarihte Bugün (7.11.2000)
> 
> ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bush'tan daha fazla oy almasına rağmen, hayli tartışmalı bir belirsizlik döneminden sonra, ABD Yüksek Mahkemesi'nin kararıyla, George W. Bush 12 Aralık 2000'de Başkan ilan edildi. #tarih
> Bu ayrıntıyı daha önce duymuş muydunuz?
