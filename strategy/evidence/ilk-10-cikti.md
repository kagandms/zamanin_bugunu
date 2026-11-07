# İlk 10 canlı çıktı (7 Kasım, kaynağa bağlı yorum, yayın yok)

Bu dosya yalnızca inceleme içindir. Yayın yapılmadı, veritabanına yazılmadı. Üretim açılmadan önce onay bekler.

Kaskad: `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-26b-a4b-it:free` → `openrouter/free`. Çağrılar arasında 20 sn bekleme.

Sonuç: 0/10 olay model çıktısıyla üretildi, 10 olay fallback'e düştü.

| # | Olay | Durum | Model | Denemeler |
|---|---|---|---|---|
| 1 | 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Ke | fallback: unsupported_words,rate_limited,empty_response | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 2 | Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti. | fallback: unsupported_name,unsupported_words,rate_limited,empty_response | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 3 | ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bus | fallback: unsupported_name,unsupported_words,rate_limited,format,length,unsupported_number | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 4 | Birleşik Devletler kuvvetleri ile Şavniler arasında Tippecanoe Muharebesi gerçekleşti. | fallback: unsupported_number,unsupported_name,unsupported_words,rate_limited,empty_respons | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 5 | Lev Troçki, Rus Bolşevik siyasetçi, devrimci ve Marksist teorisyen (1917 Rus devriminin ön | fallback: unsupported_number,unsupported_name,unsupported_words,rate_limited,empty_respons | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 6 | Richard Nixon ABD Başkanı seçildi. | fallback: unsupported_words,rate_limited,empty_response | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 7 | Brad Harris, Amerikalı oyuncu, dublör ve yapımcı (d. 1933) | fallback: unsupported_words,rate_limited,empty_response | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 8 | Ögeday Han, Moğol İmparatoru ve Cengiz Han'ın oğlu (ö. 1241) | fallback: unsupported_words,rate_limited,empty_response | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 9 | Barbara Liskov, Amerikalı bilgisayar bilimcisi | fallback: rate_limited,time_budget | - | nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429 |
| 10 | Joe Frazier, Amerikalı boksör ve Dünya ağır sıklet profesyonel boks şampiyonlarından (d. 1 | fallback: rate_limited,time_budget | - | nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=429, google/gemma-4-31b-it:free=429, google/gemma-4-31b-it:free=429 |

## 1. 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Kenan Evren, Türkiye'nin 7. Cumhurbaşkanı oldu.

- Yıl: 1982
- Kaynak özeti: Dönemin Devlet Başkanı Kenan Evren, Anayasa'nın ilk üç maddesinin "değiştirilemeyeceğini ve değiştirilmesinin teklif edilemeyeceğini" dördüncü madde olarak taslağa ekletmiştir. Anayasa, 7 Kasım 1982 Pazar günü yapılan halk oylaması sonucu yüzde 91,37 oranında kabul oyu ile kabul edilmiştir.
- Üretim tipi: `source_fallback:unsupported_words,rate_limited,empty_response:structured`
- Model: -
- Ret nedeni: unsupported_words,rate_limited,empty_response

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 1982 Anayasası, 7 Kasım 1982'de yapılan halk oylamasında yüzde 91,37 kabul oyuyla onaylandı; Kenan Evren Türkiye'nin 7. Cumhurbaşkanı oldu. #tarih ⏎ --- ⏎ Kenan Evren, anayasa taslağının dördüncü maddesine ilk üç maddenin değiştirilemeyeceğini ve değiştirilmesinin teklif edilemeyec
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: 

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1982)
> 
> 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Kenan Evren, Türkiye'nin 7. Cumhurbaşkanı oldu. Anayasa, 7 Kasım 1982 Pazar günü yapılan halk oylaması sonucu yüzde 91,37 oranında kabul oyu ile kabul edilmiştir. #tarih
>
> Bu olayı daha önce duymuş muydunuz?

## 2. Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti.

- Yıl: 656
- Kaynak özeti: Cemel Muharebesi, Cemel Vakası, Basra Savaşı ya da Deve Olayı 8 Aralık 656 tarihinde, Halife Ali bin Ebu Talib ile İslam Peygamberi Muhammed'in dul eşi Aişe'nin taraftarları arasında, Basra'da gerçekleşen muharebe. Müslümanlar arasındaki ilk iç savaştır. Cemel Savaşı, Ali'nin zaferiyle sonuçlandı.
- Üretim tipi: `source_fallback:unsupported_name,unsupported_words,rate_limited,empty_response:structured`
- Model: -
- Ret nedeni: unsupported_name,unsupported_words,rate_limited,empty_response

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ 8 Aralık 656'da Basra'da, Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı, Halife Ali bin Ebu Talib ile Hz. Muhammed'in dul eşi Aişe'nin taraftarları arasında gerçekleşti. #tarih ⏎ --- ⏎ Muharebe Ali'nin zaferiyle sonuçlandı; bu çatışma Cemel Muharebesi, Cemel Vakası, Basra S
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: 

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.656)
> 
> Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti. Cemel Muharebesi, Cemel Vakası, Basra Savaşı ya da Deve Olayı 8 Aralık 656 tarihinde, Halife Ali bin Ebu Talib ile İslam Peygamberi Muhammed'in dul eşi Aişe'nin taraftarları arasında, Basra'da gerçekleşen muharebe. #tarih
>
> Bu olayı daha önce duymuş muydunuz?

