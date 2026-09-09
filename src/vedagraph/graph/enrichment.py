"""Enrichment-artifact projection: read ``data/enrichment/`` JSONL into graph rows.

The enrichment stages write JSONL and this module reads it back. That boundary is
deliberate -- see :mod:`vedagraph.enrich.records` -- and it means the projection's job is
narrow and worth stating exactly: turn one on-disk row into one flat dict of
Neo4j-storable scalars, and lose nothing on the way.

**Nothing here talks to a database and nothing here validates a claim.** The stages
already rejected rows that could not explain themselves. A reader that re-litigated that
would be a second, drifting copy of the rules. What a reader does do is fail loudly on a
row whose *shape* is wrong, because a missing ``concept_id`` is a bug in the writer, not
a weak claim.

**A missing artifact yields nothing.** The six files are produced by six independent
stages and a partial run is a normal state during development. ``_iter_jsonl`` returning
empty for a missing path is the same contract the corpus projection uses, and it is why
``load_enrichment`` against a half-built directory loads the half that exists instead of
crashing.

Two shape decisions the rest of the layer depends on:

**Evidence stays a JSON string.** Neo4j has no nested-map property. ``Provenance`` already
has a flattening rule in :meth:`~vedagraph.enrich.provenance.Provenance.as_edge_properties`
and this module reproduces it exactly, including ``evidence_count``, so that "why are
these connected?" is answerable from the edge without parsing anything first.

**Aliases are properties, not nodes.** An alias is a surface form of a concept, not an
entity that can be the subject of a claim; giving it a node invites edges to be attached
to it, and the first such edge is a bug that no schema will catch. The frozen ontology
agrees by accident: ``HAS_ALIAS`` is signed ``Concept -> Concept``, which no alias string
can satisfy, so materialising alias nodes would mean inventing a node kind outside
:class:`~vedagraph.enrich.predicates.NodeKind`. Stored as string arrays on the Concept
node they remain fully queryable -- ``WHERE $q IN c.aliases_sa`` -- and the full-text
index in :mod:`vedagraph.graph.enrichment_schema` indexes every element of the array,
which is the lookup an alias exists to serve. :func:`iter_concept_alias_rows` materialises
the flat alias-to-concept table anyway, for callers that want the lookup in Python rather
than in Cypher; the loader does not consume it.
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Final

import orjson

from vedagraph.enrich.predicates import StructuralPredicate
from vedagraph.enrich.provenance import PIPELINE_VERSION, AssertionState, TrustClass

#: Where the enrichment stages write. One directory per pipeline version, so a version
#: bump produces a second artifact set beside the first rather than overwriting the run
#: the graph was last built from.
ENRICHMENT_DIR: Final = pathlib.Path("data") / "enrichment" / "vedagraph_enrichment_v1"

PARALLELS_FILE: Final = "cross_veda_parallels.jsonl"
FORMULAS_FILE: Final = "formulas.jsonl"
FORMULA_OCCURRENCES_FILE: Final = "formula_occurrences.jsonl"
CONCEPTS_FILE: Final = "concepts.jsonl"
CONCEPT_ASSERTIONS_FILE: Final = "concept_assertions.jsonl"
SEMANTIC_CANDIDATES_FILE: Final = "semantic_candidates.jsonl"
MANIFEST_FILE: Final = "manifest.json"

#: The method recorded on edges the concept lexicon states directly rather than derives.
#: ``concepts.jsonl`` rows carry no provenance envelope of their own -- a curated lexicon
#: entry is not a finding -- but the edges built from them still have to answer "why?",
#: so the lexicon itself is named as the evidence. See :func:`_lexicon_provenance`.
LEXICON_HIERARCHY_METHOD: Final = "concept-lexicon-broader"
LEXICON_DEVATA_METHOD: Final = "concept-lexicon-related-devata"
LEXICON_SURFACE: Final = "concept-lexicon"


def enrichment_dir(project_root: pathlib.Path) -> pathlib.Path:
    """Absolute path to the enrichment artifact directory for ``project_root``."""
    return project_root / ENRICHMENT_DIR


def _iter_jsonl(path: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield parsed records from a JSONL file, skipping blank lines.

    A missing file yields nothing rather than raising: the six artifacts come from six
    independent stages and loading whichever ones exist is the intended behaviour.
    """
    if not path.exists():
        return
    for raw in path.read_bytes().split(b"\n"):
        stripped = raw.strip()
        if stripped:
            record: dict[str, Any] = orjson.loads(stripped)
            yield record


