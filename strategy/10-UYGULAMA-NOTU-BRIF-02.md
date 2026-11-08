# 10 – Brif #2 uygulama notu (tarafsızlık, soru seçimi, hook)

Brif: `strategy/09-HAIKU-BRIF-02-TARAFSIZLIK-VE-SORU.md`. Kanıt: `strategy/evidence/brif02-cikti.md`. Push yapılmadı.

## Bulgular (kod değiştirmeden)

- **T4 – takip çağrısı (Threads footer):** `4acac41` (19 Ekim, "enrich verified historical post context") commit'inde bilerek kaldırıldı: `threads = blocks + (THREADS_FOOTER,)` → `threads = blocks`. Aynı commit'te `test_generic_follow_call_is_not_a_second_threads_part` testi eklendi, yani davranış testle sabit. Commit mesajı boş, gerekçe yazılmamış. Karar günlüğündeki Q-02 ("3+1 D-03 sonuna kadar kalır") ile çelişiyor. Telegram footer'ı yerinde. **Kullanıcı kararı gerekir:** geri getirmek için `event_preparation.py` içinde `threads = blocks + (THREADS_FOOTER,)` ve testin güncellenmesi gerekir (3 içerik + 1 çağrı = 4 parça; Threads sınırı 5).
- **T5 – model kimliği:** `ai_model` değeri `result.get("modelVersion") or model`; Gemini yanıtındaki `modelVersion` alanı. `gemini-3.5-flash` istendi, Google yanıtta `gemini-3.6-flash` bildirdi (tek istekle doğrulandı). Yanlış kayıt değil, API yönlendirmesi; kayıt sunucunun bildirdiği değeri yansıtıyor. İstenen kimlik DB'ye yazılmıyor (istenirse ek alan gerekir). Ücretsiz doğrulama: OpenRouter kimlikleri `:free`; Gemini anahtarının faturalandırma durumu koddan görülemez, Google hesabından kontrol edilmeli.

## Yapılanlar

- **T1 – yüklü dil:** `LOADED_TERM_ROOTS` (ayarlanabilir sabit); atıfsız kullanım `loaded_term` ile reddedilir. Atıf: "… göre", "… tarafından … olarak adlandırılan", tırnak içi. Özel adlar (Zafer Bayramı, Kahramanmaraş) muaf. Yapılandırılmış fallback yüklü özet cümlesini atlar; olay cümlesi yüklüyse `_rewrite_rejection` `loaded_term` döner ve bot sonraki adaya geçer. Prompt'a kural 8 ve Şuşa few-shot örneği (nötr) eklendi.
- **T2 – soru:** Banka olay türü, ayrıntı varlığı ve konu hassasiyetine göre daralır. "Bu ayrıntıyı…" yalnızca 2. parçada yıl-dışı sayı veya olay cümlesinde olmayan özel ad varsa; çatışma/siyaset olaylarında görüş soruları (iz, tarih kitapları) yok.
- **T3 – kopya ve hook:** 2. parça bir kaynak cümlenin ardışık %60'ından fazlasını tekrar ederse `copied_source`. Prompt kural 9: en merak uyandırıcı doğrulanabilir unsuru başa al; 2. parça kaynak sözcükleriyle yeniden kurulmuş olsun.
- **Ek düzeltme:** kök korumasının izinli listesine bağlaç ve yardımcı fiiller (`ancak`, `oldu`, `idi`, `bilinen`, `edildi` …) eklendi. Önceki kuralla canlı çalıştırma 0/9 geçti; değişiklikten sonra 8/9.

## Canlı sonuç (DRY_RUN, yalnızca Gemini, 20 sn aralık)

9 olay (bugün zengin özetli yalnızca 4 çatışma/siyaset olayı vardı): 8 model çıktısı, 1 fallback. Fallback olan Şuşa olayı seçimde `loaded_term` ile atlanır. Üretilen metinlerde atıfsız yüklü terim yok.

## Riskler

- **Anlam kayması yakalanmıyor:** #2'de "Cumhuriyetçi aday Bush seçildi" → "aday olarak seçildi" (sayı/ad/kök kontrolü geçiyor). İnsan incelemesi veya ek kural gerekir.
- **Atlanan olaylar:** yüklü olay cümleli fallback'ler atlanır; seçim 5 denemeyle sınırlı. Çatışma ağırlıklı bir günde hepsi atlanırsa `No event candidate passed` hatası oluşur ve slot boş geçer.
- **Kişi tespiti:** `event_kind` yalnızca "(d. …)", "(ö. …)", "doğdu/öldü" kalıplarını yakalar; doğum/ölüm kaydı bu kalıplar olmadan gelirse genel soru sorulur (#7 Alfre Woodard).
- **Hook:** metinler hâlâ ansiklopedik; hook kuralı kaynak sözcük kısıtıyla birlikte sınırlı etki gösterdi.
