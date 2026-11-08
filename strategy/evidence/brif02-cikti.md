# Brif #2 canlı doğrulama (8 Kasım, DRY_RUN, yayın yok)

Yalnızca Gemini (`GEMINI_MODEL`); OpenRouter'a çağrı yapılmadı. Çağrılar arasında 20 sn. Veritabanına yazılmadı, yayın yapılmadı. Anahtar yazılmadı.

Sonuç: 8/9 olay model çıktısıyla üretildi; 1 yapılandırılmış fallback.
Olay seçiminde atlanacak fallback sayısı (`loaded_term`): 1.

| # | Tür | Olay | Üretim | Seçimde ret |
|---|---|---|---|---|
| 1 | çatışma/siyaset | ABD başkanlık seçimlerinde Cumhuriyetçi aday George H. W. Bush seçildi | ai_source_bound | - |
| 2 | çatışma/siyaset | ABD Başkanlık seçimlerinde, Cumhuriyetçi aday George H. W. Bush seçild | ai_source_bound | - |
| 3 | çatışma/siyaset | İkinci Dağlık Karabağ Savaşı'nda Azerbaycan güçleri Şuşa şehrini Ermen | source_fallback:unsupported_words:structured | loaded_term |
| 4 | çatışma/siyaset | Almanya'da Adolf Hitler ve yandaşları tarihe "Birahane Darbesi" olarak | ai_source_bound | - |
| 5 | diğer | İngiliz Rock topluluğu Led Zeppelin'in 4. albümleri çıktı. Albümde gru | ai_source_bound | - |
| 6 | diğer | Robert Catesby, 1605'te, İngiliz parlamentosunu havaya uçurmak için bi | ai_source_bound | - |
| 7 | diğer | Alfre Woodard, Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve  | ai_source_bound | - |
| 8 | diğer | John F. Kennedy, ABD Başkanı seçildi. | ai_source_bound | - |
| 9 | diğer | Franklin D. Roosevelt, ABD Başkanı seçildi. | ai_source_bound | - |

## 1. [çatışma/siyaset] ABD başkanlık seçimlerinde Cumhuriyetçi aday George H. W. Bush seçildi.

- Yıl: 1988
- Kaynak özeti: 1988 Amerika Birleşik Devletleri başkanlık seçimleri, 8 Kasım 1988 tarihinde Mevcut Cumhuriyetçi Başkan yardımcısı George H. W. Bush ile Demokrat Massachusetts Valisi Michael Dukakis arasında geçen seçimlerdir. Seçimleri Mevcut Cumhuriyetçi Başkan yardımcısı George H. W. Bush kazanmıştır.
- Üretim: `ai_source_bound` | model: gemini-3.6-flash | ret nedeni: -
- Seçimde ret: yok

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🌍 ⏎ --- ⏎ George H. W. Bush, 1988 ABD başkanlık seçimlerinde başkan seçildi. #tarih ⏎ --- ⏎ 8 Kasım 1988 tarihinde gerçekleşen başkanlık seçimleri, mevcut Cumhuriyetçi Başkan Yardımcısı George H. W. Bush ile Demokrat Massachusetts Valisi Michael Dukakis arasında geçti; seçimi George H. W. Bush kazandı. ⏎ --- ⏎ Bu olayı daha önce duymuş muydu

**Yayımlanacak metin:**

> 🌍 Tarihte Bugün (8.11.1988)
> 
> George H. W. Bush, 1988 ABD başkanlık seçimlerinde başkan seçildi. #tarih
>
> 8 Kasım 1988 tarihinde gerçekleşen başkanlık seçimleri, mevcut Cumhuriyetçi Başkan Yardımcısı George H. W. Bush ile Demokrat Massachusetts Valisi Michael Dukakis arasında geçti; seçimi George H. W. Bush kazandı.
>
> Bu olayı bugün nasıl okuyorsunuz?

## 2. [çatışma/siyaset] ABD Başkanlık seçimlerinde, Cumhuriyetçi aday George H. W. Bush seçildi.

