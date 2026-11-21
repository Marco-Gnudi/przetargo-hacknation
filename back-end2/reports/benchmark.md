# Extraction benchmark

Null leaves are ignored. A wrong non-null value counts as one false positive and one false negative.

## By document type

| Type | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| empty | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| odwolanie | 0.990 | 0.988 | 0.989 | 1199 | 12 | 15 |
| pelnomocnictwo | 0.981 | 0.926 | 0.953 | 424 | 8 | 34 |
| przelew | 1.000 | 1.000 | 1.000 | 360 | 0 | 0 |

## Fields with the most errors

| Field | FP | FN | TP |
|---|---:|---:|---:|
| pelnomocnictwo:mocodawca[].podpisujacy[].imie_nazwisko | 8 | 10 | 85 |
| odwolanie:OdwolanieKIO.czynnosc_opis | 5 | 1 | 54 |
| odwolanie:OdwolanieKIO.czynnosc_powod_id | 5 | 1 | 54 |
| pelnomocnictwo:mocodawca[].data.krs | 0 | 6 | 56 |
| pelnomocnictwo:mocodawca[].data.nazwa | 0 | 6 | 60 |
| pelnomocnictwo:mocodawca[].data.nip | 0 | 6 | 60 |
| pelnomocnictwo:mocodawca[].data.typ | 0 | 6 | 60 |
| odwolanie:OdwolanieKIO.czynnosc_dzien | 1 | 0 | 59 |
| odwolanie:Odwolujacy[].pelnomocnik.nazwa | 0 | 1 | 59 |
| odwolanie:OdwolanieKIO.miejscowosc | 1 | 0 | 44 |

## Sample mismatches

- `odwolanie.pdf` `OdwolanieKIO.czynnosc_dzien`: predicted `2026-09-18` / reference `2026-10-09`
- `pelnomocnictwo.pdf` `mocodawca[1].data.krs`: predicted `None` / reference `9997108834`
- `pelnomocnictwo.pdf` `mocodawca[1].data.nazwa`: predicted `None` / reference `Hydromel Instalacje sp.j.`
- `pelnomocnictwo.pdf` `mocodawca[1].data.nip`: predicted `None` / reference `9994417025`
- `pelnomocnictwo.pdf` `mocodawca[1].data.typ`: predicted `None` / reference `osoba_prawna`
- `pelnomocnictwo.pdf` `mocodawca[1].podpisujacy[0].imie_nazwisko`: predicted `None` / reference `Agnieszka Kurek`
- `pelnomocnictwo.pdf` `mocodawca[1].podpisujacy[1].imie_nazwisko`: predicted `None` / reference `Robert Kurek`
- `odwolanie.pdf` `Odwolujacy[0].pelnomocnik.nazwa`: predicted `None` / reference `Michalak Legal Kancelaria Radcy Prawnego`
- `odwolanie.pdf` `OdwolanieKIO.czynnosc_opis`: predicted `Publikacja specyfikacji warunków zamówienia (SWZ)` / reference `Odpowiedzi i wyjaśnienia do SWZ`
- `odwolanie.pdf` `OdwolanieKIO.czynnosc_powod_id`: predicted `4` / reference `6`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[2].imie_nazwisko`: predicted `Wojciech Majewski` / reference `None`
- `pelnomocnictwo.pdf` `mocodawca[1].data.krs`: predicted `None` / reference `9990093297`
- `pelnomocnictwo.pdf` `mocodawca[1].data.nazwa`: predicted `None` / reference `Lumerio Facility sp.j.`
- `pelnomocnictwo.pdf` `mocodawca[1].data.nip`: predicted `None` / reference `9999917794`
- `pelnomocnictwo.pdf` `mocodawca[1].data.typ`: predicted `None` / reference `osoba_prawna`
- `pelnomocnictwo.pdf` `mocodawca[1].podpisujacy[0].imie_nazwisko`: predicted `None` / reference `Wojciech Majewski`
- `odwolanie.pdf` `OdwolanieKIO.czynnosc_opis`: predicted `Decyzja o wykluczeniu wykonawcy` / reference `Zaniechanie wykluczenia wykonawcy`
- `odwolanie.pdf` `OdwolanieKIO.czynnosc_powod_id`: predicted `3` / reference `8`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[2].imie_nazwisko`: predicted `Wojciech Wysocki` / reference `None`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[3].imie_nazwisko`: predicted `Iwona Grabowska` / reference `None`
- `pelnomocnictwo.pdf` `mocodawca[1].data.krs`: predicted `None` / reference `9997591201`
- `pelnomocnictwo.pdf` `mocodawca[1].data.nazwa`: predicted `None` / reference `Fendor Farmacja sp. z o.o.`
- `pelnomocnictwo.pdf` `mocodawca[1].data.nip`: predicted `None` / reference `9993439623`
- `pelnomocnictwo.pdf` `mocodawca[1].data.typ`: predicted `None` / reference `osoba_prawna`
- `pelnomocnictwo.pdf` `mocodawca[1].podpisujacy[0].imie_nazwisko`: predicted `None` / reference `Wojciech Wysocki`
- `pelnomocnictwo.pdf` `mocodawca[1].podpisujacy[1].imie_nazwisko`: predicted `None` / reference `Iwona Grabowska`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[1].imie_nazwisko`: predicted `Sebastian Adamczyk` / reference `None`
- `pelnomocnictwo.pdf` `mocodawca[0].podpisujacy[2].imie_nazwisko`: predicted `Damian Tomaszewski` / reference `None`
- `pelnomocnictwo.pdf` `mocodawca[1].data.krs`: predicted `None` / reference `9996965616`
- `pelnomocnictwo.pdf` `mocodawca[1].data.nazwa`: predicted `None` / reference `Polvent Aparatura Medyczna sp. z o.o.`
