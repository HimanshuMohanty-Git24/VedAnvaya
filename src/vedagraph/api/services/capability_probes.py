"""The rest of the NOT_ANSWERABLE population, each with a reproducible probe.

**Why this module exists.** ``GET /api/v1/insights/capabilities`` published seven limit
cards. The frozen 100-question benchmark grades twenty-one questions ``NOT_ANSWERABLE``.
The catalogue said so -- "this catalogue is not exhaustive" -- which is the right
disclosure and still leaves a reader who consults it to find out whether their question is
answerable with an incomplete answer that correctly warns them it is incomplete. That is
GAP-PRODUCT_SURFACE-002, and the fourteen missing dimensions are here, with the fifteenth
(Q49) which shares Q22's layer and needed a probe of its own regardless.

**The verdict is measured on every request, never copied from the benchmark.** This is the
load-bearing decision in the module. The benchmark is frozen at V3.3; the graph is not, and
three of these dimensions have moved since it was frozen:

* Q7 -- a reuse transformation typology now exists. 6,271 of 6,596 reuse edges carry
  ``cross_veda_transformation`` over a fifteen-value vocabulary. The benchmark's reason,
  *"the typology the criterion requires does not exist at all, on any edge"*, is no longer
  true of this graph.
* Q23 / Q37 / Q97 -- a deity community partition was computed and its twelve artifact
  nodes are stored. No deity is assigned to one, so the question is still unanswerable,
  but for a different reason than "no community computation exists anywhere".
* Q97 -- ``TIER_A`` now carries 8,129 passage-to-entity assertions. The benchmark's
  *"the high-confidence tier does not contain passage->concept or passage->entity
  assertions"* is half stale.

Pasting the frozen grades forward would have published three limitations that no longer
hold. A false limitation is the same class of defect as a false finding: it tells a reader
the product cannot do something it can. So every card carries ``benchmark_verdict`` beside
the live ``verdict``, and where they differ the difference is itself published.

**Editing rule.** A card's prose must not restate a figure the probe measures -- it
interpolates it. The seven original cards were written that way for the same reason, and
the one place a figure is typed rather than read is the one place nothing can catch it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Final

from vedagraph.api.models.insight import CapabilityVerdict

#: The five relationship classes that constitute textual reuse. Enumerated rather than
#: discovered: a class with no edges must still be counted, and a class discovered from the
#: data cannot be.
_REUSE_CLASSES: Final[str] = (
    "['EXACT_PARALLEL_OF','NEAR_PARALLEL_OF','REUSES_TEXT_FROM','VARIANT_OF','PARALLEL_TO']"
)

#: Benchmark question numbers the frozen V3.3 run grades NOT_ANSWERABLE. Declared here and
#: asserted against ``docs/reports/V3_3_FINAL_100_QUESTION_BENCHMARK.jsonl`` by
#: ``tests/api/test_capability_catalogue.py``, so the population this catalogue must cover
#: is checked against the artifact rather than remembered.
BENCHMARK_NOT_ANSWERABLE: Final[tuple[int, ...]] = (
    7,
    22,
    23,
    28,
    37,
    49,
    52,
    53,
    54,
    58,
    59,
    61,
    68,
    72,
    77,
    78,
    82,
    84,
    93,
    97,
    98,
)


#: Properties the probes read **expecting them to be absent**, and which are therefore
#: absent from ``db.propertyKeys()``.
#:
#: ``tests/api/test_cypher_property_hygiene.py`` asserts that every property the API's
#: Cypher reads exists in the graph, because a property that does not exist returns null
#: forever and renders as a blank field. This module is the one place where reading a
#: property that does not exist is the *measurement*: "no mantra carries a bridge score" is
#: established by asking for ``m.bridge_score`` and counting zero, and there is no way to
#: measure the absence of a property without naming it.
#:
#: So the hygiene test exempts exactly this set and nothing else, and it exempts it by
#: **re-measuring it**: a name here that turns out to exist in the graph fails, because a
#: probed absence that has become a presence means a limit card is now publishing a
#: limitation that no longer holds -- the precise defect this module was written to remove.
#: A typo in a probe still fails, because a typo is not in this set.
PROBED_ABSENT_PROPERTIES: Final[frozenset[str]] = frozenset(
    {
        "bridge_score",  # Q37: no mantra carries a betweenness or bridging score
        "betweenness",  # Q37, the same measurement under its other name
        "embedding",  # Q22/Q49/Q53: no node carries a vector representation
        "vector",  # Q49, the same measurement under its other name
        "expected_count",  # Q78: no entity carries an externally sourced expectation
    }
)
# ``ritual_context`` was in this set and is deliberately not any more. It was probed as an
# absence and it is now present on all 20,210 mantras, five-valued with absence typed. A
# name left here after the property appeared is the exact defect
# ``test_every_probed_absence_is_still_absent`` exists to catch: the Q84 card went on
# publishing "no verse carries a ritual-versus-non-ritual assignment" after every verse
# carried one. Q84 now grades itself from the measurement instead of asserting the absence.


@dataclass(frozen=True)
class ProbedLimitSpec:
    """One capability limit: a question, a probe, and how to grade what comes back."""

    limit_id: str
    question_number: int
    question: str
    benchmark_verdict: CapabilityVerdict
    cypher: str
    #: ``(field, means)`` pairs. ``field`` is the probe's returned column; ``means`` is
    #: required, because a bare zero is the figure this endpoint exists to stop shipping.
    measurements: tuple[tuple[str, str], ...]
    #: Grades the live measurement. Takes the probe's values and returns the verdict.
    grade: Callable[[Mapping[str, int | None]], CapabilityVerdict]
    #: Builds the explanation from the measurement. Never a fixed string with numbers in it.
    why: Callable[[Mapping[str, int | None]], str]
    what_this_is_not: str
    safe_alternative: str
    what_would_change_it: str
    endpoint: str | None = field(default=None)


def _n(values: Mapping[str, int | None], key: str) -> int:
    """A probe value as an int, treating an unmeasured column as zero for arithmetic only.

    The published measurement keeps the ``None``; this is used inside the prose builders so
    a formatted sentence never renders "None".
    """
    return values.get(key) or 0


def _always(verdict: CapabilityVerdict) -> Callable[[Mapping[str, int | None]], CapabilityVerdict]:
    return lambda _values: verdict


def _partial_if(
    predicate: Callable[[Mapping[str, int | None]], bool],
) -> Callable[[Mapping[str, int | None]], CapabilityVerdict]:
    """PARTIALLY_ANSWERABLE when the dimension has appeared, NOT_ANSWERABLE otherwise."""

    def grade(values: Mapping[str, int | None]) -> CapabilityVerdict:
        return (
            CapabilityVerdict.PARTIALLY_ANSWERABLE
            if predicate(values)
            else CapabilityVerdict.NOT_ANSWERABLE
        )

    return grade


NA: Final = CapabilityVerdict.NOT_ANSWERABLE

PROBED_LIMIT_SPECS: Final[tuple[ProbedLimitSpec, ...]] = (
    ProbedLimitSpec(
        limit_id="reuse_transformation_typology",
        question_number=7,
        question="How are reused verses transformed?",
        benchmark_verdict=NA,
        cypher=f"""
