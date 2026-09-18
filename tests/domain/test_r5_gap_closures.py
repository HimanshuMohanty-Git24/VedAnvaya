"""Regression tests for the gaps Release Blocker Closure R5 closed.

Each block names its gap and pins the thing that was WRONG, not merely the thing that is
now right. Several of these gaps closed by replacing a metric that could not be satisfied
truthfully, so the test refuses the old metric's satisfying form by name: a count that
merely looks healthy would pass again the moment someone reinstated the old reading.

Live tests are gated on ``VEDAGRAPH_LIVE_NEO4J`` and are reported by
``scripts/release_test_accounting.py`` under that gate, so a failure here cannot vanish
from a release report by being skipped.
"""

from __future__ import annotations

import os
import pathlib
import sys
from typing import Any

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)


def _driver() -> Any:
    from neo4j import GraphDatabase

    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))


def _scalar(query: str, **params: Any) -> Any:
    driver = _driver()
    try:
        with driver.session() as session:
            record = session.run(query, **params).single()
            return None if record is None else record[0]
    finally:
        driver.close()


def _rows(query: str, **params: Any) -> list[dict[str, Any]]:
    driver = _driver()
    try:
        with driver.session() as session:
            return [record.data() for record in session.run(query, **params)]
    finally:
        driver.close()


# ---------------------------------------------------------------------------
# GAP-ENTITY_COVERAGE-007 clause 1 -- the phrase pass, and why it needs its own table
# ---------------------------------------------------------------------------


def _mantra(key: str, veda: str, text: str) -> Any:
    """A MantraRecord whose folded surface is exactly ``text``.

    Built through the production ``build_surfaces`` so the test cannot pass on a surface
    the matcher never sees.
    """
    from vedagraph.enrich.corpus import MantraRecord
    from vedagraph.enrich.surfaces import build_surfaces

    surfaces = build_surfaces(key, veda, "Latin", text)
    return MantraRecord(
        passage_key=key,
        passage_id=key,
        veda=veda,
        citation=key,
        surfaces=surfaces,
    )


def _concept(concept_id: str, aliases: tuple[str, ...], phrases: tuple[str, ...]) -> Any:
    from vedagraph.enrich.records import ConceptRow

    return ConceptRow(
        concept_id=concept_id,
        preferred_label_sa="x",
        preferred_label_en="x",
        node_type="ACTION",
        aliases_sa=aliases,
        aliases_en=(),
        broader=(),
        definition="d",
        related_devatas=(),
        aliases_sa_phrases=phrases,
    )


def test_a_multiword_alias_in_aliases_sa_can_never_match_which_is_why_the_phrase_table_exists():
    """The defect, pinned. ``index.token`` is keyed by ONE folded token.

    A multi-word string placed there can never equal a key, so it matches nothing forever
    and reports nothing about having done so. GAP-ENTITY_COVERAGE-007's clause 1 was open
    for exactly this reason, and the registry entry for the third pressing documents it.
    """
    from vedagraph.domain.mentions import build_index

    index = build_index([_concept("VG:CONCEPT:X", ("tṛtīye savane",), ())])
    assert index.phrase == (), "a plain alias must not silently become a phrase"
    assert all(" " not in key for key in index.token) is False or True
    # the multi-word alias IS in the token table, and that is the point: it is unmatchable
    assert any(" " in key for key in index.token), (
        "the multi-word alias sits in the single-token table, where nothing can ever "
        "match it -- this is the shape the phrase table exists to avoid"
    )


def test_the_phrase_pass_fires_on_a_run_of_consecutive_tokens():
    from vedagraph.domain.mentions import extract_mentions
    from vedagraph.enrich.corpus import Corpus

    entity = _concept("VG:CONCEPT:THIRD", (), ("tṛtīye savane",))
    mantra = _mantra("VG:TEST:1", "RV", "agne tṛtīye savane hi kāniṣaḥ")
    rows, report = extract_mentions(Corpus(mantras=[mantra]), [entity])
    assert [r.entity_key for r in rows] == ["VG:CONCEPT:THIRD"]
    assert rows[0].paths == ("sanskrit-phrase",)
    assert report.notes["mentions_by_path"]["sanskrit-phrase"] == 1


def test_the_phrase_pass_does_not_fire_inside_a_longer_word():
    """The boundary control. Without it a phrase pass is a substring pass in disguise.

    ``RIGVEDA_LEXICAL_MENTION_POLICY.md`` forbids substring matching, and the Samaveda-only
    sandhi pass is the one documented exception. A phrase matched over the token SEQUENCE
    cannot reach inside a token at all, and this is what proves it.
    """
    from vedagraph.domain.mentions import extract_mentions
    from vedagraph.enrich.corpus import Corpus

    entity = _concept("VG:CONCEPT:THIRD", (), ("tṛtīye savane",))
    # the phrase's characters are present, glued into single tokens
    glued = _mantra("VG:TEST:2", "RV", "agne tṛtīyesavane hi")
    rows, _ = extract_mentions(Corpus(mantras=[glued]), [entity])
    assert rows == [], "a phrase must not fire across a token boundary it does not have"


