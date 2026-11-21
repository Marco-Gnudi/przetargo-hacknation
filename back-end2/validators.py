"""Check that a result keeps the organizer's shape. Do not invent values."""


REQUIRED = {
    "odwolanie": ["OdwolanieKIO", "Odwolujacy", "Zamawiajacy", "ZamowieniePubliczne"],
    "pelnomocnictwo": ["mocodawca", "pelnomocnicy"],
    "przelew": ["przelew_bankowy"],
}


def validate(document_type, payload):
    if document_type == "unknown":
        return [] if payload == {} else ["Unknown documents must be an empty object."]
    issues = []
    for key in REQUIRED.get(document_type, []):
        if key not in payload:
            issues.append(f"Missing key {key}.")
    if document_type == "przelew":
        transfer = payload.get("przelew_bankowy") or {}
        amount = transfer.get("kwota")
        if amount is not None and not isinstance(amount, (int, float)):
            issues.append("kwota must be numeric.")
        for field in ("na_rachunek", "z_rachunku"):
            value = transfer.get(field)
            if value is not None and not str(value).isdigit():
                issues.append(f"{field} must contain digits only.")
    if document_type == "odwolanie":
        header = payload.get("OdwolanieKIO") or {}
        powod = header.get("czynnosc_powod_id")
        if powod is not None and powod not in range(1, 13):
            issues.append("czynnosc_powod_id must be 1-12 or null.")
    return issues