MATCH ()-[r]->() WHERE type(r) IN {_REUSE_CLASSES}
RETURN count(r) AS reuse_edges,
       sum(CASE WHEN r.cross_veda_transformation IS NOT NULL THEN 1 ELSE 0 END)
         AS edges_with_a_transformation_type,
       sum(CASE WHEN r.formula_transformation_type IS NOT NULL THEN 1 ELSE 0 END)
         AS formula_edges_with_a_transformation_type,
       count(DISTINCT r.cross_veda_transformation) AS transformation_vocabulary_size
""",
        measurements=(
            (
                "reuse_edges",
                "Every textual-reuse edge in the graph, across the five classes. The "
                "denominator for the typology's coverage.",
            ),
            (
                "edges_with_a_transformation_type",
                "Reuse edges carrying a named transformation. This is the figure the frozen "
                "benchmark recorded as zero; it is not zero now.",
            ),
            (
                "formula_edges_with_a_transformation_type",
                "The formula layer's own, coarser typology. A second instrument over "
                "overlapping edges, never summed with the first.",
            ),
            (
                "transformation_vocabulary_size",
                "Distinct transformation values. A typology with one value is a label, not "
                "a typology.",
            ),
        ),
        grade=_partial_if(lambda v: _n(v, "edges_with_a_transformation_type") > 0),
        why=lambda v: (
            f"A transformation typology exists and covers part of the layer: "
            f"{_n(v, 'edges_with_a_transformation_type'):,} of {_n(v, 'reuse_edges'):,} "
            f"reuse edges carry one, over a vocabulary of "
            f"{_n(v, 'transformation_vocabulary_size')} values, and a separate formula-level "
            f"typology reaches {_n(v, 'formula_edges_with_a_transformation_type'):,} edges. "
            "It is partial in two ways that matter. The typology describes the observable "
            "surface difference between two stored strings -- substitution, word division, "
            "accent notation -- and not the philological operation a scholar would name. "
            "And the uncovered remainder is not a residue: an edge without a type was not "
            "typed, which is not the same as an edge that was typed as unchanged."
        ),
        what_this_is_not=(
            "This is NOT the finding the frozen benchmark recorded. It graded this question "
            "NOT_ANSWERABLE on a measurement of zero typed edges, and the layer has since "
            "been built. Reading the frozen grade today would tell you the product cannot "
            "answer something it partly can. Equally, a surface-difference class is NOT a "
            "philological account of how or why a verse changed."
        ),
        safe_alternative=(
            "The cross-Veda relationship matrix, which reports each reuse class with its "
            "measured population and the classes that were never built at all."
        ),
        what_would_change_it=(
            "A transformation type on every reuse edge, and a second typology stated in "
            "philological rather than string-difference terms, with the two kept separate."
        ),
        endpoint="/api/v1/insights/cross-veda",
    ),
    ProbedLimitSpec(
        limit_id="mantra_bridges_between_concept_communities",
        question_number=37,
        question="Which mantras are central bridges between concept communities?",
        benchmark_verdict=NA,
        cypher="""
CALL () { MATCH (c:DeityCommunity) RETURN count(c) AS stored_community_partitions }
CALL () { MATCH (d:Devata) WHERE d.community_id IS NOT NULL
          RETURN count(d) AS deities_assigned_to_a_community }
CALL () { MATCH (m:Mantra) WHERE m.bridge_score IS NOT NULL OR m.betweenness IS NOT NULL
          RETURN count(m) AS mantras_with_a_bridge_score }
CALL () { MATCH (m:DerivedMetric)
          WHERE toLower(coalesce(m.metric_name,'')) CONTAINS 'bridge'
             OR toLower(coalesce(m.metric_name,'')) CONTAINS 'betweenness'
          RETURN count(m) AS stored_bridging_metrics }
RETURN stored_community_partitions, deities_assigned_to_a_community,
       mantras_with_a_bridge_score, stored_bridging_metrics
