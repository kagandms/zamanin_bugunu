# İlk 10 canlı çıktı (7 Kasım, kaynağa bağlı yorum, yayın yok)

Bu dosya yalnızca inceleme içindir. Yayın yapılmadı, veritabanına yazılmadı. Üretim açılmadan önce onay bekler.

Kaskad: `google/gemma-4-31b-it:free` → `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-26b-a4b-it:free` → `openrouter/free`. Çağrılar arasında 20 sn bekleme.

Sonuç: 5/10 olay model çıktısıyla üretildi, 5 olay fallback'e düştü.

**İnceleme notu (üretim öncesi zorunlu):** Kabul edilen metinlerde otomatik kontrolün yakalamadığı kaynak dışı betimlemeler var:

- #3: "ülke tarihindeki en tartışmalı seçimler" (üstünlük iddiası), "bugün bile siyasi tartışmalara neden olmaya devam" (yeni olgu).
- #6: "Karaköse dağlarının ardında, … buzlu sabahında", "kapıları ateşe verilmemiş, sessizce açıldı" (uydurma sahne ayrıntısı).
- #9: "evlilik algısını gün yüzüne çıkardı", "Sizce … nasıl etkilemiş olabilir?" (kaynakta olmayan sonuç yorumu).
- #10: "hayatını kaybeden … nadir isimlerden biriydi" (kaynakta olmayan değerlendirme).

Sayı/ad/kalıp kontrolü bu tür uydurma sıfat ve sahneyi yakalamaz. Üretim açılmadan önce ya ek bir kural (sıfat ve sahne listesi, değerlendirme kalıpları) ya da insan incelemesi gerekir. Ayrıca kabul edilen 5 metnin 2'si (#3, #8) `openrouter/free` yönlendirmesiyle farklı bir modelden geldi; birincil model (`google/gemma-4-31b-it:free`) 10 denemede de 429 döndü.

| # | Olay | Durum | Model | Denemeler |
|---|---|---|---|---|
| 1 | 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Ke | fallback: http_error,unsupported_number,unsupported_name,banned_phrase,format | - | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 2 | Kâzım Koyuncu, Türk müzisyen, söz yazarı, oyuncu ve aktivist (ö. 2005) | fallback: http_error,unsupported_name | - | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 3 | ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bus | geçti | cohere/north-mini-code:free | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 4 | I. Dünya Savaşı: İngiliz kuvvetleri, Osmanlı Devleti idaresindeki Gazze'yi ele geçirdi. | fallback: http_error,unsupported_number | - | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 5 | Macar müzisyen Bela Bartok, Ankara Halkevi'nde konferans verdi. | fallback: http_error,unsupported_name | - | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-26b-a4b-it:free=429, openrouter/free=400 |
| 6 | Türk ordusu, Gümrü'yü ele geçirdi. | geçti | nvidia/nemotron-3-ultra-550b-a55b:free | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200 |
| 7 | Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti. | fallback: http_error,unsupported_name,banned_phrase | - | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 8 | İstanbul Zeyrek Camii'nde Bizans dönemi'nden kalma mozaikler bulundu. | geçti | nvidia/nemotron-3.5-super-vl:free | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200, google/gemma-4-26b-a4b-it:free=429, openrouter/free=200 |
| 9 | Uluslararası Evlilik Oluru, En Düşük Evlilik Yaşı ve Evliliklerin Yazımı Sözleşmesi imzala | geçti | nvidia/nemotron-3-ultra-550b-a55b:free | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200 |
| 10 | Besim Atalay, Türk dilbilimci, yazar ve politikacı (d. 1882) | geçti | nvidia/nemotron-3-ultra-550b-a55b:free | google/gemma-4-31b-it:free=429, nvidia/nemotron-3-ultra-550b-a55b:free=200 |

## 1. 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Kenan Evren, Türkiye'nin 7. Cumhurbaşkanı oldu.

- Yıl: 1982
- Kaynak özeti: Sağlanmadı.
- Üretim tipi: `source_fallback:http_error,unsupported_number,unsupported_name,banned_phrase,format:thin_source`
- Model: -
- Ret nedeni: http_error,unsupported_number,unsupported_name,banned_phrase,format

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 7 Kasım 1982'de sandık başına giden 17 milyon 700 bin vatandaş, önlerine konulan tek bir soruya "%91,37" oranında "Evet" diyerek Türkiye'nin yeni anayasasını ve ilk cumhurbaşkanını belirledi. #tarih ⏎ --- ⏎ Bu olayı daha önce bu oranlarla duymuş muydunuz? ⏎ GORSEL_PROMPT: A black a
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 1982'de Türkiye, yeni bir anayasa için ilk ve tek kez doğrudan halk oylamasına başvurdu. Anayasa, oyların %91,37'siyle kabul edildi. Ardından Kenan Evren, ülkenin 7. Cumhurbaşkanı olarak görevlendirildi. Bu olay, Türkiye'de anayasal değişimlerin nasıl happening olduğunu gösterirken

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1982)
> 
> 1982 Anayasası için halk oylaması yapıldı. Anayasa, %91,37 "KABUL" oyuyla kabul edildi. Kenan Evren, Türkiye'nin 7. Cumhurbaşkanı oldu.

