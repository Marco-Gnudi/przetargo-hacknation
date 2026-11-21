from odwolania.classifier import classify


def test_empty_text_is_unclassified():
    assert classify("") is None
    assert classify("   ") is None


def test_appeal_heading_with_party_is_odwolanie():
    text = "Prezes Krajowej Izby Odwoławczej\nOdwołujący:\nFoo sp. z o.o.\nODWOŁANIE\n"
    assert classify(text) == "odwolanie"


def test_textbook_heading_alone_stays_unclassified():
    text = "ODWOŁANIE\nCo jest funkcją odwołania?\nODWOŁANIE – ART. 128 KPA\n"
    assert classify(text) is None


def test_spaced_power_of_attorney_heading():
    text = "P E Ł N O M O C N I C T W O\nMocodawca ustanawia pełnomocnika.\n"
    assert classify(text) == "pelnomocnictwo"


def test_transfer_confirmation_phrase():
    text = "POLECENIE PRZELEWU\nPotwierdzenie realizacji polecenia przelewu\nKwota 10,00 PLN\n"
    assert classify(text) == "przelew"


def test_notice_mentioning_appeal_is_unclassified():
    text = (
        "Ogłoszenie o zamówieniu\n"
        "See the notice on TED website\n"
        "Wykonawcy przysługuje odwołanie.\n"
    )
    assert classify(text) is None