""",
        measurements=(
            (
                "stored_community_partitions",
                "Community artifact nodes in the graph. Non-zero, and it is not what the "
                "question needs: a partition with no members assigns nothing.",
            ),
            (
                "deities_assigned_to_a_community",
                "Subjects carrying a membership in one of those partitions. This zero is "
                "the first of two reasons the question cannot be answered.",
            ),
            (
                "mantras_with_a_bridge_score",
                "Mantras carrying any betweenness or bridging score. The second reason, and "
                "independent of the first.",
            ),
            (
                "stored_bridging_metrics",
                "Stored metrics of a bridging kind, under any name. Searched by name rather "
                "than assumed absent.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"Two independent absences, and only one of them is what the benchmark "
            f"recorded. A community computation now exists -- "
            f"{_n(v, 'stored_community_partitions')} partition artifacts are stored -- but "
            f"{_n(v, 'deities_assigned_to_a_community')} subjects carry a membership in one, "
            "so there are communities without members and nothing to be a bridge between. "
            f"Separately, {_n(v, 'mantras_with_a_bridge_score')} mantras carry a betweenness "
            f"or bridging score and {_n(v, 'stored_bridging_metrics')} metrics of that kind "
            "are stored, so even a populated partition would have no centrality to rank on."
        ),
        what_this_is_not=(
            "This is NOT a finding that no mantra bridges anything. It is also NOT the "
            "benchmark's reason any more: the benchmark said no community computation "
            "existed, and one does. The membership edges are what is missing."
        ),
        safe_alternative=(
            "Deity co-occurrence pairs with lift and per-corpus counts, which is a real "
            "measure over the same evidence and is pairs rather than communities."
        ),
        what_would_change_it=(
            "Membership edges from the computed partition to its members, and a stored "
            "centrality over an explicitly declared projection. A projection chosen at "
            "query time will not do: the natural one here is directed and bipartite, on "
            "which betweenness is 0.0 for every node."
        ),
        endpoint="/api/v1/insights/capabilities?question=37",
    ),
    ProbedLimitSpec(
        limit_id="cross_veda_resemblance_without_reuse",
        question_number=49,
        question="Which cross-Veda passages express similar ideas without textual reuse?",
        benchmark_verdict=NA,
        cypher=f"""
CALL () {{ MATCH ()-[r]->() WHERE type(r) IN {_REUSE_CLASSES}
           RETURN count(r) AS lexical_relatedness_edges }}
CALL () {{ MATCH ()-[r]->() WHERE type(r) IN ['SEMANTIC_RESEMBLANCE','RESEMBLES','SIMILAR_TO']
           RETURN count(r) AS asserted_resemblance_edges }}
CALL () {{ MATCH (n) WHERE n.embedding IS NOT NULL OR n.vector IS NOT NULL
           RETURN count(n) AS nodes_carrying_an_embedding }}
RETURN lexical_relatedness_edges, asserted_resemblance_edges, nodes_carrying_an_embedding
""",
        measurements=(
            (
                "lexical_relatedness_edges",
                "Every cross-corpus relationship this graph holds. All of them rest on "
                "shared wording, which is why they cannot answer a question that excludes it.",
            ),
            (
                "asserted_resemblance_edges",
                "Non-lexical resemblance asserted by any relationship. A typed zero: the "
                "measure was never built, so this is not a finding that no two verses resemble.",
            ),
            (
                "nodes_carrying_an_embedding",
                "Nodes with a vector representation. Zero, and there is no vector index "
                "either, so a similarity could not be computed at query time.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"All {_n(v, 'lexical_relatedness_edges'):,} cross-corpus relationships in this "
            "graph are grounded in shared wording, and the question excludes exactly that. "
            f"There are {_n(v, 'asserted_resemblance_edges')} asserted resemblance edges and "
            f"{_n(v, 'nodes_carrying_an_embedding')} nodes carrying an embedding, so a "
            "non-lexical similarity can be neither retrieved nor computed. Conceptual "
            "similarity without textual reuse therefore cannot be separated from chance."
        ),
        what_this_is_not=(
            "This is NOT a finding that cross-corpus relatedness in the Vedas is purely "
            "textual. It is a statement that this graph measures only the textual kind."
        ),
        safe_alternative=(
            "The cross-Veda matrix, which reports the built classes with their populations "
            "and prints SEMANTIC_RESEMBLANCE as NOT_BUILT rather than as a zero row."
        ),
        what_would_change_it=(
            "An embedding or an asserted-resemblance layer with a stated chance baseline, "
            "so a pair can be told from two verses that happen to share a subject."
        ),
        endpoint="/api/v1/insights/cross-veda",
    ),
    ProbedLimitSpec(
        limit_id="concept_route_between_deities",
        question_number=53,
        question=(
            "Which concepts connect Agni and Soma by a route that is not simple lexical "
            "co-occurrence?"
        ),
        benchmark_verdict=NA,
        cypher="""
CALL () { MATCH (:Concept)-[r]->(:Concept) RETURN count(r) AS concept_to_concept_relations }
CALL () { MATCH (:Concept)-[r]->(:Concept) WHERE r.knowledge_layer = 'L4_INTERPRETIVE_CLAIM'
          RETURN count(r) AS curated_interpretive_relations }
CALL () { MATCH (n) WHERE n.embedding IS NOT NULL RETURN count(n) AS nodes_carrying_an_embedding }
RETURN concept_to_concept_relations, curated_interpretive_relations, nodes_carrying_an_embedding
""",
        measurements=(
            (
                "concept_to_concept_relations",
                "Relations between concepts of any kind. Small, and the size is the point: "
                "a route through a layer this sparse is an artefact of what was curated.",
            ),
            (
                "curated_interpretive_relations",
                "Of those, the ones typed as an interpretive claim rather than read from a "
                "source. A route through these is a route through an editor's judgement.",
            ),
            (
                "nodes_carrying_an_embedding",
                "The second-order distributional route the question allows as an "
                "alternative. Zero, so that route does not exist either.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"The question requires a measure that excludes same-verse co-occurrence, and "
            f"the two candidates both fail. The asserted concept-to-concept layer holds "
            f"{_n(v, 'concept_to_concept_relations')} relations in total, of which "
            f"{_n(v, 'curated_interpretive_relations')} are typed as interpretive claims: "
            "a path found through a layer of that size says more about which relations were "
            "curated than about the corpus. And there are "
            f"{_n(v, 'nodes_carrying_an_embedding')} embeddings, so a second-order "
            "distributional similarity with a chance baseline cannot be computed at all."
        ),
        what_this_is_not=(
            "This is NOT a finding that Agni and Soma are unconnected. Same-verse "
            "co-occurrence connects them densely; the question asks for a route that is not "
            "that, and that route is what is missing."
        ),
        safe_alternative=(
            "Deity co-occurrence with lift, which states plainly that it is same-verse "
            "co-occurrence and does not dress it as a conceptual route."
        ),
        what_would_change_it=(
            "A concept-to-concept layer built over the whole concept inventory rather than "
            "curated, or a distributional model with a stated null."
        ),
        endpoint="/api/v1/insights/capabilities?question=53",
    ),
    ProbedLimitSpec(
        limit_id="ontology_domain_bridges",
        question_number=54,
        question=(
            "Which entities act as bridges between the ritual sub-graph and the "
            "cosmological sub-graph?"
        ),
        benchmark_verdict=NA,
        cypher="""