## 3. ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bush'tan daha fazla oy almasına rağmen, hayli tartışmalı bir belirsizlik döneminden sonra, ABD Yüksek Mahkemesi'nin kararıyla, George W. Bush 12 Aralık 2000'de Başkan ilan edildi.

- Yıl: 2000
- Kaynak özeti: Bush'un en büyük oğlu olan Cumhuriyetçi aday Teksas Valisi George W. Bush, Demokrat Başkan Yardımcısı Al Gore'u ufak bir farkla yenerek ABD'nin 43. Seçimi kaybeden aday Al Gore, Yüksek Mahkemenin seçim hakkındaki kararını açıklamasından sonra 13 Aralık'ta Bush'u tebrik etti.
- Üretim tipi: `source_fallback:unsupported_name,unsupported_words,rate_limited,format,length,unsupported_number:structured`
- Model: -
- Ret nedeni: unsupported_name,unsupported_words,rate_limited,format,length,unsupported_number

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ Daha fazla oy almasına rağmen Al Gore, Yüksek Mahkemesi'nin kararıyla George W. Bush 12 Aralık 2000'de başkan ilan edildi. #tarih ⏎ --- ⏎ Florida'daki sayım tartışmaları ve Yüksek Mahkemesi'nin müdahalesiyle sürecin seyri değişti; Gore 13 Aralık'ta Bush'u tebrik ederek süreci kapat
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: 1.  **Analyze the Request:** ⏎     *   **Role:** Turkish historical content writer. ⏎     *   **Target Audience:** Turkey, history-loving adults, ages 25-55. ⏎     *   **Task:** Transform "Kaynak olay" (source event) and "Kaynak özeti" (source summary) into an engaging article that stops the reader'

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.2000)
> 
> ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bush'tan daha fazla oy almasına rağmen, hayli tartışmalı bir belirsizlik döneminden sonra, ABD Yüksek Mahkemesi'nin kararıyla, George W. Bush 12 Aralık 2000'de Başkan ilan edildi. Seçimi kaybeden aday Al Gore, Yüksek Mahkemenin seçim hakkındaki kararını açıklamasından sonra 13 Aralık'ta Bush'u tebrik etti. #tarih
>
> Bu olayı daha önce duymuş muydunuz?

## 4. Birleşik Devletler kuvvetleri ile Şavniler arasında Tippecanoe Muharebesi gerçekleşti.

- Yıl: 1811
- Kaynak özeti: Tippecanoe Muharebesi, 7 Kasım 1811 tarihinde Indiana Toprakları(Indiana Territory) Valisi William Henry Harrison kumandasındaki Birleşik Devletler kuvvetleri ve Shawnee kabilesinin lideri Tecumseh ile bağlantılı Kızılderili savaşçılar arasında yapılan bir muharebedir. Gerilim ve şiddet arttıkça, Vali Harrison konfederasyonun Prophetstown'daki merkezini dağıtmak için yaklaşık 1.000 kişilik bir orduyla Tippecanoe ve Wabash nehirlerinin birleştiği noktaya yürüdü.
- Üretim tipi: `source_fallback:unsupported_number,unsupported_name,unsupported_words,rate_limited,empty_respons:structured`
- Model: -
- Ret nedeni: unsupported_number,unsupported_name,unsupported_words,rate_limited,empty_respons

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ 1811'de Indiana topraklarında, Vali William Harrison'ın komutasındaki ABD kuvvetleri ile Tecumseh'in konfederasyonuna bağlı Kızılderili savaşçıları Tippecanoe Muharebesi'nde karşı karşıya geldi. #tarih ⏎ --- ⏎ Harrison, gerilim artarken Prophetstown merkezini dağıtmak amacıyla yakl
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: 

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1811)
> 
> Birleşik Devletler kuvvetleri ile Şavniler arasında Tippecanoe Muharebesi gerçekleşti. Tippecanoe Muharebesi, 7 Kasım 1811 tarihinde Indiana Toprakları(Indiana Territory) Valisi William Henry Harrison kumandasındaki Birleşik Devletler kuvvetleri ve Shawnee kabilesinin lideri Tecumseh ile bağlantılı Kızılderili savaşçılar arasında yapılan bir muharebedir. #tarih
>
> Bu olayı daha önce duymuş muydunuz?

