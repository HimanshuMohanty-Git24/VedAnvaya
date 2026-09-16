"""Multi-channel evidence retrieval. The model never touches the database.

Every channel is a named query in this module with bound parameters. There is no code
path by which a question, or anything a model generated, becomes Cypher syntax: the
planner picks channels from a fixed set, the resolver turns names into ``entity_key``
values, and those travel as parameters. A generated string has nowhere to go.

Four contracts are enforced here rather than left to the prompt, because a prompt is a
request and a query is a guarantee.

**Deity certainty.** Vedic Sanskrit has one word for the god Agni and for fire. All 17,165
``MENTIONS_DEVATA`` edges are graded and the split is not marginal: 8,340 ``DEITY_CERTAIN``,
2,019 ``DEITY_PROBABLE``, 6,806 ``DEITY_AMBIGUOUS``. Retrieval defaults to certain plus
probable -- :data:`DEFAULT_CERTAINTY` -- so an answer about the *god* is not built from
occurrences of the common noun. The ambiguous count is retrieved too, separately, so the
response can say what was withheld instead of silently narrowing the corpus.

**Attribution is not mention.** ``HAS_DEVATA`` (10,558 edges, all Rigvedic, most inherited
from a hymn label) answers "is this hymn dedicated to it?". ``MENTIONS_DEVATA`` (17,165,
all four corpora) answers "is it named here?". They are retrieved by separate channels and
every row carries which relation produced it, because a count from one presented as the
other is wrong by construction.

**Absence is a retrieval result, not a missing row.** :data:`_LEXICAL_PRESENCE` asks
whether a term occurs in a corpus *and* whether that corpus has a searchable surface at
all. The Samaveda has no English translation and the Yajurveda's Sanskrit was extracted
from printed containers, so "not found" and "not searchable" are different answers and
this is the channel that can tell them apart.

**Direction is measured, not assumed.** Mention edges run Passage → Devata: Indra has 3,566
inbound and zero outbound. The traversals below are undirected where a wrong arrow would
silently return nothing.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Final

from vedagraph.api.ask.matching import fold_query_name
from vedagraph.api.ask.planner import QueryPlan
from vedagraph.api.ask.resolver import ResolvedEntity
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

logger = logging.getLogger(__name__)

#: The product default for deity mentions: the god, not the common noun. Ambiguous
#: mentions are counted separately and reported, never folded into a total.
DEFAULT_CERTAINTY: Final[tuple[str, ...]] = ("DEITY_CERTAIN", "DEITY_PROBABLE")

#: Per-channel row caps. The evidence packet has a budget and a channel that returns 400
#: passages would spend all of it on one dimension of a multi-part question.
PASSAGES_PER_ENTITY: Final = 4
MAX_TEXT_SEARCH_ROWS: Final = 5

# ---------------------------------------------------------------------------
# Passages
# ---------------------------------------------------------------------------

# `text_nfc` is the Sanskrit. `text_form` is a form descriptor whose value is 'SAMHITA',
# and reading it as the text -- which is the obvious guess from the name -- yields a
# passage whose Sanskrit renders as the word "SAMHITA".
_PASSAGE_BY_KEY: Final = """
MATCH (p:Passage)
WHERE p.canonical_key = $key OR p.canonical_citation = $key
OPTIONAL MATCH (p)-[:HAS_TEXT_VERSION]->(tv:TextVersion)
    WHERE tv.text_role = 'PRIMARY_TEXT'
// A verse inside a multi-verse print unit carries no HAS_TRANSLATION edge of its own, so
// the union of the two patterns is what stops Ask reporting the 30 even verses of
// RV 1.65-1.70 as untranslated while a rendering on the paired verse covers them.
OPTIONAL MATCH (p)-[:HAS_TRANSLATION]->(own:Translation)
OPTIONAL MATCH (anchor:Passage)-[:HAS_TRANSLATION]->(span:Translation)
    WHERE span.alignment_level = 'MANTRA_RANGE'
      AND p.canonical_key IN span.covers_canonical_keys
      AND anchor.canonical_key <> p.canonical_key
