"""The two product surfaces the Samaveda notation changed, asserted end to end.

These live here rather than beside the rest of the GAP-SAMAVEDA_MUSIC-002 regressions in
``tests/domain/test_samaveda_notation_closure.py`` because they need the ``live_client``
fixture, which this package's ``conftest.py`` owns.

Both assertions are about a divergence rather than a value:

*   The capability card's LIVE verdict moved and its FROZEN benchmark verdict did not.
    Rewriting the frozen one would hide that the graph moved; copying it forward would
    publish a limitation that no longer holds. The card is supposed to carry both.

*   A notated verse serves its marks BESIDE the primary text and not as it. The witness is a
    community transcription pinned to one revision, so promoting it would make a community
    archive canonical for 1,136 verses.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

NOTATED = 1136
WITHHELD = 708

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)


@_LIVE
def test_live_the_capability_card_moved_and_the_frozen_grade_did_not(
    live_client: Any,
) -> None:
    """Q82 read NOT_ANSWERABLE / NOT_BUILT on a sentence that is no longer true."""
    response = live_client.get("/api/v1/insights/capabilities", params={"question": 82})
    assert response.status_code == 200
    body = response.json()
    card = body["limits"][0]
    assert card["limit_id"] == "samavedic_melodic_layer"
    assert card["verdict"] == "PARTIALLY_ANSWERABLE"
    assert card["benchmark_verdict"] == "NOT_ANSWERABLE"
    assert card["data_status"] == "PARTIAL"
    assert "No melodic layer of any kind exists" not in card["why"]

    measures = {m["name"]: m["value"] for m in card["measurements"]}
    assert measures["verses_with_source_supplied_notation"] == NOTATED
    assert measures["verses_with_notation_withheld"] == WITHHELD
    assert measures["verses_with_no_notation_disposition_at_all"] == 0
    assert measures["notation_rows_interpreted_into_pitch"] == 0
    assert measures["verse_to_saman_edges"] == 0

    # The withheld FIGURE must travel with the notated one in the prose, not only in the
    # measurements. A card publishing only the positive number would be the same defect in
    # prose that an untyped absence is in data. Asserted as the number rather than the word
    # "withheld", because the sentence can be reworded and the number cannot.
    assert f"{NOTATED:,}" in card["why"]
    assert f"{WITHHELD:,}" in card["why"]

    # The catalogue's own completeness invariant must survive a card changing its live
    # verdict: the published count is derived from the FROZEN verdicts, so moving the live
    # one may not shrink it.
    assert body["unpublished_not_answerable"] == []
    assert (
        body["benchmark_not_answerable_published"] == body["benchmark_not_answerable_total"]
    )


@_LIVE
def test_live_a_notated_verse_serves_its_marks_as_a_parallel_witness(
    live_client: Any,
) -> None:
    """The primary surface still comes first, and the marks are real codepoints."""
    response = live_client.get("/api/v1/passages/VG:SV:KAU:CHANDA:P01:D01:V01")
    assert response.status_code == 200
    surfaces = response.json()["text"]["surfaces"]
    displayable = [s["surface"] for s in surfaces if s["is_displayable"]]
    assert displayable == ["PRIMARY", "PARALLEL_WITNESS"]

    witness = next(s for s in surfaces if s["surface"] == "PARALLEL_WITNESS")
    assert witness["script"] == "DEVANAGARI"
    # Real combining Devanagari Extended cantillation. NOT a private-use font hack, and NOT
    # the U+0301 acute that makes an IAST sibilant indistinguishable from an udatta -- the
    # two forgeries the staging gate refuses and the product must never render.
    assert any(0xA8E0 <= ord(ch) <= 0xA8FF for ch in witness["text"])
    assert not any(0xE000 <= ord(ch) <= 0xF8FF for ch in witness["text"])
    assert "́" not in witness["text"]


@_LIVE
def test_live_a_withheld_verse_serves_no_second_witness(live_client: Any) -> None:
    """The withholding reaches the product, not just the staging file.

    VG:SV:KAU:ARANYA:D01:V01 is withheld under NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT. If it
    served a PARALLEL_WITNESS the reader would see notation for a verse this corpus cannot
    source it for.
    """
    response = live_client.get("/api/v1/passages/VG:SV:KAU:ARANYA:D01:V01")
    assert response.status_code == 200
    surfaces = response.json()["text"]["surfaces"]
    assert [s["surface"] for s in surfaces if s["is_displayable"]] == ["PRIMARY"]
