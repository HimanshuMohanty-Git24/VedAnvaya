"""Add the verse-level coverage state to vedagraph.domain.translation_semantics.

GAP-TRANSLATION-004's measure is ``NOT (m)-[:HAS_TRANSLATION]->()``. That is the boolean
edge test this module's own docstring was written to end -- it reports the second verse of
every paired-dvipada unit as untranslated, and reaching 0 means attaching an own edge to
each even verse of RV 1.65-1.70, which republishes one Griffith unit as two independent
per-verse translations. That is GAP-TRANSLATION-006's defect exactly.

``classify`` answers "what kind of coverage does THIS TRANSLATION give". Nothing answered
"what is the terminal coverage state of THIS VERSE", and in particular nothing had a name
for the negative cases, which is why the negative case kept being expressed as the absence
of an edge. :func:`verse_coverage_state` is that missing half, added HERE rather than in a
second module, because three mechanisms answering this question three ways is the failure
this file was created to fix.

Appended with explicit ``\\n`` in binary: the file is 215 LF lines with no CRLF, and text
mode on this platform would rewrite every one of them.
"""

from __future__ import annotations

import pathlib

MODULE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "src"
    / "vedagraph"
    / "domain"
    / "translation_semantics.py"
)

ADDITION = '''

class VerseCoverageState(StrEnum):
    """The terminal translation-coverage state of one verse.

    :class:`TranslationCoverageKind` says what a translation gives a verse.  This says what
    a verse *has*, and it has names for the negative cases -- which is the whole point.  A
    verse with no rendering was previously expressible only as the absence of an edge, and
    an absence carries no reason, so every consumer that met one had to guess whether the
    source was unacquired, the row was withheld, or the print unit simply spanned elsewhere.

    The values are not rankable and no arithmetic over them is meaningful except counting.
    In particular :attr:`REUSED_RENDERING` must never be totalled into a corpus's own
    English coverage: all 173 Samavedic renderings in this graph are Griffith's Rigvedic
    English attached to verses whose Sanskrit is verified identical, so the Samaveda's
    independent English translation count is zero and a total that says 173 is wrong.
    """

    #: This verse has its own 1:1 English rendering.
    DEDICATED_TRANSLATION = "DEDICATED_TRANSLATION"
    #: This verse anchors a print unit that spans it and at least one other verse.
    RANGE_TRANSLATION_ANCHOR = "RANGE_TRANSLATION_ANCHOR"
    #: This verse carries no edge and is named in another verse's range span.
    RANGE_COVERED = "RANGE_COVERED"
    #: The only rendering reaching this verse is aligned to a hymn or a larger container.
    CONTAINER_TRANSLATION = "CONTAINER_TRANSLATION"
    #: This verse carries another corpus's published rendering of identical Sanskrit.
    REUSED_RENDERING = "REUSED_RENDERING"
    #: Every rendering reaching this verse is in a language other than English.
    NON_ENGLISH_ONLY = "NON_ENGLISH_ONLY"
    #: No rendering reaches it, but a translated parallel with identical text exists.
    UNCOVERED_REUSABLE_PARALLEL_AVAILABLE = "UNCOVERED_REUSABLE_PARALLEL_AVAILABLE"
    #: No rendering of any kind reaches it and no reusable parallel exists.
    UNCOVERED_NO_RENDERING_REACHES_IT = "UNCOVERED_NO_RENDERING_REACHES_IT"


#: The states under which a reader is shown some English text for the verse. Membership is
#: NOT a claim that the corpus translated the verse itself -- see
#: :data:`INDEPENDENT_ENGLISH_STATES` for that, and note the two sets differ by exactly
#: ``REUSED_RENDERING``.
ENGLISH_REACHES_THE_READER: Final[frozenset[VerseCoverageState]] = frozenset(
    {
        VerseCoverageState.DEDICATED_TRANSLATION,
        VerseCoverageState.RANGE_TRANSLATION_ANCHOR,
        VerseCoverageState.RANGE_COVERED,
        VerseCoverageState.CONTAINER_TRANSLATION,
        VerseCoverageState.REUSED_RENDERING,
    }
)

#: The states that may be totalled into a corpus's OWN English coverage.
INDEPENDENT_ENGLISH_STATES: Final[frozenset[VerseCoverageState]] = frozenset(
    {
        VerseCoverageState.DEDICATED_TRANSLATION,
        VerseCoverageState.RANGE_TRANSLATION_ANCHOR,
        VerseCoverageState.RANGE_COVERED,
        VerseCoverageState.CONTAINER_TRANSLATION,
    }
)

#: The states in which no rendering reaches the verse at all.
UNCOVERED_STATES: Final[frozenset[VerseCoverageState]] = frozenset(
    {
        VerseCoverageState.UNCOVERED_REUSABLE_PARALLEL_AVAILABLE,
        VerseCoverageState.UNCOVERED_NO_RENDERING_REACHES_IT,
    }
)


def verse_coverage_state(
    verse_key: str,
    translations: Sequence[Mapping[str, Any]],
    *,
    range_covered: bool = False,
    reusable_parallel: bool = False,
) -> VerseCoverageState:
    """The terminal coverage state of ``verse_key``.

    ``translations`` is every :class:`Translation` node hanging off this verse, as property
    mappings. ``range_covered`` says whether some OTHER verse's range span names this key --
    the caller supplies it because answering it needs a scan this function must not do per
    verse. ``reusable_parallel`` says whether a verified-identical translated parallel
    exists, which distinguishes a verse nobody has rendered from one whose rendering is
    merely not attached.

    Precedence runs from the strongest claim about this verse to the weakest, and the
    uncovered states come last so a verse with any rendering can never be reported as
    uncovered:

    >>> verse_coverage_state("K", [{"alignment_level": "MANTRA", "language": "en"}])
    <VerseCoverageState.DEDICATED_TRANSLATION: 'DEDICATED_TRANSLATION'>
    >>> verse_coverage_state("K", [], range_covered=True)
    <VerseCoverageState.RANGE_COVERED: 'RANGE_COVERED'>
    >>> verse_coverage_state("K", [])
    <VerseCoverageState.UNCOVERED_NO_RENDERING_REACHES_IT: 'UNCOVERED_NO_RENDERING_REACHES_IT'>

    A reused rendering outranks nothing and is outranked by nothing English of this verse's
    own, which is why it is tested before the container case but after the dedicated one.
    """
    kinds: list[tuple[TranslationCoverageKind, Mapping[str, Any]]] = [
        (classify(props, asked_about=verse_key), props) for props in translations
    ]
    english = [(k, p) for k, p in kinds if p.get("language") == ENGLISH]

    for kind, _ in english:
        if kind is TranslationCoverageKind.DEDICATED_TRANSLATION:
            return VerseCoverageState.DEDICATED_TRANSLATION
    for kind, _ in english:
        if kind is TranslationCoverageKind.RANGE_TRANSLATION:
            return VerseCoverageState.RANGE_TRANSLATION_ANCHOR
    for kind, _ in english:
        if kind is TranslationCoverageKind.REUSED_RENDERING:
            return VerseCoverageState.REUSED_RENDERING
    for kind, _ in english:
        if kind is TranslationCoverageKind.CONTAINER_TRANSLATION:
            return VerseCoverageState.CONTAINER_TRANSLATION
    if range_covered:
        return VerseCoverageState.RANGE_COVERED
    if kinds:
        return VerseCoverageState.NON_ENGLISH_ONLY
    if reusable_parallel:
        return VerseCoverageState.UNCOVERED_REUSABLE_PARALLEL_AVAILABLE
    return VerseCoverageState.UNCOVERED_NO_RENDERING_REACHES_IT
'''


def main() -> None:
    raw = MODULE.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("refusing: file now contains CRLF and this script assumes LF")
    if b"class VerseCoverageState" in raw:
        raise SystemExit("VerseCoverageState already present; refusing to duplicate")
    MODULE.write_bytes(raw + ADDITION.encode("utf-8"))
    print(f"appended {len(ADDITION.encode('utf-8'))} bytes to {MODULE.name}")


if __name__ == "__main__":
    main()
