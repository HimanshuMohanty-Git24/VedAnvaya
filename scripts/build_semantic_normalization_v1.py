"""Build the offline semantic-object normalization diagnostic.

This command reads the sealed Luna v1/v2 and Sol artifacts.  It never invokes a model,
never edits those inputs, never opens human gold, and never unlocks a predicate.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.normalization import (
    ExplicitnessReview,
    MantraDisagreementDiagnosis,
    SemanticNormalizationManifest,
    StructuredSemanticAssertion,
    StructuredSemanticComparison,
)
from vedagraph.models.semantic import EvidencePacket, SemanticAssertionCandidate
from vedagraph.models.silver import SilverSemanticAnnotation
from vedagraph.semantic.normalization import (
    LegacyEntityLabel,
    compare_assertion_sets,
    migrate_luna_assertion,
    migrate_sol_assertion,
    select_refined_expert_audit_ids,
)
from vedagraph.semantic.object_ontology import (
    COMPARISON_POLICY_VERSION,
    EXPLICITNESS_POLICY_VERSION,
    SEMANTIC_OBJECT_SCHEMA_VERSION,
    DisagreementDecomposition,
    ExplicitnessPolicyAssessment,
    StructuredComparisonCategory,
)
from vedagraph.semantic.ontology import Explicitness, SemanticNodeType, SemanticPredicate
from vedagraph.semantic.silver import load_comparisons

ROOT = Path(__file__).resolve().parents[1]
V1_DIR = ROOT / "data/semantic/vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1"
V2_DIR = ROOT / "data/semantic/vedagraph-rigveda-semantic-luna-v2-120"
SOL_DIR = ROOT / "data/semantic/vedagraph-rigveda-semantic-silver-sol-v1"
OUTPUT_DIR = ROOT / "data/semantic/vedagraph-rigveda-semantic-normalization-v1"
REPORT_DIR = ROOT / "docs/reports"
BUILD_DIR = ROOT / "data/builds"

V1_RUN_ID = "vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1"
V2_RUN_ID = "vedagraph-rigveda-semantic-luna-v2-120"
SOL_RUN_ID = "vedagraph-rigveda-semantic-silver-sol-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _write_jsonl(path: Path, rows: Sequence[object]) -> None:
    text = "".join(
        json.dumps(
            row.model_dump(mode="json") if hasattr(row, "model_dump") else row,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
        for row in rows
    )
    path.write_text(text, encoding="utf-8")


def _load_luna_payload_entities(
    path: Path, selected_ids: frozenset[str] | None = None
) -> dict[str, dict[str, LegacyEntityLabel]]:
    by_passage: dict[str, dict[str, LegacyEntityLabel]] = {}
    for row in _load_jsonl(path):
        if selected_ids is not None and row["passage_key"] not in selected_ids:
            continue
        local: dict[str, LegacyEntityLabel] = {}
        for entity in row["payload"]["entities"]:
            local[entity["local_id"]] = LegacyEntityLabel(
                label=entity["label"], node_type=SemanticNodeType(entity["entity_type"])
            )
        by_passage[row["passage_key"]] = local
    return by_passage


def _load_luna(
    path: Path,
    payload_path: Path,
    run_id: str,
    *,
    selected_ids: frozenset[str] | None = None,
) -> list[StructuredSemanticAssertion]:
    entities = _load_luna_payload_entities(payload_path, selected_ids)
    counters: Counter[str] = Counter()
    rows: list[StructuredSemanticAssertion] = []
    for raw in _load_jsonl(path):
        candidate = SemanticAssertionCandidate.model_validate(raw)
        if selected_ids is not None and candidate.subject_key not in selected_ids:
            continue
        ordinal = counters[candidate.subject_key]
        counters[candidate.subject_key] += 1
        rows.append(
            migrate_luna_assertion(
                candidate,
                run_id=run_id,
                local_entities=entities.get(candidate.subject_key, {}),
                ordinal=ordinal,
            )
        )
    return rows


def _load_sol() -> tuple[list[SilverSemanticAnnotation], list[StructuredSemanticAssertion]]:
    annotations = [
        SilverSemanticAnnotation.model_validate(row)
        for row in _load_jsonl(SOL_DIR / "silver_annotations.jsonl")
    ]
    rows: list[StructuredSemanticAssertion] = []
    for annotation in annotations:
        for ordinal, assertion in enumerate(annotation.semantic_assertions):
            rows.append(migrate_sol_assertion(assertion, run_id=SOL_RUN_ID, ordinal=ordinal))
    return annotations, rows


def _add_no_claim_rows(
    comparisons: list[StructuredSemanticComparison],
    mantra_ids: list[str],
    luna: list[StructuredSemanticAssertion],
    sol: list[StructuredSemanticAssertion],
) -> list[StructuredSemanticComparison]:
    luna_ids = {item.subject_id for item in luna}
    sol_ids = {item.subject_id for item in sol}
    for mantra_id in sorted(set(mantra_ids) - luna_ids - sol_ids):
        comparisons.append(
            StructuredSemanticComparison(
                mantra_id=mantra_id,
                category=StructuredComparisonCategory.NO_CLAIM_AGREEMENT,
                reasoning="Both stored model artifacts emitted no assertion.",
            )
        )
    return sorted(
        comparisons,
        key=lambda item: (
            item.mantra_id,
            item.luna_assertion_id or "",
            item.sol_assertion_id or "",
            item.category.value,
        ),
    )


def _explicitness_review(
    original: list[SemanticAssertionCandidate],
    structured: list[StructuredSemanticAssertion],
) -> list[ExplicitnessReview]:
    direct_predicates = {
        SemanticPredicate.INVOKES,
        SemanticPredicate.PRAISES,
        SemanticPredicate.REQUESTS,
        SemanticPredicate.INVOLVES_RITUAL,
        SemanticPredicate.INVOLVES_OFFERING,
        SemanticPredicate.INVOLVES_SUBSTANCE,
        SemanticPredicate.REFERS_TO_NATURAL_PHENOMENON,
    }
    structured_by_id = {item.legacy_assertion_id: item for item in structured}
    review_sensitive = {
        SemanticPredicate.HAS_THEME,
        SemanticPredicate.ASSOCIATED_WITH,
        SemanticPredicate.CONTRASTS_WITH,
    }
    rows: list[ExplicitnessReview] = []
    for item in original:
        notes = " ".join(evidence.note.casefold() for evidence in item.evidence)
        structured_item = structured_by_id[item.candidate_assertion_id]
        head = structured_item.object.normalized_head or ""
        if item.explicitness is Explicitness.EXPLICIT:
            assessment = ExplicitnessPolicyAssessment.SHOULD_HAVE_BEEN_EXPLICIT
            reason = "The stored assertion is already EXPLICIT and is retained unchanged."
        elif item.predicate in review_sensitive:
            assessment = ExplicitnessPolicyAssessment.TOO_INTERPRETIVE_TO_EMIT
            reason = (
                "This predicate is review-sensitive; broad interpretation should not be "
                "emitted by future semantic v3 extraction."
            )
        elif item.predicate is SemanticPredicate.REFERS_TO_PLACE:
            assessment = ExplicitnessPolicyAssessment.SCHEMA_AMBIGUITY
            reason = (
                "The v2 schema did not separate PLACE from an opaque spatial or "
                "cosmological referent well enough to audit directness mechanically."
            )
        elif item.predicate is SemanticPredicate.EXPRESSES and (
            head.endswith("ing") or head in {"gladden", "joyeth"}
        ):
            assessment = ExplicitnessPolicyAssessment.TOO_INTERPRETIVE_TO_EMIT
            reason = (
                "The v2 object is action/verb-like rather than a directly evidenced state, "
                "quality, or concept; future v3 should omit it unless structure resolves this."
            )
        elif (
            item.predicate in direct_predicates
            or item.predicate
            in {
                SemanticPredicate.DESCRIBES,
                SemanticPredicate.DESCRIBES_ACTION,
                SemanticPredicate.EXPRESSES,
            }
        ) and any(marker in notes for marker in ("explicit", "named", "present", "verb")):
            assessment = ExplicitnessPolicyAssessment.SHOULD_HAVE_BEEN_EXPLICIT
            reason = (
                "The relation and target are described as directly present in the supplied "
                "translation; v2 incorrectly treated translation reliance as inference."
            )
        else:
            assessment = ExplicitnessPolicyAssessment.CORRECTLY_STRONG_INFERENCE
            reason = (
                "The stored rationale does not establish direct wording mechanically; one "
                "limited inferential step remains plausible and requires policy review."
            )
        rows.append(
            ExplicitnessReview(
                assertion_id=item.candidate_assertion_id,
                mantra_id=item.subject_key,
                predicate=item.predicate,
                legacy_explicitness=item.explicitness,
                policy_assessment=assessment,
                reason=reason,
            )
        )
    return rows


def _diagnose_disagreements(
    mantra_ids: list[str],
    comparisons: list[StructuredSemanticComparison],
    annotations: list[SilverSemanticAnnotation],
    representational_mantras: set[str],
) -> list[MantraDisagreementDiagnosis]:
    rows_by_id: dict[str, list[StructuredSemanticComparison]] = defaultdict(list)
    for row in comparisons:
        rows_by_id[row.mantra_id].append(row)
    annotations_by_id = {item.mantra_id: item for item in annotations}
    exact = {
        StructuredComparisonCategory.EXACT_CANONICAL_ENTITY,
        StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT,
        StructuredComparisonCategory.NO_CLAIM_AGREEMENT,
    }
    diagnoses: list[MantraDisagreementDiagnosis] = []
    for mantra_id in sorted(mantra_ids):
        categories = {item.category for item in rows_by_id[mantra_id]}
        if categories and categories <= exact and mantra_id not in representational_mantras:
            continue
        if annotations_by_id[mantra_id].ontology_gaps:
            primary = DisagreementDecomposition.ONTOLOGY_GAP
            rationale = "The sealed Sol annotation explicitly records an ontology gap."
        elif StructuredComparisonCategory.UNRESOLVED in categories:
            primary = DisagreementDecomposition.UNRESOLVED_LEGACY_LABEL
            rationale = "At least one legacy object is coordinated, sentence-like, or unmapped."
        elif categories & {
            StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE,
            StructuredComparisonCategory.CONFLICTING_OBJECT,
            StructuredComparisonCategory.EXPERT_REQUIRED,
        }:
            primary = DisagreementDecomposition.ACTUAL_SEMANTIC_CONFLICT
            rationale = (
                "Typed objects select conflicting heads or object families; this is a "
                "candidate real conflict, not an adjudicated truth claim."
            )
        elif StructuredComparisonCategory.PREDICATE_DIFFERENCE in categories:
            primary = DisagreementDecomposition.PREDICATE_MISMATCH
            rationale = "Structured object alignment exposes a predicate-boundary disagreement."
        elif StructuredComparisonCategory.GRANULARITY_DIFFERENCE in categories:
            primary = DisagreementDecomposition.OBJECT_GRANULARITY_MISMATCH
            rationale = "Typed heads overlap by strict component subset without equivalence."
        elif categories & {
            StructuredComparisonCategory.LEFT_ONLY,
            StructuredComparisonCategory.RIGHT_ONLY,
        }:
            primary = DisagreementDecomposition.INSUFFICIENT_EVIDENCE
            rationale = (
                "One model emitted no counterpart; the stored artifacts cannot decide whether "
                "this is omission or unsupported extraction."
            )
        elif mantra_id in representational_mantras:
            primary = DisagreementDecomposition.REPRESENTATION_MISMATCH
            rationale = (
                "Typed structure recovers object agreement that the historical raw-label "
                "comparison did not classify as exact."
            )
        else:
            primary = DisagreementDecomposition.INSUFFICIENT_EVIDENCE
            rationale = "The stored artifacts do not support a more specific diagnosis."
        diagnoses.append(
            MantraDisagreementDiagnosis(
                mantra_id=mantra_id,
                primary_category=primary,
                comparison_categories=sorted(categories, key=lambda item: item.value),
                rationale=rationale,
            )
        )
    return diagnoses


def _load_packets() -> dict[str, EvidencePacket]:
    packets: dict[str, EvidencePacket] = {}
    for path in sorted((V2_DIR / "batches").glob("batch_*/evidence.jsonl")):
        for row in _load_jsonl(path):
            packet = EvidencePacket.model_validate(row)
            packets[packet.passage_key] = packet
    return packets


def _question_for(
    mantra_id: str,
    rows: list[StructuredSemanticComparison],
    luna: list[StructuredSemanticAssertion],
    sol: list[StructuredSemanticAssertion],
) -> str:
    predicates = {item.predicate for item in (*luna, *sol) if item.subject_id == mantra_id}
    labels = " ".join(
        item.object.display_label.casefold()
        for item in (*luna, *sol)
        if item.subject_id == mantra_id
    )
    if "soma" in labels or "pavam" in labels:
        return (
            "Does the evidenced phrase denote Soma, Pavamana Soma, a Soma ritual event, "
            "an offering role, a substance, or more than one of these?"
        )
    if predicates & {
        SemanticPredicate.INVOLVES_RITUAL,
        SemanticPredicate.INVOLVES_OFFERING,
        SemanticPredicate.INVOLVES_SUBSTANCE,
    }:
        return (
            "Does the evidenced phrase denote the ritual action, the offered item in its "
            "offering role, the physical substance, or more than one independently?"
        )
    if SemanticPredicate.REFERS_TO_NATURAL_PHENOMENON in predicates:
        return (
            "Does the phrase explicitly refer to a natural phenomenon, a deity/personified "
            "entity, or both as distinct supported relations?"
        )
    if SemanticPredicate.REFERS_TO_PLACE in predicates:
        return (
            "Does the phrase denote an explicit place, only a spatial/cosmological "
            "description, or an opaque referent?"
        )
    if predicates & {
        SemanticPredicate.INVOKES,
        SemanticPredicate.PRAISES,
        SemanticPredicate.DESCRIBES,
    }:
        return "Does the verse explicitly invoke, praise, or merely describe the referent?"
    if SemanticPredicate.DESCRIBES_ACTION in predicates:
        return (
            "Which action and which actor/patient roles are directly supported by the cited "
            "Sanskrit or translation evidence?"
        )
    categories = {item.category for item in rows}
    if StructuredComparisonCategory.PREDICATE_DIFFERENCE in categories:
        return "Which locked predicate, if any, is directly supported by the cited evidence?"
    return (
        "What referent and relation are directly supported, and does the translation leave a "
        "philologically material ambiguity?"
    )


def _expert_queue(
    comparisons: list[StructuredSemanticComparison],
) -> list[str]:
    config = yaml.safe_load(
        (BUILD_DIR / "rigveda_semantic_expert_audit_v2.yaml").read_text(encoding="utf-8")
    )
    original = [item["passage_key"] for item in config["mantras"]]
    # Keep the queue in the expert-manageable 20-25 range and preserve its prior order.
    return select_refined_expert_audit_ids(original, comparisons, target_max=25)


def _write_expert_pack(
    selected: list[str],
    comparisons: list[StructuredSemanticComparison],
    annotations: list[SilverSemanticAnnotation],
    luna: list[StructuredSemanticAssertion],
    sol: list[StructuredSemanticAssertion],
) -> list[dict[str, Any]]:
    packets = _load_packets()
    annotations_by_id = {item.mantra_id: item for item in annotations}
    comparisons_by_id: dict[str, list[StructuredSemanticComparison]] = defaultdict(list)
    for item in comparisons:
        comparisons_by_id[item.mantra_id].append(item)
    pack: list[dict[str, Any]] = []
    for mantra_id in selected:
        packet = packets[mantra_id]
        pack.append(
            {
                "mantra_id": mantra_id,
                "citation": packet.citation,
                "rights_note": (
                    "Local packet-bounded review material; do not copy into public reports "
                    "without checking the pinned source rights."
                ),
                "sanskrit": packet.sanskrit,
                "translation": (
                    {
                        "translation_id": packet.translation.translation_id,
                        "translator": packet.translation.translator,
                        "text": packet.translation.text,
                    }
                    if packet.translation
                    else None
                ),
                "traditional_metadata": {
                    "rishi": list(zip(packet.rishi_keys, packet.rishi_labels, strict=True)),
                    "devata": list(zip(packet.devata_keys, packet.devata_labels, strict=True)),
                    "chandas": list(zip(packet.chandas_keys, packet.chandas_labels, strict=True)),
                },
                "lexical_deterministic_information": {
                    "tokens": [item.model_dump(mode="json") for item in packet.tokens],
                    "mentions": [item.model_dump(mode="json") for item in packet.mentions],
                },
                "luna_v2_structured_interpretation": [
                    item.model_dump(mode="json") for item in luna if item.subject_id == mantra_id
                ],
                "sol_structured_interpretation": [
                    item.model_dump(mode="json") for item in sol if item.subject_id == mantra_id
                ],
                "structured_comparison": [
                    item.model_dump(mode="json") for item in comparisons_by_id[mantra_id]
                ],
                "ontology_gaps": [
                    item.model_dump(mode="json")
                    for item in annotations_by_id[mantra_id].ontology_gaps
                ],
                "question": _question_for(mantra_id, comparisons_by_id[mantra_id], luna, sol),
            }
        )
    _write_jsonl(OUTPUT_DIR / "expert_review_package.jsonl", pack)
    return pack


def _migration_counts(
    rows: list[StructuredSemanticAssertion],
) -> tuple[Counter[str], Counter[str]]:
    statuses = Counter(item.object.normalization_status.value for item in rows)
    kinds = Counter(item.object.object_kind.value for item in rows)
    return statuses, kinds


def _representational_rows(
    comparisons: list[StructuredSemanticComparison],
) -> list[StructuredSemanticComparison]:
    legacy = load_comparisons(V2_DIR / "v2_vs_sol_comparisons.jsonl")
    legacy_pairs: dict[tuple[str, str], str] = {}
    for legacy_row in legacy:
        if legacy_row.luna_assertion_id and legacy_row.sol_assertion_id:
            legacy_pairs[(legacy_row.luna_assertion_id, legacy_row.sol_assertion_id)] = (
                legacy_row.category.value
            )
    structured_agreement = {
        StructuredComparisonCategory.EXACT_CANONICAL_ENTITY,
        StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT,
        StructuredComparisonCategory.COMPATIBLE_OBJECT,
        StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP,
        StructuredComparisonCategory.GRANULARITY_DIFFERENCE,
    }
    rows: list[StructuredSemanticComparison] = []
    for comparison in comparisons:
        pair = (
            (comparison.luna_assertion_id, comparison.sol_assertion_id)
            if comparison.luna_assertion_id and comparison.sol_assertion_id
            else None
        )
        if comparison.category in structured_agreement and (
            pair is None or legacy_pairs.get(pair) != "MATCH"
        ):
            rows.append(comparison)
    return rows


def _write_reports(
    *,
    v1: list[StructuredSemanticAssertion],
    v2: list[StructuredSemanticAssertion],
    sol: list[StructuredSemanticAssertion],
    annotations: list[SilverSemanticAnnotation],
    comparisons: list[StructuredSemanticComparison],
    diagnoses: list[MantraDisagreementDiagnosis],
    explicitness: list[ExplicitnessReview],
    selected: list[str],
    expert_pack: list[dict[str, Any]],
) -> list[Path]:
    category_counts = Counter(item.category.value for item in comparisons)
    legacy = load_comparisons(V2_DIR / "v2_vs_sol_comparisons.jsonl")
    legacy_counts = Counter(item.category.value for item in legacy)
    representational_rows = _representational_rows(comparisons)
    representational_mantras = {item.mantra_id for item in representational_rows}
    v1_status, v1_kinds = _migration_counts(v1)
    v2_status, v2_kinds = _migration_counts(v2)
    sol_status, sol_kinds = _migration_counts(sol)
    exact = (
        category_counts[StructuredComparisonCategory.EXACT_CANONICAL_ENTITY.value]
        + category_counts[StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT.value]
    )
    compatible = category_counts[StructuredComparisonCategory.COMPATIBLE_OBJECT.value]
    partial = category_counts[StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP.value]
    conflicts = (
        category_counts[StructuredComparisonCategory.CONFLICTING_OBJECT.value]
        + category_counts[StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE.value]
    )
    unresolved = sum(
        category_counts[item.value]
        for item in (
            StructuredComparisonCategory.UNRESOLVED,
            StructuredComparisonCategory.EXPERT_REQUIRED,
            StructuredComparisonCategory.LEFT_ONLY,
            StructuredComparisonCategory.RIGHT_ONLY,
        )
    )
    v1_migration_row = (
        f"| Luna v1 | {len(v1)} | {v1_status['CANONICAL_REF']} | "
        f"{v1_status['NORMALIZED_CANDIDATE']} | "
        f"{v1_status['UNRESOLVED_LEGACY_OBJECT']} |"
    )
    v2_migration_row = (
        f"| Luna v2 | {len(v2)} | {v2_status['CANONICAL_REF']} | "
        f"{v2_status['NORMALIZED_CANDIDATE']} | "
        f"{v2_status['UNRESOLVED_LEGACY_OBJECT']} |"
    )
    sol_migration_row = (
        f"| Sol silver | {len(sol)} | {sol_status['CANONICAL_REF']} | "
        f"{sol_status['NORMALIZED_CANDIDATE']} | "
        f"{sol_status['UNRESOLVED_LEGACY_OBJECT']} |"
    )
    comparison_text = f"""# Rigveda semantic normalized comparison v1

