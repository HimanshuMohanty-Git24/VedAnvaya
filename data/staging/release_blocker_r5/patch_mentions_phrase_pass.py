"""Add the phrase pass to vedagraph.domain.mentions, so the 6 new edges are reproducible.

GAP-ENTITY_COVERAGE-007 clause 1 asks that phrase matching reach multi-word entities.
``_token_hits`` is ``index.token.get(token)`` over one folded token at a time, so a
registered alias containing a space can never equal a key: the phrase never fires, and the
registry documents the consequence itself for the third soma pressing --

    All six were read and all six are this act -- and none of them is reachable, because
    the third pressing is the only one of the three the corpus never writes as one word.

Landing 6 MENTIONS_ENTITY edges from a staging script would have left the layer's own
generator unable to reproduce them, which is the defect this project recorded as "a fix that
never reaches the shipped artifact". So the pass goes here.

DESIGN. A phrase is matched as a run of CONSECUTIVE whole tokens, and both ends must fall on
a token boundary, so a phrase can never fire inside a longer word the way the Samaveda-only
sandhi substring pass can. It is scored ABOVE the token path: a two-token match is strictly
more specific than a one-token match, not less. Phrase aliases are read from a separate
registry field, so a multi-word string can never silently land in ``index.token`` where it
would match nothing forever.
"""

from __future__ import annotations

import pathlib

MODULE = (
    pathlib.Path(__file__).resolve().parents[3]
    / "src"
    / "vedagraph"
    / "domain"
    / "mentions.py"
)

# --- 1. the score constant, beside the two that already exist ---------------
SCORE_ANCHOR = '''#: Context tokens kept either side of a hit, so the quote is evidence rather than the verse.
_CONTEXT_TOKENS: Final = 2'''

SCORE_NEW = '''#: A run of consecutive whole Sanskrit tokens. Scored ABOVE the single-token path, because
#: a two-token match is strictly more specific than a one-token match: ``tṛtīye savane`` can
#: only be the third pressing, while ``savane`` alone is any of the three. Both ends are
#: required to fall on a token boundary, so unlike the Sāmaveda sandhi pass this can never
#: fire inside a longer word.
_PHRASE_SCORE: Final = 0.95

#: Context tokens kept either side of a hit, so the quote is evidence rather than the verse.
_CONTEXT_TOKENS: Final = 2'''

# --- 2. the path name -------------------------------------------------------
PATH_ANCHOR = '''#: A substring match on the boundary-free surface, Sāmaveda only. Materially weaker: the
#: surface has no word boundaries, so a hit may span two words. Scored well below the
#: token path and carrying its path in the method, so it can be filtered out wholesale.
_SANDHI_SCORE: Final = 0.60'''

PATH_NEW = '''#: A substring match on the boundary-free surface, Sāmaveda only. Materially weaker: the
#: surface has no word boundaries, so a hit may span two words. Scored well below the
#: token path and carrying its path in the method, so it can be filtered out wholesale.
_SANDHI_SCORE: Final = 0.60

#: A multi-token Sanskrit match, available in every Veda.
_PATH_PHRASE: Final = "sanskrit-phrase"'''

# --- 3. MentionIndex gains a phrase table ----------------------------------
INDEX_ANCHOR = '''    token: dict[str, str]
    sandhi: tuple[tuple[str, str], ...]
    #: Folded aliases that are also a Devatā label form. Not excluded -- recorded.
    theonyms: frozenset[str]

    @property
    def counts(self) -> dict[str, int]:
        return {
            "token_aliases": len(self.token),
            "sandhi_aliases": len(self.sandhi),
            "theonym_aliases": len(self.theonyms),
        }'''

