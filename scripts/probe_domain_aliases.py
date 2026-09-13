"""Per-alias precision audit for the domain lexicon.

Answers one question about one candidate alias before it is committed to the registry:
*what does it actually match, and is every match the word we meant?*

This exists because corpus-wide sampling cannot answer that. A lexicon audit that draws a
random sample of matched rows and reports 97% precision is consistent with one alias being
83% wrong, because that alias's rows are a small share of the sample and its errors are
invisible inside a good aggregate. Precision has to be measured per alias or it is not
measured at all -- which is also why
:data:`~vedagraph.enrich.concepts.SANDHI_SUPPRESSED_ALIASES` is a list of individually
audited strings with a recorded host word each, rather than a length threshold.

Two passes are reported per alias, because the matcher runs two and they have different
failure modes:

*Token pass.* The alias must equal a whole word of the folded surface. Failure mode is
homonymy -- the right string, the wrong word.

*Sandhi pass.* The alias may appear anywhere in the boundary-free surface. Failure mode is
containment -- ``vāta`` ("wind") inside ``devātā``, ``ṛtasya`` inside ``ghṛtasya``. The
report therefore lists the **host tokens** each substring hit was found inside, which is
the only view in which a containment error is obvious.

Usage::

    python scripts/probe_domain_aliases.py yava hiraṇya ayas
    python scripts/probe_domain_aliases.py --file candidates.txt
    python scripts/probe_domain_aliases.py --collisions yava
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from collections import Counter
from dataclasses import dataclass, field

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.enrich.concepts import (  # noqa: E402
    MIN_SANDHI_ALIAS_CHARS,
    fold_alias,
    load_concepts,
)
from vedagraph.enrich.corpus import VEDAS, Corpus, load_corpus  # noqa: E402
from vedagraph.enrich.surfaces import render_for_display  # noqa: E402

#: Host tokens shown per alias on the sandhi pass. Enough to see whether the hits are one
#: recurring containment error or a genuine spread.
_MAX_HOSTS_SHOWN = 12

#: Example passages shown per alias, so a reader can go and check the verse.
_MAX_EXAMPLES = 4


@dataclass
class AliasReport:
    """What one alias matched, split by pass and by Veda."""

    alias: str
    folded: str
    token_hits: Counter[str] = field(default_factory=Counter)
    sandhi_hits: Counter[str] = field(default_factory=Counter)
    #: Folded host token -> how many times the alias was found inside it.
    hosts: Counter[str] = field(default_factory=Counter)
    examples: list[tuple[str, str]] = field(default_factory=list)

    @property
    def token_total(self) -> int:
        return sum(self.token_hits.values())

    @property
    def sandhi_total(self) -> int:
        return sum(self.sandhi_hits.values())

    @property
    def sandhi_eligible(self) -> bool:
        return len(self.folded) >= MIN_SANDHI_ALIAS_CHARS

    @property
    def intrusion_share(self) -> float:
        """Share of substring hits where the alias sits *inside* a longer word.

        The distinction that matters is not "is the host the bare alias" -- almost no
        Sanskrit word appears uninflected -- but *where* in the host it sits. ``vātasya``
        and ``vātam`` begin with ``vāta`` and are its genitive and accusative: good hosts.
        ``jīvātave`` merely contains it, and ``payasā`` merely contains ``ayas``: those are
        intrusions, and a different word.

        Compound-final members make this a signal rather than a verdict -- ``somapā``
        ends in a real ``pā`` -- so a high value means *read the host list*, not *reject*.
        """
        total = sum(self.hosts.values())
        if not total:
            return 0.0
        intruding = sum(
            count for host, count in self.hosts.items() if not host.startswith(self.folded)
        )
        return intruding / total


def probe(alias: str, corpus: Corpus) -> AliasReport:
    """Measure one alias against every mantra of the four Vedas."""
    folded = fold_alias(alias)
    report = AliasReport(alias=alias, folded=folded)
    if not folded:
        return report

    for mantra in corpus.mantras:
        veda = mantra.veda
        tokens = mantra.surfaces.tokens
        if folded in tokens:
            report.token_hits[veda] += 1
            if len(report.examples) < _MAX_EXAMPLES:
                position = tokens.index(folded)
                window = tokens[max(0, position - 2) : position + 3]
                report.examples.append((mantra.passage_key, render_for_display(" ".join(window))))
        # The sandhi pass is reported for every alias regardless of eligibility, so the
        # length floor can be seen to be doing something rather than assumed to.
        if folded in mantra.surfaces.sandhi_insensitive:
            report.sandhi_hits[veda] += 1
            for token in tokens:
                if folded in token:
                    report.hosts[token] += 1
    return report


def _format(report: AliasReport) -> str:
    lines: list[str] = []
    shown = render_for_display(report.folded)
    lines.append(f"\n=== {report.alias}   (folded: {shown}, {len(report.folded)} chars) ===")
    if not report.folded:
        lines.append("  FOLDS TO NOTHING -- unusable as an alias")
        return "\n".join(lines)

    by_veda = "  ".join(f"{v}={report.token_hits.get(v, 0)}" for v in VEDAS)
    lines.append(f"  token pass : {report.token_total:>5} mantras   [{by_veda}]")

    eligible = "eligible" if report.sandhi_eligible else f"BLOCKED (<{MIN_SANDHI_ALIAS_CHARS})"
    by_veda_s = "  ".join(f"{v}={report.sandhi_hits.get(v, 0)}" for v in VEDAS)
    lines.append(f"  sandhi pass: {report.sandhi_total:>5} mantras   [{by_veda_s}]  {eligible}")

    if report.hosts:
        share = report.intrusion_share
        verdict = (
            "INTRUSION RISK -- read the hosts"
            if share >= 0.5
            else "check the hosts"
            if share >= 0.15
            else "hosts look like inflections"
        )
        lines.append(f"  intrusion share: {share:6.1%}  <- {verdict}")
        lines.append("  hosts (folded token the alias was found inside):")
        for host, count in report.hosts.most_common(_MAX_HOSTS_SHOWN):
            if host == report.folded:
                flag = "  <-- the alias itself"
            elif host.startswith(report.folded):
                flag = "  (inflection/compound-initial)"
            else:
                flag = "  <-- INTRUSION"
            lines.append(f"      {count:>5}x  {render_for_display(host)}{flag}")
        if len(report.hosts) > _MAX_HOSTS_SHOWN:
            lines.append(f"      ... and {len(report.hosts) - _MAX_HOSTS_SHOWN} more hosts")

    if report.examples:
        lines.append("  examples (token pass):")
        for key, quote in report.examples:
            lines.append(f"      {key}  {quote}")
    if report.token_total == 0 and report.sandhi_total == 0:
        lines.append("  NO MATCHES ANYWHERE -- this alias would contribute nothing")
    return "\n".join(lines)


def _collisions(aliases: list[str]) -> str:
    """Report aliases already claimed by the existing lexicon.

    The registry refuses an alias claimed by two entities, so a collision found here is a
    load-time failure found early rather than a silent misassignment found never.
    """
    existing: dict[str, str] = {}
    for concept in load_concepts(PROJECT_ROOT):
        for alias in concept.aliases_sa:
            existing[fold_alias(alias)] = concept.concept_id
    lines = ["\n=== COLLISIONS WITH data/registry/concepts.yaml ==="]
    clashes = 0
    for alias in aliases:
        owner = existing.get(fold_alias(alias))
        if owner:
            clashes += 1
            lines.append(f"  {alias!r} is already claimed by {owner}")
    if not clashes:
        lines.append(f"  none of the {len(aliases)} probed aliases collide")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aliases", nargs="*", help="IAST aliases to probe")
    parser.add_argument("--file", type=pathlib.Path, help="file with one alias per line")
    parser.add_argument(
        "--collisions", action="store_true", help="also check against the live registry"
    )
    args = parser.parse_args()

    aliases = list(args.aliases)
    if args.file:
        aliases.extend(
            line.strip()
            for line in args.file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        )
    if not aliases:
        parser.error("give at least one alias, or --file")

    corpus = load_corpus(PROJECT_ROOT)
    counts = corpus.counts()
    sys.stdout.write(
        f"corpus: {sum(counts.values())} mantras  "
        + "  ".join(f"{v}={counts.get(v, 0)}" for v in VEDAS)
        + "\n"
    )
    for alias in aliases:
        sys.stdout.write(_format(probe(alias, corpus)) + "\n")
    if args.collisions:
        sys.stdout.write(_collisions(aliases) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
