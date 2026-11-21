ZESTAW TESTOWY OCR/LLM – DOKUMENTY SYNTETYCZNE

Zawartość: 9 fikcyjnych dokumentów PDF i 9 odpowiadających im plików JSON ground truth.
Poziomy: łatwy (PDF cyfrowy), średni (skan z zakłóceniami), trudny (skan wielostronicowy z korektami i niejednoznacznościami).

Pliki JSON odzwierciedlają pola możliwe do ekstrakcji. Wartość null oznacza brak danych w źródle.
Dla korekt ręcznych ground truth przyjmuje wartość po korekcie; szczegóły opisuje manifest.
Wszystkie podmioty, osoby, identyfikatory, numery rachunków i adresy są fikcyjne.
Numery rachunków i identyfikatory nie są przeznaczone do rzeczywistych transakcji ani czynności prawnych.

MAPA TESTÓW

- pdf/01_przelew_latwy.pdf -> ground_truth_json/01_przelew_latwy.json [easy]
  * Cyfrowy PDF; kwota z przecinkiem dziesiętnym; data wydruku różna od daty operacji.

- pdf/02_przelew_sredni.pdf -> ground_truth_json/02_przelew_sredni.json [intermediate]
  * Skan lekko obrócony i rozmyty; numer rachunku łamany między grupami; odręczna adnotacja „sprawdzono”; wydruk następnego dnia.

- pdf/03_przelew_trudny.pdf -> ground_truth_json/03_przelew_trudny.json [hard]
  * Dwustronicowy skan niskiej jakości; data w formacie dd/mm/yyyy; numer rachunku odbiorcy zawiera błędną końcówkę na wydruku, poprawioną odręcznie na 1111; ground truth przyjmuje korektę.

- pdf/04_pelnomocnictwo_latwe.pdf -> ground_truth_json/04_pelnomocnictwo_latwe.json [easy]
  * Cyfrowy PDF; PESEL pełnomocnika niepodany; jedna osoba podpisująca.

- pdf/05_pelnomocnictwo_srednie.pdf -> ground_truth_json/05_pelnomocnictwo_srednie.json [intermediate]
  * Skan w skali szarości i lekki skos; dwa podpisy; pieczęć zachodzi na fragment tekstu; PESEL nieobecny.

- pdf/06_pelnomocnictwo_trudne.pdf -> ground_truth_json/06_pelnomocnictwo_trudne.json [hard]
  * Dwustronicowy skan z cieniem zagięcia; stary KRS przekreślony i zastąpiony ręczną korektą; pełnomocnik raz bez tytułu, raz jako „dr Marek Lis”; PESEL nie występuje.

- pdf/07_odwolanie_latwe.pdf -> ground_truth_json/07_odwolanie_latwe.json [easy]
  * Cyfrowy PDF; numer BZP podany, numer TED nie dotyczy; dane pełnomocnika i kancelarii w osobnych polach.

- pdf/08_odwolanie_srednie.pdf -> ground_truth_json/08_odwolanie_srednie.json [intermediate]
  * Skan lekko rozmyty; nagłówek częściowo ucięty; numer TED ze spacjami; różne lokalizacje pól w nagłówku i treści.

- pdf/09_odwolanie_trudne.pdf -> ground_truth_json/09_odwolanie_trudne.json [hard]
  * Trzy strony; skan niskiego kontrastu; ręczna korekta daty czynności z 11.10 na 12.10.2026; korekta KRS; brak danych prowadzącego postępowanie.