**NO HUMAN GOLD EXISTS. These are model-model diagnostics, not accuracy.** The sealed
legacy artifacts are unchanged and no model was executed.

## Historical metric retained

- Legacy exact string/signature matches: **{legacy_counts["MATCH"]}**
- Legacy partial matches: **{legacy_counts["PARTIAL_MATCH"]}**
- Historical exact-match precision: **{legacy_counts["MATCH"] / len(v2):.1%}**
- Historical exact-match recall: **{legacy_counts["MATCH"] / len(sol):.1%}**

## Structured comparison

- Exact structured matches: **{exact}**
  - exact canonical entity: **{category_counts["EXACT_CANONICAL_ENTITY"]}**
  - exact normalized object: **{category_counts["EXACT_NORMALIZED_OBJECT"]}**
- Compatible matches: **{compatible}**
- Partial object overlap: **{partial}**
- Object granularity differences: **{category_counts["GRANULARITY_DIFFERENCE"]}**
- Predicate conflicts: **{category_counts["PREDICATE_DIFFERENCE"]}**
- Object-type conflicts: **{category_counts["OBJECT_TYPE_DIFFERENCE"]}**
- Other conflicting objects: **{category_counts["CONFLICTING_OBJECT"]}**
- Real/conflicting object total (candidate, not adjudicated): **{conflicts}**
- Unresolved / one-sided / expert-required rows: **{unresolved}**
- No-claim agreements: **{category_counts["NO_CLAIM_AGREEMENT"]}**
- Newly recoverable representational alignments: **{len(representational_rows)}** across
  **{len(representational_mantras)}** mantras

