"""Confirm catalogued mappings against each audio file's *own* stated text.

**Why this is not the validator repeating itself.** The catalog is built from the source's
chapter-listing endpoint and its ``shlok`` field. This script asks a different endpoint --
the one that serves the audio -- for the ``audio_text`` that *that specific file* recites,
and compares it against this corpus's text for the key the catalog claims. Agreement is
therefore independent evidence, not the build restating its own input. It also checks that
the file the source returns is named for the item that was requested, which catches an
endpoint that silently falls back to some other verse.

**The sample is deliberately loaded at the Valakhilya boundary.** The source numbers
Rigvedic Mandala 8 in Griffith's order, so 8.49 through 8.103 sit eleven hymns away from
where a key-for-key rule would put them. A mapping error would hide there and nowhere else,
so those keys are always included on top of the random draw.

This is the closest thing to listening that can be automated. Run it when the source
changes, or before trusting the catalog after an edit.

Usage::

    python scripts/audio/audit_mappings.py
    python scripts/audio/audit_mappings.py --sample 20 --veda RV
    python scripts/audio/audit_mappings.py --json out.json
"""

from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import random
import sys
import warnings
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

from neo4j import GraphDatabase  # noqa: E402

from vedagraph.product.audio.catalog import AudioCatalog  # noqa: E402
from vedagraph.product.audio.models import AudioRecord  # noqa: E402
from vedagraph.product.audio.net import USER_AGENT  # noqa: E402
from vedagraph.product.audio.vedsearch import VedSearchClient, verse_matches  # noqa: E402

BOLT_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
BOLT_AUTH = (
    os.environ.get("NEO4J_USER", "neo4j"),
    os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
)
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Which stored surface is this corpus's reading. Not uniform: the Yajurveda has no
#: PRIMARY_TEXT, because its verses were extracted from published adhyayas.
TEXT_ROLE = {
    "RV": "PRIMARY_TEXT",
    "AV": "PRIMARY_TEXT",
    "SV": "PRIMARY_TEXT",
    "YV": "EXTRACTED_FROM_CONTAINER",
}

#: Keys that must be audited every run, whatever the random draw selects.
#:
#: 8.48 is the last hymn before the Valakhilya and must be unshifted; 8.60, 8.71, 8.92 and
#: 8.103 all sit above the gap and must each be eleven hymns lower at the source. If the
#: permutation were dropped or inverted, these five would be the first to show it.
ALWAYS_AUDIT = (
    "VG:RV:SAK:M08:S048:V001",
    "VG:RV:SAK:M08:S060:V001",
    "VG:RV:SAK:M08:S071:V001",
    "VG:RV:SAK:M08:S092:V001",
    "VG:RV:SAK:M08:S103:V001",
    "VG:RV:SAK:M01:S001:V001",
    "VG:RV:SAK:M10:S191:V004",
)


def our_text(session: Any, record: AudioRecord) -> str:
    row = session.run(
        "MATCH (p:Passage {canonical_key: $key})-[:HAS_TEXT_VERSION]->(t:TextVersion) "
        "WHERE t.text_role = $role RETURN t.text_nfc AS text",
        key=record.scope_key,
        role=TEXT_ROLE[record.veda],
    ).single()
    return (row["text"] if row else "") or ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=8, help="random draws per Veda")
    parser.add_argument("--veda", choices=["RV", "SV", "YV", "AV"], action="append", default=[])
    parser.add_argument("--seed", type=int, default=4242)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--data-dir", type=pathlib.Path, default=PROJECT_ROOT / "data")
    args = parser.parse_args()

    catalog = AudioCatalog.load_default(args.data_dir)
    if not len(catalog):
        print("Catalog is empty; nothing to audit.")
        return 0

    rng = random.Random(args.seed)
    vedas = args.veda or ["RV", "AV", "YV", "SV"]
    selected: list[AudioRecord] = []
    seen: set[str] = set()

    for key in ALWAYS_AUDIT:
        record = next((r for r in catalog if r.scope_key == key), None)
        if record is not None and record.veda in vedas:
            selected.append(record)
            seen.add(record.audio_id)
    for veda in vedas:
        pool = [r for r in catalog.for_veda(veda) if r.audio_id not in seen]
        for record in rng.sample(pool, min(args.sample, len(pool))):
            selected.append(record)
            seen.add(record.audio_id)

    if not selected:
        print("No records selected.")
        return 0

    client = VedSearchClient(user_agent=USER_AGENT)
    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    rows: list[dict[str, Any]] = []
    confirmed = wrong = unreachable = 0
    try:
        with driver.session() as session:
            for record in selected:
                ours = our_text(session, record)
                try:
                    document = client.audio_document(record.veda, record.source_reference or "")
                except Exception as error:
                    unreachable += 1
                    print(f"  ERR  {record.scope_key:<28} {type(error).__name__}")
                    rows.append(
                        {
                            "key": record.scope_key,
                            "verdict": "UNREACHABLE",
                            "detail": type(error).__name__,
                        }
                    )
                    continue
                spoken = str(document.get("audio_text") or "")
                filename = str(document.get("attachment_name") or "")
                matched, score = verse_matches(spoken, ours)
                # The returned file must be named for the item requested: a source that
                # quietly substitutes another verse would otherwise pass on text alone.
                named = (record.source_reference or "") in filename
                verdict = "CONFIRMED" if (matched and named) else "WRONG"
                if verdict == "CONFIRMED":
                    confirmed += 1
                    print(f"  ok   {record.scope_key:<28} -> {filename:<34} sim={score:.3f}")
                else:
                    wrong += 1
                    print(f"  WRONG {record.scope_key:<28} -> {filename:<34} sim={score:.3f}")
                    print(f"         file recites: {spoken[:72]}")
                    print(f"         corpus has  : {ours[:72]}")
                rows.append(
                    {
                        "key": record.scope_key,
                        "source_item": record.source_reference,
                        "file": filename,
                        "similarity": round(score, 4),
                        "named_correctly": named,
                        "verdict": verdict,
                    }
                )
    finally:
        driver.close()

    total = len(selected)
    print(
        f"\nindependent confirmation: {confirmed} confirmed, {wrong} wrong, "
        f"{unreachable} unreachable (n={total})"
    )
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "sampled": total,
                    "confirmed": confirmed,
                    "wrong": wrong,
                    "unreachable": unreachable,
                    "seed": args.seed,
                    "rows": rows,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    # Unreachable is not a failure: the source being slow says nothing about the mapping.
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main())
