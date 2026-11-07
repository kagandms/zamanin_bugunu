# İlk 10 canlı çıktı (7 Kasım, kaynağa bağlı yorum, yayın yok)

Bu dosya yalnızca inceleme içindir. Yayın yapılmadı, veritabanına yazılmadı. Üretim açılmadan önce onay bekler.

Kaskad: `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-26b-a4b-it:free` → `openrouter/free`. Çağrılar arasında 20 sn bekleme.

Sonuç: 1/10 olay model çıktısıyla üretildi, 9 olay fallback'e düştü.

| # | Olay | Durum | Model | Denemeler |
|---|---|---|---|---|
| 1 | ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bus | geçti | nvidia/nemotron-3.5-super-vl:free | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 2 | Birleşik Devletler kuvvetleri ile Şavniler arasında Tippecanoe Muharebesi gerçekleşti. | fallback: unsupported_name,unsupported_words,http_error,unsupported_number | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 3 | 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Ke | fallback: unsupported_words,http_error | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 4 | Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti. | fallback: unsupported_words,http_error | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=400 |
| 5 | Lev Troçki, Rus Bolşevik siyasetçi, devrimci ve Marksist teorisyen (1917 Rus devriminin ön | fallback: unsupported_number,unsupported_name,unsupported_words,http_error | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 6 | Richard Nixon ABD Başkanı seçildi. | fallback: length,unsupported_number,unsupported_name,unsupported_words,http_error | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=400 |
| 7 | Ögeday Han, Moğol İmparatoru ve Cengiz Han'ın oğlu (ö. 1241) | fallback: length,unsupported_number,unsupported_name,unsupported_words,http_error | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 8 | Brad Harris, Amerikalı oyuncu, dublör ve yapımcı (d. 1933) | fallback: unsupported_name,unsupported_words,http_error | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=400 |
| 9 | Barbara Liskov, Amerikalı bilgisayar bilimcisi | fallback: unsupported_number,unsupported_name,unsupported_words,http_error | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=400 |
| 10 | Joe Frazier, Amerikalı boksör ve Dünya ağır sıklet profesyonel boks şampiyonlarından (d. 1 | fallback: length,unsupported_number,unsupported_name,unsupported_words,http_error | - | nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-31b-it:free=429, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |

## 1. ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bush'tan daha fazla oy almasına rağmen, hayli tartışmalı bir belirsizlik döneminden sonra, ABD Yüksek Mahkemesi'nin kararıyla, George W. Bush 12 Aralık 2000'de Başkan ilan edildi.

- Yıl: 2000
- Kaynak özeti: Bush'un en büyük oğlu olan Cumhuriyetçi aday Teksas Valisi George W. Bush, Demokrat Başkan Yardımcısı Al Gore'u ufak bir farkla yenerek ABD'nin 43. Seçimi kaybeden aday Al Gore, Yüksek Mahkemenin seçim hakkındaki kararını açıklamasından sonra 13 Aralık'ta Bush'u tebrik etti.
- Üretim tipi: `ai_source_bound`
- Model: nvidia/nemotron-3.5-super-vl:free
- Ret nedeni: -

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ Daha fazla oy almasına rağmen Beyaz Saray'ın kapısı kapandı; 537 oyun ve Yüksek Mahkemenin 5-4'lük kararıyla kader değişti. 12 Aralık 2000'de George W. Bush, tarihî bir hukuki mücadelenin sonucunda 43. Başkan ilan edildi. #tarih ⏎ --- ⏎ Florida'daki tekrar sayım süreci, "karanlık o
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ Al Gore, George W. Bush'tan daha fazla oy aldı. #tarih ⏎ --- ⏎ Bush'un en büyük oğlu olan Cumhuriyetçi aday Teksas Valisi George W. Bush, Demokrat Başkan Yardımcısı Al Gore'u ufak bir farkla yenerek ABD'nin 43. Seçimi kaybeden aday Al Gore, Yüksek Mahkemenin seçim hakkındaki kararı

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🏛️ Tarihte Bugün (7.11.2000)
> 
> Al Gore, George W. Bush'tan daha fazla oy aldı. #tarih
>
> Bush'un en büyük oğlu olan Cumhuriyetçi aday Teksas Valisi George W. Bush, Demokrat Başkan Yardımcısı Al Gore'u ufak bir farkla yenerek ABD'nin 43. Seçimi kaybeden aday Al Gore, Yüksek Mahkemenin seçim hakkındaki kararını açıklamasından sonra 13 Aralık'ta Bush'u tebrik etti.
>
> Bu olayı daha önce duymuş muydunuz?

## 2. Birleşik Devletler kuvvetleri ile Şavniler arasında Tippecanoe Muharebesi gerçekleşti.

- Yıl: 1811
- Kaynak özeti: Tippecanoe Muharebesi, 7 Kasım 1811 tarihinde Indiana Toprakları(Indiana Territory) Valisi William Henry Harrison kumandasındaki Birleşik Devletler kuvvetleri ve Shawnee kabilesinin lideri Tecumseh ile bağlantılı Kızılderili savaşçılar arasında yapılan bir muharebedir. Gerilim ve şiddet arttıkça, Vali Harrison konfederasyonun Prophetstown'daki merkezini dağıtmak için yaklaşık 1.000 kişilik bir orduyla Tippecanoe ve Wabash nehirlerinin birleştiği noktaya yürüdü.
- Üretim tipi: `source_fallback:unsupported_name,unsupported_words,http_error,unsupported_number:source_context`
- Model: -
- Ret nedeni: unsupported_name,unsupported_words,http_error,unsupported_number

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ 1811'in kasım ayı, Indiana topraklarının soğuk bir sabahında Prophetstown'ın sessizliği birden patladı; Vali Harrison'ın 1.000 adamlık ordusu, Tecumseh'in kardeşi Tenskwatawa'nın koruduğu konfederasyon merkezini dağıtmak için nehir birleşiminde konuldu. #tarih ⏎ --- ⏎ Harrison'ın p
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ 1811'in kasım ayı, Indiana topraklarının soğuk bir sabahında Prophetstown'ın sessizliği birdenbire koptu; Vali Harrison'ın 1.000 kişilik ordusu, Tecumseh'in kardeşi Tenskwatawa'nın koruduğu konfederasyon merkezini dağıtmak için nehir birleşiminde konumu almıştı. #tarih ⏎ --- ⏎ Harr

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1811)
> 
> Birleşik Devletler kuvvetleri ile Şavniler arasında Tippecanoe Muharebesi gerçekleşti.
>
> Kaynak özeti: Tippecanoe Muharebesi, 7 Kasım 1811 tarihinde Indiana Toprakları(Indiana Territory) Valisi William Henry Harrison kumandasındaki Birleşik Devletler kuvvetleri ve Shawnee kabilesinin lideri Tecumseh ile bağlantılı Kızılderili savaşçılar arasında yapılan bir muharebedir.

## 3. 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Kenan Evren, Türkiye'nin 7. Cumhurbaşkanı oldu.

- Yıl: 1982
- Kaynak özeti: Dönemin Devlet Başkanı Kenan Evren, Anayasa'nın ilk üç maddesinin "değiştirilemeyeceğini ve değiştirilmesinin teklif edilemeyeceğini" dördüncü madde olarak taslağa ekletmiştir. Anayasa, 7 Kasım 1982 Pazar günü yapılan halk oylaması sonucu yüzde 91,37 oranında kabul oyu ile kabul edilmiştir.
- Üretim tipi: `source_fallback:unsupported_words,http_error:thin_source`
- Model: -
- Ret nedeni: unsupported_words,http_error

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 7 Kasım 1982 Pazar günü, sandıklar bir anayasayı değil, geleceğin kilidini açıyordu. Oy kullanma oranı %91,37; "KABUL" kutucuğu, değiştirilemez maddelerle birlikte ülkenin yeni sözleşmesi haline gelmişti. #tarih ⏎ --- ⏎ Kenan Evren, taslağın dördüncü maddesine anayasanın ilk üç mad
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🕊️ ⏎ --- ⏎ Halk oylaması günü, 7 Kasım 1982 Pazar günü, Türkiye, yeni anayasa üzerinde oylama yapmak için sandık başına gitti. Kenan Evren, %91,37 oranında "KABUL" oyuyla onaylanan belgenin arkasında duran isimdi ve bu sonuç, onu ülkenin yedinci cumhurbaşkanı ilan etti. #tarih ⏎ --- ⏎ Dördünc

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1982)
> 
> 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Kenan Evren, Türkiye'nin 7. Cumhurbaşkanı oldu.