def test_a_phrase_with_an_unfoldable_part_is_refused_rather_than_shortened():
    from vedagraph.domain.mentions import build_index

    index = build_index([_concept("VG:CONCEPT:X", (), ("tṛtīye ।",))])
    assert index.phrase == (), (
        "a phrase one of whose parts folds to nothing has a hole in it and would match a "
        "run it does not describe"
    )


@_LIVE
def test_live_the_multiword_entities_are_reached():
    """GAP-ENTITY_COVERAGE-007 clause 1, against the store.

    The six loci are the six the registry's own definition names as read-but-unreachable,
    which is why this asserts the set and not merely the count.
    """
    reached = {
        row["key"]
        for row in _rows(
            """
            MATCH (p:Passage)-[r:MENTIONS_ENTITY]->
                  (e:DomainEntity {entity_key:'VG:CONCEPT:TRTIYA-SAVANA-THIRD-PRESSING'})
            WHERE r.method = 'domain-mention-v1:sanskrit-phrase'
            RETURN p.canonical_key AS key
            """
        )
    }
    assert reached == {
        "VG:RV:SAK:M03:S028:V005",
        "VG:RV:SAK:M04:S034:V004",
        "VG:RV:SAK:M04:S035:V009",
        "VG:RV:SAK:M08:S057:V001",
        "VG:AV:SAU:K06:S047:V003",
        "VG:AV:SAU:K09:S001:V013",
    }


@_LIVE
def test_live_every_natural_phenomenon_states_whether_its_phrase_evidence_exists():
    assert (
        _scalar(
            "MATCH (n:NaturalPhenomenon) WHERE n.personification_match_basis IS NULL "
            "RETURN count(n)"
        )
        == 0
    )
    bases = {
        row["basis"]: row["c"]
        for row in _rows(
            "MATCH (n:NaturalPhenomenon) RETURN n.personification_match_basis AS basis, "
            "count(*) AS c"
        )
    }
    # A refusal is a statement about the REGISTRY, so it has no source phrase to ground.
    # UNAVAILABLE must therefore be a real value, not an absence.
    assert bases == {"DETERMINISTIC": 6, "UNAVAILABLE": 7}


# ---------------------------------------------------------------------------
# GAP-TRANSLATION-004 -- the metric that could not be satisfied without reviving 006
# ---------------------------------------------------------------------------


def test_the_bad_old_translation_reading_fails_and_the_truthful_one_passes():
    """The regression the R5 brief asked for, both directions.

    004's metric asked for a HAS_TRANSLATION edge on every RV mantra. Reaching 0 means
    attaching an own edge to each even verse of RV 1.65-1.70, which republishes one
    paired-dvipada Griffith unit as two independent per-verse translations -- exactly
    GAP-TRANSLATION-006's defect. So the BAD reading must FAIL and the truthful one PASS.
    """
    from vedagraph.domain.translation_semantics import (
        INDEPENDENT_ENGLISH_STATES,
        VerseCoverageState,
        verse_coverage_state,
    )

    anchor = {
        "alignment_level": "MANTRA_RANGE",
        "language": "en",
        "covers_canonical_keys": [
            "VG:RV:SAK:M01:S065:V001",
            "VG:RV:SAK:M01:S065:V002",
        ],
    }

    # BAD reading: give the even verse its own dedicated edge to make the count 0.
    bad = verse_coverage_state(
        "VG:RV:SAK:M01:S065:V002",
        [{"alignment_level": "MANTRA", "language": "en"}],
    )
    assert bad is VerseCoverageState.DEDICATED_TRANSLATION
    assert bad is not VerseCoverageState.RANGE_COVERED, (
        "this is the FAILING case: the even verse of a paired-dvipada unit reported as "
        "carrying its own 1:1 rendering is GAP-TRANSLATION-006's defect reinstated"
    )

    # TRUTHFUL reading: the verse is covered, by the span anchored on its odd partner.
    truthful = verse_coverage_state(
        "VG:RV:SAK:M01:S065:V002", [], range_covered=True
    )
    assert truthful is VerseCoverageState.RANGE_COVERED
    assert truthful in INDEPENDENT_ENGLISH_STATES

    # And the anchor itself is not a dedicated translation either.
    assert (
        verse_coverage_state("VG:RV:SAK:M01:S065:V001", [anchor])
        is VerseCoverageState.RANGE_TRANSLATION_ANCHOR
    )


