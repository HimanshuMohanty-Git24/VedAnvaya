"""Traditional-apparatus adapters for the Sukla Yajurveda (Vajasaneyi Samhita).

What the tradition actually records for the Yajurveda
----------------------------------------------------
The Sukla Yajurveda has its own *Sarvanukramasutra* ascribed to Katyayana. It is NOT the
Rigvedic Sarvanukramani and Rigvedic rules do not transfer. Its opening sutra declares
its own fields and its own limits:

    ... rsi-devata-chandamsy anukramisyamo, yajusam aniyataksaratvad ekesam chando na
    vidyate ...

That is: it indexes rsi, devata and chandas, *and* it states that because the yajus have
no fixed syllable count, **for some of them no metre exists at all**. It also lists among
the devatas ritual implements -- anas (cart), sakha (branch), ukha (pot), samya, kapala,
udukhala -- as *pratimabhutah*, standing as representations. So:

* ``chandas`` is legitimately ASSERTED-ABSENT for many mantras, which is different from
  unknown;
* the Yajurveda ``devata`` co-domain includes ritual objects and is therefore NOT the
  same co-domain as the Rigvedic deity set;
* ``rsi`` is scoped by ritual block, with ``vivasvan`` as a stated default for the whole
  samhita, refined *pratikarma-vibhagena brahmanusarena* -- by ritual act, following the
  Brahmana;
* ``viniyoga`` (ritual application) is explicitly deferred to the Katyayana Srautasutra
  (``viniyogah kalpakaroktah``) and is not in the anukramani at all.

None of this is inferred here. This module extracts only what a source states verbatim.

What this module does and refuses to do
---------------------------------------
``RishiIndexAdapter`` parses the Wikisource ``rsisuci`` page, which is a genuinely
tabular per-mantra rsi index of the form ``<rsi> <adhyaya>.<mantra ranges>``. That is
mechanical and is extracted.

The ``sarvanukramani`` page is continuous sutra prose grouped by anuvaka. It is
snapshotted and carried as evidence text, and **no per-mantra rsi/devata/chandas claim is
derived from it by machine**. Resolving sutra prose to per-mantra claims requires expert
philological reading; doing it with a language model is forbidden by the project's core
principle and is not attempted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.ingest.adapters.yajurveda_wikisource import (
    PageRevision,
    YajurvedaWikisourceAdapter,
    content_api_url,
    parse_mixed_digits,
)
from vedagraph.models import StagingTextRecord

PARSER_VERSION = "wikisource-sa-vsm-apparatus-v1"

RISHI_INDEX_TITLE = "शुक्लयजुर्वेदः/ऋषिसूची"
SARVANUKRAMANI_TITLE = "शुक्लयजुर्वेदः/सर्वानुक्रमणी"

#: The index writes ranges with BOTH U+002D HYPHEN-MINUS and U+2013 EN DASH, sometimes in
#: the same line. Both are range separators here. The set also carries EM DASH and MINUS
#: SIGN because the page uses them interchangeably.
_RANGE_DASHES = "-–—−"  # noqa: RUF001  (hyphen, en dash, em dash, minus)

# "<name> <adhyaya>.<spec>" then an optional danda. The name may carry a parenthetical
# qualifier, e.g. "angirasah(virupa-)", which is kept verbatim as part of the value and
# never decomposed into components.
#: A member the page prints but that states no mantra number. The index uses a bare
#: asterisk once (line 90, "gotama: 25.17-22, 24-26, 28-47, *"). It is NOT expanded and
#: NOT guessed: it is dropped from the expansion and reported, so the line's readable
#: members are still ingested instead of the whole line being lost.
_PLACEHOLDER_MEMBER = "*"

_INDEX_LINE = re.compile(
    r"^(?P<name>[^\d०-९]+?)\s*[:：]?\s*"  # noqa: RUF001
    r"(?P<adhyaya>[0-9०-९]+)\s*\.\s*"  # noqa: RUF001
    r"(?P<spec>[0-9०-९\s,*" + _RANGE_DASHES + r"]+?)"  # noqa: RUF001
    r"\s*[।॥]*\s*$"
)


@dataclass(frozen=True)
class RishiAssertion:
    """One ``rsi`` claim the index states for one mantra.

    ``scope_note`` records the shape the source used, so a claim that came from a printed
    range is never later mistaken for a per-mantra statement.
    """

    adhyaya: int
    mantra: int
    rishi: str
    source_line: str
    line_number: int
    scope_note: str


@dataclass(frozen=True)
class RishiIndexParse:
    revision: PageRevision
    assertions: list[RishiAssertion]
    unparsed_lines: list[tuple[int, str]]
    adhyayas_covered: list[int]
    #: ``(line_number, member)`` for a spec member the page prints but that states no
    #: mantra number. Kept separate from ``unparsed_lines`` because the line WAS read and
    #: its other members WERE ingested; only this member is missing.
    unreadable_spec_members: list[tuple[int, str]] = field(default_factory=list)


def _spec_members(spec: str) -> list[str]:
    """Split a spec into its members on commas AND on whitespace.

    The printed index separates members with a comma, but four lines drop one and leave
    two members touching -- "27-31 36" for gr̥tsamada at 11, "23 27" for prajapati at 25.
    A comma-only split reads those as a single unreadable member and loses the WHOLE line,
    which is how adhyaya 25 came to have zero r̥ṣi coverage despite the index stating it
    twice.

    A member CAN contain a space, though, and the naive version of this split lost a line
    that the comma-only split had read correctly: bharadvaja at 29 is printed "38 -60",
    with the space before the dash rather than around a missing comma. Splitting that on
    whitespace yields "38" and "-60", and "-60" is not a range. So whitespace adjacent to
    a dash is collapsed FIRST, which binds a range back together; only whitespace that
    separates two complete members then remains, and that is the separator this split is
    for. Net effect measured over the whole index: adhyaya 25 recovered, no line lost.
    """
    joined = re.sub(rf"\s*([{_RANGE_DASHES}])\s*", r"\1", spec)
    return [member for member in re.split(r"[,\s]+", joined) if member]


def _expand_spec(spec: str) -> tuple[list[tuple[int, str]], list[str]]:
    """Expand "15-22, 24-30" into mantra numbers, tagging how each was stated.

    Returns ``(expanded, unreadable_members)``. A member that states no mantra number is
    reported rather than expanded or guessed.
    """
    results: list[tuple[int, str]] = []
    unreadable: list[str] = []
    for chunk in _spec_members(spec):
        piece = chunk.strip()
        if not piece:
            continue
        if piece == _PLACEHOLDER_MEMBER:
            unreadable.append(piece)
            continue
        # The page writes some ranges with a doubled dash ("2.1--16"). Collapsing runs of
        # dashes is safe because a dash is only ever a range separator in this index.
        piece = re.sub(f"[{_RANGE_DASHES}]{{2,}}", "-", piece)
        bounds = re.split(f"[{_RANGE_DASHES}]", piece)
        if len(bounds) == 1:
            results.append((parse_mixed_digits(bounds[0].strip()), "SINGLE_MANTRA"))
            continue
        if len(bounds) != 2:
            raise ValueError(f"cannot read a range from {piece!r}")
        start = parse_mixed_digits(bounds[0].strip())
        end = parse_mixed_digits(bounds[1].strip())
        if end < start:
            raise ValueError(f"descending range {piece!r}")
        results.extend((value, f"MANTRA_RANGE {start}-{end}") for value in range(start, end + 1))
    return results, unreadable


class RishiIndexAdapter(SourceAdapter):
    """Parse the Wikisource per-mantra rsi index for the Vajasaneyi Samhita."""

    source_id = "WIKISOURCE_SA"

    def __init__(self, *, source_artifact_id: str = "WIKISOURCE_SA.YV.VSM.RISHISUCI") -> None:
        self.source_artifact_id = source_artifact_id
        self._page = YajurvedaWikisourceAdapter(source_artifact_id=source_artifact_id)

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        if scope != "VSM.APPARATUS.RISHI":
            raise ValueError("scope must be VSM.APPARATUS.RISHI")
        return [
            DiscoveredResource(
                source_id=self.source_id,
                url=content_api_url(RISHI_INDEX_TITLE),
                locator=RISHI_INDEX_TITLE,
                media_type="application/json",
            )
        ]

    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        raise NotImplementedError("the rsi index carries metadata, not Sanskrit text")

    def parse_rishi_index(self, snapshot_path: Path) -> RishiIndexParse:
        revision = self._page.read_revision(snapshot_path)
        assertions: list[RishiAssertion] = []
        unparsed: list[tuple[int, str]] = []
        unreadable_members: list[tuple[int, str]] = []
        for line_number, raw in enumerate(revision.content.split("\n"), start=1):
            line = re.sub(r"<[^>]+>", "", raw).strip()
            if not line:
                continue
            match = _INDEX_LINE.match(line)
            if match is None:
                unparsed.append((line_number, line[:160]))
                continue
            name = " ".join(match.group("name").split())
            try:
                adhyaya = parse_mixed_digits(match.group("adhyaya"))
                expanded, unreadable = _expand_spec(match.group("spec"))
            except ValueError:
                unparsed.append((line_number, line[:160]))
                continue
            unreadable_members.extend((line_number, member) for member in unreadable)
            if not name or not expanded:
                unparsed.append((line_number, line[:160]))
                continue
            assertions.extend(
                RishiAssertion(
                    adhyaya=adhyaya,
                    mantra=mantra,
                    rishi=name,
                    source_line=line,
                    line_number=line_number,
                    scope_note=scope_note,
                )
                for mantra, scope_note in expanded
            )
        covered = sorted({item.adhyaya for item in assertions})
        return RishiIndexParse(
            revision=revision,
            assertions=assertions,
            unparsed_lines=unparsed,
            adhyayas_covered=covered,
            unreadable_spec_members=unreadable_members,
        )
