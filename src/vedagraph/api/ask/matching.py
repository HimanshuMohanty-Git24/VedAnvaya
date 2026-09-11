"""Name matching for entity resolution: diacritic folding and word-boundary containment.

Two failures made this its own module rather than a clause inside the resolver query, and
both were found by running the demo questions against the live graph.

**Folding.** The registry stores Sanskrit labels in IAST with diacritics: the concept of
cosmic order is ``ṛta``, its Sanskrit label is ``ṛta``, and its eight aliases are all
accented. A researcher types ``rta``. Without folding, ``VG:CONCEPT:RTA-ORDER`` -- the node
the question is about -- is unreachable by the spelling a keyboard produces, and the
response is a truthful-looking "no evidence" built from a matching artefact.

**Word boundaries.** The obvious repair is substring containment, and it is worse than the
disease. ``rta`` is a substring of *mortar*, so ``CONTAINS`` resolves "what connects Varuna
with rta" to ``VG:DEVATA:ULUKHALAM`` -- *the mortar* -- and the evidence packet then carries
a kitchen implement as the subject of a question about cosmic order. It is the same shape of
defect as matching the deity *Ap* inside "appear": plausible, silent, and wrong.

So containment here is over *tokens*, never characters. :data:`_TOKENISE_EXPR` splits a
folded label on its punctuation and the name must equal one of the resulting words. *Soma*
still reaches ``Soma-Pusan`` and *takman* still reaches ``fever (takman)``, because in both
the name is a whole token; *rta* no longer reaches *mortar*, because there it is not.
"""

from __future__ import annotations

import unicodedata
from typing import Final

#: IAST and ISO 15919 diacritics mapped to their ASCII base. Applied to both sides of every
#: comparison, so a folded query meets a folded label and neither spelling is privileged.
#: Not derived from ``unicodedata.decomposition`` because several of these do not decompose:
#: ``ṃ`` and ``ḥ`` are single code points with no canonical base, and they are exactly the
#: characters a transliterated Sanskrit noun ends in.
DIACRITIC_FOLD: Final[tuple[tuple[str, str], ...]] = (
    ("ā", "a"),
    ("ī", "i"),
    ("ū", "u"),
    ("ṛ", "r"),
    ("ṝ", "r"),
    ("ḷ", "l"),
    ("ḹ", "l"),
    ("ṅ", "n"),
    ("ñ", "n"),
    ("ṇ", "n"),
    ("ṃ", "m"),
    ("ṁ", "m"),
    ("ṭ", "t"),
    ("ḍ", "d"),
    ("ḥ", "h"),
    ("ś", "s"),
    ("ṣ", "s"),
    ("ē", "e"),
    ("ō", "o"),
)

#: Characters that separate words in a label. ``(`` and ``)`` are here because the product
#: label form is "gloss (sanskrit)" -- *fever (takman)*, *cosmic order (ṛta)* -- and the
#: Sanskrit term inside the parentheses is the token a researcher types.
LABEL_SEPARATORS: Final[tuple[str, ...]] = (
    "(",
    ")",
    "-",
    ",",
    ".",
    "/",
    ":",
    ";",
    "'",
    "’",  # noqa: RUF001 -- curly apostrophe is a real separator in source labels
    "[",
    "]",
)


#: ASCII digraphs an English-keyboard speller uses for sounds IAST writes with a
#: diacritic, mapped onto what :data:`DIACRITIC_FOLD` leaves those diacritics as.
#:
#: Applied to the *question* only, never to a stored label. The registry spells these with
#: diacritics -- ``viśvāmitra``, ``rakṣas`` -- which already fold to ``s``, so folding a
#: label's "sh" would only corrupt a label that legitimately contains the sequence. A
#: researcher typing ``Vishvamitra`` or ``rakshas``, though, produces a string that meets
#: nothing in the graph until the digraph is folded too.
#:
#: Ordered longest-first: ``ksh`` must be consumed before ``sh`` can split it.
QUERY_DIGRAPH_FOLD: Final[tuple[tuple[str, str], ...]] = (
    ("ksh", "ks"),
    ("chh", "ch"),
    ("sh", "s"),
    ("ee", "i"),
    ("oo", "u"),
    ("aa", "a"),
    ("ii", "i"),
    ("uu", "u"),
)