## 2. Kâzım Koyuncu, Türk müzisyen, söz yazarı, oyuncu ve aktivist (ö. 2005)

- Yıl: 1971
- Kaynak özeti: Kâzım Koyuncu, Doğu Karadeniz ve Laz müziğini rock müziği ile sentezleyerek kendi tarzını oluşturan Laz asıllı Türk müzisyen, söz yazarı, oyuncu ve aktivisttir.
- Üretim tipi: `source_fallback:http_error,unsupported_name:source_context`
- Model: -
- Ret nedeni: http_error,unsupported_name

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ Lazca ezgiler elektriktar gitarlerle buluştuğunda, bir köy kasabası sesi birden bire tüm Anadolu'nun sokaklarına yayıldı. #tarih ⏎ --- ⏎ Bu olayı daha önce duymuştunuz mu?
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🎸 ⏎  ⏎ --- ⏎  ⏎ #tarih ⏎  ⏎ Doğu Karadeniz’in dağernelerinden gelen ses, rock’un sert ritmiyle buluşturdu Laz müziğini. Kâzım Koyuncu, geleneksel ezgileri elektrik gitarla buluşturarak hem kendi tarzını yarattı hem de bir kültürün sesini yeni nesillere taşıdı. Müzikten tiyatroya, sahneye soka

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1971)
> 
> Kâzım Koyuncu, Türk müzisyen, söz yazarı, oyuncu ve aktivist (ö. 2005)
>
> Kaynak özeti: Kâzım Koyuncu, Doğu Karadeniz ve Laz müziğini rock müziği ile sentezleyerek kendi tarzını oluşturan Laz asıllı Türk müzisyen, söz yazarı, oyuncu ve aktivisttir.

## 3. ABD'de Başkanlık seçimleri yapıldı. Demokrat aday Al Gore, Cumhuriyetçi aday George W. Bush'tan daha fazla oy almasına rağmen, hayli tartışmalı bir belirsizlik döneminden sonra, ABD Yüksek Mahkemesi'nin kararıyla, George W. Bush 12 Aralık 2000'de Başkan ilan edildi.

- Yıl: 2000
- Kaynak özeti: Sağlanmadı.
- Üretim tipi: `ai_source_bound`
- Model: cohere/north-mini-code:free
- Ret nedeni: -

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ Oyları kazanan aday, Başkan olamadı; 537 oyun ve Yüksek Mahkeme'nin 5-4'lük tek oylu kararıyla Beyaz Saray'ın sahibi belirlendi. #tarih ⏎ --- ⏎ Bu olayı bugün nasıl okuyorsunuz?
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🕊️ ⏎ --- ⏎ George W. Bush, 2000 yılındaki ABD başkanlık seçiminde rakibi Al Gore'dan daha fazla popüler oy aldığı halde, ülke tarihindeki en tartışmalı seçimler arasında yer alan bir belirsizlik döneminden sonra, Yüksek Mahkeme'nin kararıyla 12 Aralık 2000'de başkan ilan edildi. #tarih ⏎ --- 

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.2000)
> 
> George W. Bush, 2000 yılındaki ABD başkanlık seçiminde rakibi Al Gore'dan daha fazla popüler oy aldığı halde, ülke tarihindeki en tartışmalı seçimler arasında yer alan bir belirsizlik döneminden sonra, Yüksek Mahkeme'nin kararıyla 12 Aralık 2000'de başkan ilan edildi. #tarih
>
> Bu son derece yakın ve çalkantılı seçim sürecinin, bugün bile siyasi tartışmalara neden olmaya devam ediyor olması şaşırtıcı mı?

## 4. I. Dünya Savaşı: İngiliz kuvvetleri, Osmanlı Devleti idaresindeki Gazze'yi ele geçirdi.