MATCH (c:Concept)
RETURN count(c) AS concepts,
       count(c.wave3_domain) AS concepts_assigned_to_a_domain,
       size(collect(DISTINCT c.wave3_domain)) AS declared_domains
""",
        measurements=(
            (
                "concepts",
                "Every concept node. The population a domain partition would have to cover.",
            ),
            (
                "concepts_assigned_to_a_domain",
                "Concepts carrying a declared ontology domain. Non-zero, which is a change "
                "from the benchmark's reading that no domain is declared anywhere.",
            ),
            (
                "declared_domains",
                "How many distinct domains are declared. One. A bridge needs two sides, and "
                "this is the measurement that says there is one.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"The question presupposes two declared domains with enough members to "
            f"constitute sub-graphs. There is one: {_n(v, 'concepts_assigned_to_a_domain')} "
            f"of {_n(v, 'concepts')} concepts carry a domain and "
            f"{_n(v, 'declared_domains')} distinct domain is declared. A cosmological domain "
            "is not declared anywhere in the ontology, so there is one side and no second "
            "side to bridge to. Partitioning by label instead would substitute a class "
            "hierarchy for a domain, which is a different claim."
        ),
        what_this_is_not=(
            "This is NOT the benchmark's reason. It recorded that neither domain was "
            "declared; one now is. It is also NOT a finding that no entity spans ritual and "
            "cosmology -- the second domain is simply not written down."
        ),
        safe_alternative=(
            "The ritual layer view, which reports the declared ritual domain with its "
            "membership and the ceilings on it, without inventing a counterpart."
        ),
        what_would_change_it=(
            "A second declared domain with its own membership, and a bridging measure over the two."
        ),
        endpoint="/api/v1/insights/rituals",
    ),
    ProbedLimitSpec(
        limit_id="semantic_function_change_under_reuse",
        question_number=58,
        question=(
            "Which lexical forms are reused across Vedas while their semantic function changes?"
        ),
        benchmark_verdict=NA,
        cypher="""
MATCH (a:SemanticAssertion)
RETURN count(a) AS semantic_assertions,
       count(DISTINCT a.derivation) AS derivation_paths,
       sum(CASE WHEN a.veda IS NOT NULL AND a.veda <> 'RV' THEN 1 ELSE 0 END)
         AS assertions_outside_the_rigveda
""",
        measurements=(
            (
                "semantic_assertions",
                "Every stored semantic assertion. All of them are computed from the verse's "
                "own tokens, which is why they cannot detect a function change.",
            ),
            (
                "derivation_paths",
                "How the assertions were derived. Two paths, one rule-based and one model "
                "extraction, and neither is independent of the wording.",
            ),
            (
                "assertions_outside_the_rigveda",
                "The layer's reach. A cross-corpus comparison needs both sides, and this "
                "zero means only one side exists.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            "Detecting a function change needs a function assignment that does not depend on "
            f"the wording. This graph has none: all {_n(v, 'semantic_assertions'):,} "
            f"assertions are derived from the verse's own tokens by "
            f"{_n(v, 'derivation_paths')} paths, so a verbatim-reused verse is assigned the "
            "same function in both corpora by construction and a change can never be "
            f"observed. The layer also carries {_n(v, 'assertions_outside_the_rigveda')} "
            "assertions outside the Rigveda, so there is no second corpus to compare against."
        ),
        what_this_is_not=(
            "This is NOT a finding that reused verses keep their function. The instrument "
            "is incapable of registering a change, which is a different statement and the "
            "one this card makes."
        ),
        safe_alternative=(
            "The reuse layer itself with its per-pair evidence quotes, which shows what "
            "changed in the wording without claiming anything about function."
        ),
        what_would_change_it=(
            "A function assignment grounded in context rather than in the verse's own "
            "tokens, extended to at least two corpora."
        ),
        endpoint="/api/v1/insights/cross-veda",
    ),
    ProbedLimitSpec(
        limit_id="directional_textual_reuse",
        question_number=59,
        question=("Which passage pairs have the strongest evidence of directional textual reuse?"),
        benchmark_verdict=NA,
        cypher=f"""
MATCH ()-[r]->() WHERE type(r) IN {_REUSE_CLASSES}
RETURN count(r) AS reuse_edges,
       sum(CASE WHEN r.cross_veda_stored_as_directed = true THEN 1 ELSE 0 END)
         AS edges_stored_as_directed,
       count(DISTINCT r.cross_veda_direction_basis) AS distinct_direction_bases
