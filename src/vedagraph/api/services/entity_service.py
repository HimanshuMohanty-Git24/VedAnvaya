"""Deities, seers, rites, conditions and every other knowledge object.

One service for all of them, and that is the point rather than a compromise. The failure
this file is shaped against is not a wrong query -- it is thirty endpoints, twenty-nine of
which remembered a contract and one of which did not. So the deity population filter is
applied in exactly one place per surface and comes from
:mod:`vedagraph.api.services.deity_population`; the certainty tiers come from
:mod:`vedagraph.domain.theonyms`; and the caveats come from the frozen query catalogue via
:func:`~vedagraph.api.repositories.neo4j_repository.named_query_caveat` rather than being
retyped, because V3.1 and V3.2 both found hand-copied caveat prose that had drifted from
the data it described.

**The four things this file exists to get right.**

*A deity list must not contain a dog.* The Anukramani names a devata for every Rigvedic
hymn and 30 of the 214 are not gods. Every deity query interpolates
:func:`~vedagraph.api.services.deity_population.deity_structure_clause` and binds its
structure list; the two populations run the same Cypher and differ only in that parameter.

*A co-deity list must not contain a human.* ``profile_co_devatas`` holds display labels,
not keys, and Indra's is literally ``['Vasukra']`` -- a human patron. The labels are
resolved back to ``:Devata`` nodes and filtered by structure, and the result for Indra is an
empty list that says why it is empty rather than an empty list that means nothing.

*A per-Veda zero must never be printed.* ``profile_mentions_by_veda_certainty`` gives the
three tiers per corpus, and the tier filter can empty a corpus that is richly attested:
Agni has 831 CERTAIN Rigvedic mentions and *zero* CERTAIN anywhere else, against 170
PROBABLE in the Atharvaveda, 97 in the Yajurveda and 82 in the Samaveda. Under
``certainty=strict`` those three corpora return ``count: null`` with
``INSUFFICIENT_EVIDENCE`` and never ``count: 0``.

*Naming is not ascribing.* ``MENTIONS_DEVATA`` (17,165 edges, all four corpora) answers
"is this deity named here?"; ``HAS_DEVATA`` (10,558 edges, every one Rigvedic, 8,329 of
them inherited from a sukta label) answers "does the Anukramani dedicate this hymn to it?".
``GET /devatas/{id}/passages`` takes ``basis`` and each row carries which relation put it
there, because a count from one presented as the other is wrong by construction.
"""

from __future__ import annotations

from typing import Any, Final, Protocol

from vedagraph.api.errors import BadRequestError, EntityNotFoundError, UnknownEntityTypeError
from vedagraph.api.models.common import (
    AttributionPrecision,
    CaveatView,
    CountedByVeda,
    CoverageView,
    EvidenceView,
    KnowledgeStatus,
    Paginated,
    ReferentCertaintyCounts,
    basis_from_attribution_precision,
    evidence_surface,
    paginate,
)
from vedagraph.api.models.entity import (
    ABSTRACT_HETEROGENEITY_CAVEAT,
    ALLOWED_ID_PROPERTIES,
    DEITY_SLUGS,
    DEITY_SURFACE_REDIRECT,
    ENTITY_TYPES,
    KNOWN_DEITY_AXES,
    AttributedRef,
    CentralityView,
    ConditionKindFilter,
    ConditionSummary,
    DeityPopulation,
    DevataNetwork,
    DevataNetworkEdge,
    DevataPassagePage,
    DevataPassageRef,
    DevataProfile,
    DevataSummary,
    DimensionStatus,
    EntityListRow,
    EntityProfile,
    EntityRef,
    EntityTypeSpec,
    MentionBasis,
    MentionCertainty,
    RecallView,
    RishiProfile,
    RitualProcedureSource,
    RitualProcedureStep,
    RitualProfile,
    RitualStep,
    RitualSummary,
    VedaMentionCount,
    parse_json_property,
    status_for_verdict,
)
from vedagraph.api.models.search import EntityTypeInfo, EntityTypeInventory
from vedagraph.api.repositories.neo4j_repository import named_query_caveat, validated_label
from vedagraph.api.services.deity_population import (
    KNOWN_DEITY_STRUCTURES,
    NOT_A_DEITY_SUBJECT,
    deity_structure_clause,
    deity_structure_parameters,
    filter_co_deity_labels,
    is_deity,
    population_caveats,
    subject_disclosure,
)
from vedagraph.api.services.search_service import VEDA_ORDER, result_type_for_labels
from vedagraph.domain.layer_figures import CORPUS_MANTRAS
from vedagraph.domain.ontology import product_filter
from vedagraph.domain.theonyms import AMBIGUOUS, CERTAIN, PROBABLE, referent_tiers_for_mode


class _Repository(Protocol):
    def run(self, cypher: str, /, **parameters: Any) -> list[dict[str, Any]]: ...

    def run_one(self, cypher: str, /, **parameters: Any) -> dict[str, Any] | None: ...


# ---------------------------------------------------------------------------
# Shared contract text and dimension mapping
# ---------------------------------------------------------------------------


#: The attribution-scope statement. Mandatory wherever an attribution figure appears: the
#: Anukramani layer is Rigvedic and a zero elsewhere is a missing apparatus.
ATTRIBUTION_SCOPE_STATEMENT: Final = (
    "ATTRIBUTION IS NOT MENTION, AND IT IS RIGVEDIC. The `attributed_*` figures come from "
    "HAS_DEVATA, the Anukramani's hymn-level dedication: 10,558 edges, every one on the "
    "Rigveda, and 8,329 of them a sukta's label projected onto each of its mantras rather "
    "than a statement about the verse. A zero for the Samaveda, Yajurveda or Atharvaveda "
    "means those corpora carry no Anukramani apparatus, NOT that the deity is absent from "
    "them -- for that read `mentions_by_veda`, which spans all four."
)

#: The Samaveda statement. Mandatory wherever a Samavedic figure appears, because the SV
#: differs from the other three in kind and not only in size.
SAMAVEDA_SCOPE_STATEMENT: Final = (
    "SAMAVEDA SCOPE: the Kauthuma Samaveda is present as the arcika (verse) collection "
    "only -- 1,844 mantras -- and the gana song corpus is not included. It carries no "
    "Anukramani seer or metre apparatus and no English translation, and its share of the "
    "deity mention layer comes from surface and sandhi matching rather than from the "
    "manual morphological annotation the Rigveda has. Compare it as a share of its 1,844 "
    "mantras, never as a raw total against the Rigveda's 10,552."
)

#: The strict-mode warning, mandatory on any response that filtered to CERTAIN alone.
STRICT_MODE_STATEMENT: Final = (
    "certainty=strict counts DEITY_CERTAIN only, and that is measured to be a Rigvedic "
    "grade rather than an accuracy grade: it returns ZERO non-Rigvedic mentions for Agni, "
    "Soma, Surya, Mitra, Savitr, Usas, Vayu, Apah and Prthivi. Any corpus whose count is "
    "null with INSUFFICIENT_EVIDENCE below has mentions at a lower tier that this filter "
    "removed; it is not an absence in the text. The cautious request gets the narrower "
    "answer here, not the safer one."
)

#: Which knowledge layer each materialised profile dimension comes from, and therefore
#: which status its absence deserves. NOT_BUILT where the layer cannot reach this deity at
#: all; INSUFFICIENT_EVIDENCE where it reaches it and could not settle the question.
#:
#: Measured rather than guessed: the six deities carrying ``top_actions`` in
#: ``profile_absent_dimensions`` are exactly the ones whose ``profile_mention_scope``
#: excludes the Rigveda or is empty, and the action layer is an aggregate over the 2,406
#: MORPHOLOGY_RULE assertions, all of which are Rigvedic.
_DIMENSION_STATUS: Final[dict[str, tuple[KnowledgeStatus, str]]] = {
    "co_devatas": (
        KnowledgeStatus.INSUFFICIENT_EVIDENCE,
        "The co-occurrence layer reaches all four corpora and could not establish a "
        "co-deity for this deity at the lift threshold the build used. Not an assertion "
        "that it is named alone.",
    ),
    "co_mentioned": (
        KnowledgeStatus.INSUFFICIENT_EVIDENCE,
        "No co-mention could be established for this deity in the mention layer.",
    ),
    "mentions": (
        KnowledgeStatus.NOT_BUILT,
        "This entry is an Anukramani ascription with no theonym in the mention registry, "
        "so the four-Veda mention layer does not reach it at all. Its ascription figures "
        "are still real; its mention figures do not exist.",
    ),
    "top_actions": (
        KnowledgeStatus.NOT_BUILT,
        "PERFORMS_ACTION aggregates the 2,406 MORPHOLOGY_RULE assertions, which come from "
        "the Rigveda-only lemma annotation. A deity absent here is absent from that "
        "annotation, not from Vedic action.",
    ),
    "top_requested_actions": (
        KnowledgeStatus.NOT_BUILT,
        "IS_ASKED_TO aggregates the same Rigveda-only morphology layer as PERFORMS_ACTION.",
    ),
    "top_objects": (
        KnowledgeStatus.NOT_BUILT,
        "The object dimension is derived from the Rigveda-only semantic assertion layer.",
    ),
    "top_concepts": (
        KnowledgeStatus.NOT_BUILT,
        "The concept dimension is derived from the Rigveda-only annotation layers.",
    ),
    "formula_count": (
        KnowledgeStatus.INSUFFICIENT_EVIDENCE,
        "No formula could be associated with this deity's mantras.",
    ),
}


def _dimension_status(name: str) -> DimensionStatus:
    status, note = _DIMENSION_STATUS.get(
        name,
        (
            KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            "The build recorded this dimension as unestablished for this entity. Its empty "
            "value is not an assertion of absence.",
        ),
    )
    return DimensionStatus(dimension=name, status=status, note=note)


def tiers_for(certainty: MentionCertainty, include_ambiguous: bool) -> frozenset[str]:
    """The referent tiers a request may read.

    Delegates to :func:`~vedagraph.domain.theonyms.referent_tiers_for_mode`, which raises
    on an unknown mode rather than falling back to the widest set -- a typo silently
    widening this filter is how an ambiguous row reaches a user as a fact.
    ``include_ambiguous`` then ADDS the ambiguous tier, so ``default`` plus
    ``include_ambiguous`` is by construction the same set as ``exploratory``.
    """
    tiers = referent_tiers_for_mode(certainty.value)
    return tiers | {AMBIGUOUS} if include_ambiguous else tiers


def _text(value: Any) -> str | None:
    """A string property, with the empty string read as absent.

    Several properties in the frozen graph carry ``''`` where a null belongs
    (``upstream_correction_id``, ``model``, ``prompt_policy``, ``devata_subtype`` on the
    unclassified entries). Passing that through would render an empty label, an empty
    description or an empty note as though the graph had said something, and a client
    cannot distinguish "" from a real value it should display.
    """
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _as_list(value: Any) -> list[str]:
    """A list property, with empty and whitespace-only members dropped as absent."""
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _text(item) if isinstance(item, str) else (None if item is None else str(item))
        if text is not None:
            out.append(text)
    return out


def _as_bool(value: Any) -> bool | None:
    """A boolean property, with absent left absent rather than coerced to False.

    ``is_seer`` is only meaningful on a ``:Rishi``; every other type must report ``null``
    rather than ``false``, which would assert that a river is not a seer instead of saying
    the question does not apply.
    """
    return bool(value) if isinstance(value, bool) else None


def _row_subtitle(row: dict[str, Any]) -> str | None:
    """The list row's one-line disambiguator, naming a non-seer as one.

    A seer list whose first row is Aditi needs to say so on the row: the subtitle is what a
    client renders without reading the schema.
    """
    kind = _text(row.get("condition_kind"))
    if kind:
        return kind
    if row.get("is_seer") is False:
        return f"not a seer: {_text(row.get('non_seer_kind')) or 'kind unrecorded'}"
    if row.get("is_seer") is True:
        return "seer"
    return None


