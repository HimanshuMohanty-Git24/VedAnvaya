"""Griffith's hymn order differs from Aufrecht's in Book 8 only."""

from vedagraph.editions import griffith_page


def test_book_8_valakhilya_is_printed_at_the_end_by_griffith() -> None:
    # Aufrecht numbers the Valakhilya inline as 8.49-8.59; Griffith prints it as 93-103.
    assert [griffith_page(8, sukta) for sukta in range(49, 60)] == list(range(93, 104))
    # Everything after it shifts back by the eleven displaced hymns.
    assert griffith_page(8, 60) == 49
    assert griffith_page(8, 103) == 92


def test_book_8_hymns_before_the_valakhilya_are_unchanged() -> None:
    assert [griffith_page(8, sukta) for sukta in range(1, 49)] == list(range(1, 49))


def test_the_mapping_is_a_permutation_of_book_8() -> None:
    """Every Griffith page is used exactly once, so no hymn is dropped or duplicated."""
    assert sorted(griffith_page(8, sukta) for sukta in range(1, 104)) == list(range(1, 104))


def test_every_other_mandala_maps_straight_through() -> None:
    for mandala in (1, 2, 3, 4, 5, 6, 7, 9, 10):
        assert [griffith_page(mandala, sukta) for sukta in (1, 49, 55, 60, 191)] == [
            1,
            49,
            55,
            60,
            191,
        ]