- Yıl: 1917
- Kaynak özeti: Sağlanmadı.
- Üretim tipi: `source_fallback:http_error,unsupported_number:thin_source`
- Model: -
- Ret nedeni: http_error,unsupported_number

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ 1917 Kasım'ında İngiliz bayrakları Gazze'nin surları üzerinde dalgalanmaya başladı; 400 yıl süren Osmanlı hâkimiyeti bir gece içinde tarihe karıştı. #tarih ⏎ --- ⏎ Bu olayın bugün ne anlama geldiğini düşünürken aklınıza ne geliyor?
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🕊️ ⏎ --- ⏎ <bölüm 1; sonuna " #tarih" ekle> ⏎ --- ⏎ 1917, I. Dünya Savaşı'nın en kritik ve en az anlatılan yönlerinden biri olan Gazze kuzeyine yönelik bir Osmanlı savunma çöküşünün izini izliyor. İngiliz ordu'su, Osmanlı imparatorluğu'nun zayıf idaresine maruz kalmış bu kıyı şehrini, askeri 

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1917)
> 
> I. Dünya Savaşı: İngiliz kuvvetleri, Osmanlı Devleti idaresindeki Gazze'yi ele geçirdi.

## 5. Macar müzisyen Bela Bartok, Ankara Halkevi'nde konferans verdi.

- Yıl: 1936
- Kaynak özeti: Sağlanmadı.
- Üretim tipi: `source_fallback:http_error,unsupported_name:thin_source`
- Model: -
- Ret nedeni: http_error,unsupported_name

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ 1936'da Ankara Halkevi'ne adım atan Bela Bartok, piyanosunun başına geçip "Türk halk müziğini çaldım, siz de dinleyin" demedi; mikrofon başında durup, toplayıp notaladığı o ezgilerin *neden* o kadar farklı olduğunu, ritimlerinin nasıl kırıldığını anlattı. #tarih ⏎ --- ⏎ Bu olayı bug
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 400: {"error":{"message":"Reasoning is mandatory for this endpoint and cannot be disabled.","code":400,"metadata":{"provider_name":null}}}

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.1936)
> 
> Macar müzisyen Bela Bartok, Ankara Halkevi'nde konferans verdi.

## 6. Türk ordusu, Gümrü'yü ele geçirdi.

- Yıl: 1920
- Kaynak özeti: Sağlanmadı.
- Üretim tipi: `ai_source_bound`
- Model: nvidia/nemotron-3-ultra-550b-a55b:free
- Ret nedeni: -

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ Karaköse dağlarının ardında, 1920 kışının buzlu sabahında Türk ordusu Gümrü'ye girdi; şehrin kapıları ateşe verilmemiş, sessizce açıldı. #tarih ⏎ --- ⏎ Bu olayı bugün nasıl okuyorsunuz? ⏎ GORSEL_PROMPT: Early morning winter 1920, Turkish cavalry entering the stone gates of Kars (Gy

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> ⚔️ Tarihte Bugün (7.11.1920)
> 
> Karaköse dağlarının ardında, 1920 kışının buzlu sabahında Türk ordusu Gümrü'ye girdi; şehrin kapıları ateşe verilmemiş, sessizce açıldı. #tarih
>
> Bu olayı bugün nasıl okuyorsunuz?

## 7. Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti.

- Yıl: 656
- Kaynak özeti: Cemel Muharebesi, Cemel Vakası, Basra Savaşı ya da Deve Olayı 8 Aralık 656 tarihinde, Halife Ali bin Ebu Talib ile İslam Peygamberi Muhammed'in dul eşi Aişe'nin taraftarları arasında, Basra'da gerçekleşen muharebe. Cemel Savaşı, Ali'nin zaferiyle sonuçlandı.
- Üretim tipi: `source_fallback:http_error,unsupported_name,banned_phrase:source_context`
- Model: -
- Ret nedeni: http_error,unsupported_name,banned_phrase

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ 8 Aralık 656'da Basra çöllerinde, Peygamberin dul eşi Aişe ile halife Ali, Müslümanlar arasında ilk kez yüz yüze geldi. #tarih ⏎ --- ⏎ Muharebe, Aişe'nin bindiği deve (cemel) etrafında toplanan taraftarların ve Ali'nin ordusunun çarpışmasıyla şekillenmişti. Gündüz boyu süren çatışm
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ Ali bin Ebu Talib ile Aişe'nin taraftarları arasında Basra'da 8 Aralık 656 tarihinde gerçekleşen muharebe, Müslümanlar arasındaki ilk iç savaş olarak tarihe geçti. Cemel Savaşı, Ali'nin zaferiyle sonuçlandı. #tarih ⏎ --- ⏎ Bu muharebe, Cemel Muharebesi, Cemel Vakası, Basra Savaşı v

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🕊️ Tarihte Bugün (7.11.656)
> 
> Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti.
>
> Kaynak özeti: Cemel Muharebesi, Cemel Vakası, Basra Savaşı ya da Deve Olayı 8 Aralık 656 tarihinde, Halife Ali bin Ebu Talib ile İslam Peygamberi Muhammed'in dul eşi Aişe'nin taraftarları arasında, Basra'da gerçekleşen muharebe.