- Yıl: 1988
- Kaynak özeti: 1988 Amerika Birleşik Devletleri başkanlık seçimleri, 8 Kasım 1988 tarihinde Mevcut Cumhuriyetçi Başkan yardımcısı George H. W. Bush ile Demokrat Massachusetts Valisi Michael Dukakis arasında geçen seçimlerdir. Seçimleri Mevcut Cumhuriyetçi Başkan yardımcısı George H. W. Bush kazanmıştır.
- Üretim: `ai_source_bound` | model: gemini-3.6-flash | ret nedeni: -
- Seçimde ret: yok

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ George H. W. Bush, 1988 ABD Başkanlık seçimlerinde aday olarak seçildi. #tarih ⏎ --- ⏎ 8 Kasım 1988 tarihinde Amerika Birleşik Devletleri başkanlık seçimleri yapıldı. Mevcut Cumhuriyetçi Başkan yardımcısı George H. W. Bush ile Demokrat Massachusetts Valisi Michael Dukakis arasında geçen seçimleri George H. W. Bush kazandı. ⏎ --- ⏎

**Yayımlanacak metin:**

> 🏛️ Tarihte Bugün (8.11.1988)
> 
> George H. W. Bush, 1988 ABD Başkanlık seçimlerinde aday olarak seçildi. #tarih
>
> 8 Kasım 1988 tarihinde Amerika Birleşik Devletleri başkanlık seçimleri yapıldı. Mevcut Cumhuriyetçi Başkan yardımcısı George H. W. Bush ile Demokrat Massachusetts Valisi Michael Dukakis arasında geçen seçimleri George H. W. Bush kazandı.
>
> Bu olayı bugün nasıl okuyorsunuz?

## 3. [çatışma/siyaset] İkinci Dağlık Karabağ Savaşı'nda Azerbaycan güçleri Şuşa şehrini Ermeni işgalinden kurtardı. Bu tarih daha sonra Zafer Bayramı ilan edildi.

- Yıl: 2020
- Kaynak özeti: İkinci Dağlık Karabağ Savaşı, 2020 Dağlık Karabağ Savaşı veya 44 Günlük Savaş Dağlık Karabağ'da Türkiye destekli Azerbaycan ile Ermenistan ve onun desteklediği tanınmayan Dağlık Karabağ Cumhuriyeti arasında yaşanmış silahlı çatışmalardır.
- Üretim: `source_fallback:unsupported_words:structured` | model: - | ret nedeni: unsupported_words
- Seçimde ret: loaded_term

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: ⚔️ ⏎ --- ⏎ Şuşa şehri Azerbaycan güçlerinin denetimine geçti ve 2020 yılındaki bu tarih daha sonra Zafer Bayramı ilan edildi. İkinci Dağlık Karabağ Savaşı'nda yaşanan bu gelişme kayıtlara girdi. #tarih ⏎ --- ⏎ 44 Günlük Savaş olarak da bilinen bu silahlı çatışmalar; Türkiye destekli Azerbaycan ile Ermenistan ve onun desteklediği tanınmayan D

**Yayımlanacak metin:**

> 🕊️ Tarihte Bugün (8.11.2020)
> 
> İkinci Dağlık Karabağ Savaşı'nda Azerbaycan güçleri Şuşa şehrini Ermeni işgalinden kurtardı. Bu tarih daha sonra Zafer Bayramı ilan edildi. #tarih
>
> Bu olayı bugün nasıl okuyorsunuz?

## 4. [çatışma/siyaset] Almanya'da Adolf Hitler ve yandaşları tarihe "Birahane Darbesi" olarak geçecek olan olayla Bavyera eyaletinin yönetimini ele geçirmek için ayaklandı.

- Yıl: 1923
- Kaynak özeti: Birahane Darbesi, Adolf Hitler, General Erich Ludendorff ve diğer Kampfbund liderleri tarafından Bavyera eyaletinin yönetimine el koymak amacıyla 8-9 Kasım 1923 tarihinde gerçekleştirdiği başarısız bir darbe girişimidir.
- Üretim: `ai_source_bound` | model: gemini-3.6-flash | ret nedeni: -
- Seçimde ret: yok

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ Bavyera eyaletinin yönetimini ele geçirmek için Adolf Hitler ve yandaşları 1923 yılında ayaklandı; bu olay tarihe "Birahane Darbesi" olarak geçti. #tarih ⏎ --- ⏎ 8-9 Kasım 1923 tarihinde gerçekleşen bu darbe girişimi; Adolf Hitler, General Erich Ludendorff ve diğer Kampfbund liderleri tarafından Bavyera eyaletinin yönetimine el ko

**Yayımlanacak metin:**

> 🏛️ Tarihte Bugün (8.11.1923)
> 
> Bavyera eyaletinin yönetimini ele geçirmek için Adolf Hitler ve yandaşları 1923 yılında ayaklandı; bu olay tarihe "Birahane Darbesi" olarak geçti. #tarih
>
> 8-9 Kasım 1923 tarihinde gerçekleşen bu darbe girişimi; Adolf Hitler, General Erich Ludendorff ve diğer Kampfbund liderleri tarafından Bavyera eyaletinin yönetimine el koymak amacıyla düzenlenen başarısız bir girişimdi.
>
> Bu olayı bugün nasıl okuyorsunuz?

