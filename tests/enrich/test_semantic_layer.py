"""The bounded model layer: what it accepts, and everything it refuses."""

from __future__ import annotations

from vedagraph.enrich.guards import MAX_SEMANTIC_ASSERTIONS_PER_PASSAGE
from vedagraph.enrich.provenance import AssertionState, TrustClass
from vedagraph.enrich.semantic import (
    Extraction,
    ObjectVocabulary,
    SemanticPacket,
    ingest_extractions,
)

PACKET = SemanticPacket(
    passage_key="VG:RV:SAK:M01:S001:V001",
    veda="RV",
    citation="RV 1.1.1",
    sanskrit="agním īḷe puróhitaṁ yajñásya devám r̥tvíjam",
    translations=("I laud Agni, the chosen Priest, God, minister of sacrifice.",),
    devatas=("VG:DEVATA:AGNIH",),
    rishis=(),
    chandas=(),
    concepts=("VG:CONCEPT:AGNI-FIRE",),
    cross_veda_parallels=(),
)

VOCAB = ObjectVocabulary(
    concepts={"VG:CONCEPT:AGNI-FIRE": "fire", "VG:CONCEPT:YAJNA-SACRIFICE": "sacrifice"},
    devatas={"VG:DEVATA:AGNIH": "agniḥ"},
)


def _extraction(**overrides: object) -> Extraction:
    base: dict[str, object] = {
        "passage_key": PACKET.passage_key,
        "predicate": "PRAISES",
        "object_label": "VG:DEVATA:AGNIH",
        "object_type": "COSMIC_ENTITY",
        "evidence_quote": "I laud Agni, the chosen Priest",
        "confidence": 0.8,
    }
    base.update(overrides)
    return Extraction(**base)  # type: ignore[arg-type]


def _ingest(*extractions: Extraction) -> tuple[list[object], object]:
    rows, report = ingest_extractions(list(extractions), [PACKET], VOCAB, "claude-opus-5")
    return list(rows), report


def test_a_well_formed_proposal_becomes_a_candidate_never_an_accepted_fact() -> None:
    rows, _ = _ingest(_extraction())
    assert len(rows) == 1
    row = rows[0]
    assert row.provenance.trust is TrustClass.LLM_EXTRACTED  # type: ignore[attr-defined]
    assert row.provenance.state is AssertionState.CANDIDATE  # type: ignore[attr-defined]
    assert row.provenance.model == "claude-opus-5"  # type: ignore[attr-defined]
    assert row.object_key == "VG:DEVATA:AGNIH"  # type: ignore[attr-defined]


def test_a_predicate_the_frozen_ontology_refuses_by_name_is_rejected_as_such() -> None:
    rows, report = _ingest(_extraction(predicate="CAUSES"))
    assert rows == []
    assert report.report.rejected["predicate_refused_by_name"] == 1  # type: ignore[attr-defined]


def test_an_invented_predicate_is_rejected_as_unknown() -> None:
    rows, report = _ingest(_extraction(predicate="IDENTIFIES_WITH"))
    assert rows == []
    assert report.report.rejected["predicate_unknown"] == 1  # type: ignore[attr-defined]


def test_a_quote_that_is_not_in_the_packet_is_not_evidence() -> None:
    """A paraphrased quote cannot be checked, so it does not count as evidence."""
    rows, report = _ingest(_extraction(evidence_quote="Agni is described as a divine priest"))
    assert rows == []
    assert report.report.rejected["evidence_not_in_packet"] == 1  # type: ignore[attr-defined]


def test_a_proposal_about_a_passage_that_was_not_in_its_packet_is_rejected() -> None:
    rows, report = _ingest(_extraction(passage_key="VG:AV:SAU:K01:S001:V001"))
    assert rows == []
    assert report.report.rejected["passage_not_in_any_packet"] == 1  # type: ignore[attr-defined]


def test_an_object_outside_the_registry_is_rejected_rather_than_minted() -> None:
    """The graph must not grow nodes that exist only because a model named them."""
    rows, report = _ingest(_extraction(object_label="the cosmic egg"))
    assert rows == []
    assert report.report.rejected["object_not_in_vocabulary"] == 1  # type: ignore[attr-defined]


def test_an_object_type_the_predicate_does_not_admit_is_rejected() -> None:
    rows, report = _ingest(_extraction(predicate="REFERS_TO_PLACE", object_type="SUBSTANCE"))
    assert rows == []
    assert "object_type_invalid_for_predicate" in report.report.rejected  # type: ignore[attr-defined]


def test_a_passage_cannot_contribute_more_than_the_cap() -> None:
    many = [
        _extraction(object_label=label, predicate=predicate)
        for label, predicate in [
            ("VG:DEVATA:AGNIH", "PRAISES"),
            ("VG:DEVATA:AGNIH", "INVOKES"),
            ("VG:CONCEPT:AGNI-FIRE", "ASSOCIATED_WITH"),
            ("VG:CONCEPT:YAJNA-SACRIFICE", "ASSOCIATED_WITH"),
            ("VG:CONCEPT:AGNI-FIRE", "DESCRIBES"),
            ("VG:CONCEPT:YAJNA-SACRIFICE", "DESCRIBES"),
            ("VG:CONCEPT:AGNI-FIRE", "CONTRASTS_WITH"),
            ("VG:CONCEPT:YAJNA-SACRIFICE", "CONTRASTS_WITH"),
        ]
    ]
    rows, report = _ingest(*many)
    assert len(rows) <= MAX_SEMANTIC_ASSERTIONS_PER_PASSAGE
    assert report.report.capped.get("assertions_per_passage", 0) > 0  # type: ignore[attr-defined]


def test_ingestion_is_order_independent() -> None:
    """The model may return proposals in any order; the artifact must not depend on it."""
    a = _extraction(object_label="VG:DEVATA:AGNIH", predicate="PRAISES")
    b = _extraction(object_label="VG:CONCEPT:AGNI-FIRE", predicate="ASSOCIATED_WITH")
    forward, _ = _ingest(a, b)
    backward, _ = _ingest(b, a)
    assert [r.as_row() for r in forward] == [r.as_row() for r in backward]  # type: ignore[attr-defined]


def test_the_packet_digest_changes_when_the_packet_does() -> None:
    other = SemanticPacket(**{**PACKET.as_dict(), "sanskrit": "different text"})  # type: ignore[arg-type]
    assert other.digest != PACKET.digest
    assert PACKET.digest == SemanticPacket(**PACKET.as_dict()).digest  # type: ignore[arg-type]
