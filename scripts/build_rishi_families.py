"""Derive the ``RishiFamily`` artifact from the three ṛṣi registries.

The layer was declared and empty: ``ontology.LABEL_RISHI_FAMILY`` had carried its Q2/Q19/
Q24/Q35 annotation and ``schema.py`` its uniqueness constraint since V2, with zero nodes
behind them, because **no gotra data file exists in this repository and none was going to
arrive**. The one ``grep`` hit for "gotra" in the corpus is the ordinary word inside a
verse.

What does exist is the Anukramaṇī's own seer strings, which are *patronymic + personal
name*. This script turns those into families through
:mod:`vedagraph.domain.rishi_families`, whose module docstring is the argument for why
that is source-stated evidence rather than string similarity; read it before changing the
patronymic table, because the table is the entire evidence base of the layer.

It writes an artifact and touches no database, for the reason the projection script's
docstring gives: derivation and projection have to be separately re-runnable so a failure
is unambiguously one or the other. The artifact records the refusals as well as the
memberships -- 88 families, 306 memberships, and every ṛṣi left unassigned with the class
it was left unassigned under -- because "we could not derive a family for this one" is a
result of this layer and not an absence of one.

Usage::

    python scripts/build_rishi_families.py
    python scripts/build_rishi_families.py --check     # measure, write nothing
"""

from __future__ import annotations

import argparse
import dataclasses
import io
import json
import pathlib
import sys
from typing import Any, Final

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import yaml  # noqa: E402

from vedagraph.domain.rishi_families import (  # noqa: E402
    RishiEntry,
    coverage,
    derive,
)

REGISTRY_DIR: Final = PROJECT_ROOT / "data" / "registry"
#: Written into the tracked V2 domain directory and **not** into ``data/derived``,
#: which ``.gitignore`` excludes wholesale. An artifact nobody can commit does not make
#: a layer reproducible; it makes the layer look reproducible.
OUTPUT: Final = PROJECT_ROOT / "data" / "domain" / "vedagraph_domain_v2" / "rishi_families_v1.json"

#: Registry file, namespace, and the ``source_id`` whose Anukramaṇī the strings come from.
#: The namespaces are kept apart exactly as the registries keep them: a Ṛgvedic
#: ``bhāradvāja`` and a Yajurvedic ``bhāradvāja`` are two rows about one gotra, and this
#: layer unifies them at the *family*, never by asserting the two ṛṣis are one person.
SOURCES: Final[tuple[tuple[str, str, str], ...]] = (
    ("rishis.yaml", "RV_WSC2023_ANUKRAMANI", "WSC2023"),
    ("rishis_yv.yaml", "YV_VSM_RSISUCI", "WIKISOURCE_SA"),
    ("rishis_av.yaml", "AV_WHITNEY_ANUKRAMANI", "WIKISOURCE_WHITNEY_AV"),
)


def _entities(path: pathlib.Path) -> list[dict[str, Any]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    entities = document.get("entities") if isinstance(document, dict) else None
    return list(entities) if isinstance(entities, list) else []


def load_entries() -> tuple[list[RishiEntry], dict[str, str]]:
    """Every ṛṣi registry row, plus the ``source_id`` that stated each one's label."""
    entries: list[RishiEntry] = []
    source_by_key: dict[str, str] = {}
    for filename, namespace, source_id in SOURCES:
        for row in _entities(REGISTRY_DIR / filename):
            key = str(row["entity_key"])
            entries.append(
                RishiEntry(
                    entity_key=key,
                    # The Ṛgvedic registry has no ``label_iast``: its ``preferred_label``
                    # already *is* IAST. Falling back rather than requiring the field
                    # keeps this reading the registries as they are.
                    label=str(row.get("label_iast") or row["preferred_label"]),
                    namespace=str(row.get("registry_namespace", namespace)),
                )
            )
            source_by_key[key] = source_id
    return entries, source_by_key


def main() -> int:
    # Rewrapped here and not at import time. The IAST in this artifact cannot survive a
    # cp1252 console, but a module that swaps sys.stdout on import is not importable from a
    # test without breaking the runner's output capture -- which is exactly what happened.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="measure, write nothing")
    args = parser.parse_args()

    entries, source_by_key = load_entries()
    derivation = derive(entries)
    measured = coverage(derivation, entries)

    label_by_key = {entry.entity_key: entry.label for entry in entries}
    payload = {
        "artifact": "rishi_families_v1",
        "coverage": measured,
        "families": [derivation.families[key] for key in sorted(derivation.families)],
        "memberships": [
            dict(dataclasses.asdict(m), source_id=source_by_key[m.entity_key])
            for m in sorted(derivation.memberships, key=lambda m: (m.entity_key, m.family_key))
        ],
        "decompositions": [
            dict(
                dataclasses.asdict(d),
                patronymics=list(d.patronymics),
                personal_names=list(d.personal_names),
                source_id=source_by_key[d.entity_key],
            )
            for d in sorted(derivation.decompositions, key=lambda d: d.entity_key)
        ],
        "unassigned": [
            {
                "entity_key": key,
                "source_label": label_by_key[key],
                "unassigned_class": verdict[0],
                "reason": verdict[1],
            }
            for key, verdict in sorted(derivation.unassigned.items())
        ],
    }

    print(json.dumps(measured, ensure_ascii=False, indent=2, sort_keys=True))
    if args.check:
        print("--check: nothing written")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {OUTPUT.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