## 5. [diğer] İngiliz Rock topluluğu Led Zeppelin'in 4. albümleri çıktı. Albümde grubun en çok bilinen şarkısı "Stairway to Heaven" var.

- Yıl: 1971
- Kaynak özeti: "Stairway to Heaven", İngiliz rock grubu Led Zeppelin tarafından 8 Kasım 1971'de piyasaya sürülen şarkı. Grubun gitaristi Jimmy Page ve vokalisti Robert Plant tarafından isimsiz dördüncü stüdyo albümleri için bestelenmiştir. Genellikle tüm zamanların en popüler rock şarkılarından biri olarak kabul edilmektedir.
- Üretim: `ai_source_bound` | model: gemini-3.6-flash | ret nedeni: -
- Seçimde ret: yok

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ "Stairway to Heaven" şarkısını içeren Led Zeppelin'in 4. albümü, 1971'de çıktı. #tarih ⏎ --- ⏎ Grubun gitaristi Jimmy Page ve vokalisti Robert Plant tarafından dördüncü stüdyo albümleri için bestelenen şarkı, 8 Kasım 1971'de piyasaya sürüldü. ⏎ --- ⏎ Bu olayı daha önce duymuş muydunuz?

**Yayımlanacak metin:**

> 🎭 Tarihte Bugün (8.11.1971)
> 
> "Stairway to Heaven" şarkısını içeren Led Zeppelin'in 4. albümü, 1971'de çıktı. #tarih
>
> Grubun gitaristi Jimmy Page ve vokalisti Robert Plant tarafından dördüncü stüdyo albümleri için bestelenen şarkı, 8 Kasım 1971'de piyasaya sürüldü.
>
> Bu olayı bugün nasıl okuyorsunuz?

## 6. [diğer] Robert Catesby, 1605'te, İngiliz parlamentosunu havaya uçurmak için bir araya gelen 12 kişilik "Barut Komplosu" ekibin lideri (d. 1572)

- Yıl: 1605
- Kaynak özeti: Barut komplosu, bir grup yönetim karşıtı İngiliz Katolik tarafından, İngiltere Kralı I. James ve diğer aristokratları öldürmek için 5 Kasım 1605'te yapılan, Parlamento binasını havaya uçurma girişimidir. Robert Catesby ve Guy Fawkes öncülüğünde planlanmıştır.
- Üretim: `ai_source_bound` | model: gemini-3.6-flash | ret nedeni: -
- Seçimde ret: yok

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🏛️ ⏎ --- ⏎ Robert Catesby, 1605'te İngiliz parlamentosunu havaya uçurmak için bir araya gelen 12 kişilik ekibin lideriydi. #tarih ⏎ --- ⏎ Bir grup yönetim karşıtı İngiliz Katolik, İngiltere Kralı I. James ve aristokratları öldürmek amacıyla 5 Kasım 1605'te Parlamento binasını havaya uçurma girişiminde bulundu. Bu girişim Robert Catesby ve Gu

**Yayımlanacak metin:**

> 🏛️ Tarihte Bugün (8.11.1605)
> 
> Robert Catesby, 1605'te İngiliz parlamentosunu havaya uçurmak için bir araya gelen 12 kişilik ekibin lideriydi. #tarih
>
> Bir grup yönetim karşıtı İngiliz Katolik, İngiltere Kralı I. James ve aristokratları öldürmek amacıyla 5 Kasım 1605'te Parlamento binasını havaya uçurma girişiminde bulundu. Bu girişim Robert Catesby ve Guy Fawkes öncülüğünde planlandı.
>
> Bu ismi tanıyor muydunuz?

## 7. [diğer] Alfre Woodard, Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve siyasal eylemci

- Yıl: 1952
- Kaynak özeti: Alfre Woodard, Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve siyasal eylemci. Woodard Akademi Ödülü ve Grammy Ödülü'ne birer kez aday gösterilmiş; 18 kez aday gösterildiği Emmy Ödülü'ne 4 kez değer görülmüş, Altın Küre Ödülü'nü bir, Sinema Oyuncuları Derneği Ödülü'nü ise üç kez kazanmıştır.
- Üretim: `ai_source_bound` | model: gemini-3.6-flash | ret nedeni: -
- Seçimde ret: yok

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🎭 ⏎ --- ⏎ Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve siyasal eylemci Alfre Woodard 1952 yılında doğdu. #tarih ⏎ --- ⏎ Woodard, 18 kez aday gösterildiği Emmy Ödülü'nü 4 kez kazandı. Sinema Oyuncuları Derneği Ödülü'nü üç kez, Altın Küre Ödülü'nü ise bir kez kazanan oyuncu; Akademi Ödülü ve Grammy Ödülü'ne de birer kez aday gösteril