INDEX_NEW = '''    token: dict[str, str]
    sandhi: tuple[tuple[str, str], ...]
    #: Folded aliases that are also a Devatā label form. Not excluded -- recorded.
    theonyms: frozenset[str]
    #: Multi-token folded aliases, as a token tuple paired with its entity. Held apart from
    #: ``token`` rather than in it: a string with a space in it can never equal a single
    #: folded token, so a multi-word alias in ``token`` is an alias that matches nothing
    #: forever and says nothing about it.
    phrase: tuple[tuple[tuple[str, ...], str], ...] = ()

    @property
    def counts(self) -> dict[str, int]:
        return {
            "token_aliases": len(self.token),
            "sandhi_aliases": len(self.sandhi),
            "theonym_aliases": len(self.theonyms),
            "phrase_aliases": len(self.phrase),
        }'''

# --- 4. build_index reads the phrase field ---------------------------------
BUILD_ANCHOR = '''def build_index(entities: Sequence[ConceptRow], devata_labels: Iterable[str] = ()) -> MentionIndex:
    """Invert the lexicon, and mark which aliases are also deity names."""
    theonym_forms = devata_label_forms(devata_labels)
    token: dict[str, str] = {}
    sandhi: list[tuple[str, str]] = []
    theonyms: set[str] = set()
    for entity in entities:
        for alias in entity.aliases_sa:
            folded = fold_alias(alias)
            if not folded:
                continue
            token[folded] = entity.concept_id
            if folded in theonym_forms:
                theonyms.add(folded)
            if (
                len(folded) >= MIN_SANDHI_ALIAS_CHARS
                and alias not in SANDHI_SUPPRESSED_ALIASES
                and alias not in V2_SANDHI_SUPPRESSED_ALIASES
            ):
                sandhi.append((folded, entity.concept_id))
    return MentionIndex(token=token, sandhi=tuple(sorted(sandhi)), theonyms=frozenset(theonyms))'''

BUILD_NEW = '''def build_index(entities: Sequence[ConceptRow], devata_labels: Iterable[str] = ()) -> MentionIndex:
    """Invert the lexicon, and mark which aliases are also deity names.

    A registered alias containing whitespace goes to the PHRASE table and never to
    ``token``. It is sorted there before it is used, so an alias that happens to be a
    prefix of a longer one cannot win by registry order.
    """
    theonym_forms = devata_label_forms(devata_labels)
    token: dict[str, str] = {}
    sandhi: list[tuple[str, str]] = []
    theonyms: set[str] = set()
    phrase: list[tuple[tuple[str, ...], str]] = []
    for entity in entities:
        for alias in entity.aliases_sa:
            folded = fold_alias(alias)
            if not folded:
                continue
            token[folded] = entity.concept_id
            if folded in theonym_forms:
                theonyms.add(folded)
            if (
                len(folded) >= MIN_SANDHI_ALIAS_CHARS
                and alias not in SANDHI_SUPPRESSED_ALIASES
                and alias not in V2_SANDHI_SUPPRESSED_ALIASES
            ):
                sandhi.append((folded, entity.concept_id))
        for alias in getattr(entity, "aliases_sa_phrases", ()) or ():
            parts = tuple(fold_alias(part) for part in str(alias).split())
            # Every part must fold to something, or the phrase has a hole in it and would
            # match a run it does not describe.
            if len(parts) < 2 or not all(parts):
                continue
            phrase.append((parts, entity.concept_id))
    return MentionIndex(
        token=token,
        sandhi=tuple(sorted(sandhi)),
        theonyms=frozenset(theonyms),
        phrase=tuple(sorted(phrase)),
    )'''

# --- 5. the pass itself -----------------------------------------------------
HITS_ANCHOR = '''def _sandhi_hits(mantra: MantraRecord, index: MentionIndex, already: set[str]) -> dict[str, _Hit]:'''

