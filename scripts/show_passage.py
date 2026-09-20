"""Print one or more passages: citation, Sanskrit, translation, and matched tokens.

Every alias decision in this repository is supposed to be checkable by reading the verse,
and until now checking it meant writing a bespoke script. This is that script. It reads
the same :func:`~vedagraph.enrich.corpus.load_corpus` view every enrichment stage reads,
so what it prints is what the matcher sees -- including the folded surface, which is where
a containment error becomes visible and the display surface is where it hides.

The Samaveda has no translations at all and the Yajurveda's are partial. That is reported
per passage rather than left as an empty line, because "no translation" and "the
translation says nothing relevant" are different findings and the first one is not the
Samaveda's fault.

Usage::

    python scripts/show_passage.py VG:RV:SAK:M01:S001:V001
    python scripts/show_passage.py --grep indra --veda SV --limit 5
    python scripts/show_passage.py --grep agne --veda RV --limit 3 --tokens
"""

from __future__ import annotations

import argparse
import io
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.enrich.concepts import fold_alias  # noqa: E402
from vedagraph.enrich.corpus import VEDAS, MantraRecord, load_corpus  # noqa: E402
from vedagraph.enrich.surfaces import render_for_display  # noqa: E402


def _show(mantra: MantraRecord, *, show_tokens: bool, highlight: str | None) -> None:
    print(f"\n=== {mantra.passage_key}   {mantra.citation}   [{mantra.veda}]")
    print(f"  source     : {mantra.surfaces.source}")
    print(f"  folded     : {mantra.surfaces.script_folded}")
    if mantra.translations:
        for index, text in enumerate(mantra.translations, start=1):
            print(f"  translation{index}: {text}")
    else:
        print("  translation: (none in this corpus)")
    if mantra.devatas or mantra.rishis or mantra.chandas:
        print(
            f"  metadata   : devata={list(mantra.devatas)} "
            f"rishi={list(mantra.rishis)} chandas={list(mantra.chandas)}"
        )
    if highlight:
        folded = fold_alias(highlight)
        hits = [token for token in mantra.surfaces.tokens if folded in token]
        exact = [token for token in hits if token == folded]
        print(
            f"  match      : {highlight!r} -> exact tokens {[render_for_display(t) for t in exact]}"
            f"  containing tokens {[render_for_display(t) for t in hits if t != folded]}"
        )
    if show_tokens:
        print(f"  tokens     : {[render_for_display(t) for t in mantra.surfaces.tokens]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keys", nargs="*", help="passage keys, e.g. VG:RV:SAK:M01:S001:V001")
    parser.add_argument("--grep", help="show passages whose folded surface contains this alias")
    parser.add_argument("--veda", choices=VEDAS, help="restrict --grep to one Veda")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--tokens", action="store_true", help="print every folded token")
    parser.add_argument(
        "--exact-token",
        action="store_true",
        help="with --grep, require a whole-token match rather than a substring",
    )
    args = parser.parse_args()

    corpus = load_corpus(PROJECT_ROOT)
    if args.keys:
        for key in args.keys:
            mantra = corpus.by_key.get(key)
            if mantra is None:
                print(f"\n=== {key}   NOT FOUND")
                continue
            _show(mantra, show_tokens=args.tokens, highlight=args.grep)
    if args.grep:
        folded = fold_alias(args.grep)
        shown = 0
        for mantra in corpus.mantras:
            if args.veda and mantra.veda != args.veda:
                continue
            tokens = mantra.surfaces.tokens
            hit = (
                folded in tokens
                if args.exact_token
                else folded in mantra.surfaces.sandhi_insensitive
            )
            if not hit:
                continue
            _show(mantra, show_tokens=args.tokens, highlight=args.grep)
            shown += 1
            if shown >= args.limit:
                break
        if shown == 0:
            print(f"\nno passage matched {args.grep!r} (folded {folded!r})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
