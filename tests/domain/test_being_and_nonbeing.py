"""Contract tests for VG:CONCEPT:SAT-EXISTENCE and VG:CONCEPT:ASAT-NONEXISTENCE.

Entirely offline, like the rest of the domain suite: everything worth pinning here is
decidable from the registry, the corpus and the two matching functions, and a test that
needed Neo4j running would be skipped exactly when it was most needed.

These two entities were added because RV 10.129.1 -- the Nāsadīya, whose first line is
``nā́sad āsīn nó sád āsīt`` -- had no Sanskrit-grounded conceptual edge of any kind, and
the reason was that the registry had no entity for either word the verse turns on. So the
test that matters most in this file is
:func:`test_the_nasadiya_acquires_a_sanskrit_grounded_mention`.

The rest of the file exists because ``sat`` is a trap and the trap is easy to walk back
into. ``sat-`` is the present participle of ``√as-`` "to be", so most of its inflections
mean "being, existing, good, real, faithful" rather than "the Existent"; ``satya-`` is a
different stem with its own entity; and ``ásat`` is homographic with the third-person
singular present subjunctive of the same root, which is 24 of that surface's 25 corpus
hits. Every rejection was measured against the University of Zurich morphological
annotation of the Rigveda and then read in all four Vedas, and
:func:`test_the_measured_rejections_stay_rejected` pins each one by name so that
re-adding it is a test failure rather than a quiet loss of precision.
"""

from __future__ import annotations

import functools
import pathlib

import pytest

from vedagraph.domain.mentions import MentionRow, extract_mentions
from vedagraph.domain.ontology import (
    LABEL_CONCEPT,
    LABEL_DOMAIN_ENTITY,
    REL_MENTIONS_ENTITY,
    RELATIONSHIP_SIGNATURES,
    labels_for_node_type,
)
from vedagraph.domain.registry import load_domain_entities, merge_registry
from vedagraph.enrich.concepts import (
    MIN_SANDHI_ALIAS_CHARS,
    SANDHI_SUPPRESSED_ALIASES,
    assign_concepts,
    fold_alias,
    load_concepts,
)
from vedagraph.enrich.corpus import Corpus, load_corpus
from vedagraph.enrich.guards import MAX_CONCEPT_NODES
from vedagraph.enrich.predicates import SIGNATURES, NodeKind, StructuralPredicate
from vedagraph.enrich.records import ConceptAssertionRow, ConceptRow

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

SAT = "VG:CONCEPT:SAT-EXISTENCE"
ASAT = "VG:CONCEPT:ASAT-NONEXISTENCE"
SATYA = "VG:CONCEPT:SATYA-TRUTH"

#: RV 10.129.1, the verse this pair was authored for.
NASADIYA = "VG:RV:SAK:M10:S129:V001"

#: Surfaces probed against the corpus and REFUSED, with the measurement that refused
#: them. Kept as a test rather than only as a comment in the registry: an alias whose
#: rejection is recorded in prose gets re-added, and an alias whose rejection is asserted
#: does not. Counts are hits over all 20,210 mantras, every one of which was read.
REJECTED_SURFACES: dict[str, str] = {
    "sat": "7 hits, 1 philosophical; VSM 2.33 and 17.24 are the subjunctive and VSM 32.9 "
    "is `guhā sat` 'hidden'",
    "sataḥ": "9 hits, 0 philosophical, and wrong in the worst direction: 5 are the "
    "masculine participle and the other 3 (RV 10.72.2, RV 10.72.3, AVS 10.7.25) are "
    "`ásataḥ` with its initial a- elided, so the surface means NON-existence",
    "sato": "15 hits, 2 philosophical; 13 are the masculine genitive participle "
    "`mahás te sató` 'thee who art great'",
    "satām": "masculine/neuter genitive plural participle; RV 2.1.3 is Griffith's 'Hero of Heroes'",
    "sate": "5 hits, dative singular masculine participle, 'to him who is'",
    "satā": "1 hit, instrumental singular masculine participle (RV 8.43.14)",
    "asat": "25 hits, 1 philosophical. All 13 Rigvedic hits are the 3sg present "
    "subjunctive of √as- by annotation, and the AV and YV hits read the same way",
    "asan": "12 hits, 0 philosophical; subjunctive, or the aorist injunctive of √as- 2",
    "asann": "7 hits, 2 philosophical; the other 5 are the subjunctive",
    "asataḥ": "1 hit, 1 philosophical, but the only candidate that clears "
    "MIN_SANDHI_ALIAS_CHARS: on the Samavedic substring path it matches inside "
    "`dhruvasya satah` at SV UTTARA 3.1.1.2. Refused rather than made to depend on a new "
    "SANDHI_SUPPRESSED_ALIASES entry",
}

