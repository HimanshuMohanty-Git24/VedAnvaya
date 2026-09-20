"""The four Samhitas: identity, scope, structure and what each corpus's silence means.

**Two names, never one.** ``work_name`` on the Samavedic node reads *Samaveda Samhita*
over a corpus that is the Kauthuma arcika only -- roughly 1,844 verses against a gana body
of some 2,639 ganas this ``work_id`` cannot address. The corpus's own manifest says *"Never
describe this dataset as the complete Samaveda."* ``vedagraph.domain.work_scope`` therefore
writes a scope-honest ``display_label`` beside the traditional name rather than overwriting
it, because the traditional name is also true and the artifact that carries it is hashed
into a manifest. This module keeps both apart to the very edge of the API:
:attr:`WorkSummary.display_label` is what a client renders and
:attr:`WorkSummary.traditional_name` is what the tradition calls it. There is no field a
client can read that returns the traditional name as the display name.

**Scope is quoted, not summarised.** ``scope`` is a prose statement already in the graph,
and for three of the four works it contains a sentence that must reach a reader intact:
the Samavedic one says THIS IS NOT THE COMPLETE SAMAVEDA, the Yajurvedic one that the
Krishna Yajurveda is not held at all, the Atharvavedic one that the Paippalada recension is
not held. Paraphrasing any of them shortens exactly the clause that does the work, so this
API returns the string.

**Layer availability is measured, not declared.** The knowledge layers do not cover the
four corpora evenly and the pattern is not guessable: deity ascription is Rigveda-only, the
agentive assertion layer is Rigveda-only, deity *ascription descriptors* are
Atharvaveda-only, metre reaches the Rigveda and Atharvaveda, seers reach three corpora but
by two incompatible instruments, and the Samaveda has no seer, no metre and zero
translations. :class:`LayerAvailability` reports each from a live count, so a corpus that
gains or loses a layer changes the payload rather than contradicting it.
"""

from __future__ import annotations

from pydantic import Field

from vedagraph.api.models.common import (
    ApiModel,
    CaveatView,
    CoverageView,
    KnowledgeStatus,
    Paginated,
)
from vedagraph.api.models.passage import PassageSummary


class HierarchyLevel(ApiModel):
    """One level of a work's native structure, as a schema descriptor.

    This is the *shape* of a corpus -- "the Rigveda has Mandala, Sukta, Mantra" -- and not
    any passage's position in it. It is derived from the hierarchy keys present on the
    work's passages through the one map in ``passage_service``, which is why the Rigveda
    gets level names at all: its ``native_labels`` property is ``'[]'`` on every node.

    ``value_kind`` distinguishes the Samavedic ``collection``, whose values are the four
    names ARANYA, CHANDA, MAHANAMNYA and UTTARA, from every other level, whose values are
    ordinals. A client that assumed integers throughout would fail on 1,844 verses.
    """

    key: str = Field(description="The graph's hierarchy key, e.g. 'mandala'.")
    native_label: str | None = Field(
        default=None, description="The tradition's name for the level, e.g. 'Mandala'."
    )
    depth: int = Field(ge=1, description="1 for the outermost level.")
    value_kind: str = Field(description="ORDINAL or NAME.")
    passage_types: list[str] = Field(
        default_factory=list,
        description="Passage types found at this level: SECTION, HYMN, "
        "STRUCTURAL_CONTAINER or MANTRA.",
    )
    passage_count: int | None = Field(
        default=None,
        description="Passages whose deepest level is this one. Null means not established.",
    )
    status: KnowledgeStatus = KnowledgeStatus.SUPPORTED


class LayerAvailability(ApiModel):
    """Whether one knowledge layer reaches one corpus, with the figure behind the verdict.

    ``NOT_BUILT`` here is the load-bearing value. A Yajurvedic passage has no ascribed
    deity because the Anukramani ascription layer covers the Rigveda only -- not because the
    verse addresses no god -- and this row is where a client learns which of the two it is
    looking at.
    """

    layer: str = Field(description="Product name of the layer, e.g. DEVATA_ASCRIPTION.")
    relation: str = Field(description="The graph predicate the figure was measured on.")
    status: KnowledgeStatus
    passages: int | None = Field(
        default=None, description="Passages this layer reaches. Null is not zero."
    )
    edges: int | None = None
    share_of_mantras: float | None = Field(
        default=None,
        description="Passages reached over the work's mantra count, so corpora six times "
        "apart in size can be compared without renormalising by hand.",
    )
    note: str | None = None


class AttributionSplit(ApiModel):
    """Source-stated against container-inherited, for one work and one layer.

    Never summed. Of the 17,889 seer edges, 15,177 are a sukta's label projected onto each
    of its mantras; every one of the Atharvaveda's 5,084 is inherited and every one of the
    Yajurveda's 2,240 is source-stated. A single "passages with a named seer" figure
    averages a statement the text makes against a projection this build performed, and the
    two corpora sit at opposite ends of it.
    """

    layer: str
    source_stated: int | None = None
    container_inherited: int | None = None
    status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    note: str | None = None


