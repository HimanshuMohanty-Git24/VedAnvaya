"""Claim audit: find every sentence carrying an absolute, a superlative or a
word that asserts more than a measurement can.

This exists because of a defect the project itself shipped and documented: an
answer in which every figure was real and correctly cited was still misleading,
because the comparative words around the figures asserted a ranking the cited rows
did not contain. A numeric check cannot see that; only reading the sentence can.

The script does not decide anything. It prints every hit with its sentence so a
human can require evidence or soften the wording, and it reports how many hits are
in each file so the pass is repeatable.

    python figures-src/audit_claims.py            # summary
    python figures-src/audit_claims.py --full     # every sentence
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

# Trigger words, grouped by why they are dangerous.
TRIGGERS = {
    "superlative": r"\b(most|largest|greatest|best|worst|highest|lowest|"
                   r"strongest|weakest|leading|unprecedented|unique(?:ly)?)\b",
    "universal": r"\b(all|every|always|never|none|no one|nothing|any)\b",
    "totality": r"\b(complete(?:ly)?|exhaustive(?:ly)?|comprehensive(?:ly)?|"
                r"entire(?:ly)?|full[ly]?|whole)\b",
    "priority": r"\b(first|novel|new(?:ly)?|original|pioneering)\b",
    "epistemic": r"\b(proves?|proven|demonstrates?|establishes?|confirms?|"
                 r"verified|validated|accurate(?:ly)?|correct(?:ly)?|"
                 r"guarantee[sd]?|ensures?)\b",
    "discovery": r"\b(discovers?|discovered|reveals?|uncovers?|finds? that)\b",
    "gold": r"\b(gold standard|ground truth|independent(?:ly)?)\b",
}

# Sentences that are explicitly about what the project does NOT claim, or that
# quote the repository, are still printed but flagged as probably fine.
MITIGATED = re.compile(
    r"(does not|do not|cannot|never|no human|not a claim|refus|withheld|"
    r"withdraw|declin|not human gold|is not|are not|we do not|would be wrong|"
    r"not establish|nothing|only)", re.I
)


def sentences(text: str) -> list[str]:
    t = re.sub(r"%.*", "", text)                       # comments
    t = re.sub(r"\\(label|ref|cref|Cref|cite[pt]?)\{[^}]*\}", " ", t)
    t = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)              # remaining macros
    t = re.sub(r"[{}$&~^_\\]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if len(s.strip()) > 25]


def main() -> int:
    full = "--full" in sys.argv
    files = sorted(
        list((BASE / "sections").glob("*.tex"))
        + list((BASE / "appendices").glob("*.tex"))
        + list((BASE / "tables").glob("*.tex"))
    )
    by_kind: Counter[str] = Counter()
    by_file: Counter[str] = Counter()
    unmitigated: list[tuple[str, str, str]] = []

    for f in files:
        for s in sentences(f.read_text(encoding="utf-8")):
            hits = [k for k, pat in TRIGGERS.items() if re.search(pat, s, re.I)]
            if not hits:
                continue
            by_file[f.name] += 1
            for k in hits:
                by_kind[k] += 1
            if not MITIGATED.search(s):
                unmitigated.append((f.name, ",".join(hits), s))

    print(f"files scanned: {len(files)}")
    print(f"sentences with at least one trigger: {sum(by_file.values())}")
    print("\nby trigger class:")
    for k, n in by_kind.most_common():
        print(f"  {n:>4}  {k}")
    print(f"\nsentences with a trigger and NO hedging/refusal marker: "
          f"{len(unmitigated)}")
    print("These are the ones a reviewer must read; the rest are sentences about "
          "what the project declines to claim.\n")
    for name, kinds, s in unmitigated if full else unmitigated[:40]:
        print(f"[{kinds}] {name}")
        print(f"    {s[:240]}")
    if not full and len(unmitigated) > 40:
        print(f"\n... {len(unmitigated) - 40} more; re-run with --full")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
