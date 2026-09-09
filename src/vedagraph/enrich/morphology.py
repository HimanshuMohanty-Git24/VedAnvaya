"""One read of the Rigvedic morphosyntactic annotation, shared by every stage that needs it.

``data/knowledge/rigveda_lexical_v1/tokens.jsonl`` holds the University of Zurich
morphosyntactic annotation of Lubotsky's Rigveda text -- 164,758 tokens, each with a
lemma, a part of speech and its inflectional features, corrected against Grassmann and
published in the VedaWeb TEI. It is a *manual scholarly annotation*, not a parser output,
and the whole of this module exists because two layers of this graph were previously built
without it and were worse for it.

**What it makes possible.** A theonym mention in the Rigveda does not have to be guessed
from a string: the annotation states that this token's lemma is ``indra-``, and it marks
the case, so the vocative -- the one form that certainly addresses a god rather than naming
a thing -- is directly available. An agentive claim does not have to be extracted by a
model either: 32,029 of these tokens are finite or non-finite verb forms carrying root,
person, number, tense, mood and voice, so "who does what" is derivable by rule from the
inflection.

**What it does not make possible, and this bounds every layer built on it.** The
annotation is morphological, not syntactic. There is no dependency parse, no clause
boundary and no subject-verb link. What it gives is *co-location plus agreement*: this
metrical line contains a nominative singular deity and a third-person singular finite
verb. In a one-clause line that is the subject of that verb; in a two-clause line it may
not be. So every consumer here must state its locality and agreement conditions and
measure its own precision, and none of them may present a co-location as a parse.

Three encoding facts, each of which silently destroys a layer if missed:

* **Vocalic r is decomposed.** The annotation writes it as ``r`` plus COMBINING RING
  BELOW; the registries and corpus surfaces use the precomposed character. Matching
  without folding loses every entity whose name contains it -- brhaspati, prthivi, rbhu,
  nirrti, rta, amrta, mrtyu.
* **The accented lemma label carries sense distinctions the normalized lemma drops.**
  Neuter *brahman* (the formulation) and masculine *brahman* (the priest) share one
  normalized lemma and are two different entities; so do the two *yama*. Callers that
  care must key on :attr:`AnnotatedToken.lemma_label`.
* **``pada`` is the metrical line**, and it is the locality unit that matters. A whole
  mantra routinely contains several clauses; one pada usually contains one.
"""

from __future__ import annotations

import functools
import pathlib
import unicodedata
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Final

import orjson

from vedagraph.enrich.concepts import fold_alias

#: Where the annotation lives, relative to the project root.
ANNOTATION_PATH: Final = pathlib.Path("data") / "knowledge" / "rigveda_lexical_v1" / "tokens.jsonl"

#: The annotation's own identity, carried onto every claim derived from it. This is the
#: provenance that makes a Rigvedic mention a *source-stated* fact rather than a match.
ANNOTATION_SOURCE_ID: Final = "VEDAWEB.ZURICH"
ANNOTATION_METHOD: Final = "MANUAL_SCHOLARLY_ANNOTATION"

#: ``part_of_speech`` values the annotation uses. Verbs are tagged ``root``; there is no
#: separate "verb" value, which is why a naive filter on the word "verb" returns nothing.
POS_NOMINAL: Final = "nominal stem"
POS_ROOT: Final = "root"
POS_PRONOUN: Final = "pronoun"
POS_INVARIABLE: Final = "invariable"

#: Grammatical cases as the annotation spells them.
CASES: Final[tuple[str, ...]] = ("NOM", "ACC", "INS", "DAT", "ABL", "GEN", "LOC", "VOC")

#: Moods that make a second-person address a *request* rather than a description. An
#: imperative addressed to a vocative deity is not an interpretation of the verse; it is
#: what the verse grammatically is.
REQUEST_MOODS: Final[frozenset[str]] = frozenset({"IMP", "IMP-si", "OPT", "SBJV", "INJ", "PREC"})

_RING_BELOW_FOLDS: Final[tuple[tuple[str, str], ...]] = (("r̥", "ṛ"), ("l̥", "ḷ"))


@functools.lru_cache(maxsize=65536)
def fold_annotation(text: str) -> str:
    """Fold an annotation lemma or surface onto the corpus search surface.

    Composes the decomposed vocalic r and l first -- see the module docstring -- then
    hands the result to the same :func:`~vedagraph.enrich.concepts.fold_alias` the
    concept and mention layers use, so a form folded here and an alias folded there are
    the same string or the layers cannot be compared.
    """
    decomposed = unicodedata.normalize("NFD", text)
    for source, target in _RING_BELOW_FOLDS:
        decomposed = decomposed.replace(source, target)
    return fold_alias(unicodedata.normalize("NFC", decomposed))