HITS_NEW = '''def _phrase_hits(mantra: MantraRecord, index: MentionIndex) -> dict[str, _Hit]:
    """Entities named by a run of consecutive whole tokens.

    Both ends of the run are token boundaries by construction -- the comparison is over the
    token SEQUENCE, never over the joined string -- so this cannot fire inside a longer
    word. That is the difference between this and :func:`_sandhi_hits`, and it is why this
    one is not restricted to the Sāmaveda.
    """
    tokens = mantra.surfaces.tokens
    found: dict[str, _Hit] = {}
    if not index.phrase or not tokens:
        return found
    for parts, entity_key in index.phrase:
        width = len(parts)
        for position in range(len(tokens) - width + 1):
            if tuple(tokens[position : position + width]) != parts:
                continue
            window = tokens[
                max(0, position - _CONTEXT_TOKENS) : position + width + _CONTEXT_TOKENS
            ]
            found.setdefault(entity_key, _Hit()).add(
                " ".join(parts), " ".join(window), "script_folded_phrase"
            )
    return found


def _sandhi_hits(mantra: MantraRecord, index: MentionIndex, already: set[str]) -> dict[str, _Hit]:'''

# --- 6. wire it into extract_mentions --------------------------------------
EXTRACT_ANCHOR = '''    path_counts: dict[str, int] = {_PATH_TOKEN: 0, _PATH_SANDHI: 0}'''
EXTRACT_NEW = '''    path_counts: dict[str, int] = {_PATH_TOKEN: 0, _PATH_SANDHI: 0, _PATH_PHRASE: 0}'''

LOOP_ANCHOR = '''        token_hits = _token_hits(mantra, index)
        sandhi_hits = (
            _sandhi_hits(mantra, index, set(token_hits))
            if mantra.veda in SANDHI_MATCH_VEDAS
            else {}
        )
        if not token_hits and not sandhi_hits:
            continue'''

LOOP_NEW = '''        token_hits = _token_hits(mantra, index)
        phrase_hits = _phrase_hits(mantra, index)
        sandhi_hits = (
            _sandhi_hits(mantra, index, set(token_hits) | set(phrase_hits))
            if mantra.veda in SANDHI_MATCH_VEDAS
            else {}
        )
        if not token_hits and not phrase_hits and not sandhi_hits:
            continue'''

BUILT_ANCHOR = '''        for entity_key, hit in sorted(sandhi_hits.items()):
            built.append(
                _build_row(mantra, entity_key, hit, _PATH_SANDHI, _SANDHI_SCORE, index, identity)
            )'''

BUILT_NEW = '''        for entity_key, hit in sorted(phrase_hits.items()):
            if entity_key in token_hits:
                # Reached by both paths. The phrase is the stronger claim, so it replaces
                # the token row rather than travelling beside it: two rows for one
                # (passage, entity) would double-count the mention.
                built = [row for row in built if row.entity_key != entity_key]
            built.append(
                _build_row(mantra, entity_key, hit, _PATH_PHRASE, _PHRASE_SCORE, index, identity)
            )
        for entity_key, hit in sorted(sandhi_hits.items()):
            built.append(
                _build_row(mantra, entity_key, hit, _PATH_SANDHI, _SANDHI_SCORE, index, identity)
            )'''


REPLACEMENTS = [
    (SCORE_ANCHOR, SCORE_NEW),
    (PATH_ANCHOR, PATH_NEW),
    (INDEX_ANCHOR, INDEX_NEW),
    (BUILD_ANCHOR, BUILD_NEW),
    (HITS_ANCHOR, HITS_NEW),
    (EXTRACT_ANCHOR, EXTRACT_NEW),
    (LOOP_ANCHOR, LOOP_NEW),
    (BUILT_ANCHOR, BUILT_NEW),
]


def main() -> None:
    raw = MODULE.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("mentions.py contains CRLF; this patcher assumes LF")
    text = raw.decode("utf-8")
    if "_PATH_PHRASE" in text:
        raise SystemExit("phrase pass already present")
    for old, new in REPLACEMENTS:
        if old not in text:
            raise SystemExit(f"anchor not found, refusing a partial patch:\n{old[:120]}")
        text = text.replace(old, new, 1)
    MODULE.write_bytes(text.encode("utf-8"))
    print(f"patched {len(REPLACEMENTS)} anchors in {MODULE.name}")


if __name__ == "__main__":
    main()