#: English tokens probed and refused.
REJECTED_ENGLISH: dict[str, str] = {
    "existence": "68 hits, 2 philosophical. Whitney's word for bhūta-/bhuvana- and "
    "Griffith's for āyus- ('prolong our existence'), so it would take passages from "
    "AYUS-LIFE",
    "being": "281 hits, overwhelmingly the English participle ('being hard', 'being "
    "revered') and Whitney's bhūta-",
    "real": "16 hits, spread across satya-, ṛta- and divine epithets",
}

#: The exact Sanskrit-grounded witness set, measured. A regression pin: if an alias is
#: widened or a corpus surface changes, this is the assertion that says so.
EXPECTED_MENTIONS: dict[str, set[str]] = {
    ASAT: {
        "AVS 3.23.5",
        "AVS 10.7.10",
        "AVS 17.1.19",
        "RV 1.124.11",
        "RV 6.23.9",
        "RV 10.5.7",
        "RV 10.129.1",
        "RV 10.129.4",
    },
    SAT: {
        "AVS 5.19.9",
        "AVS 8.4.12",
        "AVS 9.10.28",
        "AVS 10.7.10",
        "RV 1.164.46",
        "RV 5.44.3",
        "RV 6.18.4",
        "RV 6.24.5",
        "RV 6.27.2",
        "RV 7.104.12",
        "RV 10.5.7",
        "RV 10.72.2",
        "RV 10.72.3",
        "RV 10.129.1",
    },
}

#: Of the witnesses above, the ones READ and judged NOT to be the philosophical word.
#: Named, not hidden: three are the predicative participle "real, faithful" and three are
#: the subjunctive. Asserting them keeps the recorded precision honest -- if this set
#: shrinks, someone improved the aliases and should say so.
KNOWN_FALSE_POSITIVES: dict[str, set[str]] = {
    ASAT: {"AVS 3.23.5", "RV 1.124.11", "RV 6.23.9"},
    SAT: {"AVS 5.19.9", "RV 5.44.3", "RV 6.18.4", "RV 6.24.5", "RV 6.27.2"},
}


@functools.cache
def _corpus() -> Corpus:
    return load_corpus(PROJECT_ROOT)


@functools.cache
def _base_registry() -> tuple[ConceptRow, ...]:
    """The V1 registry, loaded exactly as ``build_enrichment`` loads it.

    Loaded with the defaults on purpose. ``data/registry/concepts.yaml`` under the frozen
    ``SemanticNodeType`` whitelist is the only registry the ABOUT_CONCEPT builder reads,
    so an entity that loads only under ``ALL_NODE_TYPE_NAMES`` would close the mention gap
    and leave the aboutness gap open.
    """
    return load_concepts(PROJECT_ROOT)


@functools.cache
def _merged_registry() -> tuple[ConceptRow, ...]:
    return load_domain_entities(PROJECT_ROOT)


@functools.cache
def _mentions() -> tuple[MentionRow, ...]:
    rows, _ = extract_mentions(_corpus(), _merged_registry())
    return tuple(rows)


@functools.cache
def _assertions() -> tuple[ConceptAssertionRow, ...]:
    rows, _ = assign_concepts(_corpus(), list(_base_registry()))
    return tuple(rows)


