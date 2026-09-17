"""Discover, from the corpus itself, every token that could be a form of a theonym.

The V2 pass failed on exactly this problem in the opposite direction. It built the
theonym set from ``Devata.label_iast`` -- the uninflected *stem* ``agni`` -- and so the
flag it computed never fired on ``agne``, "O Agni!", which is the one form that certainly
means the god. 915 edges then asserted the impersonal fire entity on the sole evidence of
a vocative address to the deity, and 0 of 915 were flagged.

The lesson is not "generate more forms". A generated paradigm is a claim about Sanskrit
grammar, and this corpus does not contain the paradigm -- it contains a few hundred actual
spellings, several of which no grammar would predict (sandhi-fused ``indraś``, elided
``indra'``, Samavedic Devanagari transliterated back into Latin). It also contains a great
many spellings that *share the stem and are not the deity*: ``indriya`` is "power",
``aindra`` is "belonging to Indra", ``indrota`` is the patron Indrota.

So this module does not generate. It **enumerates what is there** -- every distinct folded
token in all four Vedas that begins with, or contains, a deity stem -- with per-Veda
counts, the surrounding text of real occurrences, and a mechanical pre-classification.
Adjudication of each candidate is a separate, recorded decision; this only guarantees that
no form can ever be accepted which does not occur.

Usage::

    python scripts/discover_theonym_forms.py indra varuṇa rudra
    python scripts/discover_theonym_forms.py --json out.json indra
    python scripts/discover_theonym_forms.py --all-devatas --json out.json
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
from collections import Counter, defaultdict
from typing import Any

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.enrich.concepts import fold_alias  # noqa: E402
from vedagraph.enrich.corpus import VEDAS, Corpus, load_corpus  # noqa: E402
from vedagraph.enrich.surfaces import render_for_display  # noqa: E402

#: Occurrences kept per candidate form, so a reader can go and check the verse.
_MAX_EXAMPLES = 3

#: A candidate seen fewer times than this in the whole corpus is still reported -- rare
#: forms include the vocatives that matter most -- but is marked so adjudication can see
#: that its per-alias precision estimate rests on almost nothing.
_RARE_THRESHOLD = 3


def _corpus_token_index(corpus: Corpus) -> tuple[dict[str, dict[str, int]], dict[str, list[str]]]:
    """Return folded-token -> per-Veda count, and folded-token -> sample passage keys.

    Built once. The Samaveda writes continuous sandhi and so contributes far fewer
    separable tokens than its verse count implies; that asymmetry is real and is reported
    per Veda rather than averaged away.
    """
    counts: dict[str, dict[str, int]] = defaultdict(lambda: dict.fromkeys(VEDAS, 0))
    samples: dict[str, list[str]] = defaultdict(list)
    for mantra in corpus.mantras:
        for token in set(mantra.surfaces.tokens):
            counts[token][mantra.veda] += 1
            if len(samples[token]) < _MAX_EXAMPLES:
                samples[token].append(mantra.passage_key)
    return dict(counts), dict(samples)


def _classify(stem: str, token: str) -> str:
    """Mechanical pre-classification of one candidate token against a stem.

    Deliberately crude and deliberately not final. It sorts candidates into buckets that
    make human/model adjudication cheap; it decides nothing. ``INITIAL`` is the bucket
    that contains both every genuine inflection and every compound and derivative, so it
    is the bucket that must actually be read.
    """
    if token == stem:
        return "EXACT"
    if token.startswith(stem):
        return "INITIAL"
    if token.endswith(stem):
        return "FINAL"
    return "INTERNAL"


def discover(stem_iast: str, corpus: Corpus, index: Any, samples: Any) -> dict[str, Any]:
    """Enumerate every corpus token containing ``stem_iast`` on the folded surface."""
    stem = fold_alias(stem_iast)
    candidates: list[dict[str, Any]] = []
    for token, per_veda in index.items():
        if stem not in token:
            continue
        total = sum(per_veda.values())
        candidates.append(
            {
                "surface": render_for_display(token),
                "folded": token,
                "position": _classify(stem, token),
                "total": total,
                "rare": total < _RARE_THRESHOLD,
                "per_veda": dict(per_veda),
                "vedas": [v for v in VEDAS if per_veda[v]],
                "examples": samples.get(token, []),
            }
        )
    candidates.sort(key=lambda c: (-c["total"], c["folded"]))
    return {
        "stem_iast": stem_iast,
        "stem_folded": stem,
        "distinct_forms": len(candidates),
        "total_occurrences": sum(c["total"] for c in candidates),
        "by_position": dict(Counter(c["position"] for c in candidates)),
        "forms": candidates,
    }


def _print_human(result: dict[str, Any], limit: int) -> None:
    print(f"\n=== {result['stem_iast']}  (folded: {result['stem_folded']}) ===")
    print(
        f"  {result['distinct_forms']} distinct forms, "
        f"{result['total_occurrences']} mantra-occurrences, "
        f"positions {result['by_position']}"
    )
    for form in result["forms"][:limit]:
        vedas = "/".join(f"{v}={form['per_veda'][v]}" for v in VEDAS if form["per_veda"][v])
        rare = "  RARE" if form["rare"] else ""
        print(f"    {form['total']:6d}  {form['surface']:<28} {form['position']:<8} {vedas}{rare}")
    if len(result["forms"]) > limit:
        print(f"    ... {len(result['forms']) - limit} more forms (use --json for all)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stems", nargs="*", help="deity stems in IAST, e.g. indra varuṇa")
    parser.add_argument("--json", type=pathlib.Path, help="write the full result as JSON")
    parser.add_argument("--limit", type=int, default=40, help="forms shown per stem on stdout")
    parser.add_argument(
        "--stem-file", type=pathlib.Path, help="read stems from a file, one per line"
    )
    args = parser.parse_args()

    stems = list(args.stems)
    if args.stem_file:
        stems += [
            line.strip()
            for line in args.stem_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    if not stems:
        parser.error("give at least one stem or --stem-file")

    corpus = load_corpus(PROJECT_ROOT)
    counts = corpus.counts()
    print(
        f"corpus: {len(corpus.mantras)} mantras  "
        + "  ".join(f"{v}={counts.get(v, 0)}" for v in VEDAS)
    )
    index, samples = _corpus_token_index(corpus)
    print(f"token index: {len(index)} distinct folded tokens")

    results = [discover(stem, corpus, index, samples) for stem in stems]
    for result in results:
        _print_human(result, args.limit)
    if args.json:
        args.json.write_text(
            json.dumps({"stems": results}, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
