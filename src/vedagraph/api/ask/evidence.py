"""The evidence packet: what retrieval found, frozen, before any prompt exists.

The packet is built and closed *before* synthesis, and the model receives nothing else.
That ordering is the product's whole claim to being grounded: there is no step at which
the model can fetch more, so an assertion in the answer either traces to an item here or
is unsupported, and the citation validator can prove which.

**Every item carries its own epistemic status.** An item is not just a fact -- it is a fact
plus how it came to be known. A passage translation is a 19th-century English rendering, a
deity mention is graded for referent certainty, a formula family is a normalised-string
match rather than a tradition of reuse, and an interpretive claim is one scholar's reading
with a named falsifier. Flattening those into undifferentiated "context" is how a
retrieval system produces confident nonsense, so :meth:`EvidencePacket.as_prompt` renders
the qualifier inline with the content rather than in a preamble the model may not carry
through to the sentence it writes.

**Absence gets an item.** :data:`EvidenceItemType.LEXICAL_PRESENCE` exists so that "we
searched all four corpora for this term and here is what each surface could have shown"
is a positive statement in the packet. Without it, a term that occurs nowhere produces an
*empty* packet, and an empty packet is what a model answers from memory.

The budget is ranked, not truncated arbitrarily: see :data:`_TYPE_PRIORITY`.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Final

from vedagraph.api.ask.models import EvidenceItem, EvidenceItemType
from vedagraph.api.ask.retriever import SURFACE_LIMITS, RetrievalResult

#: How many items reach the prompt. Bounded because a packet that dumps 200 passages
#: costs latency and tokens while burying the three rows that answer the question.
DEFAULT_BUDGET: Final = 22

#: Which kinds of evidence survive the budget when there are more than fit. Source-stated
#: text outranks derived figures, which outrank interpretation -- the same ordering the
#: rest of the product uses. Interpretation is last on purpose: it is the item type most
#: likely to be restated as fact, so it earns its place only when there is room.
_TYPE_PRIORITY: Final[dict[EvidenceItemType, int]] = {
    EvidenceItemType.PASSAGE: 0,
    EvidenceItemType.LEXICAL_PRESENCE: 1,
    EvidenceItemType.ENTITY_FACT: 2,
    EvidenceItemType.ATTRIBUTION: 3,
    EvidenceItemType.CORPUS_DISTRIBUTION: 4,
    EvidenceItemType.TEXTUAL_REUSE: 5,
    EvidenceItemType.FORMULA_FAMILY: 6,
    EvidenceItemType.GRAPH_PATH: 7,
    EvidenceItemType.METRIC: 8,
    EvidenceItemType.INTERPRETIVE_CLAIM: 9,
}

#: Truncation bounds for quoted text inside the prompt. A whole hymn's translation in an
#: evidence item spends budget a second passage would use better.
_MAX_TRANSLATION = 420
_MAX_SANSKRIT = 260


@dataclass
class EvidencePacket:
    """A closed set of evidence items with stable ids."""

    items: list[EvidenceItem] = field(default_factory=list)

    #: Vedas where a term was searched for and could not have been found, whatever the
    #: text says. Carried on the packet rather than inside an item because it constrains
    #: the *whole* answer, not one citation.
    unsearchable_vedas: list[str] = field(default_factory=list)

    def citation_ids(self) -> set[str]:
        return {item.id for item in self.items}

    def by_id(self) -> dict[str, EvidenceItem]:
        return {item.id: item for item in self.items}

    def has_interpretive_content(self) -> bool:
        return any(item.type is EvidenceItemType.INTERPRETIVE_CLAIM for item in self.items)

    def as_prompt(self) -> str:
        """Render for the model. Each item's qualifier travels with its content."""
        if not self.items:
            return (
                "NO EVIDENCE RETRIEVED. No VedaGraph channel returned anything for this "
                "question. You must say that the graph does not answer it. Do not "
                "supply an answer from background knowledge."
            )
        return "\n\n".join(_render(item) for item in self.items)


def _render(item: EvidenceItem) -> str:
    """One evidence item as prompt text."""
    head = f"[{item.id}] {item.type.value}"
    lines: list[str] = []

    if item.citation:
        locus = item.citation
        if item.veda:
            locus += f" ({item.veda})"
        lines.append(f"  locus: {locus}")
    if item.entity_label:
        label = item.entity_label
        if item.entity_type:
            label += f" [{item.entity_type}]"
        lines.append(f"  subject: {label}")
    if item.sanskrit:
        lines.append(f"  sanskrit: {item.sanskrit[:_MAX_SANSKRIT]}")
    if item.translation:
        lines.append(f"  translation: {item.translation[:_MAX_TRANSLATION]}")
    if item.fact:
        lines.append(f"  fact: {item.fact}")
    if item.claim_text:
        lines.append(f"  claim: {item.claim_text}")
    if item.claim_source:
        lines.append(f"  asserted_by: {item.claim_source}")
    if item.relationship_type:
        lines.append(f"  relation: {item.relationship_type}")
    # The qualifier is last so it is the nearest line to whatever the model writes next.
    if item.qualifier:
        lines.append(f"  QUALIFIER: {item.qualifier}")

    return head + "\n" + "\n".join(lines)