def _by_id(concepts: tuple[ConceptRow, ...], concept_id: str) -> ConceptRow:
    for concept in concepts:
        if concept.concept_id == concept_id:
            return concept
    raise AssertionError(f"{concept_id} is not in the registry")


# ---------------------------------------------------------------------------
# The gap this pair was authored to close
# ---------------------------------------------------------------------------


def test_the_nasadiya_acquires_a_sanskrit_grounded_mention() -> None:
    """The measured gap, closed. This is the test that matters.

    RV 10.129.1 carried no Sanskrit-grounded conceptual edge at all. It must now name
    both words its first line turns on, and it must do so on the token path -- an English
    match would be a claim about Griffith rather than about the verse.
    """
    reached = {row.entity_key: row for row in _mentions() if row.passage_key == NASADIYA}
    assert SAT in reached, "the Nāsadīya still does not mention existence"
    assert ASAT in reached, "the Nāsadīya still does not mention non-existence"

    # The aliases are named, not merely counted: `nāsad` is the glue of ná + ásat and
    # occurs in this verse and nowhere else in 20,210 mantras, and `sad` is sát before a
    # vowel. Neither is `sat` or `asat`, which were both refused.
    assert reached[ASAT].matched_aliases == ("nāsad",)
    assert reached[SAT].matched_aliases == ("sad",)
    for row in (reached[SAT], reached[ASAT]):
        assert row.paths == ("sanskrit-token",)
        assert not row.theonym_ambiguous


def test_the_nasadiya_acquires_an_aboutness_assertion_above_the_translation_band() -> None:
    """The other half of the gap, on the V1 concept path.

    Before this pair the verse had two assertions, both at 0.42 and both resting on an
    English word alone -- exactly the translation-only class V3 retires. Both new
    assertions must sit in the Sanskrit band.
    """
    reached = {row.concept_id: row for row in _assertions() if row.passage_key == NASADIYA}
    assert {SAT, ASAT} <= set(reached)
    for concept_id in (SAT, ASAT):
        row = reached[concept_id].as_row()
        assert "sanskrit-token" in str(row["method"])
        assert float(row["confidence"]) >= 0.80


def test_both_entities_reach_a_veda_other_than_the_rigveda() -> None:
    """Without this the pair could not answer a cross-Veda question.

    ``similar_in_sense_but_not_in_words`` is anchored on RV 10.129.1 and matches other
    Vedas' mantras through the concepts it shares, so a Rigveda-only entity leaves that
    query returning nothing even once the anchor has edges.
    """
    corpus = _corpus()
    for concept_id in (SAT, ASAT):
        vedas = {
            corpus.by_key[row.passage_key].veda
            for row in _mentions()
            if row.entity_key == concept_id
        }
        assert vedas - {"RV"}, f"{concept_id} is Rigveda-only"


# ---------------------------------------------------------------------------
# Loading, and the ceiling
# ---------------------------------------------------------------------------


def test_both_entities_load_from_the_registry_the_aboutness_builder_reads() -> None:
    for concept_id in (SAT, ASAT):
        concept = _by_id(_base_registry(), concept_id)
        assert concept.node_type == "PHILOSOPHICAL_CONCEPT"
        assert concept.definition.strip()
        assert concept.aliases_sa


def test_the_merged_registry_stays_clean_and_under_the_ceiling() -> None:
    report = merge_registry(PROJECT_ROOT)
    assert report.clean
    assert not report.duplicate_ids
    assert not report.alias_collisions
    merged = _merged_registry()
    assert len(merged) == report.merged_entities
    assert len(merged) <= MAX_CONCEPT_NODES
    assert {SAT, ASAT} <= {concept.concept_id for concept in merged}


def test_neither_entity_declares_a_dangling_or_self_serving_parent() -> None:
    """``broader`` is deliberately empty on both, and non-existence is not a kind of
    existence -- filing one under the other would make every ancestor query over the pair
    return the wrong answer for the Nāsadīya's own contrast."""
    known = {concept.concept_id for concept in _merged_registry()}
    for concept_id in (SAT, ASAT):
        concept = _by_id(_merged_registry(), concept_id)
        assert concept.broader == ()
        assert set(concept.broader) <= known
    assert SAT not in _by_id(_merged_registry(), ASAT).broader
    assert ASAT not in _by_id(_merged_registry(), SAT).broader


