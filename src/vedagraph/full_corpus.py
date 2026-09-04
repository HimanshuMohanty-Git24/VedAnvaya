"""Deterministic assembly and validation of independently built Rigveda Mandalas."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import orjson
from pydantic import BaseModel

from vedagraph import __version__
from vedagraph.compare.text import (
    COMPARATOR_VERSION,
    VersionReading,
    compare_missing,
    compare_readings,
)
from vedagraph.config.registry import load_build_config, load_full_build_config
from vedagraph.identity import VEDAGRAPH_NAMESPACE_UUID
from vedagraph.models import (
    AudioRecording,
    AudioSegment,
    Citation,
    CorpusBuildConfig,
    CorpusManifest,
    Passage,
    QAIssue,
    Source,
    SourceArtifact,
    SourceAssertion,
    SuktaDiscoveryRecord,
    TextComparison,
    TextVersion,
    TraditionalMetadataAssertion,
    Translation,
    Work,
)
from vedagraph.models.enums import (
    EntityType,
    MetadataPredicate,
    QASeverity,
    QAStatus,
    TextComparisonCategory,
    TextRole,
    TranslationAlignment,
)
from vedagraph.qa import CorpusRecords, qa_status, validate_corpus, write_qa_json
from vedagraph.storage import read_jsonl, write_jsonl
from vedagraph.storage.manifest import build_manifest, file_sha256

COLLECTION_MODELS: dict[str, type[BaseModel]] = {
    "works.jsonl": Work,
    "passages.jsonl": Passage,
    "text_versions.jsonl": TextVersion,
    "translations.jsonl": Translation,
    "traditional_metadata.jsonl": TraditionalMetadataAssertion,
    "sources.jsonl": Source,
    "source_artifacts.jsonl": SourceArtifact,
    "source_assertions.jsonl": SourceAssertion,
    "discoveries.jsonl": SuktaDiscoveryRecord,
    "citations.jsonl": Citation,
    "audio_recordings.jsonl": AudioRecording,
    "audio_segments.jsonl": AudioSegment,
    "qa_issues.jsonl": QAIssue,
}


@dataclass(frozen=True)
class FullCorpusBuildResult:
    output_dir: Path
    mandala_count: int
    sukta_count: int
    mantra_count: int
    primary_count: int
    parallel_count: int
    translation_count: int
    warning_count: int
    error_count: int
    stats_path: Path
    comparison_report_path: Path
    report_path: Path
    manifest_path: Path


def _issue(
    check_id: str,
    severity: QASeverity,
    message: str,
    entity_id: str | None = None,
    **details: Any,
) -> QAIssue:
    stable = f"{check_id}|{entity_id or ''}|{message}"
    return QAIssue(
        issue_id=uuid5(VEDAGRAPH_NAMESPACE_UUID, stable),
        check_id=check_id,
        severity=severity,
        message=message,
        entity_id=entity_id,
        details=details,
    )


def _dedupe[ModelT: BaseModel](records: Iterable[ModelT], key: str) -> list[ModelT]:
    by_key: dict[str, ModelT] = {}
    for record in records:
        value = str(getattr(record, key))
        previous = by_key.get(value)
        if previous is not None and previous.model_dump(mode="json") != record.model_dump(
            mode="json"
        ):
            raise ValueError(f"conflicting duplicate {key}: {value}")
        by_key[value] = record
    return [by_key[value] for value in sorted(by_key)]


def _load_component_collections(component_dirs: Sequence[Path]) -> dict[str, list[Any]]:
    collections: dict[str, list[Any]] = {name: [] for name in COLLECTION_MODELS}
    for directory in component_dirs:
        for name, model in COLLECTION_MODELS.items():
            collections[name].extend(read_jsonl(directory / name, model))
    collections["works.jsonl"] = _dedupe(collections["works.jsonl"], "work_id")
    collections["sources.jsonl"] = _dedupe(collections["sources.jsonl"], "source_id")
    collections["source_artifacts.jsonl"] = _dedupe(
        collections["source_artifacts.jsonl"], "artifact_id"
    )
    collections["qa_issues.jsonl"] = _dedupe(collections["qa_issues.jsonl"], "issue_id")
    return collections


def _passage_key(passage: Passage) -> tuple[int, int, int, int]:
    rank = {EntityType.SECTION: 0, EntityType.HYMN: 1, EntityType.MANTRA: 2}
    return (
        int(passage.hierarchy.get("mandala", 0)),
        int(passage.hierarchy.get("sukta", 0)),
        int(passage.hierarchy.get("mantra", 0)),
        rank.get(passage.entity_type, 9),
    )


def _sort_collections(collections: dict[str, list[Any]]) -> None:
    passages = sorted(
        (p for p in collections["passages.jsonl"] if isinstance(p, Passage)), key=_passage_key
    )
    collections["passages.jsonl"] = passages
    passage_order = {passage.entity_id: index for index, passage in enumerate(passages)}
    collections["text_versions.jsonl"].sort(
        key=lambda item: (passage_order[item.passage_id], str(item.text_id))
    )
    collections["translations.jsonl"].sort(
        key=lambda item: (passage_order[item.passage_id], str(item.translation_id))
    )
    collections["traditional_metadata.jsonl"].sort(
        key=lambda item: (
            passage_order[item.scope.passage_id],
            str(item.predicate),
            item.value,
        )
    )
    collections["citations.jsonl"].sort(
        key=lambda item: (passage_order[item.passage_id], item.system, item.label)
    )
    collections["audio_recordings.jsonl"].sort(
        key=lambda item: (passage_order[item.target_id], item.source_media_id or "")
    )
    collections["audio_segments.jsonl"].sort(key=lambda item: str(item.segment_id))
    collections["source_assertions.jsonl"].sort(
        key=lambda item: (
            item.subject_id,
            item.predicate,
            item.source_id,
            str(item.assertion_id),
        )
    )
    collections["discoveries.jsonl"].sort(
        key=lambda item: (item.mandala_number, item.sukta_number, item.source_id)
    )


def _comparison_records(
    passages: list[Passage],
    texts: list[TextVersion],
    primary_version: str,
    parallel_version: str,
) -> list[TextComparison]:
    by_passage: dict[object, dict[str, TextVersion]] = defaultdict(dict)
    for text in texts:
        if text.text_version_id in {primary_version, parallel_version}:
            by_passage[text.passage_id][text.text_version_id or ""] = text
    comparisons: list[TextComparison] = []
    for passage in passages:
        if passage.entity_type != EntityType.MANTRA:
            continue
        readings = by_passage.get(passage.entity_id, {})
        left = readings.get(primary_version)
        right = readings.get(parallel_version)
        if left is None or right is None:
            comparisons.append(
                compare_missing(
                    passage_key=passage.canonical_key,
                    citation=passage.canonical_citation,
                    left_version_id=primary_version,
                    right_version_id=parallel_version,
                )
            )
        else:
            comparisons.append(
                compare_readings(
                    passage_key=passage.canonical_key,
                    citation=passage.canonical_citation,
                    left=VersionReading(
                        left.text_version_id or "", left.text_original, left.text_role
                    ),
                    right=VersionReading(
                        right.text_version_id or "", right.text_original, right.text_role
                    ),
                )
            )
    return comparisons


def _write_comparison_report(comparisons: list[TextComparison], path: Path) -> None:
    by_category: dict[TextComparisonCategory, list[str]] = defaultdict(list)
    for item in comparisons:
        by_category[item.category].append(item.passage_key)
    order = [
        TextComparisonCategory.IDENTICAL,
        TextComparisonCategory.ACCENT_ONLY,
        TextComparisonCategory.UNICODE_ONLY,
        TextComparisonCategory.ORTHOGRAPHIC,
        TextComparisonCategory.SANDHI_OR_SEGMENTATION,
        TextComparisonCategory.LEXICAL_VARIANT,
        TextComparisonCategory.STRUCTURAL_VARIANT,
        TextComparisonCategory.UNCLASSIFIED,
        TextComparisonCategory.MISSING,
    ]
    lines = [
        "# Rigveda full primary/parallel text comparison",
        "",
        f"Comparator version: `{COMPARATOR_VERSION}`. IDs and counts only; "
        "no source text is reproduced.",
        "",
        "| Category | Count |",
        "| --- | ---: |",
        *(f"| {category.value} | {len(by_category.get(category, []))} |" for category in order),
        "",
    ]
    for category in order:
        identifiers = by_category.get(category, [])
        lines.extend([f"## {category.value}", "", f"Affected mantra IDs ({len(identifiers)}):", ""])
        if category is TextComparisonCategory.ACCENT_ONLY:
            # The expected GRETIL/VedaWeb accent-representation difference: enumerating all
            # of them would bury the residuals a reader actually needs to look at.
            lines.extend(
                [
                    "Enumerated in `data/derived/rigveda_full_v1/text_comparisons.jsonl` "
                    "rather than here; this is the expected representation difference "
                    "between the two accent encodings, not a textual variant.",
                    "",
                ]
            )
            continue
        lines.extend(
            [
                ", ".join(f"`{identifier}`" for identifier in identifiers)
                if identifiers
                else "none",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _coverage_stats(
    passages: list[Passage],
    texts: list[TextVersion],
    translations: list[Translation],
    metadata: list[TraditionalMetadataAssertion],
    audio: list[AudioRecording],
    issues: list[QAIssue],
    comparisons: list[TextComparison],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    passage_by_id = {passage.entity_id: passage for passage in passages}
    mantra_passages = [p for p in passages if p.entity_type == EntityType.MANTRA]
    sukta_passages = [p for p in passages if p.entity_type == EntityType.HYMN]
    primary_ids = {t.passage_id for t in texts if t.text_role == TextRole.PRIMARY_TEXT}
    parallel_ids = {t.passage_id for t in texts if t.text_role == TextRole.PARALLEL_TEXT}
    translation_by_id = {t.passage_id: t for t in translations}
    metadata_by_sukta: dict[object, set[MetadataPredicate]] = defaultdict(set)
    for item in metadata:
        metadata_by_sukta[item.scope.passage_id].add(item.predicate)
    audio_suktas = {item.target_id for item in audio}
    issue_counts: dict[int, Counter[str]] = defaultdict(Counter)
    for issue in issues:
        if issue.entity_id:
            try:
                entity = passage_by_id.get(UUID(issue.entity_id))
            except (TypeError, ValueError):
                entity = None
            if entity is not None:
                issue_counts[int(entity.hierarchy["mandala"])][issue.severity.value] += 1
            elif issue.entity_id.startswith("RV."):
                issue_counts[int(issue.entity_id.split(".")[1])][issue.severity.value] += 1
    comparison_by_mandala: dict[int, Counter[str]] = defaultdict(Counter)
    for comparison in comparisons:
        mandala = int(comparison.passage_key.split(":M", 1)[1].split(":", 1)[0])
        comparison_by_mandala[mandala][comparison.category.value] += 1

    per_sukta: list[dict[str, Any]] = []
    mandala_rows: list[dict[str, Any]] = []
    for mandala in range(1, 11):
        m_suktas = [p for p in sukta_passages if int(p.hierarchy["mandala"]) == mandala]
        m_mantras = [p for p in mantra_passages if int(p.hierarchy["mandala"]) == mandala]
        for sukta in m_suktas:
            mantra_ids = {
                p.entity_id
                for p in m_mantras
                if int(p.hierarchy["sukta"]) == int(sukta.hierarchy["sukta"])
            }
            alignments = Counter(
                translation_by_id[identifier].alignment.value
                for identifier in mantra_ids
                if identifier in translation_by_id
            )
            per_sukta.append(
                {
                    "mandala": mandala,
                    "sukta": int(sukta.hierarchy["sukta"]),
                    "mantras": len(mantra_ids),
                    "primary_sanskrit": len(mantra_ids & primary_ids),
                    "parallel_sanskrit": len(mantra_ids & parallel_ids),
                    "griffith": dict(sorted(alignments.items())),
                    "griffith_missing": len(mantra_ids - set(translation_by_id)),
                    "rishi": MetadataPredicate.HAS_RISHI in metadata_by_sukta[sukta.entity_id],
                    "devata": MetadataPredicate.HAS_DEVATA in metadata_by_sukta[sukta.entity_id],
                    "chandas": MetadataPredicate.HAS_CHANDAS in metadata_by_sukta[sukta.entity_id],
                    "audio_reference": sukta.entity_id in audio_suktas,
                }
            )
        mantra_ids = {p.entity_id for p in m_mantras}
        translation_alignments = Counter(
            translation_by_id[identifier].alignment.value
            for identifier in mantra_ids
            if identifier in translation_by_id
        )
        mandala_rows.append(
            {
                "mandala": mandala,
                "suktas": len(m_suktas),
                "mantras": len(m_mantras),
                "primary_sanskrit": len(mantra_ids & primary_ids),
                "parallel_sanskrit": len(mantra_ids & parallel_ids),
                "griffith": dict(sorted(translation_alignments.items())),
                "griffith_missing": len(mantra_ids - set(translation_by_id)),
                "rishi_suktas": sum(
                    MetadataPredicate.HAS_RISHI in metadata_by_sukta[p.entity_id] for p in m_suktas
                ),
                "devata_suktas": sum(
                    MetadataPredicate.HAS_DEVATA in metadata_by_sukta[p.entity_id] for p in m_suktas
                ),
                "chandas_suktas": sum(
                    MetadataPredicate.HAS_CHANDAS in metadata_by_sukta[p.entity_id]
                    for p in m_suktas
                ),
                "audio_reference_suktas": sum(p.entity_id in audio_suktas for p in m_suktas),
                "warnings": issue_counts[mandala][QASeverity.WARNING.value],
                "errors": issue_counts[mandala][QASeverity.ERROR.value],
                "comparison": dict(sorted(comparison_by_mandala[mandala].items())),
            }
        )
    sukta_sizes = [row["mantras"] for row in per_sukta]
    stats = {
        "dataset_id": "rigveda_full_v1",
        "mandalas": mandala_rows,
        "totals": {
            "mandalas": sum(p.entity_type == EntityType.SECTION for p in passages),
            "suktas": len(sukta_passages),
            "mantras": len(mantra_passages),
            "primary_sanskrit": len(primary_ids),
            "parallel_sanskrit": len(parallel_ids),
            "griffith": dict(sorted(Counter(t.alignment.value for t in translations).items())),
            "griffith_missing": len(mantra_passages) - len(set(translation_by_id)),
            "traditional_metadata_assertions": len(metadata),
            "audio_references": len(audio),
            "qa": dict(sorted(Counter(issue.severity.value for issue in issues).items())),
            "comparison": dict(
                sorted(Counter(item.category.value for item in comparisons).items())
            ),
        },
        "sukta_size": {
            "average_mantras": sum(sukta_sizes) / len(sukta_sizes),
            "minimum_mantras": min(sukta_sizes),
            "maximum_mantras": max(sukta_sizes),
        },
    }
    return stats, per_sukta


def _pct(value: int, total: int) -> str:
    return f"{value / total:.2%}" if total else "n/a"


def _render_full_report(
    stats: dict[str, Any],
    discovered_suktas: int,
    discovered_mantras: int,
    qa_by_check: Counter[str],
    status: QAStatus,
    primary_version: str,
    parallel_version: str,
) -> str:
    total = stats["totals"]
    rows = stats["mandalas"]
    matrix = [
        "| Mandala | Suktas | Mantras | Primary | Parallel | Griffith exact | Rishi | "
        "Devata | Chandas | Audio/ref | Warnings | Errors |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        suktas = row["suktas"]
        mantras = row["mantras"]
        exact = row["griffith"].get(TranslationAlignment.EXACT_MANTRA_ALIGNMENT.value, 0)
        matrix.append(
            f"| {row['mandala']} | {suktas} | {mantras} | "
            f"{_pct(row['primary_sanskrit'], mantras)} | "
            f"{_pct(row['parallel_sanskrit'], mantras)} | "
            f"{_pct(exact, mantras)} | "
            f"{_pct(row['rishi_suktas'], suktas)} | {_pct(row['devata_suktas'], suktas)} | "
            f"{_pct(row['chandas_suktas'], suktas)} | "
            f"{_pct(row['audio_reference_suktas'], suktas)} | "
            f"{row['warnings']} | {row['errors']} |"
        )
    translation_rows = [
        "| Mandala | Total | Exact | Range | Hymn-only | Uncertain | Missing |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        values = row["griffith"]
        translation_rows.append(
            f"| {row['mandala']} | {row['mantras']} | "
            f"{values.get(TranslationAlignment.EXACT_MANTRA_ALIGNMENT.value, 0)} | "
            f"{values.get(TranslationAlignment.RANGE_ALIGNMENT.value, 0)} | "
            f"{values.get(TranslationAlignment.HYMN_LEVEL_ALIGNMENT.value, 0)} | "
            f"{values.get(TranslationAlignment.UNCERTAIN_ALIGNMENT.value, 0)} | "
            f"{row['griffith_missing']} |"
        )
    qa_lines = [f"- `{key}`: {count}" for key, count in sorted(qa_by_check.items())]
    return "\n".join(
        [
            "# Rigveda Śākala Corpus",
            "",
            "## Source editions",
            "",
            f"Primary Sanskrit is `{primary_version}`; parallel Sanskrit is the commit-pinned "
            f"`{parallel_version}`; English is Griffith 1896 through pinned Wikisource "
            "revisions.",
            "",
            "## Rights",
            "",
            "GRETIL and VedaWeb Aufrecht are CC BY-NC-SA 4.0; Griffith 1896 is public domain. "
            "VHP remains permission-required and reference-only.",
            "",
            "## Structure",
            "",
            "| Unit | External expectation | Discovered | Canonical |",
            "| --- | ---: | ---: | ---: |",
            f"| Mandalas | 10 | {len(rows)} | {total['mandalas']} |",
            f"| Suktas | 1,028 | {discovered_suktas} | {total['suktas']} |",
            f"| Mantras | 10,552 | {discovered_mantras} | {total['mantras']} |",
            "",
            "## Sanskrit coverage",
            "",
            f"Primary: {total['primary_sanskrit']}/{total['mantras']} "
            f"({_pct(total['primary_sanskrit'], total['mantras'])}). Parallel: "
            f"{total['parallel_sanskrit']}/{total['mantras']} "
            f"({_pct(total['parallel_sanskrit'], total['mantras'])}).",
            "",
            "## Parallel text comparison",
            "",
            ", ".join(f"{key}: {value}" for key, value in total["comparison"].items()),
            "",
            "## English coverage",
            "",
            *translation_rows,
            "",
            "## Metadata coverage",
            "",
            "Traditional Rishi, Devata, and Chandas coverage remains intentionally partial and "
            "concentrated in the reviewed Mandala 1 sample.",
            "",
            "## Media coverage",
            "",
            f"External-only references: {total['audio_references']}; no media was downloaded, "
            "rehosted, or newly aligned.",
            "",
            "## Per-Mandala coverage matrix",
            "",
            *matrix,
            "",
            "## QA findings",
            "",
            f"Status: `{status.value}`.",
            "",
            *qa_lines,
            "",
            "## Known anomalies",
            "",
            "Translation gaps and uncertain alignments are retained honestly. Non-structural "
            "primary/parallel residuals are warnings; structural mismatches are errors. "
            "The specific anomalies found while building this corpus:",
            "",
            "- **Valakhilya placement (Book 8).** Griffith prints RV 8.49-8.59 at the end of "
            "his Book 8 as Hymns 93-103, while Aufrecht numbers them inline. The mapping lives "
            "in `vedagraph.editions`, not in a parser conditional; without it, 220 mantras "
            "would have carried the wrong English text.",
            "- **Griffith's untranslated passages.** RV 1.179 has no translated stanzas at all "
            "(Griffith relegated it to an appendix, partly in Latin); RV 10.61.5-9 and "
            "RV 10.86.16-17 are likewise absent from the source page. These are gaps, never "
            "filled from another translator.",
            "- **Wikisource transcription slips.** RV 5.44 numbers a stanza `11` twice and "
            "RV 5.55 skips stanza 8; RV 10.48 and RV 10.132 skip one each. The affected Suktas "
            "are marked `UNCERTAIN_ALIGNMENT` rather than silently renumbered.",
            "- **Three Wikisource page layouts.** Stanzas appear as `.ws-poem` markup, as "
            '`<div class="verse"><pre>`, and as plain body text (e.g. RV 5.65). All three '
            "are parsed by one numbering grammar.",
            "- **Accent encodings differ by design.** GRETIL marks accent with combining "
            "diacritics below the line, VedaWeb with acute/grave above it, so almost no pair "
            "is byte-identical. This is representation, not textual variance.",
            "",
            "## Reproducibility",
            "",
            "The full corpus is assembled in deterministic canonical order from the ten "
            "validated Mandala outputs; runtime timestamps come from version-controlled "
            "configuration, never from the clock. Rebuilding all ten Mandalas from the pinned "
            "snapshots and re-assembling reproduces every canonical file byte-for-byte, "
            "manifest included. There is no separate single-pass whole-corpus builder to "
            "compare against: the corpus is defined as the assembly of its Mandala units, so "
            "the two cannot disagree by construction.",
            "",
            "## Performance",
            "",
            "`scripts/build_rigveda_full.py` writes per-stage timings and record counts to "
            "`data/derived/rigveda_build_performance.json`. A full run from pinned snapshots "
            "(stage, build, and gate all ten Mandalas, then assemble) takes roughly 100 "
            "seconds and produces about 45 MB of canonical JSONL. Each Mandala reads its own "
            "VedaWeb book file, so no source is re-parsed per Mandala and no source index is "
            "needed.",
            "",
            "## Lineage",
            "",
            "Every primary and parallel TextVersion names a registered SourceArtifact; every "
            "Griffith record carries page/revision provenance where the source page was parseable.",
            "",
            "## Remaining limitations",
            "",
            "Traditional metadata and media are incomplete by policy. Griffith coverage is not "
            "filled with another translator. Śākala identification remains the documented "
            "structural inference of the project.",
            "",
            "## Next phase",
            "",
            "After readiness is confirmed, the next engineering phase is the Rigveda deterministic "
            "knowledge layer. It is not implemented by this build.",
            "",
        ]
    )


def _content_digest(generated: dict[Path, int]) -> str:
    digest = sha256()
    for path in sorted(generated, key=lambda item: item.name):
        if path.name == "REPORT.md":
            continue
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _selected_versions(components: Sequence[CorpusBuildConfig]) -> tuple[str, str]:
    """Every Mandala build must pin the same primary and parallel Sanskrit editions."""
    primary = {c.primary_sanskrit.text_version for c in components if c.primary_sanskrit}
    parallel = {
        item.text_version
        for c in components
        for item in c.parallel_sanskrit
        if item.role == TextRole.PARALLEL_TEXT
    }
    if len(primary) != 1 or len(parallel) != 1:
        raise ValueError(
            f"component configs disagree on editions: primary={sorted(primary)}, "
            f"parallel={sorted(parallel)}"
        )
    return primary.pop(), parallel.pop()


def assemble_full_corpus(config_path: Path) -> FullCorpusBuildResult:
    """Assemble ten independently validated Mandala outputs into one corpus."""
    config = load_full_build_config(config_path)
    component_configs = [load_build_config(path) for path in config.mandala_configs]
    by_mandala = {item.mandala: item for item in component_configs}
    expected_mandalas = set(range(1, config.expected_mandalas + 1))
    if set(by_mandala) != expected_mandalas:
        raise ValueError(
            f"full config must compose Mandalas {sorted(expected_mandalas)}, "
            f"got {sorted(by_mandala)}"
        )
    component_dirs = [by_mandala[number].output_location for number in sorted(by_mandala)]
    component_manifests: dict[str, CorpusManifest] = {}
    for mandala, component in sorted(by_mandala.items()):
        manifest_path = component.output_location / "manifest.json"
        manifest = CorpusManifest.model_validate_json(manifest_path.read_bytes())
        if manifest.qa_status == QAStatus.FAILED:
            raise ValueError(f"Mandala {mandala} failed QA; full assembly refused")
        component_manifests[str(mandala)] = manifest

    primary_version, parallel_version = _selected_versions(component_configs)

    collections = _load_component_collections(component_dirs)
    _sort_collections(collections)
    passages = [item for item in collections["passages.jsonl"] if isinstance(item, Passage)]
    texts = [item for item in collections["text_versions.jsonl"] if isinstance(item, TextVersion)]
    translations = [
        item for item in collections["translations.jsonl"] if isinstance(item, Translation)
    ]
    metadata = [
        item
        for item in collections["traditional_metadata.jsonl"]
        if isinstance(item, TraditionalMetadataAssertion)
    ]
    sources = [item for item in collections["sources.jsonl"] if isinstance(item, Source)]
    assertions = [
        item for item in collections["source_assertions.jsonl"] if isinstance(item, SourceAssertion)
    ]
    discoveries = [
        item for item in collections["discoveries.jsonl"] if isinstance(item, SuktaDiscoveryRecord)
    ]
    citations = [item for item in collections["citations.jsonl"] if isinstance(item, Citation)]
    audio = [
        item for item in collections["audio_recordings.jsonl"] if isinstance(item, AudioRecording)
    ]
    audio_segments = [
        item for item in collections["audio_segments.jsonl"] if isinstance(item, AudioSegment)
    ]

    corpus = CorpusRecords(
        passages=passages,
        texts=texts,
        translations=translations,
        metadata=metadata,
        sources=sources,
        citations=citations,
        audio_recordings=audio,
        audio_segments=audio_segments,
        source_assertions=assertions,
        discoveries=discoveries,
    )
    issues = list(validate_corpus(corpus))
    issues.extend(item for item in collections["qa_issues.jsonl"] if isinstance(item, QAIssue))
    mandala_count = sum(p.entity_type == EntityType.SECTION for p in passages)
    sukta_count = sum(p.entity_type == EntityType.HYMN for p in passages)
    mantra_count = sum(p.entity_type == EntityType.MANTRA for p in passages)
    discovered_suktas = len(
        {
            (item.mandala_number, item.sukta_number)
            for item in discoveries
            if item.source_id == "GRETIL"
        }
    )
    discovered_mantras = sum(
        item.known_mantra_count or 0 for item in discoveries if item.source_id == "GRETIL"
    )
    for unit, expected, discovered, canonical in (
        ("Mandalas", config.expected_mandalas, len(by_mandala), mandala_count),
        ("Suktas", config.expected_suktas, discovered_suktas, sukta_count),
        ("Mantras", config.expected_mantras, discovered_mantras, mantra_count),
    ):
        if expected != discovered or discovered != canonical:
            issues.append(
                _issue(
                    "expected_discovered_canonical_counts",
                    QASeverity.ERROR,
                    f"{unit}: expected {expected}, discovered {discovered}, canonical {canonical}",
                    "RV",
                    expected=expected,
                    discovered=discovered,
                    canonical=canonical,
                )
            )
    primary_ids = {t.passage_id for t in texts if t.text_role == TextRole.PRIMARY_TEXT}
    parallel_ids = {t.passage_id for t in texts if t.text_role == TextRole.PARALLEL_TEXT}
    mantra_ids = {p.entity_id for p in passages if p.entity_type == EntityType.MANTRA}
    for role, covered in (("PRIMARY_TEXT", primary_ids), ("PARALLEL_TEXT", parallel_ids)):
        if covered != mantra_ids:
            issues.append(
                _issue(
                    "complete_sanskrit_role_coverage",
                    QASeverity.ERROR,
                    f"{role} covers {len(covered & mantra_ids)}/{len(mantra_ids)} "
                    "canonical mantras",
                    "RV",
                    role=role,
                    missing=len(mantra_ids - covered),
                    extra=len(covered - mantra_ids),
                )
            )
    issues = _dedupe(issues, "issue_id")
    issues.sort(key=lambda item: (item.severity, item.check_id, str(item.issue_id)))
    collections["qa_issues.jsonl"] = issues

    comparisons = _comparison_records(passages, texts, primary_version, parallel_version)
    derived_dir = Path("data/derived/rigveda_full_v1")
    comparison_output = derived_dir / "text_comparisons.jsonl"
    write_jsonl(comparison_output, comparisons)
    comparison_report = Path("docs/reports/RIGVEDA_FULL_TEXT_COMPARISON.md")
    _write_comparison_report(comparisons, comparison_report)
    stats, per_sukta = _coverage_stats(
        passages, texts, translations, metadata, audio, issues, comparisons
    )
    per_sukta_path = derived_dir / "per_sukta_coverage.json"
    per_sukta_path.parent.mkdir(parents=True, exist_ok=True)
    per_sukta_path.write_bytes(orjson.dumps(per_sukta, option=orjson.OPT_INDENT_2) + b"\n")
    revision_manifest = sorted(
        {
            (
                item.source_page_title,
                item.source_page_id,
                item.source_revision_id,
                item.source_revision_timestamp.isoformat()
                if item.source_revision_timestamp is not None
                else None,
            )
            for item in translations
        }
    )
    revision_path = derived_dir / "griffith_revision_manifest.json"
    revision_path.write_bytes(orjson.dumps(revision_manifest, option=orjson.OPT_INDENT_2) + b"\n")

    output_dir = config.output_location
    stats_path = output_dir / "rigveda_stats.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_bytes(
        orjson.dumps(stats, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )
    generated: dict[Path, int] = {}
    for name, values in collections.items():
        path = output_dir / name
        generated[path] = write_jsonl(path, values)
    generated[stats_path] = 1
    write_qa_json(Path("data/qa/rigveda_full_v1.json"), issues)
    report = _render_full_report(
        stats,
        discovered_suktas,
        discovered_mantras,
        Counter(item.check_id for item in issues),
        qa_status(issues),
        primary_version,
        parallel_version,
    )
    report_path = Path("docs/reports/RIGVEDA_FULL_BUILD.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8", newline="\n")
    local_report = output_dir / "REPORT.md"
    local_report.write_text(report, encoding="utf-8", newline="\n")
    generated[local_report] = 1

    all_inputs = [source for component in component_configs for source in component.sources]
    component_hashes = {
        mandala: file_sha256(by_mandala[int(mandala)].output_location / "manifest.json")
        for mandala in component_manifests
    }
    config_hashes = {
        str(load_build_config(path).mandala): file_sha256(path) for path in config.mandala_configs
    }
    manifest = build_manifest(
        root=output_dir.parents[1],
        version=config.release_version,
        works=[config.work_id],
        passage_count=mantra_count,
        source_snapshot_ids=sorted({item.snapshot_id for item in all_inputs}),
        source_artifact_ids=sorted(
            {item.source_artifact_id for item in all_inputs if item.source_artifact_id}
        ),
        raw_snapshot_hashes={item.snapshot_id: item.snapshot_sha256 for item in all_inputs},
        build_config_sha256=file_sha256(config_path),
        parser_versions={
            f"{item.source_id}:{item.role}": item.parser_version for item in all_inputs
        },
        reconciliation_policy_version=config.reconciliation_policy_version,
        software_version=__version__,
        software_git_commit="UNCOMMITTED",
        qa_policy_version=config.qa_policy_version,
        comparison_version=COMPARATOR_VERSION,
        component_manifest_hashes=component_hashes,
        build_config_hashes=config_hashes,
        revision_manifest_sha256=file_sha256(revision_path),
        generated_content_sha256=_content_digest(generated),
        rights_summary={
            primary_version: "CC_BY_NC_SA",
            parallel_version: "CC_BY_NC_SA",
            "GRIFFITH.RV.1896": "PUBLIC_DOMAIN",
            "VHP": "PERMISSION_REQUIRED_REFERENCE_ONLY",
        },
        generated=generated,
        qa_status=qa_status(issues),
        built_at=config.build_timestamp,
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_bytes(
        orjson.dumps(
            manifest.model_dump(mode="json", exclude_none=True),
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
        + b"\n"
    )
    return FullCorpusBuildResult(
        output_dir=output_dir,
        mandala_count=mandala_count,
        sukta_count=sukta_count,
        mantra_count=mantra_count,
        primary_count=len(primary_ids),
        parallel_count=len(parallel_ids),
        translation_count=len(translations),
        warning_count=sum(item.severity == QASeverity.WARNING for item in issues),
        error_count=sum(item.severity == QASeverity.ERROR for item in issues),
        stats_path=stats_path,
        comparison_report_path=comparison_report,
        report_path=report_path,
        manifest_path=manifest_path,
    )


def semantic_hashes(output_dir: Path) -> dict[str, str]:
    """Hashes of canonical semantic collections, excluding reports and manifests."""
    return {
        name: file_sha256(output_dir / name)
        for name in COLLECTION_MODELS
        if name != "qa_issues.jsonl"
    }
