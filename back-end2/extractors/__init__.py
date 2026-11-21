"""Document extractors."""

from extractors.odwolanie import extract_odwolanie
from extractors.pelnomocnictwo import extract_pelnomocnictwo
from extractors.przelew import extract_przelew

EXTRACTORS = {
    "odwolanie": extract_odwolanie,
    "pelnomocnictwo": extract_pelnomocnictwo,
    "przelew": extract_przelew,
}
