"""Prove the Atharvaveda skeleton corpus descends only from the 1856 scan.

The prohibited editions are not hypothetical: `data/raw/gretil_avs` and
`data/raw/vedaweb_avs` are on this disk, they contain the Atharvaveda in
Devanagari, and they are far easier to read than a 170-year-old scan. Any of
them reaching a reading -- by being opened during transcription, by being cited
in a record, or by a reader silently recalling text it has seen -- would turn
the release's central claim into a fiction, and it would not show up as an error
anywhere else.

Three things are checked, in descending order of how well a machine can see
them:

1. **Reference.** Nothing the v2 pipeline reads or writes may name a prohibited
   source, and no v2 code may open a prohibited path.
2. **Instruction.** The reader brief must actually forbid them by name.
3. **Text.** Released readings are compared against the prohibited editions.
   An exact long-run match between a released unit and a prohibited edition is
   evidence of copying rather than of reading.

Point 3 is a detector, not a proof: this edition and the modern ones are
witnesses to the same text, so *some* agreement is expected and is not
contamination. What would be damning is agreement at a length and rate that
reading cannot explain, which is why the check reports the distribution rather
than a single verdict.

Usage:
    python scripts/audit_av_source_contamination.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import unicodedata
from typing import Any

_REPO = pathlib.Path(__file__).resolve().parents[1]
AV_ROOT = _REPO / "data" / "transcriptions" / "atharvaveda_bsb_1856"
V2 = AV_ROOT / "v2"

#: Every edition of the Atharvaveda that may not be used as a correction source,
#: with the marker that would betray it in code, a record, or a filename.
PROHIBITED_MARKERS: tuple[str, ...] = (
    "GRETIL",
    "TITUS",
    "VEDAWEB",
    "ORLANDI",
    "SACRED_TEXTS",
    "SACRED-TEXTS",
    "PAIPPALADA",
)

#: Directories holding a prohibited Atharvaveda in machine-readable form.
PROHIBITED_CORPORA: tuple[pathlib.Path, ...] = (
    _REPO / "data" / "raw" / "gretil_avs",
    _REPO / "data" / "raw" / "vedaweb_avs",
)

#: v2 pipeline code. These are the files that could open a prohibited corpus.
PIPELINE_CODE: tuple[pathlib.Path, ...] = (
    _REPO / "scripts" / "reconcile_atharvaveda_v2.py",
    _REPO / "scripts" / "build_atharvaveda_canonical.py",
    _REPO / "scripts" / "av_reader_packet.py",
    _REPO / "scripts" / "av_production_ledger.py",
    _REPO / "scripts" / "crop_atharvaveda_leaf.py",
    _REPO / "scripts" / "crop_atharvaveda_line.py",
    _REPO / "scripts" / "extract_atharvaveda_accents.py",
    _REPO / "src" / "vedagraph" / "ingest" / "av_accent_binder.py",
    _REPO / "src" / "vedagraph" / "ingest" / "av_alignment.py",
)

#: A run of this many identical Devanagari characters shared between a released
#: reading and a prohibited edition is longer than coincidence comfortably
#: explains for independently produced text.
SUSPICIOUS_RUN = 40

DEVANAGARI = re.compile(r"[ऀ-ॿ]+")


def _prohibited_reference(text: str) -> list[str]:
    upper = text.upper()
    return [marker for marker in PROHIBITED_MARKERS if marker in upper]


def audit_code() -> dict[str, Any]:
    """No v2 code may name or open a prohibited edition.

    `build_atharvaveda_canonical.py` is expected to name them: it carries the
    firewall's own deny-list. A reference is therefore only a finding if the file
    also opens a prohibited path.
    """
    findings: list[dict[str, Any]] = []
    for path in PIPELINE_CODE:
        if not path.exists():
            findings.append({"file": str(path.relative_to(_REPO)), "issue": "MISSING"})
            continue
        text = path.read_text(encoding="utf-8")
        opened = [
            str(corpus.relative_to(_REPO)).replace("\\", "/")
            for corpus in PROHIBITED_CORPORA
            if corpus.name in text
        ]
        if opened:
            findings.append(
                {
                    "file": str(path.relative_to(_REPO)),
                    "issue": "REFERENCES_PROHIBITED_CORPUS_PATH",
                    "paths": opened,
                }
            )
    return {"files_examined": len(PIPELINE_CODE), "findings": findings}


def audit_brief() -> dict[str, Any]:
    """The brief must forbid the prohibited editions by name."""
    brief = V2 / "skeleton_reader_brief.md"
    if not brief.exists():
        return {"brief_present": False, "markers_named": [], "clean": False}
    upper = brief.read_text(encoding="utf-8").upper()
    named = [marker for marker in ("GRETIL", "TITUS", "VEDAWEB", "ORLANDI") if marker in upper]
    return {
        "brief_present": True,
        "markers_named": named,
        "clean": len(named) == 4,
    }


def _load_readings() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for directory in ("R1", "R2", "R3", "reconciled"):
        base = V2 / directory
        if not base.exists():
            continue
        for path in sorted(base.glob("leaf_*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    row["_origin"] = f"{directory}/{path.name}"
                    rows.append(row)
    return rows


def audit_records(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """No reading may cite a prohibited source anywhere in its own metadata."""
    findings: list[dict[str, Any]] = []
    for row in rows:
        haystack = " ".join(
            str(row.get(field) or "")
            for field in ("notes", "structural_marker", "reader_identity", "run_id")
        )
        hits = _prohibited_reference(haystack)
        if hits:
            findings.append(
                {"origin": row["_origin"], "canvas_index": row.get("canvas_index"), "markers": hits}
            )
    return {"records_examined": len(rows), "findings": findings}


def _prohibited_text() -> str:
    """Every Devanagari run in the prohibited corpora, as one haystack."""
    chunks: list[str] = []
    for corpus in PROHIBITED_CORPORA:
        if not corpus.exists():
            continue
        for path in corpus.rglob("*"):
            if not path.is_file():
                continue
            try:
                raw = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            chunks.extend(DEVANAGARI.findall(unicodedata.normalize("NFC", raw)))
    return " ".join(chunks)


def audit_text_overlap(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare released readings against the prohibited editions themselves."""
    haystack = _prohibited_text()
    if not haystack:
        return {
            "prohibited_corpora_present": False,
            "note": "no prohibited Atharvaveda on disk to compare against",
            "units_compared": 0,
            "units_with_a_suspicious_run": 0,
        }

    compared = 0
    suspicious: list[dict[str, Any]] = []
    for row in rows:
        text = row.get("text_devanagari")
        if not isinstance(text, str) or not text:
            continue
        compared += 1
        # Compare the aksara stream only: whitespace and punctuation differ
        # between a printed page and a digital edition for reasons that have
        # nothing to do with descent.
        stream = "".join(DEVANAGARI.findall(unicodedata.normalize("NFC", text)))
        if len(stream) < SUSPICIOUS_RUN:
            continue
        for start in range(0, len(stream) - SUSPICIOUS_RUN + 1):
            window = stream[start : start + SUSPICIOUS_RUN]
            if window in haystack:
                suspicious.append(
                    {
                        "origin": row["_origin"],
                        "canvas_index": row.get("canvas_index"),
                        "mantra": row.get("mantra"),
                        "matched_run": window,
                    }
                )
                break

    return {
        "prohibited_corpora_present": True,
        "suspicious_run_length": SUSPICIOUS_RUN,
        "units_compared": compared,
        "units_with_a_suspicious_run": len(suspicious),
        "examples": suspicious[:10],
        "interpretation": (
            "This edition and the prohibited ones witness the same text, so short "
            "agreement is expected and is not contamination. A shared run of "
            f"{SUSPICIOUS_RUN} aksaras with no intervening difference is longer than "
            "independent reading of a 1856 fount comfortably explains and is worth "
            "inspecting by hand; it is evidence, not a verdict."
        ),
    }


