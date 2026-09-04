"""Full-Rigveda composition: config shape, assembly invariants, and generated-data checks.

Everything that needs the generated corpus skips when it is absent, because canonical
output is deliberately excluded from Git.
"""

from collections import Counter
from hashlib import sha256
from pathlib import Path
from uuid import uuid5

import orjson
import pytest
import yaml

from vedagraph.config.registry import load_build_config, load_full_build_config
from vedagraph.full_corpus import (
    _comparison_records,
    _dedupe,
    _passage_key,
    _selected_versions,
    semantic_hashes,
)
from vedagraph.identity import VEDAGRAPH_NAMESPACE_UUID, rv_mantra_identity
from vedagraph.models import CorpusBuildConfig, Passage, TextVersion
from vedagraph.models.enums import (
    EntityType,
    RightsStatus,
    TextComparisonCategory,
    TextForm,
    TextRole,
)

FULL_CONFIG = Path("data/builds/rv_full_v1.yaml")
FULL_OUTPUT = Path("data/canonical/rigveda_full_v1")
MANDALA_1 = Path("data/canonical/rv_mandala_1_full_v1")


def _read(directory: Path, name: str) -> list[dict[str, object]]:
    return [orjson.loads(line) for line in (directory / name).read_bytes().splitlines() if line]


def _require(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} not generated in this checkout")


def test_full_config_composes_exactly_ten_mandala_builds() -> None:
    config = load_full_build_config(FULL_CONFIG)
    components = [load_build_config(path) for path in config.mandala_configs]
    assert sorted(item.mandala for item in components) == list(range(1, 11))
    assert config.expected_mandalas == 10
    assert config.expected_suktas == 1028
    assert config.expected_mantras == 10552


def test_every_mandala_config_pins_the_same_editions() -> None:
    config = load_full_build_config(FULL_CONFIG)
    components = [load_build_config(path) for path in config.mandala_configs]
    assert _selected_versions(components) == ("GRETIL.RV.AUFRECHT", "VEDAWEB.AUFRECHT")


def test_disagreeing_editions_are_refused() -> None:
    config = load_full_build_config(FULL_CONFIG)
    components = [load_build_config(path) for path in config.mandala_configs]
    payload = yaml.safe_load(config.mandala_configs[0].read_text(encoding="utf-8"))
    payload["primary_sanskrit"]["text_version"] = "VEDAWEB.VNH"
    payload["primary_sanskrit"]["role"] = "METRICALLY_RESTORED"
    with pytest.raises(ValueError, match="disagree on editions"):
        _selected_versions([CorpusBuildConfig.model_validate(payload), *components[1:]])


def test_mandala_configs_carry_no_corpus_content() -> None:
    config = load_full_build_config(FULL_CONFIG)
    for path in config.mandala_configs:
        raw = path.read_text(encoding="utf-8")
        assert "text_original" not in raw
        assert not any(ord(char) > 0x0900 for char in raw)


def test_selected_suktas_match_the_expected_shakala_structure() -> None:
    config = load_full_build_config(FULL_CONFIG)
    counts = {
        item.mandala: len(item.selected_suktas)
        for item in (load_build_config(path) for path in config.mandala_configs)
    }
    assert counts == {
        1: 191,
        2: 43,
        3: 62,
        4: 58,
        5: 87,
        6: 75,
        7: 104,
        8: 103,
        9: 114,
        10: 191,
    }
    assert sum(counts.values()) == config.expected_suktas


def test_full_corpus_hierarchy_is_complete_and_well_formed() -> None:
    _require(FULL_OUTPUT / "passages.jsonl")
    passages = _read(FULL_OUTPUT, "passages.jsonl")
    by_key = {row["canonical_key"]: row for row in passages}
    assert len(by_key) == len(passages)
    assert len({row["entity_id"] for row in passages}) == len(passages)
    assert len({row["canonical_citation"] for row in passages}) == len(passages)
    kinds = Counter(row["entity_type"] for row in passages)
    assert kinds["SECTION"] == 10
    assert kinds["HYMN"] == 1028
    assert kinds["MANTRA"] == 10552
    for row in passages:
        parent = row.get("parent_key")
        if parent is None:
            assert row["entity_type"] == "SECTION"
            continue
        assert parent in by_key
        assert by_key[parent]["hierarchy"]["mandala"] == row["hierarchy"]["mandala"]