## 5. Lev Troçki, Rus Bolşevik siyasetçi, devrimci ve Marksist teorisyen (1917 Rus devriminin önde gelen isimlerinden) (ö. 1940)

- Yıl: 1879
- Kaynak özeti: Lev Davidoviç Bronştayn ya da yaygın bilinen adıyla Lev Troçki ; Rus devrimci, Sovyet siyasetçi ve siyasi teorisyendir. İdeolojik olarak bir Marksist ve Leninist olan Troçki'nin fikirleri, Troçkizm olarak bilinen bir Marksizm düşüncesine ilham oldu.
- Üretim tipi: `source_fallback:unsupported_number,unsupported_name,unsupported_words,rate_limited,empty_respons:structured`
- Model: -
- Ret nedeni: unsupported_number,unsupported_name,unsupported_words,rate_limited,empty_respons

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🌍 ⏎ --- ⏎ 1940'ta Meksika'da bir buz kazmasıyla öldürülen Lev Troçki, ölümünden tam 23 yıl önce 1917 Rus Devrimi'ni örgütleyen komutanlardandı. #tarih ⏎ --- ⏎ Yaygın adı Lev Troçki olan Lev Davidoviç Bronştayn, Rus devrimci, Sovyet siyasetçi ve siyasi teorisyendir. İdeolojik olarak bir Marksi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: 

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1879)
> 
> Lev Troçki, Rus Bolşevik siyasetçi, devrimci ve Marksist teorisyen (1917 Rus devriminin önde gelen isimlerinden) (ö. 1940). Lev Davidoviç Bronştayn ya da yaygın bilinen adıyla Lev Troçki ; Rus devrimci, Sovyet siyasetçi ve siyasi teorisyendir. #tarih
>
> Bu olayı daha önce duymuş muydunuz?

## 6. Richard Nixon ABD Başkanı seçildi.

- Yıl: 1972
- Kaynak özeti: 1972 Amerika Birleşik Devletleri başkanlık seçimleri, 7 Kasım 1972 tarihinde Mevcut Cumhuriyetçi Başkan Richard Nixon ile Demokrat aday Güney Dakota Senatörü George McGovern arasında gerçekleşti. Seçimleri oyların büyük çoğunluğunu alan mevcut Cumhuriyetçi Başkan Richard Nixon kazandı.
- Üretim tipi: `source_fallback:unsupported_words,rate_limited,empty_response:structured`
- Model: -
- Ret nedeni: unsupported_words,rate_limited,empty_response

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🌍 ⏎ --- ⏎ 1972 seçimlerinde Richard Nixon, rakibi George McGovern'a karşı oyların büyük çoğunluğunu alarak ABD Başkanı seçildi. #tarih ⏎ --- ⏎ 7 Kasım 1972 tarihinde gerçekleşen seçimde Mevcut Cumhuriyetçi Başkan Richard Nixon, Demokrat aday Güney Dakota Senatörü George McGovern ile yarışmış 
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: 

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1972)
> 
> Richard Nixon ABD Başkanı seçildi. 1972 Amerika Birleşik Devletleri başkanlık seçimleri, 7 Kasım 1972 tarihinde Mevcut Cumhuriyetçi Başkan Richard Nixon ile Demokrat aday Güney Dakota Senatörü George McGovern arasında gerçekleşti. #tarih
>
> Bu olayı daha önce duymuş muydunuz?

## 7. Brad Harris, Amerikalı oyuncu, dublör ve yapımcı (d. 1933)

