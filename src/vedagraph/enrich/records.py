"""The on-disk shape of every enrichment artifact.

The enrichment stages and the Neo4j projection are deliberately decoupled: stages write
JSONL under ``data/enrichment/``, and the loader reads it back. That boundary is what
makes the layer reproducible without a database and reviewable in a diff, and it is why
the row shapes live here rather than inside whichever stage happens to emit them.

Every row carries its provenance envelope inline. A row that cannot explain itself is
rejected at write time, not at load time, so a bad row never reaches the graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vedagraph.enrich.provenance import Provenance, stable_id
from vedagraph.enrich.surfaces import MatchLevel


@dataclass(frozen=True)
class ParallelRow:
    """One cross-Veda textual relationship between two mantras."""

    predicate: str
    subject_key: str
    object_key: str
    subject_veda: str
    object_veda: str
    veda_pair: str
    match_level: str
    levels_reached: tuple[str, ...]
    similarity: float
    token_jaccard: float
    ngram_jaccard: float
    lcs_ratio: float
    edit_ratio: float
    provenance: Provenance

    def as_row(self) -> dict[str, Any]:
        return {
            "parallel_id": stable_id("parallel", self.predicate, self.subject_key, self.object_key),
            "predicate": self.predicate,
            "subject_key": self.subject_key,
            "object_key": self.object_key,
            "subject_veda": self.subject_veda,
            "object_veda": self.object_veda,
            "veda_pair": self.veda_pair,
            "match_level": self.match_level,
            "levels_reached": list(self.levels_reached),
            "similarity": round(self.similarity, 6),
            "token_jaccard": round(self.token_jaccard, 6),
            "ngram_jaccard": round(self.ngram_jaccard, 6),
            "lcs_ratio": round(self.lcs_ratio, 6),
            "edit_ratio": round(self.edit_ratio, 6),
            **self.provenance.as_dict(),
        }


@dataclass(frozen=True)
class FormulaRow:
    """One repeated Sanskrit phrase, promoted to a node."""

    formula_id: str
    normalized: str
    display_form: str
    word_count: int
    char_count: int
    #: Total occurrences, counting a formula twice when one mantra repeats it. Distinct
    #: from :attr:`mantra_count`, and the two differ on 60 of 4,825 nodes -- the Yajurveda
    #: repeats ``makhāya tvā makhasya tvā śīrṣṇe`` three times inside single mantras, so it
    #: reads 23 occurrences over 8 mantras. ``USES_FORMULA`` edges follow ``mantra_count``,
    #: because an edge is a fact about a passage, not about a repetition inside one.
    occurrence_count: int
    #: Distinct mantras containing the formula. This is the number that matches the edges.
    mantra_count: int
    vedas: tuple[str, ...]
    veda_counts: dict[str, int]
    cross_veda: bool
    source_forms: tuple[str, ...]
    derivation_method: str
    provenance: Provenance

    def as_row(self) -> dict[str, Any]:
        return {
            "formula_id": self.formula_id,
            "normalized": self.normalized,
            "display_form": self.display_form,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "occurrence_count": self.occurrence_count,
            "mantra_count": self.mantra_count,
            "vedas": list(self.vedas),
            "veda_counts": dict(sorted(self.veda_counts.items())),
            "cross_veda": self.cross_veda,
            "source_forms": list(self.source_forms),
            "derivation_method": self.derivation_method,
            **self.provenance.as_dict(),
        }


@dataclass(frozen=True)
class FormulaOccurrenceRow:
    """One passage's use of one formula."""

    formula_id: str
    passage_key: str
    veda: str
    source_form: str
    provenance: Provenance

    def as_row(self) -> dict[str, Any]:
        return {
            "formula_id": self.formula_id,
            "passage_key": self.passage_key,
            "veda": self.veda,
            "source_form": self.source_form,
            **self.provenance.as_dict(),
        }