Full category counts: `{dict(sorted(category_counts.items()))}`.

`label_equality_signal` is recorded for audit only. It never decides exactness. No fuzzy
model or embedding was used.

## Legacy migration coverage

| Source | Assertions | Canonical refs | Normalized candidates | Unresolved legacy objects |
|---|---:|---:|---:|---:|
{v1_migration_row}
{v2_migration_row}
{sol_migration_row}

V1 kinds: `{dict(sorted(v1_kinds.items()))}`.

V2 kinds: `{dict(sorted(v2_kinds.items()))}`.

Sol kinds: `{dict(sorted(sol_kinds.items()))}`.

Migration copies concise legacy heads but does not infer event arguments, split opaque
coordinated labels, or canonicalize semantic concepts. `NORMALIZED_CANDIDATE` is an
occurrence status, not acceptance.

## Safety

`unlocked_predicates = []`. Original output files are immutable inputs. Human gold was
not opened or modified.
"""
    comparison_path = REPORT_DIR / "RIGVEDA_SEMANTIC_NORMALIZED_COMPARISON.md"
    comparison_path.write_text(comparison_text, encoding="utf-8")

    diagnosis_counts = Counter(item.primary_category.value for item in diagnoses)
    agreed_mantras = len(annotations) - len(diagnoses)
    decomposition_lines = [
        "# Rigveda semantic disagreement decomposition",
        "",
        "**NO HUMAN GOLD EXISTS. Categories are diagnostic hypotheses, not adjudication.**",
        "",
        f"- Benchmark mantras: **{len(annotations)}**",
        f"- Mantras with no diagnosed mismatch: **{agreed_mantras}**",
        f"- Mantras requiring decomposition: **{len(diagnoses)}**",
        f"- Mantras with a contributing representation mismatch: "
        f"**{len(representational_mantras)}**",
        "",
        "## Primary mantra-level decomposition",
        "",
    ]
    for category in DisagreementDecomposition:
        decomposition_lines.append(f"- `{category.value}`: **{diagnosis_counts[category.value]}**")
    decomposition_lines.extend(
        [
            "",
            "`ACTUAL_SEMANTIC_CONFLICT` means typed structures conflict after conservative",
            "migration; only an expert can determine truth. One-sided cases are assigned to",
            "`INSUFFICIENT_EVIDENCE` because model-model output cannot distinguish omission",
            "from unsupported extraction. Sentence-like or coordinated legacy objects fail",
            "closed as `UNRESOLVED_LEGACY_LABEL`.",
            "",
            "## Cases",
            "",
        ]
    )
    for item in diagnoses:
        categories = ", ".join(value.value for value in item.comparison_categories)
        decomposition_lines.append(
            f"- `{item.mantra_id}` — `{item.primary_category.value}`; structured: "
            f"{categories}. {item.rationale}"
        )
    decomposition_path = REPORT_DIR / "RIGVEDA_SEMANTIC_DISAGREEMENT_DECOMPOSITION.md"
    decomposition_path.write_text("\n".join(decomposition_lines) + "\n", encoding="utf-8")

    explicit_counts = Counter(item.policy_assessment.value for item in explicitness)
    legacy_explicitness = Counter(item.legacy_explicitness.value for item in explicitness)
    predicate_assessment: dict[str, Counter[str]] = defaultdict(Counter)
    for explicitness_row in explicitness:
        predicate_assessment[explicitness_row.predicate.value][
            explicitness_row.policy_assessment.value
        ] += 1
    explicit_lines = [
        "# Rigveda semantic explicitness review",
        "",
        "**Policy analysis only. Sol was not used as ground truth and legacy assertions were",
        "not relabelled.**",
        "",
        f"V2 stored explicitness: `{dict(sorted(legacy_explicitness.items()))}`.",
        "",
        "## Diagnosis",
        "",
        f"- `SHOULD_HAVE_BEEN_EXPLICIT`: **{explicit_counts['SHOULD_HAVE_BEEN_EXPLICIT']}**",
        f"- `CORRECTLY_STRONG_INFERENCE`: **{explicit_counts['CORRECTLY_STRONG_INFERENCE']}**",
        f"- `TOO_INTERPRETIVE_TO_EMIT`: **{explicit_counts['TOO_INTERPRETIVE_TO_EMIT']}**",
        f"- `SCHEMA_AMBIGUITY`: **{explicit_counts['SCHEMA_AMBIGUITY']}**",
        "",
        "The dominant mechanical cause is the v2 instruction: a claim entailed mainly by a",
        "supplied translation was labelled `STRONG_INFERENCE`. Under the revised policy, a",
        "supplied translation is direct evidence. Inference depends on the reasoning step,",
        "not the language of the evidence.",
        "",
        "## Predicate breakdown",
        "",
        "| Predicate | Should explicit | Correctly strong | Too interpretive | Schema ambiguity |",
        "|---|---:|---:|---:|---:|",
    ]
    for predicate, counts in sorted(predicate_assessment.items()):
        explicit_lines.append(
            f"| `{predicate}` | {counts['SHOULD_HAVE_BEEN_EXPLICIT']} | "
            f"{counts['CORRECTLY_STRONG_INFERENCE']} | "
            f"{counts['TOO_INTERPRETIVE_TO_EMIT']} | {counts['SCHEMA_AMBIGUITY']} |"
        )
    explicit_lines.extend(
        [
            "",
            "## Revised future-v3 policy",
            "",
            "- `EXPLICIT`: relation and target are directly supportable from supplied Sanskrit",
            "  or translation evidence.",
            "- `STRONG_INFERENCE`: exactly one limited, named inferential step is required.",
            "- Broad thematic, symbolic, theological, or narrative interpretation: do not emit.",
            "- The target distribution should be dominated by `EXPLICIT`; no quota or artificial",
            "  relabelling is permitted.",
            "",
            "The row-level audit is stored locally as `explicitness_review.jsonl` and keeps every",
            "legacy value unchanged.",
        ]
    )
    explicit_path = REPORT_DIR / "RIGVEDA_SEMANTIC_EXPLICITNESS_REVIEW.md"
    explicit_path.write_text("\n".join(explicit_lines) + "\n", encoding="utf-8")

    pack_by_id = {item["mantra_id"]: item for item in expert_pack}
    queue_lines = [
        "# Rigveda semantic expert audit queue — normalized v1",
        "",
        "This refines the historical 25-case v2 queue after structured decomposition. It is",
        "a proposed expert-review package, not human gold. Pure string/order matches and",
        "known representational-only cases are excluded.",
        "",
        f"Selected cases: **{len(selected)}**.",
        "",
    ]
    comparisons_by_id: dict[str, list[StructuredSemanticComparison]] = defaultdict(list)
    for row in comparisons:
        comparisons_by_id[row.mantra_id].append(row)
    for index, mantra_id in enumerate(selected, start=1):
        categories = ", ".join(
            sorted({item.category.value for item in comparisons_by_id[mantra_id]})
        )
        queue_lines.append(
            f"{index}. `{mantra_id}` — {categories}. **Question:** "
            f"{pack_by_id[mantra_id]['question']}"
        )
    queue_lines.extend(
        [
            "",
            "The local `expert_review_package.jsonl` supplies citation, rights-bounded Sanskrit",
            "and translation, traditional metadata, deterministic lexical tokens/mentions, both",
            "structured interpretations, and the domain question. It never asks which model is",
            "correct. No expert review was sought or fabricated.",
        ]
    )
    queue_path = REPORT_DIR / "RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE_NORMALIZED.md"
    queue_path.write_text("\n".join(queue_lines) + "\n", encoding="utf-8")
    return [comparison_path, decomposition_path, explicit_path, queue_path]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    input_paths = {
        "luna_v1_manifest": V1_DIR / "semantic_run_manifest.json",
        "luna_v1_candidates": V1_DIR / "semantic_candidates.jsonl",
        "luna_v1_payloads": V1_DIR / "codex_direct_payloads.jsonl",
        "luna_v2_manifest": V2_DIR / "semantic_run_manifest.json",
        "luna_v2_candidates": V2_DIR / "semantic_candidates.jsonl",
        "luna_v2_payloads": V2_DIR / "codex_direct_payloads.jsonl",
        "sol_manifest": SOL_DIR / "semantic_silver_manifest.json",
        "sol_annotations": SOL_DIR / "silver_annotations.jsonl",
        "legacy_v2_sol_comparisons": V2_DIR / "v2_vs_sol_comparisons.jsonl",
    }
    input_hashes_before = {name: _sha256(path) for name, path in input_paths.items()}

    annotations, sol = _load_sol()
    mantra_ids = [item.mantra_id for item in annotations]
    benchmark_ids = frozenset(mantra_ids)
    v1 = _load_luna(
        V1_DIR / "semantic_candidates.jsonl",
        V1_DIR / "codex_direct_payloads.jsonl",
        V1_RUN_ID,
        selected_ids=benchmark_ids,
    )
    v2_original = [
        SemanticAssertionCandidate.model_validate(row)
        for row in _load_jsonl(V2_DIR / "semantic_candidates.jsonl")
    ]
    v2 = _load_luna(
        V2_DIR / "semantic_candidates.jsonl",
        V2_DIR / "codex_direct_payloads.jsonl",
        V2_RUN_ID,
    )
    comparisons = _add_no_claim_rows(compare_assertion_sets(v2, sol), mantra_ids, v2, sol)
    explicitness = _explicitness_review(v2_original, v2)
    representational_mantras = {item.mantra_id for item in _representational_rows(comparisons)}
    diagnoses = _diagnose_disagreements(
        mantra_ids, comparisons, annotations, representational_mantras
    )

    output_paths = {
        "normalized_luna_v1_assertions.jsonl": OUTPUT_DIR / "normalized_luna_v1_assertions.jsonl",
        "normalized_luna_v2_assertions.jsonl": OUTPUT_DIR / "normalized_luna_v2_assertions.jsonl",
        "normalized_sol_assertions.jsonl": OUTPUT_DIR / "normalized_sol_assertions.jsonl",
        "structured_v2_vs_sol_comparisons.jsonl": OUTPUT_DIR
        / "structured_v2_vs_sol_comparisons.jsonl",
        "disagreement_diagnoses.jsonl": OUTPUT_DIR / "disagreement_diagnoses.jsonl",
        "explicitness_review.jsonl": OUTPUT_DIR / "explicitness_review.jsonl",
    }
    _write_jsonl(output_paths["normalized_luna_v1_assertions.jsonl"], v1)
    _write_jsonl(output_paths["normalized_luna_v2_assertions.jsonl"], v2)
    _write_jsonl(output_paths["normalized_sol_assertions.jsonl"], sol)
    _write_jsonl(output_paths["structured_v2_vs_sol_comparisons.jsonl"], comparisons)
    _write_jsonl(output_paths["disagreement_diagnoses.jsonl"], diagnoses)
    _write_jsonl(output_paths["explicitness_review.jsonl"], explicitness)

    selected = _expert_queue(comparisons)
    expert_pack = _write_expert_pack(selected, comparisons, annotations, v2, sol)
    output_paths["expert_review_package.jsonl"] = OUTPUT_DIR / "expert_review_package.jsonl"
    reports = _write_reports(
        v1=v1,
        v2=v2,
        sol=sol,
        annotations=annotations,
        comparisons=comparisons,
        diagnoses=diagnoses,
        explicitness=explicitness,
        selected=selected,
        expert_pack=expert_pack,
    )
    output_paths.update({path.name: path for path in reports})

    audit_config_path = BUILD_DIR / "rigveda_semantic_expert_audit_normalized_v1.yaml"
    audit_config = {
        "config_version": "rigveda-semantic-expert-audit-normalized-v1",
        "source_queue": "rigveda-semantic-expert-audit-v2",
        "normalization_run_id": "vedagraph-rigveda-semantic-normalization-v1",
        "human_gold_status": "UNANNOTATED",
        "proposed_only": True,
        "cases": [
            {"passage_key": item["mantra_id"], "question": item["question"]} for item in expert_pack
        ],
    }
    audit_config_path.write_text(
        yaml.safe_dump(audit_config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    output_paths[audit_config_path.name] = audit_config_path

    input_hashes_after = {name: _sha256(path) for name, path in input_paths.items()}
    if input_hashes_before != input_hashes_after:
        raise RuntimeError("an immutable legacy input changed during normalization")

    v2_manifest = json.loads((V2_DIR / "semantic_run_manifest.json").read_text(encoding="utf-8"))
    manifest = SemanticNormalizationManifest(
        corpus_manifest_sha256=v2_manifest["corpus_manifest_sha256"],
        traditional_knowledge_manifest_sha256=v2_manifest["traditional_knowledge_manifest_sha256"],
        lexical_knowledge_manifest_sha256=v2_manifest["lexical_knowledge_manifest_sha256"],
        luna_v1_manifest_sha256=input_hashes_before["luna_v1_manifest"],
        luna_v2_manifest_sha256=input_hashes_before["luna_v2_manifest"],
        sol_silver_manifest_sha256=input_hashes_before["sol_manifest"],
        semantic_ontology_version=v2_manifest["ontology_version"],
        semantic_object_schema_version=SEMANTIC_OBJECT_SCHEMA_VERSION,
        comparison_policy_version=COMPARISON_POLICY_VERSION,
        explicitness_policy_version=EXPLICITNESS_POLICY_VERSION,
        input_hashes=input_hashes_before,
        output_hashes={name: _sha256(path) for name, path in sorted(output_paths.items())},
        record_counts={
            "luna_v1_assertions": len(v1),
            "luna_v2_assertions": len(v2),
            "sol_assertions": len(sol),
            "structured_comparison_rows": len(comparisons),
            "disagreement_mantras": len(diagnoses),
            "explicitness_review_rows": len(explicitness),
            "expert_queue_cases": len(selected),
        },
        created_at=datetime(2026, 9, 5, tzinfo=UTC),
    )
    manifest_json = (
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    (OUTPUT_DIR / "normalization_manifest.json").write_text(manifest_json, encoding="utf-8")
    (BUILD_DIR / "rigveda_semantic_normalization_v1.yaml").write_text(
        yaml.safe_dump(manifest.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