""",
        measurements=(
            (
                "reuse_edges",
                "Every reuse edge. The denominator for how far direction reaches.",
            ),
            (
                "edges_stored_as_directed",
                "Edges stored with a direction. Real, and all of them inherit one "
                "tradition-level prior about one corpus pair rather than carrying per-pair "
                "evidence.",
            ),
            (
                "distinct_direction_bases",
                "How many distinct grounds for direction are recorded. Two: one prior, and "
                "an explicit statement that the rest are symmetric and must not be read as "
                "a claim about which text came first.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"Direction exists for {_n(v, 'edges_stored_as_directed'):,} of "
            f"{_n(v, 'reuse_edges'):,} reuse edges, and it is one prior applied wholesale "
            "rather than per-pair evidence: the Kauthuma arcika is an arrangement of "
            "Rigvedic verses and its own tradition names the Rigveda as the source, so every "
            "edge in that pair inherits the same direction from the same sentence. The "
            "criterion states that a single global prior applied to one Veda pair is not "
            "per-pair evidence, which is exactly what this is. The remaining edges are "
            "explicitly typed symmetric, which is the honest form and not a weaker direction."
        ),
        what_this_is_not=(
            "The directed edges are NOT wrong and NOT to be discarded: the Samavedic "
            "borrowing is well established. They are simply not per-pair evidence, and "
            "ranking pairs by 'strength of directional evidence' over them would rank one "
            "sentence about a tradition six hundred times."
        ),
        safe_alternative=(
            "The reuse layer as stored, where a symmetric pair is typed symmetric and the "
            "one directed corpus pair states the prior it rests on."
        ),
        what_would_change_it=(
            "Per-pair directional evidence -- metrical, linguistic or contextual -- that can "
            "distinguish borrower from source for a pair, independently of the tradition's "
            "own statement about the collection."
        ),
        endpoint="/api/v1/insights/formula-diffusion",
    ),
    ProbedLimitSpec(
        limit_id="deity_to_offering_assignment",
        question_number=61,
        question=(
            "Which Devatas are associated with which specific offerings, on per-verse "
            "source-stated evidence?"
        ),
        benchmark_verdict=NA,
        cypher="""
CALL () { MATCH (:Devata)-[r]->(o) WHERE o:Offering OR o:Substance
          RETURN count(r) AS deity_to_offering_edges }
CALL () { MATCH (:Devata)-[r]->(:Offering) WHERE r.attribution_precision = 'PER_PASSAGE'
          RETURN count(r) AS edges_with_per_verse_evidence }
CALL () { MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata)
          MATCH (p)-[:MENTIONS_ENTITY]->(:Offering)
          RETURN count(DISTINCT p) AS passages_naming_both }
RETURN deity_to_offering_edges, edges_with_per_verse_evidence, passages_naming_both
""",
        measurements=(
            (
                "deity_to_offering_edges",
                "Edges from a deity to an offering. Non-zero, and every one of them is an "
                "identity link -- Soma to soma, the cow to cattle -- where the devata slot "
                "and the substance are the same thing, not a record of who receives what.",
            ),
            (
                "edges_with_per_verse_evidence",
                "Of those, the ones whose evidence is a span in a particular verse. Their "
                "evidence is a concept-lexicon locator instead, which is a dictionary entry "
                "and not a passage.",
            ),
            (
                "passages_naming_both",
                "Verses that name a deity and an offering. Large, and it is co-occurrence: "
                "naming both in one verse is not a statement that one is offered to the "
                "other, and treating it as one is how this question was answered wrongly.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"There is no deity-to-offering relation in the sense the question needs. The "
            f"{_n(v, 'deity_to_offering_edges')} edges that exist are identity links between "
            "a devata slot and the substance it names, and "
            f"{_n(v, 'edges_with_per_verse_evidence')} of them carry a per-verse textual "
            "span -- their evidence is a lexicon locator. The tempting substitute, the "
            f"{_n(v, 'passages_naming_both'):,} verses that name a deity and an offering "
            "together, is co-occurrence: it would rank Indra with soma because both appear "
            "in the same hymns, not because a verse says soma is offered to Indra."
        ),
        what_this_is_not=(
            "This is NOT a finding that the Vedas do not assign offerings to deities -- they "
            "do so constantly. It is a statement that this graph has no edge that records it."
        ),
        safe_alternative=(
            "The ritual layer view, which reports the offerings a modelled rite is curated "
            "to use and states the curation ceiling above them."
        ),
        what_would_change_it=(
            "A deity-to-offering relation carrying a per-verse span that names both, built "
            "from the text rather than from co-occurrence."
        ),
        endpoint="/api/v1/insights/rituals",
    ),
    ProbedLimitSpec(
        limit_id="epithet_occurrence_layer",
        question_number=68,
        question="Which deity epithets cluster with which actions?",
        benchmark_verdict=NA,
        cypher="""
CALL () { MATCH (e:Epithet) RETURN count(e) AS epithets }
CALL () { OPTIONAL MATCH (:Passage)-[r:HAS_EPITHET]->(:Epithet)
          RETURN count(r) AS passage_level_epithet_occurrences }
CALL () { MATCH (:Devata)-[r:HAS_EPITHET]->(:Epithet) RETURN count(r) AS deity_level_epithet_edges }
RETURN epithets, passage_level_epithet_occurrences, deity_level_epithet_edges
""",
        measurements=(
            (
                "epithets",
                "Epithet nodes in the graph. A handful, and they are a glossary rather than "
                "an annotation of the corpus.",
            ),
            (
                "passage_level_epithet_occurrences",
                "Verses annotated as containing an epithet. This zero is the whole answer: "
                "with no occurrences there is nothing to join to the action layer.",
            ),
            (
                "deity_level_epithet_edges",
                "Epithets attached to a deity rather than to a verse. This is what exists, "
                "and it says which epithets belong to whom, not where they occur.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"Epithets have no occurrence layer. The graph holds {_n(v, 'epithets')} epithet "
            f"nodes attached to deities by {_n(v, 'deity_level_epithet_edges')} edges, and "
            f"{_n(v, 'passage_level_epithet_occurrences')} verses are annotated as containing "
            "one. Clustering epithets with actions requires knowing which verse each epithet "
            "occurs in, so that it can be joined to the verb-argument layer in that verse. "
            "The first requirement is absent outright."
        ),
        what_this_is_not=(
            "This is NOT a finding that Vedic epithets carry no action profile. Nothing was "
            "measured, because the layer the measurement would run over does not exist."
        ),
        safe_alternative=(
            "A deity's action distribution from the agentive layer, which is real, is "
            "Rigveda-only, and says nothing about epithets."
        ),
        what_would_change_it=(
            "An epithet occurrence annotation per verse, at which point the join to the "
            "existing verb-argument layer is mechanical."
        ),
        endpoint="/api/v1/insights/capabilities?question=68",
    ),
    ProbedLimitSpec(
        limit_id="conflicting_interpretive_claims",
        question_number=72,
        question=(
            "Which interpretive claims in the graph have conflicting evidence, and what "
            "exactly is the conflict?"
        ),
        benchmark_verdict=NA,
        cypher="""
