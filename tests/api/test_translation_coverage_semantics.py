"""What a translation actually covers, on the surfaces a reader and Ask meet it on.

Three shapes reach a verse and only one of them is a rendering of that verse alone. A
``MANTRA_RANGE`` translation is one print unit over a span; a ``REUSED_RENDERING`` is
another corpus's published English on text verified character-identical; a non-English
``language`` is Griffith's Latin substitution. Before this layer existed all three were
indistinguishable from a dedicated 1:1 translation, and each one had a specific untruth it
produced:

* the reader told the 30 even verses of RV 1.65-1.70 that no released translation covered
  them, while a range on the paired verse did;
* any Samavedic English would have read as the Samaveda's own, when every English string
  that will ever reach that corpus is Rigvedic;
* 24 Latin literals were counted in the English coverage figure, overstating the English
  layer by exactly the passages Victorian propriety took out of it.

The tests are written against the shapes rather than against a population count, because a
count passed throughout the first defect: RV 1.65-1.70 had 31 translations before the
correction and 31 after, and what changed was which verse served which text.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from vedagraph.domain import translation_semantics as semantics
from vedagraph.domain.translation_semantics import (
    TranslationCoverageKind,
    UnknownAlignmentLevel,
)
from vedagraph.models.enums import AlignmentLevel

# ---------------------------------------------------------------------------
# The classifier, offline
# ---------------------------------------------------------------------------


def test_a_mantra_alignment_is_a_dedicated_translation() -> None:
    props = {"alignment_level": AlignmentLevel.MANTRA, "language": "en"}
    assert semantics.classify(props) is TranslationCoverageKind.DEDICATED_TRANSLATION
    assert semantics.counts_as_independent_english(props)
    assert semantics.disclosure(props) is None


def test_a_range_alignment_is_never_a_dedicated_translation() -> None:
    """The whole point. A range is real coverage and is not a 1:1 rendering."""
    props = {
        "alignment_level": AlignmentLevel.MANTRA_RANGE,
        "language": "en",
        "covers_canonical_keys": ["VG:RV:SAK:M01:S065:V001", "VG:RV:SAK:M01:S065:V002"],
    }
    assert semantics.classify(props) is TranslationCoverageKind.RANGE_TRANSLATION
    assert semantics.range_is_complete(props)
    assert "2 verses" in (semantics.disclosure(props) or "")


def test_a_range_that_names_one_verse_is_incomplete() -> None:
    """A range over a single key is indistinguishable from a dedicated translation."""
    props = {
        "alignment_level": AlignmentLevel.MANTRA_RANGE,
        "language": "en",
        "covers_canonical_keys": ["VG:RV:SAK:M01:S065:V001"],
    }
    assert not semantics.range_is_complete(props)


def test_reuse_outranks_alignment() -> None:
    """A reused rendering aligned to a mantra is still reused.

    Precedence matters here and it is the branch that would fail silently: the reuse rows
    are all ``MANTRA``-aligned, so a classifier reading alignment first would call all 194
    of them dedicated translations of their target corpus.
    """
    props = {
        "alignment_level": AlignmentLevel.MANTRA,
        "language": "en",
        "reuse_kind": "REUSED_RENDERING",
        "reused_from_veda": "RV",
        "reused_from_passage_key": "VG:RV:SAK:M03:S040:V009",
        "reused_from_citation": "RV 3.40.9",
    }
    assert semantics.classify(props) is TranslationCoverageKind.REUSED_RENDERING
    assert not semantics.is_independent(props)
    assert not semantics.counts_as_independent_english(props)
    disclosure = semantics.disclosure(props) or ""
    assert "reused" in disclosure.lower()
    assert "Rigvedic" in disclosure
    assert "RV 3.40.9" in disclosure


def test_latin_is_coverage_of_the_verse_and_not_of_the_english_layer() -> None:
    props = {"alignment_level": AlignmentLevel.MANTRA, "language": "la"}
    assert semantics.classify(props) is TranslationCoverageKind.DEDICATED_TRANSLATION
    assert semantics.is_independent(props), "Griffith's Latin is his own work on this verse"
    assert not semantics.counts_as_independent_english(props), (
        "and it is not English, so it must not be totalled into the English layer"
    )
    assert "Latin" in (semantics.disclosure(props) or "")


def test_an_undeclared_alignment_level_raises_rather_than_defaulting() -> None:
    """Defaulting is how a fifth alignment level ships as a 1:1 translation.

    The failure mode this forbids is the quiet one: a new level appears in the data, the
    classifier falls through to ``DEDICATED_TRANSLATION``, and the product asserts a
    precision the translator never claimed. An exception is a visible defect.
    """
    with pytest.raises(UnknownAlignmentLevel):
        semantics.classify({"alignment_level": "PADA", "language": "en"})
    with pytest.raises(UnknownAlignmentLevel):
        semantics.classify({"language": "en"})


def test_every_alignment_level_in_the_enum_is_classified() -> None:
    """Enumerate the value space rather than testing the values we happen to expect.

    A member added to ``AlignmentLevel`` without a branch here is exactly the data-model
    change the exception above is meant to surface, and this is what surfaces it at the
    point the enum grows rather than at the point a reader sees the wrong label.
    """
    for level in AlignmentLevel:
        kind = semantics.classify({"alignment_level": level, "language": "en"})
        assert isinstance(kind, TranslationCoverageKind), level


# ---------------------------------------------------------------------------
# The live surfaces
# ---------------------------------------------------------------------------

#: The anchor of a span, the second verse of the same span, the singleton at the end of an
#: 11-verse hymn, and an untouched neighbour. Four shapes, because a fix that made the
#: second verse right by making the singleton wrong would pass any one of them alone.
RANGE_CASES: tuple[tuple[str, str, bool], ...] = (
    ("VG:RV:SAK:M01:S065:V001", "RANGE_TRANSLATION", True),
    ("VG:RV:SAK:M01:S065:V002", "RANGE_TRANSLATION", False),
    ("VG:RV:SAK:M01:S070:V011", "DEDICATED_TRANSLATION", True),
    ("VG:RV:SAK:M01:S001:V001", "DEDICATED_TRANSLATION", True),
)


def _reader(client: TestClient, key: str) -> dict:
    response = client.get(f"/api/v1/passages/{key}/reader")
    assert response.status_code == 200, f"{key}: HTTP {response.status_code}"
    return response.json()


@pytest.mark.neo4j
@pytest.mark.parametrize(("key", "kind", "own"), RANGE_CASES)
def test_the_reader_reports_the_right_coverage_kind(
    live_client: TestClient, key: str, kind: str, own: bool
) -> None:
    rows = _reader(live_client, key)["translations"]["items"]
    assert rows, f"{key} serves no translation"
    assert rows[0]["coverage_kind"] == kind, key
    assert rows[0]["is_this_passages_own"] is own, key


@pytest.mark.neo4j
def test_an_uncovered_verse_is_named_as_uncovered(live_client: TestClient) -> None:
    """The range lookup must not start matching verses it does not cover.

    RV 10.86.16 has no translation of any kind and no unit spans it: the source's page for
    the hymn does not print the verse at all. A range query written without the membership
    test would return every range translation for every verse, and the symptom would be a
    corpus that looks fully covered rather than an error.
    """
    body = _reader(live_client, "VG:RV:SAK:M10:S086:V016")
    block = body["translations"]
    assert block["items"] == [], "RV 10.86.16 has no rendering of any kind"
    assert block["data_status"] != "SUPPORTED", "an empty translation set must not claim SUPPORTED"
    text = " ".join(c["text"] for c in block["caveats"])
    assert "multi-verse print unit" in text, (
        "the empty state must rule out range coverage explicitly, because a reader cannot "
        "tell 'no translation' from 'not one of its own'"
    )


@pytest.mark.neo4j
def test_range_coverage_is_reported_separately_from_dedicated(live_client: TestClient) -> None:
    """The coverage block must not add the two into one percentage."""
    response = live_client.get("/api/v1/works/VG:WORK:RV:SAK")
    assert response.status_code == 200
    coverage = response.json()["translation_coverage"]
    assert coverage["range_covered"] == 60, (
        "30 anchors cover 60 verses; counting the anchors is the arithmetic error"
    )
    assert coverage["dedicated"] == coverage["translated"], (
        "`translated` must mean the dedicated population and nothing wider"
    )
    assert coverage["any_coverage"] == (
        coverage["dedicated"]
        + coverage["range_covered"]
        + coverage["reused_rendering"]
        + coverage["other_language"]
    ), (
        "any_coverage is the union of all four populations, and the Rigveda is why naming "
        "only two is wrong: it has 6 verses whose sole rendering is Griffith's Latin, so "
        "dedicated + range_covered is 6 short of what a rendering actually reaches"
    )
    assert coverage["uncovered"] == coverage["mantras"] - coverage["any_coverage"]
    assert coverage["percent"] == round(100 * coverage["dedicated"] / coverage["mantras"], 2), (
        "the percentage must be divided from the two counts beside it, not transcribed"
    )


@pytest.mark.neo4j
def test_the_coverage_populations_partition_every_corpus(live_client: TestClient) -> None:
    """Four populations plus uncovered must account for the corpus exactly, per Veda.

    Reported per corpus rather than as a total, because a total can be right while two
    corpora are wrong in opposite directions.
    """
    for work in ("VG:WORK:RV:SAK", "VG:WORK:SV:KAU", "VG:WORK:YV:VSM", "VG:WORK:AV:SAU"):
        coverage = live_client.get(f"/api/v1/works/{work}").json()["translation_coverage"]
        total = (
            coverage["dedicated"]
            + coverage["range_covered"]
            + coverage["reused_rendering"]
            + coverage["other_language"]
            + coverage["uncovered"]
        )
        assert total == coverage["mantras"], (
            f"{work}: the populations sum to {total} against a corpus of "
            f"{coverage['mantras']}, so a verse is double-counted or missing"
        )
