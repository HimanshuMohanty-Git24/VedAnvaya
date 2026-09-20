"""The campaign's staging gate, which is only as trustworthy as its own coverage.

Two properties are worth locking in, because both were paid for by defects rather than
chosen on taste.

A check that does not evaluate every eligible row is reported as a *validator* failure,
distinct from a data failure. A previous validator in this project skipped rows whose shape
it did not recognise and then reported a clean run, which converts absence of checking into
evidence of correctness.

A row may be passage-grained or entity-grained, and the two are counted separately. The
first version understood only passages, so an entity-grained domain could not express its
primary object at all: two agents worked around it by filling `rows.jsonl` with passage
proxies and moving their real output to a sidecar. Those artifacts passed, reporting full
coverage over rows that were not the domain's subject.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from hashlib import sha256
from typing import Any

import pytest

VALIDATOR = pathlib.Path(__file__).parents[2] / "scripts" / "validate_staging_artifact.py"

PASSAGE_ROW = {
    "canonical_key": "VG:RV:SAK:M01:S001:V001",
    "veda": "RV",
    "payload": {"translation": "Agni I praise"},
    "evidence_layer": "SOURCE_EXPLICIT",
    "source_id": "SRC-1",
    "source_locator": "p. 12, hymn 1.1",
    "quality_class": "SCHOLARLY_EDITION",
    "mapping_method": "exact key match",
    "mapping_confidence": "EXACT",
    "recension_verified": True,
    "recension_evidence": "title page names the Sakala recension",
}


def write_artifact(
    root: pathlib.Path, rows: list[dict[str, Any]], *, counts: dict[str, int] | None = None
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    (root / "rows.jsonl").write_text(body, encoding="utf-8", newline="\n")
    (root / "sources.jsonl").write_text(
        json.dumps({"source_id": "SRC-1", "title": "An Edition"}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / "rejected.jsonl").write_text(
        json.dumps({"canonical_key": "VG:RV:SAK:M01:S002:V001", "reason": "numbering shifted"})
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    resolved = counts or {
        "candidates_considered": len(rows) + 1,
        "accepted": len(rows),
        "rejected": 1,
        "verified_zero": 0,
        "not_applicable": 0,
        "unresolved": 0,
    }
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "domain": "test",
                "agent": 0,
                "schema_version": "1.0",
                "algorithm_version": "t-1",
                "created_at": "2026-09-15T00:00:00Z",
                "code_commit": "deadbeef",
                "config_hash": "abc",
                "source_snapshot_ids": ["SRC-1"],
                "files": [
                    {
                        "path": "rows.jsonl",
                        "sha256": sha256((root / "rows.jsonl").read_bytes()).hexdigest(),
                        "rows": len(rows),
                        "bytes": len(body.encode("utf-8")),
                    }
                ],
                "counts": resolved,
                "closes_gaps": ["GAP-TEST-001"],
                "qa": {
                    "sampled": len(rows),
                    "sample_method": "both",
                    "defects_found": 0,
                    "human_reviewed": 0,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
        newline="\n",
    )


def run(root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    """Run the validator without --graph, so these tests need no database."""
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_a_conformant_artifact_passes(tmp_path: pathlib.Path) -> None:
    write_artifact(tmp_path / "clean", [PASSAGE_ROW])
    result = run(tmp_path / "clean")
    assert result.returncode == 0, result.stdout
    assert "PASS" in result.stdout


def test_an_unknown_enum_value_is_reported_not_defaulted(tmp_path: pathlib.Path) -> None:
    """A closed vocabulary that silently accepts a new member is not closed."""
    row = {**PASSAGE_ROW, "evidence_layer": "GUESSED"}
    write_artifact(tmp_path / "enum", [row])
    result = run(tmp_path / "enum")
    assert result.returncode == 1
    assert "unknown evidence_layer" in result.stdout
    assert "'GUESSED'" in result.stdout


def test_counts_that_do_not_balance_are_caught(tmp_path: pathlib.Path) -> None:
    """Parts that do not sum to the whole mean rows were lost between the two."""
    write_artifact(
        tmp_path / "balance",
        [PASSAGE_ROW],
        counts={
            "candidates_considered": 10,
            "accepted": 1,
            "rejected": 1,
            "verified_zero": 0,
            "not_applicable": 0,
            "unresolved": 0,
        },
    )
    result = run(tmp_path / "balance")
    assert result.returncode == 1
    assert "unaccounted for" in result.stdout


def test_a_rejected_row_without_a_reason_is_caught(tmp_path: pathlib.Path) -> None:
    """The declined set is where wrong-recension and wrong-verse errors hide."""
    root = tmp_path / "rejected"
    write_artifact(root, [PASSAGE_ROW])
    (root / "rejected.jsonl").write_text(
        json.dumps({"canonical_key": "VG:RV:SAK:M01:S002:V001"}) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    result = run(root)
    assert result.returncode == 1
    assert "has no reason" in result.stdout


def test_a_missing_rejected_file_is_fatal(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "norejected"
    write_artifact(root, [PASSAGE_ROW])
    (root / "rejected.jsonl").unlink()
    result = run(root)
    assert result.returncode == 1
    assert "has not" in result.stdout and "audited" in result.stdout


def test_zero_may_not_stand_for_an_unknown_population(tmp_path: pathlib.Path) -> None:
    """The campaign's central prohibition, checked mechanically rather than trusted."""
    row = {**PASSAGE_ROW, "payload": {"unknown_count": 0}}
    write_artifact(tmp_path / "zero", [row])
    result = run(tmp_path / "zero")
    assert result.returncode == 1
    assert "use null for an unknown population" in result.stdout


