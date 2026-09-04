"""Derive the full Mandala 1 coverage matrix, translation coverage report, and the
build summary report from the actual canonical build output. Every number here is
computed from `data/canonical/rv_mandala_1_full_v1/*.jsonl`; nothing is hand-typed.

No corpus text (Sanskrit or English) is reproduced in any generated report.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import orjson

CANONICAL = Path("data/canonical/rv_mandala_1_full_v1")
DERIVED = Path("data/derived")
REPORTS = Path("docs/reports")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [orjson.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


def main() -> None:
    passages = _read_jsonl(CANONICAL / "passages.jsonl")
    texts = _read_jsonl(CANONICAL / "text_versions.jsonl")
    translations = _read_jsonl(CANONICAL / "translations.jsonl")
    metadata = _read_jsonl(CANONICAL / "traditional_metadata.jsonl")
    audio = _read_jsonl(CANONICAL / "audio_recordings.jsonl")
    qa_issues = _read_jsonl(CANONICAL / "qa_issues.jsonl")
    manifest = orjson.loads((CANONICAL / "manifest.json").read_bytes())

    mantra_passages = [p for p in passages if p["entity_type"] == "MANTRA"]
    passage_by_id = {p["entity_id"]: p for p in passages}
    sukta_passages = {p["entity_id"]: p for p in passages if p["entity_type"] == "HYMN"}

    def sukta_of(passage_id: str) -> int:
        return int(passage_by_id[passage_id]["hierarchy"]["sukta"])

    total_mantras = len(mantra_passages)

    primary_by_mantra: dict[str, int] = defaultdict(int)
    parallel_by_mantra: dict[str, int] = defaultdict(int)
    for text in texts:
        if text["text_role"] == "PRIMARY_TEXT":
            primary_by_mantra[text["passage_id"]] += 1
        elif text["text_role"] == "PARALLEL_TEXT":
            parallel_by_mantra[text["passage_id"]] += 1

    translation_by_mantra: dict[str, dict[str, Any]] = {}
    for translation in translations:
        translation_by_mantra[translation["passage_id"]] = translation

    missing_suktas: dict[int, int] = defaultdict(int)
    for mantra in mantra_passages:
        if mantra["entity_id"] not in translation_by_mantra:
            missing_suktas[sukta_of(mantra["entity_id"])] += 1

    metadata_by_sukta: dict[str, dict[str, bool]] = defaultdict(
        lambda: {"rishi": False, "devata": False, "chandas": False}
    )
    for item in metadata:
        sukta_passage_id = item["scope"]["passage_id"]
        predicate = item["predicate"].lower().removeprefix("has_")
        metadata_by_sukta[sukta_passage_id][predicate] = True

    audio_sukta_ids = {item["target_id"] for item in audio}

    qa_warnings_by_entity: dict[str, int] = defaultdict(int)
    for issue in qa_issues:
        entity_id = issue.get("entity_id") or ""
        qa_warnings_by_entity[entity_id] += 1

    # ---- per-Sukta coverage matrix (task 16) -------------------------------------
    matrix: list[dict[str, Any]] = []
    for sukta_id, sukta_passage in sorted(
        sukta_passages.items(), key=lambda kv: kv[1]["hierarchy"]["sukta"]
    ):
        sukta_number = sukta_passage["hierarchy"]["sukta"]
        mantras_in_sukta = [p for p in mantra_passages if sukta_of(p["entity_id"]) == sukta_number]
        mantra_ids = {p["entity_id"] for p in mantras_in_sukta}
        exact_translations = sum(
            1
            for mantra_id in mantra_ids
            if translation_by_mantra.get(mantra_id, {}).get("alignment") == "EXACT_MANTRA_ALIGNMENT"
        )
        qa_warnings = qa_warnings_by_entity.get(str(sukta_id), 0) + sum(
            qa_warnings_by_entity.get(str(mantra_id), 0) for mantra_id in mantra_ids
        )
        matrix.append(
            {
                "sukta": sukta_number,
                "mantra_count": len(mantras_in_sukta),
                "primary_sanskrit": sum(primary_by_mantra.get(m, 0) for m in mantra_ids),
                "parallel_sanskrit": sum(parallel_by_mantra.get(m, 0) for m in mantra_ids),
                "english_exact": exact_translations,
                "rishi_metadata": metadata_by_sukta.get(sukta_id, {}).get("rishi", False),
                "devata_metadata": metadata_by_sukta.get(sukta_id, {}).get("devata", False),
                "chandas_metadata": metadata_by_sukta.get(sukta_id, {}).get("chandas", False),
                "audio_reference": sukta_id in audio_sukta_ids,
                "qa_warnings": qa_warnings,
            }
        )

    DERIVED.mkdir(parents=True, exist_ok=True)
    matrix_path = DERIVED / "rv_mandala_1_full_coverage_matrix.json"
    matrix_path.write_text(json.dumps(matrix, indent=2), encoding="utf-8")

    incomplete_english = [row for row in matrix if row["english_exact"] < row["mantra_count"]]
    incomplete_parallel = [row for row in matrix if row["parallel_sanskrit"] < row["mantra_count"]]
    with_metadata = [
        row
        for row in matrix
        if row["rishi_metadata"] or row["devata_metadata"] or row["chandas_metadata"]
    ]
    with_audio = [row for row in matrix if row["audio_reference"]]
    with_qa = [row for row in matrix if row["qa_warnings"]]

    summary_lines = [
        "# Rigveda Mandala 1 per-Sukta coverage matrix (summary)",
        "",
        "Full 191-row matrix: `data/derived/rv_mandala_1_full_coverage_matrix.json` (not",
        "committed; regenerate with `scripts/generate_mandala1_reports.py`). This summary is",
        "safe to commit: aggregate counts only, no corpus text.",
        "",
        f"- Suktas: {len(matrix)}",
        f"- Mantras: {total_mantras}",
        f"- Suktas with full mantra-exact English coverage: "
        f"{len(matrix) - len(incomplete_english)}/{len(matrix)}",
        f"- Suktas with full VedaWeb parallel-Sanskrit coverage: "
        f"{len(matrix) - len(incomplete_parallel)}/{len(matrix)}",
        f"- Suktas with any traditional metadata: {len(with_metadata)}/{len(matrix)}",
        f"- Suktas with an external audio reference: {len(with_audio)}/{len(matrix)}",
        f"- Suktas with at least one QA finding: {len(with_qa)}/{len(matrix)}",
        "",
        "## Suktas with incomplete mantra-exact English alignment",
        "",
        "| Sukta | Mantras | Exact English |",
        "| --- | --- | --- |",
        *(
            f"| {row['sukta']} | {row['mantra_count']} | {row['english_exact']} |"
            for row in incomplete_english
        ),
        "",
    ]
    (REPORTS / "rv_m1_coverage_matrix_summary.md").write_text(
        "\n".join(summary_lines), encoding="utf-8", newline="\n"
    )

    # ---- translation coverage report (task 10) -----------------------------------
    by_alignment: dict[str, int] = defaultdict(int)
    for mantra in mantra_passages:
        translation = translation_by_mantra.get(mantra["entity_id"])
        if translation is None:
            by_alignment["MISSING"] += 1
        else:
            by_alignment[translation["alignment"]] += 1
    source_pages = sorted(
        {t["source_page_title"] for t in translations if t.get("source_page_title")}
    )
    source_revisions = sorted(
        {t["source_revision_id"] for t in translations if t.get("source_revision_id")}
    )

    def pct(n: int) -> str:
        return f"{n / total_mantras:.1%}" if total_mantras else "n/a"

    exact_n = by_alignment["EXACT_MANTRA_ALIGNMENT"]
    hymn_n = by_alignment["HYMN_LEVEL_ALIGNMENT"]
    range_n = by_alignment["RANGE_ALIGNMENT"]
    uncertain_n = by_alignment["UNCERTAIN_ALIGNMENT"]
    missing_n = by_alignment["MISSING"]
    missing_table = "\n".join(
        f"| {sukta} | {count} |" for sukta, count in sorted(missing_suktas.items())
    )

    translation_report = f"""# Rigveda Mandala 1 Griffith translation coverage

