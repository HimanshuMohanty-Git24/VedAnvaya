"""Offline, config-driven text-version comparison over a stratified sample."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

from vedagraph.compare.text import VersionReading, compare_missing, compare_readings
from vedagraph.config.registry import load_text_versions
from vedagraph.identity import rv_mantra_key
from vedagraph.ingest.adapters import GRETILAdapter, VedaWebAdapter
from vedagraph.models import TextComparison
from vedagraph.models.core import VGModel
from vedagraph.models.enums import TextComparisonCategory, TextRole, TextSelectionPolicy
from vedagraph.normalize import has_vedic_accents
from vedagraph.storage.manifest import file_sha256

COMPARISON_CONFIG_VERSION = "1.0.0"


class ComparisonInput(VGModel):
    source_id: str
    artifact_id: str
    snapshot_path: Path
    snapshot_id: str
    snapshot_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    parser_version: str


class TextComparisonConfig(VGModel):
    config_version: str
    dataset_id: str
    work_id: str
    mandala: int = Field(ge=1)
    selected_suktas: list[int] = Field(min_length=1)
    sample_rationale: dict[str, str] = Field(default_factory=dict)
    baseline_version_id: str
    compared_version_ids: list[str] = Field(min_length=1)
    additional_pairs: list[tuple[str, str]] = Field(default_factory=list)
    text_selection_policy: TextSelectionPolicy = TextSelectionPolicy.ORIGINAL
    inputs: list[ComparisonInput] = Field(min_length=1)
    output_location: Path
    report_path: Path


@dataclass(frozen=True)
class ComparisonResult:
    config_sha256: str
    aligned_passages: int
    comparisons: list[TextComparison]
    readings_per_version: dict[str, int]
    accented_per_version: dict[str, int]
    output_path: Path
    report_path: Path


def load_comparison_config(path: Path) -> TextComparisonConfig:
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return TextComparisonConfig.model_validate(payload)


def _verify_inputs(config: TextComparisonConfig) -> None:
    for item in config.inputs:
        if not item.snapshot_path.exists():
            raise FileNotFoundError(item.snapshot_path)
        actual = file_sha256(item.snapshot_path)
        if actual != item.snapshot_sha256:
            raise ValueError(
                f"snapshot hash mismatch for {item.snapshot_path}: "
                f"expected {item.snapshot_sha256}, got {actual}"
            )


def load_readings(config: TextComparisonConfig) -> dict[tuple[int, int], dict[str, str]]:
    """Return ``{(sukta, mantra): {text_version_id: text}}`` from pinned snapshots only."""
    selected = frozenset(config.selected_suktas)
    readings: dict[tuple[int, int], dict[str, str]] = {}
    for item in config.inputs:
        if item.source_id == "GRETIL":
            staged = GRETILAdapter(
                text_selection_policy=config.text_selection_policy,
                source_artifact_id=item.artifact_id,
            ).parse(item.snapshot_path, snapshot_id=item.snapshot_id)
            for record in staged:
                if int(record.hierarchy["mandala"]) != config.mandala:
                    continue
                sukta = int(record.hierarchy["sukta"])
                if sukta not in selected:
                    continue
                key = (sukta, int(record.hierarchy["mantra"]))
                readings.setdefault(key, {})["GRETIL.RV.AUFRECHT"] = record.text_original
        elif item.source_id == "VEDAWEB":
            staged = VedaWebAdapter(source_artifact_id=item.artifact_id).parse_versions(
                item.snapshot_path, snapshot_id=item.snapshot_id, suktas=selected
            )
            for record in staged:
                if int(record.hierarchy["mandala"]) != config.mandala:
                    continue
                key = (int(record.hierarchy["sukta"]), int(record.hierarchy["mantra"]))
                version = (record.text_version_id or "").rsplit("#", 1)[-1]
                readings.setdefault(key, {})[f"VEDAWEB.{version.upper()}"] = record.text_original
        else:
            raise ValueError(f"no comparison reader for source: {item.source_id}")
    return readings


def run_comparison(config_path: Path) -> ComparisonResult:
    """Compare the baseline version against each configured version, deterministically."""
    config = load_comparison_config(config_path)
    _verify_inputs(config)
    roles = {version.text_version_id: version.text_role for version in load_text_versions()}
    referenced = {config.baseline_version_id, *config.compared_version_ids}
    referenced.update(name for pair in config.additional_pairs for name in pair)
    unknown = sorted(referenced - set(roles))
    if unknown:
        raise ValueError(f"unregistered text versions: {', '.join(unknown)}")

    readings = load_readings(config)
    comparisons: list[TextComparison] = []
    counts: Counter[str] = Counter()
    accented: Counter[str] = Counter()
    for (sukta, mantra), by_version in sorted(readings.items()):
        passage_key = rv_mantra_key(config.mandala, sukta, mantra)
        citation = f"RV {config.mandala}.{sukta}.{mantra}"
        counts.update(by_version.keys())
        accented.update(name for name, text in by_version.items() if has_vedic_accents(text))
        pairs = [
            (config.baseline_version_id, version_id) for version_id in config.compared_version_ids
        ] + [tuple(pair) for pair in config.additional_pairs]
        for left_id, version_id in pairs:
            baseline = by_version.get(left_id)
            other = by_version.get(version_id)
            if baseline is None or other is None:
                comparisons.append(
                    compare_missing(
                        passage_key=passage_key,
                        citation=citation,
                        left_version_id=left_id,
                        right_version_id=version_id,
                    )
                )
                continue
            comparisons.append(
                compare_readings(
                    passage_key=passage_key,
                    citation=citation,
                    left=VersionReading(
                        left_id, baseline, roles.get(left_id, TextRole.PARALLEL_TEXT)
                    ),
                    right=VersionReading(
                        version_id, other, roles.get(version_id, TextRole.PARALLEL_TEXT)
                    ),
                )
            )
    comparisons.sort(
        key=lambda item: (item.passage_key, item.left_version_id, item.right_version_id)
    )
    return ComparisonResult(
        config_sha256=file_sha256(config_path),
        aligned_passages=len(readings),
        comparisons=comparisons,
        readings_per_version=dict(sorted(counts.items())),
        accented_per_version=dict(sorted(accented.items())),
        output_path=config.output_location,
        report_path=config.report_path,
    )


def summarize(
    comparisons: list[TextComparison],
) -> dict[tuple[str, str], Counter[TextComparisonCategory]]:
    summary: dict[tuple[str, str], Counter[TextComparisonCategory]] = {}
    for comparison in comparisons:
        pair = (comparison.left_version_id, comparison.right_version_id)
        summary.setdefault(pair, Counter())[comparison.category] += 1
    return summary
