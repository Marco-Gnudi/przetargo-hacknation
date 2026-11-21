# Dataset notes

Practical notes from `UZP-hacknation-task/dane` and `oczekiwane-json`. These observations drive the deterministic extractor. They are not hardcoded answers.

## Inventory

- 60 case folders, `przyklad_01` … `przyklad_60`.
- 180 canonical PDFs: 60 appeals (`odwolanie.pdf`), 60 powers of attorney (`pelnomocnictwo.pdf`), 60 transfer confirmations (`potwierdzenie_przelewu.pdf`).
- 180 reference JSON files sit beside those PDFs and match the same case. `potwierdzenie_przelewu.pdf` is paired with `przelew.json`, not a same-basename file.
- 4 extra PDFs inside cases (`przyklad_04`, `10`, `24`, `37`) are notices or procedure letters, not one of the three classes.
- `dane/negatywne/` has 12 PDFs and `readme.md`. They are documents that must not be classified. The readme says the result is an empty JSON file.
- `oczekiwane-json/` is the schema pack (`odwolanie.json`, `pelnomocnictwo.json`, `przelew.json`, `czynnosc_powod_id_dict.md`). The JSON files contain comments and illustrative values. They are not the answer key for other PDFs.

Every case has exactly one appellant. Three cases have two contracting authorities. Four powers of attorney use a natural person as principal. Transfer amounts are JSON numbers. `czynnosc_powod_id` 12 does not appear in this training set. Id 6 is stored as `Odpowiedzi i wyjaśnienia do SWZ`, while the schema comment uses a slash.

## Recurring layout

Appeals: optional `City, date` line, then `Odwołujący` / `Zamawiający` blocks with `KRS`, `NIP`, `REGON`, a representative line, and a correspondence address. The procurement block has a quoted title, a reference number, and often BZP and TED numbers. The appealed act is the sentence immediately before `Zarzut nr 1` (`Zamawiający w dniu … unieważnił / opublikował / nie odrzucił …`). Later zarzut headings are legal arguments and are the wrong source for `czynnosc_powod_id`.

Powers of attorney: a `PEŁNOMOCNICTWO` heading, sometimes letter-spaced. The principal is introduced as `Mocodawca` / `Mocodawcą jest` or `Ja, niżej podpisany`. Representatives follow `pełnomocnikiem` or `pełnomocnictwa`. Signatures repeat the same people.

Transfers: one page, label on its own line and the value on the next lines. Sender and recipient accounts use different labels (`Rachunek obciążany`, `Z rachunku`, `Rachunek odbiorcy`, `Rachunek uznawany`, and similar). `PL` prefixes and spaced digits both occur. Print dates (`wygenerowano`, `data wydruku`) are not the operation date.

## What is deterministic

Easy: document class from headings, transfer labels, KRS/NIP/REGON near a party, account numbers, amounts, ISO and Polish dates, BZP/TED numbers, the pre-zarzut act and its date.

Harder: the single representative object (the text often names two lawyers), law-firm name versus street, which contracting authority leads a joint procedure, natural-person firm name versus the person's name, and titles broken across lines. Scanned pages with no text layer need OCR; this set's samples have a text layer.

## Approach

Classify from headings and keywords, never from the filename alone. Return `{}` when the class is uncertain. Use one extractor per class, fed by patterns in `configs/rules.json`. Normalize only values that the schema defines. Leave unknowns as `null`. Score the 180 paired JSON files in `benchmark.py`, and treat `negatywne` plus the extra case PDFs as empty-output checks.