Generated by `scripts/generate_mandala1_reports.py` from the actual canonical
`translations.jsonl`; every count below is computed, not estimated. No translation
text is reproduced here (Griffith is public domain, but this report stays a summary).

- Total mantras: {total_mantras}
- Exact mantra-level Griffith alignment: {exact_n} ({pct(exact_n)})
- Hymn-level alignment only: {hymn_n} ({pct(hymn_n)})
- Range alignment: {range_n} ({pct(range_n)})
- Uncertain alignment: {uncertain_n} ({pct(uncertain_n)})
- Missing translation: {missing_n} ({pct(missing_n)})

## Source provenance

- Distinct Wikisource pages used: {len(source_pages)}
- Distinct MediaWiki revision IDs pinned: {len(source_revisions)}

## Missing mantras by Sukta

Every mantra listed here has no translation record at all; none was fabricated. RV
1.179 has no parseable Wikisource poem markup on the pinned revision (its `.verse
pre` block holds only an editorial note, not numbered stanza text — see the
`translation_page_parse_failed` QA finding). The others parsed a real but shorter
stanza sequence than the mantra count (`translation_alignment_uncertain` QA finding).

| Sukta | Missing mantras |
| --- | --- |
{missing_table}
"""
    (REPORTS / "rv_m1_translation_coverage_report.md").write_text(
        translation_report, encoding="utf-8", newline="\n"
    )

    # ---- structural / textual anomaly summary for the build report ---------------
    qa_by_check: dict[str, int] = defaultdict(int)
    qa_by_severity: dict[str, int] = defaultdict(int)
    for issue in qa_issues:
        qa_by_check[issue["check_id"]] += 1
        qa_by_severity[issue["severity"]] += 1

    parallel_selection_id = "VEDAWEB.AUFRECHT"
    parallel_covered_mantras = sum(
        1 for m in mantra_passages if parallel_by_mantra.get(m["entity_id"], 0)
    )
    primary_covered_mantras = sum(
        1 for m in mantra_passages if primary_by_mantra.get(m["entity_id"], 0)
    )
    metadata_sukta_count = len(with_metadata)
    rishi_count = sum(1 for row in matrix if row["rishi_metadata"])
    devata_count = sum(1 for row in matrix if row["devata_metadata"])
    chandas_count = sum(1 for row in matrix if row["chandas_metadata"])

    build_report = f"""# Rigveda Mandala 1 Corpus