## 8. İstanbul Zeyrek Camii'nde Bizans dönemi'nden kalma mozaikler bulundu.

- Yıl: 1953
- Kaynak özeti: Sağlanmadı.
- Üretim tipi: `ai_source_bound`
- Model: nvidia/nemotron-3.5-super-vl:free
- Ret nedeni: -

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 1953'te Zeyrek Camii'nin tavanında, yüzyıllardır beyaz boyun altında saklı kalan Bizans mozaikleri ışığa çıktı. #tarih ⏎ --- ⏎ Bu keşif, binasın Pantokrator Manastırı olarak bilinen geçmişiyle doğrudan bağlantılıydı. Mozaikler, 12. yüzyıl Bizans sanayinin örneği olarak değerlendiri
- `google/gemma-4-26b-a4b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-26b-a4b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio
- `openrouter/free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 1953'te İstanbul Zeyrek Camii'nde Bizans dönemi mozaikleri bulundu. #tarih ⏎ --- ⏎ Sizce bu mozaikler bugün nasıl okunur?

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🏛️ Tarihte Bugün (7.11.1953)
> 
> 1953'te İstanbul Zeyrek Camii'nde Bizans dönemi mozaikleri bulundu. #tarih
>
> Sizce bu mozaikler bugün nasıl okunur?

## 9. Uluslararası Evlilik Oluru, En Düşük Evlilik Yaşı ve Evliliklerin Yazımı Sözleşmesi imzalandı. Türkiye bu sözleşmeyi onaylamadı.

- Yıl: 1962
- Kaynak özeti: Sağlanmadı.
- Üretim tipi: `ai_source_bound`
- Model: nvidia/nemotron-3-ultra-550b-a55b:free
- Ret nedeni: -

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 1962 yılında dünya genelinde evlilik yaşını sınırlayan bir uluslararası sözleşme imzalandı; Türkiye ise bu belgeyi onaylamadı. #tarih ⏎ --- ⏎ Bu sözleşmenin onaylanmaması, o dönemde medeni kanunlardaki evlilik yaş sınırları ile uluslararası standartlar arasındaki farkı gün yüzüne ç

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🏛️ Tarihte Bugün (7.11.1962)
> 
> 1962 yılında dünya genelinde evlilik yaşını sınırlayan bir uluslararası sözleşme imzalandı; Türkiye ise bu belgeyi onaylamadı. #tarih
>
> Bu sözleşmenin onaylanmaması, o dönemde medeni kanunlardaki evlilik yaş sınırları ile uluslararası standartlar arasındaki farkı gün yüzüne çıkardı.
>
> Sizce o yıllarda bu onaylanma kararı, toplumun evlilik algısını nasıl etkilemiş olabilir?

## 10. Besim Atalay, Türk dilbilimci, yazar ve politikacı (d. 1882)

- Yıl: 1965
- Kaynak özeti: Ahmet Besim Atalay, Türk dilbilimci, yazar ve siyasetçi.
- Üretim tipi: `ai_source_bound`
- Model: nvidia/nemotron-3-ultra-550b-a55b:free
- Ret nedeni: -

**Denemeler:**

- `google/gemma-4-31b-it:free` HTTP 429: {"error":{"message":"Provider returned error","code":429,"metadata":{"raw":"google/gemma-4-31b-it:free is temporarily rate-limited upstream. Please retry shortly, or add your own provider key to use your own limits: https://openrouter.ai/workspaces/default/byok","provider_name":"Google AI Studio","i
- `nvidia/nemotron-3-ultra-550b-a55b:free` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ 1965 yılında hayatını kaybeden Ahmet Besim Atalay, hem dilbilim hem siyaset alanında iz bırakan nadir isimlerden biriydi. Dilin yapısını çözümleyen bir zihnin, toplumun diliyle de uğraşması bir tesadüf değildi. #tarih ⏎ --- ⏎ Bu olayı daha önce duymuş muydunuz?

**Yayımlanacak metin (kod başlığı + model gövdesi):**

> 🏛️ Tarihte Bugün (7.11.1965)
> 
> 1965 yılında hayatını kaybeden Ahmet Besim Atalay, hem dilbilim hem siyaset alanında iz bırakan nadir isimlerden biriydi. Dilin yapısını çözümleyen bir zihnin, toplumun diliyle de uğraşması bir tesadüf değildi. #tarih
>
> Bu olayı daha önce duymuş muydunuz?
