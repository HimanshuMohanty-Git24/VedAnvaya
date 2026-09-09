"""Neo4j schema for the graph enrichment layer: labels, constraints and indexes.

The enrichment layer adds two node labels -- ``Concept`` and ``Formula`` -- and writes
relationships whose types it shares with the corpus layer. Nothing here modifies
:mod:`vedagraph.graph.schema`; the two are applied side by side, and keeping them in
separate modules is what lets the enrichment layer be rebuilt without touching the
constraints that protect the canonical corpus.

Three decisions in this file are worth the reader's time.

**Relationship property indexes exist because the deliverable queries scan edges, not
nodes.** The cross-Veda relationship matrix asks "how many parallels of each kind connect
each pair of Vedas", which is an aggregation over every parallel edge in the graph keyed
by a property. Without an index on ``veda_pair`` that is a full relationship scan of the
enrichment layer on every call. Neo4j 5 supports range indexes on relationship properties
(``FOR ()-[r:TYPE]-() ON (r.prop)``), so the matrix reads an index instead.

**``pipeline_version`` is indexed on every parallel type because two layers share those
types.** The within-Rigveda lexical layer already wrote ``EXACT_PARALLEL_OF`` and
``PARALLEL_TO`` edges. The enrichment layer writes ``EXACT_PARALLEL_OF`` too, deliberately:
"these two verses are identical" is the same claim whichever stage found it. What must not
happen is a query that cannot tell them apart, so every enrichment edge carries
``pipeline_version``, the loader puts that property inside the MERGE pattern, and this
index makes ``WHERE r.pipeline_version = $version`` cheap enough to use as a habit.

**The 14 semantic predicates get no relationship indexes.** Semantic candidate edges are
reached by traversing from a Passage or a Concept, never by scanning a type globally, and
28 more index objects would be write cost paid for a query nobody runs. If a semantic
dashboard later aggregates by ``state`` across all predicates, that is the moment to add
them; the omission is recorded here so it reads as a decision rather than an oversight.
"""

from __future__ import annotations

from typing import Final

from vedagraph.enrich.predicates import StructuralPredicate, TextualPredicate

# ---------------------------------------------------------------------------
# Node labels
# ---------------------------------------------------------------------------

LABEL_CONCEPT: Final = "Concept"
LABEL_FORMULA: Final = "Formula"

# ---------------------------------------------------------------------------
# Relationship types
#
# Mirrors of the frozen vocabulary in vedagraph.enrich.predicates, restated as module
# constants so graph code reads like vedagraph.graph.schema. They are derived from the
# enum members rather than typed out, so the two can never disagree.
# ---------------------------------------------------------------------------

REL_EXACT_PARALLEL_OF: Final = str(TextualPredicate.EXACT_PARALLEL_OF)
REL_NEAR_PARALLEL_OF: Final = str(TextualPredicate.NEAR_PARALLEL_OF)
REL_VARIANT_OF: Final = str(TextualPredicate.VARIANT_OF)
REL_REUSES_TEXT_FROM: Final = str(TextualPredicate.REUSES_TEXT_FROM)
REL_SHARES_FORMULA_WITH: Final = str(TextualPredicate.SHARES_FORMULA_WITH)

REL_USES_FORMULA: Final = str(StructuralPredicate.USES_FORMULA)
REL_ABOUT_CONCEPT: Final = str(StructuralPredicate.ABOUT_CONCEPT)
REL_BROADER_THAN: Final = str(StructuralPredicate.BROADER_THAN)
REL_DEVATA_ASSOCIATED_WITH: Final = str(StructuralPredicate.DEVATA_ASSOCIATED_WITH)

#: Relationship types that connect two Passages across Vedas. Every one of them carries
#: the same property set, so they index identically.
PARALLEL_REL_TYPES: Final[tuple[str, ...]] = tuple(str(p) for p in TextualPredicate)


# ---------------------------------------------------------------------------
# Uniqueness constraints
# ---------------------------------------------------------------------------

ENRICHMENT_CONSTRAINTS: Final[list[str]] = [
    # Concept - concept_id is assigned by the concept lexicon, not derived from a label,
    # because two concepts can share an English gloss ("fire" as element and as ritual
    # fire) and constraining on the label would silently merge them.
    "CREATE CONSTRAINT enrichment_concept_id_unique IF NOT EXISTS FOR (n:Concept) REQUIRE n.concept_id IS UNIQUE",  # noqa: E501
    # Formula - formula_id is derived from the normalized phrase, so the constraint is
    # also what makes a re-run MERGE onto the same node instead of duplicating the layer.
    "CREATE CONSTRAINT enrichment_formula_id_unique IF NOT EXISTS FOR (n:Formula) REQUIRE n.formula_id IS UNIQUE",  # noqa: E501
]


# ---------------------------------------------------------------------------
# Node indexes
# ---------------------------------------------------------------------------