WITH p, tv, coalesce(own, span) AS tr, anchor
RETURN p.canonical_key AS canonical_key,
       p.canonical_citation AS canonical_citation,
       p.veda AS veda,
       p.display_type AS display_type,
       head(collect(DISTINCT tv.text_nfc)) AS sanskrit,
       head(collect(DISTINCT tr.text)) AS translation,
       head(collect(DISTINCT tr.translator)) AS translator,
       head(collect(DISTINCT tr.language)) AS translation_language,
       head(collect(DISTINCT tr.alignment_level)) AS translation_alignment_level,
       head(collect(DISTINCT tr.covers_canonical_keys)) AS translation_covers_canonical_keys,
       head(collect(DISTINCT tr.reuse_kind)) AS translation_reuse_kind,
       head(collect(DISTINCT tr.reused_from_veda)) AS translation_reused_from_veda,
       head(collect(DISTINCT tr.reused_from_passage_key)) AS translation_reused_from_passage_key,
       head(collect(DISTINCT tr.reused_from_citation)) AS translation_reused_from_citation,
       head(collect(DISTINCT anchor.canonical_key)) AS translation_anchor_key
LIMIT 1
"""

# Mention and ascription kept apart: $relations is one of the two sets, never both, and
# the row says which. Certainty filters only the mention relation, because HAS_DEVATA
# carries no referent_certainty -- it is an editorial ascription, not a word occurrence.
_PASSAGES_FOR_ENTITY: Final = """
MATCH (p:Passage)-[r]->(e {entity_key: $entity_key})
WHERE type(r) IN $relations
  AND p.display_type = 'MANTRA'
  AND ($veda = 'ALL' OR p.veda = $veda)
  AND (r.referent_certainty IS NULL OR r.referent_certainty IN $certainty)
OPTIONAL MATCH (p)-[:HAS_TEXT_VERSION]->(tv:TextVersion)
    WHERE tv.text_role = 'PRIMARY_TEXT'
OPTIONAL MATCH (p)-[:HAS_TRANSLATION]->(tr:Translation)
WITH p, r,
     head(collect(DISTINCT tv.text_nfc)) AS sanskrit,
     head(collect(DISTINCT tr.text)) AS translation,
     head(collect(DISTINCT tr.language)) AS translation_language,
     head(collect(DISTINCT tr.reuse_kind)) AS translation_reuse_kind,
     head(collect(DISTINCT tr.reused_from_veda)) AS translation_reused_from_veda,
     head(collect(DISTINCT tr.reused_from_passage_key)) AS translation_reused_from_passage_key,
     head(collect(DISTINCT tr.reused_from_citation)) AS translation_reused_from_citation,
     head(collect(DISTINCT tr.alignment_level)) AS translation_alignment_level,
     head(collect(DISTINCT tr.covers_canonical_keys)) AS translation_covers_canonical_keys
RETURN p.canonical_key AS canonical_key,
       p.canonical_citation AS canonical_citation,
       p.veda AS veda,
       sanskrit, translation,
       translation_language, translation_reuse_kind, translation_reused_from_veda,
       translation_reused_from_passage_key, translation_reused_from_citation,
       translation_alignment_level, translation_covers_canonical_keys,
       type(r) AS relation_type,
       r.referent_certainty AS certainty,
       r.attribution_precision AS attribution_precision
ORDER BY p.veda, p.canonical_key
LIMIT $limit
"""

_TRANSLATION_SEARCH: Final = """
MATCH (p:Passage {display_type: 'MANTRA'})-[:HAS_TRANSLATION]->(tr:Translation)
WHERE toLower(tr.text) CONTAINS toLower($term)
  AND ($veda = 'ALL' OR p.veda = $veda)
