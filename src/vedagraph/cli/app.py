"""VedaGraph command-line interface."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from vedagraph.build import build_from_config, stage_from_config
from vedagraph.compare import (
    VersionReading,
    compare_readings,
    load_comparison_config,
    load_readings,
    run_comparison,
    summarize,
    write_report,
)
from vedagraph.config import get_settings
from vedagraph.config.registry import (
    load_build_config,
    load_source_artifacts,
    load_sources,
    load_text_versions,
)
from vedagraph.corpus import build_rv_1_1_pilot
from vedagraph.discovery import assertion_conflicts, discover_rigveda_mandala
from vedagraph.ingest.adapters import GRETILAdapter, VHPAdapter
from vedagraph.ingest.fetcher import PoliteFetcher
from vedagraph.knowledge.registry import load_resolvers
from vedagraph.metadata import candidates_from_assertions, write_review
from vedagraph.models import (
    CorpusManifest,
    KnowledgeAssertion,
    KnowledgeStats,
    Passage,
    SourceAssertion,
)
from vedagraph.models.enums import EntityType, KnowledgeEntityType
from vedagraph.models.semantic import (
    EvidencePacket,
    SemanticAssertionCandidate,
    SemanticValidationResult,
)
from vedagraph.qa import print_qa_report
from vedagraph.schema import export_schemas
from vedagraph.semantic.codex_direct import (
    EXECUTION_VERSION,
    ExecutionStore,
    RunContract,
    load_run_contract,
    prepare_task,
)
from vedagraph.semantic.evaluate import (
    evaluate_against_gold,
    load_gold_annotations,
    write_evaluation_reports,
)
from vedagraph.semantic.gold import (
    DEFAULT_ADJUDICATION_FILE,
    DEFAULT_GOLD_FILE,
    DEFAULT_PILOT_CONFIG,
    DEFAULT_PILOT_RUN,
    finalize_gold,
    load_adjudications,
    load_packet_index,
    progress,
    validate_gold_file,
)
from vedagraph.semantic.heuristic_baseline import BASELINE_PROVENANCE, extract_packet
from vedagraph.semantic.review import review_gold
from vedagraph.storage import read_jsonl, write_jsonl

app = typer.Typer(help="Build and validate the provenance-aware VedaGraph canonical corpus.")
source_app = typer.Typer(help="Inspect and retrieve registered sources.")
ingest_app = typer.Typer(help="Parse immutable raw snapshots into staging records.")
corpus_app = typer.Typer(help="Build, inspect, reconcile, and validate corpus releases.")
schema_app = typer.Typer(help="Manage generated JSON Schemas.")
assertions_app = typer.Typer(help="Inspect persisted source assertions and conflicts.")
text_app = typer.Typer(help="Compare Sanskrit text versions of the same passage.")
metadata_app = typer.Typer(help="Inspect candidate traditional-metadata scopes.")
knowledge_app = typer.Typer(help="Inspect the deterministic Rishi/Devata/Chandas knowledge layer.")
semantic_app = typer.Typer(help="Review and evaluate model-authored semantic candidates.")
gold_app = typer.Typer(help="Blinded human gold review and signed dataset management.")
execute_app = typer.Typer(
    help="CODEX_DIRECT model execution: prepare frozen tasks, import authored responses."
)
app.add_typer(source_app, name="source")
app.add_typer(ingest_app, name="ingest")
app.add_typer(corpus_app, name="corpus")
app.add_typer(schema_app, name="schema")
app.add_typer(assertions_app, name="assertions")
app.add_typer(text_app, name="text")
app.add_typer(metadata_app, name="metadata")
app.add_typer(knowledge_app, name="knowledge")
app.add_typer(semantic_app, name="semantic")
semantic_app.add_typer(gold_app, name="gold")
semantic_app.add_typer(execute_app, name="execute")
console = Console()


@source_app.command("list")
def source_list() -> None:
    """List validated source registry entries and ingestion status."""
    table = Table("ID", "Name", "Authority", "Rights", "Bulk ingestion")
    for source in load_sources():
        table.add_row(
            source.source_id,
            source.name,
            source.authority_tier,
            source.rights.status,
            source.bulk_ingestion_status,
        )
    console.print(table)


@source_app.command("artifacts")
def source_artifacts() -> None:
    """List exact registered source files/editions."""
    table = Table("Artifact", "Source", "Format", "Rights", "Edition")
    for artifact in load_source_artifacts():
        table.add_row(
            artifact.artifact_id,
            artifact.source_id,
            artifact.format,
            artifact.rights_status,
            artifact.source_edition or artifact.edition_title or "",
        )
    console.print(table)


@source_app.command("fetch")
def source_fetch(source_id: str, url: str, force: bool = False) -> None:
    """Fetch one explicit URL into the immutable raw snapshot store."""
    registered = {source.source_id for source in load_sources()}
    if source_id not in registered:
        raise typer.BadParameter(f"source_id is not registered: {source_id}")
    result = asyncio.run(PoliteFetcher(get_settings()).fetch(source_id, url, force=force))
    console.print(f"snapshot_id: {result.metadata.snapshot_id}")
    console.print(f"path: {result.content_path} (reused={result.reused})")


@ingest_app.command("parse")
def ingest_parse(source_id: str, snapshot: Path) -> None:
    """Parse a supported raw snapshot and report staging record count."""
    adapters = {"VHP": VHPAdapter(), "GRETIL": GRETILAdapter()}
    adapter = adapters.get(source_id)
    if adapter is None:
        raise typer.BadParameter(f"no parser enabled for source: {source_id}")
    records = adapter.parse(snapshot, snapshot_id="manual-inspection")
    console.print(f"Parsed {len(records)} staging records; canonical data was not written.")


@ingest_app.command("stage")
def ingest_stage(
    config: Path = typer.Option(  # noqa: B008
        Path("data/builds/rv_mandala_1.yaml"), exists=True
    ),
) -> None:
    """Persist typed source staging and source assertions only."""
    result = stage_from_config(config)
    console.print(f"Staged: {result.staged_dir}")
    console.print(
        f"{result.text_count} Sanskrit, {result.translation_count} translations, "
        f"{result.metadata_count} metadata pages, {result.assertion_count} assertions"
    )


@app.command("discover")
def discover(
    work: str = typer.Argument("rigveda"),
    mandala: int = typer.Option(1),
    config: Path = typer.Option(  # noqa: B008
        Path("data/builds/rv_mandala_1.yaml"), exists=True
    ),
) -> None:
    """Discover corpus structure from declared immutable snapshots."""
    if work.lower() != "rigveda":
        raise typer.BadParameter("only rigveda discovery is implemented")
    build_config = load_build_config(config)
    gretil = next(item for item in build_config.sources if item.role == "sanskrit")
    vhp = next(item for item in build_config.sources if item.role == "discovery")
    result = discover_rigveda_mandala(
        mandala=mandala,
        gretil_snapshot=gretil.snapshot_path,
        gretil_snapshot_id=gretil.snapshot_id,
        vhp_snapshot=vhp.snapshot_path,
        vhp_snapshot_id=vhp.snapshot_id,
        output_dir=Path("data/staged/discovery"),
    )
    console.print(
        f"Discovered {result.unique_suktas} unique Suktas "
        f"(GRETIL={result.gretil_suktas}, VHP={result.vhp_suktas}, "
        f"agreement={result.agreement})"
    )


@corpus_app.command("build-pilot")
def corpus_build_pilot() -> None:
    """Build the bounded RV 1.1 pilot from cached-or-live snapshots."""
    result = asyncio.run(build_rv_1_1_pilot(get_settings()))
    console.print(f"Built: {result.output_dir}")
    console.print(
        f"{result.mantra_count} mantras, {result.text_count} Sanskrit texts, "
        f"{result.translation_count} translations, {result.qa_issue_count} QA issues"
    )


@corpus_app.command("build")
def corpus_build(
    config: Path | None = typer.Option(  # noqa: B008
        None, exists=True, help="Versioned offline build config."
    ),
    scope: str = typer.Option("RV.1.1", help="Legacy bounded build scope."),
) -> None:
    """Build from a versioned config, or run the legacy RV 1.1 pilot."""
    if config is not None:
        result = build_from_config(config)
        console.print(f"Built: {result.output_dir}")
        console.print(
            f"{result.sukta_count} Suktas, {result.mantra_count} mantras, "
            f"{result.translation_count} translations, {result.qa_issue_count} QA findings"
        )
        return
    if scope != "RV.1.1":
        raise typer.BadParameter("use --config for scopes beyond the legacy RV.1.1 pilot")
    corpus_build_pilot()


@corpus_app.command("assemble")
def corpus_assemble(
    config: Path = typer.Option(  # noqa: B008
        Path("data/builds/rv_full_v1.yaml"), exists=True, help="Full-corpus composition config."
    ),
) -> None:
    """Assemble independently validated Mandala builds into the full corpus."""
    from vedagraph.full_corpus import assemble_full_corpus

    result = assemble_full_corpus(config)
    console.print(f"Assembled: {result.output_dir}")
    console.print(
        f"{result.mandala_count} Mandalas, {result.sukta_count} Suktas, "
        f"{result.mantra_count} mantras, primary {result.primary_count}, "
        f"parallel {result.parallel_count}, translations {result.translation_count}"
    )
    console.print(f"{result.error_count} errors, {result.warning_count} warnings")


@corpus_app.command("validate")
def corpus_validate(
    qa_file: Path = Path("data/qa/rv_1_1_pilot.json"),
) -> None:
    """Display the latest machine-readable QA result."""
    if not qa_file.exists():
        raise typer.BadParameter("QA file not found; run corpus build-pilot first")
    import orjson

    from vedagraph.models import QAIssue

    payload = orjson.loads(qa_file.read_bytes())
    issues = [QAIssue.model_validate(item) for item in payload["issues"]]
    print_qa_report(issues, console)


@corpus_app.command("stats")
def corpus_stats(
    passages_file: Path = Path("data/canonical/rv_1_1_pilot/passages.jsonl"),
) -> None:
    """Compute counts from actual canonical records."""
    passages = list(read_jsonl(passages_file, Passage))
    mandalas = sum(passage.entity_type == EntityType.SECTION for passage in passages)
    suktas = sum(passage.entity_type == EntityType.HYMN for passage in passages)
    mantras = sum(passage.entity_type == EntityType.MANTRA for passage in passages)
    console.print("STRUCTURAL NODES")
    console.print(f"  mandalas: {mandalas}")
    console.print(f"  suktas: {suktas}")
    console.print("TEXTUAL OCCURRENCES")
    console.print(f"  mantras: {mantras}")


@corpus_app.command("lineage")
def corpus_lineage(
    manifest_file: Path = Path("data/canonical/rv_mandala_1_sample_v2/manifest.json"),
) -> None:
    """Inspect corpus build lineage from a manifest."""
    manifest = CorpusManifest.model_validate_json(manifest_file.read_bytes())
    console.print(f"Version: {manifest.version}")
    console.print(f"Build config SHA-256: {manifest.build_config_sha256}")
    console.print(f"Artifacts: {', '.join(manifest.source_artifact_ids)}")
    console.print(f"Snapshots: {len(manifest.source_snapshot_ids)}")
    console.print(f"QA: {manifest.qa_status}")


@assertions_app.command("list")
def assertions_list(
    passage: str | None = typer.Option(None, help="Canonical key/subject filter."),
    assertions_file: Path = Path("data/staged/rv_mandala_1_sample_v2/source_assertions.jsonl"),
) -> None:
    """List persisted attributable source assertions."""
    values = list(read_jsonl(assertions_file, SourceAssertion))
    if passage:
        values = [value for value in values if value.subject_id == passage]
    table = Table("Subject", "Predicate", "Source", "Value", "Status")
    for value in values:
        table.add_row(
            value.subject_id,
            value.predicate,
            value.source_id,
            str(value.value)[:80],
            value.status,
        )
    console.print(table)


@assertions_app.command("conflicts")
def assertions_conflict_list(
    assertions_file: Path = Path("data/staged/rv_mandala_1_sample_v2/source_assertions.jsonl"),
) -> None:
    """Report source assertions that disagree for the same subject/predicate."""
    values = list(read_jsonl(assertions_file, SourceAssertion))
    conflicts = assertion_conflicts(values)
    if not conflicts:
        console.print("No source assertion conflicts.")
        return
    for (subject, predicate), assertions in sorted(conflicts.items()):
        console.print(f"{subject} {predicate}")
        for assertion in assertions:
            console.print(f"  {assertion.source_id}: {assertion.value}")


@corpus_app.command("normalize")
def corpus_normalize() -> None:
    """Describe the normalization stage available in D1."""
    console.print(
        "Unicode NFC and explicit comparison profiles are available; use build-pilot to run them."
    )


@corpus_app.command("reconcile")
def corpus_reconcile() -> None:
    """Describe field-specific reconciliation policy hooks."""
    console.print(
        "Field-specific reconciliation hooks are configured; conflicting assertions are retained."
    )


@schema_app.command("export")
def schema_export(directory: Path = Path("schemas")) -> None:
    """Regenerate JSON Schemas from Pydantic models."""
    paths = export_schemas(directory)
    console.print(f"Exported {len(paths)} schemas to {directory}")


@source_app.command("text-versions")
def source_text_versions() -> None:
    """List declared Sanskrit text versions with their per-version rights."""
    table = Table("Version", "Artifact", "Role", "Restored", "Rights")
    for version in load_text_versions():
        table.add_row(
            version.text_version_id,
            version.artifact_id,
            version.text_role,
            "yes" if version.metrical_restoration else "no",
            version.normalized_rights,
        )
    console.print(table)


@text_app.command("compare")
def text_compare(
    citation: str = typer.Argument(..., help="Passage citation, for example RV.1.1.1"),
    versions: str = typer.Option(..., help="Comma-separated registered text version IDs."),
    config: Path = typer.Option(  # noqa: B008
        Path("data/builds/rv_m1_text_comparison.yaml"), exists=True
    ),
) -> None:
    """Compare one mantra across two or more registered text versions."""
    parts = citation.replace("RV.", "").split(".")
    if len(parts) != 3:
        raise typer.BadParameter("citation must look like RV.1.1.1")
    mandala, sukta, mantra = (int(part) for part in parts)
    comparison_config = load_comparison_config(config)
    if mandala != comparison_config.mandala or sukta not in comparison_config.selected_suktas:
        raise typer.BadParameter(f"{citation} is not covered by {config}")
    wanted = [name.strip() for name in versions.split(",") if name.strip()]
    if len(wanted) < 2:
        raise typer.BadParameter("give at least two versions")
    roles = {item.text_version_id: item.text_role for item in load_text_versions()}
    unknown = sorted(set(wanted) - set(roles))
    if unknown:
        raise typer.BadParameter(f"unregistered text versions: {', '.join(unknown)}")
    readings = load_readings(comparison_config).get((sukta, mantra), {})
    absent = sorted(name for name in wanted if name not in readings)
    if absent:
        raise typer.BadParameter(f"no reading for {', '.join(absent)} at {citation}")
    baseline = wanted[0]
    table = Table("Compared", "Category", "Similarity", "Accent only", "Basis")
    for name in wanted[1:]:
        result = compare_readings(
            passage_key=f"VG:RV:SAK:M{mandala:02d}:S{sukta:03d}:V{mantra:03d}",
            citation=f"RV {mandala}.{sukta}.{mantra}",
            left=VersionReading(baseline, readings[baseline], roles[baseline]),
            right=VersionReading(name, readings[name], roles[name]),
        )
        table.add_row(
            f"{baseline} vs {name}",
            result.category,
            f"{result.similarity:.3f}",
            "yes" if result.accent_only else "no",
            result.classification_basis,
        )
    console.print(table)


@text_app.command("compare-sample")
def text_compare_sample(
    config: Path = typer.Option(  # noqa: B008
        Path("data/builds/rv_m1_text_comparison.yaml"), exists=True
    ),
) -> None:
    """Run the version-controlled stratified comparison sample and write its report."""
    comparison_config = load_comparison_config(config)
    result = run_comparison(config)
    written = write_jsonl(
        comparison_config.output_location / "text_comparisons.jsonl", result.comparisons
    )
    report = write_report(comparison_config, result, comparison_config.report_path)
    console.print(f"Aligned mantras: {result.aligned_passages}; comparisons: {written}")
    table = Table("Comparison", "Categories")
    for (left, right), counter in sorted(summarize(result.comparisons).items()):
        table.add_row(
            f"{left} vs {right}",
            ", ".join(f"{category}={count}" for category, count in sorted(counter.items())),
        )
    console.print(table)
    console.print(f"Report: {report}")


@metadata_app.command("review-ranges")
def metadata_review_ranges(
    assertions_file: Path = Path("data/staged/rv_mandala_1_sample_v2/source_assertions.jsonl"),
    output: Path = Path("docs/reports/rv_m1_metadata_range_review.md"),
    full_output: Path = Path("data/derived/metadata_candidates/rv_m1_metadata_range_review.md"),
    candidates_file: Path = Path("data/derived/metadata_candidates/candidates.jsonl"),
) -> None:
    """Parse traditional-metadata strings into reviewable candidates. Promotes nothing.

    Two reports are written. The committed one withholds the verbatim source strings,
    because VHP is a permission-required source; the local one under data/derived keeps
    them so a reader can check the parser against the notation it was given.
    """
    assertions = list(read_jsonl(assertions_file, SourceAssertion))
    candidates = candidates_from_assertions(assertions)
    written = write_jsonl(candidates_file, candidates)
    report = write_review(candidates, output, redact_source_text=True)
    full_report = write_review(candidates, full_output)
    promotable = sum(1 for candidate in candidates if candidate.safe_to_promote)
    table = Table("Subject", "Predicate", "Status", "Segments", "Safe to promote")
    for candidate in candidates:
        table.add_row(
            candidate.subject_id,
            candidate.predicate,
            candidate.parse_status,
            str(len(candidate.segments)),
            "yes" if candidate.safe_to_promote else "no",
        )
    console.print(table)
    console.print(
        f"{written} candidates written to {candidates_file}; "
        f"{promotable} parser-clean; none promoted to canonical metadata."
    )
    console.print(f"Review report (committed, redacted): {report}")
    console.print(f"Review report (local, full source strings): {full_report}")


@gold_app.command("review")
def semantic_gold_review(
    gold_file: Path = typer.Option(DEFAULT_GOLD_FILE, help="Identifier-only human gold JSONL."),  # noqa: B008
    adjudication_file: Path = typer.Option(DEFAULT_ADJUDICATION_FILE),  # noqa: B008
    pilot_config: Path = typer.Option(DEFAULT_PILOT_CONFIG, exists=True),  # noqa: B008
    run_dir: Path = typer.Option(DEFAULT_PILOT_RUN, help="Local ignored pilot packet directory."),  # noqa: B008
    reviewer: str | None = typer.Option(
        None, help="Reviewer id; prompted and persisted if omitted."
    ),
) -> None:
    """Review one local EvidencePacket at a time using blinded Stage A then Stage B."""
    review_gold(
        gold_path=gold_file,
        adjudication_path=adjudication_file,
        config_path=pilot_config,
        run_dir=run_dir,
        reviewer=reviewer,
    )


@gold_app.command("validate")
def semantic_gold_validate(
    gold_file: Path = typer.Option(DEFAULT_GOLD_FILE),  # noqa: B008
    pilot_config: Path = typer.Option(DEFAULT_PILOT_CONFIG, exists=True),  # noqa: B008
    run_dir: Path = typer.Option(DEFAULT_PILOT_RUN),  # noqa: B008
) -> None:
    """Validate all 120 ids, statuses, ontology values, and packet evidence references."""
    result = validate_gold_file(
        gold_file, config_path=pilot_config, run_dir=run_dir, require_complete=True
    )
    console.print(
        f"Gold status: {result.status.value}; rows {result.present_count}/{result.expected_count}; "
        f"complete {result.complete_count}/{result.expected_count}"
    )
    if result.errors:
        for error in result.errors:
            console.print(f"[red]ERROR[/red] {error}")
        raise typer.Exit(code=1)
    console.print("Gold validation passed.")


@gold_app.command("finalize")
def semantic_gold_finalize(
    gold_file: Path = typer.Option(DEFAULT_GOLD_FILE),  # noqa: B008
    pilot_config: Path = typer.Option(DEFAULT_PILOT_CONFIG, exists=True),  # noqa: B008
    run_dir: Path = typer.Option(DEFAULT_PILOT_RUN),  # noqa: B008
    manifest_file: Path = typer.Option(Path("data/gold/rigveda_semantic_gold_v1.manifest.json")),  # noqa: B008
    version: str = typer.Option("vedagraph-rigveda-semantic-gold-v1"),
) -> None:
    """Validate complete human gold and write its signed SHA-256 manifest."""
    try:
        manifest = finalize_gold(
            gold_file,
            config_path=pilot_config,
            run_dir=run_dir,
            manifest_path=manifest_file,
            version=version,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    console.print(f"Signed gold: {manifest['version']}")
    console.print(f"SHA-256: {manifest['gold_sha256']}")
    console.print(f"Manifest: {manifest_file}")


@semantic_app.command("eval")
def semantic_eval(
    gold_file: Path = typer.Option(DEFAULT_GOLD_FILE),  # noqa: B008
    pilot_run: Path = typer.Option(DEFAULT_PILOT_RUN),  # noqa: B008
    pilot_config: Path = typer.Option(DEFAULT_PILOT_CONFIG, exists=True),  # noqa: B008
    reports_dir: Path = typer.Option(Path("docs/reports")),  # noqa: B008
) -> None:
    """Evaluate the unchanged pilot against signed human gold, or show safe progress only."""
    from vedagraph.semantic.gold import expected_gold_ids

    status = validate_gold_file(
        gold_file, config_path=pilot_config, run_dir=pilot_run, require_complete=True
    )
    if not status.valid or status.complete_count != status.expected_count:
        state = progress(gold_file, DEFAULT_ADJUDICATION_FILE, pilot_config)
        console.print("GOLD_NOT_COMPLETE")
        console.print(
            f"Safe progress only: {state.blinded_complete}/{state.total} blinded rows complete; "
            f"{state.remaining} remaining."
        )
        write_evaluation_reports(
            output_dir=reports_dir,
            gold_complete=False,
            expected_count=len(expected_gold_ids(pilot_config)),
            gold_count=state.blinded_complete,
            adjudications=load_adjudications(DEFAULT_ADJUDICATION_FILE),
        )
        return

    gold = load_gold_annotations(gold_file)
    candidates_path = pilot_run / "semantic_candidates.jsonl"
    validation_path = pilot_run / "semantic_validation.jsonl"
    candidates = (
        [
            SemanticAssertionCandidate.model_validate(json.loads(line))
            for line in candidates_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if candidates_path.exists()
        else []
    )
    validations = (
        {
            item.candidate_assertion_id: item
            for item in (
                SemanticValidationResult.model_validate(json.loads(line))
                for line in validation_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        }
        if validation_path.exists()
        else {}
    )
    predictions: dict[str, list[SemanticAssertionCandidate]] = {key: [] for key in gold}
    for candidate in candidates:
        predictions.setdefault(candidate.subject_key, []).append(candidate)
    packets = load_packet_index(pilot_run)
    entity_labels = {
        key: label
        for packet in packets.values()
        for keys, labels in (
            (packet.devata_keys, packet.devata_labels),
            (packet.rishi_keys, packet.rishi_labels),
            (packet.chandas_keys, packet.chandas_labels),
        )
        for key, label in zip(keys, labels, strict=True)
    }
    report = evaluate_against_gold(
        gold,
        predictions,
        validations,
        entity_labels=entity_labels,
        candidate_labels={},
    )
    write_evaluation_reports(
        output_dir=reports_dir,
        gold_complete=True,
        expected_count=status.expected_count,
        gold_count=status.complete_count,
        report=report,
        gold=gold,
        predictions=predictions,
        adjudications=load_adjudications(DEFAULT_ADJUDICATION_FILE),
    )
    console.print("Gold status: COMPLETE")
    table = Table("Predicate", "TP", "FP", "FN", "Precision", "Recall", "F1", "Support", "Unlocked")
    for predicate, score in report.relation_scores.items():
        table.add_row(
            predicate.value,
            str(score.true_positives),
            str(score.false_positives),
            str(score.false_negatives),
            f"{score.precision:.3f}" if score.precision is not None else "n/a",
            f"{score.recall:.3f}" if score.recall is not None else "n/a",
            f"{score.f1:.3f}" if score.f1 is not None else "n/a",
            str(score.predicted),
            "yes" if score.meets_target else "no",
        )
    console.print(table)
    console.print(f"Reports: {reports_dir}")


DEFAULT_V3_PROMPT = Path("prompts/semantic_extraction_v3.md")
DEFAULT_V3_SCHEMA = Path("schemas/semantic_extraction_v3.schema.json")
DEFAULT_SEMANTIC_ONTOLOGY = Path("src/vedagraph/semantic/ontology.py")


def _read_packets(path: Path) -> list[EvidencePacket]:
    return [
        EvidencePacket.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@execute_app.command("prepare")
def semantic_execute_prepare(
    packets: Path = typer.Option(..., exists=True, help="JSONL of built EvidencePackets."),  # noqa: B008
    run_id: str = typer.Option(..., help="Execution run identifier."),
    out_dir: Path = typer.Option(..., help="Task store root."),  # noqa: B008
    model: str = typer.Option("gpt-5.6-luna", help="Model the run requests."),
    reasoning: str = typer.Option("high", help="Reasoning effort the run requests."),
    prompt_file: Path = typer.Option(DEFAULT_V3_PROMPT, exists=True),  # noqa: B008
    schema_file: Path = typer.Option(DEFAULT_V3_SCHEMA, exists=True),  # noqa: B008
    ontology_file: Path = typer.Option(DEFAULT_SEMANTIC_ONTOLOGY, exists=True),  # noqa: B008
    execution_version: str = typer.Option(EXECUTION_VERSION),
) -> None:
    """Freeze one immutable model task per mantra. Writes no semantic content whatsoever."""
    contract = load_run_contract(
        run_id=run_id,
        prompt_path=prompt_file,
        schema_path=schema_file,
        ontology_path=ontology_file,
        model_requested=model,
        reasoning_requested=reasoning,
        execution_version=execution_version,
    )
    store = ExecutionStore(out_dir)
    table = Table("Task", "Mantra", "Task SHA-256")
    for packet in _read_packets(packets):
        task = prepare_task(packet, contract)
        store.write_task(task)
        table.add_row(task.task_id, task.citation, task.task_sha256)
    (out_dir / "run_contract.json").write_text(
        json.dumps(contract.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    console.print(table)
    console.print(
        "Prepared tasks only. No predicate, object, confidence or explicitness was authored; "
        "a model must write a response before any semantic output exists."
    )


@execute_app.command("import-response")
def semantic_execute_import_response(
    response: Path = typer.Argument(..., help="Model-authored response file."),  # noqa: B008
    store_dir: Path = typer.Option(..., help="Task store root used by prepare."),  # noqa: B008
) -> None:
    """Validate and persist one model-authored response. Fails closed on any mismatch."""
    contract_path = store_dir / "run_contract.json"
    if not contract_path.exists():
        raise typer.BadParameter(f"{contract_path} is missing; run prepare first")
    contract = RunContract.model_validate_json(contract_path.read_text(encoding="utf-8"))
    try:
        validated = ExecutionStore(store_dir).import_response(response, contract)
    except (FileNotFoundError, ValueError) as error:
        console.print(f"[red]REFUSED[/red] {error}")
        raise typer.Exit(code=1) from error
    console.print(
        f"Imported {validated.task.task_id} ({validated.task.citation}); "
        f"attempt {validated.receipt.attempt_id}; "
        f"raw receipt SHA-256 {validated.raw_response_sha256}"
    )
    console.print(
        f"{len(validated.payload.assertions)} candidate assertions, "
        f"{len(validated.payload.ontology_gaps)} ontology gaps, status CANDIDATE / NEEDS_REVIEW."
    )


@semantic_app.command("heuristic-baseline")
def semantic_heuristic_baseline(
    packets: Path = typer.Option(..., exists=True, help="JSONL of built EvidencePackets."),  # noqa: B008
    run_id: str = typer.Option(..., help="Baseline run identifier; must not name a model."),
    out_file: Path = typer.Option(..., help="Destination JSONL for baseline payloads."),  # noqa: B008
) -> None:
    """Run the deterministic cue matcher. This is not extraction by a model.

    Output carries DETERMINISTIC_HEURISTIC_BASELINE provenance and is refused by the
    full-run store, which accepts only model-authored receipts.
    """
    rows = []
    for packet in _read_packets(packets):
        payload, _ = extract_packet(packet, run_id=run_id)
        rows.append(json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    console.print(f"{len(rows)} baseline payloads written to {out_file}")
    console.print(f"Provenance: {BASELINE_PROVENANCE}. Not a model run, not CODEX_DIRECT.")


@app.callback()
def main() -> None:
    """VedaGraph corpus tooling."""


@knowledge_app.command("stats")
def knowledge_stats(
    knowledge_dir: Path = Path("data/knowledge/rigveda_deterministic_v1"),
) -> None:
    """Show deterministic metadata coverage and the most frequently assigned entities."""
    stats = KnowledgeStats.model_validate_json(
        (knowledge_dir / "knowledge_stats.json").read_bytes()
    )
    console.print(f"[bold]{stats.metric_definition}[/bold]")
    coverage = Table("Predicate", "Resolved", "Unresolved only", "No claim", "Multiple", "Entities")
    for item in stats.coverage:
        coverage.add_row(
            item.predicate,
            f"{item.mantras_resolved:,}/{item.total_mantras:,}",
            f"{item.mantras_unresolved_only:,}",
            f"{item.mantras_without_claim:,}",
            f"{item.mantras_with_multiple_entities:,}",
            f"{item.distinct_entities:,}",
        )
    console.print(coverage)
    for title, rows in (
        ("Devatā", stats.top_devatas),
        ("Ṛṣi", stats.top_rishis),
        ("Chandas", stats.top_chandas),
    ):
        table = Table(f"{title} entity", "Label", "Mantras assigned", "Sūktas")
        for row in rows[:10]:
            table.add_row(
                row.entity_key,
                row.preferred_label,
                f"{row.mantra_assignment_count:,}",
                f"{row.sukta_count:,}",
            )
        console.print(table)


@knowledge_app.command("mantras")
def knowledge_mantras(
    entity: str,
    predicate: str | None = None,
    knowledge_dir: Path = Path("data/knowledge/rigveda_deterministic_v1"),
    limit: int = 20,
) -> None:
    """List the mantras a canonical entity is assigned to, with full provenance.

    The answer never calls a language model: it reads deterministic assertions that each
    name the source assertion and pinned artifact they came from.
    """
    matches = [
        assertion
        for assertion in read_jsonl(
            knowledge_dir / "knowledge_assertions.jsonl", KnowledgeAssertion
        )
        if assertion.object_key == entity
        and (predicate is None or assertion.predicate == predicate)
    ]
    table = Table("Citation", "Mantra key", "Predicate", "Source label", "Scope", "Resolution")
    for assertion in matches[:limit]:
        table.add_row(
            assertion.citation,
            assertion.subject_key,
            assertion.predicate,
            assertion.source_label,
            assertion.scope_origin,
            assertion.resolution_method,
        )
    console.print(table)
    console.print(
        f"{len(matches):,} mantra assignments for {entity}; showing {min(limit, len(matches))}."
    )


@knowledge_app.command("entities")
def knowledge_entities(
    entity_type: str = "DEVATA",
    registry_root: Path = Path("data/registry"),
    limit: int = 25,
) -> None:
    """List canonical entities and their reviewed aliases from the committed registries."""
    resolver = load_resolvers(registry_root)[KnowledgeEntityType(entity_type)]
    table = Table("Entity key", "Preferred label", "Aliases", "Subtype")
    for entry in resolver.entries[:limit]:
        aliases = resolver.alias_entries(entry.entity_key)
        table.add_row(
            entry.entity_key,
            entry.preferred_label,
            ", ".join(f"{alias.alias} ({alias.alias_type})" for alias in aliases) or "—",
            entry.devata_subtype or "—",
        )
    console.print(table)
    console.print(
        f"{len(resolver.entries):,} {entity_type} entities; "
        f"showing {min(limit, len(resolver.entries))}."
    )
