from vedagraph.transliteration import DevanagariToIAST


def test_devanagari_to_iast_is_deterministic() -> None:
    transliterator = DevanagariToIAST()
    assert transliterator.transliterate("अग्नि") == "agni"
    assert transliterator.transliterate("अग्नि") == transliterator.transliterate("अग्नि")


def test_transliteration_does_not_mutate_input() -> None:
    source = "अ॒ग्नि"
    _derived = DevanagariToIAST().transliterate(source)
    assert source == "अ॒ग्नि"