def read_manifest(project_root: pathlib.Path) -> dict[str, Any]:
    """The enrichment run manifest, or an empty dict when the run has not been written."""
    path = enrichment_dir(project_root) / MANIFEST_FILE
    if not path.exists():
        return {}
    manifest: dict[str, Any] = orjson.loads(path.read_bytes())
    return manifest


# ---------------------------------------------------------------------------
# Provenance flattening
# ---------------------------------------------------------------------------


def _str_list(value: Any) -> list[str]:
    """Coerce a JSON array to a list of strings, dropping nothing silently but nulls."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value if item is not None]
    return []


def _evidence(raw: Any) -> tuple[str, int]:
    """Return ``(json_string, span_count)`` for a row's evidence, whatever shape it has.

    ``Provenance.as_dict`` -- which is what gets splatted into every row and serialized --
    leaves evidence as a JSON *array* of span objects, while
    ``Provenance.as_edge_properties`` encodes the same thing as a *string* because Neo4j
    cannot store a list of maps. Both shapes therefore legitimately appear depending on
    which side wrote the file, and guessing wrong turns the evidence into either a
    double-encoded string or an unstorable list. Accepting both is not defensive
    programming; it is the actual contract of the two writers.
    """
    if isinstance(raw, str):
        if not raw:
            return "[]", 0
        decoded = orjson.loads(raw)
        return raw, len(decoded) if isinstance(decoded, list) else 0
    if isinstance(raw, list):
        return orjson.dumps(raw).decode(), len(raw)
    return "[]", 0


def _provenance_properties(rec: Mapping[str, Any]) -> dict[str, Any]:
    """The ten-key provenance envelope, flattened for Neo4j.

    Reproduces ``Provenance.as_edge_properties`` field for field. It is reproduced rather
    than called because the reader has a dict from disk, not a ``Provenance`` instance,
    and rebuilding the dataclass would re-run ``__post_init__`` validation that the
    writing stage already ran -- turning a read of an archived artifact into a re-judging
    of a decision made under a different pipeline version.
    """
    evidence, evidence_count = _evidence(rec.get("evidence", []))
    return {
        "trust": str(rec.get("trust", "")),
        "method": str(rec.get("method", "")),
        "score": float(rec.get("score", 0.0)),
        "evidence": evidence,
        "evidence_count": evidence_count,
        "state": str(rec.get("state", "")),
        # Defaulted rather than left empty: pipeline_version is part of the loader's MERGE
        # key, and an empty one would make the edge invisible to every layer-scoped query.
        "pipeline_version": str(rec.get("pipeline_version") or PIPELINE_VERSION),
        "run_id": str(rec.get("run_id", "")),
        "model": str(rec.get("model", "")),
        "prompt_policy": str(rec.get("prompt_policy", "")),
    }


def _lexicon_provenance(rec: Mapping[str, Any], method: str) -> dict[str, Any]:
    """Provenance for an edge asserted by the concept lexicon itself.

    ``ConceptRow`` has no ``Provenance`` field, because a curated lexicon entry is a
    statement rather than a finding. The edges built from ``broader`` and
    ``related_devatas`` still need the envelope -- the evidence-first contract has no
    exemption for edges we happen to trust -- so the lexicon entry is named as its own
    evidence: locator is the concept id, surface is ``concept-lexicon``, quote is the
    concept's preferred label. That is honest about where the claim comes from, which an
    empty evidence list would not be.

    If a future lexicon build does carry an envelope, it wins: the row's own provenance is
    always more specific than one synthesised here.
    """
    if rec.get("method"):
        return _provenance_properties(rec)
    concept_id = str(rec.get("concept_id", ""))
    label = str(rec.get("preferred_label_sa") or rec.get("preferred_label_en") or concept_id)
    span = {"locator": concept_id, "surface": LEXICON_SURFACE, "quote": label}
    return {
        "trust": str(TrustClass.SOURCE_EXPLICIT),
        "method": method,
        "score": 1.0,
        "evidence": orjson.dumps([span]).decode(),
        "evidence_count": 1,
        "state": str(AssertionState.ACCEPTED),
        "pipeline_version": str(rec.get("pipeline_version") or PIPELINE_VERSION),
        "run_id": str(rec.get("run_id", "")),
        "model": "",
        "prompt_policy": "",
    }


# ---------------------------------------------------------------------------
# Concept nodes and the edges the lexicon states directly
# ---------------------------------------------------------------------------


def iter_concept_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield Concept node dicts from ``concepts.jsonl``.

    ``broader`` and ``related_devatas`` are deliberately absent from the node: they are
    edges (:func:`iter_concept_hierarchy_rels`, :func:`iter_devata_concept_rels`) and
    storing them on the node as well would give the graph two answers to the same
    question that drift the first time one is rebuilt without the other.
    """
    for rec in _iter_jsonl(enrichment_dir(project_root) / CONCEPTS_FILE):
        yield {
            "concept_id": rec["concept_id"],
            "preferred_label_sa": str(rec.get("preferred_label_sa", "")),
            "preferred_label_en": str(rec.get("preferred_label_en", "")),
            "node_type": str(rec.get("node_type", "")),
            "aliases_sa": _str_list(rec.get("aliases_sa", [])),
            "aliases_en": _str_list(rec.get("aliases_en", [])),
            "definition": str(rec.get("definition", "")),
        }


