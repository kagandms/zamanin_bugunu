# 13 – Haiku Brifi #4: Sıra sayısı kesmesi, kişi/anma sorusu, AI düşüşleri

Önce `strategy/12-UYGULAMA-NOTU-BRIF-03.md` ve `strategy/03-ICERIK-ILKELERI.md` dosyalarını oku. Tek dal `main`; küçük ayrı commit'ler; push'tan önce `git pull --rebase origin main`. **Push yasak pencereler (TSİ): 09:10–10:40 ve 20:10–21:40.** `bot_data.db` ve workflow'lara dokunma. Anahtar yazma/loglama yok. Ücretli model yok.

## Canlı gözlem (9–10 Kasım gönderileri; DB id 273–275)

| id | Olay | generation_type | Not |
|---|---|---|---|
| 273 | Karındeşen Jack, 1888 | `ai_source_bound` (Gemini) | İyi: "Bu ismi tanıyor muydunuz?" uyuyor |
| 274 | VI. Mehmed Vahdettin, son Selamlık, 10.11.1922 | `source_fallback:http_error,unsupported_words,rate_limited:structured` | **1. parça kesik:** "…Osmanlı İmparatorluğu'nun 36. #tarih" |
| 275 | Atatürk'ün ölümü, 10.11.1938 | `source_fallback:exception,unsupported_number,unsupported_words,rate_limited:structured` | **Soru uyumsuz:** "Bu kişiyi daha önce duymuş muydunuz?" (anma günü, tanınmış figür) |

Kullanıcı 275'in sorusunu elle sildi.

## Görevler (her biri ayrı commit)

### T1 – "36." sıra sayısında cümle kesilmesi (hata)
- Cümle bölücü `36. padişahı…` gibi **sayı + nokta + küçük harfle devam eden** yapıyı cümle sonu saymıyor olmalı, ama saydı. `source_context.py` cümle sınırı (kısaltma listesi yanında sıra sayısı kuralı): rakam(lar) + `.` + boşluk + küçük harf/Türkçe küçük harf → bölme. Büyük harfle devam ederse (yeni cümle) bölme olabilir; belirsizse bölme.
- Test: "Osmanlı İmparatorluğu'nun 36. ve son padişahıdır." tek cümle. "1938'de öldü. 10 Kasım…" bölünür.
- Ek koruma: yayın öncesi 1. parça `\d+\.\s*(#tarih)?$` ile bitiyorsa (sıra sayısıyla biten kesik) ret ve sonraki aday/özet cümlesi.

### T2 – Kişi ve anma sorusu
- `Bu kişiyi daha önce duymuş muydunuz?` tipi sorular, ulusal lider/devlet başkanı/padişah/halife/ünlü tarihî figür için **yasak.** Basit kural: konu ya da metin `cumhurbaşkanı|başbakan|padişah|halife|kral|imparator|mareşal|başkomutan|kurucu` içeriyorsa kişi-tanıma sorusu seçilmez.
- Ölüm/anma olayları (metinde `öldü|vefat|hayatını kaybetti|ulusal yas|anma` ve konu SİYASET/lider): **soru yok**; son parça yerine sade kapanış ya da zincir 1 parça + `#tarih` (mevcut yapı izin veriyorsa). Gerekçe: anma gününde "bu kişiyi duydunuz mu" yanlış ton.
- Genel kişi sorusu yerine: `Bu kişi hakkında ne biliyordunuz?` kalıbı (banka). "Bu ismi tanıyor muydunuz?" yalnızca çok az bilinen/yabancı kişide kalabilir (Karındeşen Jack gibi lakap/takma ad durumu için uygun).
- Test: Atatürk ölüm metni → soru yok. Vahdettin → kişi-tanıma sorusu yok.

### T3 – Fallback neden bu kadar sık, ve niçin AI düştü
- 274 ve 275'in ikisinde de hem `rate_limited` hem `unsupported_words` var; Gemini `http_error`/`exception` verdi. 10 Kasım 06:07 ve 17:07 UTC (09:07/20:07 TSİ) çalışmalarının loglarını `gh run view --log` ile oku: Gemini'ye giden istek hangi HTTP kodunu aldı, 503 yeniden denemesi çalıştı mı, kaç sn bütçe harcandı, nemotron/gemma neden 429? (Anahtar yok, maskeli.)
- `unsupported_words` Turkish-priority/siyaset/ölüm olaylarında neden tetiklendi? Ret edilen kelimeleri (anahtarsız) log/nota yaz; kök-koruması (kaynakta geçmeyen sözcük) fazla katıysa gevşetme önerisi ver (kodu **değiştirmeden** önce notta göster, bana sor; sadece bariz bir hata varsa düzelt).
- Önemli: Türkçe/anma olaylarında AI düşüp ham Vikipedi cümlesi gidiyor; en çok izlenen gönderiler tam bu türde. Gözlem: son 3 gönderinin 2'si fallback.

### T4 – Fallback özet cümlesi kalitesi
- 275'te 1. parçaya ikinci cümle olarak "Mustafa Kemal Atatürk, Türk mareşal, devlet adamı, yazar, …" (Vikipedi tanım cümlesi) eklendi: bilgi yükü yok, tekrar ve fazla uzun. Fallback seçiminde, olay cümlesinde zaten adı geçen kişi için "X, ... 'dir/'dır" biçimli tanım cümlelerini (ad + virgül + sıfat listesi, ilk cümle) tercih etme; bir sonraki özet cümlesi ya da yok say.
- 274'te de benzer: "VI. Mehmed ya da Mehmed Vahideddin, … Şahbaba olarak da bilinir" tanım cümlesi seçilmiş. Aynı kural.
- Test: Atatürk özetinden fallback tanım cümlesini atlar.

## Kabul kriterleri
1. `pytest -q` yeşil; T1, T2, T4 için yeni testler.
2. T3 için notta: iki çalışmanın model/hata tablosu (log satırları, anahtarsız) + öneri.
3. Çevrimdışı: 274 ve 275'in kaynak metinleriyle yeni kuralların çıktısı notta.
4. Uygulama notu: `strategy/14-UYGULAMA-NOTU-BRIF-04.md`. Push yasak pencerelerin dışında; yoksa bana yaz.

## Yapma
- Slot/sıklık, workflow, DB, yeni model/bağımlılık, hook prompt'u, görsel mantığı.