## 4. Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti.

- Yıl: 656
- Kaynak özeti: Cemel Muharebesi, Cemel Vakası, Basra Savaşı ya da Deve Olayı 8 Aralık 656 tarihinde, Halife Ali bin Ebu Talib ile İslam Peygamberi Muhammed'in dul eşi Aişe'nin taraftarları arasında, Basra'da gerçekleşen muharebe. Müslümanlar arasındaki ilk iç savaştır. Cemel Savaşı, Ali'nin zaferiyle sonuçlandı.
- Üretim tipi: `source_fallback:unsupported_words,http_error:source_context`
- Model: -
- Ret nedeni: unsupported_words,http_error

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ İslam tarihinde ilk kez mümin müminin kanını dökdüğü gün, bir deve sırtında taşınan huzur bozulmuştu. 8 Aralık 656'da Basra çöllerinde Ali ile Aişe taraftarları birbirine karıştı. #tarih ⏎ --- ⏎ Cemel Muharebesi, Cemel Vakası ya da Deve Olayı olarak da anılan bu çatışma, Halife Ali
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 400: {"error":{"message":"Reasoning is mandatory for this endpoint and cannot be disabled.","code":400,"metadata":{"provider_name":null}}}

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.656)
> 
> Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti.
>
> Kaynak özeti: Cemel Muharebesi, Cemel Vakası, Basra Savaşı ya da Deve Olayı 8 Aralık 656 tarihinde, Halife Ali bin Ebu Talib ile İslam Peygamberi Muhammed'in dul eşi Aişe'nin taraftarları arasında, Basra'da gerçekleşen muharebe.

