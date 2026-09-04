"""VedaGraph command-line interface."""

from __future__ import annotations

import asyncio
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
from vedagraph.qa import print_qa_report
from vedagraph.schema import export_schemas
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
app.add_typer(source_app, name="source")
app.add_typer(ingest_app, name="ingest")
app.add_typer(corpus_app, name="corpus")
app.add_typer(schema_app, name="schema")
app.add_typer(assertions_app, name="assertions")
app.add_typer(text_app, name="text")
app.add_typer(metadata_app, name="metadata")
app.add_typer(knowledge_app, name="knowledge")
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