- Yıl: 2017
- Kaynak özeti: Bradford Harris, Amerikalı oyuncu, dublör ve yapımcıdır. Harris önceleri dublörlük yapmış daha sonra André de Toth's Monkey on My Back ve Li'l Abner adlı filmlerle ilk defa beyazperdede yer alarak oyunculuğa adım attı.
- Üretim tipi: `source_fallback:unsupported_words,rate_limited,empty_response:structured`
- Model: -
- Ret nedeni: unsupported_words,rate_limited,empty_response

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ Brad Harris, dublörlük kariyerinin ardından André de Toth'un *Monkey on My Back* ve *Li'l Abner* filmleriyle beyazperdeye oyuncu olarak adım attı. #tarih ⏎ --- ⏎ Amerikalı oyuncu, dublör ve yapımcı Bradford Harris, 1933'te doğdu ve 2017'de hayatını kaybetti. Dublörlükle başlayan kar
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: 

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.2017)
> 
> Brad Harris, Amerikalı oyuncu, dublör ve yapımcı (d. 1933). Bradford Harris, Amerikalı oyuncu, dublör ve yapımcıdır. #tarih
>
> Bu olayı daha önce duymuş muydunuz?

## 8. Ögeday Han, Moğol İmparatoru ve Cengiz Han'ın oğlu (ö. 1241)

- Yıl: 1186
- Kaynak özeti: Ögeday, Moğol İmparatorluğu'nun ikinci hanı ve Cengiz Han'ın üçüncü oğluydu. 1186 yılında doğan Ögeday, babasının iktidara gelmesi sırasında birçok savaşta savaştı ve Moğolların Harzemşah İmparatorluğu'nu işgalinde önemli roller üstlendi.
- Üretim tipi: `source_fallback:unsupported_words,rate_limited,empty_response:structured`
- Model: -
- Ret nedeni: unsupported_words,rate_limited,empty_response

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ 1186'da doğan Ögeday, babası Cengiz Han'ın iktidara gelişinde savaştı ve Harzemşah İmparatorluğu'nun yıkılmasında kilit rol oynadı; 1241'de vefat edene kadar Moğol İmparatorluğu'nun ikinci hanı olarak tahttı. #tarih ⏎ --- ⏎ Cengiz Han'ın üçüncü oğlu olan Ögeday, babasının mirasını 
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: 

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1186)
> 
> Ögeday Han, Moğol İmparatoru ve Cengiz Han'ın oğlu (ö. 1241). Ögeday, Moğol İmparatorluğu'nun ikinci hanı ve Cengiz Han'ın üçüncü oğluydu. #tarih
>
> Bu olayı daha önce duymuş muydunuz?

## 9. Barbara Liskov, Amerikalı bilgisayar bilimcisi

- Yıl: 1939
- Kaynak özeti: Barbara Liskov, Amerikalı bilgisayar bilimcisi. Massachusetts Teknoloji Enstitüsü'nde profesör olarak çalışan Liskov Amerika Birleşik Devletleri'nde bilgisayar bilimi doktorası sahibi ilk kadınlardan biridir.
- Üretim tipi: `source_fallback:rate_limited,time_budget:structured`
- Model: -
- Ret nedeni: rate_limited,time_budget

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1939)
> 
> Barbara Liskov, Amerikalı bilgisayar bilimcisi. Massachusetts Teknoloji Enstitüsü'nde profesör olarak çalışan Liskov Amerika Birleşik Devletleri'nde bilgisayar bilimi doktorası sahibi ilk kadınlardan biridir. #tarih
>
> Bu olayı daha önce duymuş muydunuz?

## 10. Joe Frazier, Amerikalı boksör ve Dünya ağır sıklet profesyonel boks şampiyonlarından (d. 1944)

- Yıl: 2011
- Kaynak özeti: Joe Frazier ile Muhammed Ali'nin rekabetleri boks tarihinin en büyük rekabeti olarak bilinir ve Ali ile Frazier'ın Filipinler'in başkenti Manila'da yaptıkları son maç hâlâ dünyadaki en büyük boks maçı olarak kabul edilir.
- Üretim tipi: `source_fallback:rate_limited,time_budget:structured`
- Model: -
- Ret nedeni: rate_limited,time_budget

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day","code":429,"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0","X-RateLimit-Reset":"1794096000000"},"limit_source":"openrouter_free_tier_daily","remedy_hi

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.2011)
> 
> Joe Frazier, Amerikalı boksör ve Dünya ağır sıklet profesyonel boks şampiyonlarından (d. 1944). Joe Frazier ile Muhammed Ali'nin rekabetleri boks tarihinin en büyük rekabeti olarak bilinir ve Ali ile Frazier'ın Filipinler'in başkenti Manila'da yaptıkları son maç hâlâ dünyadaki en büyük boks maçı olarak kabul edilir. #tarih
>
> Bu olayı daha önce duymuş muydunuz?