## 5. Lev Troçki, Rus Bolşevik siyasetçi, devrimci ve Marksist teorisyen (1917 Rus devriminin önde gelen isimlerinden) (ö. 1940)

- Yıl: 1879
- Kaynak özeti: Lev Davidoviç Bronştayn ya da yaygın bilinen adıyla Lev Troçki ; Rus devrimci, Sovyet siyasetçi ve siyasi teorisyendir. İdeolojik olarak bir Marksist ve Leninist olan Troçki'nin fikirleri, Troçkizm olarak bilinen bir Marksizm düşüncesine ilham oldu.
- Üretim tipi: `source_fallback:unsupported_number,unsupported_name,unsupported_words,http_error:thin_source`
- Model: -
- Ret nedeni: unsupported_number,unsupported_name,unsupported_words,http_error

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 1917'de Petrograd Sovyeti'ni yöneten ve Kızıl Ordusu'nu kuran adam, son yıllarını Meksika'da bir soyguncunun buz ucu ile geçirdi. Troçki, devrimin mimarlarından birinden Stalin'in en istenmeyen rakibine dönüşmüştü. #tarih ⏎ --- ⏎ Troçki, 1917 Rus Devrimi'nde Bolşeviklerin güce gelm
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ Lev Troçki, 1917 Rus devriminin önde gelen isimlerinden biri olarak (ö. 1940) (1879) Bolşevik siyasetçi, devrimci ve Marksist teorisyen olarak hayatını kaybetti. #tarih ⏎ --- ⏎ Troçki, Marksist ve Leninist olarak, Troçkizm olarak bilinen bir Marksizm düşüncesine ilham veren fikirler

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1879)
> 
> Lev Troçki, Rus Bolşevik siyasetçi, devrimci ve Marksist teorisyen (1917 Rus devriminin önde gelen isimlerinden) (ö. 1940)