_NODE_INDEXES: Final[list[str]] = [
    # "Which formulas cross Veda boundaries?" is the headline formula query and it is a
    # filter over the whole label. Low cardinality, but the selective side is
    # cross_veda = true, which is the side that gets asked for.
    "CREATE INDEX enrichment_formula_cross_veda IF NOT EXISTS FOR (n:Formula) ON (n.cross_veda)",
    # Ranking formulas by reach. mantra_count rather than occurrence_count is the ranking
    # the deliverable uses: a phrase repeated twice inside one verse is not as widespread
    # as one appearing in two verses, and occurrence_count cannot tell them apart.
    "CREATE INDEX enrichment_formula_mantra_count IF NOT EXISTS FOR (n:Formula) ON (n.mantra_count)",  # noqa: E501
    "CREATE INDEX enrichment_formula_occurrence_count IF NOT EXISTS FOR (n:Formula) ON (n.occurrence_count)",  # noqa: E501
    "CREATE INDEX enrichment_formula_word_count IF NOT EXISTS FOR (n:Formula) ON (n.word_count)",
    # Exact-phrase lookup: "is this string already a known formula?"
    "CREATE INDEX enrichment_formula_normalized IF NOT EXISTS FOR (n:Formula) ON (n.normalized)",
    # Concept browsing is almost always scoped by type first (rituals, substances,
    # places), then by label.
    "CREATE INDEX enrichment_concept_node_type IF NOT EXISTS FOR (n:Concept) ON (n.node_type)",
    "CREATE INDEX enrichment_concept_label_en IF NOT EXISTS FOR (n:Concept) ON (n.preferred_label_en)",  # noqa: E501
    "CREATE INDEX enrichment_concept_label_sa IF NOT EXISTS FOR (n:Concept) ON (n.preferred_label_sa)",  # noqa: E501
]

#: Full-text indexes. The range indexes above answer exact lookups; these answer the
#: search box. Aliases are included, and that is the concrete payoff of storing them as
#: string-array properties rather than as JSON blobs or as separate nodes: Neo4j indexes
#: every element of a string array, so a search for an alias finds the concept through
#: its alias list without a second query and without an Alias node to join through.
_FULLTEXT_INDEXES: Final[list[str]] = [
    "CREATE FULLTEXT INDEX enrichment_concept_text IF NOT EXISTS FOR (n:Concept) ON EACH [n.preferred_label_sa, n.preferred_label_en, n.aliases_sa, n.aliases_en, n.definition]",  # noqa: E501
    "CREATE FULLTEXT INDEX enrichment_formula_text IF NOT EXISTS FOR (n:Formula) ON EACH [n.normalized, n.display_form]",  # noqa: E501
]


# ---------------------------------------------------------------------------
# Relationship property indexes
# ---------------------------------------------------------------------------

#: Properties indexed on every cross-Veda parallel type. ``veda_pair`` drives the
#: relationship matrix, ``trust`` separates a string comparison from a model's reading,
#: ``score`` drives "strongest parallels first", and ``pipeline_version`` separates this
#: layer from the within-Rigveda lexical one that shares two of these type names.
_PARALLEL_REL_INDEXED_PROPERTIES: Final[tuple[str, ...]] = (
    "veda_pair",
    "trust",
    "score",
    "pipeline_version",
)


def _rel_index(rel_type: str, prop: str) -> str:
    """One relationship range index, named so its type and property are readable.

    Written with an undirected pattern ``()-[r:TYPE]-()`` because a relationship property
    index covers the type regardless of direction; spelling a direction into the pattern
    would suggest a restriction that does not exist.
    """
    name = f"enrichment_rel_{rel_type.lower()}_{prop}"
    return f"CREATE INDEX {name} IF NOT EXISTS FOR ()-[r:{rel_type}]-() ON (r.{prop})"


_RELATIONSHIP_INDEXES: Final[list[str]] = [
    *(
        _rel_index(rel_type, prop)
        for rel_type in PARALLEL_REL_TYPES
        for prop in _PARALLEL_REL_INDEXED_PROPERTIES
    ),
    # Concept assertions are filtered by trust and state far more often than traversed
    # blindly, because the point of the layer is being able to ask for only the
    # deterministic ones, or only the accepted ones.
    *(
        _rel_index(REL_ABOUT_CONCEPT, prop)
        for prop in ("trust", "score", "state", "pipeline_version")
    ),
    # Formula occurrences are scoped by Veda when comparing corpora, and by
    # pipeline_version for the same layer-separation reason as everything else here.
    *(_rel_index(REL_USES_FORMULA, prop) for prop in ("veda", "pipeline_version")),
]


ENRICHMENT_INDEXES: Final[list[str]] = [
    *_NODE_INDEXES,
    *_FULLTEXT_INDEXES,
    *_RELATIONSHIP_INDEXES,
]


def enrichment_constraints() -> list[str]:
    """Uniqueness constraints for the enrichment node labels."""
    return list(ENRICHMENT_CONSTRAINTS)


def enrichment_indexes() -> list[str]:
    """Node, full-text and relationship indexes for the enrichment layer."""
    return list(ENRICHMENT_INDEXES)


def all_enrichment_schema_cypher() -> list[str]:
    """Every enrichment schema statement, in application order.

    Constraints come first: a uniqueness constraint creates its own backing index, and
    creating a range index on the same label and property beforehand would leave a
    redundant index behind for ``drop_schema`` to clean up. Every statement carries
    ``IF NOT EXISTS``, so applying this list to a database that already has the schema is
    a no-op rather than an error -- which is what makes it safe to call at the top of
    every load rather than only on a fresh database.
    """
    return enrichment_constraints() + enrichment_indexes()