def test_a_reused_rendering_is_never_counted_as_the_corpus_own_english():
    from vedagraph.domain.translation_semantics import (
        INDEPENDENT_ENGLISH_STATES,
        VerseCoverageState,
        verse_coverage_state,
    )

    state = verse_coverage_state(
        "VG:SV:KAU:CHANDA:P01:D01:V01",
        [
            {
                "alignment_level": "MANTRA",
                "language": "en",
                "reuse_kind": "REUSED_RENDERING",
                "reused_from_veda": "RV",
            }
        ],
    )
    assert state is VerseCoverageState.REUSED_RENDERING
    assert state not in INDEPENDENT_ENGLISH_STATES, (
        "all 173 Samavedic renderings are Griffith's Rigvedic English on verified-identical "
        "Sanskrit. Totalling them into the Samaveda's own English coverage reports 173 "
        "translations for a corpus that has 0."
    )


def test_an_uncovered_verse_is_not_erased_to_reach_zero():
    from vedagraph.domain.translation_semantics import (
        UNCOVERED_STATES,
        VerseCoverageState,
        verse_coverage_state,
    )

    assert (
        verse_coverage_state("VG:RV:SAK:M10:S086:V016", [])
        is VerseCoverageState.UNCOVERED_NO_RENDERING_REACHES_IT
    )
    assert (
        verse_coverage_state("VG:SV:KAU:X", [], reusable_parallel=True)
        is VerseCoverageState.UNCOVERED_REUSABLE_PARALLEL_AVAILABLE
    )
    assert UNCOVERED_STATES == {
        VerseCoverageState.UNCOVERED_NO_RENDERING_REACHES_IT,
        VerseCoverageState.UNCOVERED_REUSABLE_PARALLEL_AVAILABLE,
    }


@_LIVE
def test_live_every_mantra_carries_a_typed_translation_coverage_state():
    assert (
        _scalar(
            "MATCH (m:Mantra) WHERE m.translation_coverage_state IS NULL RETURN count(m)"
        )
        == 0
    )
    # The Samaveda's independent English coverage is ZERO and must read as zero.
    assert (
        _scalar(
            """
            MATCH (m:Mantra {veda:'SV'})
            WHERE m.translation_coverage_state IN
              ['DEDICATED_TRANSLATION','RANGE_TRANSLATION_ANCHOR','RANGE_COVERED',
               'CONTAINER_TRANSLATION']
            RETURN count(m)
            """
        )
        == 0
    )
    # The six genuinely uncovered Rigvedic verses are still visible.
    assert (
        _scalar(
            """
            MATCH (m:Mantra {veda:'RV'})
            WHERE m.translation_coverage_state = 'UNCOVERED_NO_RENDERING_REACHES_IT'
            RETURN count(m)
            """
        )
        == 6
    )


# ---------------------------------------------------------------------------
# GAP-SEMANTICS-003 -- the slots were unpopulated, not undeclared
# ---------------------------------------------------------------------------


def test_the_assertion_slot_range_already_admitted_domain_entity():
    """Pinned so a later pass cannot "widen" a range that was never narrow.

    The entry's implementation_dependency asked to widen ASSERTION_AGENT and
    ASSERTION_TARGET beyond :Devata. Both were already declared over
    {Devata, DomainEntity}; what was missing was any edge.
    """
    from vedagraph.domain.ontology import (
        LABEL_DEVATA,
        LABEL_DOMAIN_ENTITY,
        REL_ASSERTION_AGENT,
        REL_ASSERTION_TARGET,
        RELATIONSHIP_SIGNATURES,
    )

    for predicate in (REL_ASSERTION_AGENT, REL_ASSERTION_TARGET):
        _, allowed = RELATIONSHIP_SIGNATURES[predicate]
        assert LABEL_DEVATA in allowed
        assert LABEL_DOMAIN_ENTITY in allowed


@_LIVE
def test_live_assertions_carry_all_three_slots_and_a_non_devata_target():
    assert (
        _scalar(
            "MATCH (a:SemanticAssertion)-[:ASSERTION_TARGET]->(x) WHERE NOT x:Devata "
            "RETURN count(*)"
        )
        > 0
    )
    assert (
        _scalar(
            """
            MATCH (a:SemanticAssertion)
            WHERE (a)-[:ASSERTION_AGENT]->() AND (a)-[:ASSERTION_PREDICATE]->()
              AND (a)-[:ASSERTION_TARGET]->()
            RETURN count(a)
            """
        )
        > 0
    )


@_LIVE
def test_live_the_projected_slot_edges_do_not_blend_their_derivation():
    """Every projected edge names its derivation, so it cannot be read as the other pass.

    The entry's warning was about blending tiers. The projection carries its own
    derivation and the RoleFiller's evidence, and the pre-existing edges carry neither, so
    the two populations stay separable by query.
    """
    rows = {
        row["derivation"]: row["c"]
        for row in _rows(
            "MATCH ()-[r:ASSERTION_AGENT|ASSERTION_TARGET]->() "
            "RETURN r.derivation AS derivation, count(*) AS c"
        )
    }
    assert rows.get("TREEBANK_DEPREL_ROLE_PROJECTION", 0) == 277
    assert (
        _scalar(
            "MATCH ()-[r:ASSERTION_AGENT|ASSERTION_TARGET]->() "
            "WHERE r.derivation = 'TREEBANK_DEPREL_ROLE_PROJECTION' "
            "AND (r.evidence IS NULL OR r.projected_from_role_filler_key IS NULL) "
            "RETURN count(r)"
        )
        == 0
    ), "a projected edge with no evidence and no source filler is unauditable"


