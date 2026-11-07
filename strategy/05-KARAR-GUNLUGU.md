# 05 – Karar Günlüğü ve Açık Sorular

Karar alındıkça bu dosyaya eklenir; silinmez, güncellenirse üstü çizilmez, yeni satır eklenir.

## Alınan kararlar

| Tarih | Karar | Gerekçe |
|---|---|---|
| 2026-11-07 | Ana hedef: Threads'te büyüme, markalaşma, tanınırlık | Kullanıcı |
| 2026-11-07 | Sıklık kararı istatistikle verilecek (D-04) | Kullanıcı |
| 2026-11-07 | Kullanıcı günde ~15 dk manuel iş ayırabilir (yorum cevapları, profil) | Kullanıcı |
| 2026-11-07 | Kışkırtıcı olabiliriz; kesinlikle taraflı olmayız | Kullanıcı |
| 2026-11-07 | Zincir, prompt, sıklık, saatler değiştirilebilir; aşırı koruma gerekmez | Kullanıcı |
| 2026-11-07 | Prompt yazımından önce tüm zemin (strateji, ilkeler, açık sorular) netleştirilecek | Kullanıcı |

## Açık sorular (prompt yazmadan önce kapanmalı)

Her satırda benim önerim var; onay ya da değişiklik yeterli.

| # | Soru | Öneri |
|---|---|---|
| Q-01 | Profil vitrini: bio, sabit gönderi, link şu an ne durumda? | Kullanıcı mevcut halini yazsın/ekran görüntüsü; birlikte netleştirelim |
| Q-02 | Zincir yapısı: 3+1 mi kalsın, yoksa kısaltalım mı? | D-03 ile test; bu arada mevcut kalsın |
| Q-03 | Kapanış sorusu stili | Aile hatırası / "bugün nasıl okuyorsunuz" (D-01) |
| Q-04 | Başlık: `🕊️ Tarihte Bugün (G.A.YYYY)` sabit kalsın mı? | Kalsın (tanınırlık) |
| Q-05 | Etiket politikası | D-06; o zamana kadar tek etiket `#tarih` denenebilir (tek değişken ilkesine uygun başlatılırsa) |
| Q-06 | Görsel politikası: gerçek fotoğraf öncelik, yapay görsel yalnız yedek | Evet; marka çerçevesi D-05 |
| Q-07 | İçerik karışımı: yakın siyasi tarih ağırlığı sürsün mü? | Veri gelene dek sabit; zayıf dayanak |
| Q-08 | Slot güvenilirliği: kaçan/başarısız slotlar için kök neden ve çözüm | Ayrı iş: GitHub cron gecikmesi vs. Cloudflare tetikleyici, loglardan teşhis |
| Q-09 | Seri/isim kimliği (ör. "Bugünün dosyası", haftalık özel seri) | Veriyle konuşunca; önce D-01..D-04 |
| Q-10 | Telegram'ın rolü: Threads dönüşümünü destekleyen kanal mı, bağımsız mı? | Destekleyici; footer metni sade |

## İş listesi (öncelik sırası, taslak)

1. Q-01 netleştir, profil vitrini düzelt (manuel).
2. Q-08 slot güvenilirliği teşhisi.
3. D-01 + D-02 için prompt sürümü `event-rewrite-v2` (tarafsız soru + şaşırtıcı hook); tarafsızlık kuralları 03'ten.
4. Yorum cevap rutini başlat (manuel).
5. D-04 öğle slotu (Per/Paz).
6. Haftalık rapor özeti (DB → medyan tablosu).
7. D-03, D-05, D-06.

## Güncelleme – 2. tur (2026-11-07)

Kullanıcının cevapları ve durum:

| # | Durum | Karar / not |
|---|---|---|
| Q-01 | Kısmen kapandı | Profil: ad "Zamanın Bugünü", bio "Dün yaşandı, bugün hatırla.", link `t.me/zamaninbugunu`, topluluk "History Threads", 76 takipçi. **Sabit gönderi yok.** Karar: sabit gönderi eklenecek (aşağıya bak). Bio markalı ve iyi; dokunma, deneyle test edilebilir. |
| Q-02 | Kapandı | 3+1 zincir D-03 sonuna kadar kalır. |
| Q-03 | Kapandı | Kapanış sorusu gönderiden gönderiye değişir; ağırlık "fikir / anı" soruları. "Beğen, takip et, yorum yap" diye doğrudan istek yok (etkileşim tuzağı sayılabilir ve markaya yakışmaz). Takip çağrısı footer'da ayrı kalır. |
| Q-04 | Kapandı | Başlık metni sabit: `Tarihte Bugün (G.A.YYYY)`. Emoji içeriğe göre değişir (küçük, onaylı bir küme; trajedilerde ⚔️/🔥 gibi hafif emojiler yok). Varsayılan 🕊️. |
| Q-05 | Kapandı (ayrıntı doğrulanacak) | `#tarih` her gönderide sabit. Threads tek konu etiketi destekler (bildiğim kadarıyla; test edilip doğrulanacak), bu yüzden içeriğe özgü anahtar kelimeler etiket yerine metinde doğal geçer. `#tarihteneoldu` çıkarılabilir (D-06). |
| Q-06 | Kapandı | Gerçek fotoğraf öncelik; yapay görsel yedek. |
| Q-07 | Kapandı (taslak) | İçerik önceliği oluşturulacak (aşağıya bak). 1900-2000 yakın siyaset hipotez olarak ağırlıklı, ama ölçülerek. |
| Q-08 | Teşhis başladı | Aşağıya bak. |
| Q-09 | Açıklanacak | Seri kimliği = tekrar eden isimli formatlar. Ertelendi. |
| Q-10 | Kapandı | Telegram açık kalır (ücretsiz, ek dağıtım). Threads kararlarını belirlemez; çatışırsa Threads kazanır. |

### Karar: tek branch

Kullanıcı tek branch istiyor. Karar: **tek çalışma dalı `main`**. Strateji dosyaları ve sonraki işler main üzerinde yapılır. Eski `codex/*` dalları ve worktree'ler temizlenecek, ama **önce** içinde main'e girmemiş iş olup olmadığı kontrol edilecek (aşağıdaki liste) ve silme için kullanıcıdan onay alınacak.

main'de olmayan commit'i olan dallar (7 Kas tespiti): `codex/p0-worker-dispatch-diagnostics` (9), `codex/analytics-foundation` (4), `codex/task04-dispatch-observability` (2), `codex/publication-reliability-content-guard` (2), `codex/source-evidence-main`, `codex/analytics-production-integration`, `codex/task04-external-trigger`, `codex/task03-publication-slots` (her biri 1), ayrıca uzak `pr-5`, `pr-5-merge`, `generation-source-evidence`. Geri kalanı main'e zaten dahil.

### Karar: sabit gönderi

Sabit gönderi önemli: profile gelen ilk kişi ilk onu görür. Önerim: marka formatını en iyi gösteren, tarafsız, iyi performans almış, mümkünse "yakın tarih" bir gönderi. Aday: 10 Ekim 1965 seçim gönderisi (217 bin) — kontrol edilecek (metin, görsel, tarafsızlık). Sabitleme sonrası 2 hafta profil ziyareti→takip oranı izlenir; belirgin iyileşme yoksa farklı gönderi denenir.

### Q-08 teşhis (DB'den, `publication_slots`)

- 8 kaçırılan slot hepsi **14-17 Ekim**: 4 gün boyunca hiçbir slot rezervasyon almamış (`window_closed_without_reservation`). Bu, sistematik arıza gibi değil, o günlerde workflow'un çalışmaması/kapalı olması gibi görünüyor (geliştirme sürecine denk gelmiş olabilir). Doğrulanmadı: GitHub Actions run geçmişi gerek (`gh` bu makinede giriş yapmamış).
- 3 başarısız slot: **22 Ekim** sabah+akşam, **24 Ekim** sabah (`interrupted_or_failed`). Neden loglardan bakılmalı.
- 25 Ekim - 7 Kasım arası kaçırılan/başarısız slot yok. Yani son 2 haftada güvenilirlik iyi; %76 rakamı büyük ölçüde 14-17 Ekim boşluğundan geliyor.
- Açık: 14-17 Ekim ve 22/24 Ekim neden olmuştu? Actions run geçmişine bakmak gerekiyor.