RETURN p.canonical_key AS canonical_key,
       p.canonical_citation AS canonical_citation,
       p.veda AS veda,
       tr.text AS translation,
       tr.language AS translation_language,
       tr.reuse_kind AS translation_reuse_kind,
       tr.reused_from_veda AS translation_reused_from_veda,
       tr.reused_from_passage_key AS translation_reused_from_passage_key,
       tr.reused_from_citation AS translation_reused_from_citation,
       tr.alignment_level AS translation_alignment_level,
       tr.covers_canonical_keys AS translation_covers_canonical_keys,
       'TRANSLATION_MATCH' AS relation_type
ORDER BY p.veda, p.canonical_key
LIMIT $limit
"""

# ---------------------------------------------------------------------------
# Lexical presence: the channel that can distinguish absence from unsearchability
# ---------------------------------------------------------------------------

#: Per-Veda searchable-surface reality, so a miss can be attributed. These are the
#: measured facts the corpus layer recorded, not assumptions: the Samaveda has no released
#: English translation at all, and the Yajurveda's Sanskrit exists only as text extracted
#: from printed containers rather than transcribed per verse.
SURFACE_LIMITS: Final[dict[str, str]] = {
    "SV": "The Samaveda has no released English translation, so an English-surface miss "
    "establishes nothing about it.",
    "YV": "The Yajurveda's Sanskrit was extracted from printed containers rather than "
    "transcribed verse by verse, so lexical recall into it is bounded by that "
    "extraction and a miss is not textual absence.",
    "AV": "Atharvavedic Sanskrit is accented inline, so an unaccented query term matches "
    "only where the accents fall outside it.",
    "RV": "Rigvedic Sanskrit is accented inline, so an unaccented query term matches only "
    "where the accents fall outside it.",
}

# Asks two questions at once, which is the point: how many passages carry the term, and
# how many carry a surface it could have been found on. A zero in the first with a
# non-zero in the second is a real absence; a zero in both is an unsearchable corpus.
_LEXICAL_PRESENCE: Final = """
MATCH (w:Work)
WITH DISTINCT w.veda AS veda
CALL (veda) {
    MATCH (p:Passage {veda: veda, display_type: 'MANTRA'})
    OPTIONAL MATCH (p)-[:HAS_TEXT_VERSION]->(tv:TextVersion)
    WITH p, collect(tv.text_nfc) AS sanskrit_forms
    OPTIONAL MATCH (p)-[:HAS_TRANSLATION]->(tr:Translation)
    WITH p, sanskrit_forms, collect(tr.text) AS translations
    RETURN
      count(p) AS mantras,
      count(CASE WHEN size(sanskrit_forms) > 0 THEN 1 END) AS with_sanskrit,
      count(CASE WHEN size(translations) > 0 THEN 1 END) AS with_translation,
      count(CASE WHEN any(s IN sanskrit_forms
                          WHERE s IS NOT NULL AND toLower(s) CONTAINS $term)
                 THEN 1 END) AS sanskrit_hits,
      count(CASE WHEN any(t IN translations
                          WHERE t IS NOT NULL AND toLower(t) CONTAINS $term)
                 THEN 1 END) AS translation_hits
}
RETURN veda, mantras, with_sanskrit, with_translation,
       sanskrit_hits, translation_hits
ORDER BY veda
"""

# ---------------------------------------------------------------------------
# Entity profiles
# ---------------------------------------------------------------------------

_ENTITY_PROFILE: Final = """
MATCH (e {entity_key: $entity_key})
WHERE NOT e:Internal AND NOT e:QAIssue
RETURN e.entity_key AS entity_key,
       e.display_label AS label,
       head(labels(e)) AS entity_type,
       coalesce(e.short_description, e.definition) AS description,
       coalesce(e.preferred_label_sa, e.label_iast, e.preferred_label) AS sanskrit_label,
       e.structure AS structure,
       e.devata_subtype AS devata_subtype,
       e.condition_kind AS condition_kind,
       e.occurrence_count AS occurrence_count,
       e.attribution_scope AS attribution_scope,
       e.attribution_scope_note AS attribution_scope_note