@_LIVE
def test_live_only_agent_and_patient_were_projected():
    """BENEFICIARY, GOAL, INSTRUMENT, LOCATION and SOURCE are distinct roles.

    Folding them into the target slot would make "target" mean five things, which is the
    blending the entry forbids.
    """
    roles = {
        row["role"]
        for row in _rows(
            "MATCH ()-[r:ASSERTION_AGENT|ASSERTION_TARGET]->() "
            "WHERE r.projected_from_role IS NOT NULL "
            "RETURN DISTINCT r.projected_from_role AS role"
        )
    }
    assert roles == {"AGENT", "PATIENT"}


# ---------------------------------------------------------------------------
# GAP-QUALITY-003 -- a tier is not a probability, and there is no human gold
# ---------------------------------------------------------------------------


@_LIVE
def test_live_no_predicate_carries_a_single_constant_confidence():
    assert (
        _scalar(
            """
            MATCH ()-[r]->() WHERE r.confidence IS NOT NULL
            WITH type(r) AS t, collect(DISTINCT r.confidence) AS vals
            WHERE size(vals) = 1
            RETURN count(*)
            """
        )
        == 0
    )


@_LIVE
def test_live_every_surviving_confidence_discloses_that_it_is_uncalibrated():
    assert (
        _scalar(
            "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL "
            "AND r.calibration_status IS NULL RETURN count(r)"
        )
        == 0
    )


@_LIVE
def test_live_the_reference_set_is_not_relabelled_human_gold():
    """Project policy: the available reference set is independently source-adjudicated.

    Relabelling it HUMAN_GOLD would manufacture a review that did not happen, so nothing
    in the graph may claim one.
    """
    assert (
        _scalar(
            "MATCH (n) WHERE n.is_human_gold = true RETURN count(n)"
        )
        == 0
    )
    assert (
        _scalar(
            "MATCH ()-[r]->() WHERE r.reference_set_available IS NOT NULL "
            "AND r.reference_set_available <> 'INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET' "
            "RETURN count(r)"
        )
        == 0
    )


# ---------------------------------------------------------------------------
# GAP-RITUAL-003 / -005 -- a refusal must be tellable from an unattempted row
# ---------------------------------------------------------------------------


@_LIVE
def test_live_yupa_reads_three_vedas_with_both_vsm_verses_matched():
    row = _rows(
        """
        MATCH (e:DomainEntity {entity_key:'VG:CONCEPT:YUPA-SACRIFICIAL-POST'})
        RETURN e.vedas_with_matches AS vedas, size(e.aliases_sa) AS aliases
        """
    )[0]
    assert row["vedas"] == 3
    assert row["aliases"] == 11
    for key in ("VG:YV:VSM:A19:V017", "VG:YV:VSM:A25:V029"):
        assert (
            _scalar(
                "MATCH (p:Passage {canonical_key:$k})-[:MENTIONS_ENTITY]->"
                "(:DomainEntity {entity_key:'VG:CONCEPT:YUPA-SACRIFICIAL-POST'}) "
                "RETURN count(*)",
                k=key,
            )
            == 1
        ), key


@_LIVE
def test_live_the_refused_ritual_objects_are_typed_refusals_not_silence():
    """dundubhi and audumbara are refused on READ evidence, and say so.

    The clause named three objects. Only mani is stated by a source: the dundubhi candidate
    is a simile inside a quoted mantra, and every audumbara line in the apparatus is
    udumbara WOOD against a node defined as an amulet. An untyped absence would be
    indistinguishable from nobody having looked.
    """
    rows = {
        row["k"]: row
        for row in _rows(
            """
            UNWIND ['VG:CONCEPT:MANI-AMULET','VG:CONCEPT:DUNDUBHI-DRUM',
                    'VG:CONCEPT:AUDUMBARA-AMULET'] AS k
            MATCH (e:DomainEntity {entity_key:k})
            RETURN k, e.ritual_use_status AS status, e.ritual_use_refusal_code AS code,
                   e.ritual_use_candidate_quote AS quote
            """
        )
    }
    assert rows["VG:CONCEPT:MANI-AMULET"]["status"] == "ASSERTED_SOURCE_STATES_USE"
    for key in ("VG:CONCEPT:DUNDUBHI-DRUM", "VG:CONCEPT:AUDUMBARA-AMULET"):
        assert rows[key]["status"] == "REFUSED_SOURCE_DOES_NOT_STATE_A_RITE_USES_IT"
        assert rows[key]["code"], f"{key} must name WHY it was refused"
        assert rows[key]["quote"], f"{key} must carry the line that was read"
    # and no edge was minted for either
    for key in ("VG:CONCEPT:DUNDUBHI-DRUM", "VG:CONCEPT:AUDUMBARA-AMULET"):
        assert (
            _scalar(
                "MATCH (:Ritual)-[:USES_OBJECT]->(e:DomainEntity {entity_key:$k}) "
                "RETURN count(*)",
                k=key,
            )
            == 0
        ), key


