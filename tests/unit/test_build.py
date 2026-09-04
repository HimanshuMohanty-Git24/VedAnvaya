from hashlib import sha256
from pathlib import Path

import orjson
import yaml

from vedagraph.build import build_from_config, stage_from_config
from vedagraph.models import CorpusManifest, Passage, QAIssue, TextVersion, Translation
from vedagraph.models.enums import EntityType, QASeverity, TextRole, TranslationAlignment
from vedagraph.storage import read_jsonl

FIXTURES = Path("tests/fixtures").resolve()


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _config(tmp_path: Path, *, include_parallel_sanskrit: bool = False) -> Path:
    gretil = FIXTURES / "gretil/rv_sample.xml"
    wiki = FIXTURES / "wikisource/rv_1_1_api.json"
    revision = FIXTURES / "wikisource/rv_1_1_revision.json"
    vhp = FIXTURES / "vhp_rv_1_1.html"
    sources = [
        {
            "source_id": "GRETIL",
            "role": "sanskrit",
            "scope": "RV.1",
            "snapshot_path": str(gretil),
            "snapshot_id": "GRETIL:fixture",
            "snapshot_sha256": _sha(gretil),
            "source_artifact_id": "GRETIL.RV.AUFRECHT.TEI.2019",
            "parser_version": "gretil-rigveda-tei-v2",
        },
        {
            "source_id": "WIKISOURCE_GRIFFITH_RV",
            "role": "translation",
            "scope": "RV.1.1",
            "snapshot_path": str(wiki),
            "snapshot_id": "WIKI:fixture",
            "snapshot_sha256": _sha(wiki),
            "source_artifact_id": "GRIFFITH.RV.1896.WIKISOURCE",
            "parser_version": "wikisource-griffith-v2",
        },
        {
            "source_id": "WIKISOURCE_GRIFFITH_RV",
            "role": "translation_revision",
            "scope": "RV.1.1",
            "snapshot_path": str(revision),
            "snapshot_id": "WIKI-REV:fixture",
            "snapshot_sha256": _sha(revision),
            "source_artifact_id": "GRIFFITH.RV.1896.WIKISOURCE",
            "parser_version": "mediawiki-revision-v1",
        },
        {
            "source_id": "VHP",
            "role": "discovery",
            "scope": "RV.1",
            "snapshot_path": str(vhp),
            "snapshot_id": "VHP:fixture",
            "snapshot_sha256": _sha(vhp),
            "source_artifact_id": "VHP.RV.SHAKALA.MANDALA1.WEB",
            "parser_version": "vhp-rigveda-v2",
        },
        {
            "source_id": "VHP",
            "role": "metadata",
            "scope": "RV.1.1",
            "snapshot_path": str(vhp),
            "snapshot_id": "VHP:fixture",
            "snapshot_sha256": _sha(vhp),
            "source_artifact_id": "VHP.RV.SHAKALA.MANDALA1.WEB",
            "parser_version": "vhp-rigveda-v2",
        },
    ]
    primary_sanskrit = None
    parallel_sanskrit: list[dict[str, str]] = []
    if include_parallel_sanskrit:
        vedaweb = FIXTURES / "vedaweb/rv_book_01_sample.tei"
        sources.append(
            {
                "source_id": "VEDAWEB",
                "role": "sanskrit_parallel",
                "scope": "RV.1",
                "snapshot_path": str(vedaweb),
                "snapshot_id": "VEDAWEB:fixture",
                "snapshot_sha256": _sha(vedaweb),
                "source_artifact_id": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
                "parser_version": "vedaweb-rigveda-tei-v1",
            }
        )
        primary_sanskrit = {
            "artifact": "GRETIL.RV.AUFRECHT.TEI.2019",
            "text_version": "GRETIL.RV.AUFRECHT",
            "role": "PRIMARY_TEXT",
        }
        parallel_sanskrit = [
            {
                "artifact": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
                "text_version": "VEDAWEB.AUFRECHT",
                "role": "PARALLEL_TEXT",
            }
        ]
    payload = {
        "config_version": "1.0.0",
        "dataset_id": "test_rv_sample",
        "release_version": "test.1",
        "work_id": "VG:WORK:RV:SAK",
        "mandala": 1,
        "selected_suktas": [1],
        "text_selection_policy": "ORIGINAL",
        "primary_sanskrit": primary_sanskrit,
        "parallel_sanskrit": parallel_sanskrit,
        "sources": sources,
        "translation_sources": ["WIKISOURCE_GRIFFITH_RV"],
        "metadata_sources": ["VHP"],
        "media_discovery_sources": ["VHP"],
        "reconciliation_policy_version": "rv-mandala-1-v1",
        "output_location": str(tmp_path / "data/canonical/test_rv_sample"),
        "staging_location": str(tmp_path / "data/staged/test_rv_sample"),
        "build_timestamp": "2026-09-04T00:00:00+05:30",
    }
    path = tmp_path / "build.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_staging_and_reproducible_build(tmp_path: Path) -> None:
    config = _config(tmp_path)
    staged = stage_from_config(config)
    assert staged.text_count == 2
    assert staged.translation_count == 2
    assert (staged.staged_dir / "source_assertions.jsonl").exists()

    first = build_from_config(config)
    first_bytes = {
        path.name: path.read_bytes()
        for path in sorted(first.output_dir.iterdir())
        if path.is_file()
    }
    second = build_from_config(config)
    second_bytes = {
        path.name: path.read_bytes()
        for path in sorted(second.output_dir.iterdir())
        if path.is_file()
    }
    assert first_bytes == second_bytes

    passages = list(read_jsonl(first.output_dir / "passages.jsonl", Passage))
    assert sum(item.entity_type == EntityType.SECTION for item in passages) == 1
    assert sum(item.entity_type == EntityType.HYMN for item in passages) == 1
    assert sum(item.entity_type == EntityType.MANTRA for item in passages) == 2
    translations = list(read_jsonl(first.output_dir / "translations.jsonl", Translation))
    assert all(
        item.alignment == TranslationAlignment.EXACT_MANTRA_ALIGNMENT for item in translations
    )
    assert translations[0].source_revision_id == 987654321
    assert translations[0].source_revision_timestamp is not None
    manifest = CorpusManifest.model_validate_json(first.manifest_path.read_bytes())
    assert manifest.build_config_sha256 == _sha(config)
    assert manifest.source_artifact_ids == [
        "GRETIL.RV.AUFRECHT.TEI.2019",
        "GRIFFITH.RV.1896.WIKISOURCE",
        "VHP.RV.SHAKALA.MANDALA1.WEB",
    ]


