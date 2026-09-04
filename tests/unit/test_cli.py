from pathlib import Path

import pytest
from typer.testing import CliRunner

from vedagraph.cli.app import app
from vedagraph.identity import rv_mandala_identity, rv_mantra_identity, rv_sukta_identity
from vedagraph.models import Passage
from vedagraph.models.enums import EntityType
from vedagraph.storage import write_jsonl

runner = CliRunner()


def test_source_artifacts_and_structural_stats_commands(tmp_path: Path) -> None:
    artifacts = runner.invoke(app, ["source", "artifacts"])
    assert artifacts.exit_code == 0
    assert "GRETIL" in artifacts.stdout
    assert "CC_BY_NC_SA" in artifacts.stdout

    mandala_key, mandala_urn, mandala_id = rv_mandala_identity(1)
    sukta_key, sukta_urn, sukta_id = rv_sukta_identity(1, 1)
    mantra_key, mantra_urn, mantra_id = rv_mantra_identity(1, 1, 1)
    passages = [
        Passage(
            entity_id=mandala_id,
            canonical_key=mandala_key,
            canonical_urn=mandala_urn,
            entity_type=EntityType.SECTION,
            work_id="VG:WORK:RV:SAK",
            hierarchy={"mandala": 1},
            canonical_citation="RV 1",
            sequence_in_parent=1,
        ),
        Passage(
            entity_id=sukta_id,
            canonical_key=sukta_key,
            canonical_urn=sukta_urn,
            entity_type=EntityType.HYMN,
            work_id="VG:WORK:RV:SAK",
            hierarchy={"mandala": 1, "sukta": 1},
            canonical_citation="RV 1.1",
            parent_key=mandala_key,
            sequence_in_parent=1,
        ),
        Passage(
            entity_id=mantra_id,
            canonical_key=mantra_key,
            canonical_urn=mantra_urn,
            entity_type=EntityType.MANTRA,
            work_id="VG:WORK:RV:SAK",
            hierarchy={"mandala": 1, "sukta": 1, "mantra": 1},
            canonical_citation="RV 1.1.1",
            parent_key=sukta_key,
            sequence_in_parent=1,
        ),
    ]
    passages_file = tmp_path / "passages.jsonl"
    write_jsonl(passages_file, passages)
    stats = runner.invoke(
        app,
        [
            "corpus",
            "stats",
            "--passages-file",
            str(passages_file),
        ],
    )
    assert stats.exit_code == 0
    assert "STRUCTURAL NODES" in stats.stdout
    assert "mandalas: 1" in stats.stdout
    assert "suktas: 1" in stats.stdout
    assert "TEXTUAL OCCURRENCES" in stats.stdout
    assert "mantras: 1" in stats.stdout


def test_knowledge_entities_command_reads_the_committed_registries() -> None:
    result = runner.invoke(app, ["knowledge", "entities", "--entity-type", "CHANDAS"])
    assert result.exit_code == 0
    assert "VG:CHANDAS:GAYATRI" in result.stdout


def test_knowledge_commands_are_registered() -> None:
    result = runner.invoke(app, ["knowledge", "--help"])
    assert result.exit_code == 0
    for command in ("stats", "mantras", "entities"):
        assert command in result.stdout


def test_knowledge_mantras_answers_from_deterministic_assertions() -> None:
    knowledge = Path("data/knowledge/rigveda_deterministic_v1/knowledge_assertions.jsonl")
    if not knowledge.exists():
        pytest.skip("knowledge layer not generated")
    result = runner.invoke(
        app,
        ["knowledge", "mantras", "VG:DEVATA:AGNIH", "--predicate", "HAS_DEVATA", "--limit", "3"],
    )
    assert result.exit_code == 0
    assert "RV 1.1.1" in result.stdout
    assert "mantra assignments for VG:DEVATA:AGNIH" in result.stdout
