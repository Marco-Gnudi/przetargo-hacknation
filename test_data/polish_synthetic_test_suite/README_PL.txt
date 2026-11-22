ZESTAW TESTOWY OCR/LLM – DOKUMENTY SYNTETYCZNE

Zawartość: 6 fikcyjnych dokumentów PDF i 6 odpowiadających im plików JSON ground truth.
Poziomy: łatwe (PDF cyfrowy) i trudne (skan z zakłóceniami).
Poprzednie pliki trudne (03, 06, 09) są w archive/ i nie wchodzą do ewaluacji.
Pliki, które wcześniej były średnie, są teraz poziomem trudnym.

Pliki JSON odzwierciedlają pola możliwe do ekstrakcji. Wartość null oznacza brak danych w źródle.
Dla korekt ręcznych ground truth przyjmuje wartość po korekcie; szczegóły opisuje manifest.
Wszystkie podmioty, osoby, identyfikatory, numery rachunków i adresy są fikcyjne.
Numery rachunków i identyfikatory nie są przeznaczone do rzeczywistych transakcji ani czynności prawnych.

MAPA TESTÓW

- pdf/01_przelew_latwy.pdf -> ground_truth_json/01_przelew_latwy.json [easy]
  * Cyfrowy PDF; kwota z przecinkiem dziesiętnym; data wydruku różna od daty operacji.

- pdf/02_przelew_trudny.pdf -> ground_truth_json/02_przelew_trudny.json [hard]
  * Skan lekko obrócony i rozmyty; numer rachunku łamany między grupami; odręczna adnotacja „sprawdzono”; wydruk następnego dnia.

- pdf/04_pelnomocnictwo_latwe.pdf -> ground_truth_json/04_pelnomocnictwo_latwe.json [easy]
  * Cyfrowy PDF; PESEL pełnomocnika niepodany; jedna osoba podpisująca.

- pdf/05_pelnomocnictwo_trudne.pdf -> ground_truth_json/05_pelnomocnictwo_trudne.json [hard]
  * Skan w skali szarości i lekki skos; dwa podpisy; pieczęć zachodzi na fragment tekstu; PESEL nieobecny.

- pdf/07_odwolanie_latwe.pdf -> ground_truth_json/07_odwolanie_latwe.json [easy]
  * Cyfrowy PDF; numer BZP podany, numer TED nie dotyczy; dane pełnomocnika i kancelarii w osobnych polach.

- pdf/08_odwolanie_trudne.pdf -> ground_truth_json/08_odwolanie_trudne.json [hard]
  * Skan lekko rozmyty; nagłówek częściowo ucięty; numer TED ze spacjami; różne lokalizacje pól w nagłówku i treści.

ARCHIWUM (poza ewaluacją)

- archive/pdf/03_przelew_trudny.pdf
- archive/pdf/06_pelnomocnictwo_trudne.pdf
- archive/pdf/09_odwolanie_trudne.pdf
