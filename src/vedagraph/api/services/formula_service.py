"""Formula and formula-family detail, with the double-count contract enforced in one place.

The formulaic-diction layer is stored in both directions, and that is the whole reason this
module exists as something other than two queries.

**One membership, two edges.** ``(Formula)-[:MEMBER_OF_FAMILY]->(FormulaFamily)`` carries
2,037 edges; ``(FormulaFamily)-[:HAS_FORMULA]->(Formula)`` carries the same 2,037, mirrored
property for property down to a shared ``membership_id``. ``load_formula_family_outward``
in the V3 loader says what they are to each other: ``HAS_FORMULA`` is *a mirror, not a
derivation*, copied from the inbound edges that already landed precisely so that the two
cannot disagree about ``role`` or tier. The mirror exists because the family landed
navigable in one direction only, and every consumer reading the graph as a directed thing
saw ``:FormulaFamily`` as a sink.

So ``MEMBER_OF_FAMILY`` is authoritative here and the mirror is not traversed at all.
Measured, three ways: inbound ``MEMBER_OF_FAMILY`` reconciles with the recorded
``member_count`` on all 720 families with zero disagreements; outbound ``HAS_FORMULA``
likewise; and a traversal that follows both gives exactly ``2 x member_count`` on all 720.
The last of those is what a "harmless" ``OPTIONAL MATCH`` in each direction would produce,
and it would read as a family twice its real size rather than as an error.

**The counts on the node are not all summable.** ``core_count + expansion_count +
variant_count`` equals ``member_count`` on every one of the 720 families. But 157 families
also carry a non-zero ``secondary_core_count`` which is a *subset* of ``core_count``, no
membership edge carries a ``SECONDARY_CORE`` role, and nothing in the frozen graph records
the containment. So this module reports the recorded counts beside the counts it actually
traversed, on every response, and never adds the fourth number to the other three.
"""

from __future__ import annotations

from typing import Any, Final

from vedagraph.api.errors import EntityNotFoundError
from vedagraph.api.models.common import (
    CaveatView,
    EvidenceView,
    KnowledgeStatus,
    evidence_surface,
)
from vedagraph.api.models.entity import parse_json_property
from vedagraph.api.models.formula import (
    FormulaDetail,
    FormulaFamilyDetail,
    FormulaFamilyMemberView,
    FormulaFamilyReconciliation,
    FormulaFamilyRef,
    FormulaOccurrenceView,
)
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.domain import layer_figures as figures
from vedagraph.api.services.graph_service import (
    FAMILY_MEMBERSHIP_DIRECTION,
    FAMILY_MEMBERSHIP_MIRROR,
    attribution_basis,
    attribution_precision,
    evidence_spans,
    layer_method,
)

#: Roles a membership edge may carry. Measured complete over all 2,037 memberships: 914
#: ``CORE``, 1,119 ``EXPANSION``, 4 ``VARIANT``. ``SECONDARY_CORE`` is deliberately absent
#: -- 157 families record a ``secondary_core_count`` but no edge carries that role, so the
#: distinction is not traversable and this API does not invent a bucket for it.
MEMBERSHIP_ROLES: Final[tuple[str, ...]] = ("CORE", "EXPANSION", "VARIANT")

#: Members returned per family. Larger than the biggest family needs: the maximum
#: ``member_count`` in the layer is well inside this, so a family is normally complete and
#: ``members_truncated`` is normally false.
MAX_FAMILY_MEMBERS: Final = 100

#: Passage occurrences returned per formula or family. Bounded because the widest-spread
#: formula occurs 93 times and the widest family 148 times, and an unbounded list here is
#: the one place this surface could grow without limit.
MAX_OCCURRENCES: Final = 60

#: Families listed on a formula. A formula belongs to few families; the bound is a bound.
MAX_FAMILIES_PER_FORMULA: Final = 20