LIMIT 1
"""

# The certainty split per corpus, all three tiers returned. A tier filter can empty a
# corpus that is richly attested -- Agni has 831 CERTAIN Rigvedic mentions and zero CERTAIN
# anywhere else against hundreds of PROBABLE -- so a single filtered number per Veda is a
# per-corpus zero waiting to be misread as textual silence.
_ENTITY_BY_VEDA: Final = """
MATCH (p:Passage)-[r]->(e {entity_key: $entity_key})
WHERE type(r) IN $relations AND p.display_type = 'MANTRA'
RETURN p.veda AS veda,
       type(r) AS relation_type,
       count(DISTINCT CASE WHEN r.referent_certainty = 'DEITY_CERTAIN' THEN p END)
           AS certain,
       count(DISTINCT CASE WHEN r.referent_certainty = 'DEITY_PROBABLE' THEN p END)
           AS probable,
       count(DISTINCT CASE WHEN r.referent_certainty = 'DEITY_AMBIGUOUS' THEN p END)
           AS ambiguous,
       count(DISTINCT CASE WHEN r.referent_certainty IS NULL THEN p END) AS ungraded,
       count(DISTINCT p) AS total
ORDER BY veda
"""

# ---------------------------------------------------------------------------
# Graph paths
# ---------------------------------------------------------------------------

# allShortestPaths inside a bounded subquery, then ranked by worst waypoint degree. A node
# predicate inside the path pattern defeats Neo4j's bidirectional planner and turns this
# into an enumeration -- the same query measured at 3-7ms without it and 22-25s with it,
# which is past the driver budget, so a legitimate "not connected" would surface as a 503.
_GRAPH_PATH: Final = """
MATCH (a {entity_key: $key1}), (b {entity_key: $key2})
CALL (a, b) {
    MATCH path = allShortestPaths((a)-[*1..4]-(b))
    RETURN path LIMIT 25
}
WITH path,
     [n IN nodes(path) |
        coalesce(n.display_label, n.canonical_citation, n.entity_key)] AS node_labels,
     [r IN relationships(path) | type(r)] AS rel_types,
     reduce(worst = 0, n IN nodes(path) |
        CASE WHEN COUNT { (n)--() } > worst THEN COUNT { (n)--() } ELSE worst END)
        AS max_degree
RETURN node_labels, rel_types, max_degree
ORDER BY max_degree ASC
LIMIT 3
"""

# ---------------------------------------------------------------------------
# Formulas and textual reuse
# ---------------------------------------------------------------------------

_FORMULA_FAMILIES_FOR_PASSAGE: Final = """
MATCH (p:Passage {canonical_key: $canonical_key})-[:USES_FORMULA]->(f:Formula)
OPTIONAL MATCH (f)-[:MEMBER_OF_FAMILY]->(ff:FormulaFamily)
RETURN coalesce(ff.family_id, f.formula_id) AS family_id,
       coalesce(ff.representative_display_form, f.display_form) AS display_form,
       coalesce(ff.member_count, 1) AS member_count,
       coalesce(ff.occurrence_count, f.occurrence_count) AS occurrence_count,
       coalesce(ff.vedas, f.vedas) AS vedas,
       coalesce(ff.veda_counts, f.veda_counts) AS veda_counts,
       coalesce(ff.cross_veda, f.cross_veda) AS cross_veda
ORDER BY occurrence_count DESC
LIMIT 4
"""

_FORMULA_FAMILIES_FOR_ENTITY: Final = """
MATCH (p:Passage)-[:MENTIONS_ENTITY|MENTIONS_DEVATA]->(e {entity_key: $entity_key})
MATCH (p)-[:USES_FORMULA]->(f:Formula)-[:MEMBER_OF_FAMILY]->(ff:FormulaFamily)
RETURN ff.family_id AS family_id,
       ff.representative_display_form AS display_form,
       ff.member_count AS member_count,
       ff.occurrence_count AS occurrence_count,
       ff.vedas AS vedas,
       ff.veda_counts AS veda_counts,
       ff.cross_veda AS cross_veda