## 6. Richard Nixon ABD Başkanı seçildi.

- Yıl: 1972
- Kaynak özeti: 1972 Amerika Birleşik Devletleri başkanlık seçimleri, 7 Kasım 1972 tarihinde Mevcut Cumhuriyetçi Başkan Richard Nixon ile Demokrat aday Güney Dakota Senatörü George McGovern arasında gerçekleşti. Seçimleri oyların büyük çoğunluğunu alan mevcut Cumhuriyetçi Başkan Richard Nixon kazandı.
- Üretim tipi: `source_fallback:length,unsupported_number,unsupported_name,unsupported_words,http_error:thin_source`
- Model: -
- Ret nedeni: length,unsupported_number,unsupported_name,unsupported_words,http_error

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 1972 Kasım'ında Richard Nixon, rakibi George McGovern'a karşı tarihin en geniş seçim zaferlerinden birini kaydetti. Oyların neredeyse üçte ikisini alarak 49 eyaleti kazandı. #tarih ⏎ --- ⏎ Seçim kampanyası sırasında Watergate binasına yapılan baskın ve ardından gelen örtbas girişim
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 400: {"error":{"message":"Reasoning is mandatory for this endpoint and cannot be disabled.","code":400,"metadata":{"provider_name":null}}}

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1972)
> 
> Richard Nixon ABD Başkanı seçildi.

## 7. Ögeday Han, Moğol İmparatoru ve Cengiz Han'ın oğlu (ö. 1241)

- Yıl: 1186
- Kaynak özeti: Ögeday, Moğol İmparatorluğu'nun ikinci hanı ve Cengiz Han'ın üçüncü oğluydu. 1186 yılında doğan Ögeday, babasının iktidara gelmesi sırasında birçok savaşta savaştı ve Moğolların Harzemşah İmparatorluğu'nu işgalinde önemli roller üstlendi.
- Üretim tipi: `source_fallback:length,unsupported_number,unsupported_name,unsupported_words,http_error:thin_source`
- Model: -
- Ret nedeni: length,unsupported_number,unsupported_name,unsupported_words,http_error

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 1186 yılında doğan Ögeday, babası Cengiz Han hâlâ bir kabile önderiyken ilk savaşlarını verdi ve Harzemşah İmparatorluğu'nun yıkılmasında kilit rol oynadı. Daha sonra Moğol İmparatorluğu'nun ikinci hanı olarak tahta geçecekti. #tarih ⏎ --- ⏎ Cengiz Han'ın üçüncü oğlu olan Ögeday, b
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ Cengiz Han'ın üçüncü oğlu Ögeday, babasının gölgesinde büyümektense Harzemşah İmparatorluğu'nun yıkılışında kilit komutanlığını üstlenmişti. 1186'da doğan bu isim, Moğol İmparatorluğu'nun ikinci hanı olmadan çok önce, tarihin seyrini değiştiren seferlerin arkasındaydı. #tarih ⏎ ---

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1186)
> 
> Ögeday Han, Moğol İmparatoru ve Cengiz Han'ın oğlu (ö. 1241)

## 8. Brad Harris, Amerikalı oyuncu, dublör ve yapımcı (d. 1933)