MATCH (c:InterpretiveClaim)
RETURN count(c) AS interpretive_claims,
       sum(CASE WHEN c.about = 'VEDIC_TEXT' THEN 1 ELSE 0 END) AS claims_about_the_vedic_text,
       sum(CASE WHEN c.asserted_by IS NOT NULL AND c.asserted_by <> '' THEN 1 ELSE 0 END)
         AS claims_attributed_to_a_named_position,
       sum(CASE WHEN EXISTS { (c)-[:CONTRADICTS]->() } THEN 1 ELSE 0 END)
         AS claims_with_a_recorded_contradiction
""",
        measurements=(
            (
                "interpretive_claims",
                "Every interpretive claim in the graph. Six, which is the size of the whole "
                "layer and not a filtered subset.",
            ),
            (
                "claims_about_the_vedic_text",
                "Of those, the ones about the corpus rather than about this dataset's own "
                "construction. The question explicitly excludes the second kind.",
            ),
            (
                "claims_attributed_to_a_named_position",
                "Claims attributed to a named scholarly position. This zero is decisive: an "
                "unattributed claim cannot be one side of a scholarly disagreement.",
            ),
            (
                "claims_with_a_recorded_contradiction",
                "Claims carrying a typed contradiction. Real, and they contradict a reading "
                "of this dataset rather than a named scholar.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"The layer holds {_n(v, 'interpretive_claims')} claims in total, of which "
            f"{_n(v, 'claims_about_the_vedic_text')} are about the Vedic text rather than "
            f"about this dataset's construction, and "
            f"{_n(v, 'claims_attributed_to_a_named_position')} are attributed to a named "
            "scholarly position. The criterion needs at least a dozen attributed claims "
            "about Vedic content with typed supporting and contradicting evidence on both "
            f"sides. {_n(v, 'claims_with_a_recorded_contradiction')} carry a contradiction at "
            "all, and those contradict a reading of this dataset."
        ),
        what_this_is_not=(
            "This is NOT a finding that Vedic scholarship agrees. It is a statement that "
            "this graph does not hold scholarly disagreement, and that the handful of claims "
            "it does hold are its own, not anyone's."
        ),
        safe_alternative=(
            "The claims as stored, each with its falsifier, read as this dataset's own "
            "positions rather than as a survey of scholarship."
        ),
        what_would_change_it=(
            "An ingested body of attributed scholarly positions on Vedic passages, with "
            "their evidence typed on both sides."
        ),
        endpoint="/api/v1/insights/capabilities?question=72",
    ),
    ProbedLimitSpec(
        limit_id="entities_too_thin_to_support_a_claim",
        question_number=78,
        question="Which major entities have coverage too thin to support a claim about them?",
        benchmark_verdict=NA,
        cypher="""
MATCH (n:DomainEntity)
RETURN count(n) AS entities_in_the_graph,
       sum(CASE WHEN n.samhita_attestation_count IS NOT NULL THEN 1 ELSE 0 END)
         AS entities_with_a_curated_attestation_count,
       sum(CASE WHEN n.expected_count IS NOT NULL THEN 1 ELSE 0 END)
         AS entities_with_an_external_expectation
""",
        measurements=(
            (
                "entities_in_the_graph",
                "Every entity the graph holds. It can rank these by thinness; that is not "
                "what the question asks.",
            ),
            (
                "entities_with_a_curated_attestation_count",
                "Entities carrying a curated attestation figure. Real, and it is a count of "
                "what was found, not a statement of what should have been found.",
            ),
            (
                "entities_with_an_external_expectation",
                "Entities carrying an externally sourced expected count. This zero is the "
                "trap the question sets: without it, 'too thin' has no denominator.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"The graph can enumerate its {_n(v, 'entities_in_the_graph')} entities and rank "
            "them by how little evidence each carries. What it cannot do is say which "
            "*major* entities are underrepresented, because that needs a manifest of "
            "entities that ought to be present, and "
            f"{_n(v, 'entities_with_an_external_expectation')} entities carry an external "
            f"expectation. The {_n(v, 'entities_with_a_curated_attestation_count')} curated "
            "attestation counts are counts of what was found, so an entity missing from the "
            "graph entirely is missing from the ranking too -- which is precisely the "
            "population the question is about."
        ),
        what_this_is_not=(
            "A ranking of the thinnest entities the graph holds is NOT an answer to this "
            "question, and serving it as one would be the question's own trap sprung: the "
            "entity with no node at all ranks nowhere."
        ),
        safe_alternative=(
            "The entity listing with each entity's measured evidence count, read as a "
            "statement about the graph's coverage rather than about the corpus."
        ),
        what_would_change_it=(
            "An externally sourced manifest of entities expected in the Samhitas, against "
            "which presence and thinness both become measurable."
        ),
        endpoint="/api/v1/entities",
    ),
    ProbedLimitSpec(
        limit_id="ritual_versus_non_ritual_context",
        question_number=84,
        question=(
            "Which crops, metals and animals occur in which Vedas and in which contexts -- "
            "ritual versus non-ritual?"
        ),
        benchmark_verdict=NA,
        cypher="""
