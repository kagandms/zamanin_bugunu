# 09 – Haiku Brifi #2: Tarafsızlık, soru seçimi, hook kalitesi

Önce `strategy/03-ICERIK-ILKELERI.md` ve `strategy/06-PROMPT-V2-TASLAK.md` dosyalarını oku. Tek dal `main`; küçük ayrı commit'ler; push'tan önce `git pull --rebase origin main`. **Push zamanı: 09:10–10:40 ve 20:10–21:40 (TSİ) pencerelerinde push yok.** `bot_data.db` ve workflow'lara dokunma. Anahtarları loga yazma.

## Canlı gözlem (8 Kasım, 20:08 gönderisi)

Olay: İkinci Dağlık Karabağ Savaşı / Şuşa, 2020. `generation_type=ai_source_bound`, `ai_model=gemini-3.6-flash`.

Çıkan metin:
1. parça: `⚔️ Tarihte Bugün (8.11.2020)` + "Azerbaycan güçleri, İkinci Dağlık Karabağ Savaşı'nda Şuşa şehrini Ermeni işgalinden kurtardı ve bu tarih daha sonra Zafer Bayramı ilan edildi. #tarih"
2. parça: Vikipedi özetinin neredeyse aynısı.
3. parça: "Bu ayrıntıyı daha önce duymuş muydunuz?"

Sorunlar:
- **S1 Tarafsızlık:** "işgalinden kurtardı" tek tarafın dili. Kaynakta geçtiği için doğrulama geçirdi.
- **S2 Soru uyumsuz:** "Bu ayrıntıyı" bir ayrıntıya işaret etmiyor.
- **S3 Hook ansiklopedik, 2. parça kopya:** yorum/çerçeve yok.
- **S4 Takip çağrısı yok** (önceki yapı 3+1 idi).
- **S5 Model kimliği:** DB'de `gemini-3.6-flash`; yapılandırma varsayılanı `gemini-3.5-flash`.

## Görevler (her biri ayrı commit)

### T1 – Yüklü dil denetimi (S1)
- `content_guard.py` içine yüklü sözcük listesi ekle (kök bazlı): işgal, kurtar, zafer (kaynakta atıf olmadan), soykırım, katliam, vahşet, hain, kahraman, şehit, alçak, zalim, haklı/haksız, terör(ist) gibi. Liste ayarlanabilir sabit olsun.
- Kaynakta geçse bile üretilen metinde bu kökler **atıfsız** kullanılamaz. Atıf kalıpları: "… göre", "… tarafından … olarak adlandırılan", tırnak içinde. Atıf yoksa ret (`loaded_term`), sonraki model, hepsi reddedilirse fallback.
- Prompt'a kural ekle: çatışma/siyaset olaylarında taraf tutan fiil yerine nötr fiil ("denetimi ele geçirdi", "kontrolü Azerbaycan'a geçti"), yüklü terim gerekiyorsa atıf. Örnekle göster (ör. Şuşa olayının tarafsız yazımı).
- **Fallback de aynı denetimden geçsin:** yapılandırılmış fallback ham Vikipedi cümlesini aynen kullanıyor; yüklü terim içeriyorsa bu cümleyi atla veya olayı atlayıp sonraki adaya geç.

### T2 – Soru seçimi (S2)
- "Bu ayrıntıyı daha önce duymuş muydunuz?" yalnızca 2. parçada somut bir sayı/isim/yıl-dışı özel ayrıntı varsa seçilsin. Aksi halde "Bu olayı bugün nasıl okuyorsunuz?" veya "Bu olay hakkında ne biliyordunuz?" tipi genel soru.
- Çatışma/siyaset konularında yargı çağrıştıran soru yok (03 dosyasındaki kurallar).
- Test: ayrıntısız metin → "ayrıntı" sorusu seçilmemeli.

### T3 – Hook ve 2. parça kalitesi (S3)
- Prompt'a ekle: 1. parça olay cümlesini **yeniden sıralamak** değil, kaynaktan en merak uyandırıcı **doğrulanabilir** unsuru öne almak. 2. parça özetin kopyası olamaz: kaynak cümlelerinden ≥ %60 ardışık örtüşme varsa ret (`copied_source`), sonraki model.
- Zorlamak yerine few-shot'a 1–2 iyi/kötü örnek ekle (Şuşa için nötr + hook'lu örnek yaz; olgu eklemeden).
- Ölçüt: yeni bilgi eklemek yok (Seviye 1 kuralı aynı).

### T4 – Takip çağrısı (S4)
- Son commit'lerde footer neden kalktı/çıkmadı? Bilerek bir değişiklik mi, hata mı bak. Bilerek değilse geri getir; bilerek ise nedeniyle birlikte bana bildir (kod değiştirmeden).

### T5 – Model kimliği (S5)
- `ai_model` değeri nereden geliyor (API yanıtı mı, ayar mı)? `gemini-3.6-flash` gerçekten çağrılmış mı yoksa API yönlendirmesi mi? Kaynakta açıkla; yanlış kayıtsa düzelt. Ücretli model kullanılmadığını doğrula.

## Kabul kriterleri
1. `pytest -q` yeşil.
2. Yeni testler: yüklü terim atıfsız → ret; atıflı → geçer; fallback yüklü cümleyi atlar; ayrıntısız metinde "ayrıntı" sorusu yok; kopya 2. parça ret.
3. Çevrimdışı: Şuşa 2020 kaynak metniyle sahte model çıktıları üzerinde yukarıdaki kuralları göster.
4. Canlı doğrulama (DRY_RUN, yayın yok): 5 çatışma/siyaset olayı + 5 diğer. Çıktıları `strategy/evidence/brif02-cikti.md` dosyasına yaz (anahtar yok).
5. Kısa uygulama notu: `strategy/10-UYGULAMA-NOTU-BRIF-02.md`.

## Yapma
- Gönderi sıklığı/slot, workflow, DB değişikliği. Üretime canlı push'u kullanıcı onayı olmadan açma; pencerelere dikkat.
