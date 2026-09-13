"""Tests for the concept lexicon and the deterministic passage-to-concept matcher.

Two kinds of test, and they are not interchangeable.

The **synthetic** tests build a two-file registry in ``tmp_path`` and assert that each
validation rule fires. They exist because every one of those failures is silent in
production: a cycle in ``broader`` does not raise, it makes ancestor queries loop; an
unresolvable devata key does not raise, it makes an edge to a node that is not there. A
rule with no test for its failure case is a rule that has never been observed to work.

The **real-corpus** tests run the matcher over all 20,210 mantras. They are the only place
the caps, the per-Veda coverage and the byte-determinism of the output can actually be
checked, and they are slow on purpose: a fixture that stands in for the corpus would also
stand in for every property worth asserting about it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from vedagraph.enrich.concepts import (
    CONCEPT_ID_PATTERN,
    MAX_CONCEPT_NODES,
    SANDHI_SUPPRESSED_ALIASES,
    ConceptRegistryError,
    assign_concepts,
    build_index,
    concept_hierarchy_rows,
    devata_association_rows,
    fold_alias,
    load_ambiguous_aliases,
    load_concepts,
)
from vedagraph.enrich.corpus import Corpus, load_corpus
from vedagraph.enrich.guards import MAX_CONCEPT_ASSERTIONS, MAX_CONCEPTS_PER_PASSAGE
from vedagraph.enrich.predicates import StructuralPredicate
from vedagraph.enrich.provenance import AssertionState, TrustClass
from vedagraph.enrich.records import ConceptRow
from vedagraph.normalize import ComparisonForm, comparison_form
from vedagraph.semantic.ontology import SemanticNodeType

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Synthetic registries
# ---------------------------------------------------------------------------


def _concept(concept_id: str, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "concept_id": concept_id,
        "preferred_label_sa": "agni",
        "preferred_label_en": "fire",
        "node_type": "NATURAL_PHENOMENON",
        "definition": "A test concept.",
        "aliases_sa": ["agnim"],
        "aliases_en": ["fire"],
        "broader": [],
        "related_devatas": [],
    }
    base.update(overrides)
    return base


def _write_registry(root: Path, concepts: list[dict[str, Any]], **top: Any) -> Path:
    registry = root / "data" / "registry"
    registry.mkdir(parents=True, exist_ok=True)
    (registry / "devatas.yaml").write_text(
        yaml.safe_dump(
            {
                "entities": [
                    {"entity_key": "VG:DEVATA:AGNIH", "entity_type": "DEVATA"},
                    {"entity_key": "VG:DEVATA:SOMAH", "entity_type": "DEVATA"},
                ]
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    document: dict[str, Any] = {"policy_version": "test", "concepts": concepts}
    document.update(top)
    (registry / "concepts.yaml").write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return root


def _expect(root: Path, fragment: str) -> None:
    with pytest.raises(ConceptRegistryError) as excinfo:
        load_concepts(root)
    assert fragment in str(excinfo.value)


def test_minimal_registry_loads(tmp_path: Path) -> None:
    root = _write_registry(tmp_path, [_concept("VG:CONCEPT:AGNI-FIRE")])
    (concept,) = load_concepts(root)
    assert concept.concept_id == "VG:CONCEPT:AGNI-FIRE"
    assert concept.aliases_sa == ("agnim",)


def test_malformed_concept_id_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(tmp_path, [_concept("VG:Concept:agni_fire")])
    _expect(root, "is not a valid concept id")


def test_duplicate_concept_id_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path,
        [
            _concept("VG:CONCEPT:AGNI-FIRE"),
            _concept("VG:CONCEPT:AGNI-FIRE", aliases_sa=["agne"], aliases_en=["flame"]),
        ],
    )
    _expect(root, "duplicate concept_id")


def test_node_type_must_be_a_semantic_node_type(tmp_path: Path) -> None:
    root = _write_registry(tmp_path, [_concept("VG:CONCEPT:AGNI-FIRE", node_type="ELEMENT")])
    _expect(root, "is not an allowed entity type")


def test_every_node_type_in_the_real_registry_is_a_member() -> None:
    allowed = {str(member) for member in SemanticNodeType}
    for concept in load_concepts(PROJECT_ROOT):
        assert concept.node_type in allowed


def test_broader_must_resolve(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path, [_concept("VG:CONCEPT:AGNI-FIRE", broader=["VG:CONCEPT:HEAT"])]
    )
    _expect(root, "does not exist")


def test_broader_may_not_be_self(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path, [_concept("VG:CONCEPT:AGNI-FIRE", broader=["VG:CONCEPT:AGNI-FIRE"])]
    )
    _expect(root, "its own broader concept")


def test_broader_two_cycle_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path,
        [
            _concept("VG:CONCEPT:A", broader=["VG:CONCEPT:B"]),
            _concept(
                "VG:CONCEPT:B",
                broader=["VG:CONCEPT:A"],
                aliases_sa=["agne"],
                aliases_en=["flame"],
            ),
        ],
    )
    _expect(root, "forms a cycle")


def test_broader_three_cycle_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path,
        [
            _concept("VG:CONCEPT:A", broader=["VG:CONCEPT:B"]),
            _concept(
                "VG:CONCEPT:B",
                broader=["VG:CONCEPT:C"],
                aliases_sa=["agne"],
                aliases_en=["flame"],
            ),
            _concept(
                "VG:CONCEPT:C",
                broader=["VG:CONCEPT:A"],
                aliases_sa=["agnau"],
                aliases_en=["blaze"],
            ),
        ],
    )
    _expect(root, "forms a cycle")


def test_a_deep_acyclic_chain_is_accepted(tmp_path: Path) -> None:
    """A diamond is not a cycle, and the checker must not confuse the two."""
    root = _write_registry(
        tmp_path,
        [
            _concept("VG:CONCEPT:TOP"),
            _concept(
                "VG:CONCEPT:LEFT",
                broader=["VG:CONCEPT:TOP"],
                aliases_sa=["agne"],
                aliases_en=["flame"],
            ),
            _concept(
                "VG:CONCEPT:RIGHT",
                broader=["VG:CONCEPT:TOP"],
                aliases_sa=["agnau"],
                aliases_en=["blaze"],
            ),
            _concept(
                "VG:CONCEPT:BOTTOM",
                broader=["VG:CONCEPT:LEFT", "VG:CONCEPT:RIGHT"],
                aliases_sa=["agnir"],
                aliases_en=["fires"],
            ),
        ],
    )
    assert len(load_concepts(root)) == 4


def test_unknown_devata_key_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path, [_concept("VG:CONCEPT:AGNI-FIRE", related_devatas=["VG:DEVATA:AGNIS"])]
    )
    _expect(root, "is not in")


def test_known_devata_key_is_accepted(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path, [_concept("VG:CONCEPT:AGNI-FIRE", related_devatas=["VG:DEVATA:AGNIH"])]
    )
    (concept,) = load_concepts(root)
    assert concept.related_devatas == ("VG:DEVATA:AGNIH",)


def test_sanskrit_alias_shared_by_two_concepts_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path,
        [
            _concept("VG:CONCEPT:A"),
            _concept("VG:CONCEPT:B", aliases_en=["flame"]),
        ],
    )
    _expect(root, "claimed by both")


def test_alias_collision_is_detected_after_folding(tmp_path: Path) -> None:
    """Two spellings that fold to one string are one alias, and must collide as one.

    ``ṛta`` and ``r̥ta`` are different code points and the same word. Checking uniqueness
    on the written form alone would let both into the lexicon under different concepts and
    then let matching pick whichever the dict happened to hold.
    """
    root = _write_registry(
        tmp_path,
        [
            _concept("VG:CONCEPT:A", aliases_sa=["ṛta"], aliases_en=["order"]),
            _concept("VG:CONCEPT:B", aliases_sa=["r̥ta"], aliases_en=["law"]),
        ],
    )
    _expect(root, "claimed by both")


def test_english_alias_shared_by_two_concepts_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path,
        [
            _concept("VG:CONCEPT:A"),
            _concept("VG:CONCEPT:B", aliases_sa=["agne"]),
        ],
    )
    _expect(root, "claimed by both")


def test_declared_ambiguous_alias_may_be_shared_and_never_matches(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path,
        [
            _concept("VG:CONCEPT:A", aliases_sa=["madhu"], aliases_en=["honey"]),
            _concept("VG:CONCEPT:B", aliases_sa=["madhu"], aliases_en=["juice"]),
        ],
        ambiguous_aliases=[{"alias": "madhu", "kind": "sa", "reason": "claimed by both"}],
    )
    concepts = load_concepts(root)
    assert [c.aliases_sa for c in concepts] == [(), ()]
    index = build_index(concepts)
    assert fold_alias("madhu") not in index.token
    assert ("sa", "madhu") in load_ambiguous_aliases(root)


def test_ambiguous_alias_without_a_reason_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(
        tmp_path,
        [_concept("VG:CONCEPT:A")],
        ambiguous_aliases=[{"alias": "madhu", "kind": "sa", "reason": "  "}],
    )
    _expect(root, "needs both an alias and a reason")


def test_concept_with_no_usable_alias_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(tmp_path, [_concept("VG:CONCEPT:A", aliases_sa=[], aliases_en=[])])
    _expect(root, "no usable alias")


def test_multi_word_english_alias_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(tmp_path, [_concept("VG:CONCEPT:A", aliases_en=["sacred grass"])])
    _expect(root, "must be one lower-case token")


def test_repeated_alias_within_one_concept_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(tmp_path, [_concept("VG:CONCEPT:A", aliases_en=["fire", "fire"])])
    _expect(root, "repeats")


def test_empty_definition_is_rejected(tmp_path: Path) -> None:
    root = _write_registry(tmp_path, [_concept("VG:CONCEPT:A", definition="   ")])
    _expect(root, "definition must be a non-empty string")


def test_too_many_concepts_is_rejected(tmp_path: Path) -> None:
    concepts = [
        _concept(f"VG:CONCEPT:C{n}", aliases_sa=[f"agni{n}"], aliases_en=[f"fire{n}"])
        for n in range(MAX_CONCEPT_NODES + 1)
    ]
    root = _write_registry(tmp_path, concepts)
    _expect(root, "exceeds MAX_CONCEPT_NODES")


def test_missing_registry_is_reported_as_such(tmp_path: Path) -> None:
    _expect(tmp_path, "registry not found")


# ---------------------------------------------------------------------------
# The shipped registry
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def concepts() -> tuple[ConceptRow, ...]:
    return load_concepts(PROJECT_ROOT)


def test_shipped_registry_is_within_the_brief(concepts: tuple[ConceptRow, ...]) -> None:
    assert 50 <= len(concepts) <= MAX_CONCEPT_NODES
    assert all(CONCEPT_ID_PATTERN.match(c.concept_id) for c in concepts)
    assert len({c.concept_id for c in concepts}) == len(concepts)


def test_shipped_registry_is_returned_sorted(concepts: tuple[ConceptRow, ...]) -> None:
    ids = [c.concept_id for c in concepts]
    assert ids == sorted(ids)
    for concept in concepts:
        assert list(concept.aliases_sa) == sorted(concept.aliases_sa)
        assert list(concept.aliases_en) == sorted(concept.aliases_en)


def test_every_concept_can_be_reached_by_something(concepts: tuple[ConceptRow, ...]) -> None:
    for concept in concepts:
        assert concept.aliases_sa or concept.aliases_en, concept.concept_id


def test_hierarchy_rows_run_from_broader_to_narrower(concepts: tuple[ConceptRow, ...]) -> None:
    rows = concept_hierarchy_rows(concepts)
    by_id = {c.concept_id: c for c in concepts}
    assert rows
    for row in rows:
        assert row.predicate == str(StructuralPredicate.BROADER_THAN)
        assert row.subject_key in by_id[row.object_key].broader
        assert row.provenance.trust is TrustClass.SOURCE_EXPLICIT
        assert row.provenance.evidence


def test_devata_rows_resolve_against_the_devata_registry(
    concepts: tuple[ConceptRow, ...],
) -> None:
    document = yaml.safe_load(
        (PROJECT_ROOT / "data" / "registry" / "devatas.yaml").read_text(encoding="utf-8")
    )
    keys = {entity["entity_key"] for entity in document["entities"]}
    rows = devata_association_rows(concepts)
    assert rows
    for row in rows:
        assert row.predicate == str(StructuralPredicate.DEVATA_ASSOCIATED_WITH)
        assert row.subject_key in keys
        assert row.object_key.startswith("VG:CONCEPT:")


def test_no_concept_id_collides_with_a_devata_key(concepts: tuple[ConceptRow, ...]) -> None:
    """The two ontologies must not be able to name the same node."""
    ids = {c.concept_id for c in concepts}
    assert not any(i.startswith("VG:DEVATA:") for i in ids)


def test_suppressed_sandhi_aliases_still_exist_in_the_registry(
    concepts: tuple[ConceptRow, ...],
) -> None:
    """A suppression that no longer names a real alias is a stale rule, not a safeguard."""
    declared = {alias for concept in concepts for alias in concept.aliases_sa}
    assert set(SANDHI_SUPPRESSED_ALIASES) <= declared


def test_folding_an_alias_matches_the_corpus_search_surface() -> None:
    """The registry is IAST, the corpus is folded, and the two must meet in one place."""
    assert fold_alias("ṛtasya") == comparison_form("ṛtasya", ComparisonForm.SEARCH_NORMALIZED)
    assert fold_alias("ṛtasya") != "ṛtasya"
    assert fold_alias("AGNIM") == "agnim"


# ---------------------------------------------------------------------------
# The real corpus
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    return load_corpus(PROJECT_ROOT)


@pytest.fixture(scope="module")
def assigned(corpus: Corpus, concepts: tuple[ConceptRow, ...]) -> tuple[list[Any], dict[str, Any]]:
    rows, report = assign_concepts(corpus, concepts)
    return rows, report.as_dict()


def test_assignment_respects_the_per_passage_cap(assigned: tuple[list[Any], Any]) -> None:
    rows, _ = assigned
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.passage_key] = counts.get(row.passage_key, 0) + 1
    assert max(counts.values()) <= MAX_CONCEPTS_PER_PASSAGE


def test_dropped_concepts_are_counted_not_silently_discarded(
    assigned: tuple[list[Any], Any],
) -> None:
    _, report = assigned
    assert report["capped"]["concepts_per_passage"] > 0


def test_assignment_stays_under_the_global_ceiling(assigned: tuple[list[Any], Any]) -> None:
    rows, _ = assigned
    assert len(rows) <= MAX_CONCEPT_ASSERTIONS


def test_coverage_is_reported_per_veda_and_is_real(assigned: tuple[list[Any], Any]) -> None:
    _, report = assigned
    coverage = report["notes"]["coverage_by_veda"]
    assert set(coverage) == {"AV", "RV", "SV", "YV"}
    assert coverage["RV"]["coverage"] > 0.90
    assert coverage["AV"]["coverage"] > 0.70
    assert coverage["YV"]["coverage"] > 0.80
    assert coverage["SV"]["coverage"] > 0.60


def test_samaveda_has_no_translations_and_no_english_evidence(
    corpus: Corpus, assigned: tuple[list[Any], Any]
) -> None:
    """The Samaveda's whole coverage rests on Sanskrit, and the rows must show it.

    This is the single easiest number in the layer to misreport: a corpus-wide coverage
    figure hides the fact that one Veda in four cannot use half the machinery.
    """
    assert all(not m.translations for m in corpus.of_veda("SV"))
    rows, _ = assigned
    for row in rows:
        if row.veda != "SV":
            continue
        assert "english" not in row.provenance.method
        for span in row.provenance.evidence:
            assert span.surface in {"script_folded", "sandhi_insensitive"}


def test_sanskrit_evidence_always_outranks_english_evidence(
    assigned: tuple[list[Any], Any],
) -> None:
    rows, _ = assigned
    english_only = [r.confidence for r in rows if r.provenance.method.endswith(":english")]
    token_only = [r.confidence for r in rows if r.provenance.method.endswith(":sanskrit-token")]
    sandhi_only = [r.confidence for r in rows if r.provenance.method.endswith(":sanskrit-sandhi")]
    assert max(english_only) < min(sandhi_only)
    assert max(sandhi_only) < min(token_only)


def test_every_assertion_carries_a_usable_provenance_envelope(
    assigned: tuple[list[Any], Any],
) -> None:
    rows, _ = assigned
    for row in rows:
        provenance = row.provenance
        assert provenance.trust is TrustClass.DETERMINISTIC_DERIVED
        assert provenance.state is AssertionState.ACCEPTED
        assert provenance.model == ""
        assert provenance.run_id
        assert provenance.evidence
        assert 0.0 < provenance.score <= 1.0
        for span in provenance.evidence:
            assert span.locator == row.passage_key
            assert span.quote.strip()


def test_evidence_quotes_are_windows_of_the_surface_they_name(
    corpus: Corpus, assigned: tuple[list[Any], Any]
) -> None:
    """Evidence must be findable in the text it claims to come from.

    A quote that cannot be located on its own surface is not evidence, it is a label. The
    English window is normalised for whitespace, so it is checked against a whitespace
    normalised translation rather than the raw one.

    The Sanskrit surfaces are compared *rendered*, because a published quote is rendered:
    the comparison fold maps four sounds onto private-use code points and those must never
    reach a reader, so the quote holds ``teṣāṃ`` where the raw surface holds ``teṣā``.
    Rendering both sides keeps the check on the substantive question -- is this quote really
    a window of that surface -- rather than on which representation it is in.
    """
    from vedagraph.enrich.surfaces import contains_private_use, render_for_display

    rows, _ = assigned
    for row in rows[:: max(1, len(rows) // 500)]:
        mantra = corpus.by_key[row.passage_key]
        for span in row.provenance.evidence:
            assert not contains_private_use(span.quote), span.quote
            if span.surface == "script_folded":
                assert span.quote in render_for_display(mantra.surfaces.script_folded)
            elif span.surface == "sandhi_insensitive":
                assert span.quote in render_for_display(mantra.surfaces.sandhi_insensitive)
            else:
                joined = [" ".join(t.split()) for t in mantra.translations]
                assert any(span.quote in t for t in joined)


def test_matched_aliases_are_recorded_on_every_row(assigned: tuple[list[Any], Any]) -> None:
    rows, _ = assigned
    for row in rows[:: max(1, len(rows) // 500)]:
        assert row.provenance.notes.startswith("matched aliases: ")
        assert row.provenance.notes.removeprefix("matched aliases: ").strip()


def test_output_is_sorted_and_free_of_duplicates(assigned: tuple[list[Any], Any]) -> None:
    rows, _ = assigned
    keys = [(r.passage_key, r.concept_id) for r in rows]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)


def test_two_runs_produce_byte_identical_rows(
    corpus: Corpus, concepts: tuple[ConceptRow, ...]
) -> None:
    """The reproducibility claim, checked rather than asserted.

    Serialised through ``as_row`` because that is what reaches disk and Neo4j; two runs
    that agree on objects but disagree on their emitted order would still produce a
    different graph.
    """
    first, _ = assign_concepts(corpus, concepts)
    second, _ = assign_concepts(corpus, concepts)
    assert [row.as_row() for row in first] == [row.as_row() for row in second]


def test_alias_order_in_the_registry_does_not_change_the_output(
    corpus: Corpus, concepts: tuple[ConceptRow, ...]
) -> None:
    """Reversing every alias list must not move a single edge.

    Input order is the classic hidden dependency in this kind of matcher: it changes which
    concept wins a tie, and it never shows up as an error.
    """
    reversed_rows = tuple(
        ConceptRow(
            concept_id=c.concept_id,
            preferred_label_sa=c.preferred_label_sa,
            preferred_label_en=c.preferred_label_en,
            node_type=c.node_type,
            aliases_sa=tuple(reversed(c.aliases_sa)),
            aliases_en=tuple(reversed(c.aliases_en)),
            broader=c.broader,
            definition=c.definition,
            related_devatas=c.related_devatas,
        )
        for c in reversed(concepts)
    )
    baseline, _ = assign_concepts(corpus, concepts)
    shuffled, _ = assign_concepts(corpus, reversed_rows)
    assert [r.as_row() for r in baseline] == [r.as_row() for r in shuffled]


def test_every_concept_is_used_by_at_least_one_passage(
    concepts: tuple[ConceptRow, ...], assigned: tuple[list[Any], Any]
) -> None:
    """A concept nothing reaches is a node that only makes the graph bigger."""
    rows, _ = assigned
    used = {row.concept_id for row in rows}
    assert {c.concept_id for c in concepts} - used == set()


def test_every_sanskrit_alias_is_attested_in_the_corpus(
    corpus: Corpus, concepts: tuple[ConceptRow, ...]
) -> None:
    """No alias may be aspirational.

    An unattested alias costs nothing at runtime and is therefore never noticed, which is
    exactly why a lexicon accumulates them until nobody can tell which entries were
    checked against the text and which were remembered from a grammar.
    """
    tokens: set[str] = set()
    for mantra in corpus.mantras:
        tokens.update(mantra.surfaces.tokens)
    unattested = sorted(
        alias
        for concept in concepts
        for alias in concept.aliases_sa
        if fold_alias(alias) not in tokens
    )
    assert unattested == []


def test_every_english_alias_is_attested_in_a_translation(
    corpus: Corpus, concepts: tuple[ConceptRow, ...]
) -> None:
    from vedagraph.enrich.concepts import ENGLISH_TOKEN_PATTERN

    words: set[str] = set()
    for mantra in corpus.mantras:
        for translation in mantra.translations:
            words.update(ENGLISH_TOKEN_PATTERN.findall(translation.lower()))
    unattested = sorted(
        alias for concept in concepts for alias in concept.aliases_en if alias not in words
    )
    assert unattested == []