ORDER BY ff.occurrence_count DESC
LIMIT 4
"""

# Undirected on purpose. All 1,684 REUSES_TEXT_FROM edges point Samaveda-to-Rigveda, and
# 1,421 Rigvedic passages have reuse edges only inbound -- following the arrow shows those
# verses no reuse whatsoever while returning HTTP 200.
_PARALLELS: Final = """
MATCH (p:Passage {canonical_key: $canonical_key})-[r]-(other:Passage)
WHERE type(r) IN $parallel_relations
OPTIONAL MATCH (other)-[:HAS_TRANSLATION]->(tr:Translation)
WITH other, r,
     head(collect(DISTINCT tr.text)) AS translation,
     head(collect(DISTINCT tr.language)) AS translation_language,
     head(collect(DISTINCT tr.reuse_kind)) AS translation_reuse_kind,
     head(collect(DISTINCT tr.reused_from_veda)) AS translation_reused_from_veda,
     head(collect(DISTINCT tr.reused_from_passage_key)) AS translation_reused_from_passage_key,
     head(collect(DISTINCT tr.reused_from_citation)) AS translation_reused_from_citation,
     head(collect(DISTINCT tr.alignment_level)) AS translation_alignment_level,
     head(collect(DISTINCT tr.covers_canonical_keys)) AS translation_covers_canonical_keys
RETURN other.canonical_key AS canonical_key,
       other.canonical_citation AS canonical_citation,
       other.veda AS veda,
       translation,
       translation_language, translation_reuse_kind, translation_reused_from_veda,
       translation_reused_from_passage_key, translation_reused_from_citation,
       translation_alignment_level, translation_covers_canonical_keys,
       type(r) AS relation_type
ORDER BY other.veda, other.canonical_key
LIMIT 8
"""

PARALLEL_RELATIONS: Final[tuple[str, ...]] = (
    "EXACT_PARALLEL_OF",
    "NEAR_PARALLEL_OF",
    "REUSES_TEXT_FROM",
    "VARIANT_OF",
    "PARALLEL_TO",
)

# ---------------------------------------------------------------------------
# Interpretive claims
# ---------------------------------------------------------------------------

# `asserted_by` is the source and `falsifier` is what would defeat the claim. Both travel
# with the text: an interpretation rendered without its source reads as what the text says.
_INTERPRETIVE_CLAIMS: Final = """
MATCH (ic:InterpretiveClaim)
WHERE ic.about IN $entity_keys
RETURN ic.claim_id AS claim_id,
       ic.claim_text AS claim_text,
       ic.asserted_by AS asserted_by,
       ic.claim_type AS claim_type,
       ic.about AS about,
       ic.scope AS scope,
       ic.falsifier AS falsifier,
       ic.status AS status,
       ic.quality_tier AS quality_tier,
       ic.evidence_passages AS evidence_passages
LIMIT 4
"""

_DERIVED_METRICS: Final = """
MATCH (m:DerivedMetric)
WHERE m.subject_key IN $entity_keys
RETURN m.metric_id AS metric_id,
       m.metric_name AS metric_name,
       m.subject_key AS subject_key,
       m.values_json AS values_json,
       m.scope_note AS scope_note,
       m.method AS method