@dataclass(frozen=True)
class ConceptRow:
    """One node of the concept layer."""

    concept_id: str
    preferred_label_sa: str
    preferred_label_en: str
    node_type: str
    aliases_sa: tuple[str, ...]
    aliases_en: tuple[str, ...]
    broader: tuple[str, ...]
    definition: str
    related_devatas: tuple[str, ...]
    #: Only ``CONDITION`` entities carry this; empty string everywhere else. Required and
    #: validated for conditions in :func:`vedagraph.enrich.concepts.load_concepts`, because
    #: a condition with no kind is what made "which diseases?" answer with demons.
    condition_kind: str = ""
    #: Forms this concept owns that may not assert it on their own. Kept on the row rather
    #: than dropped at load, because the owner's decision is that they stay usable for
    #: search, candidate generation, audit and manual review -- only their authority to
    #: create an edge is withdrawn. They are deliberately NOT in ``aliases_sa`` /
    #: ``aliases_en``, which is what the mention matcher reads.
    non_triggering_aliases_sa: tuple[str, ...] = ()
    non_triggering_aliases_en: tuple[str, ...] = ()
    #: Multi-word Sanskrit aliases, matched as a run of consecutive whole tokens by the
    #: mention layer's phrase pass. Held apart from ``aliases_sa`` because that table is
    #: keyed by one folded token: a string with a space in it can never equal a key there,
    #: so a multi-word alias placed in it matches nothing forever and reports nothing about
    #: having done so. Registered for the two soma pressings whose phrase the corpus writes
    #: and whose one-word form it does not.
    aliases_sa_phrases: tuple[str, ...] = ()

    def as_row(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "preferred_label_sa": self.preferred_label_sa,
            "preferred_label_en": self.preferred_label_en,
            "node_type": self.node_type,
            "aliases_sa": list(self.aliases_sa),
            "aliases_en": list(self.aliases_en),
            "broader": list(self.broader),
            "definition": self.definition,
            "related_devatas": list(self.related_devatas),
            "condition_kind": self.condition_kind,
            "aliases_sa_phrases": list(self.aliases_sa_phrases),
            "non_triggering_aliases_sa": list(self.non_triggering_aliases_sa),
            "non_triggering_aliases_en": list(self.non_triggering_aliases_en),
        }


@dataclass(frozen=True)
class ConceptAssertionRow:
    """One passage-to-concept claim, with the span that supports it."""

    passage_key: str
    veda: str
    concept_id: str
    confidence: float
    provenance: Provenance

    def as_row(self) -> dict[str, Any]:
        return {
            "assertion_id": stable_id(
                "concept-assertion", self.passage_key, self.concept_id, self.provenance.method
            ),
            "passage_key": self.passage_key,
            "veda": self.veda,
            "concept_id": self.concept_id,
            "confidence": round(self.confidence, 6),
            **self.provenance.as_dict(),
        }


@dataclass(frozen=True)
class SemanticCandidateRow:
    """One model-proposed semantic relation. Candidate by construction."""

    passage_key: str
    veda: str
    predicate: str
    object_kind: str
    object_key: str
    object_label: str
    confidence: float
    provenance: Provenance

    def as_row(self) -> dict[str, Any]:
        return {
            "candidate_id": stable_id(
                "semantic", self.passage_key, self.predicate, self.object_key
            ),
            "passage_key": self.passage_key,
            "veda": self.veda,
            "predicate": self.predicate,
            "object_kind": self.object_kind,
            "object_key": self.object_key,
            "object_label": self.object_label,
            "confidence": round(self.confidence, 6),
            **self.provenance.as_dict(),
        }


def veda_pair(veda_a: str, veda_b: str) -> str:
    """A stable, order-independent label for a Veda pair.

    Sorted rather than given in argument order, so ``RV<->SV`` and ``SV<->RV`` aggregate
    into one cell of the relationship matrix instead of two.
    """
    first, second = sorted((veda_a, veda_b))
    return f"{first}-{second}"


def level_name(level: MatchLevel) -> str:
    return str(level)