# ---------------------------------------------------------------------------
# The alias discipline
# ---------------------------------------------------------------------------


def test_no_being_alias_collides_with_satya_truth() -> None:
    """``satya-`` is a different stem, and the two must not leak in either direction.

    Checked on the folded surface, which is what matching compares -- ``satyaṃ`` and
    ``satyam`` fold to the same string, so an equality test on the written IAST would pass
    while the matcher collided.
    """
    satya_sa = {fold_alias(alias) for alias in _by_id(_merged_registry(), SATYA).aliases_sa}
    satya_en = set(_by_id(_merged_registry(), SATYA).aliases_en)
    for concept_id in (SAT, ASAT):
        concept = _by_id(_merged_registry(), concept_id)
        mine = {fold_alias(alias) for alias in concept.aliases_sa}
        assert not (mine & satya_sa)
        assert not (set(concept.aliases_en) & satya_en)
        # Nor may one be a substring of the other, which is how a leak would arrive if
        # the sandhi floor were ever lowered.
        for alias in mine:
            assert not any(alias in host for host in satya_sa), alias
            assert not any(host in alias for host in satya_sa), alias


def test_no_being_alias_is_claimed_by_any_other_entity() -> None:
    """``load_concepts`` already refuses this, per file. Asserted here as well because
    the refusal is per-file and this pair lives in the base registry while 136 other
    entities live in fragments."""
    mine = {SAT, ASAT}
    claimed_sa: dict[str, str] = {}
    claimed_en: dict[str, str] = {}
    for concept in _merged_registry():
        if concept.concept_id in mine:
            continue
        for alias in concept.aliases_sa:
            claimed_sa[fold_alias(alias)] = concept.concept_id
        for alias in concept.aliases_en:
            claimed_en[alias] = concept.concept_id
    for concept_id in sorted(mine):
        concept = _by_id(_merged_registry(), concept_id)
        for alias in concept.aliases_sa:
            owner = claimed_sa.get(fold_alias(alias))
            assert owner is None, f"{alias!r} is also claimed by {owner}"
        for alias in concept.aliases_en:
            owner = claimed_en.get(alias)
            assert owner is None, f"{alias!r} is also claimed by {owner}"


def test_no_being_alias_reaches_the_samavedic_substring_path() -> None:
    """Every alias here is short enough that it can only ever match a whole token.

    This is the property that makes the pair safe rather than merely measured: the
    substring pass is where a three-character participle would do real damage, and no
    alias below the floor can enter it. It is also why no entry in
    ``SANDHI_SUPPRESSED_ALIASES`` is needed -- and this asserts that none is, so the pair
    cannot silently start depending on a code change it does not own.
    """
    for concept_id in (SAT, ASAT):
        for alias in _by_id(_merged_registry(), concept_id).aliases_sa:
            folded = fold_alias(alias)
            assert len(folded) < MIN_SANDHI_ALIAS_CHARS, (
                f"{alias!r} folds to {len(folded)} characters and would enter the "
                "Samavedic substring pass"
            )
            assert alias not in SANDHI_SUPPRESSED_ALIASES


@pytest.mark.parametrize("surface", sorted(REJECTED_SURFACES))
def test_the_measured_rejections_stay_rejected(surface: str) -> None:
    """A refused participle surface must not be an alias of anything.

    The reason is in ``REJECTED_SURFACES``. The two worth restating: ``asat`` is 24/25 the
    third-person singular subjunctive of ``√as-``, and ``sataḥ`` is 0/9 the philosophical
    word and is *elided ásataḥ* in three of its hits, so a surface probe would file
    "existence sprang from non-existence" under existence on the evidence of the word for
    non-existence.
    """
    folded = fold_alias(surface)
    for concept in _merged_registry():
        aliases = {fold_alias(alias) for alias in concept.aliases_sa}
        assert folded not in aliases, (
            f"{surface!r} was measured and refused ({REJECTED_SURFACES[surface]}) but is "
            f"an alias of {concept.concept_id}"
        )


