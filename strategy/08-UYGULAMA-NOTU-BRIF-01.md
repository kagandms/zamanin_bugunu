# 08 – Brif #1 uygulama notu (kaynağa bağlı AI yazımı)

Brif: `strategy/07-HAIKU-BRIF-01-AI-YAZIMI.md`. Kapsam: profilsiz olaylarda AI'yı yeniden açmak, Seviye 1 koruması.

## Ne değişti

- **Elle profil şartı kalktı (G1).** Profili olmayan olaylar artık modeli çağırır (`AIService.rewrite_event`). Profilli olaylar (Kars 1921, II. Murad 1448) eski yolla çalışır. Yeni üretim tipi: `ai_source_bound`. Model kaskadının ilk 3 modeli denenir; hepsi reddedilirse mevcut `generate_source_fallback`.
- **Yeni prompt (G2).** `event-rewrite-v5`: `strategy/06-PROMPT-V2-TASLAK.md` sistem prompt'u birebir Python sabitine alındı. Model yalnızca `EMOJI:` + `---` bölümleri + isteğe bağlı `GORSEL_PROMPT:` döndürür. Başlık (`<emoji> Tarihte Bugün (G.A.YYYY)`) ve `#tarih` kod tarafından yazılır. Emoji onaylı kümede değilse 🕊️. Bölüm sayısı 2–3 kabul edilir.
- **Kaynak özeti (G3).** Seçilen sayfanın özeti: sayfa yine sıkı filtreyle seçilir, sonra o sayfadan olay başlığının kilit kelimesini içeren cümleler ve olay cümlesiyle ilgili cümleler alınır; yıl çelişkisi olan cümleler elenir; en fazla 800 karakter. Özet ≥ 200 karakter ise "zengin" (3 bölüm mümkün). Özet < 100 karakter ise `_calculate_fame_score` −10 (eleme yok).
- **Otomatik doğrulama (G4).** `content_guard.validate_source_bound_content`: kaynakta olmayan yıl/sayı (rakam ve Türkçe sayı sözcükleri), büyük harfli kaynaksız özel ad, değer yargısı sıfatları, "ilk kez / en büyük / tek", "doğru muydu / yanlış mıydı", "Ailenizde…" ile başlayan soru, doğrudan "beğenin / takip edin / yorum yapın" istekleri, biçim (EMOJI satırı, 2–3 bölüm, son bölüm soru). Kaynak metinde geçen kalıplar serbest bırakılır. Ret nedenleri kısa kodlarla `last_validation_reason`'a yazılır.
- **İzlenebilirlik (G5).** `generation_type` ve `prompt_version` mevcut metadata yolundan yazılır. Her kabulde model, deneme sırası ve zengin/ince kaynak bilgisi loglanır; ret nedenleri hata logunda toplanır; çıktı örneği ilk 400 karakter loglanır.

## Dosyalar

- `src/services/ai_service.py`: profilsiz yol, `_rewrite_source_bound`, ayrıştırma, başlık birleştirme, prompt sabiti.
- `src/services/content_guard.py`: `CONTENT_GUARD_VERSION = fact-guard-v7`, `validate_source_bound_content`, `source_summary_sentences`.
- `src/services/source_context.py`: `summary_sentences`, `select_event_summary`, `bounded_summary`.
- `src/event_preparation.py`: `_rewrite_request` özet seçimini kullanır; `_used_source_sentences` `ai_source_bound` için özet cümlelerini döndürür.
- `src/services/content_service.py`: özet cezası.
- Testler: `tests/test_source_bound_generation.py` (yeni), `tests/conftest.py` (yeni, canlı model çağrısını testlerde kapatır), güncellenen `test_task02_reliability.py`, `test_source_aware_content.py`, `test_event_source_context.py`.

## Bilinen riskler

- **Kaynak sayfası yanlış olabilir.** Sayfa seçimi değişmedi; ama sayfanın özetinden alınan cümleler olay dışına kayabilir. Doğrulayıcı yalnızca sayı/ad/yasak kalıbı yakalar; anlam kayması yakalamaz. İnceleme için `strategy/evidence/ilk-10-cikti.md`.
- **"tek" yasağı (çözüldü: 06 örneği değiştirildi).** Brifteki kural gereği "tek" kaynakta yoksa reddedilir. `06` dokümanındaki "tek bir ret oyu" örneği bu yüzden reddedilir (örnek ilk tur için kabul edilebilir ama uygulamada geçmez).
- **Kişi sayfaları.** Doğum/ölüm olaylarında sayfa başlığı "kind" kelimesi taşımaz (ör. "Burak Güven"); özet zenginleştirmesi uygulanmaz, çoğu bu olaylar ince kalır.
- **Gecikme.** Profilsiz olaylarda kaskadın 4 modeli denenir (`google/gemma-4-31b-it:free` → `nvidia/nemotron-3-ultra-550b-a55b:free` → `google/gemma-4-26b-a4b-it:free` → `openrouter/free`); her biri 35 sn zaman aşımı. Model kimlikleri yalnızca `src/core/config.py` / ortam değişkenlerinden okunur. Canlı denemede çağrılar arası 20 sn beklenir (yalnızca deneme betiğinde; üretimde yoktur). Olay başına süre artabilir.
- **Sıcaklık.** `temperature=0.5` seçildi (brif belirtmiyordu); veriyle ayarlanabilir.
- **Üretim kapalı.** Bu değişiklik yalnızca kod ve testtir. Yayın yapılmadı, veritabanına yazılmadı, bot canlıda açılmadı. Canlı açılış için kullanıcı onayı gerekir.
