"""Build and verify the Vajasaneyi Samhita pilot.

    python scripts/build_yajurveda_pilot.py                     # build + verify
    python scripts/build_yajurveda_pilot.py --config other.yaml

This script RUNS ``vedagraph.qa.validate_corpus`` and prints whatever it actually does --
including the exception, if it raises -- and then runs work-agnostic checks of its own, so
the pilot is genuinely verified rather than merely unvalidated.

The second set exists for a reason worth remembering: when this pilot was written,
``qa/checks.py`` hard-coded the Rigvedic Mandala/Sukta/Mantra hierarchy and would raise
``KeyError: 'mandala'`` on any 2-level work, because it dereferenced
``passage.hierarchy["mandala"]`` for every MANTRA record without a guard. Agent F has
since landed a work-agnostic fix that derives legal parent types from ``works.yaml``, and
this build now passes it with 0 issues -- the first non-Rigvedic corpus to do so. The
independent checks are kept as a second opinion rather than removed.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path
from uuid import uuid5

from vedagraph.identity import VEDAGRAPH_NAMESPACE_UUID
from vedagraph.ingest.adapters.yajurveda_pilot import build_pilot
from vedagraph.models import (
    Citation,
    Passage,
    Source,
    SourceAssertion,
    TextVersion,
    TraditionalMetadataAssertion,
)
from vedagraph.models.enums import EntityType
from vedagraph.normalize import normalize_nfc
from vedagraph.storage import read_jsonl

DEFAULT_CONFIG = Path("data/builds/yajurveda_pilot_v1.yaml")


def _load(output: Path):
    return {
        "passages": list(read_jsonl(output / "passages.jsonl", Passage)),
        "texts": list(read_jsonl(output / "text_versions.jsonl", TextVersion)),
        "citations": list(read_jsonl(output / "citations.jsonl", Citation)),
        "sources": list(read_jsonl(output / "sources.jsonl", Source)),
        "metadata": list(
            read_jsonl(output / "traditional_metadata.jsonl", TraditionalMetadataAssertion)
        ),
        "assertions": list(read_jsonl(output / "source_assertions.jsonl", SourceAssertion)),
    }


def verify(output: Path) -> list[str]:
    """Work-agnostic structural checks. Returns failure strings; empty means pass."""
    records = _load(output)
    passages = records["passages"]
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}{(' - ' + detail) if detail else ''}")
        if not ok:
            failures.append(f"{name}: {detail}")

    # G01 unique structural ids
    for label, values in (
        ("canonical_key", [p.canonical_key for p in passages]),
        ("entity_id", [str(p.entity_id) for p in passages]),
        ("canonical_citation", [p.canonical_citation for p in passages]),
        ("canonical_urn", [p.canonical_urn for p in passages]),
    ):
        dupes = [v for v, n in Counter(values).items() if n > 1]
        check(f"G01 unique {label}", not dupes, f"duplicates: {dupes[:5]}")

    # G02 uuid determinism - recompute uuid5(NS, canonical_urn)
    bad = [
        p.canonical_key
        for p in passages
        if uuid5(VEDAGRAPH_NAMESPACE_UUID, p.canonical_urn) != p.entity_id
    ]
    check("G02 uuid5(NS, canonical_urn) == entity_id", not bad, f"mismatched: {bad[:5]}")

    # G03 parent reference integrity
    keys = {p.canonical_key for p in passages}
    orphans = [p.canonical_key for p in passages if p.parent_key and p.parent_key not in keys]
    check("G03 parent_key resolves within build", not orphans, f"orphans: {orphans[:5]}")

    # legal parent type for a 2-level work: MANTRA -> SECTION
    by_key = {p.canonical_key: p for p in passages}
    wrong = [
        p.canonical_key
        for p in passages
        if p.entity_type == EntityType.MANTRA
        and (p.parent_key is None or by_key[p.parent_key].entity_type != EntityType.SECTION)
    ]
    check("G03b mantra parent is the Adhyaya SECTION", not wrong, f"bad: {wrong[:5]}")

    # G04 sequence continuity per parent - gaps are REPORTED, never filled
    children: dict[str, list[int]] = {}
    for p in passages:
        if p.parent_key:
            children.setdefault(p.parent_key, []).append(p.sequence_in_parent)
    gap_report: list[str] = []
    for parent, seqs in sorted(children.items()):
        missing = sorted(set(range(1, max(seqs) + 1)) - set(seqs))
        if missing:
            gap_report.append(f"{parent} missing {missing}")
    check(
        "G04 sequence_in_parent contiguous 1..N",
        not gap_report,
        "; ".join(gap_report) or "",
    )

    # G06/G07 unicode + accent preservation
    not_nfc = [str(t.text_id) for t in records["texts"] if normalize_nfc(t.text_nfc) != t.text_nfc]
    check("G06 text_nfc is NFC-stable", not not_nfc, f"unstable: {len(not_nfc)}")
    bad_hash = [
        str(t.text_id)
        for t in records["texts"]
        if sha256(t.text_nfc.encode("utf-8")).hexdigest() != t.content_sha256
    ]
    check("G06b content_sha256 matches text_nfc", not bad_hash, f"bad: {len(bad_hash)}")
    # text_original must NOT have been replaced by a normalized/derived surface: at least
    # one accented record must still carry tone marks.
    accented = [t for t in records["texts"] if t.accented]
    check(
        "G07 accented readings retain tone marks",
        bool(accented),
        f"accented records: {len(accented)}",
    )
    replaced = [
        str(t.text_id)
        for t in records["texts"]
        if t.accented and normalize_nfc(t.text_original) != t.text_nfc
    ]
    check("G07b text_original preserved (NFC only)", not replaced, f"altered: {len(replaced)}")

    # every canonical mantra must carry Sanskrit
    with_text = {t.passage_id for t in records["texts"] if t.language == "sa"}
    textless = [
        p.canonical_key
        for p in passages
        if p.entity_type == EntityType.MANTRA and p.entity_id not in with_text
    ]
    check("mantras all carry Sanskrit text", not textless, f"textless: {textless[:5]}")

    # referential integrity of metadata and citations
    ids = {p.entity_id for p in passages}
    check(
        "citations target a passage in this build",
        all(c.passage_id in ids for c in records["citations"]),
    )
    check(
        "traditional metadata targets a passage in this build",
        all(m.scope.passage_id in ids for m in records["metadata"]),
    )
    source_ids = {s.source_id for s in records["sources"]}
    check(
        "every text/metadata source is declared",
        all(t.source_id in source_ids for t in records["texts"])
        and all(m.source_id in source_ids for m in records["metadata"]),
    )
    return failures


def run_upstream_qa(output: Path) -> str:
    """Run vedagraph.qa.validate_corpus and report what ACTUALLY happens."""
    from vedagraph.models import AudioRecording, AudioSegment, Translation
    from vedagraph.qa import CorpusRecords, validate_corpus

    records = _load(output)
    try:
        issues = validate_corpus(
            CorpusRecords(
                passages=records["passages"],
                texts=records["texts"],
                translations=list(read_jsonl(output / "translations.jsonl", Translation)),
                metadata=records["metadata"],
                sources=records["sources"],
                citations=records["citations"],
                audio_recordings=list(
                    read_jsonl(output / "audio_recordings.jsonl", AudioRecording)
                ),
                audio_segments=list(read_jsonl(output / "audio_segments.jsonl", AudioSegment)),
                source_assertions=records["assertions"],
            )
        )
    except Exception as error:  # reporting the real failure IS the point here
        return f"RAISED {type(error).__name__}: {error}"
    counts = Counter(f"{i.severity}:{i.check_id}" for i in issues)
    return f"returned {len(issues)} issues: {dict(counts)}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    print(f"=== BUILD 1 from {args.config} ===")
    report = build_pilot(args.config)
    output = report.output_dir
    print(
        f"  adhyayas={report.adhyaya_count} mantras={report.mantra_count} "
        f"passages={report.passage_count} texts={report.text_count} "
        f"citations={report.citation_count} rsi_assertions={report.metadata_count} "
        f"comparisons={report.comparison_count}"
    )
    print(f"  comparison categories: {report.comparison_categories}")
    print(f"  layer divergence: {report.layer_divergence}")
    print(f"  accented collisions: {report.accented_collisions}")
    print(f"  parser failures: {len(report.parser_failures)}")
    for failure in report.parser_failures:
        print(f"    adhyaya {failure['adhyaya']}: {failure['reason']}")
    print("  registry checksum findings:")
    for finding in report.registry_checksum_findings:
        print(f"    {finding['artifact_id']}: {finding['status']}")
    print(f"  computed work structure: {report.computed_work_totals}")
    status = report.primary_text_status
    print(
        f"  PRIMARY_TEXT layer exists: {status.get('has_primary_text_layer')}"
        f" (leading={status.get('leading_layer', status.get('primary'))}"
        f" role={status.get('leading_role', 'PRIMARY_TEXT')})"
    )
    if report.editorial_interventions:
        print("  EDITORIAL INTERVENTIONS (emitted as NEEDS_REVIEW assertions):")
        for item in report.editorial_interventions:
            print(f"    {item['citation']} {item['kind']}: {item['removed'][:60]}")
    if report.unregistered_text_versions:
        print(
            f"  UNREGISTERED text_version_ids (registration requested from Agent E): "
            f"{report.unregistered_text_versions}"
        )
    first_digest = report.generated_content_sha256
    print(f"  generated_content_sha256 = {first_digest}")

    # G10 byte-identical rebuild: snapshot build 1, rebuild, diff every file.
    keep = output.parent / f"{output.name}__build1"
    if keep.exists():
        shutil.rmtree(keep)
    shutil.copytree(output, keep)

    print("\n=== BUILD 2 (rebuild determinism) ===")
    second = build_pilot(args.config)
    print(f"  generated_content_sha256 = {second.generated_content_sha256}")

    differing: list[str] = []
    for path in sorted(keep.glob("*")):
        other = output / path.name
        if not other.exists() or path.read_bytes() != other.read_bytes():
            differing.append(path.name)
    print(
        f"  G10 rebuild byte-identical: {'PASS' if not differing else 'FAIL'}"
        f"{'' if not differing else ' differing=' + str(differing)}"
    )
    shutil.rmtree(keep)

    print("\n=== UPSTREAM vedagraph.qa.validate_corpus ===")
    print(f"  {run_upstream_qa(output)}")

    print("\n=== WORK-AGNOSTIC STRUCTURAL QA ===")
    failures = verify(output)

    print("\n=== RESULT ===")
    ok = not failures and not differing and first_digest == second.generated_content_sha256
    print("  PASS" if ok else f"  FAIL ({len(failures)} check failures)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
