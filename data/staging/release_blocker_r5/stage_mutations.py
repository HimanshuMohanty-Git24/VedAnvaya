"""Stage every R5 graph mutation. Reads the live store; writes only JSON under this directory.

One module rather than nine, because §14 of the brief requires ONE immutable integrated
migration plan and a plan assembled from nine independently-shaped files is a plan whose
promised totals nobody can recompute. Each ``stage_*`` function owns one gap, returns its
rows, and states its own falsifier in its docstring.

Nothing here executes a write. ``apply_migration.py`` is the only writer.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))

from vedagraph.domain.translation_semantics import (  # noqa: E402
    INDEPENDENT_ENGLISH_STATES,
    UNCOVERED_STATES,
    VerseCoverageState,
    verse_coverage_state,
)
from vedagraph.enrich.concepts import fold_alias  # noqa: E402
from vedagraph.enrich.surfaces import render_for_display  # noqa: E402

import _q  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
SPRINT = HERE.parents[0] / "final_closure_sprint"

CONTRACT = "VG:R5_CLOSURE:V1"


# ---------------------------------------------------------------------------
# GAP-SEMANTICS-003
# ---------------------------------------------------------------------------


def stage_semantics_003(session) -> dict[str, Any]:
    """Project the RoleFiller resolution onto the assertion.

    The closure test wants an assertion carrying agent + predicate + target, and at least
    one non-Devata target. Both read 0. The ontology range on ``ASSERTION_AGENT`` and
    ``ASSERTION_TARGET`` ALREADY admits ``:DomainEntity`` (ontology.py:1176-1187), so
    nothing needs widening in the schema -- the slots are unpopulated, not undeclared.

    The resolution exists one hop away and was never lifted: ``ASSERTION_ROLE`` reaches
    2,052 ``:RoleFiller`` nodes and 348 of those carry a ``REFERS_TO`` edge to a registered
    entity, derived ``TREEBANK_DEPREL`` from DCS dependency relations at TIER_B with the
    conllu sent_id on the edge.

    Only two roles are projected. ``AGENT`` becomes ``ASSERTION_AGENT`` and ``PATIENT``
    becomes ``ASSERTION_TARGET``. BENEFICIARY, GOAL, INSTRUMENT, LOCATION and SOURCE are
    deliberately NOT folded into the target slot: they are distinct roles already carried
    on ``ASSERTION_ROLE``, and collapsing them into "target" is exactly the tier-and-role
    blending the entry's implementation_dependency warns against.

    FALSIFIER: if the projected edge count does not equal the number of
    (assertion, role, resolved entity) triples the read query returns, the projection has
    either duplicated or dropped rows and must not be applied.
    """
    rows = _q.rows(
        session,
        """
        MATCH (a:SemanticAssertion)-[r:ASSERTION_ROLE]->(f:RoleFiller)-[ref:REFERS_TO]->(e)
        WHERE r.role IN ['AGENT', 'PATIENT'] AND a.assertion_key IS NOT NULL
        RETURN a.assertion_key           AS assertion_key,
               a.derivation              AS assertion_derivation,
               r.role                    AS role,
               f.role_filler_key         AS role_filler_key,
               f.surface                 AS surface,
               f.lemma                   AS lemma,
               f.case                    AS grammatical_case,
               coalesce(e.entity_key, e.concept_key) AS entity_key,
               labels(e)                 AS entity_labels,
               ref.evidence              AS evidence,
               ref.quality_tier          AS quality_tier,
               ref.knowledge_layer       AS knowledge_layer,
               ref.evidence_basis        AS evidence_basis,
               ref.derivation            AS role_derivation,
               ref.source_id             AS source_id,
               ref.canonical_key         AS canonical_key
        ORDER BY assertion_key, role, entity_key
        """,
    )
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for r in rows:
        rel = "ASSERTION_AGENT" if r["role"] == "AGENT" else "ASSERTION_TARGET"
        ident = (r["assertion_key"], rel, r["entity_key"])
        if ident in seen:
            continue
        seen.add(ident)
        edges.append(
            {
                "rel_type": rel,
                "assertion_key": r["assertion_key"],
                "entity_key": r["entity_key"],
                "entity_is_devata": "Devata" in (r["entity_labels"] or []),
                "properties": {
                    # The projected edge is exactly as good as the RoleFiller resolution it
                    # comes from and no better, so it carries that row's own tier rather
                    # than the assertion's.
                    "knowledge_layer": r["knowledge_layer"] or "L2_DETERMINISTIC_DERIVED",
                    "quality_tier": r["quality_tier"] or "TIER_B",
                    "evidence_basis": r["evidence_basis"] or "SANSKRIT",
                    "attribution_precision": "NOT_AN_ATTRIBUTION",
                    "derivation": "TREEBANK_DEPREL_ROLE_PROJECTION",
                    "projected_from_role": r["role"],
                    "projected_from_role_filler_key": r["role_filler_key"],
                    "role_derivation": r["role_derivation"] or "TREEBANK_DEPREL",
                    "evidence": r["evidence"],
                    "source_id": r["source_id"],
                    "surface": r["surface"],
                    "lemma": r["lemma"],
                    "grammatical_case": r["grammatical_case"],
                    "grade_basis": (
                        "projected from the assertion's own ASSERTION_ROLE filler, whose "
                        "REFERS_TO resolution to a registered entity carries the DCS "
                        "dependency evidence on the edge"
                    ),
                    "r5_contract": CONTRACT,
                },
            }
        )

    by_rel = collections.Counter(e["rel_type"] for e in edges)
    non_devata_targets = sum(
        1 for e in edges if e["rel_type"] == "ASSERTION_TARGET" and not e["entity_is_devata"]
    )
    agents = {e["assertion_key"] for e in edges if e["rel_type"] == "ASSERTION_AGENT"}
    targets = {e["assertion_key"] for e in edges if e["rel_type"] == "ASSERTION_TARGET"}
    with_predicate = {
        r["assertion_key"]
        for r in _q.rows(
            session,
            "MATCH (a:SemanticAssertion)-[:ASSERTION_PREDICATE]->() "
            "WHERE a.assertion_key IS NOT NULL RETURN a.assertion_key AS assertion_key",
        )
    }
    slot_full = agents & targets & with_predicate

    return {
        "gap_id": "GAP-SEMANTICS-003",
        "edges": edges,
        "promised": {
            "relationships_created": dict(by_rel),
            "total_relationships_created": len(edges),
        },
        "measured_before": {
            "assertions_with_all_three_slots": 0,
            "non_devata_assertion_target_edges": 0,
        },
        "predicted_after": {
            "assertions_with_all_three_slots": len(slot_full),
            "non_devata_assertion_target_edges": non_devata_targets,
        },
        "falsifier": {
            "triples_read": len(rows),
            "edges_after_dedup": len(edges),
            "duplicate_triples_collapsed": len(rows) - len(edges),
            "identity_property": "assertion_key",
            "why_not_assertion_id": (
                "assertion_id is NULL on all 1,532 TREEBANK_DEPREL assertions and populated on "
                "only 4,865 of 35,131 overall. Keying on it collapsed 277 triples into 90 -- a "
                "defect this falsifier caught in my own staging before anything was applied. "
                "assertion_key is present on all 1,532 and is the passage key plus the "
                "assertion ordinal."
            ),
        },
        "roles_deliberately_not_projected": [
            "BENEFICIARY",
            "GOAL",
            "INSTRUMENT",
            "LOCATION",
            "SOURCE",
        ],
        "why": (
            "Those five are distinct roles already carried on ASSERTION_ROLE. Folding them "
            "into the target slot would make 'target' mean five different things and is the "
            "blending the entry's implementation_dependency names."
        ),
    }


# ---------------------------------------------------------------------------
# GAP-ENTITY_COVERAGE-006
# ---------------------------------------------------------------------------

#: The applicability vocabulary. Mapped onto the R4 ``lexical_recall_status`` values rather
#: than invented beside them, so one row cannot carry two disagreeing answers.
APPLICABILITY = {
    "MEASURED_AGAINST_RV_ANNOTATION": "LEXICAL_RECOVERY_APPLICABLE",
    "UNMEASURED_NO_REGISTERED_SANSKRIT_ALIAS": "NOT_APPLICABLE",
    "UNMEASURED_NO_ANNOTATION_ANCHOR": "INSUFFICIENT_EVIDENCE",
}


def stage_entity_006(session) -> dict[str, Any]:
    """Type recall applicability per entity, and make the recall metric say what it counts.

    Clause 2 is ``NO_LEXICAL_MATCH`` and must stay 0: ayas is source-attested at
    VG:YV:VSM:A18:V013 and the token there is a sandhi-elided avagraha plus ``yas``, which
    the search fold reduces to ``yasca`` -- indistinguishable from the relative pronoun and
    from ``girayasca``/``parvatasca``/``vanaspatayasca`` standing in the same line. No alias
    is registered for it and the matcher is not weakened.

    Clause 1 asks that "every entity carries a measured recall figure with its sample size".
    164 of 384 do. The other 220 cannot: 155 register no Sanskrit alias at all and 65
    register one that folds onto no annotated lemma. A single recall figure over 384 would
    therefore be a coverage claim the layer cannot support -- this project's own recorded
    lesson is that a validator which silently skips is worse than none, and that coverage
    must be reported, not just precision.

    So the denominator is REPLACED by a typed one rather than redefined to close the gap:
    every entity carries an applicability class, and the layer-level metric reports eligible
    / tested / matched / attested-outside-lexical-recoverability as four separate figures.

    FALSIFIER: if any entity ends with an applicability class that disagrees with its
    existing ``lexical_recall_status``, or if the four figures do not sum to 384, the typing
    is wrong and must not be applied.
    """
    rows = _q.rows(
        session,
        """
        MATCH (n:DomainEntity)
        RETURN n.entity_key                AS entity_key,
               n.lexical_recall_status     AS status,
               n.lexical_recall            AS recall,
               n.lexical_recall_matched    AS matched,
               n.lexical_recall_sample_size AS sample_size,
               size([(n)<-[:ATTESTED_IN]-()|1]) AS attested_in_in,
               size([(n)-[:ATTESTED_IN]->()|1]) AS attested_in_out
        ORDER BY entity_key
        """,
    )
    attested = {
        r["entity_key"]
        for r in _q.rows(
            session,
            """
            MATCH (e:DomainEntity)-[r:ATTESTED_IN]->(:Passage)
            WHERE r.lexical_match = 'NOT_SAFELY_RECOVERABLE'
               OR r.attestation_basis = 'SOURCE_ATTESTED_NONLEXICAL'
            RETURN e.entity_key AS entity_key
            """,
        )
    }
    updates: list[dict[str, Any]] = []
    disagreements: list[str] = []
    for r in rows:
        cls = APPLICABILITY.get(r["status"])
        if cls is None:
            disagreements.append(f"{r['entity_key']}: unmapped status {r['status']!r}")
            continue
        # A source attestation outside lexical recoverability overrides the lexical class:
        # a zero lexical match on a verse we have READ the entity in is not an absence.
        if r["entity_key"] in attested:
            cls = "SOURCE_ATTESTED_NONLEXICAL"
        updates.append(
            {
                "entity_key": r["entity_key"],
                "properties": {
                    "recall_applicability": cls,
                    "recall_applicability_contract": "VG:ENTITY_RECALL_APPLICABILITY:V1",
                    "recall_applicability_basis": (
                        "derived from lexical_recall_status, with a graph-level ATTESTED_IN "
                        "carrying lexical_match=NOT_SAFELY_RECOVERABLE taking precedence"
                    ),
                    "r5_contract": CONTRACT,
                },
            }
        )
    dist = collections.Counter(u["properties"]["recall_applicability"] for u in updates)
    tested = [r for r in rows if r["status"] == "MEASURED_AGAINST_RV_ANNOTATION"]
    metric = {
        "metric_key": "VG:METRIC:ENTITY_LEXICAL_RECALL:V2",
        "registry_population": len(rows),
        "eligible_denominator": dist.get("LEXICAL_RECOVERY_APPLICABLE", 0),
        "tested_population": len(tested),
        "true_positives_matched_tokens": sum(int(r["matched"] or 0) for r in tested),
        "tested_sample_tokens": sum(int(r["sample_size"] or 0) for r in tested),
        "source_attested_outside_lexical_recoverability": dist.get(
            "SOURCE_ATTESTED_NONLEXICAL", 0
        ),
        "not_applicable_no_registered_sanskrit_alias": dist.get("NOT_APPLICABLE", 0),
        "insufficient_evidence_no_annotation_anchor": dist.get("INSUFFICIENT_EVIDENCE", 0),
        "scope": "RV_ONLY_ANNOTATION_COVERS_NO_OTHER_CORPUS",
        "what_this_is_not": (
            "This is NOT a recall figure over 384 entities. A single ratio over the whole "
            "registry would silently price 220 entities the lexical layer cannot test as "
            "either matched or missed, and they are neither. The eligible denominator, the "
            "tested population and the untestable classes are reported separately so a "
            "reader cannot construct the ratio the layer does not support."
        ),
    }
    metric["classes_sum_to_population"] = (
        metric["eligible_denominator"]
        + metric["source_attested_outside_lexical_recoverability"]
        + metric["not_applicable_no_registered_sanskrit_alias"]
        + metric["insufficient_evidence_no_annotation_anchor"]
    ) == metric["registry_population"]
    # The applicability classes PARTITION the registry, so they sum to 384. The tested
    # population does not sit inside one class: ayas is lexically tested against the RV
    # annotation AND source-attested outside lexical recoverability in the YV, so it is
    # classed SOURCE_ATTESTED_NONLEXICAL and still contributes a tested row. Stated, so
    # that eligible_denominator < tested_population does not read as an arithmetic error.
    metric["tested_population_also_counted_under_source_attested"] = sum(
        1
        for u in updates
        if u["properties"]["recall_applicability"] == "SOURCE_ATTESTED_NONLEXICAL"
        and u["entity_key"] in {r["entity_key"] for r in rows if r["status"] == "MEASURED_AGAINST_RV_ANNOTATION"}
    )
    metric["why_tested_exceeds_eligible"] = (
        "An entity may be both lexically testable and source-attested outside lexical "
        "recoverability. ayas is: its RV recall is measured at 7 of 13 tokens, and its "
        "Yajurvedic occurrence at VG:YV:VSM:A18:V013 is real and not lexically recoverable. "
        "The applicability class records the STRONGER fact, so the row leaves the eligible "
        "denominator while remaining in the tested population."
    )
    return {
        "gap_id": "GAP-ENTITY_COVERAGE-006",
        "node_updates": updates,
        "layer_metric": metric,
        "applicability_distribution": dict(dist),
        "promised": {"nodes_updated": len(updates), "nodes_created": 0, "relationships_created": 0},
        "falsifier": {
            "unmapped_statuses": disagreements,
            "classes_sum_to_population": metric["classes_sum_to_population"],
        },
        "ayas_cell": {
            "measure": "MATCH (m:Mantra {veda:'YV'})-[:MENTIONS_ENTITY]->(e) WHERE e.entity_key='VG:CONCEPT:AYAS-METAL' RETURN count(DISTINCT m)",
            "value": 0,
            "required_to_stay": 0,
            "why": (
                "Source-attested and lexically unrecoverable. Forcing it positive needs an "
                "alias that manufactures false positives inside the witness verse itself."
            ),
        },
    }


# ---------------------------------------------------------------------------
# GAP-ENTITY_COVERAGE-007
# ---------------------------------------------------------------------------

#: Multi-word phrase aliases to register, with the attested locus each was read at. Every
#: one was confirmed to occur as a run of consecutive folded tokens by probe_phrase_match2,
#: and every one's host-run audit shows it reaching only itself.
PHRASE_ALIASES: dict[str, list[str]] = {
    "VG:CONCEPT:TRTIYA-SAVANA-THIRD-PRESSING": [
        "tṛtīye savane",
        "tṛtīye savana",
        "tṛtīyaṃ savanaṃ",
        "tṛtīyaṃ savanam",
    ],
    "VG:CONCEPT:MADHYANDINA-SAVANA-MIDDAY-PRESSING": [
        "mādhyaṃdine savane",
        "mādhyandine savana",
    ],
}


def stage_entity_007(session) -> dict[str, Any]:
    """Phrase matching for multi-word entities, and evidence spans on the 13 personifications.

    Clause 2 closed at R4: all 13 ``:NaturalPhenomenon`` carry a typed
    ``personification_status`` and 0 are null.

    Clause 1 is the open one. Exactly 2 ``:DomainEntity`` carry a multi-word Sanskrit label
    and the mention layer matches whole single tokens, so no phrase can fire. The registry
    entry for the third pressing documents the consequence itself: "All six were read and
    all six are this act -- and none of them is reachable, because the third pressing is the
    only one of the three the corpus never writes as one word."

    FALSIFIER, stated before the test and run in probe_phrase_match2.py: a phrase pass is
    only worth building if the phrases occur. A first probe over the LEMMA forms measured
    zero; that zero was my own query's, not the corpus's, because the registry registers
    inflections. Re-run over the attested inflected forms with a positive control
    (``agnim īḷe``, 6 hits) the phrase pass reaches 6 mantras for the third pressing --
    RV 3.28.5, RV 4.34.4, RV 4.35.9, RV 8.57.1, AV 6.47.3, AV 9.1.13 -- which is EXACTLY the
    six loci the registry named as read-but-unreachable, and no seventh.
    """
    search = _q.rows(
        session,
        """
        MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(t:TextVersion)
        WHERE t.text_role = 'SEARCH_DERIVATIVE'
        RETURN m.canonical_key AS key, m.veda AS veda, t.text_nfc AS text
        """,
    )
    existing = {
        (r["entity_key"], r["passage_key"])
        for r in _q.rows(
            session,
            """
            MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
            WHERE e.entity_key IN $keys
            RETURN e.entity_key AS entity_key, p.canonical_key AS passage_key
            """,
            keys=list(PHRASE_ALIASES),
        )
    }

    folded = {
        key: {p: " ".join(fold_alias(w) for w in p.split()) for p in phrases}
        for key, phrases in PHRASE_ALIASES.items()
    }
    mentions: list[dict[str, Any]] = []
    host_audit: dict[str, dict[str, int]] = {}
    already_reached: list[dict[str, str]] = []
    for row in search:
        joined = " ".join((row["text"] or "").split())
        for entity_key, phrases in folded.items():
            for phrase, target in phrases.items():
                if not target or " " not in target:
                    continue
                pos = joined.find(target)
                if pos < 0:
                    continue
                if not (pos == 0 or joined[pos - 1] == " "):
                    continue
                end = pos + len(target)
                if not (end == len(joined) or joined[end] == " "):
                    continue
                audit_key = f"{entity_key}|{phrase}"
                host = render_for_display(joined[pos:end])
                host_audit.setdefault(audit_key, {})
                host_audit[audit_key][host] = host_audit[audit_key].get(host, 0) + 1
                if (entity_key, row["key"]) in existing:
                    already_reached.append(
                        {"entity_key": entity_key, "passage_key": row["key"], "phrase": phrase}
                    )
                    continue
                mentions.append(
                    {
                        "passage_key": row["key"],
                        "veda": row["veda"],
                        "entity_key": entity_key,
                        "matched_phrase": phrase,
                        "properties": {
                            "knowledge_layer": "L2_DETERMINISTIC_DERIVED",
                            "quality_tier": "TIER_B",
                            "evidence_basis": "SANSKRIT",
                            "attribution_precision": "NOT_AN_ATTRIBUTION",
                            "method": "domain-mention-v1:sanskrit-phrase",
                            "matched_aliases": [phrase],
                            "alias_count": 1,
                            "paths": ["sanskrit-phrase"],
                            "score": 0.95,
                            "theonym_ambiguous": False,
                            "quote": render_for_display(joined[max(0, pos - 45) : end + 45]),
                            "grade_basis": (
                                "a run of consecutive whole folded tokens, matched on both "
                                "boundaries, so the phrase cannot fire inside a longer word"
                            ),
                            "r5_contract": CONTRACT,
                        },
                    }
                )

    # Deterministic per-row evidence for the personification layer.
    pers = _q.rows(
        session,
        """
        MATCH (n:NaturalPhenomenon)
        RETURN n.entity_key AS entity_key, n.personification_status AS status,
               n.personified_as AS personified_as, n.personification_status_reason AS reason
        ORDER BY entity_key
        """,
    )
    witnesses = {
        r["entity_key"]: r
        for r in _q.rows(
            session,
            """
            MATCH (n:NaturalPhenomenon)
            WHERE n.personified_as IS NOT NULL
            MATCH (p:Passage)-[:MENTIONS_ENTITY]->(n)
            MATCH (d:Devata {entity_key: n.personified_as})
            MATCH (p)-[dr]->(d)
            WHERE type(dr) IN ['MENTIONS_DEVATA', 'HAS_DEVATA']
            WITH n, p, d, type(dr) AS via
            ORDER BY p.canonical_key
            WITH n, collect({passage: p.canonical_key, via: via})[0] AS first, count(p) AS n_wit
            RETURN n.entity_key AS entity_key, first.passage AS passage, first.via AS via,
                   n_wit AS witness_count
            """,
        )
    }
    quotes = {}
    if witnesses:
        for r in _q.rows(
            session,
            """
            MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE m.canonical_key IN $keys AND t.text_role = 'SEARCH_DERIVATIVE'
            RETURN m.canonical_key AS key, t.text_nfc AS text
            """,
            keys=[w["passage"] for w in witnesses.values()],
        ):
            quotes[r["key"]] = render_for_display(" ".join((r["text"] or "").split())[:160])

    pers_updates: list[dict[str, Any]] = []
    for r in pers:
        tier = None
        if r["reason"] and "Match tier:" in r["reason"]:
            tier = r["reason"].split("Match tier:")[1].strip().rstrip(".")
        if r["status"] == "PERSONIFIED_AS_A_REGISTERED_DEVATA":
            w = witnesses.get(r["entity_key"])
            props = {
                "personification_match_basis": "DETERMINISTIC",
                "personification_match_tier": tier,
                "personification_evidence_passage": w["passage"] if w else None,
                "personification_evidence_via": w["via"] if w else None,
                "personification_evidence_witness_count": w["witness_count"] if w else 0,
                "personification_evidence_quote": quotes.get(w["passage"]) if w else None,
                "personification_evidence_reason": (
                    "A passage that names this phenomenon by its own registered alias AND "
                    "carries a dedication or naming edge to the deity the registry pairs it "
                    "with. Deterministic over two edges already in the graph; it is a "
                    "co-witness, not a source statement that the two are one being."
                    if w
                    else "No passage names this phenomenon and its paired deity together, so "
                    "the registry pairing has no in-corpus co-witness. Recorded, not inferred."
                ),
            }
        else:
            props = {
                "personification_match_basis": "UNAVAILABLE",
                "personification_match_tier": tier,
                "personification_evidence_passage": None,
                "personification_evidence_via": None,
                "personification_evidence_witness_count": 0,
                "personification_evidence_quote": None,
                "personification_evidence_reason": (
                    "This row is a REFUSAL, and the refusal is a statement about THIS "
                    "REGISTRY -- that no registered deity carries the phenomenon's stem. "
                    "There is no source phrase to ground, because no claim about the text is "
                    "being made. Phrase evidence is unavailable BY CONSTRUCTION and not by "
                    "omission."
                ),
            }
        props["personification_evidence_contract"] = "VG:PERSONIFICATION_EVIDENCE:V1"
        props["r5_contract"] = CONTRACT
        pers_updates.append({"entity_key": r["entity_key"], "properties": props})

    collisions = {k: v for k, v in host_audit.items() if len(v) > 1}
    return {
        "gap_id": "GAP-ENTITY_COVERAGE-007",
        "phrase_mentions": mentions,
        "phrase_aliases_to_register": PHRASE_ALIASES,
        "personification_updates": pers_updates,
        "promised": {
            "relationships_created": {"MENTIONS_ENTITY": len(mentions)},
            "nodes_updated": len(pers_updates) + len(PHRASE_ALIASES),
        },
        "already_reached_by_the_token_path": already_reached,
        "host_run_audit_per_alias": host_audit,
        "falsifier": {
            "aliases_reaching_more_than_their_own_form": collisions,
            "collision_free": not collisions,
            "new_mentions_by_entity": dict(
                collections.Counter(m["entity_key"] for m in mentions)
            ),
        },
        "personification_evidence_distribution": dict(
            collections.Counter(
                u["properties"]["personification_match_basis"] for u in pers_updates
            )
        ),
    }


# ---------------------------------------------------------------------------
# GAP-RITUAL-003 / -005 / -006
# ---------------------------------------------------------------------------


def stage_ritual(session) -> dict[str, Any]:
    """The three ritual gaps, against the adjudications staged by the final closure sprint.

    Historical safety rules are binding and none is broken here: ``HAS_STEP`` is not
    ``HAS_RITUAL_STEP`` and no step edge is touched; no global step order is asserted;
    PROBABLE ritual material stays excluded; the 13,187 excluded probable elements are not
    resurrected.

    RITUAL-003 clause 2. The SUBSTANCE already holds -- yupa reaches 12 mantras over 3
    Vedas including VG:YV:VSM:A19:V017 and VG:YV:VSM:A25:V029 -- but the node carries no
    ``vedas_with_matches`` and ``aliases_sa`` still lists only the original 4, so the 12
    edges are not reproducible from the registry that generates them. The 7 audited aliases
    are registered and the figure is MEASURED from the edges rather than declared.

    RITUAL-003 clause 1. mani is wired on GobhGS 3.8.6, read, with Oldenberg as an
    independent witness. dundubhi and audumbara are REFUSED on read evidence: the single
    dundubhi candidate is ``jigyuṣām iva dundubhiḥ``, a SIMILE inside a quoted mantra, and
    every one of the 91 audumbara apparatus lines is udumbara WOOD -- KatySS 17.2.8 yokes an
    udumbara-wood PLOUGH -- against a graph node defined from AVS 19.31 as an amulet. Wiring
    that sutra would assert that a plough is an amulet. Both refusals are typed on the node
    so a reader can tell a refused object from an unattempted one. No edge is minted.

    RITUAL-005 clause 2. Unsatisfiable from held evidence BECAUSE of clause 3, which forbids
    presenting co-occurrence as an asserted offering: the only rite-to-offering material is
    258 rows staged PROBABLE on one sutra naming both a rite and an offering. Under owner
    decision 39 those are non-asserted candidates, so the per-rite status is typed and the
    258 stay unimported.

    RITUAL-006 clauses 3 and 4. The precision figures exist and live only in a staging file.
    They are landed with their review level stated: the sample was adjudicated by ONE AGENT
    and ``human_reviewed`` is 0. Two figures are carried, not one, because a single figure
    would have to decide whether an unreproducible row is an error or an unknown.
    """
    out: dict[str, Any] = {"gap_ids": ["GAP-RITUAL-003", "GAP-RITUAL-005", "GAP-RITUAL-006"]}
    node_updates: list[dict[str, Any]] = []

    # --- RITUAL-003 -------------------------------------------------------
    yupa = json.loads((SPRINT / "agent4" / "yupa_alias_fix.json").read_text(encoding="utf-8"))
    live = _q.rows(
        session,
        """
        MATCH (e:DomainEntity {entity_key: 'VG:CONCEPT:YUPA-SACRIFICIAL-POST'})
        OPTIONAL MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e)
        RETURN e.aliases_sa AS aliases, collect(p.canonical_key) AS passages,
               collect(DISTINCT p.veda) AS vedas
        """,
    )[0]
    passages = sorted(p for p in live["passages"] if p)
    vedas = sorted(v for v in live["vedas"] if v)
    merged = sorted(set(live["aliases"] or []) | set(yupa["aliases_added"]))
    node_updates.append(
        {
            "entity_key": "VG:CONCEPT:YUPA-SACRIFICIAL-POST",
            "properties": {
                "aliases_sa": merged,
                "vedas_with_matches": len(vedas),
                "vedas_with_matches_list": vedas,
                "vedas_with_matches_basis": (
                    "MEASURED from the MENTIONS_ENTITY edges in the live store, not declared: "
                    f"{len(passages)} passages over {len(vedas)} Vedas."
                ),
                "mention_passages_measured": len(passages),
                "alias_host_form_audit": (
                    "Audited per alias, not per row. Every host form of every added alias is a "
                    "yupa form; no alias reaches a different word. dhariyūpīyāyāṁ (the "
                    "place-name Hariyupiya), sthūrayūpavat, aśvayūpāya and the sandhi-glued "
                    "yūpavāhāścaṣālaṃ are deliberately NOT registered."
                ),
                "r5_contract": CONTRACT,
            },
        }
    )
    adjudications = [
        json.loads(line)
        for line in (SPRINT / "agent4" / "uses_object_adjudication.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    refusals = [a for a in adjudications if a["verdict"].startswith("REJECT")]
    for adj in refusals:
        node_updates.append(
            {
                "entity_key": adj["object_key"],
                "properties": {
                    "ritual_use_status": "REFUSED_SOURCE_DOES_NOT_STATE_A_RITE_USES_IT",
                    "ritual_use_refusal_code": adj["verdict"],
                    "ritual_use_refusal_reason": adj["reason"],
                    "ritual_use_candidate_citation": adj["citation"],
                    "ritual_use_candidate_quote": adj["quote"],
                    "ritual_use_review_level": adj["review_level"],
                    "ritual_use_human_reviewed": adj["human_reviewed"],
                    "ritual_use_contract": "VG:RITUAL_OBJECT_USE:V1",
                    "r5_contract": CONTRACT,
                },
            }
        )
    accepted = [a for a in adjudications if a["verdict"].startswith("ACCEPT")]
    for adj in accepted:
        node_updates.append(
            {
                "entity_key": adj["object_key"],
                "properties": {
                    "ritual_use_status": "ASSERTED_SOURCE_STATES_USE",
                    "ritual_use_candidate_citation": adj["citation"],
                    "ritual_use_candidate_quote": adj["quote"],
                    "ritual_use_independent_witness": adj["independent_witness"],
                    "ritual_use_review_level": adj["review_level"],
                    "ritual_use_human_reviewed": adj["human_reviewed"],
                    "ritual_use_contract": "VG:RITUAL_OBJECT_USE:V1",
                    "r5_contract": CONTRACT,
                },
            }
        )
    out["ritual_003"] = {
        "yupa_vedas_with_matches": len(vedas),
        "yupa_mention_passages": len(passages),
        "yupa_vsm_19_17_matched": "VG:YV:VSM:A19:V017" in passages,
        "yupa_vsm_25_29_matched": "VG:YV:VSM:A25:V029" in passages,
        "yupa_aliases_before": len(live["aliases"] or []),
        "yupa_aliases_after": len(merged),
        "objects_asserted": [a["object_key"] for a in accepted],
        "objects_refused": [
            {"key": a["object_key"], "code": a["verdict"], "citation": a["citation"]}
            for a in refusals
        ],
        "edges_minted": 0,
        "why_no_edge_minted": (
            "The three objects the clause names by name were adjudicated against the acquired "
            "apparatus and only mani is stated by a source. Minting a dundubhi or audumbara "
            "edge would assert a simile and a plough respectively."
        ),
    }

    # --- RITUAL-005 -------------------------------------------------------
    rites = _q.rows(
        session,
        """
        MATCH (r:Ritual)
        RETURN r.entity_key AS entity_key,
               size([(r)-[:USES_OFFERING]->()|1]) AS uses_offering,
               size([(r)-[:USES_SUBSTANCE]->(:Offering)|1]) AS uses_offering_substance
        ORDER BY entity_key
        """,
    )
    # The rite-to-offering candidate population is the 258 USES_OFFERING rows of the
    # sealed ritual staging, every one mapping_confidence PROBABLE, over 58 rites. An
    # earlier draft read receives_offering_rejected.jsonl instead, which holds 7
    # DEITY-offering rejects and is a different question.
    rite_edges = HERE.parents[0] / "ritual" / "rite_edges.jsonl"
    candidate_rows = [
        json.loads(line)
        for line in rite_edges.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    probable_offering_rows = [
        r
        for r in candidate_rows
        if r.get("predicate") == "USES_OFFERING" and r.get("mapping_confidence") == "PROBABLE"
    ]
    rites_with_probable = {
        r["ritual_key"] for r in probable_offering_rows if r.get("ritual_key")
    }
    rejected_rows = probable_offering_rows
    offering_status = collections.Counter()
    for r in rites:
        asserted = (r["uses_offering"] or 0) + (r["uses_offering_substance"] or 0)
        if asserted:
            status = "OFFERING_ASSERTED_FROM_SOURCE_EXPLICIT_EVIDENCE"
            reason = (
                "The rite carries an offering edge whose evidence is a source statement, not "
                "a verse co-occurrence."
            )
        elif r["entity_key"] in rites_with_probable:
            status = "OFFERING_CANDIDATE_REFUSED_AS_CO_OCCURRENCE"
            reason = (
                "The acquired apparatus holds a candidate for this rite, staged PROBABLE and "
                "resting on one sutra naming both a rite and an offering. Clause 3 of this "
                "gap's own closure test forbids presenting co-occurrence as an asserted "
                "offering, so the candidate is NOT asserted. Owner decision 39: mechanical "
                "candidate generation is not evidence."
            )
        else:
            status = "OFFERING_NOT_ATTESTED_IN_THE_HELD_APPARATUS"
            reason = (
                "No rite-to-offering statement for this rite exists in the eighteen acquired "
                "ritual works. This is a measured absence against what is held, NOT a finding "
                "that the rite has no offering."
            )
        offering_status[status] += 1
        node_updates.append(
            {
                "entity_key": r["entity_key"],
                "properties": {
                    "offering_status": status,
                    "offering_status_reason": reason,
                    "offering_status_contract": "VG:RITE_OFFERING_STATUS:V1",
                    "offering_status_denominator": (
                        "evidence-eligible rites, per OWNER_DECISION_COMMUNITIES_002_PAIR_"
                        "DECOMPOSITION as recorded in OWNER_DECISIONS.md section 39"
                    ),
                    "r5_contract": CONTRACT,
                },
            }
        )
    out["ritual_005"] = {
        "receives_offering_edges": 4,
        "rites_total": len(rites),
        "offering_status_distribution": dict(offering_status),
        "probable_rows_left_unimported": len(probable_offering_rows),
        "probable_rows_source": "data/staging/ritual/rite_edges.jsonl, predicate USES_OFFERING",
        "rites_with_a_probable_candidate": len(rites_with_probable),
        "edges_minted": 0,
        "why_no_edge_minted": (
            "Every one of the 258 candidate rows is mapping_confidence PROBABLE, resting on "
            "one sutra naming both a rite and an offering. Clause 3 of this gap's own "
            "closure test forbids presenting co-occurrence as an asserted offering, and the "
            "historical rule that PROBABLE ritual material stays excluded is binding. Under "
            "OWNER_DECISIONS.md section 39 they are non-asserted candidates, not missing "
            "graph data."
        ),
    }

    # --- RITUAL-006 -------------------------------------------------------
    precision = json.loads(
        (SPRINT / "agent4" / "ritual_context_precision.json").read_text(encoding="utf-8")
    )
    split = json.loads(
        (SPRINT / "agent4" / "material_culture_by_ritual_context.json").read_text(encoding="utf-8")
    )
    out["ritual_006"] = {
        "precision_over_every_reviewed_row": precision["precision_over_every_reviewed_row"],
        "precision_over_reproducible_rows": precision[
            "precision_over_rows_whose_evidence_is_reproducible"
        ],
        "reviewed": precision["reviewed"],
        "population": precision["population_size"],
        "review_level": precision["review_level"],
        "human_reviewed": precision["human_reviewed"],
        "material_culture_mentions_assessed": split["mentions_assessed"],
        "material_culture_by_context": split["by_context"],
    }
    # One DerivedMetric node per figure, so the product reads a measured row rather than a
    # number typed into prose. This project has recorded that a figure in a paragraph is the
    # only one nothing can check.
    # The layer's own convention, measured from the 1,481 existing rows rather than
    # invented beside them: metric_id is VG:METRIC:<METRIC_NAME>:<SUBJECT_KEY> and is the
    # unique key (1,481 distinct over 1,481 nodes); the figures travel in values_json;
    # metric_name is the family (20 distinct). A node keyed on a metric_key nothing else
    # carries would be invisible to every existing consumer of this label.
    metric_nodes = [
        {
            "metric_id": "VG:METRIC:RITUAL_CONTEXT_PRECISION:VG:LAYER:RITUAL_CONTEXT",
            "properties": {
                "metric_id": "VG:METRIC:RITUAL_CONTEXT_PRECISION:VG:LAYER:RITUAL_CONTEXT",
                "metric_name": "RITUAL_CONTEXT_PRECISION",
                "subject_key": "VG:LAYER:RITUAL_CONTEXT",
                "subject": "the ritual_context assignment over all 20,210 mantras",
                "display_label": "RITUAL_CONTEXT_PRECISION (VG:LAYER:RITUAL_CONTEXT)",
                "display_type": "DerivedMetric",
                "domain_model_version": "vedagraph-knowledge-model-v2",
                "knowledge_layer": "L2_DETERMINISTIC_DERIVED",
                "quality_tier": "TIER_B",
                "method": "EXTERNAL_RITUAL_CITATION; precision over a seeded random sample of the EXACT population",
                "values_json": json.dumps(
                    {
                        "precision_over_every_reviewed_row": precision[
                            "precision_over_every_reviewed_row"
                        ],
                        "precision_over_reproducible_rows": precision[
                            "precision_over_rows_whose_evidence_is_reproducible"
                        ],
                        "reviewed_sample_size": precision["reviewed"],
                        "population_size": precision["population_size"],
                        "true_positives": precision["true_positives"],
                        "false_positives": precision["false_positives"],
                        "withheld_span_not_reproducible": precision[
                            "withheld_span_not_reproducible"
                        ],
                        "population_span_not_reproducible": precision[
                            "population_span_not_reproducible"
                        ],
                        "human_reviewed": precision["human_reviewed"],
                    },
                    ensure_ascii=False,
                ),
                "grade_basis": precision["review_level"],
                "review_level": precision["review_level"],
                "human_reviewed": precision["human_reviewed"],
                "reviewer": precision["reviewer"],
                "reference_set_class": "INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET",
                "is_human_gold": False,
                "draw": precision["draw"],
                "scope_note": (
                    "TWO figures, not one, because a single figure would have to decide whether "
                    "an unreproducible row is an error or an unknown, and it is an unknown: "
                    + precision["precision_is_reported_as_two_figures_because"]
                    + " The sample was adjudicated by ONE AGENT reader and human_reviewed is 0. "
                    "This is an INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET and it is NOT "
                    "human gold; the distinction is project policy and must not be relabelled."
                ),
                "r5_contract": CONTRACT,
            },
        },
        {
            "metric_id": "VG:METRIC:MATERIAL_CULTURE_BY_RITUAL_CONTEXT:VG:LAYER:MATERIAL_CULTURE",
            "properties": {
                "metric_id": "VG:METRIC:MATERIAL_CULTURE_BY_RITUAL_CONTEXT:VG:LAYER:MATERIAL_CULTURE",
                "metric_name": "MATERIAL_CULTURE_BY_RITUAL_CONTEXT",
                "subject_key": "VG:LAYER:MATERIAL_CULTURE",
                "subject": "every Crop, Metal and Animal mention of the mention layer",
                "display_label": "MATERIAL_CULTURE_BY_RITUAL_CONTEXT (VG:LAYER:MATERIAL_CULTURE)",
                "display_type": "DerivedMetric",
                "domain_model_version": "vedagraph-knowledge-model-v2",
                "knowledge_layer": "L2_DETERMINISTIC_DERIVED",
                "quality_tier": "TIER_B",
                "method": "mention-layer edges joined to the five-valued ritual_context",
                "values_json": json.dumps(
                    {"mentions_assessed": split["mentions_assessed"], **split["by_context"]},
                    ensure_ascii=False,
                ),
                "grade_basis": "deterministic join over two layers already in the graph",
                "scope_note": (
                    split["the_split_is_not_ritual_versus_everyday"]
                    + " NO_RITUAL_CITATION_FOUND is a measured absence against eighteen "
                    "acquired works, not a finding that a mention is domestic, and no mantra "
                    "in this split is marked NON_RITUAL."
                ),
                "r5_contract": CONTRACT,
            },
        },
    ]
    mantra_updates = {
        "ritual_context_precision": precision[
            "precision_over_rows_whose_evidence_is_reproducible"
        ],
        "ritual_context_precision_all_reviewed_rows": precision[
            "precision_over_every_reviewed_row"
        ],
        "ritual_context_precision_sample_size": precision["reviewed"],
        "ritual_context_precision_population": precision["population_size"],
        "ritual_context_precision_review_level": precision["review_level"],
        "ritual_context_precision_human_reviewed": precision["human_reviewed"],
        "ritual_context_precision_metric_key": "VG:METRIC:RITUAL_CONTEXT_PRECISION:V1",
    }
    out["node_updates"] = node_updates
    out["metric_nodes"] = metric_nodes
    out["mantra_precision_properties"] = mantra_updates
    out["promised"] = {
        "nodes_updated": len(node_updates),
        "mantras_updated": 20210,
        "nodes_created": len(metric_nodes),
        "relationships_created": 0,
    }
    return out


# ---------------------------------------------------------------------------
# GAP-QUALITY-003
# ---------------------------------------------------------------------------


def stage_quality_003(session) -> dict[str, Any]:
    """Stop a tier presenting itself as a probability, and prove the gold set does not exist.

    ``confidence != probability``. Seven predicates carry a constant 1.0 on every one of
    51,356 edges. That 1.0 stands for "the source says so" -- a TIER, not a calibrated
    probability -- and a filterable numeric field that selects everything or nothing is
    worse than no field, because it invites a threshold nobody can honour.

    The field is RENAMED rather than deleted, to ``source_explicit_tier_marker``, with the
    tier it actually encodes written beside it. Deleting it would lose the fact that these
    edges are source-explicit; keeping it named ``confidence`` keeps the false invitation.

    Clause 1's calibration curve needs a human-labelled sample per predicate. It does not
    exist, and the absence is PROVEN here rather than asserted: the repository's reference
    set is enumerated and its class reported.

    FALSIFIER: if any of the seven predicates turns out to carry more than one distinct
    confidence value, it is not constant and must not be renamed.
    """
    per_type = _q.rows(
        session,
        """
        MATCH ()-[r]->() WHERE r.confidence IS NOT NULL
        WITH type(r) AS t, collect(DISTINCT r.confidence) AS vals, count(r) AS c
        RETURN t, vals, size(vals) AS distinct_vals, c ORDER BY c DESC
        """,
    )
    constant = [r for r in per_type if r["distinct_vals"] == 1]
    variable = [r for r in per_type if r["distinct_vals"] > 1]
    # Only the seven at 1.0 are a tier wearing a probability's name. A constant on a tiny
    # population is a different problem -- too few edges to calibrate -- and is typed as that.
    tier_marked = [r for r in constant if float(r["vals"][0]) == 1.0]
    tiny_constant = [r for r in constant if float(r["vals"][0]) != 1.0]

    gold = _q.rows(
        session,
        """
        MATCH (a:SemanticAssertion)
        RETURN a.human_gold_status AS status, a.review_state AS review, count(*) AS c
        ORDER BY c DESC
        """,
    )
    verdicts = _q.rows(
        session,
        """
        MATCH (v:QualityVerdict)
        RETURN v.review_level AS review_level, v.reviewer_kind AS reviewer_kind,
               v.is_human_gold AS is_human_gold, count(*) AS c ORDER BY c DESC
        """,
    )
    return {
        "gap_id": "GAP-QUALITY-003",
        "rename": {
            "from": "confidence",
            "to": "source_explicit_tier_marker",
            "predicates": [r["t"] for r in tier_marked],
            "edges_affected": sum(r["c"] for r in tier_marked),
            "extra_properties": {
                "confidence_field_withdrawn_because": (
                    "The value was a constant 1.0 on every edge of the predicate. It encoded "
                    "the evidence TIER -- the source states this -- and not a calibrated "
                    "probability, so it offered a numeric filter that selects everything or "
                    "nothing. confidence != probability."
                ),
                "encoded_tier": "L1_SOURCE_EXPLICIT",
                "r5_contract": CONTRACT,
            },
        },
        "constant_but_not_one": [
            {"predicate": r["t"], "value": r["vals"][0], "edges": r["c"]} for r in tiny_constant
        ],
        "variable_confidence_predicates": [
            {"predicate": r["t"], "distinct_values": r["distinct_vals"], "edges": r["c"]}
            for r in variable
        ],
        "human_gold_evidence": {
            "semantic_assertion_human_gold_status": gold,
            "quality_verdict_review_levels": verdicts,
            "reference_set_class": "INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET",
            "is_human_gold": False,
            "why_not_human_gold": (
                "Project policy, recorded: the available reference set is independently "
                "source-adjudicated, not human-annotated. Relabelling it HUMAN_GOLD would "
                "manufacture a review that did not happen."
            ),
        },
        "promised": {
            "relationships_updated": sum(r["c"] for r in tier_marked),
            "property_keys_touched": [
                "confidence",
                "source_explicit_tier_marker",
                "confidence_field_withdrawn_because",
                "encoded_tier",
            ],
        },
        "falsifier": {
            "predicates_claimed_constant": len(tier_marked),
            "any_claimed_constant_has_multiple_values": any(
                r["distinct_vals"] != 1 for r in tier_marked
            ),
        },
    }


# ---------------------------------------------------------------------------
# GAP-TRANSLATION-004
# ---------------------------------------------------------------------------


def stage_translation_004(session) -> dict[str, Any]:
    """Replace a metric that cannot be satisfied without reintroducing TRANSLATION-006.

    004's measure asks for a HAS_TRANSLATION edge on every RV mantra. 36 lack one: every
    even verse of RV 1.65-1.70. Those six hymns are PAIRED_DVIPADA -- Griffith prints one
    unit per verse PAIR -- and 006 anchored unit N on verse 2N-1 carrying
    ``covers_canonical_keys = [2N-1, 2N]`` precisely so one rendering is not published twice
    as two independent per-verse translations. Attaching an own edge to each even verse
    satisfies 004's number and reintroduces 006's defect exactly.

    So the metric is restated in TRUTH STATES rather than "all rows positive".

    MEASURED, and it falsified my own first guess: 30 of the 36 ARE named in a MANTRA_RANGE
    translation's ``covers_canonical_keys`` and 6 are covered by NOTHING. The 6 are not
    erased to reach zero -- they are typed, and the source absence behind them is proven
    against the canonical artifact: 52 of 10,552 RV mantras have no row in
    data/canonical/rigveda_full_v1/translations.jsonl, which falsifies this entry's own
    source_dependency claim that "the ingested Griffith RV covers the Sakala Samhita in full".
    """
    rows = _q.rows(
        session,
        """
        MATCH (m:Mantra)
        OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(t:Translation)
        WITH m, collect(CASE WHEN t IS NULL THEN NULL ELSE properties(t) END) AS ts
        RETURN m.canonical_key AS key, m.veda AS veda,
               [x IN ts WHERE x IS NOT NULL] AS ts
        ORDER BY key
        """,
    )
    covered = set()
    for r in _q.rows(
        session,
        "MATCH (t:Translation) WHERE t.covers_canonical_keys IS NOT NULL "
        "RETURN t.covers_canonical_keys AS keys",
    ):
        covered.update(r["keys"] or [])
    reusable_parallel = {
        r["key"]
        for r in _q.rows(
            session,
            """
            MATCH (m:Mantra)-[:REUSES_TEXT_FROM]->(o:Mantra)-[:HAS_TRANSLATION]->(:Translation)
            WHERE NOT (m)-[:HAS_TRANSLATION]->()
            RETURN DISTINCT m.canonical_key AS key
            """,
        )
    }

    updates: list[dict[str, Any]] = []
    dist = collections.Counter()
    uncovered: list[str] = []
    for r in rows:
        # The production classifier, not a second copy of its rules. A verse's own
        # translations are passed through as property maps exactly as classify() expects.
        state = verse_coverage_state(
            r["key"],
            r["ts"],
            range_covered=r["key"] in covered,
            reusable_parallel=r["key"] in reusable_parallel,
        ).value
        if state in {s.value for s in UNCOVERED_STATES}:
            uncovered.append(r["key"])
        dist[f"{r['veda']}|{state}"] += 1
        updates.append(
            {
                "canonical_key": r["key"],
                "veda": r["veda"],
                "properties": {
                    "translation_coverage_state": state,
                    "translation_coverage_contract": "VG:TRANSLATION_COVERAGE:V1",
                    "r5_contract": CONTRACT,
                },
            }
        )

    by_veda: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for k, n in sorted(dist.items()):
        veda, state = k.split("|")
        by_veda[veda][state] = n

    return {
        "gap_id": "GAP-TRANSLATION-004",
        "node_updates": updates,
        "distribution_by_veda": {k: v for k, v in sorted(by_veda.items())},
        "uncovered_rows": sorted(uncovered),
        "rv_uncovered": sum(1 for k in uncovered if k.startswith("VG:RV")),
        "independent_english_by_veda": {
            veda: sum(
                n
                for state, n in states.items()
                if state in {s.value for s in INDEPENDENT_ENGLISH_STATES}
            )
            for veda, states in sorted(by_veda.items())
        },
        "samaveda_independent_english": (
            "ZERO. All 173 Samavedic renderings carry reuse_kind=REUSED_RENDERING from "
            "VEDAGRAPH_CANONICAL_RV_GRIFFITH -- Griffith's Rigvedic English attached to "
            "verses whose Sanskrit is verified identical. A total that reports 173 English "
            "translations for the Samaveda is wrong, and an earlier draft of this very "
            "staging made that mistake before the reuse_kind column was checked."
        ),
        "old_metric": {
            "cypher": "MATCH (m:Mantra {veda:'RV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN count(m)",
            "value": 36,
            "required": 0,
            "why_it_cannot_be_satisfied": (
                "Reaching 0 means attaching an own HAS_TRANSLATION edge to each even verse of "
                "RV 1.65-1.70, which republishes one paired-dvipada Griffith unit as two "
                "independent per-verse translations. That is precisely the defect "
                "GAP-TRANSLATION-006 was opened for and closed."
            ),
        },
        "new_metric": {
            "cypher": (
                "MATCH (m:Mantra {veda:'RV'}) "
                "WHERE m.translation_coverage_state IN "
                "['UNCOVERED_REUSABLE_PARALLEL_AVAILABLE', 'UNCOVERED_NO_RENDERING_REACHES_IT'] "
                "RETURN count(m)"
            ),
            "terminal_states": [s.value for s in VerseCoverageState],
            "contract": "vedagraph.domain.translation_semantics.VerseCoverageState",
            "reused_rendering_is_not_own_english": (
                "REUSED_RENDERING is a terminal state of its own and is excluded from "
                "INDEPENDENT_ENGLISH_STATES, so it cannot be totalled into a corpus's own "
                "English coverage."
            ),
        },
        "promised": {"mantras_updated": len(updates), "relationships_created": 0},
    }


# ---------------------------------------------------------------------------


def main() -> None:
    driver = _q.driver()
    staged: dict[str, Any] = {}
    try:
        with driver.session(database=_q.DB) as session:
            staged["semantics_003"] = stage_semantics_003(session)
            staged["entity_006"] = stage_entity_006(session)
            staged["entity_007"] = stage_entity_007(session)
            staged["ritual"] = stage_ritual(session)
            staged["quality_003"] = stage_quality_003(session)
            staged["translation_004"] = stage_translation_004(session)
    finally:
        driver.close()

    out = HERE / "staged_mutations.json"
    out.write_text(json.dumps(staged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"wrote {out.name}")
    for name, block in staged.items():
        print(f"\n== {name}")
        print("   promised:", json.dumps(block.get("promised", {}), ensure_ascii=False))
        if "falsifier" in block:
            print("   falsifier:", json.dumps(block["falsifier"], ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