def _as_int(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _as_float(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _tier_map(raw: Any) -> dict[str, dict[str, int]]:
    """Read ``profile_mentions_by_veda_certainty``, a JSON string on the node.

    A malformed value degrades to empty rather than raising: one bad property should cost
    one field, not the request. The caller sees the resulting nulls as
    INSUFFICIENT_EVIDENCE, which is the honest reading of "we could not parse our own
    profile".
    """
    parsed = parse_json_property(raw)
    if not isinstance(parsed, dict):
        return {}
    out: dict[str, dict[str, int]] = {}
    for tier, per_veda in parsed.items():
        if isinstance(per_veda, dict):
            out[str(tier)] = {
                str(v): int(n) for v, n in per_veda.items() if isinstance(n, (int, float))
            }
    return out


def _grid_to_tier_map(grid: Any) -> dict[str, dict[str, int]]:
    """Read a collected ``[veda, certainty, count]`` grid into ``{tier: {veda: n}}``.

    Replaces :func:`_tier_map`, which parsed the same shape out of a JSON string property
    that only 30 of the 214 Devata nodes carry.
    """
    out: dict[str, dict[str, int]] = {}
    if not isinstance(grid, list):
        return out
    for entry in grid:
        if not isinstance(entry, list) or len(entry) != 3:
            continue
        veda, tier, count = entry
        if veda is None or tier is None or not isinstance(count, (int, float)):
            continue
        out.setdefault(str(tier), {})[str(veda)] = int(count)
    return out


def _pairs_to_counts(pairs: Any) -> dict[str, int]:
    """Read a collected ``[key, count]`` list into a mapping, skipping null keys."""
    out: dict[str, int] = {}
    if not isinstance(pairs, list):
        return out
    for entry in pairs:
        if isinstance(entry, list) and len(entry) == 2 and entry[0] is not None:
            if isinstance(entry[1], (int, float)):
                out[str(entry[0])] = int(entry[1])
    return out


def _verdicts(raw: Any) -> dict[str, str]:
    parsed = parse_json_property(raw)
    if not isinstance(parsed, dict):
        return {}
    return {str(k): str(v) for k, v in parsed.items()}


# ---------------------------------------------------------------------------
# Deity queries
# ---------------------------------------------------------------------------

#: The deity-population predicate for the far end of a deity-to-deity traversal, written
#: once so every branch of the network query inherits the same answer.
_OTHER_IS_DEITY: Final = deity_structure_clause("other")

#: The same predicate for the near end, used where the deity is the traversal target.
_DV_IS_DEITY: Final = deity_structure_clause("dv")


#: Every materialised profile property, plus the axes, epithets and interpretive claims,
#: in one round trip. Four OPTIONAL MATCHes in one scope would multiply each other, so
#: each is collected in its own ``CALL`` subquery -- the mistake
#: ``deity_reach_named_versus_ascribed`` documents, where a sibling OPTIONAL MATCH turned
#: 3,196 x 2,869 rows into one figure.
_DEVATA_NODE_QUERY: Final = """
MATCH (dv:Devata {entity_key: $key})
CALL (dv) {
    OPTIONAL MATCH (:Passage)-[m:MENTIONS_DEVATA]->(dv)
    RETURN m.referent_certainty AS certainty, count(*) AS edges
}
WITH dv, collect([certainty, edges]) AS certainty_split
CALL (dv) {
    OPTIONAL MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(dv)
    RETURN p.veda AS veda, m.referent_certainty AS certainty, count(DISTINCT p) AS n
}
WITH dv, certainty_split, collect([veda, certainty, n]) AS mention_grid
CALL (dv) {
    OPTIONAL MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(dv)
      WHERE m.referent_certainty IN $tiers
    RETURN p.veda AS veda, count(DISTINCT p) AS named
}
WITH dv, certainty_split, mention_grid, collect([veda, named]) AS named_by_veda
CALL (dv) {
    OPTIONAL MATCH (p:Passage)-[h:HAS_DEVATA]->(dv)
    RETURN count(DISTINCT p) AS ascribed,
           count(DISTINCT CASE WHEN h.attribution_precision = 'PER_PASSAGE'
                               THEN p END) AS ascribed_strict,
           collect(DISTINCT p.veda) AS ascribed_vedas
}
CALL (dv) {
    OPTIONAL MATCH (dv)-[:HAS_AXIS]->(ax:DeityAxis)
    RETURN collect(DISTINCT {id: ax.axis_key, label: ax.display_label, axis: ax.axis}) AS axes
}
CALL (dv) {
    OPTIONAL MATCH (dv)-[:HAS_EPITHET]->(ep:Epithet)
    RETURN collect(DISTINCT coalesce(ep.label_iast, ep.display_label)) AS epithets
}
CALL (dv) {
    OPTIONAL MATCH (dv)<-[:CONCERNS]-(cl:InterpretiveClaim)
    RETURN collect(DISTINCT {id: cl.claim_id, label: cl.short_description}) AS claims
}
RETURN properties(dv) AS props, axes, epithets, claims, certainty_split, mention_grid,
       named_by_veda, ascribed, ascribed_strict, ascribed_vedas
"""

#: The three-tier split over every one of a deity's mention edges, unfiltered. Its shape
#: matches ``_DEVATA_INSIGHT_QUERY``'s certainty block exactly, so the deity page and the
#: insight page cannot report different splits for the same deity.
_DEVATA_CERTAINTY_QUERY: Final = """
MATCH (:Passage)-[m:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
RETURN m.referent_certainty AS certainty, count(*) AS edges
"""

#: Defect A containment. ``profile_co_devatas`` stores DISPLAY LABELS, so each is resolved
#: back to a ``:Devata`` node and the row carries the structure that decides whether it is
#: a deity. Unresolvable labels come back with a null key and are dropped by
#: :func:`filter_co_deity_labels` rather than rendered as a bare string.
_CO_DEITY_QUERY: Final = """
MATCH (dv:Devata {entity_key: $key})
WITH coalesce(dv.profile_co_devatas, []) AS profile_labels
UNWIND profile_labels AS profile_label
OPTIONAL MATCH (other:Devata) WHERE other.display_label = profile_label
RETURN profile_label, other.entity_key AS entity_key,
       other.display_label AS display_label, other.structure AS structure,
       other.short_description AS short_description
"""

#: Formulas recurring in the mantras that name this deity. There is no Devata-to-Formula
#: edge in the graph, so this is deliberately a co-occurrence within the tier-filtered
#: mention layer and the caveat says so.
_DEVATA_FORMULA_QUERY: Final = """
MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
WHERE m.referent_certainty IN $tiers
MATCH (p)-[:USES_FORMULA]->(f:Formula)
RETURN f.formula_id AS id, coalesce(f.display_form, f.normalized) AS label,
       count(DISTINCT p) AS passages
ORDER BY passages DESC, id
LIMIT $top
"""


#: The deity list. There is ONE query text and the population chooses only the bound
#: structure list, so there is no second code path in which the filter can be forgotten --
#: which is precisely how one of the two carried-forward defects would come back.
_DEVATA_LIST_QUERY: Final = f"""
MATCH (dv:Devata)
WHERE {_DV_IS_DEITY}
  AND ($structure IS NULL OR dv.structure = $structure)
  AND ($axis IS NULL OR EXISTS {{ (dv)-[:HAS_AXIS]->(:DeityAxis {{axis: $axis}}) }})
RETURN dv.entity_key AS id, dv.display_label AS display_label,
       dv.label_iast AS label_iast, dv.structure AS structure,
       dv.short_description AS short_description, dv.axes AS axes,
       dv.is_composite AS is_composite,
       dv.profile_mentions_by_veda_certainty AS tier_json,
       dv.profile_attributed_total AS attributed_total,
       coalesce(dv.profile_mentions_total, 0) AS sort_total
ORDER BY sort_total DESC, id
SKIP $offset LIMIT $limit
"""

_DEVATA_COUNT_QUERY: Final = f"""
MATCH (dv:Devata)
WHERE {_DV_IS_DEITY}
  AND ($structure IS NULL OR dv.structure = $structure)
  AND ($axis IS NULL OR EXISTS {{ (dv)-[:HAS_AXIS]->(:DeityAxis {{axis: $axis}}) }})
RETURN count(dv) AS total
"""


#: Passages that NAME the deity. Tier-filtered, four corpora.
_DEVATA_MENTION_PASSAGES: Final = """
MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
WHERE m.referent_certainty IN $tiers
  AND ($veda IS NULL OR p.veda = $veda)
RETURN p.canonical_key AS passage_id, p.canonical_citation AS citation, p.veda AS veda,
       m.referent_certainty AS referent_certainty, m.occurrences AS occurrences,
       m.matched_forms AS matched_forms, m.quality_tier AS quality_tier,
       m.method AS method, m.evidence_basis AS evidence_basis,
       m.referent_basis AS referent_basis, m.extraction_path AS extraction_path,
       m.attribution_precision AS attribution_precision
ORDER BY p.canonical_key
SKIP $offset LIMIT $limit
"""

_DEVATA_MENTION_COUNT: Final = """
MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
WHERE m.referent_certainty IN $tiers AND ($veda IS NULL OR p.veda = $veda)
RETURN count(DISTINCT p) AS total
"""

#: Passages the Anukramani ASCRIBES to the deity. Rigvedic by construction.
_DEVATA_ASCRIPTION_PASSAGES: Final = """
MATCH (p:Passage)-[h:HAS_DEVATA]->(:Devata {entity_key: $key})
WHERE ($veda IS NULL OR p.veda = $veda)
RETURN p.canonical_key AS passage_id, p.canonical_citation AS citation, p.veda AS veda,
       h.attribution_precision AS attribution_precision, h.quality_tier AS quality_tier,
       h.evidence_basis AS evidence_basis, h.provenance_class AS provenance_class,
       h.scope_origin AS scope_origin, h.confidence AS confidence
ORDER BY p.canonical_key
SKIP $offset LIMIT $limit
"""

_DEVATA_ASCRIPTION_COUNT: Final = """
MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
WHERE ($veda IS NULL OR p.veda = $veda)
RETURN count(DISTINCT p) AS total
"""


#: The neighbourhood, with every deity-valued side of it population-filtered.
#:
#: ``CO_OCCURS_WITH`` is traversed UNDIRECTED: the 306 edges are stored one way and a
#: directed traversal would return half a deity's neighbours and call it all of them.
_DEVATA_NETWORK_QUERY: Final = f"""
MATCH (dv:Devata {{entity_key: $key}})
CALL (dv) {{
    OPTIONAL MATCH (dv)-[c:CO_OCCURS_WITH]-(other:Devata)
    WHERE {_OTHER_IS_DEITY}
    RETURN collect({{
        id: other.entity_key, label: other.display_label,
        subtitle: other.short_description, lift: c.lift,
        passage_count: c.passage_count, rv: c.rv_passage_count,
        non_rv: c.non_rv_passage_count, per_veda: c.per_veda_counts,
        examples: c.example_citations, tier: c.quality_tier,
        evidence_caveat: c.evidence_caveat
    }})[0..$top] AS co_occurring
}}
CALL (dv) {{
    OPTIONAL MATCH (dv)-[:COMPOSED_OF]->(other:Devata)
    WHERE {_OTHER_IS_DEITY}
    RETURN collect(DISTINCT {{id: other.entity_key, label: other.display_label,
                              subtitle: other.structure}}) AS components
}}
CALL (dv) {{
    OPTIONAL MATCH (dv)-[:MEMBER_OF]->(other:Devata)
    WHERE {_OTHER_IS_DEITY}
    RETURN collect(DISTINCT {{id: other.entity_key, label: other.display_label,
                              subtitle: other.structure}}) AS member_of
}}
CALL (dv) {{
    OPTIONAL MATCH (dv)-[:HAS_AXIS]->(ax:DeityAxis)
    RETURN collect(DISTINCT {{id: ax.axis_key, label: ax.display_label,
                              subtitle: ax.axis}}) AS axes
}}
CALL (dv) {{
    OPTIONAL MATCH (dv)-[:DEVATA_ASSOCIATED_WITH]->(e)
    RETURN collect(DISTINCT {{id: coalesce(e.entity_key, e.concept_id),
                              label: e.display_label,
                              labels: labels(e)}})[0..$top] AS associated
}}
RETURN dv.display_label AS display_label, co_occurring, components, member_of, axes,
       associated
"""

#: DEFECT B CONTAINMENT: deities reached through the seers a deity shares.
#:
#: Two things the unfiltered walk gets wrong, both verified against the live graph for
#: Indra. Without the structure clause the neighbours include "praise of a patron's gift"
#: (31 mantras), the sons of Vasistha (9), "praise of the gift of Svanaya" (7), Vasukra
#: (5), Svanaya Bhavayavya (5), Atri (4), Brbu the carpenter (3), Visvamitra (3), Vamadeva
#: (1), "praise of the gift of Sudas son of Pijavana" (4) and the dog (1) -- 22
#: non-deities in all. Without ``rs.is_seer`` the bridge is also allowed to run through
#: the 113 ``:Rishi`` nodes that are not seers -- Aditi, the Waters, a plant -- so two
#: deities would be reported as connected by "a seer they share" who is in fact a third
#: deity that both hymns address.
#:
#: Purpose: which deities share seers with this one, and over how many mantras.
#: Caveat: HAS_DEVATA is Rigvedic and 95.5% of HAS_RISHI is sukta-inherited, so this is a
#: co-attribution figure over the Anukramani apparatus and not a claim about composition.
#: Parameters: ``$key`` (deity), ``$top`` (row cap), plus the bound structure list.
#: ``WITH DISTINCT`` twice, and that is not tidying. The seer bridge is a four-hop walk,
#: and expressed as one pattern Indra's 2,869 ascribed mantras multiply their seers by
#: those seers' mantras by those mantras' deities before anything is aggregated: measured
#: at 2,133ms against 30ms for the staged form, which collapses to the ~50 distinct seers
#: and then to their distinct passages before touching the deity end.
_SHARED_RISHI_DEITIES_QUERY: Final = f"""
MATCH (:Devata {{entity_key: $key}})<-[:HAS_DEVATA]-(p:Passage)-[:HAS_RISHI]->(rs:Rishi)
WHERE coalesce(rs.is_seer, false)
WITH DISTINCT rs
MATCH (rs)<-[:HAS_RISHI]-(p2:Passage)
WITH DISTINCT p2
MATCH (p2)-[:HAS_DEVATA]->(other:Devata)
WHERE other.entity_key <> $key AND {_OTHER_IS_DEITY}
RETURN other.entity_key AS id, other.display_label AS label,
       other.structure AS structure, count(p2) AS shared_mantras
ORDER BY shared_mantras DESC, id
LIMIT $top
"""


# ---------------------------------------------------------------------------
# Generic entity queries
# ---------------------------------------------------------------------------


def _entity_list_query(spec: EntityTypeSpec) -> str:
    """The list query for one type. Label and id property are both allow-listed first.

    Carries ``product_filter`` because it did not, and the inventory endpoint beside it did:
    /api/v1/entities/chandas returned 575 rows while /api/v1/entities reported 547 for the
    same type, the difference being 28 nodes marked :Internal. The ontology calls
    ``product_filter`` "the one place the product/internal boundary is written as Cypher.
    Every product query interpolates this" -- and this was the query that showed rows.

    ``passage_count`` COUNTS THE EDGES, using the same ``_PASSAGE_TO_ENTITY`` predicate set
    and the same ``count(DISTINCT p)`` as the detail view, so a row and its own profile
    cannot disagree. They did: reading
    ``coalesce(n.mention_edges_total, n.occurrence_count, ...)`` landed on an unrelated
    registry statistic for a ``:Rishi`` -- no Rishi node carries ``mention_edges_total``
    and 367 carry ``occurrence_count = 0`` -- so 367 of 729 seers reported a bare ``0``
    while holding real ``HAS_RISHI`` edges (Vasistha read 0 against 836), and 501 of 729
    rows disagreed with the graph. Atharvan read 121 in the list and 1,282 in its profile.

    ``is_seer`` and ``non_seer_kind`` are projected here for the same reason
    :class:`~vedagraph.api.models.entity.EntityListRow` carries ``kind``: the response
    caveat promises them on every row, and the list is where a client picks a seer. 113 of
    the 729 are not seers.
    """
    label = validated_label(spec.label)
    id_property = _validated_id_property(spec.id_property)
    return f"""
MATCH (n:{label})
WHERE {product_filter("n")}
  AND ($condition_kind IS NULL OR n.condition_kind = $condition_kind)
  AND ($name IS NULL OR toLower(coalesce(n.display_label, '')) CONTAINS $name)
CALL (n) {{
    OPTIONAL MATCH (p:Passage)-[{_PASSAGE_TO_ENTITY}]->(n)
    RETURN count(DISTINCT p) AS passage_count
}}
RETURN n.{id_property} AS id, n.display_label AS display_label,
       coalesce(n.label_iast, n.preferred_label_sa, n.preferred_label) AS label_iast,
       n.short_description AS short_description, n.condition_kind AS condition_kind,
       n.display_type AS display_type, labels(n) AS node_labels,
       n.is_seer AS is_seer, n.non_seer_kind AS non_seer_kind,
       passage_count,
       coalesce(n.centrality_degree, 0.0) AS sort_degree
ORDER BY sort_degree DESC, id
SKIP $offset LIMIT $limit
"""


def _entity_count_query(spec: EntityTypeSpec) -> str:
    label = validated_label(spec.label)
    # The same product filter as the list query above and the inventory beside it. Without
    # it this total counted internal nodes: /api/v1/entities/chandas reported 575 against
    # the inventory's 547, the difference being 28 retired metre identities marked
    # :Internal by M10 -- and six of them were on page 1.
    return f"""
MATCH (n:{label})
WHERE {product_filter("n")}
  AND ($condition_kind IS NULL OR n.condition_kind = $condition_kind)
  AND ($name IS NULL OR toLower(coalesce(n.display_label, '')) CONTAINS $name)
RETURN count(n) AS total
"""


def _entity_node_query(spec: EntityTypeSpec) -> str:
    label = validated_label(spec.label)
    id_property = _validated_id_property(spec.id_property)
    return f"""
MATCH (n:{label} {{{id_property}: $id}})
CALL (n) {{
    OPTIONAL MATCH (p:Passage)-[{_PASSAGE_TO_ENTITY}]->(n)
    RETURN collect(DISTINCT p.veda) AS reached_vedas, count(DISTINCT p) AS passage_count
}}
CALL (n) {{
    OPTIONAL MATCH (n)-[r]-(m)
    WHERE (m:DomainEntity OR m:Devata OR m:Rishi OR m:RishiFamily) AND m <> n
    RETURN collect(DISTINCT {{id: coalesce(m.entity_key, m.concept_id, m.family_key),
                              label: m.display_label, labels: labels(m),
                              structure: m.structure,
                              relation: type(r)}})[0..$top] AS neighbours
}}
RETURN properties(n) AS props, labels(n) AS node_labels, reached_vedas, passage_count,
       neighbours
"""


#: The predicates that put a passage and a knowledge object together. Written once so the
#: passage count, the per-Veda breakdown and the co-mention neighbourhood all count the
#: same thing -- three predicate lists that drifted apart would give one object three
#: different reaches in one payload.
_PASSAGE_TO_ENTITY: Final = (
    ":MENTIONS_ENTITY|ABOUT_CONCEPT|TREATS|PROTECTS_FROM"
    "|ADDRESSES_CONCERN|USED_FOR_RITE|USES_FORMULA|HAS_RISHI|HAS_CHANDAS"
)


def _entity_co_mention_query(spec: EntityTypeSpec) -> str:
    """What is named in the same mantras as this object, strongest first.

    The reason this exists beside ``neighbours``: most domain entities carry NO curated
    edge to another entity at all -- ``VG:CONCEPT:TAKMAN-FEVER`` has none -- so a detail
    view built only on direct edges answers "what surrounds fever?" with an empty list.
    The two are kept as separate fields rather than merged, because a curated
    ``BROADER_THAN`` and a co-mention are different strengths of claim and this graph's
    whole discipline is not to blend those.

    Caveat: co-occurrence within a mantra. No causal or prescriptive claim, and none of
    pharmacology -- apamarga is named against sorcery, not against a cough.
    Parameters: ``$id``, ``$top``.
    """
    label = validated_label(spec.label)
    id_property = _validated_id_property(spec.id_property)
    return f"""
MATCH (n:{label} {{{id_property}: $id}})
MATCH (p:Passage)-[{_PASSAGE_TO_ENTITY}]->(n)
MATCH (p)-[:MENTIONS_ENTITY]->(m:DomainEntity)
WHERE m <> n
RETURN coalesce(m.entity_key, m.concept_id) AS id, m.display_label AS label,
       labels(m) AS labels, count(DISTINCT p) AS passages
ORDER BY passages DESC, id
LIMIT $top
"""


def _entity_passages_by_veda_query(spec: EntityTypeSpec) -> str:
    label = validated_label(spec.label)
    id_property = _validated_id_property(spec.id_property)
    return f"""
MATCH (n:{label} {{{id_property}: $id}})
MATCH (p:Passage)-[{_PASSAGE_TO_ENTITY}]->(n)
RETURN p.veda AS veda, count(DISTINCT p) AS passages
"""


def _validated_id_property(name: str) -> str:
    """Refuse an identity property that is not on the registry's allow-list.

    A second gate behind :data:`~vedagraph.api.models.entity.ENTITY_TYPES`. The registry
    decides which property a type uses; this refuses anything outside the union of them
    even if the registry were later mis-edited to name an arbitrary string.
    """
    if name not in ALLOWED_ID_PROPERTIES:
        raise BadRequestError(f"'{name}' is not an identity property of a knowledge type.")
    return name


#: Condition rows need their own query: ``ConditionSummary`` promises the treated and
#: protected-from counts, and the three predicates carry different tiers so they are
#: counted separately rather than unioned into one number.
_CONDITION_LIST_QUERY: Final = f"""
MATCH (n:Condition)
WHERE ($condition_kind IS NULL OR n.condition_kind = $condition_kind)
  AND ($name IS NULL OR toLower(coalesce(n.display_label, '')) CONTAINS $name)
CALL (n) {{
    OPTIONAL MATCH (p:Passage)-[:TREATS]->(n)
    RETURN count(DISTINCT p) AS treated
}}
CALL (n) {{
    OPTIONAL MATCH (p:Passage)-[:PROTECTS_FROM]->(n)
    RETURN count(DISTINCT p) AS protected
}}
CALL (n) {{
    // The SAME predicate set and the SAME count(DISTINCT p) as the detail view, so a
    // condition row cannot disagree with its own profile. It did: this counted
    // MENTIONS_ENTITY alone while the profile counted all nine relations, and
    // yaksma-disease read 89 here against 132 there.
    OPTIONAL MATCH (p:Passage)-[{_PASSAGE_TO_ENTITY}]->(n)
    RETURN count(DISTINCT p) AS passage_count
}}
RETURN n.entity_key AS id, n.display_label AS display_label,
       n.preferred_label_sa AS label_iast, n.short_description AS short_description,
       n.condition_kind AS condition_kind, treated, protected, passage_count
ORDER BY passage_count DESC, id
SKIP $offset LIMIT $limit
"""

#: Rishi profile. Every count is kept in its own subquery and the strict and inherited
#: attributions are returned as separate columns, never summed: the Yajurveda's 2,240 seer
#: edges are every one source-stated and the Atharvaveda's 5,084 are every one inherited,
#: so a blended total would compare a statement of the text against a projection.
_RISHI_PROFILE_QUERY: Final = """
MATCH (rs:Rishi {entity_key: $id})
CALL (rs) {
    OPTIONAL MATCH (p:Passage)-[h:HAS_RISHI]->(rs)
    RETURN collect(DISTINCT {veda: p.veda, precision: h.attribution_precision,
                             key: p.canonical_key}) AS seer_edges
}
CALL (rs) {
    OPTIONAL MATCH (rs)-[:BELONGS_TO_FAMILY]->(fam:RishiFamily)
    RETURN collect(DISTINCT {id: fam.family_key, label: fam.display_label,
                             subtitle: fam.patronymic_iast})[0..5] AS families
}
CALL (rs) {
    OPTIONAL MATCH (p:Passage)-[:HAS_RISHI]->(rs)
    OPTIONAL MATCH (p)-[:HAS_CHANDAS]->(ch:Chandas)
    RETURN collect(DISTINCT {id: ch.entity_key, label: ch.display_label}) AS chandas
}
CALL (rs) {
    OPTIONAL MATCH (p:Passage)-[:HAS_RISHI]->(rs)
    OPTIONAL MATCH (p)-[:USES_FORMULA]->(f:Formula)
    RETURN count(DISTINCT f) AS formula_count
}
RETURN properties(rs) AS props, seer_edges, families, chandas, formula_count
"""


#: Deities attributed to this seer's mantras, each row carrying its own precision.
#:
#: The precision is per row and never averaged. 15,177 of 17,889 seer edges and 8,329 of
#: 10,558 deity ascriptions are container-inherited, so a reference without its precision
#: lets a hymn-level ascription read as a statement the verse itself makes.
_RISHI_DEITIES_QUERY: Final = f"""
MATCH (p:Passage)-[h:HAS_RISHI]->(:Rishi {{entity_key: $id}})
MATCH (p)-[d:HAS_DEVATA]->(dv:Devata)
WHERE {_DV_IS_DEITY}
WITH dv,
     sum(CASE WHEN h.attribution_precision = 'PER_PASSAGE'
                AND d.attribution_precision = 'PER_PASSAGE' THEN 1 ELSE 0 END) AS strict,
     count(DISTINCT p) AS passages
RETURN dv.entity_key AS id, dv.display_label AS label, dv.structure AS structure,
       strict, passages
ORDER BY passages DESC, id
LIMIT $top
"""


_RISHI_CONCEPTS_QUERY: Final = """
MATCH (p:Passage)-[:HAS_RISHI]->(:Rishi {entity_key: $id})
MATCH (p)-[:MENTIONS_ENTITY]->(c:Concept)
RETURN c.entity_key AS id, c.display_label AS label, count(DISTINCT p) AS passages
ORDER BY passages DESC, id
LIMIT $top
"""

_RISHI_FAMILY_MEMBERS_QUERY: Final = """
MATCH (fam:RishiFamily {family_key: $id})<-[:BELONGS_TO_FAMILY]-(rs:Rishi)
RETURN rs.entity_key AS id, rs.display_label AS label, rs.is_seer AS is_seer,
       rs.non_seer_kind AS non_seer_kind
ORDER BY label
LIMIT $top
"""

# ---------------------------------------------------------------------------
# Ritual queries
# ---------------------------------------------------------------------------

#: The measurement the ritual coverage statement is built from. Read from the graph rather
#: than typed into the prose, because a figure inside a sentence is the one nothing checks:
#: this statement said "EIGHT MODELLED RITES" for a whole wave after the rite inventory
#: became 103, and only an API contract test asserting an unrelated total caught it.
_RITUAL_COVERAGE_QUERY: Final = """
CALL () { MATCH (r:Ritual) RETURN count(r) AS rites }
CALL () { MATCH (:Ritual)-[h:HAS_STEP]->() RETURN count(h) AS samhita_steps }
CALL () {
    MATCH (:Ritual)-[h:HAS_RITUAL_STEP]->()
    RETURN count(h) AS procedure_steps,
           sum(CASE WHEN h.order_completeness = 'PARTIAL_STATED_POSITIONS' THEN 1 ELSE 0 END)
               AS partial_steps
}
CALL () {
    MATCH (r:Ritual) WHERE (r)-[:HAS_RITUAL_STEP]->()
    RETURN count(r) AS rites_with_procedure
}
CALL () {
    MATCH (:Ritual)-[a:USES_OFFERING|USES_SUBSTANCE|USES_OBJECT|PERFORMED_BY|PERFORMED_FOR]->()
    RETURN count(a) AS apparatus_edges
}
RETURN rites, samhita_steps, procedure_steps, partial_steps, rites_with_procedure,
       apparatus_edges
"""


def ritual_coverage_statement(
    *,
    rites: int,
    samhita_steps: int,
    procedure_steps: int,
    partial_steps: int,
    rites_with_procedure: int,
    apparatus_edges: int,
) -> str:
    """Build the ritual bound from measured figures.

    Every number in the sentence is an argument. The previous version was a literal string
    asserting eight rites and three steps; both were true when written, and Wave 3 made the
    first one wrong by 95 while the prose went on claiming it.

    The two step families stay distinct in the wording for the same reason they are distinct
    predicates in the graph: the Samhita numbering a hymn states and the order a sutra prints
    are different claims, and collapsing them into one count would describe procedural
    coverage the Samhita layer does not have.
    """
    partial_share = (100.0 * partial_steps / procedure_steps) if procedure_steps else 0.0
    return (
        f"AN INVENTORY OF {rites} RITES, NOT A TAXONOMY. The Ritual class holds {rites} "
        f"nodes against a corpus that names considerably more, so a rank in this list is a "
        f"rank within {rites} and says nothing about Vedic ritual as a whole. Two step "
        f"layers exist and they are not interchangeable. The Samhita layer holds "
        f"{samhita_steps} numbered steps in the entire graph, all on the soma pressing, "
        f"whose morning, midday and third libations the text itself numbers. The procedural "
        f"layer holds {procedure_steps:,} steps over {rites_with_procedure} rites, read out "
        f"of Srautasutras and Grhyasutras rather than Samhita passages, and "
        f"{partial_share:.0f}% of them state a position without printing the run it falls "
        f"in -- so a procedure list is not a complete procedure. All {apparatus_edges} "
        f"apparatus edges are TIER_D curation, and a rite's 'purpose' is what a curator says "
        f"it is for, not a purpose clause quoted from a passage."
    )

def _work_label(work_key: object) -> str | None:
    """The source work's short name, read off its key.

    Read off the key and not fetched, because the 11 works these steps cite have no node in
    the graph: ``work_key`` is a foreign key to a record that was never imported. Deriving
    the label makes that visible rather than returning a null nobody can interpret.
    """
    text = str(work_key or "").strip()
    if not text:
        return None
    return text.rsplit(":", 1)[-1] or None


def _ritual_subtitle(samhita_steps: int | None, procedure_steps: int | None) -> str:
    """Say which step layer a rite actually has, rather than "one of 8 modelled rites".

    The old subtitle stated the inventory size on every row, which was wrong the moment the
    inventory changed and told the reader nothing about the rite in front of them. What
    matters per rite is which evidence layer covers it, since a rite with 227 sutra steps and
    a rite with none are both "modelled".
    """
    if samhita_steps and procedure_steps:
        return f"{samhita_steps} steps the text numbers, {procedure_steps} from the sutras"
    if samhita_steps:
        return f"{samhita_steps} steps the text itself numbers"
    if procedure_steps:
        return f"{procedure_steps} procedural steps, sutra-attested"
    return "no step layer built for this rite"


_RITUAL_LIST_QUERY: Final = """
MATCH (r:Ritual)
CALL (r) {
    OPTIONAL MATCH (r)-[:HAS_STEP]->(s)
    RETURN count(DISTINCT s) AS step_count
}
CALL (r) {
    OPTIONAL MATCH (r)-[:HAS_RITUAL_STEP]->(ps)
    RETURN count(DISTINCT ps) AS procedure_step_count
}
CALL (r) {
    OPTIONAL MATCH (r)-[:INVOKES_DEVATA]->(dv:Devata)
    RETURN count(DISTINCT dv) AS devata_count
}
CALL (r) {
    OPTIONAL MATCH (r)-[:DESCRIBED_IN]->(p:Passage)
    RETURN count(DISTINCT p) AS described_in_count
}
CALL (r) {
    OPTIONAL MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r)
    RETURN count(DISTINCT p) AS mention_count
}
RETURN r.entity_key AS id, r.display_label AS display_label,
       r.preferred_label_sa AS label_iast, r.short_description AS short_description,
       step_count, procedure_step_count, devata_count, described_in_count, mention_count
ORDER BY mention_count DESC, id
SKIP $offset LIMIT $limit
"""


#: One rite and its apparatus. The invoked deities pass the population contract too.
#:
#: Every branch is its own ``CALL`` subquery for the reason
#: ``ritual_officiants_and_purposes`` documents: as sibling OPTIONAL MATCHes the yajna row
#: alone would multiply 9 officiants by 4 purposes by 8 passages and report 288 passages
#: for 8.
_RITUAL_PROFILE_QUERY: Final = f"""
MATCH (r:Ritual {{entity_key: $id}})
CALL (r) {{
    OPTIONAL MATCH (r)-[h:HAS_STEP]->(s)
    RETURN collect({{order: h.step_order, label: s.display_label,
                     basis: h.order_basis, evidence: h.order_evidence}}) AS steps
}}
CALL (r) {{
    // Grouped by the work that records it, because step_position is an ordinal WITHIN a
    // work: 2,666 of 3,121 steps share a position with another step of the same rite, so a
    // flat ordered list would compose eight independent sequences into one procedure.
    OPTIONAL MATCH (r)-[h:HAS_RITUAL_STEP]->(s)
    WITH h, s ORDER BY h.step_position, s.display_label
    WITH h.work_key AS work_key,
         head(collect(h.evidence_source_type)) AS source_type,
         head(collect(h.veda_school)) AS veda_school,
         head(collect(h.anchor_note)) AS anchoring_basis,
         count(*) AS step_count,
         collect({{position: h.step_position, label: s.display_label,
                   text: s.text_iast, citation: h.citation,
                   stated_position: h.source_stated_position,
                   order_basis: h.order_basis,
                   order_completeness: h.order_completeness}}) AS steps
    WHERE work_key IS NOT NULL
    RETURN collect({{work_key: work_key, source_type: source_type, veda_school: veda_school,
                     step_count: step_count, anchoring_basis: anchoring_basis,
                     steps: steps[0..$step_limit]}}) AS procedure_sources
}}
CALL (r) {{
    OPTIONAL MATCH (r)-[h:HAS_RITUAL_STEP]->()
    RETURN count(h) AS procedure_step_count
}}
CALL (r) {{
    OPTIONAL MATCH (r)-[:PERFORMED_BY]->(role:RitualRole)
    RETURN collect(DISTINCT {{id: role.entity_key, label: role.display_label}}) AS roles
}}
CALL (r) {{
    OPTIONAL MATCH (r)-[:USES_OFFERING]->(off:Offering)
    RETURN collect(DISTINCT {{id: off.entity_key, label: off.display_label}}) AS offerings
}}
CALL (r) {{
    OPTIONAL MATCH (r)-[:USES_SUBSTANCE]->(sub)
    RETURN collect(DISTINCT {{id: sub.entity_key, label: sub.display_label}}) AS substances
}}
CALL (r) {{
    OPTIONAL MATCH (r)-[:USES_OBJECT]->(ob)
    RETURN collect(DISTINCT {{id: ob.entity_key, label: ob.display_label}}) AS objects
}}
CALL (r) {{
    OPTIONAL MATCH (r)-[:INVOKES_DEVATA]->(other:Devata)
    WHERE {_OTHER_IS_DEITY}
    RETURN collect(DISTINCT {{id: other.entity_key, label: other.display_label,
                              subtitle: other.structure}}) AS devatas
}}
CALL (r) {{
    OPTIONAL MATCH (r)-[:PERFORMED_FOR]->(purpose)
    RETURN collect(DISTINCT {{id: coalesce(purpose.entity_key, purpose.concept_id),
                              label: purpose.display_label}}) AS purposes
}}
CALL (r) {{
    OPTIONAL MATCH (r)-[:BROADER_THAN]->(sub:Ritual)
    RETURN collect(DISTINCT {{id: sub.entity_key, label: sub.display_label}}) AS broader_than
}}
CALL (r) {{
    OPTIONAL MATCH (r)-[d:DESCRIBED_IN]->(p:Passage)
    RETURN collect(DISTINCT {{id: p.canonical_key, label: p.canonical_citation,
                              subtitle: p.veda}})[0..$top] AS passages,
           count(DISTINCT p) AS passage_count
}}
CALL (r) {{
    OPTIONAL MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r)
    RETURN count(DISTINCT p) AS mention_count
}}
RETURN properties(r) AS props, steps, procedure_sources, procedure_step_count, roles,
       offerings, substances, objects, devatas, purposes, broader_than, passages,
       passage_count, mention_count
"""


class EntityService:
    """Every knowledge surface except passages, search and formula detail."""

    #: Row cap on any nested list inside a detail payload. Detail responses are not
    #: paginated, so their fan-out is bounded here instead.
    NESTED_LIMIT: Final = 25

    def __init__(self, repository: _Repository) -> None:
        self._repository = repository
        self._ritual_coverage_cache: str | None = None

    def _ritual_coverage(self) -> str:
        """The ritual bound, measured once per service instance.

        Memoized rather than recomputed per row: ``list_rituals`` puts it on every row and
        the figures cannot change inside one response. Cached on the instance and not at
        module level, because a module-level cache would outlive an import and keep serving
        the pre-import figures -- which is the failure this whole change exists to fix.
        """
        if self._ritual_coverage_cache is None:
            row = self._repository.run_one(_RITUAL_COVERAGE_QUERY) or {}
            self._ritual_coverage_cache = ritual_coverage_statement(
                rites=_as_int(row.get("rites")) or 0,
                samhita_steps=_as_int(row.get("samhita_steps")) or 0,
                procedure_steps=_as_int(row.get("procedure_steps")) or 0,
                partial_steps=_as_int(row.get("partial_steps")) or 0,
                rites_with_procedure=_as_int(row.get("rites_with_procedure")) or 0,
                apparatus_edges=_as_int(row.get("apparatus_edges")) or 0,
            )
        return self._ritual_coverage_cache

    # =======================================================================
    # Deities
    # =======================================================================

    def list_devatas(
        self,
        *,
        population: DeityPopulation,
        certainty: MentionCertainty,
        include_ambiguous: bool,
        structure: str | None,
        axis: str | None,
        limit: int,
        offset: int,
    ) -> Paginated[DevataSummary]:
        """The deity list, population-resolved, with all three certainty tiers per row."""
        tiers = tiers_for(certainty, include_ambiguous)
        self._validate_choice("structure", structure, KNOWN_DEITY_STRUCTURES)
        self._validate_choice("axis", axis, KNOWN_DEITY_AXES)
        parameters: dict[str, Any] = {
            **deity_structure_parameters(population),
            "structure": structure,
            "axis": axis,
            "limit": limit,
            "offset": offset,
        }
        rows = self._repository.run(_DEVATA_LIST_QUERY, **parameters)
        total_row = self._repository.run_one(_DEVATA_COUNT_QUERY, **parameters)
        total = _as_int(total_row.get("total")) if total_row else None

        items: list[DevataSummary] = []
        for row in rows:
            counts = self._certainty_counts(_tier_map(row.get("tier_json")), tiers)
            included = counts.certain_count + counts.probable_count
            if include_ambiguous:
                included += counts.ambiguous_count
            items.append(
                DevataSummary(
                    type="DEVATA",
                    id=str(row["id"]),
                    display_label=str(row.get("display_label") or row["id"]),
                    label_iast=_text(row.get("label_iast")),
                    subtitle=_text(row.get("structure")),
                    short_description=_text(row.get("short_description")),
                    structure=_text(row.get("structure")),
                    is_deity=is_deity(_text(row.get("structure"))),
                    axes=_as_list(row.get("axes")),
                    is_composite=bool(row.get("is_composite")),
                    passage_count=_as_int(row.get("attributed_total")),
                    mentions_default_total=included or None,
                    certainty=counts,
                )
            )

        caveats = [*population_caveats(population), *self._certainty_caveats(certainty, tiers)]
        if any(item.structure == "ABSTRACT" for item in items):
            caveats.append(
                CaveatView(text=ABSTRACT_HETEROGENEITY_CAVEAT, source="deity_population_contract")
            )
        return paginate(
            items,
            limit=limit,
            offset=offset,
            total=total,
            data_status=KnowledgeStatus.SUPPORTED if items else KnowledgeStatus.PARTIAL,
            caveats=caveats,
        )

    def get_devata(
        self,
        entity_id: str,
        *,
        population: DeityPopulation,
        certainty: MentionCertainty,
        include_ambiguous: bool,
    ) -> DevataProfile:
        """The flagship deity payload, with every empty dimension explained."""
        tiers = tiers_for(certainty, include_ambiguous)
        structure = self._resolve_devata(entity_id, population)
        row = self._repository.run_one(_DEVATA_NODE_QUERY, key=entity_id, tiers=sorted(tiers))
        if row is None:  # pragma: no cover - the gate already proved it exists
            raise EntityNotFoundError(f"No deity with id '{entity_id}'.")
        props: dict[str, Any] = dict(row.get("props") or {})

        mentions, counts, included_total, mention_caveats = self._mentions_by_veda(
            props, tiers, row
        )
        absent = _as_list(props.get("profile_absent_dimensions"))
        dimensions = [_dimension_status(name) for name in absent]

        co_deities, co_deity_dimension = self._co_deities(entity_id, props)
        if co_deity_dimension is not None:
            dimensions.append(co_deity_dimension)

        top_formulas = [
            EntityRef(
                type="FORMULA",
                id=str(formula["id"]),
                display_label=str(formula.get("label") or formula["id"]),
                subtitle=f"{formula.get('passages')} mantras naming this deity",
            )
            for formula in self._repository.run(
                _DEVATA_FORMULA_QUERY,
                key=entity_id,
                tiers=sorted(tiers),
                top=self.NESTED_LIMIT,
            )
            if formula.get("id")
        ]

        claims = [
            EntityRef(
                type="INTERPRETIVE_CLAIM",
                id=str(claim["id"]),
                display_label=str(claim.get("label") or claim["id"]),
            )
            for claim in (row.get("claims") or [])
            if isinstance(claim, dict) and claim.get("id")
        ]
        # Deliberately NOT a dimension_status entry. That field reports the dimensions the
        # BUILD recorded as unestablished for this deity -- the 25 nodes carrying
        # profile_absent_dimensions, plus a list the population filter emptied. An
        # unconditional row here put one on 213 of the 214, which made the field look
        # uninformative in exactly the responses where it carries the real warning.
        claims_caveat = (
            None
            if claims
            else CaveatView(
                text="The interpretive-claim layer holds 6 claims for the whole corpus and "
                "one of them concerns a deity, so an empty `interpretive_claims` is an "
                "unbuilt layer rather than an undisputed deity.",
                source="measured",
            )
        )

        subject_is_deity, subject_caveats = subject_disclosure(structure)
        caveats = [
            *subject_caveats,
            *population_caveats(population),
            *mention_caveats,
            *self._certainty_caveats(certainty, tiers),
            CaveatView(text=ATTRIBUTION_SCOPE_STATEMENT, source="measured"),
            CaveatView(text=named_query_caveat("deity_profile"), source="deity_profile"),
        ]
        if claims_caveat is not None:
            caveats.append(claims_caveat)
        if top_formulas:
            caveats.append(
                CaveatView(
                    text="`top_formulas` is co-occurrence: the graph carries no "
                    "deity-to-formula edge, so these are formulas recurring in mantras "
                    "that name this deity at the included certainty tiers, not formulas "
                    "asserted to be about it.",
                    source="measured",
                )
            )
        if structure == "ABSTRACT":
            caveats.append(
                CaveatView(text=ABSTRACT_HETEROGENEITY_CAVEAT, source="deity_population_contract")
            )

        return DevataProfile(
            id=str(props.get("entity_key") or entity_id),
            display_label=str(props.get("display_label") or entity_id),
            label_iast=_text(props.get("label_iast")),
            label_en=_text(props.get("label_en")),
            preferred_label=_text(props.get("preferred_label")),
            aliases=_as_list(props.get("aliases_iast")),
            short_description=_text(props.get("short_description")),
            structure=structure,
            is_composite=bool(props.get("is_composite")),
            component_count=_as_int(props.get("component_count")) or 0,
            axes=[
                str(axis["axis"])
                for axis in (row.get("axes") or [])
                if isinstance(axis, dict) and axis.get("axis")
            ],
            epithets=_as_list(row.get("epithets")),
            population=population,
            is_deity=subject_is_deity,
            certainty=counts,
            mentions_by_veda=mentions,
            mentions_included_total=included_total,
            mention_scope=_as_list(props.get("profile_mention_scope")),
            included_certainty=certainty,
            # Counted from HAS_DEVATA rather than read off profile_attributed_total,
            # which 184 of the 214 nodes do not carry. Null and never 0 where the
            # Anukramani apparatus does not reach this entry.
            attributed_total=_as_int(row.get("ascribed")) or None,
            attributed_per_passage=_as_int(row.get("ascribed_strict")) or None,
            attributed_inherited=(
                (_as_int(row.get("ascribed")) or 0) - (_as_int(row.get("ascribed_strict")) or 0)
            )
            or None,
            attribution_scope=_as_list(row.get("ascribed_vedas"))
            or _as_list(props.get("profile_attribution_scope")),
            top_rishis=_as_list(props.get("profile_top_rishis")),
            top_chandas=_as_list(props.get("profile_top_chandas")),
            top_concepts=_as_list(props.get("profile_top_concepts")),
            top_actions=_as_list(props.get("profile_top_actions")),
            top_requested_actions=_as_list(props.get("profile_top_requested_actions")),
            top_objects=_as_list(props.get("profile_top_objects")),
            co_deities=co_deities,
            co_mentioned=_as_list(props.get("profile_co_mentioned")),
            formula_count=_as_int(props.get("profile_formula_count")),
            top_formulas=top_formulas,
            interpretive_claims=claims,
            dimension_status=dimensions,
            data_status=KnowledgeStatus.SUPPORTED if included_total else KnowledgeStatus.PARTIAL,
            coverage=self._mention_coverage(mentions),
            caveats=caveats,
        )

    def devata_passages(
        self,
        entity_id: str,
        *,
        basis: MentionBasis,
        certainty: MentionCertainty,
        include_ambiguous: bool,
        veda: str | None,
        population: DeityPopulation,
        limit: int,
        offset: int,
    ) -> DevataPassagePage:
        """Passages related to a deity by ONE named relation, never a blend of two.

        Takes ``population`` for the same reason ``/devatas/{id}`` does, and through the
        same gate. Without it this route served the dog's Anukramani slot as a 200
        SUPPORTED page from an endpoint titled "Passages naming or ascribed to a deity",
        while ``/devatas/VG:DEVATA:SUNAH`` 404'd for the same id.
        """
        structure = self._resolve_devata(entity_id, population)
        self._validate_veda(veda)
        tiers = tiers_for(certainty, include_ambiguous)
        counts = self._mention_certainty_from_edges(entity_id, tiers)
        if basis is MentionBasis.MENTION:
            parameters: dict[str, Any] = {
                "key": entity_id,
                "tiers": sorted(tiers),
                "veda": veda,
                "limit": limit,
                "offset": offset,
            }
            rows = self._repository.run(_DEVATA_MENTION_PASSAGES, **parameters)
            total_row = self._repository.run_one(_DEVATA_MENTION_COUNT, **parameters)
            items = [self._mention_row(row) for row in rows]
            caveats = [
                CaveatView(
                    text=named_query_caveat("devata_mention_certainty_by_veda"),
                    source="devata_mention_certainty_by_veda",
                ),
                *self._certainty_caveats(certainty, tiers),
            ]
        else:
            parameters = {"key": entity_id, "veda": veda, "limit": limit, "offset": offset}
            rows = self._repository.run(_DEVATA_ASCRIPTION_PASSAGES, **parameters)
            total_row = self._repository.run_one(_DEVATA_ASCRIPTION_COUNT, **parameters)
            items = [self._ascription_row(row) for row in rows]
            caveats = [CaveatView(text=ATTRIBUTION_SCOPE_STATEMENT, source="measured")]

        if veda == "SV" or any(item.veda == "SV" for item in items):
            caveats.append(CaveatView(text=SAMAVEDA_SCOPE_STATEMENT, source="measured"))
        if basis is MentionBasis.ASCRIPTION and veda in {"SV", "YV", "AV"}:
            caveats.append(
                CaveatView(
                    text=f"basis=ascription with veda={veda} is empty by construction: the "
                    "Anukramani deity apparatus exists for the Rigveda only. Use "
                    "basis=mention to ask whether the deity is named in that corpus.",
                    source="measured",
                )
            )
        subject_is_deity, subject_caveats = subject_disclosure(structure)
        caveats[:0] = subject_caveats
        total = _as_int(total_row.get("total")) if total_row else None
        page = paginate(
            items,
            limit=limit,
            offset=offset,
            total=total,
            data_status=KnowledgeStatus.SUPPORTED if items else KnowledgeStatus.PARTIAL,
            caveats=caveats,
        )
        return DevataPassagePage(
            items=page.items,
            pagination=page.pagination,
            data_status=page.data_status,
            caveats=page.caveats,
            certainty=counts,
            basis=basis,
            subject_structure=structure,
            subject_is_deity=subject_is_deity,
            # Never 0: a relation that does not reach this subject at all is a null with a
            # caveat, not a zero a client can chart.
            matched_total=total or None,
        )

    def devata_network(self, entity_id: str, *, population: DeityPopulation) -> DevataNetwork:
        """The neighbourhood, with the SUBJECT and every deity-valued edge both filtered.

        The subject gate is the fix for the defect that let the dog reach Indra and Agni
        through ``shared_rishi_deities``: the edge filter was applied and the subject was
        not, so the endpoint refused a non-deity as a neighbour while serving one as the
        thing being asked about.
        """
        structure = self._resolve_devata(entity_id, population)
        subject_is_deity, subject_caveats = subject_disclosure(structure)
        parameters = {
            **deity_structure_parameters(population),
            "key": entity_id,
            "top": self.NESTED_LIMIT,
        }
        row = self._repository.run_one(_DEVATA_NETWORK_QUERY, **parameters)
        if row is None:  # pragma: no cover - the gate already proved it exists
            raise EntityNotFoundError(f"No deity with id '{entity_id}'.")

        edges: list[DevataNetworkEdge] = []
        edge_caveats: set[str] = set()
        for entry in row.get("co_occurring") or []:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            caveat = entry.get("evidence_caveat")
            if isinstance(caveat, str) and caveat:
                edge_caveats.add(caveat)
            edges.append(
                DevataNetworkEdge(
                    other=EntityRef(
                        type="DEVATA",
                        id=str(entry["id"]),
                        display_label=str(entry.get("label") or entry["id"]),
                        subtitle=_truncate(entry.get("subtitle")),
                    ),
                    lift=_as_float(entry.get("lift")),
                    passage_count=_as_int(entry.get("passage_count")),
                    rv_passage_count=_as_int(entry.get("rv")),
                    non_rv_passage_count=_as_int(entry.get("non_rv")),
                    per_veda_counts=_int_map(parse_json_property(entry.get("per_veda"))),
                    example_citations=_as_list(entry.get("examples")),
                    quality_tier=entry.get("tier"),
                )
            )
        edges.sort(key=lambda e: (-(e.lift or 0.0), e.other.id))

        shared = self._repository.run(_SHARED_RISHI_DEITIES_QUERY, **parameters)
        shared_refs = [
            EntityRef(
                type="DEVATA",
                id=str(item["id"]),
                display_label=str(item.get("label") or item["id"]),
                subtitle=f"{item.get('shared_mantras')} mantras by seers in common",
            )
            for item in shared
            if item.get("id")
        ]

        dimensions: list[DimensionStatus] = []
        if not edges:
            dimensions.append(
                DimensionStatus(
                    dimension="co_occurring",
                    status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
                    note="The co-occurrence layer carries 306 edges over the whole pantheon "
                    "and reached none for this deity at the lift threshold the build used. "
                    "This is not a claim that it is never named beside another god.",
                )
            )
        if not shared_refs:
            dimensions.append(
                DimensionStatus(
                    dimension="shared_rishi_deities",
                    status=KnowledgeStatus.NOT_BUILT,
                    note="The seer bridge runs over HAS_DEVATA and HAS_RISHI together, and "
                    "HAS_DEVATA is Rigvedic. A deity with no Anukramani ascription has no "
                    "bridge to walk, whatever the other three corpora say about it.",
                )
            )

        caveats = [
            *subject_caveats,
            *population_caveats(population),
            CaveatView(
                text="`shared_rishi_deities` is a co-attribution figure over the Anukramani "
                "apparatus, not a claim about who composed what: HAS_DEVATA is Rigvedic and "
                "95.5% of HAS_RISHI is a sukta label projected onto its mantras. The bridge "
                "also runs only through seers -- 113 of the 729 :Rishi nodes are not seers "
                "but the beings a hymn addresses, and routing through those would connect "
                "two deities by way of a third.",
                source="measured",
            ),
        ]
        caveats.extend(
            CaveatView(text=text, source="graph:CO_OCCURS_WITH.evidence_caveat")
            for text in sorted(edge_caveats)
        )
        if any((edge.non_rv_passage_count or 0) > 0 for edge in edges):
            caveats.append(CaveatView(text=SAMAVEDA_SCOPE_STATEMENT, source="measured"))

        return DevataNetwork(
            id=entity_id,
            display_label=str(row.get("display_label") or entity_id),
            subject_structure=structure,
            subject_is_deity=subject_is_deity,
            co_occurring=edges,
            components=_refs(row.get("components")),
            member_of=_refs(row.get("member_of")),
            axes=[
                EntityRef(
                    type="DEITY_AXIS",
                    id=str(a["id"]),
                    display_label=str(a.get("label") or a["id"]),
                    subtitle=a.get("subtitle"),
                )
                for a in (row.get("axes") or [])
                if isinstance(a, dict) and a.get("id")
            ],
            associated_entities=_refs(row.get("associated")),
            shared_rishi_deities=shared_refs,
            dimension_status=dimensions,
            data_status=KnowledgeStatus.SUPPORTED if edges else KnowledgeStatus.PARTIAL,
            caveats=caveats,
        )

    # -- deity helpers ----------------------------------------------------------

    def _resolve_devata(self, entity_id: str, population: DeityPopulation) -> str | None:
        """THE deity gate. Every deity route passes through it; none can opt out.

        Returns the subject's ``structure``, and raises otherwise, so a caller gets the
        population decision and the structure from one call and cannot take one without
        the other. It is a chokepoint rather than a check because the alternative was
        measured: the population contract lived in ``get_devata`` alone, and the network
        and passage routes each forgot it, so ``/devatas/VG:DEVATA:SUNAH/network`` served
        the dog as ``type=DEVATA`` under a caveat reading "This response excludes all 30"
        while being one of the 30 -- and ``/devatas/VG:DEVATA:SUNAH`` 404'd for the same
        id in the same API. Requiring ``population`` here means a route cannot forget it
        without failing to type-check.
        """
        row = self._repository.run_one(
            "MATCH (dv:Devata {entity_key: $key}) RETURN dv.structure AS structure",
            key=entity_id,
        )
        if row is None:
            raise EntityNotFoundError(
                f"No deity with id '{entity_id}'.",
                hint="GET /api/v1/devatas lists them. Ids look like VG:DEVATA:INDRAH.",
            )
        structure = _text(row.get("structure"))
        if population is DeityPopulation.DEITIES and not is_deity(structure):
            raise EntityNotFoundError(
                f"'{entity_id}' is an Anukramani devata-slot ascription, not a deity "
                f"(structure={structure!r}).",
                hint="Ask again with population=all_ascriptions to read it as what it is. "
                + DEITY_SURFACE_REDIRECT,
            )
        return structure

    def _certainty_counts(
        self, tier_map: dict[str, dict[str, int]], tiers: frozenset[str]
    ) -> ReferentCertaintyCounts:
        return ReferentCertaintyCounts(
            certain_count=sum(tier_map.get(CERTAIN, {}).values()),
            probable_count=sum(tier_map.get(PROBABLE, {}).values()),
            ambiguous_count=sum(tier_map.get(AMBIGUOUS, {}).values()),
            included_tiers=sorted(tiers),
        )

    def _mentions_by_veda(
        self, props: dict[str, Any], tiers: frozenset[str], row: dict[str, Any]
    ) -> tuple[list[VedaMentionCount], ReferentCertaintyCounts, int | None, list[CaveatView]]:
        """All four corpora, always, each with the reason its number is what it is.

        **Counted from the edges, not from the materialisation.**
        ``profile_mentions_by_veda_certainty`` exists on only 30 of the 214 ``:Devata``
        nodes, and treating it as the source of truth made this endpoint report ``null``
        with ``INSUFFICIENT_EVIDENCE`` for all four corpora on 184 of them -- including
        Sarasvati, who has 213 mention edges, and Prthivi, who has 712. Both were counted
        correctly the whole time by ``/insights/devatas/{id}``, which reads the edges. Two
        endpoints of one API disagreeing about one deity is the worst failure available
        here, and it came from one number having two sources.

        ``INSUFFICIENT_EVIDENCE`` is also the wrong word for it: it means "evidence exists
        and cannot support the claim", and an unmaterialised property is not that.

        The counting shape matches ``_DEVATA_INSIGHT_QUERY`` deliberately --
        ``count(DISTINCT p)`` per Veda over tier-filtered edges -- so the two agree by
        construction rather than by coincidence.

        Four rows even where three are null, because a payload carrying only the corpora
        with a positive count lets a reader infer a zero for the rest. The status
        distinguishes them: SUPPORTED where an included tier has evidence,
        INSUFFICIENT_EVIDENCE where the tier filter removed evidence the deity does have,
        NOT_BUILT where the mention layer does not reach it at all.
        """
        tier_map = _grid_to_tier_map(row.get("mention_grid"))
        verdicts = _verdicts(props.get("profile_mention_verdict_by_veda"))
        live_by_veda = _pairs_to_counts(row.get("named_by_veda"))
        rows: list[VedaMentionCount] = []
        included_total = 0
        filtered_out: list[str] = []
        unreached: list[str] = []

        for veda in VEDA_ORDER:
            per_tier = {
                tier: tier_map.get(tier, {}).get(veda, 0)
                for tier in (
                    CERTAIN,
                    PROBABLE,
                    AMBIGUOUS,
                )
            }
            # The per-Veda figure is the tier-filtered DISTINCT-passage count straight
            # from the graph, so it matches the insight endpoint row for row. The grid is
            # used only to decide WHY a corpus is empty and to report the three-way split.
            included = live_by_veda.get(veda, 0)
            everything = sum(per_tier.values())
            if included:
                status = KnowledgeStatus.SUPPORTED
                count: int | None = included
            elif everything:
                status = KnowledgeStatus.INSUFFICIENT_EVIDENCE
                count = None
                filtered_out.append(veda)
            elif verdicts:
                status = status_for_verdict(verdicts.get(veda))
                count = None
            else:
                # No materialised verdict and no edge at any tier: the theonym mention
                # layer does not reach this ascription at all. That is NOT_BUILT, a
                # statement about the layer, and never INSUFFICIENT_EVIDENCE, which would
                # claim evidence exists.
                status = KnowledgeStatus.NOT_BUILT
                count = None
                unreached.append(veda)
            included_total += included
            rows.append(
                VedaMentionCount(
                    veda=veda,
                    count=count,
                    status=status,
                    certainty=ReferentCertaintyCounts(
                        certain_count=per_tier[CERTAIN],
                        probable_count=per_tier[PROBABLE],
                        ambiguous_count=per_tier[AMBIGUOUS],
                        included_tiers=sorted(tiers),
                    ),
                )
            )

        caveats: list[CaveatView] = []
        if filtered_out:
            caveats.append(
                CaveatView(
                    text=(
                        "The certainty filter emptied "
                        + ", ".join(filtered_out)
                        + ": those corpora have mentions of this deity at tiers this "
                        "request excluded, so their count is null with "
                        "INSUFFICIENT_EVIDENCE and is NOT zero. Read each row's "
                        "`certainty` block for the three tiers as measured."
                    ),
                    source="measured",
                )
            )
        if len(unreached) == len(VEDA_ORDER):
            caveats.append(
                CaveatView(
                    text=(
                        "THIS ENTRY CARRIES NO MENTION LAYER AT ALL. It is an Anukramani "
                        "devata-slot ascription with no theonym in the mention registry, "
                        "so every corpus reports NOT_BUILT: the four-Veda mention layer "
                        "does not reach it, which is a statement about the layer and not "
                        "about the text. Only 42 of the 214 devata-slot entries carry "
                        "mention edges at all. Its Anukramani ascription figures are still "
                        "real -- read `attributed_total`."
                    ),
                    source="measured",
                )
            )
        elif unreached:
            caveats.append(
                CaveatView(
                    text=(
                        "NOT_BUILT in "
                        + ", ".join(unreached)
                        + ": the mention layer records no edge for this deity in those "
                        "corpora at any certainty tier. That is weaker than absence from "
                        "the text -- the layer's measured recall is 0.8857 -- and it is "
                        "not a zero."
                    ),
                    source="measured",
                )
            )
        if any(row.veda == "SV" and row.count for row in rows) or "SV" in filtered_out:
            caveats.append(CaveatView(text=SAMAVEDA_SCOPE_STATEMENT, source="measured"))
        return (
            rows,
            self._certainty_counts(tier_map, tiers),
            included_total or None,
            caveats,
        )

    def _mention_certainty_from_edges(
        self, entity_id: str, tiers: frozenset[str]
    ) -> ReferentCertaintyCounts:
        """The three-tier split over ALL of a deity's mention edges.

        From the edges for the same reason the profile is: the materialisation covers 30 of
        214 nodes, and a page reporting only its filtered rows would let a client read 421
        Soma passages without ever seeing the 1,091 ambiguous mentions the filter removed.
        """
        rows = self._repository.run(_DEVATA_CERTAINTY_QUERY, key=entity_id)
        counts = {
            str(item["certainty"]): _as_int(item.get("edges")) or 0
            for item in rows
            if item.get("certainty")
        }
        return ReferentCertaintyCounts(
            certain_count=counts.get(CERTAIN, 0),
            probable_count=counts.get(PROBABLE, 0),
            ambiguous_count=counts.get(AMBIGUOUS, 0),
            included_tiers=sorted(tiers),
        )

    def _mention_coverage(self, mentions: list[VedaMentionCount]) -> CoverageView:
        return CoverageView(
            vedas_in_scope=[m.veda for m in mentions if m.count],
            vedas_not_covered=[m.veda for m in mentions if not m.count],
            measured={m.veda: m.count for m in mentions if m.count is not None},
            denominator=dict(CORPUS_MANTRAS),
        )

    def _certainty_caveats(
        self, certainty: MentionCertainty, tiers: frozenset[str]
    ) -> list[CaveatView]:
        caveats = [
            CaveatView(
                text=(
                    "Deity counts here include "
                    + " + ".join(sorted(tiers))
                    + ". The product default is DEITY_CERTAIN + DEITY_PROBABLE, measured at "
                    "0.9742 precision against the gold sample versus 0.6142 for what "
                    "DEITY_AMBIGUOUS holds; all three tiers are reported regardless, "
                    "because a deity whose name is an ordinary noun is flattered or "
                    "penalised by that choice."
                ),
                source="measured",
            )
        ]
        if certainty is MentionCertainty.STRICT:
            caveats.append(CaveatView(text=STRICT_MODE_STATEMENT, source="measured"))
        if AMBIGUOUS in tiers:
            caveats.append(
                CaveatView(
                    text="DEITY_AMBIGUOUS is INCLUDED in these totals. That bucket is "
                    "measured at 0.6142 precision: agni is also fire, soma also the "
                    "pressed drink and vac also speech, and on the gold sample every "
                    "asserted mention of VG:DEVATA:VAK is the common noun. Use these "
                    "figures for candidate generation, not as fact.",
                    source="measured",
                )
            )
        return caveats

    def _co_deities(
        self, entity_id: str, props: dict[str, Any]
    ) -> tuple[list[EntityRef], DimensionStatus | None]:
        """Defect A containment, with the dropped rows counted rather than swallowed."""
        profile_labels = _as_list(props.get("profile_co_devatas"))
        if not profile_labels:
            return [], None

        rows = self._repository.run(_CO_DEITY_QUERY, key=entity_id)
        resolved = [row for row in rows if row.get("entity_key")]
        unresolved = [str(row["profile_label"]) for row in rows if not row.get("entity_key")]
        deity_rows = filter_co_deity_labels(resolved)
        dropped = [
            f"{row.get('display_label')} ({row.get('structure')})"
            for row in resolved
            if not is_deity(_text(row.get("structure")))
        ]

        refs = [
            EntityRef(
                type="DEVATA",
                id=str(row["entity_key"]),
                display_label=str(row.get("display_label") or row["entity_key"]),
                subtitle=_truncate(_text(row.get("short_description"))),
            )
            for row in deity_rows
        ]
        if refs and not dropped and not unresolved:
            return refs, None

        reasons: list[str] = []
        if dropped:
            reasons.append(
                f"{len(dropped)} resolved to a non-deity Anukramani ascription "
                f"({', '.join(sorted(dropped))})"
            )
        if unresolved:
            reasons.append(
                f"{len(unresolved)} matched no Devata node at all ({', '.join(sorted(unresolved))})"
            )
        status = KnowledgeStatus.PARTIAL if refs else KnowledgeStatus.INSUFFICIENT_EVIDENCE
        return refs, DimensionStatus(
            dimension="co_deities",
            status=status,
            note=(
                f"The frozen `profile_co_devatas` property listed {len(profile_labels)} "
                f"display label(s); {'; '.join(reasons)}. Those rows are dropped rather "
                "than shown as deities, so this list is "
                + ("shorter than the stored property" if refs else "empty")
                + ". The measured co-occurrence layer is at "
                "GET /api/v1/devatas/{id}/network."
            ),
        )

    def _mention_row(self, row: dict[str, Any]) -> DevataPassageRef:
        return DevataPassageRef(
            passage_id=str(row["passage_id"]),
            citation=_text(row.get("citation")),
            veda=_text(row.get("veda")),
            basis=MentionBasis.MENTION,
            referent_certainty=_text(row.get("referent_certainty")),
            occurrences=_as_int(row.get("occurrences")),
            matched_forms=_as_list(row.get("matched_forms")),
            evidence=EvidenceView(
                method=_text(row.get("method")),
                tier=_text(row.get("quality_tier")),
                # Derived from attribution_precision, NOT cast from the graph property of
                # the same name: MENTIONS_DEVATA carries evidence_basis='SANSKRIT' on all
                # 17,165 edges, which is a surface and not a derivation, and casting it
                # would report every mention in the corpus as UNKNOWN.
                evidence_basis=basis_from_attribution_precision(
                    _text(row.get("attribution_precision"))
                ),
                surface=evidence_surface(row.get("evidence_basis")),
                attribution_precision=_precision(_text(row.get("attribution_precision"))),
                derivation=row.get("extraction_path") or row.get("referent_basis"),
            ),
        )

    def _ascription_row(self, row: dict[str, Any]) -> DevataPassageRef:
        return DevataPassageRef(
            passage_id=str(row["passage_id"]),
            citation=_text(row.get("citation")),
            veda=_text(row.get("veda")),
            basis=MentionBasis.ASCRIPTION,
            attribution_precision=_text(row.get("attribution_precision")),
            evidence=EvidenceView(
                tier=_text(row.get("quality_tier")),
                evidence_basis=basis_from_attribution_precision(
                    _text(row.get("attribution_precision"))
                ),
                surface=evidence_surface(row.get("evidence_basis")),
                attribution_precision=_precision(_text(row.get("attribution_precision"))),
                # confidence is a pipeline constant on this predicate, so it is not
                # returned as if it varied -- see the confidence_is_a_pipeline_constant
                # query in the frozen catalogue.
                confidence=None,
                derivation=row.get("provenance_class") or row.get("scope_origin"),
            ),
        )

    # =======================================================================
    # The generic entity surface
    # =======================================================================

    def type_inventory(self) -> EntityTypeInventory:
        """Every queryable type with its live count.

        Exists because ``validated_label``'s hint promises it on every unknown-type 400. A
        hint pointing at a route that does not exist is worse than no hint.
        """
        counts = {
            str(row["label"]): int(row["c"])
            for row in self._repository.run(
                "MATCH (n) WHERE NOT n:Internal UNWIND labels(n) AS label "
                "RETURN label, count(*) AS c"
            )
            if row.get("label") is not None
        }
        return EntityTypeInventory(
            types=[
                EntityTypeInfo(
                    slug=spec.slug,
                    type=spec.type_name,
                    count=counts.get(spec.label),
                    detail_available=True,
                    note=spec.detail_note,
                )
                for spec in sorted(ENTITY_TYPES.values(), key=lambda s: s.slug)
            ],
            caveats=[
                CaveatView(text=DEITY_SURFACE_REDIRECT, source="deity_population_contract"),
                CaveatView(
                    text="These counts are node counts in the frozen graph, not measures of "
                    "how much of the corpus each type reaches. A type with 8 nodes is a "
                    "curated selection and not an inventory of what the Samhitas name -- "
                    "open the type to read its own coverage statement.",
                    source="measured",
                ),
            ],
        )

    def resolve_type(self, slug: str) -> EntityTypeSpec:
        """The registry entry for a URL slug, or a 400 naming what is available.

        An unknown type is never an empty 200: "no such type" and "that type is empty" are
        different answers. A deity slug is refused with a pointer at the deity surface,
        because serving a deity here would be serving it with no population contract --
        which is the surface that returns 22 human patrons and a dog.
        """
        normalised = slug.strip().lower()
        if normalised in DEITY_SLUGS:
            raise UnknownEntityTypeError(DEITY_SURFACE_REDIRECT, hint="GET /api/v1/devatas")
        spec = ENTITY_TYPES.get(normalised)
        if spec is None:
            raise UnknownEntityTypeError(
                f"'{slug}' is not a queryable knowledge type.",
                hint="Available types: " + ", ".join(sorted(ENTITY_TYPES)) + ". "
                "GET /api/v1/entities lists them with counts.",
            )
        return spec

    def list_entities(
        self,
        slug: str,
        *,
        condition_kind: ConditionKindFilter | None,
        name: str | None,
        limit: int,
        offset: int,
    ) -> Paginated[EntityListRow]:
        """One page of one knowledge type."""
        spec = self.resolve_type(slug)
        kind = self._condition_kind_value(spec, condition_kind)
        parameters: dict[str, Any] = {
            "condition_kind": kind,
            "name": name.strip().lower() if name else None,
            "limit": limit,
            "offset": offset,
        }
        if spec.label == "Condition":
            rows = self._repository.run(_CONDITION_LIST_QUERY, **parameters)
            items: list[EntityListRow] = [
                ConditionSummary(
                    type=spec.type_name,
                    id=str(row["id"]),
                    display_label=str(row.get("display_label") or row["id"]),
                    label_iast=_text(row.get("label_iast")),
                    subtitle=_text(row.get("condition_kind")),
                    short_description=_text(row.get("short_description")),
                    kind=_text(row.get("condition_kind")),
                    passage_count=_as_int(row.get("passage_count")) or None,
                    treated_by_count=_as_int(row.get("treated")) or None,
                    protected_from_count=_as_int(row.get("protected")) or None,
                )
                for row in rows
            ]
        else:
            rows = self._repository.run(_entity_list_query(spec), **parameters)
            items = [
                EntityListRow(
                    type=result_type_for_labels(row.get("node_labels")).value,
                    id=str(row["id"]),
                    display_label=str(row.get("display_label") or row["id"]),
                    label_iast=_text(row.get("label_iast")),
                    subtitle=_row_subtitle(row),
                    short_description=_text(row.get("short_description")),
                    # `or None`: a measured zero is returned as null, because a bare 0 in a
                    # field named passage_count is the shape this product exists to refuse.
                    # The response caveat says what a null means.
                    passage_count=_as_int(row.get("passage_count")) or None,
                    is_seer=_as_bool(row.get("is_seer")),
                    non_seer_kind=_text(row.get("non_seer_kind")),
                )
                for row in rows
                if row.get("id")
            ]
        total_row = self._repository.run_one(_entity_count_query(spec), **parameters)
        return paginate(
            items,
            limit=limit,
            offset=offset,
            total=_as_int(total_row.get("total")) if total_row else None,
            data_status=KnowledgeStatus.SUPPORTED if items else KnowledgeStatus.PARTIAL,
            caveats=self._type_caveats(spec, kind, bool(items)),
        )

    def get_entity(self, slug: str, entity_id: str) -> EntityProfile:
        """One knowledge object, with the seer block attached where the type is RISHI."""
        spec = self.resolve_type(slug)
        row = self._repository.run_one(
            _entity_node_query(spec), id=entity_id, top=self.NESTED_LIMIT
        )
        if row is None:
            raise EntityNotFoundError(
                f"No {spec.slug} with id '{entity_id}'.",
                hint=f"GET /api/v1/entities/{spec.slug} lists them.",
            )
        props: dict[str, Any] = dict(row.get("props") or {})
        by_veda = {
            str(item["veda"]): int(item["passages"])
            for item in self._repository.run(_entity_passages_by_veda_query(spec), id=entity_id)
            if item.get("veda") is not None
        }

        co_mentioned = [
            EntityRef(
                type=result_type_for_labels(item.get("labels")).value,
                id=str(item["id"]),
                display_label=str(item.get("label") or item["id"]),
                subtitle=f"named in {item.get('passages')} of the same mantras",
            )
            for item in self._repository.run(
                _entity_co_mention_query(spec), id=entity_id, top=self.NESTED_LIMIT
            )
            if item.get("id")
        ]

        dimensions: list[DimensionStatus] = []
        centrality = self._centrality(props)
        if centrality is not None and centrality.bridging_status is not KnowledgeStatus.SUPPORTED:
            dimensions.append(
                DimensionStatus(
                    dimension="centrality.bridging",
                    status=centrality.bridging_status,
                    note=centrality.bridging_note
                    or "Bridge centrality is not computable in this graph and is not "
                    "reported as a zero.",
                )
            )

        seer = None
        if spec.label == "Rishi":
            seer = self._rishi_profile(entity_id)

        caveats = self._type_caveats(spec, _text(props.get("condition_kind")), True)
        if not by_veda:
            dimensions.append(
                DimensionStatus(
                    dimension="passages_by_veda",
                    status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
                    note="No passage in the graph reaches this object through the lexical, "
                    "conceptual or ritual predicates this surface counts. It is curated "
                    "and unattested rather than absent from the corpus.",
                )
            )
        if "SV" in by_veda:
            caveats.append(CaveatView(text=SAMAVEDA_SCOPE_STATEMENT, source="measured"))
        if co_mentioned:
            caveats.append(
                CaveatView(
                    text="`co_mentioned` is CO-OCCURRENCE WITHIN A MANTRA and nothing more. "
                    "It carries no causal, prescriptive or pharmacological claim: a plant "
                    "named beside an affliction is named beside it, and apamarga is named "
                    "against sorcery rather than against a cough. `neighbours` holds the "
                    "curated edges, which are a different strength of claim; the two are "
                    "separate fields so they cannot be read as one.",
                    source="measured",
                )
            )
        if not co_mentioned and not _refs(row.get("neighbours")):
            dimensions.append(
                DimensionStatus(
                    dimension="co_mentioned",
                    status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
                    note="No mantra reaching this object also names another domain entity, "
                    "so no neighbourhood could be measured. The mention layer's recall is "
                    "0.8857, so this is a lower bound and not an isolated object.",
                )
            )

        return EntityProfile(
            type=result_type_for_labels(row.get("node_labels")).value,
            id=str(props.get(spec.id_property) or props.get("entity_key") or entity_id),
            display_label=str(props.get("display_label") or entity_id),
            label_iast=_text(props.get("label_iast")) or _text(props.get("preferred_label")),
            preferred_label_en=_text(props.get("preferred_label_en")),
            preferred_label_sa=_text(props.get("preferred_label_sa")),
            aliases_en=_as_list(props.get("aliases_en")),
            aliases_sa=_as_list(props.get("aliases_sa")),
            definition=_text(props.get("definition")),
            short_description=_text(props.get("short_description")),
            condition_kind=_text(props.get("condition_kind")),
            centrality=centrality,
            recall=self._recall(props),
            passages_by_veda=self._counted_by_veda(by_veda),
            passage_count=_as_int(row.get("passage_count")) or None,
            neighbours=_refs(row.get("neighbours")),
            co_mentioned=co_mentioned,
            seer=seer,
            dimension_status=dimensions,
            data_status=KnowledgeStatus.SUPPORTED if by_veda else KnowledgeStatus.PARTIAL,
            coverage=CoverageView(
                vedas_in_scope=[v for v in VEDA_ORDER if v in by_veda],
                vedas_not_covered=[v for v in VEDA_ORDER if v not in by_veda],
                measured=by_veda,
                denominator=dict(CORPUS_MANTRAS),
            ),
            caveats=caveats,
        )

    # -- generic helpers --------------------------------------------------------

    def _condition_kind_value(
        self, spec: EntityTypeSpec, condition_kind: ConditionKindFilter | None
    ) -> str | None:
        """Resolve the condition filter, defaulting an affliction question to afflictions.

        The default is AFFLICTION and it is the whole point of the parameter: of the 718
        MENTIONS_ENTITY edges reaching a Condition, 314 reach a THREAT and 88 a
        PATHOGEN_OR_CAUSE, so an unfiltered disease list ranks rakshas, sorcery, curses,
        worms and poison as diseases. A caller who wants those asks for them by name.
        """
        if spec.label != "Condition":
            if condition_kind is not None:
                raise BadRequestError(
                    f"kind is only meaningful for the condition type, not {spec.slug}.",
                    hint="Drop the kind parameter, or ask GET /api/v1/entities/condition.",
                )
            return None
        if condition_kind is None:
            return ConditionKindFilter.AFFLICTION.value
        if condition_kind is ConditionKindFilter.ANY:
            return None
        return condition_kind.value

    def _type_caveats(
        self, spec: EntityTypeSpec, condition_kind: str | None, non_empty: bool
    ) -> list[CaveatView]:
        caveats: list[CaveatView] = []
        if spec.label == "Condition":
            if condition_kind == ConditionKindFilter.AFFLICTION.value:
                caveats.append(
                    CaveatView(
                        text="Filtered to condition_kind=AFFLICTION: 26 of the 36 Condition "
                        "nodes. The 8 THREAT entries (demons, sorcery, curses) and 2 "
                        "PATHOGEN_OR_CAUSE entries (worms, poison) are excluded, because a "
                        "disease list that returns a demon is a category error and not a "
                        "rounding error. Ask kind=ANY to see all three, and read the `kind` "
                        "on every row.",
                        source="measured",
                    )
                )
            elif condition_kind is None:
                caveats.append(
                    CaveatView(
                        text="kind=ANY: these rows mix AFFLICTION (26), THREAT (8) and "
                        "PATHOGEN_OR_CAUSE (2). Read `kind` on each row before calling any "
                        "of them a disease.",
                        source="measured",
                    )
                )
            caveats.append(
                CaveatView(
                    text=named_query_caveat("conditions_treated"),
                    source="conditions_treated",
                )
            )
        if spec.label == "Ritual":
            caveats.append(CaveatView(text=self._ritual_coverage(), source="measured"))
        if spec.label == "Rishi":
            caveats.append(
                CaveatView(
                    text="113 of the 729 :Rishi nodes are NOT seers: the Anukramani's rishi "
                    "slot also holds the being a hymn addresses, so it contains 58 deities, "
                    "21 abstractions, 13 mythic beings, 11 deity groups, 5 plants or "
                    "animals, 3 collectives and 2 objects. Every row carries `is_seer` and "
                    "`non_seer_kind`; a false there must not be rendered as a seer, and it "
                    "is not a reason to render the node as a deity either.",
                    source="measured",
                )
            )
        if spec.detail_note:
            caveats.append(CaveatView(text=spec.detail_note, source="measured"))
        caveats.append(
            CaveatView(
                text="`passage_count` counts DISTINCT passages reaching the object through "
                "the lexical, conceptual and ritual predicates this surface counts, and is "
                "the same figure the detail view reports. It is NULL, never 0, where no "
                "passage reaches it: the mention layer's measured recall is 0.8857, so a "
                "null is a lower bound and not an assertion that the corpus is silent.",
                source="measured",
            )
        )
        if not non_empty:
            caveats.append(
                CaveatView(
                    text=f"No {spec.slug} matched these filters. The type exists and has "
                    "nodes in the graph, so this is a filter result rather than an absent "
                    "type -- an unknown type would have been a 400.",
                    source="measured",
                )
            )
        return caveats

    def _centrality(self, props: dict[str, Any]) -> CentralityView | None:
        if props.get("centrality_degree") is None and props.get("centrality_share") is None:
            return None
        bridging_raw = props.get("centrality_bridging")
        bridging = _as_float(bridging_raw)
        if bridging is not None:
            status = KnowledgeStatus.SUPPORTED
            note = None
        else:
            status = KnowledgeStatus.NOT_BUILT
            note = str(bridging_raw) if isinstance(bridging_raw, str) else None
        return CentralityView(
            degree=_as_float(props.get("centrality_degree")),
            share=_as_float(props.get("centrality_share")),
            measure=_text(props.get("centrality_measure")),
            layer=_text(props.get("centrality_layer")),
            bridging=bridging,
            bridging_status=status,
            bridging_note=note,
        )

    def _recall(self, props: dict[str, Any]) -> RecallView | None:
        keys = (
            "recall_is_measured",
            "recall_basis",
            "strict_recall_against_locus",
            "mention_edges_total",
            "alias_purity",
        )
        if not any(props.get(key) is not None for key in keys):
            return None
        return RecallView(
            is_measured=bool(props.get("recall_is_measured")),
            basis=_text(props.get("recall_basis")),
            strict_recall_against_locus=_as_float(props.get("strict_recall_against_locus")),
            locus_veda=_text(props.get("locus_veda")),
            locus_book=_text(props.get("locus_book")),
            locus_tagged_passages=_as_int(props.get("locus_tagged_passages")),
            locus_book_passages=_as_int(props.get("locus_book_passages")),
            mention_edges_total=_as_int(props.get("mention_edges_total")),
            mention_edges_own_alias=_as_int(props.get("mention_edges_own_alias")),
            mention_edges_foreign_alias=_as_int(props.get("mention_edges_foreign_alias")),
            alias_purity=_as_float(props.get("alias_purity")),
            alias_purity_basis=_text(props.get("alias_purity_basis")),
        )

    def _counted_by_veda(self, by_veda: dict[str, int]) -> CountedByVeda:
        return CountedByVeda(
            rv=by_veda.get("RV"),
            sv=by_veda.get("SV"),
            yv=by_veda.get("YV"),
            av=by_veda.get("AV"),
            status=KnowledgeStatus.SUPPORTED if by_veda else KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            note="A null is not a zero: it means this object was not reached in that "
            "corpus by the lexical, conceptual or ritual predicates counted here. The "
            "mention layer's measured recall is 0.8857, so even a reached corpus is a "
            "lower bound.",
        )

    # =======================================================================
    # Seers
    # =======================================================================

    def _rishi_profile(self, entity_id: str) -> RishiProfile:
        """The seer block, with strict and inherited attribution kept apart."""
        row = self._repository.run_one(_RISHI_PROFILE_QUERY, id=entity_id)
        if row is None:  # pragma: no cover - get_entity already found the node
            raise EntityNotFoundError(f"No rishi with id '{entity_id}'.")
        props: dict[str, Any] = dict(row.get("props") or {})

        source_stated = 0
        inherited = 0
        per_veda: dict[str, dict[str, int]] = {}
        for edge in row.get("seer_edges") or []:
            if not isinstance(edge, dict) or edge.get("veda") is None:
                continue
            veda = str(edge["veda"])
            bucket = per_veda.setdefault(veda, {"strict": 0, "inherited": 0})
            if edge.get("precision") == "PER_PASSAGE":
                source_stated += 1
                bucket["strict"] += 1
            else:
                inherited += 1
                bucket["inherited"] += 1

        passages_by_veda = [
            VedaMentionCount(
                veda=veda,
                count=(
                    per_veda[veda]["strict"] + per_veda[veda]["inherited"]
                    if veda in per_veda
                    else None
                ),
                status=(
                    KnowledgeStatus.SUPPORTED
                    if veda in per_veda
                    else KnowledgeStatus.NOT_BUILT
                    if veda == "SV"
                    else KnowledgeStatus.INSUFFICIENT_EVIDENCE
                ),
            )
            for veda in VEDA_ORDER
        ]

        deities = [
            AttributedRef(
                type="DEVATA",
                id=str(item["id"]),
                display_label=str(item.get("label") or item["id"]),
                subtitle=item.get("structure"),
                attribution_precision=_precision_for_strict(item.get("strict")).value,
                evidence_basis=basis_from_attribution_precision(
                    _precision_for_strict(item.get("strict")).value
                ),
                passage_count=_as_int(item.get("passages")),
            )
            for item in self._repository.run(
                _RISHI_DEITIES_QUERY,
                id=entity_id,
                top=self.NESTED_LIMIT,
                **deity_structure_parameters(DeityPopulation.DEITIES),
            )
            if item.get("id")
        ]

        concepts = [
            EntityRef(
                type="CONCEPT",
                id=str(item["id"]),
                display_label=str(item.get("label") or item["id"]),
                subtitle=f"{item.get('passages')} mantras",
            )
            for item in self._repository.run(
                _RISHI_CONCEPTS_QUERY, id=entity_id, top=self.NESTED_LIMIT
            )
            if item.get("id")
        ]

        families = [
            EntityRef(
                type="RISHI_FAMILY",
                id=str(f["id"]),
                display_label=str(f.get("label") or f["id"]),
                subtitle=f.get("subtitle"),
            )
            for f in (row.get("families") or [])
            if isinstance(f, dict) and f.get("id")
        ]

        is_seer = bool(props.get("is_seer"))
        dimensions: list[DimensionStatus] = []
        if not families:
            dimensions.append(
                DimensionStatus(
                    dimension="family",
                    status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
                    note="BELONGS_TO_FAMILY carries 305 edges over 729 seers, derived from "
                    "Anukramani-stated vrddhi patronymics. No family here means no "
                    "patronymic was stated or derivable, not that the seer had no lineage.",
                )
            )
        if not source_stated:
            dimensions.append(
                DimensionStatus(
                    dimension="passages_source_stated",
                    status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
                    note="Every seer edge for this figure is CONTAINER_INHERITED: a sukta's "
                    "label projected onto each of its mantras. 15,177 of the 17,889 seer "
                    "edges in the graph are, and all 5,084 Atharvavedic ones are. A verse "
                    "here does not itself name this seer.",
                )
            )

        caveats = [
            CaveatView(
                text="STRICT AND INHERITED ATTRIBUTION ARE NOT SUMMED, AND MUST NOT BE. "
                "`passages_source_stated` is what a source states verse by verse; "
                "`passages_container_inherited` is a sukta label projected downward. The "
                "Yajurveda's 2,240 seer edges are every one source-stated and the "
                "Atharvaveda's 5,084 are every one inherited, so a blended total would "
                "compare a statement of the text against a projection.",
                source="measured",
            ),
            CaveatView(
                text=named_query_caveat("rishi_layer_reach_by_veda"),
                source="rishi_layer_reach_by_veda",
            ),
        ]
        if not is_seer:
            caveats.append(
                CaveatView(
                    text=f"THIS IS NOT A SEER. `is_seer` is false and `non_seer_kind` is "
                    f"{props.get('non_seer_kind')!r}: the Anukramani's rishi slot holds the "
                    "being a hymn ADDRESSES as well as the one who saw it, and 113 of the "
                    "729 entries are of that kind. Do not render this as a composer. It is "
                    "also not a reason to render it as a deity -- the deity surface has its "
                    "own population contract and this node is not part of it.",
                    source="measured",
                )
            )
        if "SV" in per_veda:  # pragma: no cover - the SV carries no seer apparatus
            caveats.append(CaveatView(text=SAMAVEDA_SCOPE_STATEMENT, source="measured"))
        else:
            caveats.append(
                CaveatView(
                    text="The Samaveda carries NO seer apparatus at all -- HAS_RISHI reaches "
                    "the Rigveda (10,565), Atharvaveda (5,084) and Yajurveda (2,240) and no "
                    "Samavedic mantra. Its absence from `passages_by_veda` is a missing "
                    "layer, not an unattributed corpus.",
                    source="measured",
                )
            )

        return RishiProfile(
            id=str(props.get("entity_key") or entity_id),
            display_label=str(props.get("display_label") or entity_id),
            label_iast=_text(props.get("label_iast")),
            preferred_label=_text(props.get("preferred_label")),
            normalized_name=_text(props.get("normalized_name")),
            is_seer=is_seer,
            non_seer_kind=_text(props.get("non_seer_kind")),
            family_assignment_class=_text(props.get("family_assignment_class")),
            registry_namespace=_text(props.get("registry_namespace")),
            occurrence_count=_as_int(props.get("occurrence_count")),
            patronymic_iast=_text(props.get("patronymic_iast")),
            patronymics_iast=_as_list(props.get("patronymics_iast")),
            personal_name_iast=_text(props.get("personal_name_iast")),
            personal_names_iast=_as_list(props.get("personal_names_iast")),
            decomposition_method=_text(props.get("decomposition_method")),
            layer_veda_scope=_as_list(props.get("layer_veda_scope")),
            family=families[0] if families else None,
            family_members=families[1:],
            passages_source_stated=source_stated or None,
            passages_container_inherited=inherited or None,
            passages_by_veda=passages_by_veda,
            deities=deities,
            concepts=concepts,
            chandas=[
                EntityRef(
                    type="CHANDAS",
                    id=str(c["id"]),
                    display_label=str(c.get("label") or c["id"]),
                )
                for c in (row.get("chandas") or [])
                if isinstance(c, dict) and c.get("id")
            ][: self.NESTED_LIMIT],
            formula_count=_as_int(row.get("formula_count")),
            dimension_status=dimensions,
            data_status=(
                KnowledgeStatus.SUPPORTED
                if source_stated or inherited
                else KnowledgeStatus.INSUFFICIENT_EVIDENCE
            ),
            coverage=CoverageView(
                vedas_in_scope=sorted(per_veda),
                vedas_not_covered=[v for v in VEDA_ORDER if v not in per_veda],
                measured={
                    veda: counts["strict"] + counts["inherited"]
                    for veda, counts in per_veda.items()
                },
                denominator=dict(CORPUS_MANTRAS),
            ),
            caveats=caveats,
        )

    def rishi_family_members(self, family_id: str) -> list[EntityRef]:
        """Members of one seer family, each carrying whether it is a seer at all."""
        return [
            EntityRef(
                type="RISHI",
                id=str(row["id"]),
                display_label=str(row.get("label") or row["id"]),
                subtitle=(
                    "seer"
                    if row.get("is_seer")
                    else f"not a seer: {row.get('non_seer_kind') or 'kind unrecorded'}"
                ),
            )
            for row in self._repository.run(
                _RISHI_FAMILY_MEMBERS_QUERY, id=family_id, top=self.NESTED_LIMIT
            )
            if row.get("id")
        ]

    # =======================================================================
    # Rituals
    # =======================================================================

    def list_rituals(self, *, limit: int, offset: int) -> Paginated[RitualSummary]:
        """The modelled rites, each row carrying the measured inventory bound."""
        rows = self._repository.run(_RITUAL_LIST_QUERY, limit=limit, offset=offset)
        coverage = self._ritual_coverage()
        items = [
            RitualSummary(
                type="RITUAL",
                id=str(row["id"]),
                display_label=str(row.get("display_label") or row["id"]),
                label_iast=_text(row.get("label_iast")),
                subtitle=_ritual_subtitle(
                    _as_int(row.get("step_count")),
                    _as_int(row.get("procedure_step_count")),
                ),
                short_description=_text(row.get("short_description")),
                passage_count=_as_int(row.get("mention_count")),
                inventory_coverage=coverage,
                step_count=_as_int(row.get("step_count")),
                procedure_step_count=_as_int(row.get("procedure_step_count")),
                devata_count=_as_int(row.get("devata_count")),
                described_in_count=_as_int(row.get("described_in_count")),
            )
            for row in rows
            if row.get("id")
        ]
        total_row = self._repository.run_one("MATCH (r:Ritual) RETURN count(r) AS total")
        return paginate(
            items,
            limit=limit,
            offset=offset,
            total=_as_int(total_row.get("total")) if total_row else None,
            data_status=KnowledgeStatus.PARTIAL,
            caveats=[
                CaveatView(text=self._ritual_coverage(), source="measured"),
                CaveatView(text=named_query_caveat("ritual_profile"), source="ritual_profile"),
            ],
        )

    #: Procedure rows returned in one profile. One rite carries 227 sutra steps, so the
    #: nested list needs a cap of its own; ``procedure_step_count`` reports the full figure
    #: so a truncated list cannot read as the whole procedure.
    PROCEDURE_LIMIT: Final = 60

    def get_ritual(self, entity_id: str, *, population: DeityPopulation) -> RitualProfile:
        """One rite, whose empty step list says which kind of empty it is."""
        parameters = {
            **deity_structure_parameters(population),
            "id": entity_id,
            "top": self.NESTED_LIMIT,
            "step_limit": self.PROCEDURE_LIMIT,
        }
        row = self._repository.run_one(_RITUAL_PROFILE_QUERY, **parameters)
        if row is None:
            raise EntityNotFoundError(
                f"No ritual with id '{entity_id}'.",
                hint="GET /api/v1/rituals lists every modelled rite.",
            )
        props: dict[str, Any] = dict(row.get("props") or {})

        steps = [
            RitualStep(
                order=_as_int(step.get("order")),
                display_label=str(step.get("label")),
                description=step.get("evidence") or step.get("basis"),
            )
            for step in (row.get("steps") or [])
            if isinstance(step, dict) and step.get("label")
        ]
        steps.sort(key=lambda s: (s.order is None, s.order or 0, s.display_label))

        procedure = [
            RitualProcedureSource(
                work_key=_text(source.get("work_key")),
                work_label=_work_label(source.get("work_key")),
                source_type=_text(source.get("source_type")),
                veda_school=_text(source.get("veda_school")),
                step_count=_as_int(source.get("step_count")),
                anchoring_basis=_text(source.get("anchoring_basis")),
                steps=[
                    RitualProcedureStep(
                        position=_as_int(step.get("position")),
                        display_label=str(step.get("label")),
                        text=_text(step.get("text")),
                        citation=_text(step.get("citation")),
                        stated_position=_text(step.get("stated_position")),
                        order_basis=_text(step.get("order_basis")),
                        order_completeness=_text(step.get("order_completeness")),
                    )
                    for step in (source.get("steps") or [])
                    if isinstance(step, dict) and step.get("label")
                ],
            )
            for source in (row.get("procedure_sources") or [])
            if isinstance(source, dict) and source.get("work_key")
        ]
        procedure.sort(key=lambda s: (-(s.step_count or 0), s.work_key or ""))
        procedure_total = _as_int(row.get("procedure_step_count"))

        dimensions: list[DimensionStatus] = []
        if not steps:
            dimensions.append(
                DimensionStatus(
                    dimension="steps",
                    status=KnowledgeStatus.NOT_BUILT,
                    note="This is the Samhita-numbered layer, and 3 such edges exist in the "
                    "entire graph, all on the soma pressing, whose morning, midday and third "
                    "libations the text itself numbers. No other rite in this corpus states "
                    "an order in its own words and none was invented for it -- elaborate "
                    "procedure is Brahmana and Sutra material. Read `procedure` before "
                    "concluding the rite has no recorded sequence: an empty `steps` is an "
                    "unbuilt Samhita layer, not an unstructured rite.",
                )
            )
        if procedure:
            listed = [step for source in procedure for step in source.steps]
            partial = sum(
                1 for s in listed if s.order_completeness == "PARTIAL_STATED_POSITIONS"
            )
            shown = (
                f"{len(listed)} of {procedure_total} steps shown. "
                if procedure_total and procedure_total > len(listed)
                else ""
            )
            dimensions.append(
                DimensionStatus(
                    dimension="procedure",
                    status=KnowledgeStatus.PARTIAL,
                    note=f"{len(procedure)} source work(s) each record their own sequence "
                    f"for this rite, numbered from 1 independently, so the groups do not "
                    f"compose into one procedure. {shown}{partial} of the {len(listed)} "
                    "steps listed state a position without printing the run it falls in. "
                    "The evidence is Srautasutra and Grhyasutra, never a Samhita passage, "
                    "and it is a different claim from `steps` -- which is why it is a "
                    "different field. The cited works have no node in this graph.",
                )
            )
        else:
            dimensions.append(
                DimensionStatus(
                    dimension="procedure",
                    status=KnowledgeStatus.NOT_BUILT,
                    note="No sutra-attested procedure is recorded for this rite. That is an "
                    "absence in the staged sources, not evidence that the rite has none.",
                )
            )
        for name, values in (
            ("offerings", row.get("offerings")),
            ("substances", row.get("substances")),
            ("objects", row.get("objects")),
            ("roles", row.get("roles")),
            ("purposes", row.get("purposes")),
        ):
            if not _refs(values):
                dimensions.append(
                    DimensionStatus(
                        dimension=name,
                        status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
                        note="Ritual apparatus is curated and thin by design, and all of it "
                        "is TIER_D; the measured edge count is in `coverage_statement`. An "
                        "empty list is uncurated, not a rite performed without one.",
                    )
                )

        coverage = self._ritual_coverage()
        return RitualProfile(
            id=str(props.get("entity_key") or entity_id),
            display_label=str(props.get("display_label") or entity_id),
            label_iast=_text(props.get("preferred_label_sa")),
            short_description=_text(props.get("short_description"))
            or _text(props.get("definition")),
            steps=steps,
            procedure=procedure,
            procedure_step_count=procedure_total,
            roles=_refs(row.get("roles")),
            offerings=_refs(row.get("offerings")),
            substances=_refs(row.get("substances")),
            objects=_refs(row.get("objects")),
            devatas=_refs(row.get("devatas")),
            purposes=_refs(row.get("purposes")),
            broader_than=_refs(row.get("broader_than")),
            passages=_refs(row.get("passages")),
            passage_count=_as_int(row.get("passage_count")),
            mention_count=_as_int(row.get("mention_count")),
            coverage_statement=coverage,
            dimension_status=dimensions,
            data_status=KnowledgeStatus.PARTIAL,
            caveats=[
                CaveatView(text=self._ritual_coverage(), source="measured"),
                CaveatView(
                    text=named_query_caveat("ritual_step_sequence"), source="ritual_step_sequence"
                ),
                CaveatView(
                    text=named_query_caveat("rituals_described_in_passages"),
                    source="rituals_described_in_passages",
                ),
                *population_caveats(population),
            ],
        )

    # =======================================================================

    def _validate_choice(self, name: str, value: str | None, allowed: frozenset[str]) -> None:
        """Refuse a filter value outside its measured space, by name.

        A misspelling used to yield ``200`` with ``total=0`` and nothing distinguishing an
        invalid filter from an empty result -- and ``?structure=WARRIOR``, an axis value in
        the structure slot, looked identical to a structure with no members. The generic
        entity surface already got this right; this makes the deity surface match it.
        """
        if value is None or value in allowed:
            return
        raise BadRequestError(
            f"'{value}' is not a known {name} for a devata-slot entry.",
            hint=f"Available {name}: " + ", ".join(sorted(allowed)) + ".",
        )

    def _validate_veda(self, veda: str | None) -> None:
        if veda is not None and veda not in CORPUS_MANTRAS:
            raise BadRequestError(
                f"'{veda}' is not a corpus in this graph.",
                hint="Corpora: " + ", ".join(VEDA_ORDER) + ".",
            )


# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------


def _truncate(text: Any, width: int = 160) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    stripped = text.strip()
    return stripped if len(stripped) <= width else stripped[: width - 3] + "..."


def _precision_for_strict(strict_count: Any) -> AttributionPrecision:
    """PER_PASSAGE only where at least one edge in the pair is source-stated.

    A seer-to-deity reference is reached through two attribution edges, and it is strict
    only if BOTH state their claim of the passage itself. Anything less is a projection,
    and 15,177 of 17,889 seer edges are exactly that.
    """
    return (
        AttributionPrecision.PER_PASSAGE
        if isinstance(strict_count, (int, float)) and strict_count
        else AttributionPrecision.CONTAINER_INHERITED
    )


def _precision(value: Any) -> AttributionPrecision:
    """Read the graph's ``attribution_precision`` without coercing an unknown value.

    The measured value space is ``TEXTUAL_MENTION`` on all 17,165 mention edges and
    ``CONTAINER_INHERITED`` / ``PER_PASSAGE`` on the attribution edges. An unrecognised
    value becomes ``UNKNOWN`` rather than defaulting to ``PER_PASSAGE``, because defaulting
    would promote a projection into a statement the text makes.
    """
    if isinstance(value, str):
        try:
            return AttributionPrecision(value)
        except ValueError:
            return AttributionPrecision.UNKNOWN
    return AttributionPrecision.UNKNOWN


def _int_map(value: Any) -> dict[str, int]:
    if isinstance(value, str):
        value = parse_json_property(value)
    if not isinstance(value, dict):
        return {}
    return {str(k): int(v) for k, v in value.items() if isinstance(v, (int, float))}


def _refs(entries: Any) -> list[EntityRef]:
    """Map collected ``{id, label, labels}`` maps onto typed references.

    The product type comes from the node's labels through
    :func:`~vedagraph.api.services.search_service.result_type_for_labels`, so no raw Neo4j
    label reaches a response body even when a traversal returned a node of a type the
    caller did not ask for.
    """
    if not isinstance(entries, list):
        return []
    refs: list[EntityRef] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        identifier = str(entry["id"])
        if identifier in seen:
            continue
        seen.add(identifier)
        labels = entry.get("labels")
        type_name = (
            result_type_for_labels(labels).value
            if isinstance(labels, list)
            else _type_from_id(identifier)
        )
        subtitle = entry.get("subtitle") or entry.get("relation")
        refs.append(
            EntityRef(
                type=type_name,
                id=identifier,
                display_label=str(entry.get("label") or identifier),
                subtitle=_truncate(subtitle),
            )
        )
    return refs


def _type_from_id(identifier: str) -> str:
    """Product type for a reference collected without its labels.

    Falls back on the id namespace, which the graph assigns deterministically
    (``VG:DEVATA:``, ``VG:RISHI:``, ``VG:CHANDAS:``, ``VG:CONCEPT:``). Unknown namespaces
    are ``CONCEPT`` rather than a guess dressed as a type.
    """
    prefixes = {
        "VG:DEVATA:": "DEVATA",
        "VG:RISHI_FAMILY:": "RISHI_FAMILY",
        "VG:RISHI:": "RISHI",
        "VG:CHANDAS:": "CHANDAS",
        "VG:EPITHET:": "EPITHET",
        "VG:DEITYAXIS:": "DEITY_AXIS",
    }
    for prefix, type_name in prefixes.items():
        if identifier.startswith(prefix):
            return type_name
    if identifier.startswith("VG:") and ":FORMULA" in identifier:
        return "FORMULA"
    if identifier.count(":") >= 3 and identifier.startswith("VG:"):
        return "PASSAGE"
    return "CONCEPT"


__all__ = [
    "ATTRIBUTION_SCOPE_STATEMENT",
    "NOT_A_DEITY_SUBJECT",
    "SAMAVEDA_SCOPE_STATEMENT",
    "STRICT_MODE_STATEMENT",
    "EntityService",
    "ritual_coverage_statement",
    "subject_disclosure",
    "tiers_for",
]