#: What a client must not conclude from a formula's Veda spread. Attached to every formula
#: and family response that spans more than one corpus.
CROSS_VEDA_CAVEAT: Final = (
    "Formula identity is a normalised-string match, so a wording shared across corpora is "
    "shared DICTION and not a demonstrated line of transmission. Read the per-Veda counts "
    "as shares of their corpus (RV 10,552 mantras, AV 5,839, YV 1,975, SV 1,844) rather "
    "than as totals, and remember that the Samaveda and much of the Yajurveda are drawn "
    "from the Rigveda: a four-Veda formula is often one Rigvedic phrase carried forward, "
    "not four independent attestations."
)

#: Attached to every family, because the direction contract is invisible in the payload.
DIRECTION_CONTRACT_CAVEAT: Final = (
    f"Membership was traversed in one direction only. The graph stores every membership "
    f"twice -- 2,037 {FAMILY_MEMBERSHIP_DIRECTION} edges and 2,037 {FAMILY_MEMBERSHIP_MIRROR} "
    f"edges mirroring them property for property, including a shared membership_id -- and "
    f"following both would return each member twice. {FAMILY_MEMBERSHIP_DIRECTION} is "
    f"authoritative; {FAMILY_MEMBERSHIP_MIRROR} is a mirror copied from it. The "
    f"`reconciliation` block states the traversed counts beside the counts recorded on the "
    f"family node so the two can be checked against each other."
)

#: Attached where a family records a secondary core.
SECONDARY_CORE_CAVEAT: Final = (
    "secondary_core_count is a SUBSET of core_count and not a fourth role. The membership "
    "edges carry only CORE, EXPANSION and VARIANT, and core + expansion + variant already "
    "equals member_count; adding secondary_core_count to them over-counts this family. The "
    "split is recorded on the family node and is not traversable, so this response cannot "
    "list which cores are secondary."
)

#: Attached where any membership in the family rests on resemblance rather than containment.
SIMILARITY_MEMBERSHIP_CAVEAT: Final = (
    "At least one membership in this family is TIER_D: derived from string similarity "
    "rather than from containment. Those are the only rows in the whole family layer where "
    "membership is an inference instead of a checkable fact -- there are 5 of 2,037 -- and "
    "the failure mode is visible in them: 'nu dyavaprthivi' against 'dyavaprthivi a' is a "
    "sandhi boundary falling differently, not a variant reading."
)


# ---------------------------------------------------------------------------
# Cypher
# ---------------------------------------------------------------------------

_FORMULA_CYPHER: Final = """
MATCH (f:Formula {formula_id: $formula_id})
RETURN properties(f) AS formula
"""

#: Families a formula belongs to. ``MEMBER_OF_FAMILY`` only -- the ``HAS_FORMULA`` mirror
#: would return each family a second time.
_FORMULA_FAMILIES_CYPHER: Final = f"""
MATCH (f:Formula {{formula_id: $formula_id}})-[m:{FAMILY_MEMBERSHIP_DIRECTION}]->(ff:FormulaFamily)
RETURN ff.family_id AS family_id,
       ff.representative_display_form AS representative,
       properties(m) AS membership
ORDER BY m.role, ff.family_id
LIMIT $limit
"""

_FORMULA_OCCURRENCES_CYPHER: Final = """
MATCH (p:Passage)-[u:USES_FORMULA]->(:Formula {formula_id: $formula_id})
RETURN p.canonical_key AS passage_id, p.canonical_citation AS citation, p.veda AS veda,
       u.source_form AS source_form
ORDER BY p.canonical_key
LIMIT $limit
"""

_FAMILY_CYPHER: Final = """
MATCH (ff:FormulaFamily {family_id: $family_id})
RETURN properties(ff) AS family
"""

#: Members, with each member's own reach. ``count(DISTINCT p)`` and not ``count(*)``: the
#: membership pattern and the ``USES_FORMULA`` pattern are both in scope, so a formula used
#: by sixty passages would otherwise be multiplied by its membership row -- which is the
#: same trap the frozen ``formula_family_profile`` caveat names.
_FAMILY_MEMBERS_CYPHER: Final = f"""
MATCH (f:Formula)-[m:{FAMILY_MEMBERSHIP_DIRECTION}]->(:FormulaFamily {{family_id: $family_id}})
OPTIONAL MATCH (p:Passage)-[:USES_FORMULA]->(f)
WITH f, m, count(DISTINCT p) AS passage_count, collect(DISTINCT p.veda) AS vedas
RETURN f.formula_id AS formula_id, f.display_form AS display_form,
       f.word_count AS word_count, properties(m) AS membership,
       passage_count, vedas
ORDER BY m.role, passage_count DESC, f.display_form
LIMIT $limit
"""