### İçerik önceliği (taslak)

Hipotez: yakın tarih (1900-2000) ve Osmanlı/Milli Mücadele, dünya olaylarına göre daha iyi performans verir; ama veri karışık (Ekim başı Osmanlı savaşları 4-6 bin, 10 Ekim seçim 217 bin, birçok siyaset gönderisi 400-3000). Öneri: olaylara `dönem` + `konu` etiketi veririz (ör. `TR_1900_2000`, `OSMANLI`, `DUNYA_TR_BAGLI`, `DUNYA`), içerik karışımını sabit bir hedefle sürdürüp 4 hafta sonra medyanlarla ağırlıkları ayarlarız. Şimdilik karışım: ağırlık TR 1900-2000 ve Osmanlı; dünya olayları yalnızca Türkiye bağlantısıyla.

## Güncelleme – 3. tur (2026-11-07)

- **Sabit gönderi yapıldı:** 10 Ekim 1965 seçim gönderisi (kullanıcı: 256 bin görüntüleme). Sabitleme tarihi 7 Kas; 2 hafta sonra profil ziyareti→takip izlenecek.
- **Q-03..Q-07, Q-10 kapandı** (bkz. 2. tur). Öncelik: Türk tarihi. Hafta sonu özel seri fikri onaylandı (Q-09): ayrıntı sonra.
- **Q-08 kök neden (kullanıcı):** 14-17 Ekim'deki kaçan slotlar Threads API token süresinin dolmasından (2 aylık/60 gün). Devamlılık etkileşim için kritik.
  - **Risk:** main'de "auth uyarısı için slot dışı Telegram gönderimi kaldırıldı" (task03 belgesi). Yani token tekrar ölürse uyarı gelmeyebilir. Token en geç ~60 gün sonra tekrar riskte.
  - **Yapılacak (kod, Haiku):** token ömrünü ölçüp ~10 gün kala admin'e (Telegram DM/özel kanal) uyarı; yenileme çağrısının gerçekten çalıştığını doğrulamak. Takvim notu: son token yenilemesinin tarihi kullanıcıdan alınacak.
- **Dal temizliği yapıldı (7 Kas, 20:19-20:25):**
  - Önce tüm repo `zamanin-yedek-2026-11-07.bundle` olarak yedeklendi (repo'nun bir üst klasöründe, `Проекты/`). Bütün dallar ve commit'ler bu dosyada; gerekirse `git clone zamanin-yedek-2026-11-07.bundle` ile geri açılır.
  - Yerel `main` `origin/main`'e eşitlendi (753 commit geride + 1 yerel commit vardı: 942fe4a "inject wiki extract into ai prompt…"; yedekte duruyor).
  - 9 temiz worktree kaldırıldı, 3 kayıp worktree kaydı temizlendi, 20 yerel `codex/*` dalı silindi. Geriye yalnızca `main`.
  - **Uzak dallar (`origin/codex/*`, `pr-5`, `pr-5-merge`) silinmedi.** Onay bekliyor.
  - Bilgi: main'deki `ai_service.py` prompt'una wiki `extract` metni enjekte edilmiyor (yerel eski commit 942fe4a bunu yapıyordu). Main'de kaynak bağlamı `source_context.py` üzerinden geliyor; prompt çalışmasında önce bu akışı okuyacağız.

## Notlar

- Haiku 5.5 high oturumuna verilecek görev brifleri **bu belgelerin kapanmış sorularından** üretilecek.
- 10 Ekim (217 bin) gönderisini neyin patlattığı araştırılmalı: konu, saat, görsel, gönderi metni.
