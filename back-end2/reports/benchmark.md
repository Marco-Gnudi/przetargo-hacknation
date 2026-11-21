# Extraction benchmark

Null leaves are ignored. A wrong non-null value counts as one false positive and one false negative.

## By document type

| Type | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| empty | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| odwolanie | 0.939 | 0.974 | 0.956 | 1183 | 77 | 31 |
| pelnomocnictwo | 0.929 | 0.830 | 0.877 | 380 | 29 | 78 |
| przelew | 0.966 | 0.953 | 0.959 | 343 | 12 | 17 |

## Fields with the most errors

| Field | FP | FN | TP |
|---|---:|---:|---:|
| pelnomocnictwo:mocodawca[].podpisujacy[].imie_nazwisko | 8 | 21 | 74 |
| odwolanie:Zamawiajacy[].nazwa | 15 | 6 | 52 |
| pelnomocnictwo:pelnomocnicy[].imie_nazwisko | 8 | 12 | 78 |
| pelnomocnictwo:mocodawca[].data.nazwa | 13 | 6 | 47 |
| odwolanie:Zamawiajacy[].prowadzacy_postepowanie | 16 | 0 | 5 |
| odwolanie:Zamawiajacy[].krs | 12 | 0 | 58 |
| odwolanie:Zamawiajacy[].nip | 10 | 0 | 63 |
| odwolanie:Zamawiajacy[].regon | 10 | 0 | 63 |
| przelew:przelew_bankowy.tytul | 7 | 0 | 53 |
| odwolanie:OdwolanieKIO.czynnosc_opis | 5 | 1 | 54 |
| odwolanie:OdwolanieKIO.czynnosc_powod_id | 5 | 1 | 54 |
| pelnomocnictwo:mocodawca[].data.krs | 0 | 6 | 56 |
| pelnomocnictwo:mocodawca[].data.nip | 0 | 6 | 60 |
| pelnomocnictwo:mocodawca[].data.typ | 0 | 6 | 60 |
| przelew:przelew_bankowy.kwota | 0 | 5 | 55 |
| odwolanie:Odwolujacy[].nazwa | 1 | 3 | 56 |
| przelew:przelew_bankowy.data_operacji | 4 | 0 | 56 |
| odwolanie:OdwolanieKIO.czynnosc_dzien | 1 | 0 | 59 |
| odwolanie:Odwolujacy[].krs | 1 | 0 | 56 |
| odwolanie:Odwolujacy[].pelnomocnik.nazwa | 0 | 1 | 59 |

## Sample mismatches

- `pelnomocnictwo.pdf` `mocodawca[0].data.nazwa`: predicted `Mocodawca Hartica Serwis S.A.` / reference `Hartica Serwis S.A.`
- `pelnomocnictwo.pdf` `pelnomocnicy[0].imie_nazwisko`: predicted `None` / reference `Bartosz Szymanski`
- `pelnomocnictwo.pdf` `pelnomocnicy[1].imie_nazwisko`: predicted `None` / reference `Cezary Wierzbicki`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[0].imie_nazwisko`: predicted `None` / reference `Sławomir Jabłoński`
- `pelnomocnictwo.pdf` `mocodawca[0].data.nazwa`: predicted `MOCODAWCA Corvantis Wyposażenie sp. z o.o.` / reference `Corvantis Wyposażenie sp. z o.o.`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[0].imie_nazwisko`: predicted `None` / reference `Aleksandra Gajewski`
- `pelnomocnictwo.pdf` `pelnomocnicy[0].imie_nazwisko`: predicted `Ignacy Sadowski nr` / reference `Ignacy Sadowski`
- `potwierdzenie_przelewu.pdf` `przelew_bankowy.kwota`: predicted `None` / reference `17.0`
- `potwierdzenie_przelewu.pdf` `przelew_bankowy.tytul`: predicted `„opłata skarbowa od pełnomocnictwa dla Ignacy Sadowski w postępowaniu przed KIO w przetargu SWZ.780.2026 CEN2611091860728” Numer transakcji operacji CEN2611091860728` / reference `opłata skarbowa od pełnomocnictwa dla Ignacy Sadowski w postępowaniu przed KIO w przetargu SWZ.780.2026 CEN2611091860728`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[1].imie_nazwisko`: predicted `None` / reference `Oliwia Gajewski`
- `pelnomocnictwo.pdf` `mocodawca[0].data.nazwa`: predicted `Mocodawca Umbria Rozwiązania sp. j.` / reference `Umbria Rozwiązania sp. j.`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[1].imie_nazwisko`: predicted `None` / reference `Ryszard Lewandowski`
- `pelnomocnictwo.pdf` `pelnomocnicy[0].imie_nazwisko`: predicted `None` / reference `Bartosz Jastrzębski`
- `pelnomocnictwo.pdf` `pelnomocnicy[1].imie_nazwisko`: predicted `None` / reference `Oliwia Zajkowski`
- `pelnomocnictwo.pdf` `mocodawca[0].data.nazwa`: predicted `MOCODAWCA Quantis Serwis sp. k.` / reference `Quantis Serwis sp. k.`
- `pelnomocnictwo.pdf` `pelnomocnicy[0].imie_nazwisko`: predicted `Cezary Bartoszewicz nr` / reference `Cezary Bartoszewicz`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[0].imie_nazwisko`: predicted `None` / reference `Cezary Dudziewicz`
- `potwierdzenie_przelewu.pdf` `przelew_bankowy.data_operacji`: predicted `2026-07-12` / reference `2026-07-09`
- `potwierdzenie_przelewu.pdf` `przelew_bankowy.kwota`: predicted `None` / reference `200.0`
- `potwierdzenie_przelewu.pdf` `przelew_bankowy.tytul`: predicted `„opłata skarbowa od pełnomocnictwa dla Klaudia Dobrowolski w postępowaniu przed KIO w przetargu SWZ.755.2026 CEN2607206163458” Numer transakcji operacji CEN2607206163458` / reference `opłata skarbowa od pełnomocnictwa dla Klaudia Dobrowolski w postępowaniu przed KIO w przetargu SWZ.755.2026 CEN2607206163458`
- `pelnomocnictwo.pdf` `mocodawca[0].data.nazwa`: predicted `Mocodawca Opalit Serwis sp. k.` / reference `Opalit Serwis sp. k.`
- `pelnomocnictwo.pdf` `pelnomocnicy[0].imie_nazwisko`: predicted `None` / reference `Patrycja Bartoszewicz`
- `pelnomocnictwo.pdf` `pelnomocnicy[1].imie_nazwisko`: predicted `None` / reference `Aleksandra Gajewicz`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[0].imie_nazwisko`: predicted `None` / reference `Marek Nowakowicz`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[1].imie_nazwisko`: predicted `None` / reference `Ryszard Biernacki`
- `pelnomocnictwo.pdf` `mocodawca[0].data.nazwa`: predicted `MOCODAWCA Kavendis Infrastruktura sp. z o.o.` / reference `Kavendis Infrastruktura sp. z o.o.`
- `pelnomocnictwo.pdf` `pelnomocnicy[0].imie_nazwisko`: predicted `Norbert Milewski nr` / reference `Norbert Milewski`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[1].imie_nazwisko`: predicted `None` / reference `Ewa Dudziewicz`
- `potwierdzenie_przelewu.pdf` `przelew_bankowy.data_operacji`: predicted `2026-04-29` / reference `2026-04-26`
- `potwierdzenie_przelewu.pdf` `przelew_bankowy.kwota`: predicted `None` / reference `100.0`
