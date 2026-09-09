"""Contract tests for the ``RishiFamily`` layer.

The layer's whole claim is that a membership rests on a patronymic the Anukramaṇī *states*
and never on two names resembling each other, so the tests that matter here are the ones
that would catch a slide into resemblance. They run offline against the registries and the
committed artifact, because both are decidable without a database and a test needing Neo4j
would be skipped exactly when it was most needed.

The one ``live`` test is read-only and gated on ``VEDAGRAPH_LIVE_NEO4J``, matching
``test_v3_layers.py``: this file must not turn a green suite red on a machine with no
Neo4j.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
from typing import Any

import pytest

from vedagraph.domain.rishi_families import (
    DECLINED_PATRONYMICS,
    GOTRA_PATRONYMICS,
    METHOD_COMPOUND,
    METHOD_FUSED,
    METHOD_TOKEN,
    SURFACE_INDEX,
    RishiEntry,
    coverage,
    derive,
    family_key,
    fold_whitney,
    surfaces,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
ARTIFACT = PROJECT_ROOT / "data" / "domain" / "vedagraph_domain_v2" / "rishi_families_v1.json"


@pytest.fixture(scope="module")
def artifact() -> dict[str, Any]:
    if not ARTIFACT.exists():  # pragma: no cover - the builder has to have been run
        pytest.skip(f"{ARTIFACT} not built")
    parsed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


# ---------------------------------------------------------------------------
# The rule: stated patronymic, never resemblance
# ---------------------------------------------------------------------------


def test_the_eponym_is_not_a_member_of_his_own_family() -> None:
    """``bharadvāja`` must not join ``bhāradvāja``, and the vowel length is the reason.

    This is the single test that separates this layer from string similarity. The two
    labels differ by one vowel and that vowel *is* the descent claim: a non-vṛddhi
    ``bharadvāja`` is the ancestor, a vṛddhi ``bhāradvāja`` is his descendant. A future
    change that folded vowel length "to improve coverage" would raise Yajurvedic coverage
    and would be asserting that every ancestor is his own descendant.
    """
    entries = [
        RishiEntry("K:BHARADVAJA", "bharadvāja", "YV_VSM_RSISUCI"),
        RishiEntry("K:VASISTHA", "vasiṣṭha", "YV_VSM_RSISUCI"),
        RishiEntry("K:ATRI", "atri", "YV_VSM_RSISUCI"),
        RishiEntry("K:BHARADVAJAH-PAYUH", "bhāradvājaḥ pāyuḥ", "RV_WSC2023_ANUKRAMANI"),
    ]
    derivation = derive(entries)
    assigned = {m.entity_key: m.family_stem for m in derivation.memberships}
    assert assigned == {"K:BHARADVAJAH-PAYUH": "bhāradvāja"}
    for key in ("K:BHARADVAJA", "K:VASISTHA", "K:ATRI"):
        assert derivation.unassigned[key][0] == "EPONYM_WITHOUT_STATED_PATRONYMIC"


def test_a_shared_prefix_creates_nothing() -> None:
    """Names that begin like a patronymic but are not one stay unassigned."""
    entries = [
        # Shares four characters with `bhārgava` and is unrelated to Bhṛgu.
        RishiEntry("K:BHAGA", "bhagaḥ", "RV_WSC2023_ANUKRAMANI"),
        # Shares three with `kāṇva` under any fold that ignored vowel length.
        RishiEntry("K:KANVA-PERSON", "kaṇvaḥ", "RV_WSC2023_ANUKRAMANI"),
        RishiEntry("K:ATRI-LIKE", "atrāvī", "RV_WSC2023_ANUKRAMANI"),
    ]
    derivation = derive(entries)
    assert derivation.memberships == []
    assert derivation.families == {}


def test_every_membership_quotes_a_token_present_in_its_source_label(
    artifact: dict[str, Any],
) -> None:
    """The evidence on the edge has to be findable in the string it came from.

    ``source_token`` is what licenses the edge, so if it is not a substring of the label
    the Anukramaṇī printed, the edge is quoting evidence that does not exist. Checked over
    every row rather than a sample, because two random samples once reported 97% accuracy
    in this repository while one alias was 82.9% wrong.
    """
    offenders = [
        row
        for row in artifact["memberships"]
        if row["source_token"] not in fold_whitney(str(row["source_label"])).lower()
    ]
    assert offenders == []


def test_no_declined_patronymic_became_a_family(artifact: dict[str, Any]) -> None:
    """A refusal recorded in the table must be a refusal in the artifact.

    The theonymic and titular patronymics are the tempting ones -- ``aindra``,
    ``prājāpatya``, ``vaivasvata`` -- and reifying them would add 71 memberships and turn
    a gotra layer into a mixed bag of gotras and divine parentage.
    """
    declined_keys = {family_key(stem) for stem in DECLINED_PATRONYMICS}
    assert declined_keys.isdisjoint({row["family_key"] for row in artifact["families"]})
    assert declined_keys.isdisjoint({row["family_key"] for row in artifact["memberships"]})


def test_the_surface_table_is_unambiguous() -> None:
    """No inflected surface belongs to two stems, so membership cannot depend on order."""
    for entry in GOTRA_PATRONYMICS:
        for stem in (entry.stem, *entry.variants):
            for surface in surfaces(stem):
                assert SURFACE_INDEX[surface].stem == entry.stem


def test_declined_and_accepted_stems_do_not_overlap() -> None:
    """A stem cannot be both reified and refused; that would make the refusal a no-op."""
    accepted = {entry.stem for entry in GOTRA_PATRONYMICS} | {
        variant for entry in GOTRA_PATRONYMICS for variant in entry.variants
    }
    assert accepted.isdisjoint(set(DECLINED_PATRONYMICS))


# ---------------------------------------------------------------------------
# The weaker derivation, pinned
# ---------------------------------------------------------------------------

#: Every fused split the three registries produce, checked one by one against the
#: Anukramaṇī reading. Pinned as a *closed* set, not a count: the fused split is the one
#: place this layer supplies a word boundary the source did not print, so a table change
#: that quietly produces a seventeenth split must fail rather than pass at a new number.
EXPECTED_FUSED: dict[str, str] = {
    "bandhuḥ śrutabandhurviprabandhugaupāyanāḥ": "gaupāyana",
    "kāṇvastriśokaḥ": "kāṇva",
    "mānavaścakṣuḥ": "mānava",
    "paurukutsyastrasadasyuḥ": "paurukutsa",
    "pārucchepiranānataḥ": "pārucchepi",
    "vāsiṣṭhaścitramahāḥ": "vāsiṣṭha",
    "āptyastritaḥ": "āptya",
    "śyāvāśvirandhīguḥ": "śyāvāśvi",
    "kumārahārita": "hārita",
    "dadhyaṅṅātharvaṇa": "atharvaṇa",
    "luśodhānāka": "dhānāka",
    "svastyātreya": "ātreya",
}


def test_the_fused_splits_are_exactly_the_audited_set(artifact: dict[str, Any]) -> None:
    fused = {
        str(row["source_label"]): str(row["family_stem"])
        for row in artifact["memberships"]
        if row["method"] == METHOD_FUSED
    }
    # The one label carrying two fused patronymics is checked separately, because a dict
    # keyed on the label cannot hold both.
    two_patronymics = "traivṛṣṇastryaruṇaḥ paurukutsastrasadasyuḥ"
    assert fused.pop(two_patronymics, None) is not None
    assert {
        str(row["family_stem"])
        for row in artifact["memberships"]
        if row["source_label"] == two_patronymics
    } == {"traivṛṣṇa", "paurukutsa"}
    assert fused == EXPECTED_FUSED


def test_a_fused_split_needs_a_whole_patronymic_and_a_real_residue() -> None:
    """``bhārgavaḥ`` alone must not "split" into a patronymic plus a stray visarga."""
    derivation = derive([RishiEntry("K:BHARGAVA-ALONE", "bhārgavaḥ", "RV_WSC2023_ANUKRAMANI")])
    assert [m.method for m in derivation.memberships] == [METHOD_TOKEN]
    assert derivation.decompositions[0].personal_names == ()


def test_descent_stated_in_words_is_marked_as_such() -> None:
    """``vasiṣṭhaputrāḥ`` is descent, and its method must say it came from a compound."""
    derivation = derive([RishiEntry("K:VASISTHAPUTRAH", "vasiṣṭhaputrāḥ", "RV_WSC2023_ANUKRAMANI")])
    assert [(m.family_stem, m.method) for m in derivation.memberships] == [
        ("vāsiṣṭha", METHOD_COMPOUND)
    ]


def test_one_edge_per_rishi_and_family() -> None:
    """``ātreyaḥ svastyātreyaḥ`` states one patronymic twice and must yield one edge.

    Two edges would inflate the Ātreya member count off a single label -- the shape of
    defect where a recorded summary block and the rows themselves disagree.
    """
    derivation = derive(
        [RishiEntry("K:ATREYAH-SVASTYATREYAH", "ātreyaḥ svastyātreyaḥ", "RV_WSC2023_ANUKRAMANI")]
    )
    assert [(m.family_stem, m.method) for m in derivation.memberships] == [("ātreya", METHOD_TOKEN)]


# ---------------------------------------------------------------------------
# The measurement
# ---------------------------------------------------------------------------


def test_member_counts_on_the_family_match_the_membership_rows(
    artifact: dict[str, Any],
) -> None:
    """The recorded count must equal the rows, not the other way round.

    A ``corrections_applied`` block in this repository once recorded nine corrections of
    which one was written into the data. A ``member_count`` property is the same kind of
    claim, so it is recomputed from the rows here rather than trusted.
    """
    tallied: dict[str, int] = {}
    for row in artifact["memberships"]:
        key = str(row["family_key"])
        tallied[key] = tallied.get(key, 0) + 1
    recorded = {str(row["family_key"]): int(row["member_count"]) for row in artifact["families"]}
    assert recorded == tallied


def test_coverage_is_a_fraction_of_every_rishi_not_of_the_assigned_ones(
    artifact: dict[str, Any],
) -> None:
    measured = artifact["coverage"]
    assert measured["total"] == sum(
        bucket["total"] for bucket in measured["per_namespace"].values()
    )
    assert measured["assigned"] == sum(
        bucket["assigned"] for bucket in measured["per_namespace"].values()
    )
    assert measured["assigned"] < measured["total"]
    # Partial coverage, honestly labelled, is the success condition; a layer claiming a
    # family for every ṛṣi would have invented the evidence for roughly 400 of them.
    assert measured["assigned"] == len({row["entity_key"] for row in artifact["memberships"]})
    unassigned = {row["entity_key"] for row in artifact["unassigned"]}
    assert len(unassigned) == measured["total"] - measured["assigned"]
    assert unassigned.isdisjoint({row["entity_key"] for row in artifact["memberships"]})


def test_every_rishi_is_either_assigned_or_classified(artifact: dict[str, Any]) -> None:
    """No ṛṣi falls through: an unassigned one carries the class it was refused under."""
    decomposed = {str(row["entity_key"]) for row in artifact["decompositions"]}
    assert decomposed == {str(row["entity_key"]) for row in artifact["unassigned"]} | {
        str(row["entity_key"]) for row in artifact["memberships"]
    }
    assert all(str(row["reason"]).strip() for row in artifact["unassigned"])


def test_the_artifact_is_reproducible_from_the_registries(artifact: dict[str, Any]) -> None:
    """Re-deriving from the committed registries must give the committed numbers."""
    spec = importlib.util.spec_from_file_location(
        "build_rishi_families", PROJECT_ROOT / "scripts" / "build_rishi_families.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entries, _ = module.load_entries()
    recomputed = coverage(derive(entries), entries)
    assert recomputed == artifact["coverage"]


# ---------------------------------------------------------------------------
# Live, read-only
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("VEDAGRAPH_LIVE_NEO4J"), reason="needs VEDAGRAPH_LIVE_NEO4J")
def test_live_every_membership_edge_carries_full_grading(
    artifact: dict[str, Any],
) -> None:
    """100% of this graph's edges carry grading metadata; this layer must not be the gap."""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))
    try:
        with driver.session() as session:
            landed = session.run(
                "MATCH (:Rishi)-[m:BELONGS_TO_FAMILY]->(:RishiFamily) RETURN count(m) AS c"
            ).single()
            ungraded = session.run(
                "MATCH ()-[m:BELONGS_TO_FAMILY]->() "
                "WHERE m.quality_tier IS NULL OR m.knowledge_layer IS NULL "
                "OR m.grade_basis IS NULL OR m.evidence_basis IS NULL "
                "OR m.source_token IS NULL OR m.derivation IS NULL "
                "RETURN count(m) AS c"
            ).single()
    finally:
        driver.close()
    assert landed is not None and ungraded is not None
    assert landed["c"] == len(artifact["memberships"])
    assert ungraded["c"] == 0