@pytest.mark.parametrize("token", sorted(REJECTED_ENGLISH))
def test_the_measured_english_rejections_stay_rejected(token: str) -> None:
    for concept in _merged_registry():
        assert token not in concept.aliases_en, (
            f"{token!r} was measured and refused ({REJECTED_ENGLISH[token]}) but is an "
            f"English alias of {concept.concept_id}"
        )


def test_every_alias_actually_occurs_in_the_corpus() -> None:
    """The registry's own rule: an alias that matches nothing is a claim nobody checked."""
    tokens: set[str] = set()
    for mantra in _corpus().mantras:
        tokens.update(mantra.surfaces.tokens)
    for concept_id in (SAT, ASAT):
        for alias in _by_id(_merged_registry(), concept_id).aliases_sa:
            assert fold_alias(alias) in tokens, f"{alias!r} matches no corpus token"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def test_the_node_type_satisfies_both_predicate_signatures() -> None:
    """``PHILOSOPHICAL_CONCEPT`` has to be a legal object of two different predicates.

    ``ABOUT_CONCEPT`` requires ``Concept`` and ``MENTIONS_ENTITY`` requires
    ``DomainEntity``, and the pair is produced by both layers. A type that carried only
    one of the two labels would make one of the two builds emit contract violations
    instead of edges -- silently, because the rows simply would not match.
    """
    labels = set(labels_for_node_type("PHILOSOPHICAL_CONCEPT"))
    assert LABEL_CONCEPT in labels
    assert LABEL_DOMAIN_ENTITY in labels

    aboutness = SIGNATURES[str(StructuralPredicate.ABOUT_CONCEPT)]
    assert aboutness.subject == frozenset({NodeKind.PASSAGE})
    assert str(NodeKind.CONCEPT) in labels

    _, mention_range = RELATIONSHIP_SIGNATURES[REL_MENTIONS_ENTITY]
    assert mention_range & labels


# ---------------------------------------------------------------------------
# The measured witness sets, pinned
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("concept_id", [SAT, ASAT])
def test_the_witness_set_is_exactly_what_was_read(concept_id: str) -> None:
    """Every passage either entity reaches on the Sanskrit path was read and judged.

    Pinned as an equality rather than a floor. The point of the whole probe was that this
    set is small enough to enumerate; a change to it is a change somebody has to defend,
    not a coverage improvement to be noticed later.
    """
    corpus = _corpus()
    reached = {
        corpus.by_key[row.passage_key].citation
        for row in _mentions()
        if row.entity_key == concept_id
    }
    assert reached == EXPECTED_MENTIONS[concept_id]


@pytest.mark.parametrize("concept_id", [SAT, ASAT])
def test_the_recorded_precision_is_still_what_was_recorded(concept_id: str) -> None:
    """The known-wrong witnesses are named, and the resulting precision is asserted.

    ``KNOWN_FALSE_POSITIVES`` is a deliberate part of the deliverable: 9 of 14 for
    existence and 5 of 8 for non-existence, with every wrong verse named. A recorded
    residual that drifts without anyone noticing is the failure this pins.
    """
    expected = EXPECTED_MENTIONS[concept_id]
    wrong = KNOWN_FALSE_POSITIVES[concept_id]
    assert wrong <= expected, "a named false positive is no longer reached at all"
    precision = (len(expected) - len(wrong)) / len(expected)
    assert precision >= 0.60, f"{concept_id} precision fell to {precision:.2f}"


def test_the_nasadiya_is_not_among_the_known_false_positives() -> None:
    corpus = _corpus()
    citation = corpus.by_key[NASADIYA].citation
    for concept_id in (SAT, ASAT):
        assert citation in EXPECTED_MENTIONS[concept_id]
        assert citation not in KNOWN_FALSE_POSITIVES[concept_id]