def _ids() -> Iterator[str]:
    n = 0
    while True:
        n += 1
        yield f"E{n}"


# ---------------------------------------------------------------------------
# Per-channel qualifiers. Measured statements about what a row can support.
# ---------------------------------------------------------------------------

_TRANSLATION_QUALIFIER: Final = (
    "This English wording is a 19th-century translation (Griffith/Whitney), not the "
    "Sanskrit. Do not present it as a literal rendering."
)

_CERTAINTY_QUALIFIER: Final[dict[str, str]] = {
    "DEITY_CERTAIN": "Referent graded CERTAIN: this is the deity, not the common noun.",
    "DEITY_PROBABLE": "Referent graded PROBABLE: most likely the deity, not certain.",
    "DEITY_AMBIGUOUS": "Referent graded AMBIGUOUS: may be the common noun rather than "
    "the deity. Do not count this as a deity occurrence.",
}

_ASCRIPTION_QUALIFIER: Final[dict[str, str]] = {
    "PER_PASSAGE": "The source states this attribution of this verse.",
    "CONTAINER_INHERITED": "Inherited: the containing hymn carries this label and it was "
    "projected onto this verse. Not a per-verse statement of the source.",
}

_FORMULA_QUALIFIER: Final = (
    "Formula identity is a normalised-string match over the corpus. Shared wording, NOT "
    "a claim that either passage reuses or quotes the other."
)

_REUSE_QUALIFIER: Final[dict[str, str]] = {
    "REUSES_TEXT_FROM": "A directed reuse claim. All such edges run Samaveda-to-Rigveda.",
    "EXACT_PARALLEL_OF": "Verbatim shared wording between the two passages.",
    "NEAR_PARALLEL_OF": "Close but not verbatim shared wording.",
    "VARIANT_OF": "A textual variant of the same underlying verse.",
    "PARALLEL_TO": "A parallel recorded without a graded method.",
}

_PATH_QUALIFIER: Final = (
    "A shortest path through the graph. A path is not an assertion that the tradition "
    "connects these two things; it means only that these edges exist."
)

_HUB_QUALIFIER: Final = (
    "This route passes through a very high-degree node, which connects thousands of "
    "unrelated verses. It explains little about this specific pair."
)