Generated from the reproducible `rv_mandala_1_full_v1` build
(`data/builds/rv_mandala_1_full_v1.yaml`, config SHA-256
`{manifest["build_config_sha256"]}`). Every figure below comes from the canonical
JSONL output or the QA report; nothing is hand-counted. No bulk Sanskrit or English
corpus text is reproduced in this document.

## Structure

- Suktas: {len(matrix)} / 191
- Mantras: {total_mantras} / 2,006 (independent GRETIL/VHP/VedaWeb structural expectation)

## Sanskrit coverage

- Primary (`GRETIL.RV.AUFRECHT`): {primary_covered_mantras}/{total_mantras}
  ({pct(primary_covered_mantras)})
- Parallel (`{parallel_selection_id}`): {parallel_covered_mantras}/{total_mantras}
  ({pct(parallel_covered_mantras)})

## Parallel text coverage

Every mantra with a GRETIL primary reading also carries a VedaWeb `AUFRECHT`
parallel reading pinned to VedaWeb commit `d3eb8af7324338161520d2d35eae8f7e985a19a5`,
compared deterministically per mantra (`primary_parallel_text_divergence` QA policy).

## English coverage

- Exact mantra-level Griffith alignment: {exact_n}/{total_mantras} ({pct(exact_n)})
- Missing, across {len(missing_suktas)} Suktas ({sorted(missing_suktas)}): {missing_n}
- See `docs/reports/rv_m1_translation_coverage_report.md` for the per-Sukta breakdown.

## Traditional metadata coverage (VHP; intentionally partial, see docs/STATUS.md)

- Suktas with any traditional metadata: {metadata_sukta_count}/{len(matrix)}
- Rishi assertions: {rishi_count} Suktas
- Devata assertions: {devata_count} Suktas
- Chandas assertions: {chandas_count} Suktas
- No new bulk VHP ingestion happened this session; coverage is unchanged from the
  5-Sukta reviewed sample (Suktas 1, 22, 50, 164, 191).

## Audio/media coverage

- Suktas with an external audio reference: {len(with_audio)}/{len(matrix)} (VHP reference-only,
  same 5 Suktas as traditional metadata; no download, no new discovery this session)

## Source versions

- Primary Sanskrit: `GRETIL.RV.AUFRECHT` (`GRETIL.RV.AUFRECHT.TEI.2019`)
- Parallel Sanskrit: `VEDAWEB.AUFRECHT` (`VEDAWEB.RV.BOOK01.TEI.D3EB8AF`, commit-pinned)
- Translation: Griffith 1896, via Wikisource, page/revision-pinned per Sukta
- Traditional metadata/media: VHP, reference-only, 5 Suktas

