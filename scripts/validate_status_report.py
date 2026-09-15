#!/usr/bin/env python3
"""Guard the resume contract against silent accretion.

STATUS.md is the file a resuming session is told to work from. It reached 935 lines
carrying three "## Registry" sections and two "## Done", because successive turns each
located a heading and replaced through to the next one -- and several replacement blocks
themselves ended with a heading, so the edits accumulated instead of superseding.

Nothing failed at the time. That is the whole problem: a resume document degrades
invisibly, and it is read with the expectation of being current, so a contradictory one is
worse than none.

This checks the two properties that corruption violated and a reader cannot see at a
glance: every heading appears exactly once, and the file has not grown past the point where
anyone will actually read it.

Usage:
    python scripts/validate_status_report.py [PATH] [--max-lines N] [--json OUT]

Exit 0 if the report is sound, 1 if not, 2 if the file is missing.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter

DEFAULT_PATH = pathlib.Path("docs/reports/data-completeness/STATUS.md")

#: Past which nobody reads the whole thing, so drift stops being visible. The number is not
#: sacred -- the guard is. Raise it deliberately with --max-lines and say why in the commit.
DEFAULT_MAX_LINES = 300

#: Sections whose duplication is what corruption looked like last time. A heading absent
#: from the file is not an error -- the canonical heading set is allowed to evolve -- but a
#: heading present twice is, always, because two of them cannot both be current.
SINGLETON_HINTS = (
    "Registry",
    "Done",
    "Running",
    "Remaining",
    "Next",
    "Blocking",
    "Current wave",
    "Where the campaign is",
)

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")


def check(path: pathlib.Path, max_lines: int) -> tuple[list[str], dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    failures: list[str] = []

    # Headings inside fenced code blocks are content, not structure.
    in_fence = False
    headings: list[tuple[int, int, str]] = []
    for number, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING.match(line)
        if match:
            headings.append((number, len(match.group(1)), match.group(2)))

    if in_fence:
        failures.append("a fenced code block is never closed, so heading detection is unreliable")

    titles = [(level, title) for _, level, title in headings if level == 1]
    if len(titles) != 1:
        failures.append(f"expected exactly one top-level title, found {len(titles)}")

    # Every heading, at every level, must be unique. Two headings with one name cannot both
    # be current, whatever they are called.
    counts = Counter(title for _, _, title in headings)
    for title, count in sorted(counts.items()):
        if count > 1:
            where = [str(n) for n, _, t in headings if t == title]
            failures.append(
                f'heading "{title}" appears {count} times (lines {", ".join(where)}); '
                f"two sections of one name cannot both be current"
            )

    # The named ones get a louder message, because these are the sections that actually
    # duplicated and the ones a stale copy misleads about.
    for hint in SINGLETON_HINTS:
        matching = [t for t in counts if hint.lower() in t.lower()]
        total = sum(counts[t] for t in matching)
        if total > 1 and len(matching) > 1:
            failures.append(
                f'{total} sections mention "{hint}" ({", ".join(sorted(matching))}); '
                f"the resume contract needs one place to look"
            )

    if len(lines) > max_lines:
        failures.append(
            f"{len(lines)} lines exceeds the {max_lines}-line threshold. Rewrite the file "
            f"whole rather than appending, or raise --max-lines deliberately"
        )

    stats: dict[str, object] = {
        "path": str(path),
        "lines": len(lines),
        "max_lines": max_lines,
        "headings": len(headings),
        "duplicate_headings": sorted(t for t, c in counts.items() if c > 1),
        "ok": not failures,
    }
    return failures, stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=str(DEFAULT_PATH))
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    parser.add_argument("--json", default="")
    args = parser.parse_args()

    path = pathlib.Path(args.path)
    if not path.is_file():
        print(f"FATAL: {path} does not exist")
        return 2

    failures, stats = check(path, args.max_lines)

    print()
    print(f"  {path}")
    print(
        f"  {stats['lines']} lines (threshold {stats['max_lines']}), {stats['headings']} headings"
    )
    print()
    if failures:
        for failure in failures:
            print(f"  [FAIL] {failure}")
        print()
        print("  The resume contract is not sound. Rewrite the file whole; do not splice.")
    else:
        print("  PASS. Every heading is unique and the file is still short enough to read.")
    print()

    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps({**stats, "failures": failures}, indent=2), encoding="utf-8"
        )

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