LIMIT 4
"""

#: Which relations answer "named here" versus "dedicated to". Kept as named sets so a
#: channel cannot accidentally union them.
MENTION_RELATIONS: Final[tuple[str, ...]] = ("MENTIONS_DEVATA", "MENTIONS_ENTITY")
ASCRIPTION_RELATIONS: Final[tuple[str, ...]] = ("HAS_DEVATA",)
CONCEPT_RELATIONS: Final[tuple[str, ...]] = (
    "MENTIONS_ENTITY",
    "ABOUT_CONCEPT",
    "PROTECTS_FROM",
    "DESCRIBED_IN",
)


@dataclass
class LexicalPresence:
    """Whether a term occurs in a corpus, and whether it could have."""

    term: str
    rows: list[dict[str, Any]] = field(default_factory=list)

    def unsearchable_vedas(self) -> list[str]:
        """Vedas where a miss cannot mean absence, because no surface carries the term."""
        out: list[str] = []
        for row in self.rows:
            hits = (row.get("sanskrit_hits") or 0) + (row.get("translation_hits") or 0)
            if hits:
                continue
            if not row.get("with_sanskrit") and not row.get("with_translation"):
                out.append(str(row["veda"]))
        return out

    def found_in(self) -> dict[str, int]:
        return {
            str(r["veda"]): int((r.get("sanskrit_hits") or 0) + (r.get("translation_hits") or 0))
            for r in self.rows
            if (r.get("sanskrit_hits") or 0) + (r.get("translation_hits") or 0) > 0
        }


@dataclass
class RetrievalResult:
    channels_used: list[str] = field(default_factory=list)
    channels_empty: list[str] = field(default_factory=list)
    passages: list[dict[str, Any]] = field(default_factory=list)
    ascription_passages: list[dict[str, Any]] = field(default_factory=list)
    entity_profiles: list[dict[str, Any]] = field(default_factory=list)
    entity_by_veda: list[dict[str, Any]] = field(default_factory=list)
    graph_paths: list[dict[str, Any]] = field(default_factory=list)
    formulas: list[dict[str, Any]] = field(default_factory=list)
    parallels: list[dict[str, Any]] = field(default_factory=list)
    interpretive_claims: list[dict[str, Any]] = field(default_factory=list)
    derived_metrics: list[dict[str, Any]] = field(default_factory=list)
    lexical: LexicalPresence | None = None
    retrieval_ms: float = 0.0

    def note(self, channel: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Record a channel as used or empty. An empty channel is reported, not dropped:
        "we looked and found nothing" and "we never looked" are different answers.
        """
        (self.channels_used if rows else self.channels_empty).append(channel)
        return rows


def _relations_for(entity_type: str) -> tuple[str, ...]:
    """Which mention relations reach this entity type.

    A ``Devata`` is reached by ``MENTIONS_DEVATA``; a ``Concept``, ``Condition`` or
    ``Ritual`` by ``MENTIONS_ENTITY`` and ``ABOUT_CONCEPT``. Asking for the wrong set
    returns zero rows and looks exactly like an entity nothing is said about.
    """
    if entity_type == "Devata":
        return MENTION_RELATIONS
    return CONCEPT_RELATIONS


