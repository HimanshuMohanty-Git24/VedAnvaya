"""The knowledge build: alignment, scope, provenance, QA, and byte-stable output."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from vedagraph.identity import rv_mandala_identity, rv_mantra_identity, rv_sukta_identity
from vedagraph.knowledge.build import build_knowledge, load_corpus_index
from vedagraph.knowledge.output import write_knowledge_layer
from vedagraph.knowledge.stats import build_stats
from vedagraph.models import Passage
from vedagraph.models.enums import (
    EntityType,
    MetadataPredicate,
    ProvenanceClass,
    QASeverity,
    QAStatus,
    ResolutionStatus,
    ScopeOrigin,
    ScopeType,
)
from vedagraph.storage.jsonl import write_jsonl

FIXTURES = Path("tests/fixtures/anukramani")
BUILT_AT = datetime(2026, 1, 1, tzinfo=UTC)

# Verse counts matching the fixture rows exactly.
SHAPE = {(1, 1): 3, (1, 2): 4, (1, 3): 5, (2, 1): 2, (2, 2): 3, (2, 3): 2}

REGISTRY_LABELS = {
    "rishis.yaml": [
        ("VG:RISHI:VAISVAMITRO-MADHUCCHANDAH", "vaiśvāmitro madhucchandāḥ"),
        ("VG:RISHI:KANVO-MEDHATITHIH", "kāṇvo medhātithiḥ"),
        ("VG:RISHI:SAUNAKO-GRTSAMADAH", "śaunako gṛtsamadaḥ"),
    ],
    "devatas.yaml": [
        ("VG:DEVATA:AGNIH", "agniḥ"),
        ("VG:DEVATA:VAYUH", "vāyuḥ"),
        ("VG:DEVATA:INDRAVAYU", "indravāyū"),
        ("VG:DEVATA:MITRAVARUNAU", "mitrāvaruṇau"),
        ("VG:DEVATA:ILA-SARASVATI-MAHI", "iḻā-sarasvatī-mahī"),
        ("VG:DEVATA:DAMPATI", "dampatī"),
    ],
    "chandas.yaml": [
        ("VG:CHANDAS:GAYATRI", "gāyatrī"),
        ("VG:CHANDAS:JAGATI", "jagatī"),
        ("VG:CHANDAS:ANUSTUP", "anuṣṭup"),
        ("VG:CHANDAS:USNIK", "uṣṇik"),
        ("VG:CHANDAS:TRISTUP", "triṣṭup"),
    ],
}

ALIASES = [
    {
        "entity_type": "CHANDAS",
        "alias": "jagatiī",
        "canonical": "jagatī",
        "alias_type": "SOURCE_SPELLING",
        "evidence": "fixture: doubled vowel sign against a far more frequent spelling",
    },
    {
        "entity_type": "CHANDAS",
        "alias": "uṣnik",
        "canonical": "uṣṇik",
        "alias_type": "SOURCE_SPELLING",
        "evidence": "fixture: missing retroflex dot against a far more frequent spelling",
    },
]


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    root = tmp_path / "registry"
    root.mkdir()
    for filename, entries in REGISTRY_LABELS.items():
        entity_type = {"rishis.yaml": "RISHI", "devatas.yaml": "DEVATA", "chandas.yaml": "CHANDAS"}[
            filename
        ]
        (root / filename).write_text(
            yaml.safe_dump(
                {
                    "entities": [
                        {
                            "entity_key": key,
                            "entity_type": entity_type,
                            "preferred_label": label,
                        }
                        for key, label in entries
                    ]
                },
                allow_unicode=True,
            ),
            encoding="utf-8",
        )
    (root / "anukramani_aliases.yaml").write_text(
        yaml.safe_dump({"aliases": ALIASES}, allow_unicode=True), encoding="utf-8"
    )
    return root


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    directory = tmp_path / "corpus"
    passages: list[Passage] = []
    for mandala in (1, 2):
        key, urn, entity_id = rv_mandala_identity(mandala)
        passages.append(
            Passage(
                entity_id=entity_id,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.SECTION,
                work_id="VG:WORK:RV:SAK",
                hierarchy={"mandala": mandala},
                canonical_citation=f"RV {mandala}",
                sequence_in_parent=mandala,
            )
        )
    for (mandala, sukta), verses in sorted(SHAPE.items()):
        key, urn, entity_id = rv_sukta_identity(mandala, sukta)
        passages.append(
            Passage(
                entity_id=entity_id,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.HYMN,
                work_id="VG:WORK:RV:SAK",
                hierarchy={"mandala": mandala, "sukta": sukta},
                canonical_citation=f"RV {mandala}.{sukta}",
                parent_key=f"VG:RV:SAK:M{mandala:02d}",
                sequence_in_parent=sukta,
            )
        )
        for mantra in range(1, verses + 1):
            key, urn, entity_id = rv_mantra_identity(mandala, sukta, mantra)
            passages.append(
                Passage(
                    entity_id=entity_id,
                    canonical_key=key,
                    canonical_urn=urn,
                    entity_type=EntityType.MANTRA,
                    work_id="VG:WORK:RV:SAK",
                    hierarchy={"mandala": mandala, "sukta": sukta, "mantra": mantra},
                    canonical_citation=f"RV {mandala}.{sukta}.{mantra}",
                    parent_key=f"VG:RV:SAK:M{mandala:02d}:S{sukta:03d}",
                    sequence_in_parent=mantra,
                )
            )
    write_jsonl(directory / "passages.jsonl", passages)
    (directory / "manifest.json").write_text(
        f'{{"version": "fixture-corpus-1", "passage_count": {sum(SHAPE.values())}}}',
        encoding="utf-8",
    )
    return directory


def _artifacts() -> list[dict[str, object]]:
    return [
        {
            "mandala": mandala,
            "artifact_id": f"WSC2023.RV.ANUKRAMANI.M{mandala:02d}",
            "snapshot_path": str(FIXTURES / f"Mandala_{mandala}.txt"),
            "snapshot_id": f"WSC2023:fixture{mandala}",
            "sha256": "0" * 64,
            "url": (
                "https://raw.githubusercontent.com/mahesh-ak/WSC2023/"
                f"{'a' * 40}/Anukramani/Mandala_{mandala}.txt"
            ),
        }
        for mandala in (1, 2)
    ]


def test_every_row_aligns_and_the_verse_counts_agree(corpus: Path, registry: Path) -> None:
    result = build_knowledge(corpus_dir=corpus, artifacts=_artifacts(), registry_root=registry)
    assert result.alignment.dataset_rows == 6
    assert result.alignment.aligned_rows == 6
    assert result.alignment.unaligned_rows == []
    assert result.alignment.duplicate_rows == []
    assert result.alignment.verse_count_mismatches == []
    assert result.qa_status is QAStatus.PASSED_WITH_WARNINGS
    assert not [issue for issue in result.qa_issues if issue.severity is QASeverity.ERROR]


def test_a_verse_count_disagreement_fails_the_build(corpus: Path, registry: Path) -> None:
    passages = [
        record
        for record in (corpus / "passages.jsonl").read_text(encoding="utf-8").splitlines()
        if "VG:RV:SAK:M01:S001:V003" not in record
    ]
    (corpus / "passages.jsonl").write_text("\n".join(passages) + "\n", encoding="utf-8")
    result = build_knowledge(corpus_dir=corpus, artifacts=_artifacts(), registry_root=registry)
    errors = [issue for issue in result.qa_issues if issue.severity is QASeverity.ERROR]
    assert errors
    assert any(issue.check_id == "anukramani_verse_count_mismatch" for issue in errors)
    assert result.qa_status is QAStatus.FAILED


def test_scope_is_preserved_and_a_hymn_wide_claim_is_marked_as_derived(
    corpus: Path, registry: Path
) -> None:
    result = build_knowledge(corpus_dir=corpus, artifacts=_artifacts(), registry_root=registry)
    sukta_wide = [
        assertion
        for assertion in result.source_assertions
        if assertion.subject_key == "VG:RV:SAK:M01:S001"
        and assertion.predicate is MetadataPredicate.HAS_DEVATA
    ]
    assert [item.scope_type for item in sukta_wide] == [ScopeType.WHOLE_PASSAGE]

    edges = {
        (item.subject_key, item.object_key): item
        for item in result.assertions
        if item.predicate is MetadataPredicate.HAS_DEVATA
    }
    inherited = edges[("VG:RV:SAK:M01:S001:V002", "VG:DEVATA:AGNIH")]
    assert inherited.scope_origin is ScopeOrigin.SUKTA_WIDE
    assert inherited.provenance_class is ProvenanceClass.SOURCE_DERIVED_SCOPE

    explicit = edges[("VG:RV:SAK:M01:S002:V003", "VG:DEVATA:INDRAVAYU")]
    assert explicit.scope_origin is ScopeOrigin.SINGLE_MANTRA
    assert explicit.provenance_class is ProvenanceClass.SOURCE_EXPLICIT


def test_a_verse_set_is_not_widened(corpus: Path, registry: Path) -> None:
    result = build_knowledge(corpus_dir=corpus, artifacts=_artifacts(), registry_root=registry)
    assigned = {
        item.subject_key
        for item in result.assertions
        if item.object_key == "VG:DEVATA:ILA-SARASVATI-MAHI"
    }
    assert assigned == {
        "VG:RV:SAK:M01:S003:V001",
        "VG:RV:SAK:M01:S003:V002",
        "VG:RV:SAK:M01:S003:V005",
    }


def test_every_edge_links_back_to_its_source_assertion(corpus: Path, registry: Path) -> None:
    result = build_knowledge(corpus_dir=corpus, artifacts=_artifacts(), registry_root=registry)
    known = {item.assertion_id for item in result.source_assertions}
    assert result.assertions
    for assertion in result.assertions:
        assert assertion.source_assertion_id in known
        assert assertion.confidence == 1.0
        assert assertion.source_id == "WSC2023"
        assert assertion.source_artifact_id.startswith("WSC2023.RV.ANUKRAMANI.")


def test_the_source_label_is_never_rewritten_to_the_canonical_spelling(
    corpus: Path, registry: Path
) -> None:
    result = build_knowledge(corpus_dir=corpus, artifacts=_artifacts(), registry_root=registry)
    aliased = [item for item in result.assertions if item.object_key == "VG:CHANDAS:JAGATI"]
    assert aliased
    assert {item.source_label for item in aliased} == {"jagatiī"}
    assert {item.resolution_method for item in aliased} == {ResolutionStatus.KNOWN_ALIAS}


def test_an_unregistered_label_is_reported_and_produces_no_edge(
    corpus: Path, registry: Path
) -> None:
    devatas = yaml.safe_load((registry / "devatas.yaml").read_text(encoding="utf-8"))
    devatas["entities"] = [
        entry for entry in devatas["entities"] if entry["entity_key"] != "VG:DEVATA:VAYUH"
    ]
    (registry / "devatas.yaml").write_text(
        yaml.safe_dump(devatas, allow_unicode=True), encoding="utf-8"
    )
    result = build_knowledge(corpus_dir=corpus, artifacts=_artifacts(), registry_root=registry)
    assert not [item for item in result.assertions if item.source_label == "vāyuḥ"]
    unresolved = {item.normalized_label: item for item in result.unresolved}
    assert "vāyuḥ" in unresolved
    assert unresolved["vāyuḥ"].mantra_count == 2
    assert unresolved["vāyuḥ"].resolution_status is ResolutionStatus.NEEDS_REVIEW
    assert any(issue.check_id == "knowledge_unresolved_label" for issue in result.qa_issues)


def test_multiple_entities_of_one_predicate_are_supported(corpus: Path, registry: Path) -> None:
    result = build_knowledge(corpus_dir=corpus, artifacts=_artifacts(), registry_root=registry)
    stats = build_stats(result)
    coverage = {item.predicate: item for item in stats.coverage}
    # The fixture's RV 2.1 has no seer field, so its two mantras carry no rishi.
    assert coverage[MetadataPredicate.HAS_RISHI].mantras_without_claim == 2
    assert coverage[MetadataPredicate.HAS_DEVATA].mantras_resolved == sum(SHAPE.values())
    assert stats.metric_definition.startswith("Counts are mantra occurrences")


def test_the_layer_is_byte_identical_when_rebuilt(
    corpus: Path, registry: Path, tmp_path: Path
) -> None:
    digests = []
    for run in ("first", "second"):
        result = build_knowledge(corpus_dir=corpus, artifacts=_artifacts(), registry_root=registry)
        output = tmp_path / run
        manifest = write_knowledge_layer(
            result,
            build_stats(result),
            output_dir=output,
            corpus_dir=corpus,
            artifacts=_artifacts(),
            built_at=BUILT_AT,
            registry_root=registry,
            version="fixture-knowledge-1",
        )
        digests.append({item["path"]: item["sha256"] for item in manifest.generated_files})
        assert manifest.corpus_version == "fixture-corpus-1"
        assert manifest.source_commit_sha == "a" * 40
    assert digests[0] == digests[1]
    assert (tmp_path / "first" / "manifest.json").read_bytes() == (
        tmp_path / "second" / "manifest.json"
    ).read_bytes()


def test_the_corpus_index_reads_hymns_and_mantras(corpus: Path) -> None:
    index = load_corpus_index(corpus)
    assert index.total_mantras == sum(SHAPE.values())
    assert index.total_suktas == len(SHAPE)
    assert index.mantra_counts == SHAPE
