"""Formula and formula-family contracts.

A *formula* here is a recurring wording -- ``pāta svastibhiḥ sadā naḥ``, four words, 93
occurrences across all four Samhitas -- and a *family* is a representative wording together
with everything that contains or closely resembles it. Two things about that layer are easy
to get wrong in a response, and both are handled on these models rather than left to a
service to remember.

**The double-count.** Every family membership exists twice in the graph. There are 2,037
``(Formula)-[:MEMBER_OF_FAMILY]->(FormulaFamily)`` edges and 2,037
``(FormulaFamily)-[:HAS_FORMULA]->(Formula)`` edges, mirrored property for property,
including a shared ``membership_id``. Measured: traversing one direction reconciles exactly
with the ``member_count`` recorded on the family node for **all 720** families, and
traversing both gives exactly ``2 x member_count`` for all 720. So
:class:`FormulaFamilyReconciliation` is returned with every family payload, stating the
recorded count, the traversed count, the direction traversed, and whether the two agree --
a response that quietly double-counted would look like a larger family rather than like a
bug.

**``secondary_core_count`` is a sub-count, not a fourth role.** The membership edges carry
only three roles (measured: 914 ``CORE``, 1,119 ``EXPANSION``, 4 ``VARIANT``), and
``core_count + expansion_count + variant_count`` equals ``member_count`` on all 720
families. But 157 families also carry a non-zero ``secondary_core_count``, which is a
*subset* of ``core_count`` -- one family records ``member_count`` 3 with ``core_count`` 2 and
``secondary_core_count`` 1 -- and adding the four numbers over-counts those 157. Nothing in
the frozen graph says so, and no membership edge carries a ``SECONDARY_CORE`` role, so the
split is visible on the family node and not traversable. It is therefore reported as
:attr:`FormulaFamilyDetail.secondary_core_count` with the containment stated in its
description, and never summed.
"""

from __future__ import annotations

from pydantic import Field

from vedagraph.api.models.common import (
    ApiModel,
    CaveatView,
    EvidenceView,
    KnowledgeStatus,
)


class FormulaOccurrenceView(ApiModel):
    """One passage that uses a formula, with the wording as that passage has it.

    ``source_form`` is on the edge and not on the formula: the family is a normalised
    identity and the passage's actual wording can differ from it by sandhi, so returning
    only the normalised form would show a reader a phrase that is not in the verse.
    """

    passage_id: str
    citation: str | None = None
    veda: str | None = None
    source_form: str | None = Field(
        default=None, description="The wording as it stands in this passage."
    )


class FormulaFamilyRef(ApiModel):
    """A pointer from a formula to a family it belongs to, carrying the membership's grade.

    ``role`` and ``contains_representative`` travel with the pointer because they are
    properties of *this membership* rather than of either endpoint, and a family list
    without them cannot distinguish the phrase that names the family from something that
    only reaches it through another member.
    """

    family_id: str
    representative_display_form: str | None = None
    role: str | None = Field(default=None, description="CORE, EXPANSION or VARIANT.")
    contains_representative: bool | None = None
    containment_is_transitive: bool | None = None
    similarity: float | None = None
    quality_tier: str | None = None


class FormulaDetail(ApiModel):
    """One recurring wording, its reach, and what its reach does not prove.

    ``cross_veda`` is the field most likely to be over-read, so ``caveats`` always carries
    the reason: formula identity is a normalised-string match, so a wording found in all
    four Samhitas is shared diction and not a demonstrated line of transmission -- and the
    Samaveda and much of the Yajurveda are drawn from the Rigveda, which means a four-Veda
    formula is often one Rigvedic phrase carried forward rather than four independent
    attestations.
    """

    type: str = "FORMULA"
    id: str
    display_form: str
    normalized: str | None = None
    word_count: int | None = None
    char_count: int | None = None
    occurrence_count: int | None = None
    mantra_count: int | None = None
    vedas: list[str] = Field(default_factory=list)
    occurrences_by_veda: dict[str, int] = Field(
        default_factory=dict,
        description="Occurrences per corpus. Compare as a share of each corpus (RV 10,552 "
        "mantras, AV 5,839, YV 1,975, SV 1,844), not as raw totals.",
    )
    cross_veda: bool = False
    source_forms: list[str] = Field(
        default_factory=list, description="Surface wordings collapsed into this identity."
    )
    families: list[FormulaFamilyRef] = Field(default_factory=list)
    occurrences: list[FormulaOccurrenceView] = Field(default_factory=list)
    occurrences_truncated: bool = Field(
        default=False,
        description="True when the passage list was cut by the page bound. The full figure "
        "is `occurrence_count`.",
    )
    evidence: EvidenceView
    score: float | None = Field(
        default=None,
        description="The matcher's own output for this formula. Not a probability; its "
        "meaning depends on `evidence.method`.",
    )
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)


