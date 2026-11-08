# İlk 10 canlı çıktı (8 Kasım, yalnızca Gemini, yayın yok)

Bu dosya yalnızca inceleme içindir. Yayın yapılmadı, veritabanına yazılmadı. Üretim açılmadan önce onay bekler.

Kaskad: yalnızca Gemini (`GEMINI_MODEL`). OpenRouter'a hiç çağrı yapılmadı. Çağrılar arasında 20 sn bekleme.

Sonuç: 5/10 olay model çıktısıyla üretildi, 5 olay yapılandırılmış fallback'e düştü.

| # | Olay | Durum | Denemeler |
|---|---|---|---|
| 1 | II. Dünya Savaşı: Britanya İmparatorluğu ve ABD, Kuzey Afrika'da Cezayir ve Fas'ı işgal et | geçti | gemini-3.5-flash=200 |
| 2 | İkinci Dağlık Karabağ Savaşı'nda Azerbaycan güçleri Şuşa şehrini Ermeni işgalinden kurtard | geçti | gemini-3.5-flash=200 |
| 3 | Almanya'da Adolf Hitler ve yandaşları tarihe "Birahane Darbesi" olarak geçecek olan olayla | geçti | gemini-3.5-flash=200 |
| 4 | Robert Catesby, 1605'te, İngiliz parlamentosunu havaya uçurmak için bir araya gelen 12 kiş | fallback: unsupported_words | gemini-3.5-flash=200 |
| 5 | İngiliz Rock topluluğu Led Zeppelin'in 4. albümleri çıktı. Albümde grubun en çok bilinen ş | fallback: unsupported_words | gemini-3.5-flash=200 |
| 6 | Alfre Woodard, Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve siyasal eylemci | fallback: unsupported_words | gemini-3.5-flash=200 |
| 7 | Tatsuya Nakadai, Japon oyuncu (d. 1932) | fallback: unsupported_words | gemini-3.5-flash=200 |
| 8 | Montana, ABD'nin 41. Eyaleti oldu. | geçti | gemini-3.5-flash=200 |
| 9 | Felix Hausdorff, Alman matematikçi (ö. 1942) | geçti | gemini-3.5-flash=200 |
| 10 | ABD başkanlık seçimlerinde Cumhuriyetçi aday George H. W. Bush seçildi. | fallback: unsupported_words,language | gemini-3.5-flash=200 |

## 1. II. Dünya Savaşı: Britanya İmparatorluğu ve ABD, Kuzey Afrika'da Cezayir ve Fas'ı işgal ettiler.

- Yıl: 1942
- Kaynak özeti: Savaşa dönemin büyük güçleri ve dünya ülkelerinin büyük çoğunluğu katıldı, Müttefikler ve Mihver olmak üzere iki karşıt askerî ittifak kuruldu. 70 ila 85 milyon insanın ölümüyle sonuçlanan II. Dünya Savaşı, insanlık tarihindeki en ölümcül savaştı ve savaş boyunca askerî personelden daha çok sivil kayıp verildi.
- Üretim tipi: `ai_source_bound`
- Model: gemini-3.6-flash
- Ret nedeni: -

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ Britanya İmparatorluğu ve ABD, 1942 yılında Kuzey Afrika'da Cezayir ve Fas'ı işgal ettiler. #tarih ⏎ --- ⏎ Savaşa dönemin büyük güçleri ve dünya ülkelerinin büyük çoğunluğu katıldı; Müttefikler ve Mihver olmak üzere iki karşıt askerî ittifak kuruldu. 70 ila 85 milyon insanın ölümüy

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> ⚔️ Tarihte Bugün (8.11.1942)
> 
> Britanya İmparatorluğu ve ABD, 1942 yılında Kuzey Afrika'da Cezayir ve Fas'ı işgal ettiler. #tarih
>
> Savaşa dönemin büyük güçleri ve dünya ülkelerinin büyük çoğunluğu katıldı; Müttefikler ve Mihver olmak üzere iki karşıt askerî ittifak kuruldu. 70 ila 85 milyon insanın ölümüyle sonuçlanan II. Dünya Savaşı, insanlık tarihindeki en ölümcül savaştı ve savaş boyunca askerî personelden daha çok sivil kayıp verildi.
>
> Bu olayı bugün nasıl okuyorsunuz?

## 2. İkinci Dağlık Karabağ Savaşı'nda Azerbaycan güçleri Şuşa şehrini Ermeni işgalinden kurtardı. Bu tarih daha sonra Zafer Bayramı ilan edildi.

