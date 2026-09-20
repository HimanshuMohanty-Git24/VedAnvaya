"""RV 1.65-1.70 on the public surfaces, after the spine correction. GAP-TRANSLATION-006.

25 of the span's 31 shipped translations read against the wrong Sanskrit, and the surface that
carried them is the one asserted here: ``/api/v1/passages/{key}`` and its reader view are what
``GAP-TRANSLATION-006`` named as the affected surface, and the frontend reader renders straight
from them.

These are end-to-end and deliberately content-level. A test that only counted translations in
the span would have passed throughout the defect: the count was 31 before and is 31 now. What
changed is *which verse serves which text*, so each case pins a historically wrong pair -- the
verse, a phrase from the English, and a word from its own Sanskrit -- and asserts they belong
together.

One unaffected neighbour is asserted alongside, because a fix that shifted RV 1.71 would be a
worse defect than the one it repaired.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

pytestmark = pytest.mark.neo4j

#: Historically wrong cases, one per hymn plus the two shapes that are special.
#:
#: ``english_fragment`` is a phrase from Griffith's unit; ``sanskrit_fragment`` is a word from
#: the verse the unit renders, taken from our own canonical text. Before the correction the
#: English sat one verse up from the Sanskrit it renders, so asserting both on one verse is
#: what makes these cases falsifiable rather than decorative.
CORRECTED: tuple[tuple[str, str, str, str], ...] = (
    (
        "VG:RV:SAK:M01:S065:V003",
        "The Gods approached the ways of holy Law",
        "vra̱tā",
        "unit 2, which shipped on verse 2",
    ),
    (
        "VG:RV:SAK:M01:S065:V009",
        "Like a swan sitting in the floods",
        "ha̱ṁso",
        "unit 5, which shipped on verse 5",
    ),
    (
        "VG:RV:SAK:M01:S066:V005",
        "With flame insatiate, like eternal might",
        "du̱roka̍śoci",
        "unit 3, which shipped on verse 3",
    ),
    (
        "VG:RV:SAK:M01:S070:V011",
        "Like a brave archer",
        "śūro̱",
        "unit 6: the odd verse of an 11-verse hymn, covered alone",
    ),
)

#: Verses that must not carry a rendering of their own. Each one served a wrong rendering
#: before, so the correction was to stop presenting one -- but the verse is not untranslated:
#: Griffith renders the pair as one unit anchored on the odd verse, and that unit covers it.
#:
#: This tuple was originally asserted as "serves no translation at all", which was the
#: product's behaviour and was itself a false statement to a reader: the reader's empty state
#: told these 30 verses that no released translation covered them while one did. So the
#: assertion below now pins the honest shape instead -- the covering unit is served, marked as
#: anchored elsewhere and not as this verse's own.
COVERED_BY_A_NEIGHBOURS_UNIT: tuple[tuple[str, str], ...] = (
    ("VG:RV:SAK:M01:S065:V002", "VG:RV:SAK:M01:S065:V001"),
    ("VG:RV:SAK:M01:S065:V004", "VG:RV:SAK:M01:S065:V003"),
    ("VG:RV:SAK:M01:S066:V002", "VG:RV:SAK:M01:S066:V001"),
    ("VG:RV:SAK:M01:S070:V006", "VG:RV:SAK:M01:S070:V005"),
)


def _passage(client: TestClient, key: str) -> dict[str, object]:
    response = client.get(f"/api/v1/passages/{key}")
    assert response.status_code == 200, f"{key}: HTTP {response.status_code}"
    body: dict[str, object] = response.json()
    return body


def _sanskrit(body: dict[str, object]) -> str:
    """Every Sanskrit surface the passage serves, concatenated.

    The route returns ``text.surfaces``, a list of witnesses -- primary, parallel, Devanagari.
    Reading all of them rather than the first means a fixture fragment is checked against what
    a reader can actually see, whichever witness the frontend chooses to show.
    """
    text = body.get("text")
    assert isinstance(text, dict), "the passage serves no text block"
    surfaces = text.get("surfaces") or []
    assert isinstance(surfaces, list) and surfaces, "the text block serves no surface"
    return " ".join(str(s.get("text", "")) for s in surfaces if isinstance(s, dict))


def _translations(body: dict[str, object]) -> list[dict[str, object]]:
    """The translation rows out of the paginated envelope the route returns."""
    block = body.get("translations")
    if block is None:
        return []
    assert isinstance(block, dict), f"unexpected translations shape: {type(block).__name__}"
    items = block.get("items") or []
    assert isinstance(items, list)
    return [r for r in items if isinstance(r, dict)]


@pytest.mark.parametrize(
    ("key", "english", "sanskrit", "why"),
    CORRECTED,
    ids=[case[0].rsplit(":", 2)[-2] + "-" + case[0].rsplit(":", 1)[-1] for case in CORRECTED],
)
def test_the_api_serves_each_unit_against_its_own_sanskrit(
    live_client: TestClient, key: str, english: str, sanskrit: str, why: str
) -> None:
    """The defect, asserted where a reader would have met it."""
    body = _passage(live_client, key)
    rows = _translations(body)
    assert rows, f"{key} has no translation ({why})"
    text = " ".join(str(r.get("text", "")) for r in rows)
    assert english in text, f"{key} does not serve {english!r} ({why})"
    assert sanskrit in _sanskrit(body), (
        f"{key}'s own Sanskrit does not contain {sanskrit!r}; the fixture is wrong, "
        "which would make this test pass for the wrong reason"
    )


@pytest.mark.parametrize(("key", "anchor"), COVERED_BY_A_NEIGHBOURS_UNIT)
def test_a_verse_covered_by_its_neighbours_unit_says_so_rather_than_claiming_the_text(
    live_client: TestClient, key: str, anchor: str
) -> None:
    """Serving another verse's rendering is wrong; so is denying that it covers this one.

    The defect this replaces was symmetrical to the one the file was opened for. Attaching
    unit N's English to verse 2N was the first error; answering "no released translation
    covers this passage" once that stopped was the second, and a reader cannot tell a
    withheld translation from an absent one. Both are avoided only if the row is served
    *and* says it is not this verse's own.
    """
    rows = _translations(_passage(live_client, key))
    assert len(rows) == 1, f"{key} should be covered by exactly one unit, got {len(rows)}"
    row = rows[0]
    assert row["coverage_kind"] == "RANGE_TRANSLATION", (
        f"{key} is covered by a multi-verse print unit and must say so, not present the "
        f"rendering as a dedicated translation (got {row['coverage_kind']!r})"
    )
    assert row["is_this_passages_own"] is False, (
        f"{key} has no rendering aligned to it alone, so the row must not claim to be its own"
    )
    assert row["anchor_canonical_key"] == anchor, (
        f"{key} must name the verse its covering unit is anchored on"
    )
    assert key in row["covers_canonical_keys"], (
        f"{key} must appear in the span it is served from, or the claim is unfalsifiable"
    )
    assert row["disclosure"], f"{key}'s covering unit must carry its disclosure sentence"


@pytest.mark.parametrize(
    ("key", "expected_level", "covers"),
    [
        (
            "VG:RV:SAK:M01:S065:V001",
            "MANTRA_RANGE",
            ["VG:RV:SAK:M01:S065:V001", "VG:RV:SAK:M01:S065:V002"],
        ),
        (
            "VG:RV:SAK:M01:S070:V011",
            "MANTRA",
            ["VG:RV:SAK:M01:S070:V011"],
        ),
    ],
)
def test_the_api_states_the_span_a_translation_covers(
    live_client: TestClient,
    live_repository: Neo4jRepository,
    key: str,
    expected_level: str,
    covers: list[str],
) -> None:
    """A row covering two verses must not claim ``MANTRA``.

    That half of the defect survives a correct re-anchoring: unit 1 of RV 1.65 was always on
    verse 1, and it was always claiming to be the translation of verse 1 alone while rendering
    verses 1 and 2 together. The claim is asserted on the API surface and the covered keys in
    the graph, because the API does not expose the key list today.
    """
    rows = _translations(_passage(live_client, key))
    assert rows, key
    assert {str(r.get("alignment_level")) for r in rows} == {expected_level}
    stored = live_repository.run_one(
        "MATCH (:Mantra {canonical_key: $key})-[:HAS_TRANSLATION]->(t:Translation) "
        "RETURN t.covers_canonical_keys AS covers",
        key=key,
    )
    assert stored is not None
    assert list(stored["covers"]) == covers


def test_an_unaffected_neighbouring_hymn_is_untouched(live_client: TestClient) -> None:
    """RV 1.71 is one-to-one with its source and fully translated. It must stay that way."""
    body = _passage(live_client, "VG:RV:SAK:M01:S071:V002")
    rows = _translations(body)
    assert rows, "RV 1.71.2 lost its translation"
    assert {str(r.get("alignment_level")) for r in rows} == {"MANTRA"}
    text = " ".join(str(r.get("text", "")) for r in rows)
    assert "Our sires with lauds burst" in text, (
        "RV 1.71.2 is not serving its own unit; a one-to-one hymn beside the span shifted"
    )
    assert "pi̱taro" in _sanskrit(body), "fixture drift: that is not RV 1.71.2's Sanskrit"


def test_the_span_coverage_metric_did_not_move(live_repository: Neo4jRepository) -> None:
    """31 translated before and after, on 61 verses. The count is not the fix.

    Asserted precisely because it is unchanged: a reader of coverage numbers alone would have
    seen nothing happen, which is why the defect survived a campaign of counting.
    """
    row = live_repository.run_one(
        """
        MATCH (m:Mantra {veda:'RV'})
        WHERE any(p IN $prefixes WHERE m.canonical_key STARTS WITH p)
        RETURN count(m) AS verses,
               sum(CASE WHEN (m)-[:HAS_TRANSLATION]->() THEN 1 ELSE 0 END) AS translated
        """,
        prefixes=[f"VG:RV:SAK:M01:S{n:03d}:" for n in range(65, 71)],
    )
    assert row is not None
    assert int(row["verses"]) == 61
    assert int(row["translated"]) == 31


def test_every_translated_verse_in_the_span_is_an_anchor(
    live_repository: Neo4jRepository,
) -> None:
    """The invariant the registry asked for, stated structurally rather than as a ratio.

    Under a paired spine every translated verse is odd-numbered, because the anchor of the
    pair (2N-1, 2N) is always odd. A single even-numbered translated verse in this span means
    a row drifted back onto a covered verse.
    """
    rows = live_repository.run(
        """
        MATCH (m:Mantra {veda:'RV'})-[:HAS_TRANSLATION]->()
        WHERE any(p IN $prefixes WHERE m.canonical_key STARTS WITH p)
        RETURN m.canonical_key AS key ORDER BY key
        """,
        prefixes=[f"VG:RV:SAK:M01:S{n:03d}:" for n in range(65, 71)],
    )
    even = [str(r["key"]) for r in rows if int(str(r["key"]).rsplit(":V", 1)[1]) % 2 == 0]
    assert not even, f"even-numbered verses carrying a translation: {even}"


def test_no_verse_in_the_span_carries_two_translations(
    live_repository: Neo4jRepository,
) -> None:
    """The correction re-points edges; a botched one would leave a verse with both."""
    rows = live_repository.run(
        """
        MATCH (m:Mantra {veda:'RV'})-[r:HAS_TRANSLATION]->()
        WHERE any(p IN $prefixes WHERE m.canonical_key STARTS WITH p)
        WITH m.canonical_key AS key, count(r) AS n WHERE n > 1
        RETURN key, n
        """,
        prefixes=[f"VG:RV:SAK:M01:S{n:03d}:" for n in range(65, 71)],
    )
    assert not list(rows)
