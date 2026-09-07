"""Classify the pre-correction semantic runs. Reads the artefacts; changes none of them.

The readiness audit established that the producer behind the V2 and V3 runs was
deterministic Python, not ``gpt-5.6-luna``. The artefacts stay exactly as sealed — they
are still the best available fixtures for the typed-object schema, the normalization
layer, the evidence validators and the batch machinery — but their model field is wrong
about who wrote them, and no report may cite them as evidence about Luna.

This writes a registry recording that, and a human-readable report beside it. It never
opens an artefact for writing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SEMANTIC = Path("data/semantic")
MANIFEST = Path("docs/manifests/rigveda_semantic_historical_artifacts.json")
REPORT = Path("docs/reports/RIGVEDA_SEMANTIC_HISTORICAL_ARTIFACT_REGISTRY.md")

CLASSIFICATION = "HISTORICAL_HEURISTIC_ARTIFACT"

PERMITTED_USES = [
    "typed semantic object schema testing",
    "normalization and comparison architecture testing",
    "evidence validator regression fixtures",
    "operational rehearsal of batching, custody, recovery and seal",
    "deterministic replay fixtures",
]
FORBIDDEN_USES = [
    "evidence of gpt-5.6-luna accuracy",
    "evidence of gpt-5.6-luna stability or replication",
    "any statement about model behaviour, determinism or agreement",
    "input to a run whose provenance claims a model authored it",
]

#: run directory -> the script that actually authored its payloads.
PRODUCERS = {
    "vedagraph-rigveda-semantic-luna-v2-120": "scripts/author_semantic_luna_v2_payloads.py",
    "vedagraph-rigveda-semantic-luna-v3-120": "scripts/author_semantic_luna_v3_payloads.py",
    "vedagraph-rigveda-semantic-luna-v3-replication-120": (
        "scripts/run_semantic_luna_v3_replication.py"
    ),
    "vedagraph-rigveda-semantic-luna-v3-508": "scripts/run_semantic_luna_v3_508.py",
    "vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1": (
        "scripts/author_codex_direct_payloads.py"
    ),
}

NOTES = {
    "vedagraph-rigveda-semantic-luna-v3-replication-120": (
        "Its agreement with the 120 pilot demonstrates deterministic pipeline replay, not "
        "model replication stability: the same regular expressions were run twice."
    ),
    "vedagraph-rigveda-semantic-luna-v3-508": (
        "Carries the fourteen audited substring anchors (B02) and the relation-scope "
        "failures (B01). Both are now refused by the current validators."
    ),
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seals(directory: Path) -> dict[str, str]:
    return {
        path.name: file_sha256(path)
        for path in sorted(directory.glob("*seal*.json"))
        if path.is_file()
    }


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def main() -> None:
    records = []
    for run_id, producer in sorted(PRODUCERS.items()):
        directory = SEMANTIC / run_id
        if not directory.is_dir():
            continue
        records.append(
            {
                "run_id": run_id,
                "path": directory.as_posix(),
                "classification": CLASSIFICATION,
                "producer": producer,
                "producer_kind": "DETERMINISTIC_HEURISTIC_BASELINE",
                "declared_model_in_artifact": "gpt-5.6-luna",
                "declared_model_is_accurate": False,
                "artifact_mutated_by_this_registry": False,
                "seal_hashes": _seals(directory),
                "extraction_row_count": _count_lines(directory / "v3_extractions.jsonl"),
                "permitted_uses": PERMITTED_USES,
                "forbidden_uses": FORBIDDEN_USES,
                "note": NOTES.get(run_id, ""),
            }
        )
    payload = {
        "registry_version": "rigveda-semantic-historical-artifact-registry-v1",
        "classification": CLASSIFICATION,
        "correction_document": "docs/architecture/SEMANTIC_V3_PROVENANCE_CORRECTION.md",
        "artifacts_preserved_unmodified": True,
        "runs": records,
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    rows = "\n".join(
        f"| {item['run_id']} | `{item['producer']}` | {CLASSIFICATION} | "
        f"{item['extraction_row_count']} | {item['note']} |"
        for item in records
    )
    REPORT.write_text(
        f"""# Historical semantic artifact registry

Engineering classification, not Vedic expertise, HUMAN_GOLD, or canonical truth. No artefact
was altered, relabelled or deleted. All existing output stays CANDIDATE / NEEDS_REVIEW;
unlocked_predicates = []. No extraction was performed.

## Classification

Every run below is `{CLASSIFICATION}`. Its payloads were authored by deterministic Python,
not by `gpt-5.6-luna`, even though the sealed records say otherwise in their model field.
That field is wrong and is left wrong: rewriting a sealed artefact to fix a label would
destroy the only record of what was actually produced. The correction is prospective and is
stated in `docs/architecture/SEMANTIC_V3_PROVENANCE_CORRECTION.md`.

| Run | Producer | Classification | Extraction rows | Note |
| --- | --- | --- | --- | --- |
{rows}

## What these artefacts are still good for

{chr(10).join(f"- {use}" for use in PERMITTED_USES)}

## What they may never be cited as

{chr(10).join(f"- {use}" for use in FORBIDDEN_USES)}

Two of these runs agree with each other exactly. That is deterministic pipeline replay: the
same regular expressions over the same packets. It is not evidence that a model is stable,
and no report may present it as such.

The registry itself is regenerated by `scripts/classify_historical_semantic_artifacts.py`,
which opens artefacts read-only and hashes their seals so that a later silent edit would be
detectable.
""",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{len(records)} runs classified as {CLASSIFICATION}")
    print(f"{MANIFEST}\n{REPORT}")


if __name__ == "__main__":
    main()