@_LIVE
def test_live_every_rite_states_its_offering_position_and_no_probable_row_was_imported():
    assert _scalar("MATCH (r:Ritual) WHERE r.offering_status IS NULL RETURN count(r)") == 0
    dist = {
        row["status"]: row["c"]
        for row in _rows(
            "MATCH (r:Ritual) RETURN r.offering_status AS status, count(*) AS c"
        )
    }
    assert sum(dist.values()) == 103
    assert dist["OFFERING_CANDIDATE_REFUSED_AS_CO_OCCURRENCE"] == 51, (
        "the 258 PROBABLE rite-to-offering rows rest on one sutra naming both a rite and an "
        "offering. Clause 3 of this gap forbids asserting co-occurrence, so they stay "
        "candidates."
    )
    assert _scalar("MATCH ()-[r:USES_OFFERING]->() RETURN count(r)") == 4


@_LIVE
def test_live_ritual_context_precision_states_that_no_human_reviewed_it():
    rows = _rows(
        """
        MATCH (m:DerivedMetric {metric_name:'RITUAL_CONTEXT_PRECISION'})
        RETURN m.review_level AS level, m.human_reviewed AS human,
               m.is_human_gold AS gold, m.reference_set_class AS cls
        """
    )
    assert len(rows) == 1
    assert rows[0]["level"] == "AGENT_ADJUDICATED_SINGLE_READER_NO_HUMAN_REVIEW"
    assert rows[0]["human"] == 0
    assert rows[0]["gold"] is False
    assert rows[0]["cls"] == "INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET"


# ---------------------------------------------------------------------------
# GAP-SAMAVEDA_MUSIC-003 clause 1 -- a published number, not our own array order
# ---------------------------------------------------------------------------


@_LIVE
def test_live_the_sv_running_number_is_not_an_enumerate_over_our_own_ordering():
    """The control that makes this a source figure rather than a restatement.

    An ``enumerate()`` over 1,844 verses is exactly 1..1844 contiguous. The published
    series spans 1..1875 with 31 absences, and each absence is a verse the source prints
    and this release withholds a canonical key for.
    """
    assert (
        _scalar(
            "MATCH (m:Mantra {veda:'SV'}) WHERE m.running_samhita_number IS NULL "
            "RETURN count(m)"
        )
        == 0
    )
    row = _rows(
        """
        MATCH (m:Mantra {veda:'SV'})
        RETURN min(m.running_samhita_number) AS lo, max(m.running_samhita_number) AS hi,
               count(DISTINCT m.running_samhita_number) AS distinct
        """
    )[0]
    assert (row["lo"], row["hi"], row["distinct"]) == (1, 1875, 1844)
    assert row["hi"] - row["lo"] + 1 != row["distinct"], (
        "a contiguous run of exactly 1,844 would be this corpus's own index, not the "
        "source's printed number"
    )


@_LIVE
def test_live_clause_two_of_samaveda_music_003_is_not_quietly_claimed():
    """MUSICALIZED_AS is still empty and its object end still does not exist.

    Clause 1 closed; clause 2 did not. Pinned so a later pass cannot report the entry
    closed while the melodic layer is absent.
    """
    assert _scalar("MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)") == 0
    assert (
        _scalar(
            "MATCH (n) WHERE n.work_id STARTS WITH 'VG:WORK:SV:KAU:GANA' "
            "OR n.canonical_key STARTS WITH 'VG:SV:KAU:GANA' RETURN count(n)"
        )
        == 0
    )


# ---------------------------------------------------------------------------
# GAP-ENTITY_COVERAGE-004 / -006 -- provenance, and a denominator that is typed
# ---------------------------------------------------------------------------


@_LIVE
def test_live_no_entity_pretends_a_source_predicted_it():
    """223 of 384 keep ``expected_source`` null ON PURPOSE.

    A closure that populates all 384 is decorative field completion and must be rejected
    on sight, so this test refuses it in both directions.
    """
    assert (
        _scalar("MATCH (n:DomainEntity) WHERE n.expectation_origin IS NULL RETURN count(n)")
        == 0
    )
    assert (
        _scalar(
            """
            MATCH (n:DomainEntity)
            WHERE n.expected_source IS NOT NULL
              AND n.expectation_origin <> 'EXPLICITLY_EXPECTED_BY_A_SOURCE'
            RETURN count(n)
            """
        )
        == 0
    )
    assert (
        _scalar(
            "MATCH (n:DomainEntity) WHERE n.externally_expected = true "
            "AND n.expected_source IS NULL RETURN count(n)"
        )
        == 0
    )
    assert (
        _scalar("MATCH (n:DomainEntity) WHERE n.expected_source IS NULL RETURN count(n)")
        == 223
    ), (
        "if this reaches 0 somebody has put a source on every row, which is the one thing "
        "the provenance field exists to prevent"
    )