**Yayımlanacak metin:**

> 🎭 Tarihte Bugün (8.11.1952)
> 
> Amerikalı sinema, dizi ve tiyatro oyuncusu, yapımcı ve siyasal eylemci Alfre Woodard 1952 yılında doğdu. #tarih
>
> Woodard, 18 kez aday gösterildiği Emmy Ödülü'nü 4 kez kazandı. Sinema Oyuncuları Derneği Ödülü'nü üç kez, Altın Küre Ödülü'nü ise bir kez kazanan oyuncu; Akademi Ödülü ve Grammy Ödülü'ne de birer kez aday gösterildi.
>
> Bu olayı bugün nasıl okuyorsunuz?

## 8. [diğer] John F. Kennedy, ABD Başkanı seçildi.

- Yıl: 1960
- Kaynak özeti: 1960 Amerika Birleşik Devletleri başkanlık seçimleri, 8 Kasım 1960 tarihinde Cumhuriyetçi aday Mevcut Başkan yardımcısı Richard Nixon ile Demokrat aday Massachusetts senatörü John F. Kennedy arasında gerçekleşti. Seçimleri Demokrat aday Massachusetts senatörü John F. Kennedy kazandı.
- Üretim: `ai_source_bound` | model: gemini-3.6-flash | ret nedeni: -
- Seçimde ret: yok

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🌍 ⏎ --- ⏎ John F. Kennedy, 1960 yılında ABD Başkanı seçildi. #tarih ⏎ --- ⏎ 8 Kasım 1960 tarihinde gerçekleşen seçimler, Cumhuriyetçi aday Richard Nixon ile Demokrat aday John F. Kennedy arasında geçti; kazanan Kennedy oldu. ⏎ --- ⏎ Bu olayı daha önce duymuş muydunuz?

**Yayımlanacak metin:**

> 🌍 Tarihte Bugün (8.11.1960)
> 
> John F. Kennedy, 1960 yılında ABD Başkanı seçildi. #tarih
>
> 8 Kasım 1960 tarihinde gerçekleşen seçimler, Cumhuriyetçi aday Richard Nixon ile Demokrat aday John F. Kennedy arasında geçti; kazanan Kennedy oldu.
>
> Bu olayı bugün nasıl okuyorsunuz?

## 9. [diğer] Franklin D. Roosevelt, ABD Başkanı seçildi.

- Yıl: 1932
- Kaynak özeti: 1932 Amerika Birleşik Devletleri başkanlık seçimleri, 8 Kasım 1932 tarihinde Mevcut Cumhuriyetçi Başkan Herbert Hoover ile Demokrat aday Franklin D. Roosevelt arasında gerçekleşti. Seçimleri Demokrat aday Franklin D. Roosevelt büyük bir zaferle kazandı.
- Üretim: `ai_source_bound` | model: gemini-3.6-flash | ret nedeni: -
- Seçimde ret: yok

**Denemeler:**

- `gemini-3.5-flash` HTTP 200: EMOJI: 🌍 ⏎ --- ⏎ Franklin D. Roosevelt, 1932 yılında ABD Başkanı seçildi. #tarih ⏎ --- ⏎ 8 Kasım 1932 tarihindeki seçimlerde Demokrat aday Franklin D. Roosevelt ile mevcut Cumhuriyetçi Başkan Herbert Hoover yarıştı; oylamayı Franklin D. Roosevelt kazandı. ⏎ --- ⏎ Bu olayı daha önce duymuş muydunuz?

**Yayımlanacak metin:**

> 🌍 Tarihte Bugün (8.11.1932)
> 
> Franklin D. Roosevelt, 1932 yılında ABD Başkanı seçildi. #tarih
>
> 8 Kasım 1932 tarihindeki seçimlerde Demokrat aday Franklin D. Roosevelt ile mevcut Cumhuriyetçi Başkan Herbert Hoover yarıştı; oylamayı Franklin D. Roosevelt kazandı.
>
> Bu olayı bugün nasıl okuyorsunuz?