MATCH (m:Mantra)
RETURN count(m) AS mantras,
       sum(CASE WHEN EXISTS { (m)-[:USED_FOR_RITE]->() } THEN 1 ELSE 0 END)
         AS mantras_linked_to_a_rite,
       sum(CASE WHEN m.ritual_context IS NOT NULL THEN 1 ELSE 0 END)
         AS mantras_with_a_context_assignment,
       sum(CASE WHEN m.ritual_context IN
                 ['RITE_NAMED_IN_THIS_MANTRA', 'EMPLOYED_IN_RITE', 'EMPLOYED_IN_RITE_PROBABLE']
                THEN 1 ELSE 0 END)
         AS mantras_placed_in_a_rite,
       sum(CASE WHEN m.ritual_context IN
                 ['NO_RITUAL_CITATION_FOUND', 'UNRESOLVED_SHARED_OPENING']
                THEN 1 ELSE 0 END)
         AS mantras_whose_context_is_a_typed_absence
""",
        measurements=(
            (
                "mantras",
                "Every verse in the corpus. The population a context assignment would have "
                "to cover for the split to mean anything.",
            ),
            (
                "mantras_linked_to_a_rite",
                "Verses linked to a rite. Real, and it is a same-verse mention of a rite "
                "rather than an assignment of the verse to a ritual setting.",
            ),
            (
                "mantras_with_a_context_assignment",
                "Verses carrying a ritual-context assignment. Every verse carries one, "
                "which is a statement about coverage of the axis and not about how many "
                "of them resolve to a rite.",
            ),
            (
                "mantras_placed_in_a_rite",
                "Verses the assignment actually places in a rite, certainly or probably. "
                "This is the figure a context split can be run on.",
            ),
            (
                "mantras_whose_context_is_a_typed_absence",
                "Verses whose assignment is a typed non-answer -- no citation found, or an "
                "opening shared with rival verses that the citation cannot choose between. "
                "Counted here so the coverage figure above cannot be read as resolution.",
            ),
        ),
        grade=_partial_if(lambda v: _n(v, "mantras_placed_in_a_rite") > 0),
        why=lambda v: (
            "The axis exists and it resolves for a minority of the corpus. Every one of the "
            f"{_n(v, 'mantras'):,} verses carries a ritual-context assignment derived from "
            "external ritual citation, but "
            f"only {_n(v, 'mantras_placed_in_a_rite'):,} of them are placed in a rite; the "
            f"other {_n(v, 'mantras_whose_context_is_a_typed_absence'):,} carry a typed "
            "absence -- no citation found, or an opening shared with rival verses. So a "
            "crop-by-context or metal-by-context split is now possible over the resolved "
            "verses and is NOT served by any endpoint yet: no product surface reads "
            "ritual_context. What has changed is that the axis exists to build it on, and "
            "that a split built on it would have to carry the typed absence rather than "
            "collapse it into a zero."
        ),
        what_this_is_not=(
            "The coverage figure is NOT a resolution figure, and neither is a finding that "
            "Vedic crops and metals are non-ritual. A verse whose context is "
            "NO_RITUAL_CITATION_FOUND is one no surviving ritual manual cites, which is a "
            "fact about the manuals and not about the verse."
        ),
        safe_alternative=(
            "The material-culture and metals views, which report occurrence by corpus with "
            "the lexical-minimum ceiling stated, and do not split by context. There is no "
            "context-split endpoint to point at: the axis is on the verses and nothing "
            "reads it yet."
        ),
        what_would_change_it=(
            "Two things, and only one of them is a data problem. A surface that reads the "
            "axis, which nothing does yet; and raising resolution rather than coverage, "
            "because the verses held at UNRESOLVED_SHARED_OPENING are blocked on choosing "
            "between rival verses that share a pratika, which a pratika-disambiguating "
            "index of the sutra literature would settle."
        ),
        endpoint="/api/v1/insights/material-culture",
    ),
    ProbedLimitSpec(
        limit_id="narrative_and_myth_episode_layer",
        question_number=93,
        question="Which weapons occur in which narratives?",
        benchmark_verdict=NA,
        cypher="""
CALL () { MATCH (w:Weapon) RETURN count(w) AS weapons_in_the_registry }
CALL () { MATCH (:Passage)-[r:HAS_THEME]->() RETURN count(r) AS passage_theme_edges }
CALL () { CALL db.labels() YIELD label
          WHERE toLower(label) CONTAINS 'narrat' OR toLower(label) CONTAINS 'myth'
             OR toLower(label) CONTAINS 'episode'
          RETURN count(label) AS narrative_labels }
RETURN weapons_in_the_registry, passage_theme_edges, narrative_labels
""",
        measurements=(
            (
                "weapons_in_the_registry",
                "Weapons the graph knows. The half of the question that exists.",
            ),
            (
                "passage_theme_edges",
                "Verses carrying a theme. The nearest thing to a narrative, and a theme is "
                "a subject label rather than an episode with participants.",
            ),
            (
                "narrative_labels",
                "Node labels naming a narrative, myth or episode. This zero is the layer "
                "the question is built on, searched for by name rather than assumed absent.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"The graph holds {_n(v, 'weapons_in_the_registry')} weapons and no narrative "
            f"layer: {_n(v, 'narrative_labels')} node labels name a narrative, myth or "
            f"episode, and the {_n(v, 'passage_theme_edges')} theme edges that exist attach a "
            "subject label to a verse rather than grouping verses into an episode. There is "
            "no way to say 'these verses tell the Vrtra-slaying', so a weapon cannot be "
            "placed in a narrative and no role in one can be recorded."
        ),
        what_this_is_not=(
            "This is NOT a finding that the Vedas contain no narratives. The corpus is full "
            "of them; this graph has no construct that represents one."
        ),
        safe_alternative=(
            "Weapon occurrence by corpus from the material-culture view, with its lexical "
            "minimum stated."
        ),
        what_would_change_it=(
            "A myth-episode construct grouping verses into episodes, with participant roles "
            "on the membership."
        ),
        endpoint="/api/v1/insights/material-culture",
    ),
    ProbedLimitSpec(
        limit_id="communities_over_high_confidence_edges",
        question_number=97,
        question=(
            "Which communities emerge when the graph is restricted to high-confidence edges?"
        ),
        benchmark_verdict=NA,
        cypher="""