@_LIVE
def test_live_the_ayas_cell_stays_zero_and_says_why():
    """A zero lexical match on a verse we have READ the entity in is not an absence.

    VG:YV:VSM:A18:V013 names ayas as a sandhi-elided avagraha plus ``yas``, which the
    search fold reduces to a token indistinguishable from the relative pronoun and from
    the -ayas plural stems in the same line. Forcing this positive needs an alias that
    manufactures false positives inside the witness verse itself.
    """
    assert (
        _scalar(
            "MATCH (m:Mantra {veda:'YV'})-[:MENTIONS_ENTITY]->(e) "
            "WHERE e.entity_key='VG:CONCEPT:AYAS-METAL' RETURN count(DISTINCT m)"
        )
        == 0
    )
    assert (
        _rows(
            "MATCH (e:DomainEntity {entity_key:'VG:CONCEPT:AYAS-METAL'}) "
            "RETURN e.recall_applicability AS cls"
        )[0]["cls"]
        == "SOURCE_ATTESTED_NONLEXICAL"
    )


@_LIVE
def test_live_recall_applicability_partitions_the_registry():
    dist = {
        row["cls"]: row["c"]
        for row in _rows(
            "MATCH (n:DomainEntity) RETURN n.recall_applicability AS cls, count(*) AS c"
        )
    }
    assert None not in dist
    assert sum(dist.values()) == 384
    assert dist == {
        "LEXICAL_RECOVERY_APPLICABLE": 163,
        "NOT_APPLICABLE": 155,
        "INSUFFICIENT_EVIDENCE": 65,
        "SOURCE_ATTESTED_NONLEXICAL": 1,
    }


# ---------------------------------------------------------------------------
# GAP-PRODUCT_SURFACE-005 -- the four Samavedic verses, and their consequences
# ---------------------------------------------------------------------------

_APPARATUS_TOKENS = ("dra", "āraṇyakagānam", "āraṇyakam", "ārṣeyabrāhmaṇam", "bhāṣyam")
_CORRECTED = (
    "VG:SV:KAU:CHANDA:P01:D08:V04",
    "VG:SV:KAU:ARANYA:D01:V04",
    "VG:SV:KAU:CHANDA:P04:D05:V06",
    "VG:SV:KAU:CHANDA:P02:D07:V07",
)


@_LIVE
def test_live_no_apparatus_token_survives_on_the_four_corrected_verses():
    """Both text roles, not just the one the staged Cypher named.

    The staged proposal corrected the row matching ``old_sha256``, which is PRIMARY_TEXT.
    The apparatus also sat in SEARCH_DERIVATIVE, where it was a searchable token.
    """
    for row in _rows(
        """
        MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
        WHERE p.canonical_key IN $keys
        RETURN p.canonical_key AS key, t.text_role AS role, t.text_nfc AS text,
               t.text_original AS original
        """,
        keys=list(_CORRECTED),
    ):
        first = (row["text"] or "").split()[:1]
        assert first and first[0] not in _APPARATUS_TOKENS, (
            f"{row['key']} {row['role']} still opens on an apparatus token"
        )
        # text_original too, and this is Agent B's M01: R5's first pass set text_nfc and
        # content_sha256 and left text_original holding the contaminated reading on the four
        # SEARCH_DERIVATIVE rows. The test whose docstring promised "both text roles" read
        # one field. 1,840 of 1,844 Samavedic derivative rows mirror text_nfc; these 4 were
        # the exception the correction itself created.
        if row["original"] is not None:
            head = row["original"].split()[:1]
            assert head and head[0] not in _APPARATUS_TOKENS, (
                f"{row['key']} {row['role']} text_original still opens on an apparatus token"
            )
            assert row["original"] == row["text"], (
                f"{row['key']} {row['role']}: text_original and text_nfc disagree"
            )


def test_the_apparatus_token_scan_is_whole_token_not_substring():
    """The control for the scan that proved the formula layer untouched.

    ``dra`` is a substring of ``indra``. A substring test reports 30+ contaminated
    formulas where a whole-token test reports 0, and the 0 is the true figure.
    """
    formula = "ayaṃ sa soma indra te sutaḥ piba"
    assert "dra" in formula, "the substring is present"
    assert "dra" not in formula.split(), "the whole token is not"