- Yıl: 2020
- Kaynak özeti: İkinci Dağlık Karabağ Savaşı, 2020 Dağlık Karabağ Savaşı veya 44 Günlük Savaş Dağlık Karabağ'da Türkiye destekli Azerbaycan ile Ermenistan ve onun desteklediği tanınmayan Dağlık Karabağ Cumhuriyeti arasında yaşanmış silahlı çatışmalardır.
- Üretim tipi: `ai_source_bound`
- Model: gemini-3.6-flash
- Ret nedeni: -

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ Azerbaycan güçleri, İkinci Dağlık Karabağ Savaşı'nda Şuşa şehrini Ermeni işgalinden kurtardı ve bu tarih daha sonra Zafer Bayramı ilan edildi. #tarih ⏎ --- ⏎ 2020 yılında yaşanan ve 44 Günlük Savaş olarak da bilinen İkinci Dağlık Karabağ Savaşı, Dağlık Karabağ'da gerçekleşti. Çatış

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> ⚔️ Tarihte Bugün (8.11.2020)
> 
> Azerbaycan güçleri, İkinci Dağlık Karabağ Savaşı'nda Şuşa şehrini Ermeni işgalinden kurtardı ve bu tarih daha sonra Zafer Bayramı ilan edildi. #tarih
>
> 2020 yılında yaşanan ve 44 Günlük Savaş olarak da bilinen İkinci Dağlık Karabağ Savaşı, Dağlık Karabağ'da gerçekleşti. Çatışmalar; Türkiye destekli Azerbaycan ile Ermenistan ve onun desteklediği tanınmayan Dağlık Karabağ Cumhuriyeti arasında yaşanmış silahlı çatışmalardır.
>
> Bu olayı bugün nasıl okuyorsunuz?

## 3. Almanya'da Adolf Hitler ve yandaşları tarihe "Birahane Darbesi" olarak geçecek olan olayla Bavyera eyaletinin yönetimini ele geçirmek için ayaklandı.

- Yıl: 1923
- Kaynak özeti: Birahane Darbesi, Adolf Hitler, General Erich Ludendorff ve diğer Kampfbund liderleri tarafından Bavyera eyaletinin yönetimine el koymak amacıyla 8-9 Kasım 1923 tarihinde gerçekleştirdiği başarısız bir darbe girişimidir.
- Üretim tipi: `ai_source_bound`
- Model: gemini-3.6-flash
- Ret nedeni: -

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ Adolf Hitler ve yandaşları, Bavyera eyaletinin yönetimini ele geçirmek için ayaklandı. #tarih ⏎ --- ⏎ Birahane Darbesi olarak geçen bu olay; Adolf Hitler, General Erich Ludendorff ve diğer Kampfbund liderleri tarafından Bavyera eyaletinin yönetimine el koymak amacıyla 8-9 Kasım 192

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> ⚔️ Tarihte Bugün (8.11.1923)
> 
> Adolf Hitler ve yandaşları, Bavyera eyaletinin yönetimini ele geçirmek için ayaklandı. #tarih
>
> Birahane Darbesi olarak geçen bu olay; Adolf Hitler, General Erich Ludendorff ve diğer Kampfbund liderleri tarafından Bavyera eyaletinin yönetimine el koymak amacıyla 8-9 Kasım 1923 tarihinde gerçekleştirdiği başarısız bir darbe girişimidir.
>
> Bu darbe girişimini daha önce duymuş muydunuz?

## 4. Robert Catesby, 1605'te, İngiliz parlamentosunu havaya uçurmak için bir araya gelen 12 kişilik "Barut Komplosu" ekibin lideri (d. 1572)

- Yıl: 1605
- Kaynak özeti: Barut komplosu, bir grup yönetim karşıtı İngiliz Katolik tarafından, İngiltere Kralı I. James ve diğer aristokratları öldürmek için 5 Kasım 1605'te yapılan, Parlamento binasını havaya uçurma girişimidir. Robert Catesby ve Guy Fawkes öncülüğünde planlanmıştır.
- Üretim tipi: `source_fallback:unsupported_words:structured`
- Model: -
- Ret nedeni: unsupported_words

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ İngiliz parlamentosunu havaya uçurmak için 12 kişilik bir ekip bir araya geldi; liderleri Robert Catesby idi. #tarih ⏎ --- ⏎ Barut komplosu, Robert Catesby ve Guy Fawkes öncülüğünde, İngiltere Kralı I. James ve diğer aristokratları öldürmek için 5 Kasım 1605'te yapılan bir Parlamen

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> 🕊️ Tarihte Bugün (8.11.1605)
> 
> Robert Catesby, 1605'te, İngiliz parlamentosunu havaya uçurmak için bir araya gelen 12 kişilik "Barut Komplosu" ekibin lideri (d. 1572). Barut komplosu, bir grup yönetim karşıtı İngiliz Katolik tarafından, İngiltere Kralı I. #tarih
>
> Bu ismi tanıyor muydunuz?