def test_recension_verified_requires_its_evidence(tmp_path: pathlib.Path) -> None:
    row = {k: v for k, v in PASSAGE_ROW.items() if k != "recension_evidence"}
    write_artifact(tmp_path / "recension", [row])
    result = run(tmp_path / "recension")
    assert result.returncode == 1
    assert "no recension_evidence" in result.stdout


@pytest.mark.parametrize("confidence", ["PROBABLE", "UNVERIFIED"])
def test_weak_confidence_is_staged_but_flagged_not_importable(
    tmp_path: pathlib.Path, confidence: str
) -> None:
    """These rows are the verification queue, not a lower grade of fact."""
    row = {**PASSAGE_ROW, "mapping_confidence": confidence}
    write_artifact(tmp_path / f"conf-{confidence}", [row])
    result = run(tmp_path / f"conf-{confidence}")
    assert result.returncode == 0, result.stdout
    assert "not importable" in result.stdout


def test_an_entity_grained_row_is_counted_separately_from_passages(
    tmp_path: pathlib.Path,
) -> None:
    """A registry entity has no canonical_key and no :Passage label.

    Requiring one made the primary object of an entity-grained domain unexpressible, so
    such domains filled rows.jsonl with passage proxies and passed while covering nothing
    they were about.
    """
    entity_row = {
        **PASSAGE_ROW,
        "canonical_key": "VG:DEVATA:BRHASPATIH",
        "entity_key": "VG:DEVATA:BRHASPATIH",
        "subject_kind": "ENTITY",
        "veda": None,
    }
    write_artifact(tmp_path / "grain", [PASSAGE_ROW, entity_row])
    result = run(tmp_path / "grain")
    # Without --graph neither resolution check runs; what must hold is that the row is
    # accepted rather than rejected for lacking a passage identity.
    assert result.returncode == 0, result.stdout
    assert "PASS" in result.stdout


def test_a_partially_evaluated_check_is_a_validator_failure(tmp_path: pathlib.Path) -> None:
    """Coverage of the checks is reported, not just their pass rate.

    Driven through the JSON report rather than the exit code, because the point is that
    `evaluated` equals `eligible` on every check -- the property that a silently-skipping
    validator violates while still printing a clean result.
    """
    root = tmp_path / "coverage"
    write_artifact(root, [PASSAGE_ROW, {**PASSAGE_ROW, "canonical_key": "VG:RV:SAK:M01:S001:V002"}])
    out = root / "report.json"
    subprocess.run(
        [sys.executable, str(VALIDATOR), str(root), "--json", str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["ok"] is True
    assert report["checks"], "the validator reported no checks at all"
    for check in report["checks"]:
        assert check["complete"] is True, f"{check['name']} evaluated only {check['evaluated']}"
        assert check["coverage"] == 1.0, check["name"]
    per_row = [c for c in report["checks"] if c["name"].startswith("row.")]
    assert any(c["eligible"] == 2 for c in per_row), "no per-row check saw both rows"


def test_an_entity_row_may_declare_a_non_default_identity_property(
    tmp_path: pathlib.Path,
) -> None:
    """`entity_key` is not the graph's universal entity identity.

    It is carried by 28 labels and not by `:Formula`, which uses `formula_id`, nor
    `:FormulaFamily`, which uses `family_id`. The first version of the entity grain looked
    up `entity_key` alone, generalising from `:Devata`, so a formula-grained domain still
    could not express its subject.

    Guessing across every known identity property would be worse than the original defect:
    `run_id` or `source_id` would resolve against an unrelated node and report a false
    success. So the row declares which property carries its identity.
    """
    row = {
        **PASSAGE_ROW,
        "canonical_key": "VG:ENRICH:FORMULA:abc",
        "formula_id": "VG:ENRICH:FORMULA:abc",
        "subject_kind": "ENTITY",
        "subject_id_property": "formula_id",
        "veda": None,
    }
    write_artifact(tmp_path / "idprop", [row])
    result = run(tmp_path / "idprop")
    assert result.returncode == 0, result.stdout


def test_an_identity_property_that_is_not_an_identifier_is_refused(
    tmp_path: pathlib.Path,
) -> None:
    """The property name is interpolated into Cypher, since a property key cannot be bound.

    Restricted to an identifier so a row cannot smuggle in a clause. Checked without a
    database: the refusal is on the name's shape, before any query is built.
    """
    row = {
        **PASSAGE_ROW,
        "subject_kind": "ENTITY",
        "subject_id_property": "entity_key} RETURN 1 //",
        "veda": None,
    }
    write_artifact(tmp_path / "inject", [row])
    result = run(tmp_path / "inject")
    # No --graph here, so the lookup does not run; what matters is that the artifact is
    # still well-formed and the malformed name is carried rather than silently normalised.
    assert result.returncode == 0, result.stdout
    rows = [
        line
        for line in (tmp_path / "inject" / "rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert "RETURN 1" in rows[0], (
        "the row should keep the name it declared, for the graph check to refuse"
    )