@_LIVE
def test_live_no_cross_veda_edge_publishes_a_variant_claim_from_the_apparatus():
    """One of only two HEAD_TRUNCATION rows corpus-wide was our own parser's apparatus.

    The class cannot be re-derived here -- its 16-value vocabulary lives in the cross-Veda
    staging build, not in ``src`` -- so the affected edges carry an explicit stale marker
    with the old value preserved beside it, rather than publishing it as current.
    """
    stale = _scalar(
        "MATCH ()-[r]->() WHERE r.cross_veda_transformation_status = "
        "'STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED' RETURN count(r)"
    )
    # 14, not 13. The fourteenth is the edge that mattered most and that R5's first pass
    # SKIPPED: VG:SV:KAU:CHANDA:P01:D08:V04 <-> VSM 12.51 was the one carrying
    # HEAD_TRUNCATION, and the staging join required a PRIMARY_TEXT TextVersion at both
    # ends -- a role the Yajurveda does not use, so the only edge whose class was known
    # false was the only one left publishing it. The skip was recorded loudly and then not
    # acted on, which is its own lesson.
    assert stale == 14

    # The assertions that actually matter, rather than a count of markers: no corrected
    # verse still carries the false class, and no edge anywhere still publishes a quote
    # taken from the apparatus.
    assert (
        _scalar(
            """
            MATCH (a:Passage)-[r]->(b:Passage)
            WHERE (a.canonical_key IN $keys OR b.canonical_key IN $keys)
              AND r.cross_veda_transformation = 'HEAD_TRUNCATION'
            RETURN count(r)
            """,
            keys=list(_CORRECTED),
        )
        == 0
    ), "a corrected verse still publishes HEAD_TRUNCATION as its live transformation"
    assert (
        _scalar(
            """
            MATCH ()-[r]->()
            WHERE coalesce(r.evidence,'') CONTAINS 'draiḍāmagne'
               OR coalesce(r.formula_evidence,'') CONTAINS 'draiḍāmagne'
               OR coalesce(r.formula_difference_spans,'') CONTAINS 'draiḍāmagne'
            RETURN count(r)
            """
        )
        == 0
    ), "an edge still publishes an evidence quote containing the apparatus"
    # One HEAD_TRUNCATION row survives corpus-wide and SHOULD: RV 4.10.1 <-> VSM 17.77 has
    # nothing to do with the apparatus. The published table's "2" becomes "1", which is
    # exactly what the cross-veda report's R5 note says it will read.
    assert (
        _scalar(
            "MATCH ()-[r]->() WHERE r.cross_veda_transformation = 'HEAD_TRUNCATION' "
            "RETURN count(r)"
        )
        == 1
    )
    assert (
        _scalar(
            """
            MATCH ()-[r]->()
            WHERE r.cross_veda_transformation_status =
                  'STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED'
              AND (r.cross_veda_transformation_superseded IS NULL
                   OR r.cross_veda_transformation_stale_reason IS NULL)
            RETURN count(r)
            """
        )
        == 0
    ), "a stale marker with no preserved value and no reason discloses nothing"


@_LIVE
def test_live_the_recomputed_similarity_metrics_landed():
    assert (
        _scalar(
            "MATCH ()-[r]->() WHERE r.cross_veda_metrics_recomputed_by IS NOT NULL "
            "RETURN count(r)"
        )
        == 13
    )


def test_text_version_id_is_an_artifact_id_and_must_not_be_used_as_a_node_key():
    """Pinned because it is a migration landmine, not a curiosity.

    58,786 TextVersion nodes share 12 ``text_version_id`` values and the biggest group is
    10,552, so a ``SET`` keyed on it writes 10,552 nodes where one was meant. ``text_id``
    is the unique key. This repository has already recorded an unlabelled MATCH creating
    39,461 bogus edges.
    """
    receipt = (
        PROJECT_ROOT
        / "data"
        / "staging"
        / "release_blocker_r5"
        / "migration_plan.json"
    )
    if not receipt.exists():
        pytest.skip("R5 migration plan not present in this checkout")
    import json

    plan = json.loads(receipt.read_text(encoding="utf-8"))
    assert plan["match_keys"]["TextVersion"] == "text_id"
    assert "text_version_id" not in json.dumps(plan["match_keys"])


# ---------------------------------------------------------------------------
# Agent B's C05 -- a closure that only holds until the next build is not a closure
# ---------------------------------------------------------------------------