def iter_concept_alias_rows(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield one flat row per (concept, alias) pair.

    Not loaded into the graph. Aliases live as string arrays on the Concept node -- see
    the module docstring for why an alias is not an entity -- and this generator exists
    for callers that want the alias-to-concept lookup table in Python: a search box, an
    ambiguity report, or a check that no two concepts claim the same surface form. It
    reads the same artifact the nodes are built from, so it cannot disagree with them.

    ``is_preferred`` marks the alias that is also the concept's preferred label in that
    language, which is the row a disambiguation UI should rank first.
    """
    for rec in _iter_jsonl(enrichment_dir(project_root) / CONCEPTS_FILE):
        concept_id = rec["concept_id"]
        for language, field, preferred in (
            ("sa", "aliases_sa", str(rec.get("preferred_label_sa", ""))),
            ("en", "aliases_en", str(rec.get("preferred_label_en", ""))),
        ):
            for alias in _str_list(rec.get(field, [])):
                yield {
                    "concept_id": concept_id,
                    "alias": alias,
                    "language": language,
                    "is_preferred": alias == preferred,
                }


def iter_concept_hierarchy_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield BROADER_THAN relationship dicts between Concepts.

    Direction follows the frozen signature: the *subject* is the superordinate, so a row
    listing ``FIRE`` in the ``broader`` field of ``RITUAL_FIRE`` becomes
    ``(FIRE)-[:BROADER_THAN]->(RITUAL_FIRE)``. Getting this backwards is the classic
    SKOS mistake and it is silent -- the graph still looks like a tree, upside down.
    """
    predicate = str(StructuralPredicate.BROADER_THAN)
    for rec in _iter_jsonl(enrichment_dir(project_root) / CONCEPTS_FILE):
        concept_id = rec["concept_id"]
        provenance = _lexicon_provenance(rec, LEXICON_HIERARCHY_METHOD)
        for broader_id in _str_list(rec.get("broader", [])):
            if broader_id == concept_id:
                continue
            yield {
                "predicate": predicate,
                "subject_key": broader_id,
                "object_key": concept_id,
                **provenance,
            }


def iter_devata_concept_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield DEVATA_ASSOCIATED_WITH relationship dicts from Devata to Concept.

    The one edge that joins the deity registry to the concept layer, and the reason the
    two can stay separate: Agni-the-deity is *associated with* fire-the-concept and is not
    the same node as it. ``subject_key`` is a registry ``entity_key`` (``VG:DEVATA:...``),
    not a concept id, which is why the loader matches it against a different label.
    """
    predicate = str(StructuralPredicate.DEVATA_ASSOCIATED_WITH)
    for rec in _iter_jsonl(enrichment_dir(project_root) / CONCEPTS_FILE):
        concept_id = rec["concept_id"]
        provenance = _lexicon_provenance(rec, LEXICON_DEVATA_METHOD)
        for devata_key in _str_list(rec.get("related_devatas", [])):
            yield {
                "predicate": predicate,
                "subject_key": devata_key,
                "object_key": concept_id,
                **provenance,
            }


# ---------------------------------------------------------------------------
# Formulas
# ---------------------------------------------------------------------------


def iter_formula_nodes(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield Formula node dicts from ``formulas.jsonl``.

    ``veda_counts`` is a map and Neo4j has no map property, so it is stored as a JSON
    string -- the same treatment ``iter_passage_nodes`` gives ``hierarchy``. ``vedas`` is
    a list of strings and stays a native list, because ``'SV' IN f.vedas`` is a query
    somebody will actually write and ``f.veda_counts CONTAINS '"SV"'`` is not.
    """
    for rec in _iter_jsonl(enrichment_dir(project_root) / FORMULAS_FILE):
        yield {
            "formula_id": rec["formula_id"],
            "normalized": str(rec.get("normalized", "")),
            "display_form": str(rec.get("display_form", "")),
            "word_count": int(rec.get("word_count", 0)),
            "char_count": int(rec.get("char_count", 0)),
            "occurrence_count": int(rec.get("occurrence_count", 0)),
            "mantra_count": int(rec.get("mantra_count", 0)),
            "vedas": _str_list(rec.get("vedas", [])),
            "veda_counts": orjson.dumps(rec.get("veda_counts", {})).decode(),
            "cross_veda": bool(rec.get("cross_veda", False)),
            "source_forms": _str_list(rec.get("source_forms", [])),
            "derivation_method": str(rec.get("derivation_method", "")),
            **_provenance_properties(rec),
        }


def iter_formula_occurrence_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield USES_FORMULA relationship dicts from Passage to Formula.

    This is the hub that replaces combinatorial passage-to-passage edges: a formula in
    400 mantras is 400 edges here and 79,800 if the passages were joined directly.
    ``source_form`` is kept on the edge rather than only on the node because it is the
    per-occurrence fact -- how *this* passage spells the formula -- and it is what an
    evidence display quotes.
    """
    predicate = str(StructuralPredicate.USES_FORMULA)
    for rec in _iter_jsonl(enrichment_dir(project_root) / FORMULA_OCCURRENCES_FILE):
        yield {
            "predicate": predicate,
            "subject_key": rec["passage_key"],
            "object_key": rec["formula_id"],
            "veda": str(rec.get("veda", "")),
            "source_form": str(rec.get("source_form", "")),
            **_provenance_properties(rec),
        }


# ---------------------------------------------------------------------------
# Cross-Veda parallels
# ---------------------------------------------------------------------------


def iter_cross_veda_parallel_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield cross-Veda parallel relationship dicts between Passages.

    The ``predicate`` on each row selects the relationship type, and it is carried through
    as data rather than resolved here: the reader's job is to report what the artifact
    says, and the loader's job is to refuse anything outside the controlled vocabulary.
    Filtering here as well would mean a rejected predicate vanishes from the run instead of
    stopping it.

    ``match_level`` and ``levels_reached`` are both kept. The first is the strongest
    surface the pair matched on; the second is every surface it reached. Collapsing them
    would lose the difference between "identical text" and "identical only after accents,
    script and word division were all set aside", which is the single most misleading
    thing this layer could do.
    """
    for rec in _iter_jsonl(enrichment_dir(project_root) / PARALLELS_FILE):
        yield {
            "predicate": str(rec["predicate"]),
            "parallel_id": str(rec.get("parallel_id", "")),
            "subject_key": rec["subject_key"],
            "object_key": rec["object_key"],
            "subject_veda": str(rec.get("subject_veda", "")),
            "object_veda": str(rec.get("object_veda", "")),
            "veda_pair": str(rec.get("veda_pair", "")),
            "match_level": str(rec.get("match_level", "")),
            "levels_reached": _str_list(rec.get("levels_reached", [])),
            "similarity": float(rec.get("similarity", 0.0)),
            "token_jaccard": float(rec.get("token_jaccard", 0.0)),
            "ngram_jaccard": float(rec.get("ngram_jaccard", 0.0)),
            "lcs_ratio": float(rec.get("lcs_ratio", 0.0)),
            "edit_ratio": float(rec.get("edit_ratio", 0.0)),
            **_provenance_properties(rec),
        }


# ---------------------------------------------------------------------------
# Concept assertions and semantic candidates
# ---------------------------------------------------------------------------


def iter_concept_assertion_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield ABOUT_CONCEPT relationship dicts from Passage to Concept."""
    predicate = str(StructuralPredicate.ABOUT_CONCEPT)
    for rec in _iter_jsonl(enrichment_dir(project_root) / CONCEPT_ASSERTIONS_FILE):
        yield {
            "predicate": predicate,
            "assertion_id": str(rec.get("assertion_id", "")),
            "subject_key": rec["passage_key"],
            "object_key": rec["concept_id"],
            "veda": str(rec.get("veda", "")),
            "confidence": float(rec.get("confidence", 0.0)),
            **_provenance_properties(rec),
        }


def iter_semantic_candidate_rels(project_root: pathlib.Path) -> Iterator[dict[str, Any]]:
    """Yield semantic relationship dicts from Passage to its proposed object.

    ``object_kind`` is carried through unresolved. It decides which label the loader
    matches the object against, and it is a
    :class:`~vedagraph.semantic.ontology.SemanticNodeType` in the normal case -- the frozen
    ontology has no deity type, filing gods under ``COSMIC_ENTITY``, so almost every
    semantic object is a Concept. ``DEVATA`` is accepted as well, for a proposal that names
    a registry deity directly, and the loader routes on that value through a lookup table
    rather than by interpolating it into Cypher.

    Every row here is a model proposal. ``state`` is ``CANDIDATE`` by construction and the
    loader never creates the object node: an object that does not exist is reported as
    unmatched, because creating a Concept because a model mentioned it is exactly the
    "LLM output becomes canonical source data" failure the trust classes exist to prevent.
    """
    for rec in _iter_jsonl(enrichment_dir(project_root) / SEMANTIC_CANDIDATES_FILE):
        yield {
            "predicate": str(rec["predicate"]),
            "candidate_id": str(rec.get("candidate_id", "")),
            "subject_key": rec["passage_key"],
            "object_key": rec["object_key"],
            "object_kind": str(rec.get("object_kind", "")),
            "object_label": str(rec.get("object_label", "")),
            "veda": str(rec.get("veda", "")),
            "confidence": float(rec.get("confidence", 0.0)),
            **_provenance_properties(rec),
        }