def _json_or_none(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return value


def build_evidence_packet(
    result: RetrievalResult, *, budget: int = DEFAULT_BUDGET
) -> EvidencePacket:
    """Structure retrieval output into a budgeted, id-stamped, qualified packet."""
    staged: list[EvidenceItem] = []
    ids = _ids()
    seen_passages: set[str] = set()

    # -- lexical presence: the item that makes absence sayable ---------------
    unsearchable: list[str] = []
    if result.lexical is not None:
        unsearchable = result.lexical.unsearchable_vedas()
        per_veda: list[str] = []
        for row in result.lexical.rows:
            veda = str(row["veda"])
            skt_hits = int(row.get("sanskrit_hits") or 0)
            tr_hits = int(row.get("translation_hits") or 0)
            has_skt = int(row.get("with_sanskrit") or 0)
            has_tr = int(row.get("with_translation") or 0)
            per_veda.append(
                f"{veda}: {skt_hits} Sanskrit-surface and {tr_hits} translation-surface "
                f"matches, out of {has_skt} verses carrying Sanskrit and {has_tr} "
                f"carrying a translation"
            )
        notes = [SURFACE_LIMITS[v] for v in sorted(SURFACE_LIMITS) if v in SURFACE_LIMITS]
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.LEXICAL_PRESENCE,
                entity_label=result.lexical.term,
                fact=(
                    f"Lexical search for '{result.lexical.term}' across all four "
                    "corpora. " + "; ".join(per_veda) + "."
                ),
                qualifier=(
                    "A zero here is a search result, NOT textual absence. "
                    + " ".join(notes)
                    + (
                        f" No searchable surface at all for: {', '.join(unsearchable)}."
                        if unsearchable
                        else ""
                    )
                ),
                knowledge_status="PARTIAL",
            )
        )

    # -- passages -----------------------------------------------------------
    for row in result.passages:
        key = row.get("canonical_key")
        if key:
            if key in seen_passages:
                continue
            seen_passages.add(str(key))
        certainty = row.get("certainty")
        qualifier_parts: list[str] = []
        if row.get("translation") and not row.get("sanskrit"):
            qualifier_parts.append(_TRANSLATION_QUALIFIER)
        if certainty and certainty in _CERTAINTY_QUALIFIER:
            qualifier_parts.append(_CERTAINTY_QUALIFIER[str(certainty)])
        if row.get("relation_type") == "TRANSLATION_MATCH":
            qualifier_parts.append(
                "Found by matching the English translation, so the match is in the "
                "translator's wording and not necessarily in the Sanskrit."
            )
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.PASSAGE,
                passage_key=str(key) if key else None,
                citation=row.get("canonical_citation"),
                veda=row.get("veda"),
                sanskrit=row.get("sanskrit"),
                translation=row.get("translation"),
                relationship_type=row.get("relation_type"),
                qualifier=" ".join(qualifier_parts) or None,
                knowledge_status="SUPPORTED",
            )
        )

    # -- ascriptions, kept apart from mentions ------------------------------
    for row in result.ascription_passages:
        precision = str(row.get("attribution_precision") or "")
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.ATTRIBUTION,
                passage_key=row.get("canonical_key"),
                citation=row.get("canonical_citation"),
                veda=row.get("veda"),
                translation=row.get("translation"),
                entity_label=row.get("_entity_label"),
                relationship_type=row.get("relation_type"),
                fact=(
                    f"This verse is ascribed to {row.get('_entity_label')} by the "
                    "Anukramani apparatus (HAS_DEVATA), which is dedication and not "
                    "mention."
                ),
                qualifier=_ASCRIPTION_QUALIFIER.get(precision),
                knowledge_status="SUPPORTED",
            )
        )

    # -- entity profiles ----------------------------------------------------
    for row in result.entity_profiles:
        facts: list[str] = []
        if row.get("description"):
            facts.append(str(row["description"]))
        if row.get("sanskrit_label"):
            facts.append(f"Sanskrit label: {row['sanskrit_label']}")
        if row.get("devata_subtype"):
            facts.append(f"Deity subtype: {row['devata_subtype']}")
        if row.get("condition_kind"):
            facts.append(f"Condition kind: {row['condition_kind']}")
        if row.get("occurrence_count") is not None:
            facts.append(f"Registry occurrence count: {row['occurrence_count']}")
        qualifier = row.get("attribution_scope_note")
        if row.get("_match_rank") == "TOKEN_IN_LABEL":
            qualifier = (
                f"Resolved from the question's word '{row.get('_asked_as')}' by matching "
                "one word of this entity's label, not the whole label."
            ) + (f" {qualifier}" if qualifier else "")
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.ENTITY_FACT,
                entity_key=row.get("entity_key"),
                entity_label=row.get("label"),
                entity_type=row.get("entity_type"),
                fact="; ".join(facts) if facts else None,
                qualifier=qualifier,
                knowledge_status="SUPPORTED",
            )
        )

    # -- corpus distribution, with all three certainty tiers ----------------
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in result.entity_by_veda:
        grouped.setdefault(str(row.get("_entity_key")), []).append(row)

    for rows in grouped.values():
        label = rows[0].get("_entity_label")
        parts: list[str] = []
        ambiguous_total = 0
        for row in rows:
            certain = int(row.get("certain") or 0)
            probable = int(row.get("probable") or 0)
            ambiguous = int(row.get("ambiguous") or 0)
            ungraded = int(row.get("ungraded") or 0)
            ambiguous_total += ambiguous
            counted = certain + probable + ungraded
            # The relation is part of the measurement, not decoration. The channel
            # returns one row per (veda, relation_type), so an unlabelled join printed
            # "AV: 68 verses; AV: 68 verses; AV: 66 verses" -- three different questions
            # answered in one breath, with nothing to say which was which. A reader could
            # only read it as one corpus counted three times, and summing it gives 202
            # verses in a corpus that has 68. Worse, the counts being merged are exactly
            # the attribution/mention distinction this API is required never to blur:
            # PROTECTS_FROM, MENTIONS_ENTITY and ABOUT_CONCEPT are different claims.
            relation = str(row.get("relation_type") or "").strip()
            detail = (
                f"{row['veda']} via {relation}: {counted} verses"
                if relation
                else (f"{row['veda']}: {counted} verses")
            )
            if certain or probable:
                detail += f" ({certain} certain, {probable} probable)"
            if ambiguous:
                detail += f", plus {ambiguous} ambiguous excluded"
            parts.append(detail)
        # One type only when every row agrees. Naming the first row's relation while the
        # fact carried three made the item assert a relationship it had not measured.
        relations = list(
            dict.fromkeys(str(r.get("relation_type")) for r in rows if r.get("relation_type"))
        )
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.CORPUS_DISTRIBUTION,
                entity_label=label,
                entity_key=rows[0].get("_entity_key"),
                relationship_type=" / ".join(relations) if relations else None,
                fact=f"Verses per corpus for {label} — " + "; ".join(parts) + ".",
                qualifier=(
                    "Counts default to CERTAIN plus PROBABLE referents; "
                    f"{ambiguous_total} AMBIGUOUS occurrences are excluded because in "
                    "Vedic Sanskrit the deity's name is also an ordinary noun. Each "
                    "figure counts one relationship type; the same verse can appear "
                    "under several, so figures for one corpus must not be added "
                    "together. A corpus "
                    "with no row here was not reached by this annotation layer, which is "
                    "not the same as the text being silent."
                ),
                knowledge_status="SUPPORTED",
            )
        )

    # -- textual reuse ------------------------------------------------------
    for row in result.parallels:
        relation = str(row.get("relation_type") or "")
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.TEXTUAL_REUSE,
                passage_key=row.get("canonical_key"),
                citation=row.get("canonical_citation"),
                veda=row.get("veda"),
                translation=row.get("translation"),
                relationship_type=relation,
                qualifier=_REUSE_QUALIFIER.get(relation),
                knowledge_status="SUPPORTED",
            )
        )

    # -- formula families ---------------------------------------------------
    for row in result.formulas:
        veda_counts = _json_or_none(row.get("veda_counts"))
        spread = ""
        if isinstance(veda_counts, dict):
            spread = " Per corpus: " + ", ".join(
                f"{k}: {v}" for k, v in sorted(veda_counts.items())
            )
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.FORMULA_FAMILY,
                entity_label=row.get("display_form") or row.get("family_id"),
                fact=(
                    f"Formula family with {row.get('member_count')} members and "
                    f"{row.get('occurrence_count')} occurrences."
                    f"{spread}"
                    + (
                        " Occurs in more than one Veda."
                        if row.get("cross_veda")
                        else " Confined to a single Veda."
                    )
                ),
                qualifier=_FORMULA_QUALIFIER,
                knowledge_status="SUPPORTED",
            )
        )

    # -- graph paths --------------------------------------------------------
    for row in result.graph_paths:
        nodes = [str(n) for n in (row.get("node_labels") or [])]
        rels = [str(r) for r in (row.get("rel_types") or [])]
        if not nodes or not rels:
            continue
        rendered = nodes[0]
        # A path has one fewer edge than nodes, so the lengths differ by design.
        for rel, node in zip(rels, nodes[1:], strict=False):
            rendered += f" -[{rel}]- {node}"
        degree = int(row.get("max_degree") or 0)
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.GRAPH_PATH,
                source_label=nodes[0],
                target_label=nodes[-1],
                relationship_type=" / ".join(dict.fromkeys(rels)),
                fact=f"Path: {rendered}",
                qualifier=(
                    _PATH_QUALIFIER
                    + (f" {_HUB_QUALIFIER} (degree {degree:,})" if degree > 1500 else "")
                ),
                knowledge_status="SUPPORTED",
            )
        )

    # -- derived metrics ----------------------------------------------------
    for row in result.derived_metrics:
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.METRIC,
                entity_key=row.get("subject_key"),
                entity_label=row.get("metric_name"),
                fact=f"{row.get('metric_name')}: {row.get('values_json')}",
                qualifier=(
                    "A figure this project derived, not a statement of the text. "
                    + str(row.get("scope_note") or "")
                ).strip(),
                knowledge_status="SUPPORTED",
            )
        )

    # -- interpretation, labelled as such -----------------------------------
    for row in result.interpretive_claims:
        falsifier = row.get("falsifier")
        staged.append(
            EvidenceItem(
                id=next(ids),
                type=EvidenceItemType.INTERPRETIVE_CLAIM,
                claim_text=row.get("claim_text"),
                claim_source=row.get("asserted_by"),
                entity_key=row.get("about"),
                fact=f"Claim type: {row.get('claim_type')}; scope: {row.get('scope')}",
                qualifier=(
                    "This is ONE INTERPRETATION represented in VedaGraph, not what the "
                    "text states. Attribute it to its source when using it."
                    + (f" It would be falsified by: {falsifier}" if falsifier else "")
                ),
                knowledge_status="INTERPRETIVE",
            )
        )

    # Rank by type priority, keep original order within a type, then cut to budget and
    # renumber so the ids a model sees are contiguous.
    staged.sort(key=lambda item: _TYPE_PRIORITY.get(item.type, 99))
    kept = staged[:budget]

    renumber = _ids()
    final = [item.model_copy(update={"id": next(renumber)}) for item in kept]

    return EvidencePacket(items=final, unsearchable_vedas=unsearchable)