class TranslationCoverage(ApiModel):
    """How much of a work is translated, in what sense, and by whom.

    ``translated`` is nullable but never rounded up, and the Samaveda is why this is a
    first-class block rather than a percentage on the summary: it has 0 translations of its
    own from 1,844 verses, so every translation-derived layer is empty for that corpus and
    every one of those empty lists would otherwise read as a fact about the Samaveda.

    The four populations below are separate fields because they are four different claims
    and one percentage cannot carry them. ``dedicated`` is a verse with its own 1:1 English
    rendering. ``range_covered`` is a verse the translator rendered inside a multi-verse
    print unit -- real coverage, and not a rendering of that verse alone. ``reused_rendering``
    is another corpus's published English on text verified identical, which is the only
    English that will ever reach a Samavedic verse and is not the Samaveda's own. And
    ``other_language`` is Griffith's Latin substitutions, which are his real text and are
    not the English layer. ``translated`` counts ``dedicated`` alone, so the field that
    existed before these distinctions did still means what it meant.
    """

    mantras: int | None = None
    translated: int | None = Field(
        default=None,
        description="Verses with their own dedicated English translation. Deliberately "
        "not the sum of the four populations below: adding them would assert that every "
        "covered verse has a 1:1 rendering of its own.",
    )
    percent: float | None = Field(
        default=None, description="`dedicated` over `mantras`. The English layer's own share."
    )
    dedicated: int | None = None
    range_covered: int | None = Field(
        default=None,
        description="Verses covered only by a multi-verse print unit anchored elsewhere.",
    )
    reused_rendering: int | None = Field(
        default=None,
        description="Verses showing another corpus's rendering of verified-identical text. "
        "Never added to `translated`.",
    )
    other_language: int | None = Field(
        default=None, description="Verses whose only rendering is not in English."
    )
    uncovered: int | None = Field(
        default=None,
        description="Verses no rendering of any kind reaches. Reported so the four "
        "populations above can be checked against the corpus rather than trusted.",
    )
    any_coverage: int | None = Field(
        default=None,
        description="Verses reached by a rendering of any kind. The honest answer to "
        "'can I read something here', which is a different question to 'is it translated'.",
    )
    translators: list[str] = Field(
        default_factory=list,
        description="Translators of this work's own English, scoped to the population "
        "`translated` counts. A name reaches this list only if it translated this corpus.",
    )
    reused_from_translators: list[str] = Field(
        default_factory=list,
        description="Translators whose rendering of another corpus is shown against verses "
        "of this one. Kept apart from `translators` because 'Griffith' beside a Samavedic "
        "`translated: 0` reads as a contradiction rather than as reuse.",
    )
    status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)


class WorkSummary(ApiModel):
    """A work's identity and size, safe to render in a list."""

    work_id: str
    veda: str
    abbreviation: str | None = None
    display_label: str = Field(
        description="The scope-honest name. Render this. For the Samaveda it reads "
        "'Samaveda Samhita - Kauthuma arcika only (gana corpus NOT included)'."
    )
    traditional_name: str | None = Field(
        default=None,
        description="The work's traditional name, e.g. 'Samaveda Samhita'. True, and not "
        "a description of what this corpus holds. Never render it alone.",
    )
    recension: str | None = None
    excluded_corpora: list[str] = Field(
        default_factory=list,
        description="Bodies this work_id does not address, as a filterable list rather "
        "than only as prose in `scope`.",
    )
    passage_count: int | None = None
    mantra_count: int | None = None
    translated_mantra_count: int | None = Field(
        default=None, description="Null means not established. Zero means measured as zero."
    )
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)


class WorkDetail(WorkSummary):
    """A work with its scope statement, structure and measured layer availability."""

    scope: str | None = Field(
        default=None,
        description="The corpus scope, quoted from the graph and never paraphrased. For "
        "three of the four works this string carries the exclusion a reader most needs.",
    )
    scope_source: str | None = None
    scope_evidence: str | None = None
    completeness: str | None = Field(
        default=None,
        description="The measured coverage figure with its shortfall enumerated. Distinct "
        "from a COMPLETE/INCOMPLETE verdict, which cannot carry the numbers.",
    )
    rights: str | None = None

    hierarchy: list[HierarchyLevel] = Field(
        default_factory=list, description="The work's native structure, outermost first."
    )
    passage_counts_by_type: dict[str, int] = Field(default_factory=dict)
    knowledge_layers: list[LayerAvailability] = Field(default_factory=list)
    attribution_splits: list[AttributionSplit] = Field(default_factory=list)
    translation_coverage: TranslationCoverage
    text_scripts: list[str] = Field(
        default_factory=list,
        description="Scripts this work's text is held in. Disjoint across the corpus: no "
        "passage anywhere carries both, so this is not a rendering preference.",
    )
    coverage: CoverageView | None = None


class WorkRoot(ApiModel):
    """A work's top-level containers, the entry point for browsing it.

    Returns the level descriptor beside the passages because the four works enter at four
    different levels -- 10 Mandalas, 20 Kandas, 40 Adhyayas, 4 Samavedic Collections -- and
    a client that had only the rows would have to infer the level from their labels.
    """

    work_id: str
    veda: str
    display_label: str
    traditional_name: str | None = None
    root_level: HierarchyLevel | None = None
    results: Paginated[PassageSummary]
