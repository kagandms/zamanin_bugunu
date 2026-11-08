# Gemini model probu (2026-11-08)

Yöntem: üretimdeki `_gemini_request` gövdesi (sistem prompt'u, few-shot, kaynaksız olay: "Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı gerçekleşti."), aday başına tek istek, zaman aşımı 25 sn, `maxOutputTokens` 1200, düşünme kısıtı: `thinkingLevel: minimal` (Gemini 3.x). Anahtar yalnızca `x-goog-api-key` başlığında gönderildi; hiçbir çıktıya yazılmadı.

| Aday | HTTP | Sonuç |
|---|---|---|
| `gemini-3.5-flash` | 200 | Geçerli Türkçe çıktı (finish=STOP, 141 karakter). **Seçildi.** |
| `gemini-3.8-flash` | 400 | "Thinking level MINIMAL is not supported for this model" — denenmedi, düşünme seviyesi bu model için ayrıca ayarlanmalı. |

Gemini 3.5 çıktısı (ilk 80 karakter): `EMOJI: ⚔️ --- Müslümanlar arasındaki ilk iç savaş olan Cemel Savaşı, 656 yılında gerçekleşti. #tarih --- Bu savaşı daha önce duymuş muydunuz?`

Karar: `GEMINI_MODEL` varsayılanı `gemini-3.5-flash` yapıldı. Testler: 266 geçiyor. Push yok.
