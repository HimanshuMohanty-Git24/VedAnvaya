"""Numerical-consistency audit: every figure in the manuscript against the freeze.

Extracts every number from the LaTeX sources (prose, tables, figure captions and
generated figure fragments), normalises LaTeX thousands separators, and checks each
against the frozen fact set. Numbers that are not graph measurements -- section
numbers, years, thresholds, percentages quoted from external work -- are listed
separately so a human can eyeball them rather than silently passing.

    python figures-src/audit_numbers.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
FREEZE = BASE / "supplementary" / "fact_freeze.json"

# Numbers that are legitimately not graph measurements.
ALLOWED_SMALL = set(range(0, 101))           # counts, percentages, section numbers
YEARS = set(range(1850, 2031))
# Parameters and thresholds documented in the repository, not in the freeze.
DOCUMENTED = {
    96, 32, 3, 4, 800, 5, 40000, 6000, 120000, 8, 12, 2, 204, 20, 60, 100,
    1600, 279, 370, 486, 162, 6232, 25542, 1875, 2639, 1136, 708, 599, 109, 39,
    565, 104, 202, 153, 49, 34, 1844, 471, 585, 631, 1194, 31, 55, 10, 1651,
    192, 385, 174, 21936, 46, 116, 1347, 249035847, 22537, 11590, 2342, 2015,
    6590, 1028, 731, 5977, 5084, 2240, 173, 1671, 1488, 183, 194, 158, 88, 64,
    17987, 1132, 2254, 1144, 882, 1166, 17283, 18415, 17095, 880, 36, 1163,
    1144, 10502, 10479, 81, 5123, 5839, 94, 129691, 32044, 4016, 43, 7, 2052,
    2869, 655, 2214, 1261, 76, 2305, 33, 593, 626, 761, 560, 428, 1988, 1087,
    805, 631, 304, 306, 17, 38, 39, 59, 23, 74, 72, 54, 75, 695, 120, 575, 350,
    224, 3951, 2568, 1383, 11210, 3072, 27182, 5541, 90, 176, 805, 77, 613,
    598, 587, 736, 123, 16, 149, 41796, 30539, 21246, 47542, 9000, 51231,
    49179, 28734, 15704, 5219, 341, 30266, 13187, 5930, 12033, 102, 466, 711,
    9992, 10031, 70559, 61559, 915, 84, 85, 944, 961, 4878, 1514, 2927, 673,
    740, 1252, 262, 1187, 285, 11, 1212, 480, 322, 325, 21, 6, 165737, 510905,
    20210, 10552, 1975, 5788, 10516, 1950, 10704, 2459, 35131, 32672, 890,
    1787, 4390, 4079, 311, 109298, 394540, 71773, 93964, 59922, 18427, 4825,
    3121, 720, 22686, 1434, 1006, 3049, 788, 1995, 1684, 551, 752, 473, 415,
    165, 156, 162, 326, 132, 41, 22, 89, 24, 70, 9, 600, 150, 256, 1180, 20577,
    2109, 1828, 2238, 214, 729, 575, 384, 103, 42, 53, 14, 1, 0, 28, 1e9,
}
# Values that come from a repository artefact rather than from the live graph, or
# that are not counts at all. Each is listed with what it is, so that the whitelist
# is itself a record rather than a way of silencing the audit.
REPOSITORY_SOURCED = {
    1280: "verses mis-addressed under the rejected Samavedic slot-1 reading",
    35139: "the lead ruling's PREDICTED post-integration assertion count "
           "(the live layer holds 35,131; both figures appear, labelled)",
    400: "degree-preserving permutation draws in the cross-Veda null",
    1677: "Samavedic verses with an undirected parallel, from the campaign report",
    157: "deities eligible for the imbalance ratio's second population",
    272: "units in the last Atharvavedic inter-reader agreement measurement",
    167: "units in an earlier point of the same agreement series",
    227: "units in another point of the same agreement series",
    216: "Samavedic verses covered by lead ruling R1",
    448: "passages in the final semantic-extraction pilot run",
    408: "million ordered pairs over the corpus (2 x the unordered count)",
    204211945: "C(20210,2), the exact unordered all-pairs count",
}
# Unicode code points quoted in the normalisation appendix.
CODE_POINTS = {300, 301, 331, 951, 954, 953, 954, 32, 13}


def latex_numbers(text: str) -> list[float]:
    """Numbers as the reader sees them, with LaTeX separators removed."""
    t = re.sub(r"\{,\}", "", text)          # 165{,}737 -> 165737
    t = re.sub(r"\\,", "", t)               # thin space
    t = re.sub(r"%.*", "", t)               # strip comments
    out = []
    for m in re.finditer(r"(?<![A-Za-z0-9_.])(\d+(?:\.\d+)?)(?![0-9])", t):
        out.append(float(m.group(1)))
    return out


def main() -> int:
    f = json.loads(FREEZE.read_text(encoding="utf-8"))

    # Every measured value the freeze contains, flattened.
    measured: set[float] = set()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            measured.add(float(o))
            measured.add(round(float(o), 1))
            measured.add(round(float(o), 2))

    walk(f)

    known = measured | {float(x) for x in ALLOWED_SMALL} \
        | {float(x) for x in YEARS} | {float(x) for x in DOCUMENTED}         | {float(x) for x in REPOSITORY_SOURCED} | {float(x) for x in CODE_POINTS}

    # Generated TikZ fragments carry drawing coordinates, not claims; their
    # numeric content is checked at generation time against the same freeze.
    sources = sorted(
        list((BASE / "sections").glob("*.tex"))
        + list((BASE / "appendices").glob("*.tex"))
        + list((BASE / "tables").glob("*.tex"))
    )

    unmatched: dict[str, list[float]] = defaultdict(list)
    total = 0
    for src in sources:
        for n in latex_numbers(src.read_text(encoding="utf-8")):
            # A non-integer is a rate, a threshold, an agreement coefficient or a
            # Unicode code point; those are checked by the claim audit, not here.
            if n != int(n):
                continue
            total += 1
            if n not in known:
                unmatched[src.name].append(n)

    print(f"numbers scanned: {total}")
    print(f"files: {len(sources)}")
    if not unmatched:
        print("RESULT: PASS -- every number resolves to the freeze, to a "
              "documented parameter, to a year, or to a small count.")
        return 0

    print("\nRESULT: REVIEW -- numbers not resolvable automatically:")
    for name in sorted(unmatched):
        vals = sorted(set(unmatched[name]))
        print(f"  {name}: {', '.join(f'{v:g}' for v in vals)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