def fold_name(text: str) -> str:
    """Lower-case, NFC-normalise and strip IAST diacritics for comparison.

    Not for display, ever. ``fold_name("Ṛta") == "rta"`` and rendering that back to a
    reader would silently de-accent the corpus.
    """
    folded = unicodedata.normalize("NFC", text).strip().lower()
    for accented, base in DIACRITIC_FOLD:
        folded = folded.replace(accented, base)
    return folded


def fold_query_name(text: str) -> str:
    """Fold a name *as typed in a question*: diacritics, then ASCII digraphs.

    Strictly more aggressive than :func:`fold_name`, and asymmetric on purpose -- see
    :data:`QUERY_DIGRAPH_FOLD`. Use this on question input and :func:`fold_name` on
    anything read out of the graph.
    """
    folded = fold_name(text)
    for digraph, base in QUERY_DIGRAPH_FOLD:
        folded = folded.replace(digraph, base)
    return folded


#: Popular transliteration spells the vocalic ``ṛ`` with an inserted vowel: *Ṛgveda* is
#: typed *Rigveda*, *Pṛthvī* as *Prithvi*, *Bṛhaspati* as *Brihaspati*. Undoing that is
#: lossy in a way the folds above are not -- it also rewrites the ordinary syllable *ri*,
#: so ``sarira`` would fold to ``sarr`` -- which is why it is a separate, later rung
#: rather than part of :func:`fold_query_name`.
VOCALIC_R_FOLD: Final[tuple[tuple[str, str], ...]] = (
    ("ri", "r"),
    ("ru", "r"),
    ("li", "l"),
)


def fold_query_name_vocalic(text: str) -> str:
    """The most permissive fold: :func:`fold_query_name` plus vocalic-``ṛ`` spellings.

    Only sound as a *fallback*. Tried first it would let a loose rewrite outrank an exact
    hit, so the resolver attempts it only where the stricter fold matched nothing.
    """
    folded = fold_query_name(text)
    for spelling, base in VOCALIC_R_FOLD:
        folded = folded.replace(spelling, base)
    return folded


#: The fold ladder, strictest first. A resolver walks it and stops at the first rung that
#: matches, so a permissive rewrite can never outrank an exact one.
FOLD_LADDER: Final = (fold_query_name, fold_query_name_vocalic)


def _cypher_fold(expression: str) -> str:
    """Wrap a Cypher string expression in the same fold :func:`fold_name` applies.

    Built as nested ``replace()`` calls rather than a database function because this graph
    is frozen and read-only to this API: installing an APOC-style normaliser to answer a
    GET would make a read endpoint a schema change. The chain is 19 replacements over a
    registry of roughly 2,900 label-bearing nodes, which measures in single-digit
    milliseconds.

    ``expression`` is always a literal written in this module or the resolver, never client
    input, so there is nothing here a question could interpolate.
    """
    folded = f"toLower(toString({expression}))"
    for accented, base in DIACRITIC_FOLD:
        folded = f"replace({folded}, '{accented}', '{base}')"
    return folded


def cypher_folded(expression: str) -> str:
    """The folded comparison form of a Cypher expression."""
    return _cypher_fold(expression)


def cypher_tokens(expression: str) -> str:
    """A Cypher list of the folded word tokens of a label expression.

    Every separator becomes a space, then the string is split on space. ``fever (takman)``
    yields ``['fever', '', 'takman', '']``; the empties are harmless because a name of
    fewer than two characters never reaches a comparison.
    """
    normalised = _cypher_fold(expression)
    for separator in LABEL_SEPARATORS:
        escaped = separator.replace("\\", "\\\\").replace("'", "\\'")
        normalised = f"replace({normalised}, '{escaped}', ' ')"
    return f"split({normalised}, ' ')"


def token_match(name: str, label: str) -> bool:
    """Whether ``name`` is a whole folded token of ``label``. The Python mirror of the
    Cypher above, used by tests to assert the two agree.
    """
    folded_label = fold_name(label)
    for separator in LABEL_SEPARATORS:
        folded_label = folded_label.replace(separator, " ")
    return fold_name(name) in folded_label.split()