CALL () { MATCH (:Passage)-[r]->() WHERE r.quality_tier = 'TIER_A'
            AND type(r) IN ['MENTIONS_DEVATA','HAS_DEVATA','ABOUT_CONCEPT','MENTIONS_ENTITY']
          RETURN count(r) AS tier_a_passage_to_entity_edges }
CALL () { MATCH (:Passage)-[r]->() WHERE r.quality_tier = 'TIER_A'
            AND type(r) IN ['ABOUT_CONCEPT','MENTIONS_ENTITY']
          RETURN count(r) AS tier_a_passage_to_concept_edges }
CALL () { MATCH (d:Devata) WHERE d.community_id IS NOT NULL
          RETURN count(d) AS subjects_assigned_to_a_community }
RETURN tier_a_passage_to_entity_edges, tier_a_passage_to_concept_edges,
       subjects_assigned_to_a_community
""",
        measurements=(
            (
                "tier_a_passage_to_entity_edges",
                "High-confidence edges from a verse to an entity. Non-zero, which reverses "
                "the benchmark's first clause: the high-confidence tier is no longer purely "
                "bibliographic.",
            ),
            (
                "tier_a_passage_to_concept_edges",
                "Of those, the ones reaching a concept. Still zero: the concept layer sits "
                "entirely at TIER_B, so a high-confidence restriction removes it completely.",
            ),
            (
                "subjects_assigned_to_a_community",
                "Subjects carrying a community membership. The second clause, and it fails "
                "absolutely whatever tier is chosen.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            "Half of the benchmark's reason no longer holds and the other half is decisive. "
            f"The high-confidence tier now carries "
            f"{_n(v, 'tier_a_passage_to_entity_edges'):,} verse-to-entity assertions, so it "
            "is not purely bibliographic as the benchmark recorded -- although "
            f"{_n(v, 'tier_a_passage_to_concept_edges')} of them reach a concept, so "
            "restricting to high confidence still deletes the concept layer outright. The "
            f"second clause is what closes it: {_n(v, 'subjects_assigned_to_a_community')} "
            "subjects carry a community membership at any tier, so there is no partition to "
            "restrict."
        ),
        what_this_is_not=(
            "This is NOT a finding that high-confidence Vedic evidence yields no structure. "
            "No partition exists to be restricted, and the restriction itself would silently "
            "drop the concept layer, which a returned answer would not have disclosed."
        ),
        safe_alternative=(
            "Deity co-occurrence with the tier of each contributing edge stated, so a reader "
            "can see what a confidence filter would remove."
        ),
        what_would_change_it=(
            "Community memberships stored on subjects, and a concept layer that reaches "
            "TIER_A so the restriction does not amount to deleting a whole dimension."
        ),
        endpoint="/api/v1/insights/capabilities?question=97",
    ),
    ProbedLimitSpec(
        limit_id="path_interpretability_score",
        question_number=98,
        question=(
            "Which graph paths are meaningful versus accidental -- can a path be scored for "
            "interpretability?"
        ),
        benchmark_verdict=NA,
        cypher="""
CALL () { MATCH (m:DerivedMetric) WHERE toLower(coalesce(m.metric_name,'')) CONTAINS 'path'
          RETURN count(m) AS stored_path_metrics }
CALL () { MATCH ()-[r]->() WHERE r.review_state = 'HUMAN_REVIEWED'
          RETURN count(r) AS human_reviewed_edges }
CALL () { MATCH ()-[r]->() WHERE r.quality_tier IS NOT NULL RETURN count(r) AS graded_edges }
RETURN stored_path_metrics, human_reviewed_edges, graded_edges
""",
        measurements=(
            (
                "stored_path_metrics",
                "Stored metrics of a path kind, under any name. Searched by name rather "
                "than assumed absent.",
            ),
            (
                "human_reviewed_edges",
                "Edges a human has reviewed. This zero bounds every calibration question in "
                "this product: with no judged sample, no score can be calibrated against "
                "anything.",
            ),
            (
                "graded_edges",
                "Edges carrying a quality grade. Large, and a grade per edge is not a score "
                "per path: multiplying grades along a path would invent a number.",
            ),
        ),
        grade=_always(NA),
        why=lambda v: (
            f"A path can be traversed and each of its {_n(v, 'graded_edges'):,} candidate "
            "edges carries a grade, but there is no scoring function with a stated basis, "
            f"{_n(v, 'stored_path_metrics')} stored path metrics, and "
            f"{_n(v, 'human_reviewed_edges')} human-reviewed edges to calibrate one against. "
            "Composing per-edge grades into a per-path number would produce a sortable "
            "ranking that nothing validates, which is worse than refusing: the ranking would "
            "look like a finding."
        ),
        what_this_is_not=(
            "This is NOT a finding that graph paths here are meaningless. It is the absence "
            "of any instrument that could tell a meaningful one from an accidental one."
        ),
        safe_alternative=(
            "The path endpoint, which returns the path with every edge's own grade and "
            "evidence and leaves the judgement to the reader."
        ),
        what_would_change_it=(
            "A human-judged sample of paths, and a scoring function calibrated against it "
            "with its basis stated."
        ),
        endpoint="/api/v1/graph/path",
    ),
)