- Yıl: 2017
- Kaynak özeti: Bradford Harris, Amerikalı oyuncu, dublör ve yapımcıdır. Harris önceleri dublörlük yapmış daha sonra André de Toth's Monkey on My Back ve Li'l Abner adlı filmlerle ilk defa beyazperdede yer alarak oyunculuğa adım attı.
- Üretim tipi: `source_fallback:unsupported_name,unsupported_words,http_error:thin_source`
- Model: -
- Ret nedeni: unsupported_name,unsupported_words,http_error

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ Bradford Harris, 1933'te doğmuş bir Amerikalı oyuncu, dublör ve yapımcıydı. Kariyerine dublörlükle başlayıp André de Toth'un "Monkey on My Back" ve "Li'l Abner" filmleriyle beyazperdeye geçti. #tarih ⏎ --- ⏎ Harris, dublörlük deneyimini oyunculuk ve yapımcılık alanlarına taşıyarak s
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 400: {"error":{"message":"Reasoning is mandatory for this endpoint and cannot be disabled.","code":400,"metadata":{"provider_name":null}}}

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.2017)
> 
> Brad Harris, Amerikalı oyuncu, dublör ve yapımcı (d. 1933)

## 9. Barbara Liskov, Amerikalı bilgisayar bilimcisi

- Yıl: 1939
- Kaynak özeti: Barbara Liskov, Amerikalı bilgisayar bilimcisi. Massachusetts Teknoloji Enstitüsü'nde profesör olarak çalışan Liskov Amerika Birleşik Devletleri'nde bilgisayar bilimi doktorası sahibi ilk kadınlardan biridir.
- Üretim tipi: `source_fallback:unsupported_number,unsupported_name,unsupported_words,http_error:thin_source`
- Model: -
- Ret nedeni: unsupported_number,unsupported_name,unsupported_words,http_error

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🔬 ⏎ --- ⏎ 1968'de bir kadın, ABD'de bilgisayar bilimi doktorası alıyordu; o dönemde bu alanın neredeyse tamamı erkekler tarafından işletiliyordu. Barbara Liskov, bu yolu açan isimlerden biri oldu. #tarih ⏎ --- ⏎ Massachusetts Teknoloji Enstitüsü'nde (MIT) profesörlüğe yükselen Liskov, program
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 400: {"error":{"message":"Reasoning is mandatory for this endpoint and cannot be disabled.","code":400,"metadata":{"provider_name":null}}}

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1939)
> 
> Barbara Liskov, Amerikalı bilgisayar bilimcisi

## 10. Joe Frazier, Amerikalı boksör ve Dünya ağır sıklet profesyonel boks şampiyonlarından (d. 1944)

- Yıl: 2011
- Kaynak özeti: Joe Frazier ile Muhammed Ali'nin rekabetleri boks tarihinin en büyük rekabeti olarak bilinir ve Ali ile Frazier'ın Filipinler'in başkenti Manila'da yaptıkları son maç hâlâ dünyadaki en büyük boks maçı olarak kabul edilir.
- Üretim tipi: `source_fallback:length,unsupported_number,unsupported_name,unsupported_words,http_error:thin_source`
- Model: -
- Ret nedeni: length,unsupported_number,unsupported_name,unsupported_words,http_error

**Denemeler:**

- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ Manila'nın o gece yarısı, iki dev birbirlerini yok etmeye çalışırken dünyanın nefesini kesecek bir sessizlik çökmüştü ringin etrafına. Frazier'ın gözü neredeyse tamamen kapanmışken köşesindeki adamlar "dur" diyememiş, Ali ise son gong çaldığında kendi köşesinde baygınlık içinde yat
- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🥊 ⏎  ⏎ --- ⏎  ⏎ 1970’lerin en büyük boks rakipleri, Manila’da bir araya geldiğinde tarih yazdı. Joe Frazier ve Muhammed Ali, sadece bir ringde değil, bir neslin hafızasında yer edindi. Üç maçtan oluşan bu serinin sonu, Filipinler’in başkenti Manila’da_pickled: “The Thrilla in Manila” olarak a

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.2011)
> 
> Joe Frazier, Amerikalı boksör ve Dünya ağır sıklet profesyonel boks şampiyonlarından (d. 1944)
