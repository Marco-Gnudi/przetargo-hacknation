from odwolania.config import load_document_types


def test_yaml_loads_three_document_types():
    types = load_document_types()
    assert [item.id for item in types] == ["odwolanie", "pelnomocnictwo", "przelew"]
    for item in types:
        assert item.output_filename.endswith(".json")
        assert item.keywords
        assert item.fields
        assert item.llm_prompt