def test_every_mantra_carries_primary_and_parallel_sanskrit() -> None:
    _require(FULL_OUTPUT / "text_versions.jsonl")
    passages = _read(FULL_OUTPUT, "passages.jsonl")
    texts = _read(FULL_OUTPUT, "text_versions.jsonl")
    mantras = {row["entity_id"] for row in passages if row["entity_type"] == "MANTRA"}
    for role in ("PRIMARY_TEXT", "PARALLEL_TEXT"):
        covered = {row["passage_id"] for row in texts if row["text_role"] == role}
        assert covered >= mantras, f"{role} misses {len(mantras - covered)} mantras"


def test_assembly_reproduces_mandala_1_identities_exactly() -> None:
    _require(FULL_OUTPUT / "passages.jsonl")
    _require(MANDALA_1 / "passages.jsonl")
    fields = ("canonical_key", "canonical_urn", "entity_id", "parent_key", "canonical_citation")

    def identities(rows: list[dict[str, object]]) -> list[tuple[object, ...]]:
        return sorted(
            tuple(row.get(field) for field in fields)
            for row in rows
            if row["hierarchy"]["mandala"] == 1  # type: ignore[index]
        )

    assert identities(_read(FULL_OUTPUT, "passages.jsonl")) == identities(
        _read(MANDALA_1, "passages.jsonl")
    )


def test_full_corpus_reports_zero_qa_errors() -> None:
    _require(FULL_OUTPUT / "qa_issues.jsonl")
    severities = Counter(row["severity"] for row in _read(FULL_OUTPUT, "qa_issues.jsonl"))
    assert severities.get("ERROR", 0) == 0
    assert severities.get("CRITICAL", 0) == 0


def test_stats_agree_with_the_canonical_records() -> None:
    _require(FULL_OUTPUT / "rigveda_stats.json")
    stats = orjson.loads((FULL_OUTPUT / "rigveda_stats.json").read_bytes())
    passages = _read(FULL_OUTPUT, "passages.jsonl")
    assert stats["totals"]["mantras"] == sum(row["entity_type"] == "MANTRA" for row in passages)
    assert stats["totals"]["suktas"] == sum(row["entity_type"] == "HYMN" for row in passages)
    assert len(stats["mandalas"]) == 10


def test_semantic_hashes_cover_content_but_not_qa() -> None:
    """QA output is excluded so a warning-count change cannot look like content drift."""
    _require(FULL_OUTPUT / "passages.jsonl")
    hashes = semantic_hashes(FULL_OUTPUT)
    assert set(hashes) >= {"passages.jsonl", "text_versions.jsonl", "translations.jsonl"}
    assert "qa_issues.jsonl" not in hashes
    assert hashes == semantic_hashes(FULL_OUTPUT)


def test_mandala_1_comparison_classifications_stay_frozen() -> None:
    """The 164 Mandala 1 residuals are a regression baseline, not a moving target."""
    comparisons = FULL_OUTPUT.parent.parent / "derived/rigveda_full_v1/text_comparisons.jsonl"
    _require(comparisons)
    baseline = orjson.loads(
        (Path("tests/fixtures/identity") / "rv_mandala_1_comparison_baseline.json").read_bytes()
    )
    rows = [
        orjson.loads(line)
        for line in comparisons.read_bytes().splitlines()
        if line and orjson.loads(line)["passage_key"].startswith("VG:RV:SAK:M01:")
    ]
    assert len(rows) == baseline["comparison_count"]
    assert dict(sorted(Counter(row["category"] for row in rows).items())) == baseline["categories"]
    residual = sorted(
        row["passage_key"] for row in rows if row["category"] not in {"IDENTICAL", "ACCENT_ONLY"}
    )
    assert len(residual) == baseline["residual_count"]
    assert sha256(orjson.dumps(residual)).hexdigest() == baseline["residual_keys_sha256"]