def retrieve(
    plan: QueryPlan,
    resolved_entities: list[ResolvedEntity],
    repository: Neo4jRepository,
) -> RetrievalResult:
    """Run the channels the plan selected. Never raises for one channel's failure."""
    start = time.monotonic()
    result = RetrievalResult()
    channels = set(plan.retrieval_channels)
    veda = plan.veda_scope
    certainty = list(DEFAULT_CERTAINTY)

    # -- the named passage, and what it is parallel to ----------------------
    focus_key: str | None = None
    if plan.passage_key:
        rows = result.note("passage_by_key", repository.run(_PASSAGE_BY_KEY, key=plan.passage_key))
        result.passages.extend(rows)
        if rows:
            focus_key = str(rows[0]["canonical_key"])

    if focus_key:
        result.parallels.extend(
            result.note(
                "parallels",
                repository.run(
                    _PARALLELS,
                    canonical_key=focus_key,
                    parallel_relations=list(PARALLEL_RELATIONS),
                ),
            )
        )
        if "formulas" in channels:
            result.formulas.extend(
                result.note(
                    "formula_families",
                    repository.run(_FORMULA_FAMILIES_FOR_PASSAGE, canonical_key=focus_key),
                )
            )

    # -- entity profiles, their corpus distribution, their passages ---------
    for entity in resolved_entities[:4]:
        relations = list(_relations_for(entity.entity_type))

        profile = repository.run(_ENTITY_PROFILE, entity_key=entity.entity_key)
        for row in profile:
            row["_asked_as"] = entity.name_as_asked
            row["_match_rank"] = entity.match_rank.name
        result.entity_profiles.extend(result.note("entity_profile", profile))

        by_veda = repository.run(_ENTITY_BY_VEDA, entity_key=entity.entity_key, relations=relations)
        for row in by_veda:
            row["_entity_label"] = entity.label
            row["_entity_key"] = entity.entity_key
        result.entity_by_veda.extend(result.note("entity_by_veda", by_veda))

        passages = repository.run(
            _PASSAGES_FOR_ENTITY,
            entity_key=entity.entity_key,
            relations=relations,
            veda=veda,
            certainty=certainty,
            limit=PASSAGES_PER_ENTITY,
        )
        for row in passages:
            row["_entity_label"] = entity.label
        result.passages.extend(result.note("entity_passages", passages))

        # "Dedicated to" is a different question from "named here", so it is a
        # different channel and the rows stay separate.
        if entity.entity_type == "Devata":
            ascribed = repository.run(
                _PASSAGES_FOR_ENTITY,
                entity_key=entity.entity_key,
                relations=list(ASCRIPTION_RELATIONS),
                veda=veda,
                certainty=certainty,
                limit=PASSAGES_PER_ENTITY,
            )
            for row in ascribed:
                row["_entity_label"] = entity.label
            result.ascription_passages.extend(result.note("ascriptions", ascribed))

        if "formulas" in channels:
            result.formulas.extend(
                result.note(
                    "entity_formulas",
                    repository.run(_FORMULA_FAMILIES_FOR_ENTITY, entity_key=entity.entity_key),
                )
            )

    # -- how two subjects are connected -------------------------------------
    if "graph_paths" in channels and len(resolved_entities) >= 2:
        try:
            result.graph_paths.extend(
                result.note(
                    "graph_paths",
                    repository.run(
                        _GRAPH_PATH,
                        key1=resolved_entities[0].entity_key,
                        key2=resolved_entities[1].entity_key,
                    ),
                )
            )
        except Exception:
            # A path search that blows its budget is a missing channel, not a failed
            # request: the rest of the evidence still answers part of the question.
            logger.warning("ask: graph path channel failed", exc_info=True)
            result.channels_empty.append("graph_paths")

    # -- interpretation and derived figures ---------------------------------
    if resolved_entities:
        keys = [e.entity_key for e in resolved_entities]
        # Interpretive claims are fetched for every resolved entity, whatever the plan
        # selected. Not an oversight: an interpretation this graph holds about the
        # question's subject must be offered even when the question used no interpretive
        # vocabulary, because withholding it means presenting one scholar's reading as
        # the text's plain sense the moment that reading is the only thing in the packet.
        result.interpretive_claims.extend(
            result.note(
                "interpretive_claims",
                repository.run(_INTERPRETIVE_CLAIMS, entity_keys=keys),
            )
        )
        result.derived_metrics.extend(
            result.note("derived_metrics", repository.run(_DERIVED_METRICS, entity_keys=keys))
        )

    # -- lexical presence ---------------------------------------------------
    # Run whenever the question asks whether something occurs. This is the only channel
    # that can answer such a question honestly, because it reports the searchable surface
    # alongside the hit count.
    if "lexical" in channels and plan.lexical_terms:
        term = fold_query_name(plan.lexical_terms[0])
        rows = result.note("lexical_presence", repository.run(_LEXICAL_PRESENCE, term=term))
        result.lexical = LexicalPresence(term=plan.lexical_terms[0], rows=rows)

    # -- free-text fallback -------------------------------------------------
    if "search" in channels and plan.search_term and len(result.passages) < 3:
        result.passages.extend(
            result.note(
                "translation_search",
                repository.run(
                    _TRANSLATION_SEARCH,
                    term=plan.search_term[:100],
                    veda=veda,
                    limit=MAX_TEXT_SEARCH_ROWS,
                ),
            )
        )

    result.retrieval_ms = (time.monotonic() - start) * 1000
    return result