## 5. İngiliz Rock topluluğu Led Zeppelin'in 4. albümleri çıktı. Albümde grubun en çok bilinen şarkısı "Stairway to Heaven" var.

- Yıl: 1971
- Kaynak özeti: "Stairway to Heaven", İngiliz rock grubu Led Zeppelin tarafından 8 Kasım 1971'de piyasaya sürülen şarkı. Grubun gitaristi Jimmy Page ve vokalisti Robert Plant tarafından isimsiz dördüncü stüdyo albümleri için bestelenmiştir. Genellikle tüm zamanların en popüler rock şarkılarından biri olarak kabul edilmektedir.
- Üretim tipi: `source_fallback:unsupported_words:structured`
- Model: -
- Ret nedeni: unsupported_words

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ Led Zeppelin'in dördüncü stüdyo albümünde yer alan "Stairway to Heaven", tüm zamanların en popüler rock şarkılarından biri olarak kabul edilmektedir. #tarih ⏎ --- ⏎ İngiliz rock grubunun gitaristi Jimmy Page ve vokalisti Robert Plant tarafından isimsiz albüm için bestelenen eser, 8 

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> 🕊️ Tarihte Bugün (8.11.1971)
> 
> İngiliz Rock topluluğu Led Zeppelin'in 4. albümleri çıktı. Albümde grubun en çok bilinen şarkısı "Stairway to Heaven" var. Grubun gitaristi Jimmy Page ve vokalisti Robert Plant tarafından isimsiz dördüncü stüdyo albümleri için bestelenmiştir. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?

## 6. Alfre Woodard, Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve siyasal eylemci

- Yıl: 1952
- Kaynak özeti: Alfre Woodard, Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve siyasal eylemci. Woodard Akademi Ödülü ve Grammy Ödülü'ne birer kez aday gösterilmiş; 18 kez aday gösterildiği Emmy Ödülü'ne 4 kez değer görülmüş, Altın Küre Ödülü'nü bir, Sinema Oyuncuları Derneği Ödülü'nü ise üç kez kazanmıştır.
- Üretim tipi: `source_fallback:unsupported_words:structured`
- Model: -
- Ret nedeni: unsupported_words

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ Alfre Woodard, 18 kez aday gösterildiği Emmy Ödülü'nü 4 kez kazandı. Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve siyasal eylemci 1952 yılında doğdu. #tarih ⏎ --- ⏎ Woodard; Akademi Ödülü ve Grammy Ödülü'ne birer kez aday gösterildi. Altın Küre Ödülü'nü bir, Sinema Oyuncul

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> 🕊️ Tarihte Bugün (8.11.1952)
> 
> Alfre Woodard, Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve siyasal eylemci. Woodard Akademi Ödülü ve Grammy Ödülü'ne birer kez aday gösterilmiş; 18 kez aday gösterildiği Emmy Ödülü'ne 4 kez değer görülmüş, Altın Küre Ödülü'nü bir, Sinema Oyuncuları Derneği Ödülü'nü ise üç kez kazanmıştır. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?

## 7. Tatsuya Nakadai, Japon oyuncu (d. 1932)

- Yıl: 2025
- Kaynak özeti: Tatsuya Nakadai , Japon oyuncudur. Sinemaya Akira Kurosawa'nin ünlü filmi Yedi Samuray'daki ufak bir rol ile başlamıș, ilerleyen yıllarda Masaki Kobayashi'nin yönettiği filmlerde kendini kanıtlayarak Japonya'nın en tanınan oyuncularndan biri haline gelmiștir.
- Üretim tipi: `source_fallback:unsupported_words:structured`
- Model: -
- Ret nedeni: unsupported_words

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ Japon oyuncu Tatsuya Nakadai, sinemaya Akira Kurosawa'nın ünlü filmi Yedi Samuray'daki ufak bir rol ile başladı. #tarih ⏎ --- ⏎ İlerleyen yıllarda Masaki Kobayashi'nin yönettiği filmlerde kendini kanıtlayarak Japonya'nın en tanınan oyuncularından biri haline geldi. 1932 doğumlu oyun

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> 🕊️ Tarihte Bugün (8.11.2025)
> 
> Tatsuya Nakadai, Japon oyuncu (d. 1932). Sinemaya Akira Kurosawa'nin ünlü filmi Yedi Samuray'daki ufak bir rol ile başlamıș, ilerleyen yıllarda Masaki Kobayashi'nin yönettiği filmlerde kendini kanıtlayarak Japonya'nın en tanınan oyuncularndan biri haline gelmiștir. #tarih
>
> Bu ismi tanıyor muydunuz?

## 8. Montana, ABD'nin 41. Eyaleti oldu.

