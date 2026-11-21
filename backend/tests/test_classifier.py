from odwolania.classifier import classify, classify_text


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


def test_line_wrap_does_not_create_an_appeal_label():
    text = (
        "uznać należy, że\n"
        "Odwołujący dochował regulacji art. 515.\n"
        "odwołania wniesionego do Prezesa Krajowej Izby Odwoławczej w dniu 3\n"
    )
    result = classify_text(text)
    assert result.label is None
    assert result.scores["odwolanie"] == 3


def test_heading_is_not_assembled_across_lines():
    text = "o\nd\nw\no\nł\na\nn\ni\ne\n"
    assert classify_text(text).scores["odwolanie"] == 0


def test_notice_mentioning_appeal_is_unclassified():
    text = (
        "Ogłoszenie o zamówieniu\n"
        "See the notice on TED website\n"
        "Wykonawcy przysługuje odwołanie.\n"
    )
    assert classify(text) is None
