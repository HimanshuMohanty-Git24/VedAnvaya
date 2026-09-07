"""Turn the staged Griffith 1899 alignment into the ``Translation`` JSONL a build reads.

Why a conversion step exists at all
===================================

The acquisition stage (:mod:`scripts.fetch_griffith_yajurveda`) is an *alignment* artifact:
it records every parsed unit and what happened to it, including the units that bound to no
canonical key. The release builder wants the opposite shape -- one ``Translation`` per
passage it is going to emit. Collapsing the two would lose the unbound units, which are the
evidence that the coverage figure is honest rather than merely large.

So this step is deliberately lossy in ONE direction only: it drops nothing, it just selects
the bound rows. The unbound ones stay in the stage file and are reported as gaps.

Alignment is carried through, never flattened
=============================================

``TranslationAlignment.EXACT_MANTRA_ALIGNMENT`` is written only for units the stage marked
``EXACT`` -- a unit whose own printed verse number resolved to this key. A unit marked
``STRUCTURAL_DIVERGENCE`` gets ``RANGE_ALIGNMENT`` instead: the translation is attached, and
the record says the two spines do not agree unit-for-unit there. Writing EXACT for those 14
would claim a precision the source does not support.

Usage::

    python scripts/stage_yajurveda_translations.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid5

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from vedagraph.identity import (  # noqa: E402
    VEDAGRAPH_NAMESPACE_UUID,
    uuid_for_urn,
    vsm_mantra_identity,
)
from vedagraph.models import Translation  # noqa: E402
from vedagraph.models.enums import (  # noqa: E402
    AlignmentLevel,
    QualityStatus,
    RightsStatus,
    TranslationAlignment,
)
from vedagraph.storage.jsonl import write_jsonl  # noqa: E402

STAGE = REPO / "data" / "staged" / "yajurveda_translation_stage.json"
OUT_DIR = REPO / "data" / "staged" / "yajurveda_griffith_1899"
OUT = OUT_DIR / "translations.jsonl"

SOURCE_ID = "SACRED_TEXTS"
ARTIFACT_ID = "GRIFFITH.YV.1899.SACREDTEXTS"
TRANSLATOR = "Ralph T. H. Griffith"
WORK_EDITION = (
    "Ralph T. H. Griffith, The Texts of the White Yajurveda, E. J. Lazarus and Co., Benares, 1899"
)

ALIGNMENT_BY_STAGE_VERDICT = {
    "EXACT": TranslationAlignment.EXACT_MANTRA_ALIGNMENT,
    "STRUCTURAL_DIVERGENCE": TranslationAlignment.RANGE_ALIGNMENT,
}


def build() -> tuple[int, dict[str, int]]:
    payload: Any = json.loads(STAGE.read_text(encoding="utf-8"))
    rows: list[Translation] = []
    by_verdict: dict[str, int] = {}
    seen: set[str] = set()

    for verse in payload["verses"]:
        verdict = str(verse["alignment"])
        alignment = ALIGNMENT_BY_STAGE_VERDICT.get(verdict)
        if alignment is None:
            # A verdict this converter does not understand is refused, not guessed. The
            # stage's other verdicts (SOURCE_GAP, AMBIGUOUS, UNRESOLVED) bind to no key by
            # definition and never reach here.
            raise ValueError(f"unhandled stage alignment verdict {verdict!r}")

        key = str(verse["canonical_key"])
        if key in seen:
            raise ValueError(f"two translation units claim {key}")
        seen.add(key)

        _, urn, _ = vsm_mantra_identity(int(verse["adhyaya"]), int(verse["mantra"]))
        passage_id = uuid_for_urn(urn)
        rows.append(
            Translation(
                translation_id=uuid5(VEDAGRAPH_NAMESPACE_UUID, f"translation|{ARTIFACT_ID}|{urn}"),
                passage_id=passage_id,
                language="en",
                translator=TRANSLATOR,
                work_edition=WORK_EDITION,
                year=1899,
                text=str(verse["text"]),
                source_id=SOURCE_ID,
                source_artifact_id=ARTIFACT_ID,
                rights_status=RightsStatus.PUBLIC_DOMAIN,
                alignment_level=AlignmentLevel.MANTRA,
                alignment=alignment,
                quality_status=QualityStatus.MACHINE_ALIGNED,
                canonical_page_url=str(verse["source_page_url"]),
            )
        )
        by_verdict[verdict] = by_verdict.get(verdict, 0) + 1

    rows.sort(key=lambda row: str(row.passage_id))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = write_jsonl(OUT, rows)
    return written, dict(sorted(by_verdict.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    if not STAGE.exists():
        print(f"no staged alignment at {STAGE}; run scripts/fetch_griffith_yajurveda.py first")
        return 1
    written, by_verdict = build()
    print(f"translations written {written} -> {OUT}")
    print(f"by stage verdict {by_verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