def _passage(mandala: int, sukta: int, mantra: int) -> Passage:
    key, urn, identifier = rv_mantra_identity(mandala, sukta, mantra)
    return Passage(
        entity_id=identifier,
        entity_type=EntityType.MANTRA,
        work_id="VG:WORK:RV:SAK",
        canonical_key=key,
        canonical_urn=urn,
        canonical_citation=f"RV {mandala}.{sukta}.{mantra}",
        hierarchy={"mandala": mandala, "sukta": sukta, "mantra": mantra},
        sequence_in_parent=mantra,
    )


def _reading(passage: Passage, version: str, role: TextRole, text: str) -> TextVersion:
    return TextVersion(
        text_id=uuid5(VEDAGRAPH_NAMESPACE_UUID, f"{passage.canonical_key}|{version}"),
        passage_id=passage.entity_id,
        language="sa",
        script="Latin",
        text_form=TextForm.SAMHITA,
        text_role=role,
        text_version_id=version,
        text_original=text,
        text_nfc=text,
        accented=True,
        source_id="TEST",
        source_locator=passage.canonical_citation,
        content_sha256="0" * 64,
        rights_status=RightsStatus.CC_BY_NC_SA,
    )


def test_duplicate_records_that_actually_conflict_are_refused() -> None:
    """Two Mandala builds emitting different rows for one id must fail, not pick a winner."""
    passage = _passage(1, 1, 1)
    first = _reading(passage, "GRETIL.RV.AUFRECHT", TextRole.PRIMARY_TEXT, "agním")
    same = first.model_copy(deep=True)
    different = first.model_copy(update={"text_original": "agnim"})
    assert _dedupe([first, same], "text_id") == [first]
    with pytest.raises(ValueError, match="conflicting duplicate"):
        _dedupe([first, different], "text_id")


def test_comparison_pairs_the_configured_editions_and_flags_a_missing_side() -> None:
    paired, unpaired = _passage(1, 1, 1), _passage(1, 1, 2)
    texts = [
        _reading(paired, "GRETIL.RV.AUFRECHT", TextRole.PRIMARY_TEXT, "agním"),
        _reading(paired, "VEDAWEB.AUFRECHT", TextRole.PARALLEL_TEXT, "agním"),
        _reading(unpaired, "GRETIL.RV.AUFRECHT", TextRole.PRIMARY_TEXT, "íḷe"),
        # A version nobody selected must not stand in for the parallel reading.
        _reading(unpaired, "VEDAWEB.VNH", TextRole.METRICALLY_RESTORED, "íḷe"),
    ]
    results = _comparison_records(
        [paired, unpaired], texts, "GRETIL.RV.AUFRECHT", "VEDAWEB.AUFRECHT"
    )
    assert [item.passage_key for item in results] == [
        paired.canonical_key,
        unpaired.canonical_key,
    ]
    assert results[0].category is TextComparisonCategory.IDENTICAL
    assert results[1].category is TextComparisonCategory.MISSING


def test_passages_sort_by_citation_hierarchy_not_by_string() -> None:
    """Sukta 10 must follow Sukta 2, and every child must follow its Mandala."""
    passages = [_passage(1, 10, 1), _passage(1, 2, 1), _passage(2, 1, 1), _passage(1, 2, 10)]
    assert [_passage_key(item) for item in sorted(passages, key=_passage_key)] == [
        (1, 2, 1, 2),
        (1, 2, 10, 2),
        (1, 10, 1, 2),
        (2, 1, 1, 2),
    ]
