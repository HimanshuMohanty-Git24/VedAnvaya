"""The deterministic lexical layer: tokens, mentions, parallels, components, analytics.

The tests that matter most here are the negative ones. It is easy to check that Agni is
found; the properties worth defending are that a word which merely *looks* like an entity
name is not found, that an ambiguous lemma produces nothing at all, and that a candidate
never becomes an edge on its own.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
import yaml

from vedagraph.identity import entity_identity, rv_mantra_identity, uuid_for_urn
from vedagraph.lexical.aliases import (
    MENTION_POLICY_VERSION,
    LexicalMatcher,
    load_lexical_aliases,
    match_key,
    propose_alias_candidates,
)
from vedagraph.lexical.analytics import build_lexical_stats
from vedagraph.lexical.components import COMPONENT_POLICY_VERSION, load_component_assertions
from vedagraph.lexical.mentions import build_mentions
from vedagraph.lexical.morphology import (
    ANNOTATION_LAYER_ID,
    MORPHOLOGY_COMMIT_SHA,
    MorphologyArtifact,
    MorphologyParseReport,
    load_morphology_artifacts,
    normalize_lemma,
    parse_morphology,
    token_identity,
)
from vedagraph.lexical.parallels import (
    MantraText,
    ParallelRunReport,
    build_parallels,
    classify,
    find_exact_parallels,
    generate_candidate_pairs,
    score_pair,
)
from vedagraph.models.enums import (
    KnowledgeEntityType,
    LexicalMatchStatus,
    LexicalPredicate,
    LexicalProvenanceClass,
    MentionMethod,
    MetadataPredicate,
    ParallelMethod,
    ParallelStatus,
    ProvenanceClass,
    ResolutionStatus,
    ReviewStatus,
    ScopeOrigin,
)
from vedagraph.models.knowledge import KnowledgeAssertion, KnowledgeEntity

FIXTURE = Path("tests/fixtures/vedaweb/rv_zurich_morphology_sample.tei")

ARTIFACT = MorphologyArtifact(
    mandala=1,
    artifact_id="VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
    snapshot_path=FIXTURE,
    snapshot_id="VEDAWEB:fixture",
    sha256="0" * 64,
    url=(
        "https://raw.githubusercontent.com/VedaWebProject/vedaweb-data/"
        f"{MORPHOLOGY_COMMIT_SHA}/rigveda/TEI/rv_book_01.tei"
    ),
)

# Entities the fixture's lemmas point at, matching the real registry's keys.
ENTITY_LABELS = {
    "VG:DEVATA:AGNIH": "agniḥ",
    "VG:DEVATA:INDRAH": "indraḥ",
    "VG:DEVATA:MITRAH": "mitraḥ",
    "VG:DEVATA:KAH": "kaḥ",
    "VG:DEVATA:DADHIKRA": "dadhikrā",
    "VG:DEVATA:DADHIKRAH": "dadhikrāḥ",
    "VG:DEVATA:VARUNAH": "varuṇaḥ",
    "VG:DEVATA:MITRAVARUNAU": "mitrāvaruṇau",
    "VG:RISHI:AGNIH": "agniḥ",
}


def make_entities() -> dict[str, KnowledgeEntity]:
    entities: dict[str, KnowledgeEntity] = {}
    for key, label in ENTITY_LABELS.items():
        family, slug = key.split(":")[1], key.split(":")[2]
        _, urn, entity_id = entity_identity(family, slug)
        entities[key] = KnowledgeEntity(
            entity_id=entity_id,
            entity_key=key,
            canonical_urn=urn,
            entity_type=KnowledgeEntityType[family],
            preferred_label=label,
            preferred_label_iast=label,
            resolution_status=ResolutionStatus.EXACT,
        )
    return entities


def write_alias_registry(root: Path, rows: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "lexical_aliases.yaml").write_text(
        yaml.safe_dump(
            {
                "policy_version": MENTION_POLICY_VERSION,
                "annotation_layer_id": ANNOTATION_LAYER_ID,
                "aliases": rows,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


def alias_row(entity_key: str, lemma: str, lemma_ids: list[str], **overrides: object) -> dict:
    row = {
        "entity_key": entity_key,
        "lemma": lemma,
        "lemma_ids": lemma_ids,
        "alias_type": "CANONICAL_LEMMA",
        "review_status": "ACCEPTED",
        "evidence": "fixture",
    }
    row.update(overrides)
    return row


@pytest.fixture
def tokens():
    return parse_morphology(ARTIFACT)


@pytest.fixture
def corpus():
    keys = {}
    citations = {}
    for mandala, sukta, mantra in ((1, 1, 1), (1, 1, 2), (1, 1, 3), (1, 2, 1)):
        key, _, entity_id = rv_mantra_identity(mandala, sukta, mantra)
        keys[key] = entity_id
        citations[key] = f"RV {mandala}.{sukta}.{mantra}"
    return keys, citations


# --------------------------------------------------------------------------------------
# Morphology parsing and token identity
# --------------------------------------------------------------------------------------


def test_parses_only_the_zurich_layer(tokens):
    assert len(tokens) == 9
    assert {token.annotation_layer_id for token in tokens} == {ANNOTATION_LAYER_ID}
    # The aufrecht <lg> in the fixture must contribute nothing.
    assert all("aufrecht" not in token.source_locator for token in tokens)


def test_alignment_is_structural_not_textual(tokens):
    """Citation, never text similarity, decides which mantra a token belongs to."""
    assert {token.passage_key for token in tokens} == {
        "VG:RV:SAK:M01:S001:V001",
        "VG:RV:SAK:M01:S001:V002",
        "VG:RV:SAK:M01:S001:V003",
        "VG:RV:SAK:M01:S002:V001",
    }
    for token in tokens:
        mandala, sukta, mantra = (
            int(token.passage_key.split(":")[3][1:]),
            int(token.passage_key.split(":")[4][1:]),
            int(token.passage_key.split(":")[5][1:]),
        )
        _, _, expected = rv_mantra_identity(mandala, sukta, mantra)
        assert token.passage_id == expected


def test_token_ids_are_deterministic_and_order_independent(tokens):
    keys = [token.token_key for token in tokens]
    assert len(keys) == len(set(keys))
    again = parse_morphology(ARTIFACT)
    assert [token.token_id for token in again] == [token.token_id for token in tokens]
    # Identity comes from the citation alone, not from position in the file.
    key, urn, token_id = token_identity(1, 1, 1, "a", 1)
    assert key == "VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M01:S001:V001:PA:T001"
    assert token_id == uuid_for_urn(urn)
    assert tokens[0].token_key == key


def test_token_ids_name_the_annotation_layer_but_mantra_ids_do_not(tokens):
    """A different morphology source may re-tokenize; it may not re-identify a mantra."""
    assert all(":VEDAWEB-ZURICH:" in token.token_key for token in tokens)
    _, _, mantra_id = rv_mantra_identity(1, 1, 1)
    assert tokens[0].passage_id == mantra_id
    assert "VEDAWEB" not in tokens[0].passage_key


def test_token_sequence_is_contiguous_within_a_mantra(tokens):
    first = [token for token in tokens if token.passage_key == "VG:RV:SAK:M01:S001:V001"]
    assert [token.sequence for token in first] == [1, 2, 3]
    # The sequence spans padas; the pada letter is kept separately.
    assert [token.pada for token in first] == ["a", "a", "b"]


def test_lemmas_are_preserved_verbatim_and_never_invented(tokens):
    by_key = {token.token_key: token for token in tokens}
    agni = by_key["VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M01:S001:V001:PA:T001"]
    assert agni.lemma == "agní-"
    assert agni.lemma_ids == ["lemma_agni_79"]
    assert agni.part_of_speech == "nominal stem"
    assert agni.morphological_features == {"case": "ACC", "gender": "M", "number": "SG"}
    assert agni.surface_form == "agním"


def test_multiple_lemma_ids_are_kept_not_collapsed(tokens):
    dyu = next(token for token in tokens if token.lemma.startswith("dyú-"))
    assert dyu.lemma_ids == ["lemma_agni_79", "lemma_div_4231"]


def test_normalize_lemma_strips_notation_only():
    assert normalize_lemma("agní-") == "agni"
    assert normalize_lemma("√jan¹-") == "jan¹"
    # Distinct spellings are never merged by normalization.
    assert normalize_lemma("uṣṇik") != normalize_lemma("uṣnik")


def test_parse_report_records_gaps_rather_than_hiding_them():
    report = MorphologyParseReport()
    parse_morphology(ARTIFACT, report=report)
    assert report.stanzas_seen == 4
    assert report.stanzas_with_annotation == 4
    assert report.unparsable_stanza_ids == []
    assert report.tokens_without_lemma == []


def test_artifact_index_refuses_an_unpinned_commit(tmp_path):
    index = tmp_path / "artifacts.json"
    index.write_text(
        '[{"mandala": 1, "artifact_id": "X", "snapshot_path": "x.tei", '
        '"snapshot_id": "s", "sha256": "0", '
        '"url": "https://x/vedaweb-data/deadbeef/rigveda/TEI/rv_book_01.tei"}]',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must all come from"):
        load_morphology_artifacts(index)


# --------------------------------------------------------------------------------------
# Lexical aliases
# --------------------------------------------------------------------------------------


def test_alias_registry_rejects_a_rishi_entity(tmp_path):
    """v1 is Devata-only; a Rishi alias must fail loudly, not be silently dropped."""
    write_alias_registry(tmp_path, [alias_row("VG:RISHI:AGNIH", "agní-", ["lemma_agni_79"])])
    with pytest.raises(ValueError, match="v1 accepts lexical aliases for"):
        load_lexical_aliases(tmp_path, entities=make_entities())


def test_alias_registry_rejects_an_unknown_entity(tmp_path):
    write_alias_registry(tmp_path, [alias_row("VG:DEVATA:NOPE", "x-", ["lemma_x"])])
    with pytest.raises(ValueError, match="unknown entity"):
        load_lexical_aliases(tmp_path, entities=make_entities())


def test_alias_registry_pins_its_policy_version(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "lexical_aliases.yaml").write_text(
        yaml.safe_dump({"policy_version": "something-else", "aliases": []}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="policy_version"):
        load_lexical_aliases(tmp_path, entities=make_entities())


def test_unreviewed_alias_produces_no_mention(tmp_path, tokens, corpus):
    entities = make_entities()
    write_alias_registry(
        tmp_path,
        [alias_row("VG:DEVATA:AGNIH", "agní-", ["lemma_agni_79"], review_status="NEEDS_REVIEW")],
    )
    aliases = load_lexical_aliases(tmp_path, entities=entities)
    assert aliases[0].may_produce_mention is False
    passage_ids, citations = corpus
    mentions, _ = build_mentions(
        tokens, LexicalMatcher(aliases), entities, citations=citations, passage_ids=passage_ids
    )
    assert mentions == []


def test_do_not_match_suppresses_a_high_frequency_lemma(tmp_path, tokens, corpus):
    """`ka-` is the interrogative pronoun. It must never reach VG:DEVATA:KAH."""
    entities = make_entities()
    write_alias_registry(
        tmp_path,
        [
            alias_row("VG:DEVATA:KAH", "ká-", ["lemma_ka_2373"], alias_type="DO_NOT_MATCH"),
            alias_row("VG:DEVATA:MITRAH", "mitrá-", ["lemma_mitra_6824"]),
        ],
    )
    aliases = load_lexical_aliases(tmp_path, entities=entities)
    matcher = LexicalMatcher(aliases)
    ka = next(token for token in tokens if token.lemma == "ká-")
    assert matcher.match(ka).status is LexicalMatchStatus.SUPPRESSED_DO_NOT_MATCH

    passage_ids, citations = corpus
    mentions, _ = build_mentions(
        tokens, matcher, entities, citations=citations, passage_ids=passage_ids
    )
    assert {mention.object_key for mention in mentions} == {"VG:DEVATA:MITRAH"}


def test_ambiguous_lemma_creates_no_edge(tmp_path, tokens, corpus):
    """One lemma reaching two accepted entities fails closed, however frequent."""
    entities = make_entities()
    write_alias_registry(
        tmp_path,
        [
            alias_row("VG:DEVATA:DADHIKRA", "dadhikrā́-", ["lemma_daDikrA_4074"]),
            alias_row("VG:DEVATA:DADHIKRAH", "dadhikrā́-", ["lemma_daDikrA_4074"]),
        ],
    )
    aliases = load_lexical_aliases(tmp_path, entities=entities)
    passage_ids, citations = corpus
    mentions, ambiguous = build_mentions(
        tokens, LexicalMatcher(aliases), entities, citations=citations, passage_ids=passage_ids
    )
    assert mentions == []
    assert len(ambiguous) == 1
    assert ambiguous[0].status is LexicalMatchStatus.AMBIGUOUS_LEXICAL_ENTITY
    assert ambiguous[0].candidate_entity_keys == [
        "VG:DEVATA:DADHIKRA",
        "VG:DEVATA:DADHIKRAH",
    ]


def test_source_lemma_ambiguity_is_reported_not_resolved(tmp_path, tokens, corpus):
    """The annotators gave `dyú- ~ div-` two entries; only one reaches an entity."""
    entities = make_entities()
    write_alias_registry(tmp_path, [alias_row("VG:DEVATA:AGNIH", "agní-", ["lemma_agni_79"])])
    aliases = load_lexical_aliases(tmp_path, entities=entities)
    matcher = LexicalMatcher(aliases)
    dyu = next(token for token in tokens if token.lemma.startswith("dyú-"))
    assert matcher.match(dyu).status is LexicalMatchStatus.AMBIGUOUS_SOURCE_LEMMA


def test_no_substring_matching(tmp_path, tokens, corpus):
    """`mitra` occurs inside `viśvāmitra-`; a substring engine would match it."""
    entities = make_entities()
    write_alias_registry(tmp_path, [alias_row("VG:DEVATA:MITRAH", "mitrá-", ["lemma_mitra_6824"])])
    aliases = load_lexical_aliases(tmp_path, entities=entities)
    matcher = LexicalMatcher(aliases)

    compound = tokens[0].model_copy(
        update={
            "lemma": "viśvā́mitra-",
            "normalized_lemma": "viśvāmitra",
            "lemma_ids": ["lemma_viSvAmitra_8224"],
            "surface_form": "viśvā́mitraḥ",
        }
    )
    assert matcher.match(compound).status is LexicalMatchStatus.NO_LEXICAL_ALIAS


def test_fuzzy_proposals_are_candidates_and_never_edges(tokens):
    """propose_alias_candidates may suggest; it may not create an alias or an edge."""
    entities = make_entities()
    candidates = propose_alias_candidates(tokens, entities, existing=[])
    assert candidates, "the exact proposal rules should find at least one pairing"
    for candidate in candidates:
        assert candidate.review_status is ReviewStatus.NEEDS_REVIEW
        assert not hasattr(candidate, "assertion_id")
    # A candidate for an already-reviewed entity is not proposed again.
    reviewed = propose_alias_candidates(
        tokens,
        entities,
        existing=load_lexical_aliases_inline(entities),
    )
    assert all(c.entity_key != "VG:DEVATA:AGNIH" for c in reviewed)


def load_lexical_aliases_inline(entities, tmp=Path("tests/fixtures/_tmp_alias")):
    tmp.mkdir(parents=True, exist_ok=True)
    write_alias_registry(tmp, [alias_row("VG:DEVATA:AGNIH", "agní-", ["lemma_agni_79"])])
    aliases = load_lexical_aliases(tmp, entities=entities)
    (tmp / "lexical_aliases.yaml").unlink()
    tmp.rmdir()
    return aliases


def test_match_key_folds_transcription_not_meaning():
    # IAST and ISO 15919 spellings of the same word must compare equal.
    assert match_key("bṛhaspati") == match_key("br̥haspati")
    # Different words must not.
    assert match_key("agni") != match_key("indra")


# --------------------------------------------------------------------------------------
# MENTIONS_ENTITY
# --------------------------------------------------------------------------------------


@pytest.fixture
def built(tmp_path, tokens, corpus):
    entities = make_entities()
    write_alias_registry(
        tmp_path,
        [
            alias_row("VG:DEVATA:AGNIH", "agní-", ["lemma_agni_79"]),
            alias_row("VG:DEVATA:INDRAH", "índra-", ["lemma_indra_1708"]),
            alias_row("VG:DEVATA:MITRAH", "mitrá-", ["lemma_mitra_6824"]),
            alias_row("VG:DEVATA:KAH", "ká-", ["lemma_ka_2373"], alias_type="DO_NOT_MATCH"),
        ],
    )
    aliases = load_lexical_aliases(tmp_path, entities=entities)
    passage_ids, citations = corpus
    mentions, ambiguous = build_mentions(
        tokens, LexicalMatcher(aliases), entities, citations=citations, passage_ids=passage_ids
    )
    return entities, aliases, mentions, ambiguous


def test_multiple_occurrences_make_one_edge_with_all_evidence(built):
    _, _, mentions, _ = built
    agni = next(
        m
        for m in mentions
        if m.subject_key == "VG:RV:SAK:M01:S001:V001" and m.object_key == "VG:DEVATA:AGNIH"
    )
    assert agni.occurrence_count == 2
    assert len(agni.evidence) == 2
    assert [item.surface for item in agni.evidence] == ["agním", "ágne"]
    assert [item.pada for item in agni.evidence] == ["a", "b"]
    assert [item.sequence for item in agni.evidence] == [1, 3]


def test_every_mention_carries_token_level_evidence(built):
    _, _, mentions, _ = built
    for mention in mentions:
        assert mention.evidence
        assert mention.occurrence_count == len(mention.evidence)
        assert mention.provenance_class is LexicalProvenanceClass.DETERMINISTIC_DERIVED
        assert mention.predicate is LexicalPredicate.MENTIONS_ENTITY
        for item in mention.evidence:
            assert isinstance(item.token_id, UUID)
            assert item.method is MentionMethod.LEMMA_ID_EXACT


def test_mention_ids_are_stable_for_a_subject_object_pair(built):
    _, _, mentions, _ = built
    urn = "urn:vedagraph:assertion:mentions_entity:vg:rv:sak:m01:s001:v001:vg:devata:agnih"
    agni = next(
        m
        for m in mentions
        if m.subject_key == "VG:RV:SAK:M01:S001:V001" and m.object_key == "VG:DEVATA:AGNIH"
    )
    assert agni.assertion_id == uuid_for_urn(urn)


def test_mention_predicate_never_carries_a_metadata_predicate(built):
    _, _, mentions, _ = built
    values = {m.predicate.value for m in mentions}
    assert values == {"MENTIONS_ENTITY"}
    assert not values & {p.value for p in MetadataPredicate}


# --------------------------------------------------------------------------------------
# HAS_COMPONENT
# --------------------------------------------------------------------------------------


def write_components(root: Path, rows: list[dict[str, object]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "devata_components.yaml").write_text(
        yaml.safe_dump(
            {"policy_version": COMPONENT_POLICY_VERSION, "components": rows}, allow_unicode=True
        ),
        encoding="utf-8",
    )


def test_only_reviewed_components_become_edges(tmp_path):
    entities = make_entities()
    write_components(
        tmp_path,
        [
            {
                "composite_entity_id": "VG:DEVATA:MITRAVARUNAU",
                "component_entity_ids": ["VG:DEVATA:MITRAH", "VG:DEVATA:VARUNAH"],
                "evidence": "dvandva",
                "review_status": "ACCEPTED",
            },
            {
                "composite_entity_id": "VG:DEVATA:DADHIKRA",
                "component_entity_ids": ["VG:DEVATA:AGNIH"],
                "evidence": "not reviewed",
                "review_status": "NEEDS_REVIEW",
            },
        ],
    )
    assertions = load_component_assertions(tmp_path, entities=entities)
    assert [a.object_key for a in assertions] == ["VG:DEVATA:MITRAH", "VG:DEVATA:VARUNAH"]
    assert [a.component_sequence for a in assertions] == [1, 2]
    for assertion in assertions:
        assert assertion.provenance_class is LexicalProvenanceClass.HUMAN_REVIEWED
        assert assertion.review_status is ReviewStatus.ACCEPTED


def test_group_deity_rejection_produces_nothing(tmp_path):
    """A REJECTED row is a recorded decision, not an edge."""
    entities = make_entities()
    write_components(
        tmp_path,
        [
            {
                "composite_entity_id": "VG:DEVATA:AGNIH",
                "component_entity_ids": [],
                "evidence": "a group is not the set of its members",
                "review_status": "REJECTED",
            }
        ],
    )
    assert load_component_assertions(tmp_path, entities=entities) == []


def test_accepted_row_without_components_is_an_error(tmp_path):
    entities = make_entities()
    write_components(
        tmp_path,
        [
            {
                "composite_entity_id": "VG:DEVATA:MITRAVARUNAU",
                "component_entity_ids": [],
                "evidence": "x",
                "review_status": "ACCEPTED",
            }
        ],
    )
    with pytest.raises(ValueError, match="ACCEPTED but lists no components"):
        load_component_assertions(tmp_path, entities=entities)


def test_component_naming_an_unknown_entity_is_an_error(tmp_path):
    entities = make_entities()
    write_components(
        tmp_path,
        [
            {
                "composite_entity_id": "VG:DEVATA:MITRAVARUNAU",
                "component_entity_ids": ["VG:DEVATA:GHOST"],
                "evidence": "x",
                "review_status": "ACCEPTED",
            }
        ],
    )
    with pytest.raises(ValueError, match="unknown component"):
        load_component_assertions(tmp_path, entities=entities)


def test_the_real_component_registry_never_expands_a_group():
    """Guards the actual committed registry, not a fixture."""
    document = yaml.safe_load(
        Path("data/registry/devata_components.yaml").read_text(encoding="utf-8")
    )
    rows = {row["composite_entity_id"]: row for row in document["components"]}
    for key in ("VG:DEVATA:VISVEDEVAH", "VG:DEVATA:ADITYAH", "VG:DEVATA:MARUTAH"):
        assert rows[key]["review_status"] == "REJECTED"
        assert rows[key]["component_entity_ids"] == []
    for row in document["components"]:
        if row["review_status"] == "ACCEPTED":
            assert row["component_entity_ids"], row["composite_entity_id"]
            assert row["composite_entity_id"] not in row["component_entity_ids"]


# --------------------------------------------------------------------------------------
# Parallels
# --------------------------------------------------------------------------------------


def make_text(key: str, text: str, tokens: tuple[str, ...], mandala: int = 1) -> MantraText:
    parts = key.split(":")
    identity = rv_mantra_identity(int(parts[3][1:]), int(parts[4][1:]), int(parts[5][1:]))
    return MantraText(
        passage_key=key,
        passage_id=identity[2],
        citation=key,
        mandala=mandala,
        source_text=text,
        tokens=tokens,
        lemmas=tokens,
    )


TEXTS = [
    make_text("VG:RV:SAK:M01:S001:V001", "agnim ile purohitam", ("agnim", "ile", "purohitam")),
    make_text("VG:RV:SAK:M01:S002:V001", "agnim ile purohitam", ("agnim", "ile", "purohitam")),
    make_text("VG:RV:SAK:M01:S003:V001", "agnim ile devam", ("agnim", "ile", "devam")),
    make_text("VG:RV:SAK:M02:S001:V001", "indram huve maghavanam", ("indram", "huve", "x"), 2),
]


def test_exact_parallels_are_grouped_and_pairs_canonically_ordered():
    report = ParallelRunReport()
    groups, pairs = find_exact_parallels(TEXTS, report=report)
    source = [g for g in groups if g.method is ParallelMethod.SOURCE_EXACT]
    assert len(source) == 1
    assert source[0].member_keys == ["VG:RV:SAK:M01:S001:V001", "VG:RV:SAK:M01:S002:V001"]
    # A-B exists; B-A must not.
    assert ("VG:RV:SAK:M01:S001:V001", "VG:RV:SAK:M01:S002:V001") in pairs
    assert ("VG:RV:SAK:M01:S002:V001", "VG:RV:SAK:M01:S001:V001") not in pairs
    for left, right in pairs:
        assert left < right


def test_representation_levels_are_not_collapsed():
    report = ParallelRunReport()
    find_exact_parallels(TEXTS, report=report)
    assert set(report.exact_pairs) == {
        "SOURCE_EXACT",
        "NFC_EXACT",
        "ACCENTLESS_EXACT",
        "TOKEN_EXACT",
        "LEMMA_SEQUENCE_EXACT",
    }


def test_accent_only_difference_is_accentless_but_not_source_exact():
    texts = [
        make_text("VG:RV:SAK:M01:S001:V001", "agním ī́ḷe", ("a",)),
        make_text("VG:RV:SAK:M01:S002:V001", "agnim īḷe", ("a",)),
    ]
    report = ParallelRunReport()
    _, pairs = find_exact_parallels(texts, report=report)
    methods = pairs[("VG:RV:SAK:M01:S001:V001", "VG:RV:SAK:M01:S002:V001")]
    assert ParallelMethod.SOURCE_EXACT not in methods
    assert ParallelMethod.ACCENTLESS_EXACT in methods


def test_parallel_records_carry_a_canonical_order_invariant():
    report = ParallelRunReport()
    parallels, _, _ = build_parallels(TEXTS, report=report)
    for parallel in parallels:
        assert parallel.subject_key < parallel.object_key
        assert parallel.predicate in {
            LexicalPredicate.EXACT_PARALLEL_OF,
            LexicalPredicate.PARALLEL_TO,
        }


def test_candidate_generation_is_deterministic():
    first = generate_candidate_pairs(TEXTS, report=ParallelRunReport())
    second = generate_candidate_pairs(list(reversed(TEXTS)), report=ParallelRunReport())
    assert first == second


def test_candidate_generation_is_not_quadratic():
    """The engine must scale by hashing, not by comparing every pair."""
    many = [
        make_text(f"VG:RV:SAK:M01:S{index:03d}:V001", f"unrelated text {index}", (f"w{index}",))
        for index in range(1, 301)
    ]
    report = ParallelRunReport()
    pairs = generate_candidate_pairs(many, report=report)
    assert len(pairs) < 300 * 299 // 2 / 10


def test_metrics_are_stored_individually():
    metrics = score_pair(TEXTS[0], TEXTS[2])
    assert 0 < metrics.token_jaccard < 1
    assert 0 < metrics.ordered_token_similarity < 1
    assert metrics.shared_token_count == 2
    assert metrics.left_token_count == 3
    # No fused score field exists to be misread as authoritative.
    assert not hasattr(metrics, "score")


def test_threshold_policy_rejects_short_mantras():
    short = score_pair(
        make_text("VG:RV:SAK:M01:S001:V001", "a b", ("a", "b")),
        make_text("VG:RV:SAK:M01:S002:V001", "a b", ("a", "b")),
    )
    assert classify(short) is ParallelStatus.CANDIDATE_PARALLEL


def test_threshold_policy_needs_every_condition():
    metrics = score_pair(
        make_text("VG:RV:SAK:M01:S001:V001", "a b c d e", ("a", "b", "c", "d", "e")),
        make_text("VG:RV:SAK:M01:S002:V001", "a b c d e", ("a", "b", "c", "d", "e")),
    )
    assert classify(metrics) is ParallelStatus.HIGH_CONFIDENCE_NEAR_PARALLEL
    unrelated = score_pair(
        make_text("VG:RV:SAK:M01:S001:V001", "a b c d e", ("a", "b", "c", "d", "e")),
        make_text("VG:RV:SAK:M01:S002:V001", "v w x y z", ("v", "w", "x", "y", "z")),
    )
    assert classify(unrelated) is ParallelStatus.REJECTED


def test_pada_level_parallels_are_not_designed_out():
    report = ParallelRunReport()
    parallels, _, _ = build_parallels(TEXTS, report=report)
    parallel = parallels[0]
    assert parallel.unit.value == "MANTRA"
    # The fields a pada-level record would need already exist.
    assert parallel.subject_locator is None
    assert parallel.object_locator is None


# --------------------------------------------------------------------------------------
# Analytics
# --------------------------------------------------------------------------------------


def test_assignment_and_mention_are_counted_separately(built, tokens):
    entities, aliases, mentions, ambiguous = built
    # Traditional metadata assigns Mitra where the text never names him, and vice versa.
    _, _, subject_id = rv_mantra_identity(1, 1, 3)
    assignment = KnowledgeAssertion(
        assertion_id=uuid_for_urn("urn:vedagraph:assertion:test:1"),
        subject_key="VG:RV:SAK:M01:S001:V003",
        subject_id=subject_id,
        predicate=MetadataPredicate.HAS_DEVATA,
        object_key="VG:DEVATA:MITRAH",
        object_id=entities["VG:DEVATA:MITRAH"].entity_id,
        source_label="mitraḥ",
        source_assertion_id=uuid_for_urn("urn:vedagraph:assertion:test:src"),
        provenance_class=ProvenanceClass.SOURCE_EXPLICIT,
        scope_origin=ScopeOrigin.SUKTA_WIDE,
        resolution_method=ResolutionStatus.EXACT,
        source_id="WSC2023",
        source_artifact_id="X",
        citation="RV 1.1.3",
    )
    stats, _ = build_lexical_stats(
        tokens=tokens,
        entities=entities,
        aliases=aliases,
        alias_candidates=[],
        mentions=mentions,
        ambiguous_count=len(ambiguous),
        knowledge_assertions=[assignment],
        parallels=[],
        parallel_candidates=[],
        exact_groups=[],
        component_count=0,
        total_mantras=4,
    )
    mitra = next(row for row in stats.top_assigned_devatas if row.entity_key == "VG:DEVATA:MITRAH")
    assert mitra.mantra_assignment_count == 1
    assert mitra.mantra_mention_count == 1
    # The mantra assigned Mitra (1.1.3) is not the mantra mentioning him (1.1.2).
    assert mitra.assigned_and_mentioned_count == 0
    assert mitra.assigned_not_mentioned_count == 1
    assert mitra.mentioned_not_assigned_count == 1


def test_stats_refuse_to_offer_one_combined_number(built, tokens):
    entities, aliases, mentions, ambiguous = built
    stats, _ = build_lexical_stats(
        tokens=tokens,
        entities=entities,
        aliases=aliases,
        alias_candidates=[],
        mentions=mentions,
        ambiguous_count=len(ambiguous),
        knowledge_assertions=[],
        parallels=[],
        parallel_candidates=[],
        exact_groups=[],
        component_count=0,
        total_mantras=4,
    )
    assert "warning" in stats.metric_definitions
    assert "most used god" in stats.metric_definitions["warning"]
    for field in ("mantra_assignment_count", "mantra_mention_count", "token_occurrence_count"):
        assert field in stats.metric_definitions


def test_co_occurrence_is_an_observation_with_a_unit(built, tokens):
    entities, aliases, mentions, ambiguous = built
    _, co = build_lexical_stats(
        tokens=tokens,
        entities=entities,
        aliases=aliases,
        alias_candidates=[],
        mentions=mentions,
        ambiguous_count=len(ambiguous),
        knowledge_assertions=[],
        parallels=[],
        parallel_candidates=[],
        exact_groups=[],
        component_count=0,
        total_mantras=4,
    )
    pair = next(
        row
        for row in co
        if row.left_entity_key == "VG:DEVATA:AGNIH" and row.right_entity_key == "VG:DEVATA:INDRAH"
    )
    assert pair.count == 2  # 1.1.1 and 1.2.1
    assert pair.unit == "MANTRA"
    assert pair.method == "LEXICAL_MENTION_CO_OCCURRENCE"
    # Co-occurrence pairs are canonically ordered, like parallels.
    for row in co:
        assert row.left_entity_key < row.right_entity_key


# --------------------------------------------------------------------------------------
# Committed registries
# --------------------------------------------------------------------------------------


def test_committed_alias_registry_is_devata_only_and_evidenced():
    document = yaml.safe_load(
        Path("data/registry/lexical_aliases.yaml").read_text(encoding="utf-8")
    )
    assert document["policy_version"] == MENTION_POLICY_VERSION
    for row in document["aliases"]:
        assert row["entity_key"].startswith("VG:DEVATA:"), row["entity_key"]
        assert row["evidence"].strip(), row["entity_key"]
        assert row["review_status"] in {"ACCEPTED", "NEEDS_REVIEW", "REJECTED"}
        if row["alias_type"] != "DO_NOT_MATCH":
            assert row["lemma_ids"], row["entity_key"]


def test_committed_alias_registry_has_no_duplicate_entities():
    document = yaml.safe_load(
        Path("data/registry/lexical_aliases.yaml").read_text(encoding="utf-8")
    )
    keys = [row["entity_key"] for row in document["aliases"]]
    assert len(keys) == len(set(keys))