_FAMILY_OCCURRENCES_CYPHER: Final = f"""
MATCH (:FormulaFamily {{family_id: $family_id}})<-[:{FAMILY_MEMBERSHIP_DIRECTION}]-(f:Formula)
MATCH (p:Passage)-[u:USES_FORMULA]->(f)
WITH DISTINCT p, u.source_form AS source_form
RETURN p.canonical_key AS passage_id, p.canonical_citation AS citation, p.veda AS veda,
       source_form
ORDER BY p.canonical_key
LIMIT $limit
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class FormulaService:
    """Detail views for one formula and for one formula family.

    The list surfaces belong to the generic entity endpoints; what lives here is the pair of
    detail payloads, because both of them have to enforce the membership direction contract
    and neither can do that from a generic projection.
    """

    def __init__(self, repository: Neo4jRepository) -> None:
        self._repository = repository

    # -- formula -----------------------------------------------------------------

    def formula_detail(self, formula_id: str) -> FormulaDetail:
        row = self._repository.run_one(_FORMULA_CYPHER, formula_id=formula_id)
        if row is None:
            raise EntityNotFoundError(
                f"No formula has the id {formula_id!r}.",
                hint="Formula ids look like VG:ENRICH:FORMULA:<32 hex characters>. "
                "GET /api/v1/entities?type=formula lists them.",
            )
        properties: dict[str, Any] = dict(row["formula"])

        family_rows = self._repository.run(
            _FORMULA_FAMILIES_CYPHER, formula_id=formula_id, limit=MAX_FAMILIES_PER_FORMULA
        )
        occurrence_rows = self._repository.run(
            _FORMULA_OCCURRENCES_CYPHER, formula_id=formula_id, limit=MAX_OCCURRENCES
        )

        vedas = _string_list(properties.get("vedas"))
        per_veda = _veda_counts(properties.get("veda_counts"))
        occurrence_count = _as_int(properties.get("occurrence_count"))
        return FormulaDetail(
            id=formula_id,
            display_form=str(properties.get("display_form") or properties.get("normalized") or ""),
            normalized=_as_str(properties.get("normalized")),
            word_count=_as_int(properties.get("word_count")),
            char_count=_as_int(properties.get("char_count")),
            occurrence_count=occurrence_count,
            mantra_count=_as_int(properties.get("mantra_count")),
            vedas=vedas,
            occurrences_by_veda=per_veda,
            cross_veda=bool(properties.get("cross_veda")),
            source_forms=_string_list(properties.get("source_forms")),
            families=[
                FormulaFamilyRef(
                    family_id=str(family_row["family_id"]),
                    representative_display_form=_as_str(family_row["representative"]),
                    role=_as_str(dict(family_row["membership"]).get("role")),
                    contains_representative=_as_bool(
                        dict(family_row["membership"]).get("contains_representative")
                    ),
                    containment_is_transitive=_as_bool(
                        dict(family_row["membership"]).get("containment_is_transitive")
                    ),
                    similarity=_as_float(dict(family_row["membership"]).get("similarity")),
                    quality_tier=_as_str(dict(family_row["membership"]).get("quality_tier")),
                )
                for family_row in family_rows
            ],
            occurrences=[_occurrence(occurrence_row) for occurrence_row in occurrence_rows],
            occurrences_truncated=len(occurrence_rows) == MAX_OCCURRENCES,
            evidence=_evidence(properties),
            score=_as_float(properties.get("score")),
            data_status=KnowledgeStatus.SUPPORTED,
            caveats=self._formula_caveats(
                properties=properties,
                vedas=vedas,
                returned_occurrences=len(occurrence_rows),
                occurrence_count=occurrence_count,
            ),
        )

    def _formula_caveats(
        self,
        *,
        properties: dict[str, Any],
        vedas: list[str],
        returned_occurrences: int,
        occurrence_count: int | None,
    ) -> list[CaveatView]:
        caveats: list[CaveatView] = [
            CaveatView(
                text=(
                    "A formula is a recurring wording identified by normalised-string "
                    "match over the corpus, not a unit the tradition names. Two passages "
                    "sharing one share diction."
                ),
                source="measured",
            )
        ]
        if len(vedas) > 1 or properties.get("cross_veda"):
            caveats.append(CaveatView(text=CROSS_VEDA_CAVEAT, source="measured"))
        if occurrence_count is not None and returned_occurrences < occurrence_count:
            caveats.append(
                CaveatView(
                    text=(
                        f"{returned_occurrences} of {occurrence_count} occurrences are "
                        "listed; the list is bounded and the count is not. The absence of a "
                        "passage from this list is not evidence that it does not use the "
                        "formula."
                    ),
                    source="measured",
                )
            )
        if properties.get("state") == "CANDIDATE":
            caveats.append(
                CaveatView(
                    text="state is CANDIDATE: this formula was not accepted into the "
                    "deterministic layer and is offered for inspection.",
                    source="measured",
                )
            )
        # GAP-FORMULA-003 clause 2. Every formula carries a formula_nesting_type and this
        # ranking ordered by occurrence count without saying which nesting reading it
        # applied -- so a reader could not tell whether the top of the list was several
        # phrases or one phrase at several lengths. The sentence is derived from the live
        # population by layer_figures rather than typed here, so it cannot go stale.
        caveats.append(CaveatView(text=figures.formula_nesting_policy(), source="measured"))
        return caveats

    # -- family ------------------------------------------------------------------

    def family_detail(self, family_id: str) -> FormulaFamilyDetail:
        """One family, traversed in the authoritative direction only.

        Members come back grouped by role rather than as one list, because the roles are not
        degrees of the same thing: ``CORE`` is the phrase that names the family,
        ``EXPANSION`` is something that contains it, and ``VARIANT`` is the four-row
        similarity-derived corner of the layer where membership is an inference.
        """
        row = self._repository.run_one(_FAMILY_CYPHER, family_id=family_id)
        if row is None:
            raise EntityNotFoundError(
                f"No formula family has the id {family_id!r}.",
                hint="Family ids look like VG:ENRICH:FORMULA-FAMILY:<32 hex characters>.",
            )
        properties: dict[str, Any] = dict(row["family"])
        member_rows = self._repository.run(
            _FAMILY_MEMBERS_CYPHER, family_id=family_id, limit=MAX_FAMILY_MEMBERS
        )
        occurrence_rows = self._repository.run(
            _FAMILY_OCCURRENCES_CYPHER, family_id=family_id, limit=MAX_OCCURRENCES
        )

        members = [_member(member_row) for member_row in member_rows]
        by_role: dict[str, list[FormulaFamilyMemberView]] = {role: [] for role in MEMBERSHIP_ROLES}
        for member in members:
            by_role.setdefault(member.role or "CORE", []).append(member)

        reconciliation = FormulaFamilyReconciliation(
            direction_traversed=FAMILY_MEMBERSHIP_DIRECTION,
            recorded_member_count=_as_int(properties.get("member_count")),
            traversed_member_count=len(members),
            recorded_core_count=_as_int(properties.get("core_count")),
            traversed_core_count=len(by_role.get("CORE", [])),
            recorded_expansion_count=_as_int(properties.get("expansion_count")),
            traversed_expansion_count=len(by_role.get("EXPANSION", [])),
            recorded_variant_count=_as_int(properties.get("variant_count")),
            traversed_variant_count=len(by_role.get("VARIANT", [])),
            agrees=_reconciles(properties, members, by_role),
        )
        vedas = _string_list(properties.get("vedas"))
        occurrence_count = _as_int(properties.get("occurrence_count"))
        return FormulaFamilyDetail(
            id=family_id,
            representative_display_form=_as_str(properties.get("representative_display_form")),
            representative_formula_id=_as_str(properties.get("representative_formula_id")),
            representative_coverage=_as_float(properties.get("representative_coverage")),
            member_count=_as_int(properties.get("member_count")),
            core_count=_as_int(properties.get("core_count")),
            secondary_core_count=_as_int(properties.get("secondary_core_count")),
            expansion_count=_as_int(properties.get("expansion_count")),
            variant_count=_as_int(properties.get("variant_count")),
            occurrence_count=occurrence_count,
            mantra_count=_as_int(properties.get("mantra_count")),
            veda_span=_as_int(properties.get("veda_span")),
            vedas=vedas,
            occurrences_by_veda=_veda_counts(properties.get("veda_counts")),
            cross_veda=bool(properties.get("cross_veda")),
            containment_depth=_as_int(properties.get("containment_depth")),
            min_word_count=_as_int(properties.get("min_word_count")),
            max_word_count=_as_int(properties.get("max_word_count")),
            parallel_corroborated=_as_bool(properties.get("parallel_corroborated")),
            core=by_role.get("CORE", []),
            expansions=by_role.get("EXPANSION", []),
            variants=by_role.get("VARIANT", []),
            members_truncated=len(member_rows) == MAX_FAMILY_MEMBERS,
            occurrences=[_occurrence(occurrence_row) for occurrence_row in occurrence_rows],
            occurrences_truncated=len(occurrence_rows) == MAX_OCCURRENCES,
            reconciliation=reconciliation,
            evidence=_evidence(properties),
            grade_basis=_as_str(properties.get("grade_basis")),
            notes=_as_str(properties.get("notes")),
            data_status=KnowledgeStatus.SUPPORTED,
            caveats=self._family_caveats(
                properties=properties,
                members=members,
                reconciliation=reconciliation,
                vedas=vedas,
                returned_occurrences=len(occurrence_rows),
                occurrence_count=occurrence_count,
            ),
        )

    def _family_caveats(
        self,
        *,
        properties: dict[str, Any],
        members: list[FormulaFamilyMemberView],
        reconciliation: FormulaFamilyReconciliation,
        vedas: list[str],
        returned_occurrences: int,
        occurrence_count: int | None,
    ) -> list[CaveatView]:
        caveats: list[CaveatView] = [
            CaveatView(
                text=(
                    "A family is a representative wording plus what contains or closely "
                    "resembles it. Its span is a property of shared diction, not of "
                    "transmission: 105 of the 720 families are single-Veda, which is the "
                    "baseline the cross-Veda ones should be read against."
                ),
                source="measured",
            ),
            CaveatView(text=DIRECTION_CONTRACT_CAVEAT, source="measured"),
        ]
        if _as_int(properties.get("secondary_core_count")):
            caveats.append(CaveatView(text=SECONDARY_CORE_CAVEAT, source="measured"))
        if any(member.quality_tier == "TIER_D" for member in members):
            caveats.append(CaveatView(text=SIMILARITY_MEMBERSHIP_CAVEAT, source="measured"))
        transitive = sum(1 for member in members if member.containment_is_transitive)
        if transitive:
            caveats.append(
                CaveatView(
                    text=(
                        f"{transitive} of this family's {len(members)} traversed memberships "
                        "reach the representative wording only transitively, through another "
                        "member. A transitive membership is a weaker claim: the member and "
                        "the representative may share no words at all, and the tier does not "
                        "distinguish them."
                    ),
                    source="measured",
                )
            )
        if len(vedas) > 1 or properties.get("cross_veda"):
            caveats.append(CaveatView(text=CROSS_VEDA_CAVEAT, source="measured"))
        if not reconciliation.agrees:
            caveats.append(
                CaveatView(
                    text=(
                        "THE RECORDED COUNTS ON THIS FAMILY DISAGREE WITH THE MEMBERSHIPS "
                        f"THAT ACTUALLY EXIST: it records {reconciliation.recorded_member_count} "
                        f"members and {reconciliation.traversed_member_count} were traversed. "
                        "The traversed lists are what the graph contains; the recorded "
                        "numbers are a summary that has drifted from it. Read the lists."
                    ),
                    source="measured",
                )
            )
        if occurrence_count is not None and returned_occurrences < occurrence_count:
            caveats.append(
                CaveatView(
                    text=(
                        f"{returned_occurrences} of {occurrence_count} occurrences are "
                        "listed; the list is bounded and the count is not."
                    ),
                    source="measured",
                )
            )
        return caveats


# ---------------------------------------------------------------------------
# Projection helpers
# ---------------------------------------------------------------------------


def _reconciles(
    properties: dict[str, Any],
    members: list[FormulaFamilyMemberView],
    by_role: dict[str, list[FormulaFamilyMemberView]],
) -> bool:
    """Whether every recorded count equals what was traversed.

    Truncation is not a disagreement: a family larger than the member bound would report a
    smaller traversed count for a reason the payload already states in
    ``members_truncated``, and calling that a data defect would cry wolf.
    """
    if len(members) >= MAX_FAMILY_MEMBERS:
        return True
    pairs = (
        (properties.get("member_count"), len(members)),
        (properties.get("core_count"), len(by_role.get("CORE", []))),
        (properties.get("expansion_count"), len(by_role.get("EXPANSION", []))),
        (properties.get("variant_count"), len(by_role.get("VARIANT", []))),
    )
    return all(recorded is None or int(recorded) == traversed for recorded, traversed in pairs)


def _member(row: dict[str, Any]) -> FormulaFamilyMemberView:
    membership: dict[str, Any] = dict(row["membership"])
    return FormulaFamilyMemberView(
        formula_id=str(row["formula_id"]),
        display_form=str(row["display_form"] or ""),
        role=_as_str(membership.get("role")),
        quality_tier=_as_str(membership.get("quality_tier")),
        contains_representative=_as_bool(membership.get("contains_representative")),
        containment_is_transitive=_as_bool(membership.get("containment_is_transitive")),
        has_containment_support=_as_bool(membership.get("has_containment_support")),
        similarity=_as_float(membership.get("similarity")),
        word_count=_as_int(row.get("word_count")),
        passage_count=_as_int(row.get("passage_count")),
        vedas=sorted(_string_list(row.get("vedas"))),
    )


def _occurrence(row: dict[str, Any]) -> FormulaOccurrenceView:
    return FormulaOccurrenceView(
        passage_id=str(row["passage_id"]),
        citation=_as_str(row.get("citation")),
        veda=_as_str(row.get("veda")),
        source_form=_as_str(row.get("source_form")),
    )


def _evidence(properties: dict[str, Any]) -> EvidenceView:
    """The node's own grade, projected through the shared evidence contract.

    ``confidence`` is left null on purpose. Neither ``Formula`` nor ``FormulaFamily`` carries
    a ``confidence`` property at all; both carry ``score``, which on a family is
    ``representative_coverage`` -- the share of the family's mantras the core accounts for --
    and the graph's own ``notes`` says in as many words that it is not a probability. Putting
    it in a field named ``confidence`` would make it one.
    """
    tier = properties.get("quality_tier")
    return EvidenceView(
        method=layer_method(properties),
        tier=str(tier) if isinstance(tier, str) else None,
        evidence_basis=attribution_basis(properties),
        surface=evidence_surface(_as_str(properties.get("evidence_basis"))),
        attribution_precision=attribution_precision(properties),
        review_state=_as_str(properties.get("review_state")),
        confidence=None,
        spans=evidence_spans(properties),
        derivation=_as_str(properties.get("derivation_method")),
    )


def _veda_counts(value: Any) -> dict[str, int]:
    """Parse ``veda_counts``, which the frozen graph stores as a JSON string."""
    parsed = parse_json_property(value)
    if not isinstance(parsed, dict):
        return {}
    return {
        str(key): int(count)
        for key, count in parsed.items()
        if isinstance(count, (int, float)) and not isinstance(count, bool)
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(entry) for entry in value if entry is not None]
    if isinstance(value, str) and value:
        return [value]
    return []


def _as_str(value: Any) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    return int(value) if isinstance(value, (int, float)) else None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    return float(value) if isinstance(value, (int, float)) else None


def _as_bool(value: Any) -> bool | None:
    return bool(value) if isinstance(value, bool) else None