- Yıl: 1889
- Kaynak özeti: Alan bakımından dördüncü büyük eyalet olmasına rağmen, nüfus bakımından sekizinci, nüfus yoğunluğu bakımından ise üçüncü en düşük eyalettir. Eyaletin batı yarısı, özellikle Rocky Dağları olmak üzere çok sayıda sıradağ içerirken, doğu yarısı batı bozkır arazisi ve çorak arazilerle karakterize edilir ve eyalet genelinde daha küçük sıradağlar bulunur.
- Üretim tipi: `ai_source_bound`
- Model: gemini-3.6-flash
- Ret nedeni: -

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🌍 ⏎ --- ⏎ Montana, 1889 yılında ABD'nin 41. eyaleti oldu. Alan bakımından dördüncü büyük eyalet olmasına rağmen nüfus bakımından sekizinci, nüfus yoğunluğu bakımından ise üçüncü en düşük eyalettir. #tarih ⏎ --- ⏎ Eyaletin batı yarısı, özellikle Rocky Dağları olmak üzere çok sayıda sıradağ içe

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> 🌍 Tarihte Bugün (8.11.1889)
> 
> Montana, 1889 yılında ABD'nin 41. eyaleti oldu. Alan bakımından dördüncü büyük eyalet olmasına rağmen nüfus bakımından sekizinci, nüfus yoğunluğu bakımından ise üçüncü en düşük eyalettir. #tarih
>
> Eyaletin batı yarısı, özellikle Rocky Dağları olmak üzere çok sayıda sıradağ içerirken, doğu yarısı batı bozkır arazisi ve çorak arazilerle karakterize edilir ve eyalet genelinde daha küçük sıradağlar bulunur.
>
> Bu eyaletin coğrafi özelliklerini ve nüfus yapısını daha önce duymuş muydunuz?

## 9. Felix Hausdorff, Alman matematikçi (ö. 1942)

- Yıl: 1868
- Kaynak özeti: Felix Hausdorff, modern topolojinin kurucularından biri olarak kabul edilen ve küme teorisine, tanımlayıcı küme teorisine, ölçü teorisine ve fonksiyonel analize önemli katkılarda bulunan bir Alman matematikçi.
- Üretim tipi: `ai_source_bound`
- Model: gemini-3.6-flash
- Ret nedeni: -

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🔬 ⏎ --- ⏎ Modern topolojinin kurucularından kabul edilen Alman matematikçi Felix Hausdorff 1868 yılında doğdu ve 1942 yılında öldü. #tarih ⏎ --- ⏎ Hausdorff, küme teorisine, tanımlayıcı küme teorisine, ölçü teorisine ve fonksiyonel analize katkılarda bulundu. ⏎ --- ⏎ Hausdorff'un matematiğe o

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> 🔬 Tarihte Bugün (8.11.1868)
> 
> Modern topolojinin kurucularından kabul edilen Alman matematikçi Felix Hausdorff 1868 yılında doğdu ve 1942 yılında öldü. #tarih
>
> Hausdorff, küme teorisine, tanımlayıcı küme teorisine, ölçü teorisine ve fonksiyonel analize katkılarda bulundu.
>
> Hausdorff'un matematiğe olan bu katkılarını daha önce duymuş muydunuz?

## 10. ABD başkanlık seçimlerinde Cumhuriyetçi aday George H. W. Bush seçildi.

- Yıl: 1988
- Kaynak özeti: 1988 Amerika Birleşik Devletleri başkanlık seçimleri, 8 Kasım 1988 tarihinde Mevcut Cumhuriyetçi Başkan yardımcısı George H. Seçimleri Mevcut Cumhuriyetçi Başkan yardımcısı George H.
- Üretim tipi: `source_fallback:unsupported_words,language:structured`
- Model: -
- Ret nedeni: unsupported_words,language

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ Cumhuriyetçi aday George H. W. Bush, 1988 ABD başkanlık seçimlerinde başkan seçildi. #tarih ⏎ --- ⏎ 8 Kasım 1988 tarihinde gerçekleşen seçimlerde, mevcut Cumhuriyetçi Başkan yardımcısı George H. W. Bush sandıktan zaferle çıktı. ⏎ --- ⏎ Bu seçimi daha önce duymuş muydunuz?

**Yayımlanacak metin (kod başlığı + model gövdesi veya yapılandırılmış fallback):**

> 🕊️ Tarihte Bugün (8.11.1988)
> 
> ABD başkanlık seçimlerinde Cumhuriyetçi aday George H. W. Bush seçildi. 1988 Amerika Birleşik Devletleri başkanlık seçimleri, 8 Kasım 1988 tarihinde Mevcut Cumhuriyetçi Başkan yardımcısı George H. #tarih
>
> Bu ayrıntıyı daha önce duymuş muydunuz?