@dataclass(frozen=True)
class AnnotatedToken:
    """One annotated Rigvedic token."""

    passage_key: str
    token_key: str
    sequence: int
    pada: str
    surface_form: str
    lemma_label: str
    normalized_lemma: str
    folded_lemma: str
    part_of_speech: str
    case: str | None
    number: str | None
    gender: str | None
    person: str | None
    tense: str | None
    mood: str | None
    voice: str | None
    non_finite: str | None
    secondary_conjugation: str | None
    #: The annotation's ``local particle`` feature. Set on the particle's own token for
    #: 10,266 invariables, and on the verb for the 2,177 roots that govern one. It is the
    #: only way to tell a preverb from a conjunction: adjacency alone puts ``ca`` "and"
    #: next to a verb as readily as ``ā`` "hither".
    local_particle: str | None = None

    @property
    def is_nominal(self) -> bool:
        return self.part_of_speech == POS_NOMINAL

    @property
    def is_finite_verb(self) -> bool:
        """A finite verb: tagged ``root``, inflected for person, and not a participle.

        ``non_finite`` is the discriminator, not the presence of a person feature: the
        annotation marks participles with both a person-less paradigm and a case, and a
        participle is not the clause's finite verb.
        """
        return (
            self.part_of_speech == POS_ROOT and self.person is not None and self.non_finite is None
        )

    @property
    def is_vocative(self) -> bool:
        return self.case == "VOC"

    def as_evidence_quote(self) -> str:
        """The token with the morphology that justifies using it, as one readable string."""
        features = [
            value
            for value in (
                self.case,
                self.number,
                self.gender,
                self.person,
                self.tense,
                self.mood,
                self.voice,
            )
            if value
        ]
        return f"{self.surface_form} ({self.lemma_label}; {'/'.join(features)})"


@dataclass(frozen=True)
class Annotation:
    """The whole Rigvedic annotation, indexed the ways its consumers need it."""

    tokens: tuple[AnnotatedToken, ...]
    #: passage key -> its tokens in sequence order.
    by_passage: dict[str, tuple[AnnotatedToken, ...]]
    #: (passage key, pada) -> its tokens in sequence order. The locality unit.
    by_pada: dict[tuple[str, str], tuple[AnnotatedToken, ...]]
    #: folded lemma -> the tokens carrying it.
    by_lemma: dict[str, tuple[AnnotatedToken, ...]]

    def passages(self) -> int:
        return len(self.by_passage)

    def lemma_passages(self, folded_lemma: str) -> frozenset[str]:
        """Passages containing a token of this lemma. The mention layer's core query."""
        return frozenset(token.passage_key for token in self.by_lemma.get(folded_lemma, ()))

    def finite_verbs(self) -> Iterator[AnnotatedToken]:
        return (token for token in self.tokens if token.is_finite_verb)


def _read(path: pathlib.Path) -> Iterator[dict[str, Any]]:
    with path.open("rb") as handle:
        for raw in handle:
            if raw.strip():
                yield orjson.loads(raw)


def load_annotation(project_root: pathlib.Path) -> Annotation:
    """Read the Rigvedic annotation once and index it.

    Raises if the file is missing or empty rather than returning an empty annotation:
    every failure seen while building on this layer showed up as one silently
    unannotated Veda, which reads as "the Rigveda has no verbs" rather than as an error.
    """
    path = project_root / ANNOTATION_PATH
    if not path.exists():
        raise FileNotFoundError(f"Rigvedic annotation not found: {path}")

    tokens: list[AnnotatedToken] = []
    for record in _read(path):
        features = record.get("morphological_features") or {}
        lemma = str(record.get("normalized_lemma") or "")
        tokens.append(
            AnnotatedToken(
                passage_key=str(record["passage_key"]),
                token_key=str(record.get("token_key") or ""),
                sequence=int(record.get("sequence") or 0),
                pada=str(record.get("pada") or ""),
                surface_form=str(record.get("surface_form") or ""),
                lemma_label=str(record.get("lemma") or ""),
                normalized_lemma=lemma,
                folded_lemma=fold_annotation(lemma),
                part_of_speech=str(record.get("part_of_speech") or ""),
                case=features.get("case"),
                number=features.get("number"),
                gender=features.get("gender"),
                person=features.get("person"),
                tense=features.get("tense"),
                mood=features.get("mood"),
                voice=features.get("voice"),
                non_finite=features.get("non-finite"),
                secondary_conjugation=features.get("secondary conjugation"),
                local_particle=features.get("local particle"),
            )
        )
    if not tokens:
        raise ValueError(f"Rigvedic annotation is empty: {path}")

    by_passage: dict[str, list[AnnotatedToken]] = defaultdict(list)
    by_pada: dict[tuple[str, str], list[AnnotatedToken]] = defaultdict(list)
    by_lemma: dict[str, list[AnnotatedToken]] = defaultdict(list)
    for token in tokens:
        by_passage[token.passage_key].append(token)
        by_pada[(token.passage_key, token.pada)].append(token)
        by_lemma[token.folded_lemma].append(token)

    def freeze(
        grouped: dict[Any, list[AnnotatedToken]],
    ) -> dict[Any, tuple[AnnotatedToken, ...]]:
        return {
            key: tuple(sorted(value, key=lambda token: token.sequence))
            for key, value in grouped.items()
        }

    return Annotation(
        tokens=tuple(tokens),
        by_passage=freeze(by_passage),
        by_pada=freeze(by_pada),
        by_lemma=freeze(by_lemma),
    )