class FormulaFamilyMemberView(ApiModel):
    """One member of a family, with the membership's own grade and reach.

    ``passage_count`` and ``vedas`` describe where *this member's wording* occurs, not where
    the family does. The family's own span is on the family node, and conflating the two is
    the mistake the frozen ``formula_family_profile`` caveat exists to prevent.
    """

    formula_id: str
    display_form: str
    role: str | None = Field(default=None, description="CORE, EXPANSION or VARIANT.")
    quality_tier: str | None = None
    contains_representative: bool | None = Field(
        default=None,
        description="True where this member directly contains the representative wording. "
        "False means it reaches the representative only through another member.",
    )
    containment_is_transitive: bool | None = None
    has_containment_support: bool | None = None
    similarity: float | None = None
    word_count: int | None = None
    passage_count: int | None = None
    vedas: list[str] = Field(default_factory=list)


class FormulaFamilyReconciliation(ApiModel):
    """Recorded counts against traversed counts, for the one layer stored in both directions.

    Returned on every family payload rather than only when it disagrees. A reconciliation
    block that appears only on failure is a block nobody reads, and this repository has
    already shipped an audit block whose 9 recorded corrections included 8 that were never
    written into the data -- the lesson being to read the row, not the summary.
    """

    direction_traversed: str = Field(
        description="The authoritative direction, MEMBER_OF_FAMILY. Its HAS_FORMULA mirror "
        "carries the same 2,037 memberships and is deliberately not also traversed."
    )
    recorded_member_count: int | None = None
    traversed_member_count: int
    recorded_core_count: int | None = None
    traversed_core_count: int
    recorded_expansion_count: int | None = None
    traversed_expansion_count: int
    recorded_variant_count: int | None = None
    traversed_variant_count: int
    agrees: bool = Field(
        description="Whether every recorded count equals the count actually traversed."
    )


class FormulaFamilyDetail(ApiModel):
    """A family of shared wording: its representative, its members by role, and its reach."""

    type: str = "FORMULA_FAMILY"
    id: str
    representative_display_form: str | None = None
    representative_formula_id: str | None = None
    representative_coverage: float | None = Field(
        default=None,
        description="The share of the family's distinct mantras the core alone accounts "
        "for. The graph's own note says it plainly: not a probability.",
    )
    member_count: int | None = None
    core_count: int | None = None
    secondary_core_count: int | None = Field(
        default=None,
        description="A SUBSET of core_count, not a fourth role. Never add this to "
        "core_count: the membership edges carry only CORE, EXPANSION and VARIANT, and "
        "core + expansion + variant already equals member_count on all 720 families.",
    )
    expansion_count: int | None = None
    variant_count: int | None = None
    occurrence_count: int | None = None
    mantra_count: int | None = None
    veda_span: int | None = Field(
        default=None, description="How many corpora this family's wording reaches, 1 to 4."
    )
    vedas: list[str] = Field(default_factory=list)
    occurrences_by_veda: dict[str, int] = Field(default_factory=dict)
    cross_veda: bool = False
    containment_depth: int | None = None
    min_word_count: int | None = None
    max_word_count: int | None = None
    parallel_corroborated: bool | None = Field(
        default=None,
        description="Whether the textual-parallel layer independently joins members of "
        "this family.",
    )
    core: list[FormulaFamilyMemberView] = Field(default_factory=list)
    expansions: list[FormulaFamilyMemberView] = Field(default_factory=list)
    variants: list[FormulaFamilyMemberView] = Field(default_factory=list)
    members_truncated: bool = False
    occurrences: list[FormulaOccurrenceView] = Field(default_factory=list)
    occurrences_truncated: bool = False
    reconciliation: FormulaFamilyReconciliation
    evidence: EvidenceView
    grade_basis: str | None = Field(
        default=None, description="Why the family carries the tier it carries."
    )
    notes: str | None = None
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)