def build() -> dict[str, Any]:
    rows = _load_readings()
    code = audit_code()
    brief = audit_brief()
    records = audit_records(rows)
    overlap = audit_text_overlap(rows)

    contamination = len(code["findings"]) + len(records["findings"])
    if not brief["clean"]:
        contamination += 1

    return {
        "artifact_id": "BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN",
        "prohibited_markers": list(PROHIBITED_MARKERS),
        "prohibited_corpora_on_disk": [
            str(corpus.relative_to(_REPO)).replace("\\", "/")
            for corpus in PROHIBITED_CORPORA
            if corpus.exists()
        ],
        "code_audit": code,
        "brief_audit": brief,
        "record_audit": records,
        "text_overlap_audit": overlap,
        "AV_PROHIBITED_SOURCE_CONTAMINATION": contamination,
        "verdict": "CLEAN" if contamination == 0 else "CONTAMINATED",
        "scope_note": (
            "A reader recalling a prohibited edition from memory rather than opening "
            "it leaves no trace in code, paths or records. The text overlap check is "
            "the only instrument pointed at that failure, and it is a detector rather "
            "than a proof."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=V2 / "contamination_audit.json")
    args = parser.parse_args()
    report = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    printable = {key: value for key, value in report.items() if key != "text_overlap_audit"}
    printable["text_overlap_audit"] = {
        key: value for key, value in report["text_overlap_audit"].items() if key != "examples"
    }
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