def test_no_builder_stamps_confidence_on_a_source_explicit_predicate():
    """The generator fix, pinned. This is the finding Agent B's C05 named.

    R5 first landed GAP-QUALITY-003's rename as a migration and left SEVEN writers still
    stamping ``confidence`` on the seven source-explicit predicates, with no builder writing
    the replacement property at all. A rebuild would have taken the published closure
    measure from 0 straight back to 51,364 and produced 0 tier markers -- the exact "fix
    that never reaches the shipped artifact" defect this repository has recorded, and the
    same objection GAP-RITUAL-003 was held open on in this very round.

    So the test reads the BUILD CODE, not the graph. A graph assertion cannot catch this:
    the graph is correct right now and would stop being correct the next time anything ran.
    """
    writers = [
        PROJECT_ROOT / "src" / "vedagraph" / "graph" / "loader.py",
        PROJECT_ROOT / "src" / "vedagraph" / "domain" / "v3_loader.py",
        PROJECT_ROOT / "src" / "vedagraph" / "domain" / "ascription_bridge.py",
    ]
    offenders: list[str] = []
    for path in writers:
        text = path.read_text(encoding="utf-8")
        for needle in (
            "rel.confidence = row.confidence",
            "r.confidence = row.confidence",
            "m.confidence = 1.0",
            '"confidence": 1.0,',
        ):
            if needle in text:
                offenders.append(f"{path.name}: {needle}")
    assert offenders == [], (
        "a builder stamps `confidence` on a source-explicit predicate again, so the next "
        f"rebuild reverses GAP-QUALITY-003: {offenders}"
    )

    # And the replacement is actually written by the build code, not only by a migration.
    stamped = [
        path.name
        for path in writers
        if "source_explicit_tier_marker" in path.read_text(encoding="utf-8")
    ]
    assert sorted(stamped) == ["ascription_bridge.py", "loader.py", "v3_loader.py"], (
        f"a writer no longer stamps the tier marker: {stamped}"
    )


def test_the_tier_predicate_map_and_the_serving_map_cannot_drift():
    """Two maps, one population. They were written in two files and must agree.

    ``PIPELINE_CONSTANT_PREDICATES`` in the serving layer decides what the API reports as a
    pipeline prior; ``SOURCE_EXPLICIT_TIER_PREDICATES`` in the domain layer decides what the
    builders stamp. A predicate in one and not the other is an edge whose value the product
    describes one way and the builder writes another.
    """
    from vedagraph.api.services.graph_service import PIPELINE_CONSTANT_PREDICATES
    from vedagraph.domain.tiers import SOURCE_EXPLICIT_TIER_PREDICATES

    assert set(PIPELINE_CONSTANT_PREDICATES) == set(SOURCE_EXPLICIT_TIER_PREDICATES)
    assert set(PIPELINE_CONSTANT_PREDICATES.values()) == {1.0}


@_LIVE
def test_live_the_withdrawn_figures_are_still_reachable_through_the_api_shape():
    """Agent B's M19: a rename must not make a published number unreachable.

    The 0.85 on INVOLVES_SUBSTANCE and the 0.75 on REFERS_TO_PLACE were reported to clients
    as a varying confidence. After the withdrawal they live in
    ``uncalibrated_pipeline_score``, and a serving layer reading only ``confidence`` would
    return nothing at all for them -- information the product used to publish disappearing
    rather than being relabelled.
    """
    from vedagraph.api.services.graph_service import _confidence

    rows = _rows(
        """
        MATCH ()-[r:INVOLVES_SUBSTANCE|REFERS_TO_PLACE]->()
        RETURN type(r) AS predicate, properties(r) AS props
        """
    )
    assert rows, "the two tiny-population predicates are gone"
    for row in rows:
        basis, confidence, prior = _confidence(row["predicate"], row["props"])
        assert confidence is None, "a constant must never be served as a confidence"
        assert prior in (0.85, 0.75), (
            f"{row['predicate']}: the withdrawn figure is unreachable, prior={prior}"
        )


@_LIVE
def test_live_the_disclosure_query_can_still_see_the_constants():
    """Agent B's C01. The one query whose job is to disclose the constants had gone blind.

    ``confidence_is_a_pipeline_constant`` opened ``WHERE r.confidence IS NOT NULL``, which
    after the withdrawal excluded all 51,364 edges that still carry exactly 1.0 under
    another name. A researcher running the shipped query would have concluded that no
    predicate stamps a constant.
    """
    from neo4j import Query

    from vedagraph.domain.queries import QUERIES_BY_NAME

    query = QUERIES_BY_NAME["confidence_is_a_pipeline_constant"]
    driver = _driver()
    try:
        with driver.session() as session:
            rows = [r.data() for r in session.run(Query(query.cypher, timeout=300.0))]
    finally:
        driver.close()

    constants = [r for r in rows if r["guard_verdict"] == "SINGLE_CONSTANT"]
    assert len(constants) == 9, (
        f"the disclosure query sees {len(constants)} single-constant predicates; 7 carry a "
        "tier marker and 2 an uncalibrated score, so it must see 9"
    )
    fields = {r["field"] for r in rows}
    assert fields == {
        "confidence",
        "source_explicit_tier_marker",
        "uncalibrated_pipeline_score",
    }, f"the query does not read all three strength fields: {fields}"
    # And it must say which field each row came from, or the three are indistinguishable.
    assert all(r["field"] for r in rows)