def test_parallel_sanskrit_attaches_to_the_primary_passage_and_flags_divergence(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path, include_parallel_sanskrit=True)
    result = build_from_config(config)

    texts = list(read_jsonl(result.output_dir / "text_versions.jsonl", TextVersion))
    by_role: dict[TextRole, list[TextVersion]] = {}
    for text in texts:
        by_role.setdefault(text.text_role, []).append(text)
    primary = by_role[TextRole.PRIMARY_TEXT]
    parallel = by_role[TextRole.PARALLEL_TEXT]
    assert len(primary) == 2
    assert len(parallel) == 2
    # Same textual occurrence, same passage: no second passage was minted for the
    # parallel reading.
    assert {t.passage_id for t in primary} == {t.passage_id for t in parallel}
    assert all(t.text_version_id == "GRETIL.RV.AUFRECHT" for t in primary)
    assert all(t.text_version_id == "VEDAWEB.AUFRECHT" for t in parallel)

    # The GRETIL fixture text is a deliberately truncated stanza, so it cannot match
    # the fuller VedaWeb reading beyond accent/notation: the divergence QA policy must
    # flag it rather than silently accept it.
    issues = list(read_jsonl(result.output_dir / "qa_issues.jsonl", QAIssue))
    divergences = [i for i in issues if i.check_id == "primary_parallel_text_divergence"]
    assert divergences
    assert all(i.severity in (QASeverity.WARNING, QASeverity.ERROR) for i in divergences)


def test_unparseable_translation_page_is_a_warning_not_a_crash(tmp_path: Path) -> None:
    broken_wiki = tmp_path / "broken_wikisource.json"
    broken_wiki.write_text(
        orjson.dumps(
            {
                "parse": {
                    "title": "The Hymns of the Rigveda/Book 1/Hymn 1",
                    "pageid": 1,
                    "revid": 1,
                    "text": {"*": "<div class='mw-parser-output'>no poem markup here</div>"},
                }
            }
        ).decode("utf-8"),
        encoding="utf-8",
    )
    config = _config(tmp_path)
    payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    for source in payload["sources"]:
        if source["role"] == "translation":
            source["snapshot_path"] = str(broken_wiki)
            source["snapshot_sha256"] = _sha(broken_wiki)
    config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    result = build_from_config(config)  # must not raise
    translations = list(read_jsonl(result.output_dir / "translations.jsonl", Translation))
    assert translations == []
    issues = list(read_jsonl(result.output_dir / "qa_issues.jsonl", QAIssue))
    failures = [i for i in issues if i.check_id == "translation_page_parse_failed"]
    assert len(failures) == 1
    assert failures[0].severity == QASeverity.WARNING
    assert failures[0].entity_id == "RV.1.1"


def test_passage_identity_is_stable_when_the_build_scope_grows(tmp_path: Path) -> None:
    """A passage's identity must depend only on its own citation, never on which other
    Suktas happen to be selected in the same build — this is what lets a later full
    build add Suktas 2-191 without disturbing anything already built for Sukta 1."""
    two_suktas = FIXTURES / "gretil/rv_sample_two_suktas.xml"
    small_config = _config(tmp_path)
    payload = yaml.safe_load(small_config.read_text(encoding="utf-8"))
    payload["dataset_id"] = "small_scope"
    payload["output_location"] = str(tmp_path / "small")
    payload["staging_location"] = str(tmp_path / "small_staged")
    small_config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    small = build_from_config(small_config)

    grown_config = tmp_path / "grown.yaml"
    payload["dataset_id"] = "grown_scope"
    payload["selected_suktas"] = [1, 2]
    payload["output_location"] = str(tmp_path / "grown")
    payload["staging_location"] = str(tmp_path / "grown_staged")
    for source in payload["sources"]:
        if source["role"] == "sanskrit":
            source["snapshot_path"] = str(two_suktas)
            source["snapshot_sha256"] = _sha(two_suktas)
    grown_config.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    grown = build_from_config(grown_config)

    def by_citation(output_dir: Path) -> dict[str, Passage]:
        return {p.canonical_citation: p for p in read_jsonl(output_dir / "passages.jsonl", Passage)}

    small_passages = by_citation(small.output_dir)
    grown_passages = by_citation(grown.output_dir)
    assert len(grown_passages) > len(small_passages)  # Sukta 2 really was added
    for citation, old_passage in small_passages.items():
        new_passage = grown_passages[citation]
        assert new_passage.entity_id == old_passage.entity_id
        assert new_passage.canonical_key == old_passage.canonical_key
        assert new_passage.canonical_urn == old_passage.canonical_urn
        assert new_passage.parent_key == old_passage.parent_key
        assert new_passage.canonical_citation == old_passage.canonical_citation