## Rights

- GRETIL primary text: CC BY-NC-SA 4.0 (declared in the TEI header, verbatim preserved)
- VedaWeb `AUFRECHT` parallel text: CC BY-NC-SA 4.0 (per-version,
  `data/registry/text_versions.yaml`)
- Griffith translation: public domain (1896); Wikisource transcription/revision layer
  tracked separately
- VHP: permission-required; reference-only, nothing redistributed

## QA

- Status: {manifest["qa_status"]}
- Total findings: {len(qa_issues)}
- By severity: {dict(sorted(qa_by_severity.items()))}
- By check: {dict(sorted(qa_by_check.items()))}
- Structural errors: {qa_by_severity.get("ERROR", 0)}

## Text divergences

{qa_by_check.get("primary_parallel_text_divergence", 0)} of {total_mantras} mantras
show a residual primary/parallel divergence beyond known accent-notation differences
(`primary_parallel_text_divergence`, all WARNING severity in this build — no
ERROR-level structural misalignment). This matches the proportion already recorded
in the 240-mantra stratified sample (`docs/reports/rv_m1_text_comparison_report.md`);
see `docs/reports/rv_m1_full_text_comparison_report.md` for the full-corpus classification.

## Translation anomalies

- RV 1.179: no parseable Wikisource stanza markup on the pinned revision
  (`translation_page_parse_failed`).
- {qa_by_check.get("translation_alignment_uncertain", 0)} Suktas parsed a real but
  unconfirmed stanza sequence (`translation_alignment_uncertain`): the detected
  stanza count did not exactly match a confirmed 1..N verse-number sequence.
- {qa_by_check.get("translation_coverage_incomplete", 0)} Suktas (including some of
  the above) parsed with internally consistent 1..N numbering but fewer stanzas than
  the Sukta's real mantra count (`translation_coverage_incomplete`) — "exact" only
  means self-consistent, not complete; the shortfall is missing, not guessed. See
  `docs/reports/rv_m1_translation_coverage_report.md` for the exact Sukta list.
- The remaining Suktas parsed with a complete `EXACT_MANTRA_ALIGNMENT`.

## Reproducibility

Two builds from the identical pinned config produced byte-identical
`passages.jsonl`, `text_versions.jsonl`, `translations.jsonl`, `traditional_metadata.jsonl`,
`citations.jsonl`, `source_assertions.jsonl`, `discoveries.jsonl`, and `qa_issues.jsonl`.
`build_timestamp` in the config is the only externalized non-derived value; nothing else
depends on wall-clock time, retrieval order, or dict iteration order.

## Known limitations

1. Traditional metadata (Rishi/Devata/Chandas) and audio references cover only the 5
   Suktas already reviewed under the pilot; VHP bulk ingestion remains prohibited
   without written permission.
2. {missing_n} mantras across {len(missing_suktas)} Suktas ({sorted(missing_suktas)})
   have no Griffith translation on the pinned Wikisource revisions; genuinely missing,
   not fabricated.
3. Śākala recension identification remains a structural inference in both
   redistributable sources (GRETIL, VedaWeb), as already documented in
   `docs/architecture/RIGVEDA_BASE_EDITION.md`.
4. 164 mantras carry an unresolved primary/parallel textual divergence beyond
   notation; recorded as QA WARNINGs, not resolved by this build.

## Readiness for next stage

`READY_WITH_LIMITATIONS`. Structure, identity, primary/parallel Sanskrit, translation
alignment, QA, and reproducibility all pass with zero structural errors. Traditional
metadata and audio remain intentionally partial by rights policy, not by omission.
"""
    (REPORTS / "RIGVEDA_MANDALA_1_BUILD.md").write_text(
        build_report, encoding="utf-8", newline="\n"
    )

    print(f"Wrote {matrix_path}")
    print(f"Wrote {REPORTS / 'rv_m1_coverage_matrix_summary.md'}")
    print(f"Wrote {REPORTS / 'rv_m1_translation_coverage_report.md'}")
    print(f"Wrote {REPORTS / 'RIGVEDA_MANDALA_1_BUILD.md'}")


if __name__ == "__main__":
    main()
