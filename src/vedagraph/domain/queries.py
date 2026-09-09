"""Named domain queries: what a reader can actually ask the graph.

This module is the product surface. Every entry is a question a researcher would put in
words, the Cypher that answers it, and -- the part that matters most -- a ``caveat``
stating what the answer does *not* establish.

The caveat field is not documentation politeness. Three properties of this corpus make an
uncaveated answer actively misleading, and all three are invisible in the result set:

**The attribution layer is Rigveda-only.** ``HAS_DEVATA``, ``HAS_RISHI``, ``HAS_CHANDAS``
and ``MENTIONS_LEMMA`` have zero edges on the Sāmaveda, Yajurveda and Atharvaveda. A
per-Veda deity table therefore shows three zeroes, and a reader will read that as *the
deity is absent from those Vedas* rather than as *those Vedas have no Anukramaṇī layer*.

**Most attribution is inherited, not stated.** 8,329 of 10,558 ``HAS_DEVATA`` edges and
10,093 of 10,565 ``HAS_RISHI`` edges arrive by projecting a sūkta's label onto each of its
mantras. Every query that counts attributions therefore has a strict variant filtered to
``attribution_precision = 'PER_PASSAGE'``, and where the two answers differ materially the
pair is offered rather than the flattering one.

**Some words are both a deity and a thing.** ``agniḥ`` is Agni and it is fire. Mentions
reached only through such aliases carry ``theonym_ambiguous``, and the queries that would
otherwise silently assert the impersonal reading expose it.

Queries never return internal nodes: :func:`~vedagraph.domain.ontology.product_filter` is
interpolated rather than each query naming excluded labels itself, so a diagnostic label
added later is excluded by editing one constant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from vedagraph.domain.ontology import LABEL_INTERNAL

#: Default parameters, so every query is runnable as written with no arguments.
INDRA: Final = "VG:DEVATA:INDRAH"
AGNI: Final = "VG:DEVATA:AGNIH"
SOMA: Final = "VG:DEVATA:SOMAH"
VARUNA: Final = "VG:DEVATA:VARUNAH"
RUDRA: Final = "VG:DEVATA:RUDRAH"


@dataclass(frozen=True)
class DomainQuery:
    """One answerable question, with its limits attached."""

    name: str
    question: str
    cypher: str
    parameters: dict[str, Any] = field(default_factory=dict)
    #: What this answer does NOT establish. Empty only where there is genuinely nothing
    #: to warn about, which is rarer than it looks.
    caveat: str = ""
    #: Killer-question numbers this serves, for the answerability audit.
    serves: tuple[int, ...] = ()


_NOT_INTERNAL = f"NOT n:{LABEL_INTERNAL}"

_SCOPE_CAVEAT = (
    "The Anukramani attribution layer covers the Rigveda only. Zeroes for SV/YV/AV mean "
    "those corpora have no attribution layer, not that the entity is absent from them."
)
_INHERIT_CAVEAT = (
    "Counts include CONTAINER_INHERITED attributions: a sukta's label projected onto each "
    "of its mantras. See the *_strict variant for source-stated attribution only."
)

#: Shared by every single-deity profile query. Hoisted to a constant rather than
#: copied per deity, because two profiles that drifted apart would be worse than one.
_DEITY_PROFILE_CYPHER = """
        MATCH (dv:Devata {entity_key: $key})
        OPTIONAL MATCH (dv)-[:HAS_AXIS]->(ax:DeityAxis)
        OPTIONAL MATCH (dv)-[:HAS_EPITHET]->(ep:Epithet)
        WITH dv, collect(DISTINCT ax.axis) AS axes, collect(DISTINCT ep.label_iast) AS epithets
        RETURN dv.display_label AS deity, dv.label_iast AS iast, dv.structure AS structure,
               axes, epithets, dv.short_description AS description,
               dv.profile_attributed_total AS attributed,
               dv.profile_attributed_per_passage AS attributed_per_passage,
               dv.profile_attributed_inherited AS attributed_inherited,
               dv.profile_top_rishis AS top_rishis, dv.profile_top_chandas AS top_chandas,
               dv.profile_top_concepts AS top_concepts, dv.profile_co_devatas AS co_deities,
               dv.profile_attribution_scope AS attribution_scope
        """

QUERIES: Final[tuple[DomainQuery, ...]] = (
    # ---------------------------------------------------------------- deities
    DomainQuery(
        name="deity_profile",
        question="Who is this deity, where do they appear, and what surrounds them?",
        cypher=_DEITY_PROFILE_CYPHER,
        parameters={"key": INDRA},
        caveat=_SCOPE_CAVEAT + " " + _INHERIT_CAVEAT,
        serves=(1, 17, 18, 19, 20, 38, 43, 44, 45, 46),
    ),
    DomainQuery(
        name="varuna_profile",
        question="What is Varuna's corpus profile, and how does it differ from Indra's?",
        cypher=_DEITY_PROFILE_CYPHER,
        parameters={"key": VARUNA},
        caveat=(
            "Uses the same projection as deity_profile, so the two are directly "
            "comparable. Varuna is attributed to 99 Rigvedic mantras against Indra's "
            "2,869, and the gap is a fact about the Anukramani's sukta labels rather "
            "than a measure of prominence: Varuna is also named inside hymns labelled "
            "for Mitravarunau, which is a separate entity. " + _SCOPE_CAVEAT
        ),
        serves=(3, 44),
    ),
    DomainQuery(
        name="deities_by_axis",
        question="Which deities occupy a given functional role?",
        cypher="""
        MATCH (dv:Devata)-[:HAS_AXIS]->(ax:DeityAxis)
        RETURN ax.axis AS axis, count(dv) AS deities,
               collect(dv.display_label)[0..12] AS examples
        ORDER BY deities DESC, axis
        """,
        caveat=(
            "Axes are curated interpretation (TIER_D), not source statements. 101 of 214 "
            "deities are deliberately [UNSPECIFIED] and do not appear here."
        ),
        serves=(20, 38, 41, 46),
    ),
    DomainQuery(
        name="deity_widest_range",
        question="Which deities have the widest functional range?",
        cypher="""
        MATCH (dv:Devata)-[:HAS_AXIS]->(ax:DeityAxis)
        WHERE ax.axis <> 'UNSPECIFIED'
        WITH dv, count(ax) AS axis_count, collect(ax.axis) AS axes
        RETURN dv.display_label AS deity, axis_count, axes,
               coalesce(dv.profile_attributed_total, 0) AS attributed
        ORDER BY axis_count DESC, attributed DESC, deity LIMIT 15
        """,
        caveat=(
            "Range as curated, so this measures the taxonomy as much as the corpus. "
            "`attributed` is coalesced to 0 rather than left null: only the top 25 "
            "deities are profiled, and a null sorted ahead of a real count, which put "
            "composite Anukramani labels at the head of the list."
        ),
        serves=(38, 46),
    ),
    DomainQuery(
        name="deity_composition",
        question="Which deity labels are duals or composites, and of what?",
        cypher="""
        MATCH (whole:Devata)-[:COMPOSED_OF]->(part:Devata)
        RETURN whole.display_label AS composite, whole.structure AS structure,
               collect(part.display_label) AS components
        ORDER BY composite
        """,
        caveat=(
            "Decomposition follows the dual/plural form of the label. The registry marks "
            "MITRAVARUNAU as deliberately not decomposed while devata_components.yaml "
            "decomposes it; the two files disagree and this follows the component file."
        ),
        serves=(33, 42),
    ),
    DomainQuery(
        name="deity_co_occurrence",
        question="Which deities are attributed to the same mantras?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(a:Devata)
        MATCH (p)-[:HAS_DEVATA]->(b:Devata)
        WHERE a.entity_key < b.entity_key
        RETURN a.display_label AS deity_a, b.display_label AS deity_b,
               count(DISTINCT p) AS shared_mantras
        ORDER BY shared_mantras DESC LIMIT 25
        """,
        caveat=_SCOPE_CAVEAT + " " + _INHERIT_CAVEAT,
        serves=(23, 33, 35),
    ),
    DomainQuery(
        name="deities_through_common_rishis",
        question="Which deities are connected through the same seers?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(dv:Devata)
        MATCH (p)-[:HAS_RISHI]->(rs:Rishi)
        WITH rs, dv, count(DISTINCT p) AS n WHERE n > 4
        WITH rs, collect({deity: dv.display_label, mantras: n}) AS deities
        WHERE size(deities) > 1
        RETURN rs.display_label AS rishi, deities ORDER BY size(deities) DESC LIMIT 20
        """,
        caveat=_SCOPE_CAVEAT + " " + _INHERIT_CAVEAT,
        serves=(2, 19, 35),
    ),
    DomainQuery(
        name="rishis_invoking_deity",
        question="Which seers are most associated with this deity?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[r:HAS_RISHI]->(rs:Rishi)
        RETURN rs.display_label AS rishi, count(DISTINCT p) AS mantras,
               sum(CASE WHEN r.attribution_precision = 'PER_PASSAGE' THEN 1 ELSE 0 END)
                 AS source_stated
        ORDER BY mantras DESC LIMIT 15
        """,
        parameters={"key": AGNI},
        caveat=(
            "The `mantras` and `source_stated` columns can rank differently: 95.5% of "
            "HAS_RISHI is sukta-inherited. Prefer source_stated for a defensible claim."
        ),
        serves=(2, 19),
    ),
    DomainQuery(
        name="rishis_invoking_deity_strict",
        question="Which seers does the source itself name for this deity's mantras?",
        cypher="""
        MATCH (p:Passage)-[d:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[r:HAS_RISHI]->(rs:Rishi)
        WHERE d.attribution_precision = 'PER_PASSAGE'
          AND r.attribution_precision = 'PER_PASSAGE'
        RETURN rs.display_label AS rishi, count(DISTINCT p) AS mantras
        ORDER BY mantras DESC LIMIT 15
        """,
        parameters={"key": AGNI},
        caveat="Strict: both attributions source-stated. Small result sets are expected.",
        serves=(2, 19, 29),
    ),
    DomainQuery(
        name="deity_epithets",
        question="Which epithets does the graph record, and for whom?",
        cypher="""
        MATCH (dv:Devata)-[:HAS_EPITHET]->(ep:Epithet)
        RETURN dv.display_label AS deity, collect(ep.display_label) AS epithets
        ORDER BY size(epithets) DESC, deity
        """,
        caveat=(
            "Curated for major deities only (13 epithets total), so absence means "
            "uncurated rather than unattested."
        ),
        serves=(42,),
    ),
    DomainQuery(
        name="natural_phenomena_personified",
        question="Which natural phenomena does the corpus treat as deities?",
        cypher="""
        MATCH (dv:Devata)-[:DEVATA_ASSOCIATED_WITH]->(n:NaturalPhenomenon)
        RETURN dv.display_label AS deity, dv.axes AS axes,
               collect(n.display_label) AS phenomena
        ORDER BY deity
        """,
        caveat=(
            "Association, not identity. The registry refuses IS_GOD_OF and REPRESENTS by "
            "name: 'Agni is associated with fire' is recorded, 'Agni is the fire god' is not."
        ),
        serves=(41, 46),
    ),
    # ------------------------------------------------------- material culture
    DomainQuery(
        name="crops_by_veda",
        question="Which crops occur in each Veda?",
        cypher="""
        MATCH (p:Passage)-[m:MENTIONS_ENTITY]->(c:Crop)
        RETURN c.display_label AS crop, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY crop, mantras DESC
        """,
        caveat=(
            "Lexical mentions on Sanskrit evidence. A mention is not a claim that the "
            "passage is about agriculture."
        ),
        serves=(9, 48),
    ),
    DomainQuery(
        name="metals_by_veda",
        question="Which metals occur in each Veda?",
        cypher="""
        MATCH (p:Passage)-[m:MENTIONS_ENTITY]->(x:Metal)
        RETURN x.display_label AS metal, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(DISTINCT m.matched_aliases)[0..3] AS sample_aliases
        ORDER BY metal, mantras DESC
        """,
        caveat=(
            "The bare stem `ayas` was rejected as an alias: it token-matches nothing and "
            "substring-matches 645 times inside payasa/madayasva. Only inflected forms "
            "that occur as whole words are used, so recall is deliberately conservative."
        ),
        serves=(10,),
    ),
    DomainQuery(
        name="animals_by_veda",
        question="Which animals occur in each Veda?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(a:Animal)
        RETURN a.display_label AS animal, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY animal, mantras DESC
        """,
        caveat="Lexical mentions only.",
        serves=(11, 48),
    ),
    DomainQuery(
        name="animals_with_wealth",
        question="Which animals co-occur with wealth vocabulary?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(a:Animal)
        MATCH (p)-[:MENTIONS_ENTITY]->(w:DomainEntity)
        WHERE w.entity_key IN $wealth
        RETURN a.display_label AS animal, w.display_label AS wealth_term,
               count(DISTINCT p) AS mantras
        ORDER BY mantras DESC LIMIT 20
        """,
        parameters={
            "wealth": ["VG:CONCEPT:VASU-WEALTH", "VG:CONCEPT:HIRANYA-GOLD"]
        },
        caveat=(
            "Co-occurrence in one mantra, not a stated relation. Cattle-as-wealth is a "
            "real Vedic association, but this query measures adjacency only."
        ),
        serves=(11, 48),
    ),
    DomainQuery(
        name="weapons_and_deities",
        question="Which weapons and objects belong to which deity's narratives?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(w:Object)
        MATCH (p)-[:HAS_DEVATA]->(dv:Devata)
        RETURN w.display_label AS object, w.display_type AS kind,
               dv.display_label AS deity, count(DISTINCT p) AS mantras
        ORDER BY mantras DESC LIMIT 25
        """,
        caveat=_SCOPE_CAVEAT + " " + _INHERIT_CAVEAT + " Co-occurrence, not possession.",
        serves=(25, 40),
    ),
    DomainQuery(
        name="ritual_objects_recurring",
        question="Which ritual objects recur most?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(o:Object)
        RETURN o.display_label AS object, count(DISTINCT p) AS mantras,
               count(DISTINCT p.veda) AS vedas
        ORDER BY mantras DESC
        """,
        caveat="Lexical mentions only.",
        serves=(25, 40),
    ),
    DomainQuery(
        name="rivers_mentioned",
        question="Which rivers does the corpus name, and where?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r:River)
        RETURN r.display_label AS river, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY river, mantras DESC
        """,
        caveat=(
            "There is deliberately no Sarasvati RIVER node: its forms match 172 mantras "
            "of which the great majority are the goddess, and a river node claiming them "
            "would assert 'this passage is about a river' of passages about a deity. "
            "Ancient names are not mapped to modern identifications."
        ),
        serves=(26,),
    ),
    DomainQuery(
        name="tribes_mentioned",
        question="Which tribes and clans does the corpus name, and where?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(t:Tribe)
        RETURN t.display_label AS tribe, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..5] AS examples
        ORDER BY mantras DESC
        """,
        caveat=(
            "Five tribes, 42 mentions. Published separately from rivers_and_tribes "
            "because the join of the two is empty: the tribes are attested and the "
            "rivers are attested, and they never share a mantra in this corpus."
        ),
        serves=(26,),
    ),
    DomainQuery(
        name="rivers_and_tribes",
        question="Which rivers occur with which tribes or clans?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r:River)
        MATCH (p)-[:MENTIONS_ENTITY]->(t:Tribe)
        RETURN r.display_label AS river, t.display_label AS tribe,
               count(DISTINCT p) AS mantras, collect(p.canonical_citation)[0..4] AS examples
        ORDER BY mantras DESC LIMIT 20
        """,
        caveat=(
            "Returns nothing, and that is a measured result rather than a missing "
            "feature: 42 tribe mentions and 12 river mentions exist, and no mantra "
            "carries one of each. Question 26 is therefore not answerable by "
            "co-occurrence in this corpus. See tribes_mentioned and rivers_mentioned."
        ),
        serves=(26,),
    ),
    # ---------------------------------------------------- Atharvaveda concerns
    DomainQuery(
        name="human_concerns_by_veda",
        question="Which human concerns does each Veda address?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(h:HumanConcern)
        RETURN h.display_label AS concern, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY concern, mantras DESC
        """,
        caveat=(
            "A passage naming a concern is evidence it concerns it, not that it prescribes "
            "a remedy for it."
        ),
        serves=(13, 14, 15, 16, 32, 47, 48),
    ),
    DomainQuery(
        name="conditions_treated",
        question="Which afflictions do passages address, and in which Veda?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(c:Condition)
        RETURN c.display_label AS condition, p.veda AS veda,
               count(DISTINCT p) AS mantras
        ORDER BY condition, mantras DESC
        """,
        caveat=(
            "Naming an affliction is weaker than treating it. There is deliberately no "
            "separate 'fever' entity: takman- forms sit in YAKSMA-DISEASE because "
            "splitting them would have put 39% of the paradigm under 'fever' and 61% "
            "under 'disease' invisibly."
        ),
        serves=(12, 15, 47),
    ),
    DomainQuery(
        name="condition_neighbourhood",
        question="What surrounds one affliction in the Atharvaveda: plants, objects, others?",
        cypher="""
        MATCH (p:Passage {veda: 'AV'})-[:MENTIONS_ENTITY]->(c:Condition {entity_key: $condition})
        OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(pl:Plant)
        OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(ob:Object)
        OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(other:Condition)
          WHERE other.entity_key <> $condition
        RETURN p.canonical_citation AS passage,
               collect(DISTINCT pl.display_label) AS plants,
               collect(DISTINCT ob.display_label) AS objects,
               collect(DISTINCT other.display_label) AS other_conditions
        ORDER BY passage LIMIT 25
        """,
        parameters={"condition": "VG:CONCEPT:VISA-POISON"},
        caveat=(
            "Co-occurrence within a mantra; no causal or prescriptive claim. Keyed on a "
            "Condition rather than on a healing HumanConcern because the registry has no "
            "healing concern entity: bhesaja was not curated, so passages about healing "
            "are reachable only through the afflictions and plants named in them."
        ),
        serves=(12, 15, 47),
    ),
    DomainQuery(
        name="social_rites",
        question="Which passages concern marriage, childbirth and funerary rites?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(s:SocialRite)
        RETURN s.display_label AS rite, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..5] AS examples
        ORDER BY rite, mantras DESC
        """,
        caveat=(
            "AV 14 redacts RV 10.85, so marriage vocabulary is not exclusively "
            "Atharvavedic and the RV share is real rather than noise."
        ),
        serves=(13, 14),
    ),
    DomainQuery(
        name="medicinal_plants",
        question="Which plants are named, and alongside which afflictions?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(pl:Plant)
        OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(c:Condition)
        RETURN pl.display_label AS plant, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(DISTINCT c.display_label) AS co_conditions
        ORDER BY mantras DESC
        """,
        caveat="Co-occurrence, not pharmacology.",
        serves=(47,),
    ),
    # ------------------------------------------------------------------ ritual
    DomainQuery(
        name="ritual_profile",
        question="What does a ritual involve: deities, offerings, objects, purpose?",
        cypher="""
        MATCH (r:Ritual)
        OPTIONAL MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r)
        OPTIONAL MATCH (r)-[:USES_OFFERING]->(off:Offering)
        OPTIONAL MATCH (r)-[:USES_SUBSTANCE]->(sub:Substance)
        OPTIONAL MATCH (r)-[:USES_OBJECT]->(ob:Object)
        OPTIONAL MATCH (r)-[:INVOKES_DEVATA]->(dv:Devata)
        RETURN r.display_label AS ritual, count(DISTINCT p) AS mantras,
               collect(DISTINCT off.display_label) AS offerings,
               collect(DISTINCT sub.display_label) AS substances,
               collect(DISTINCT ob.display_label) AS objects,
               collect(DISTINCT dv.display_label) AS deities
        ORDER BY mantras DESC
        """,
        caveat=(
            "Ritual structure is curated and thin by design: elaborate procedure is "
            "largely post-Samhita and was not imported into Samhita passages."
        ),
        serves=(5, 32, 39),
    ),
    DomainQuery(
        name="agni_and_indra_together",
        question="Which passages address both Agni and Indra?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $dual})
        RETURN 'dual entity indragni' AS route, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..6] AS examples
        UNION ALL
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $a})
        MATCH (p)-[:HAS_DEVATA]->(:Devata {entity_key: $b})
        RETURN 'both singly attributed' AS route, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..6] AS examples
        """,
        parameters={"a": AGNI, "b": INDRA, "dual": "VG:DEVATA:INDRAGNI"},
        caveat=(
            "The second route returns zero, and that is the finding rather than a gap: "
            "only 6 of 10,552 Rigvedic mantras carry more than one attributed deity, "
            "because the Anukramani names one addressee per mantra. Where the tradition "
            "means the pair it uses a dual deity, which is why VG:DEVATA:INDRAGNI exists "
            "as its own entity, so co-attribution asks the wrong question of this "
            "apparatus. " + _SCOPE_CAVEAT
        ),
        serves=(5, 33),
    ),
    DomainQuery(
        name="ritual_roles",
        question="Which priestly offices does the corpus name?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(rr:RitualRole)
        RETURN rr.display_label AS role, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY role, mantras DESC
        """,
        caveat="Lexical mentions only.",
        serves=(32, 39),
    ),
    DomainQuery(
        name="substances_offered_to_deities",
        question="Which substances co-occur with which deities?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(s:Substance)
        MATCH (p)-[:HAS_DEVATA]->(dv:Devata)
        RETURN dv.display_label AS deity, s.display_label AS substance,
               count(DISTINCT p) AS mantras
        ORDER BY mantras DESC LIMIT 30
        """,
        caveat=(
            _SCOPE_CAVEAT + " " + _INHERIT_CAVEAT + " Co-occurrence, not oblation: this "
            "does not establish that the substance was offered to that deity."
        ),
        serves=(4, 31),
    ),
    # ------------------------------------------------------------- cross-Veda
    DomainQuery(
        name="sv_reuse_of_rv",
        question="Which Rigvedic verses are reused in the Samaveda, and how closely?",
        cypher="""
        MATCH (sv:Passage)-[r:REUSES_TEXT_FROM]->(rv:Passage)
        RETURN sv.canonical_citation AS samaveda, rv.canonical_citation AS rigveda,
               r.match_level AS match_level, r.quality_tier AS tier
        ORDER BY samaveda LIMIT 30
        """,
        caveat=(
            "Cross-script comparison bottoms out at SANDHI_INSENSITIVE, the weakest "
            "surface, because a Devanagari SV text and a Latin RV text share no code "
            "points. A blank match_level means the edge predates level recording."
        ),
        serves=(6, 7, 50),
    ),
    DomainQuery(
        name="cross_veda_formulas",
        question="Which formulas occur across more than one Veda?",
        cypher="""
        MATCH (f:Formula) WHERE f.cross_veda
        RETURN f.display_form AS formula, f.vedas AS vedas,
               f.occurrence_count AS occurrences, f.word_count AS words
        ORDER BY occurrences DESC LIMIT 30
        """,
        caveat="Formula identity is a normalised-string match, not a tradition of reuse.",
        serves=(8, 27),
    ),
    DomainQuery(
        name="formula_family_diffusion",
        question="How does one formula spread across the corpus?",
        cypher="""
        MATCH (p:Passage)-[:USES_FORMULA]->(f:Formula {formula_id: $formula})
        RETURN f.display_form AS formula, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..6] AS examples
        ORDER BY mantras DESC
        """,
        parameters={"formula": "VG:ENRICH:FORMULA:01ee076bd8b5c608c52c6cb6f245f7f5"},
        caveat=(
            "Default is the widest-spread formula in the corpus, pata svastibhih sada "
            "nah, occurring 93 times across all four Vedas. Formula identity is a "
            "normalised-string match, so a family is a shared wording rather than a "
            "demonstrated line of transmission."
        ),
        serves=(8, 27, 50),
    ),
    DomainQuery(
        name="conceptually_similar_not_reused",
        question="Which cross-Veda passages share ideas without sharing text?",
        cypher="""
        MATCH (a:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)<-[:MENTIONS_ENTITY]-(b:Passage)
        WHERE a.veda < b.veda
        WITH a, b, count(DISTINCT e) AS shared WHERE shared >= 3
        AND NOT (a)-[:EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|REUSES_TEXT_FROM]-(b)
        RETURN a.canonical_citation AS passage_a, b.canonical_citation AS passage_b,
               a.veda AS veda_a, b.veda AS veda_b, shared AS shared_entities
        ORDER BY shared_entities DESC LIMIT 25
        """,
        caveat=(
            "Shared vocabulary is a weak proxy for shared idea, and high-frequency "
            "entities dominate. Treat as a candidate list, not a finding."
        ),
        serves=(22, 49),
    ),
    DomainQuery(
        name="concepts_bridging_vedas",
        question="Which entities appear across the most Vedas?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
        WITH e, collect(DISTINCT p.veda) AS vedas, count(DISTINCT p) AS mantras
        RETURN e.display_label AS entity, e.display_type AS kind,
               size(vedas) AS veda_count, vedas, mantras
        ORDER BY veda_count DESC, mantras DESC LIMIT 30
        """,
        caveat="Presence, not equivalence of sense across corpora.",
        serves=(21, 34, 36),
    ),
    DomainQuery(
        name="entity_distribution_by_veda",
        question="How is each entity type distributed across the four Vedas?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
        RETURN e.display_type AS kind, p.veda AS veda, count(*) AS mentions,
               count(DISTINCT e) AS entities
        ORDER BY kind, mentions DESC
        """,
        caveat=(
            "Mention counts scale with corpus size: RV is 10,552 mantras against SV's "
            "1,844, so compare shares rather than totals."
        ),
        serves=(21, 24, 36),
    ),
    # ------------------------------------------------- evidence and provenance
    DomainQuery(
        name="claim_evidence_trace",
        question="What supports an interpretive claim, and what would refute it?",
        cypher="""
        MATCH (c:InterpretiveClaim)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(p:Passage)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY_STATISTIC]->(m:DerivedMetric)
        OPTIONAL MATCH (c)-[:CONTRADICTS]->(other:InterpretiveClaim)
        RETURN c.claim_id AS claim, c.status AS status, c.confidence AS confidence,
               c.quality_tier AS tier, c.claim_text AS text, c.falsifier AS falsifier,
               collect(DISTINCT p.canonical_citation) AS passages,
               collect(DISTINCT {metric: m.metric_name, values: m.values_json}) AS statistics,
               collect(DISTINCT other.claim_id) AS contradicts
        ORDER BY claim
        """,
        caveat=(
            "Every row here is TIER_D interpretation and permanently CANDIDATE. Two of "
            "these claims contradict each other on purpose: that is the state of the "
            "question, not an error to resolve."
        ),
        serves=(28, 29, 30),
    ),
    DomainQuery(
        name="competing_interpretations",
        question="Where does the graph record disagreement?",
        cypher="""
        MATCH (a:InterpretiveClaim)-[:CONTRADICTS]->(b:InterpretiveClaim)
        WHERE a.claim_id < b.claim_id
        RETURN a.claim_id AS claim_a, a.status AS status_a, a.confidence AS confidence_a,
               b.claim_id AS claim_b, b.status AS status_b, b.confidence AS confidence_b
        """,
        caveat="Neither side is marked as winning.",
        serves=(28,),
    ),
    DomainQuery(
        name="textual_versus_interpretive",
        question="Which of the graph's claims are textual and which are interpretation?",
        cypher="""
        MATCH ()-[r]->()
        RETURN r.quality_tier AS tier, r.knowledge_layer AS layer,
               count(*) AS edges, collect(DISTINCT type(r))[0..10] AS example_types
        ORDER BY tier, edges DESC
        """,
        caveat=(
            "TIER_C is empty by construction: the 736 model-extracted candidates are all "
            "state=CANDIDATE because there is no human gold to accept them against."
        ),
        serves=(29, 30),
    ),
    DomainQuery(
        name="attribution_precision_audit",
        question="How much attribution is source-stated versus scope-inherited?",
        cypher="""
        MATCH ()-[r:HAS_DEVATA|HAS_RISHI|HAS_CHANDAS]->()
        RETURN type(r) AS predicate, r.attribution_precision AS precision,
               count(*) AS edges
        ORDER BY predicate, edges DESC
        """,
        caveat="This is the query most worth running before trusting any deity ranking.",
        serves=(29, 30),
    ),
    DomainQuery(
        name="theonym_ambiguous_mentions",
        question="Which mentions cannot be told apart from a mention of a deity?",
        cypher="""
        MATCH (p:Passage)-[m:MENTIONS_ENTITY]->(e:DomainEntity)
        WHERE m.theonym_ambiguous
        RETURN e.display_label AS entity, e.display_type AS kind,
               count(*) AS ambiguous_mentions,
               collect(DISTINCT m.matched_aliases)[0..3] AS aliases
        ORDER BY ambiguous_mentions DESC
        """,
        caveat=(
            "An upper bound on deity/concept conflation, not a count of errors: some of "
            "these passages do mean the impersonal referent."
        ),
        serves=(29, 45, 46),
    ),
    DomainQuery(
        name="soma_deity_versus_substance",
        question="How does Soma behave as deity versus substance?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(dv:Devata)
        WHERE dv.entity_key IN $deities
        WITH collect(DISTINCT p) AS deity_passages
        MATCH (q:Passage)-[m:MENTIONS_ENTITY]->(s:Substance {entity_key: $substance})
        WITH deity_passages, collect(DISTINCT q) AS substance_passages
        RETURN size(deity_passages) AS as_deity_attributed,
               size(substance_passages) AS as_substance_mentioned,
               size([x IN substance_passages WHERE x IN deity_passages]) AS both,
               size([x IN substance_passages WHERE NOT x IN deity_passages])
                 AS substance_only
        """,
        parameters={
            "deities": [SOMA, "VG:DEVATA:PAVAMANAH-SOMAH"],
            "substance": "VG:CONCEPT:SOMA-DRINK",
        },
        caveat=(
            "The deity side is Rigveda-only; the substance side spans four Vedas, so "
            "`substance_only` is inflated by that asymmetry rather than by usage."
        ),
        serves=(17, 45),
    ),
    DomainQuery(
        name="agni_deity_fire_medium",
        question="How does Agni behave as deity, as fire, and as ritual medium?",
        cypher="""
        MATCH (dv:Devata {entity_key: $deity})
        OPTIONAL MATCH (dv)-[:HAS_AXIS]->(ax:DeityAxis)
        WITH dv, collect(DISTINCT ax.axis) AS axes
        CALL (dv) {
            MATCH (p:Passage)-[:HAS_DEVATA]->(dv)
            RETURN count(DISTINCT p) AS attributed_mantras
        }
        CALL () {
            MATCH (q:Passage)-[m:MENTIONS_ENTITY]->(:NaturalPhenomenon {entity_key: $fire})
            RETURN count(DISTINCT q) AS fire_mentions,
                   sum(CASE WHEN m.theonym_ambiguous THEN 1 ELSE 0 END)
                     AS ambiguous_fire_mentions
        }
        RETURN dv.display_label AS deity, axes, attributed_mantras, fire_mentions,
               ambiguous_fire_mentions
        """,
        parameters={"deity": AGNI, "fire": "VG:CONCEPT:AGNI-FIRE"},
        caveat=(
            "The corpus does not lexically distinguish the deity from the element -- both "
            "are the word agni -- so the split between these columns is an editorial "
            "convenience. See VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED. The two counts are "
            "computed in separate CALL subqueries because they are independent: stacking "
            "them as OPTIONAL MATCH multiplied 3 axes by 1,988 attributed passages by "
            "2,206 fire mentions and took 9.5 seconds to return one row."
        ),
        serves=(20, 46),
    ),
    DomainQuery(
        name="rudra_profile_no_shiva",
        question="What is Rudra's corpus profile, without importing later identity?",
        cypher="""
        MATCH (dv:Devata {entity_key: $key})
        OPTIONAL MATCH (dv)-[:HAS_AXIS]->(ax:DeityAxis)
        OPTIONAL MATCH (p:Passage)-[r:HAS_DEVATA]->(dv)
        RETURN dv.display_label AS deity, dv.structure AS structure,
               collect(DISTINCT ax.axis) AS axes, dv.short_description AS description,
               count(DISTINCT p) AS attributed_mantras,
               sum(CASE WHEN r.attribution_precision = 'PER_PASSAGE' THEN 1 ELSE 0 END)
                 AS source_stated,
               collect(DISTINCT p.veda) AS vedas
        """,
        parameters={"key": RUDRA},
        caveat=(
            "No Siva identification is asserted anywhere in the graph. Rudra's later "
            "identification with Siva is post-Vedic and recording it here would dress a "
            "historical claim as a textual fact."
        ),
        serves=(43,),
    ),
    # -------------------------------------------------------------- integrity
    DomainQuery(
        name="product_graph_census",
        question="What does the product graph contain, excluding internal plumbing?",
        cypher=f"""
        MATCH (n) WHERE {_NOT_INTERNAL}
        UNWIND labels(n) AS label
        WITH label, count(DISTINCT n) AS nodes
        WHERE NOT label IN ['DomainEntity', 'Mantra']
        RETURN label, nodes ORDER BY nodes DESC
        """,
        caveat="DomainEntity and Mantra are marker/sublabels and would double-count.",
        serves=(),
    ),
    DomainQuery(
        name="internal_leakage_check",
        question="Does any internal diagnostic node reach product traversal?",
        cypher=f"""
        MATCH (n:{LABEL_INTERNAL})
        UNWIND labels(n) AS label
        WITH label WHERE NOT label IN
          ['{LABEL_INTERNAL}', 'QAIssue', 'TextVersion', 'Translation', 'Source',
           'SourceArtifact']
        RETURN label, count(*) AS leaked_nodes
        """,
        caveat="An empty result is the pass condition.",
        serves=(),
    ),
    DomainQuery(
        name="orphan_domain_entities",
        question="Which domain entities have no edge at all?",
        cypher="""
        MATCH (e:DomainEntity)
        WHERE NOT (e)--()
        RETURN e.entity_key AS entity, e.display_type AS kind, e.display_label AS label
        ORDER BY kind, entity
        """,
        caveat=(
            "An orphan is either an entity whose aliases match nothing, or one awaiting "
            "curated edges. Both are reportable; neither is automatically a defect."
        ),
        serves=(),
    ),
    DomainQuery(
        name="unlabelled_product_nodes",
        question="Does any product node lack a human-readable label?",
        cypher=f"""
        MATCH (n) WHERE {_NOT_INTERNAL}
          AND (n.display_label IS NULL OR trim(toString(n.display_label)) IN
               ['', 'UNKNOWN', 'Unknown', 'unknown', 'NULL', 'null', 'None', '?', '-'])
        RETURN labels(n) AS labels, count(*) AS nodes ORDER BY nodes DESC
        """,
        caveat="An empty result is the pass condition (UNKNOWN_LABEL_RATE = 0).",
        serves=(),
    ),
    DomainQuery(
        name="devata_taxonomy_coverage",
        question="How much of the deity taxonomy is real, and how much is UNSPECIFIED?",
        cypher="""
        MATCH (dv:Devata)
        RETURN dv.structure AS structure,
               sum(CASE WHEN dv.is_classified THEN 1 ELSE 0 END) AS with_axes,
               sum(CASE WHEN dv.is_classified THEN 0 ELSE 1 END) AS unspecified,
               count(*) AS total
        ORDER BY total DESC
        """,
        caveat=(
            "UNSPECIFIED is a deliberate value, not a gap to be filled: a justified "
            "UNSPECIFIED is worth more than an invented axis."
        ),
        serves=(),
    ),
)

QUERIES_BY_NAME: Final[dict[str, DomainQuery]] = {q.name: q for q in QUERIES}

assert len(QUERIES_BY_NAME) == len(QUERIES), "duplicate query name"


def questions_served() -> dict[int, list[str]]:
    """Killer-question number to the queries that address it."""
    served: dict[int, list[str]] = {}
    for query in QUERIES:
        for number in query.serves:
            served.setdefault(number, []).append(query.name)
    return dict(sorted(served.items()))
