"""The deterministic heuristic baseline: cue matching over one evidence packet.

This module is the producer that authored the historical V3 pilot artefacts. It is
regular expressions over Griffith's English, and nothing in it is a model. It is kept
because it is useful — it exercises the typed-object schema, the normalization layer,
the evidence validator and the batch machinery without a model in the loop, and it is
byte-reproducible, which makes it a fixture generator no model can be.

It is not, and must never be labelled as, semantic extraction by ``gpt-5.6-luna``.
Everything it emits carries :data:`BASELINE_PROVENANCE` in the model field, which the
full-run validator rejects, so this path cannot reach a model-provenanced run. See
``docs/architecture/SEMANTIC_V3_PROVENANCE_CORRECTION.md``.

Its two known defects are recorded rather than hidden. Verse-wide cue scope (B01) means
a cue anywhere in the verse can combine with an entity anywhere else; that is a property
of cue matching and is not fixable here, which is why the real extraction path requires a
model to author assertion-specific binding evidence. Span anchoring (B02) *is* fixed:
anchors resolve through :mod:`vedagraph.semantic.spans`, so a span never lands inside an
unrelated word, and an anchor that occurs more than once yields no span at all.
"""

# Evidence notes are intentionally explicit and readable in serialized output.
# ruff: noqa: E501

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from vedagraph.models.normalization import (
    ActionEvent,
    SemanticEvidenceAnchor,
    SemanticExtractionV3,
    SemanticObjectCandidate,
    StructuredSemanticAssertion,
    TranslationSpan,
)
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.normalization import deterministic_object_candidate_id
from vedagraph.semantic.object_ontology import (
    SemanticObjectKind,
    SemanticObjectNormalizationStatus,
    SemanticOntologyGapCode,
)
from vedagraph.semantic.ontology import SemanticPredicate
from vedagraph.semantic.registry import normalize_label
from vedagraph.semantic.spans import first_anchor
from vedagraph.semantic.v3 import OBJECT_SCHEMA_VERSION, PREDICATE_CHECKS, PROMPT_VERSION

#: What the model field says when no model authored the payload. The full-run validator
#: requires the run's model here, so baseline output cannot be committed to a model run.
BASELINE_PROVENANCE = "DETERMINISTIC_HEURISTIC_BASELINE"

#: The run identifier the historical V3 120-mantra pilot was authored under. Supplied so
#: that replaying that artefact is possible; new baseline runs must name their own.
HISTORICAL_V3_120_RUN_ID = "vedagraph-rigveda-semantic-luna-v3-120"


@dataclass
class V3Draft:
    packet: EvidencePacket
    run_id: str
    assertions: list[StructuredSemanticAssertion]
    ontology_gaps: list[SemanticObjectCandidate]
    status: dict[str, str]
    notes: dict[str, str]

    @property
    def text(self) -> str:
        return self.packet.translation.text or "" if self.packet.translation else ""

    @property
    def folded(self) -> str:
        return normalize_label(self.text)


def _translation_span(packet: EvidencePacket, terms: Iterable[str]) -> TranslationSpan | None:
    """Anchor a cue into the translation exactly as stored, or refuse.

    Offsets are into ``packet.translation.text`` and nothing else: the cue that produced
    them was found in the folded text, which is a different string of a different length,
    so it may not supply offsets. A cue that occurs more than once yields no span, because
    the baseline has no way to know which occurrence its assertion came from.
    """
    if packet.translation is None or packet.translation.text is None:
        return None
    anchor = first_anchor(packet.translation.text, [term for term in terms if term])
    if anchor is None:
        return None
    return TranslationSpan(start=anchor.start, end=anchor.end)


def _evidence(
    packet: EvidencePacket,
    *,
    terms: Iterable[str] = (),
    token_ids: Iterable[str] = (),
    other_ids: Iterable[str] = (),
) -> list[SemanticEvidenceAnchor]:
    translation_id = packet.translation.translation_id if packet.translation else None
    span = _translation_span(packet, terms)
    anchor = SemanticEvidenceAnchor(
        source_passage_id=packet.passage_key,
        translation_record_id=translation_id,
        translation_span=span,
        token_ids=sorted(set(token_ids)),
        passage_ids=[packet.passage_key],
        other_evidence_ids=sorted(set(other_ids)),
    )
    return [anchor]


def _tokens_for(packet: EvidencePacket, terms: Iterable[str]) -> list[str]:
    folded_terms = [normalize_label(term) for term in terms if term]
    if not folded_terms:
        return []
    return [
        token.token_key
        for token in packet.tokens
        if any(
            term in normalize_label(token.surface) or term in normalize_label(token.lemma)
            for term in folded_terms
        )
    ]


def _word_forms(value: str) -> set[str]:
    """Make only orthographic variants for packet-local matching, never semantic aliases."""
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(char for char in folded if not unicodedata.combining(char)).casefold()
    folded = re.sub(r"[^a-z0-9 ]+", " ", folded)
    forms = {item for item in folded.split() if len(item) >= 3}
    for item in tuple(forms):
        if item.endswith("h"):
            forms.add(item[:-1])
        if item.endswith("a"):
            forms.add(item[:-1])
    return forms


def _has_label(text: str, label: str) -> bool:
    return any(re.search(rf"\b{re.escape(form)}\b", text) for form in _word_forms(label))


def _add(
    draft: V3Draft,
    predicate: SemanticPredicate,
    *,
    kind: SemanticObjectKind,
    label: str,
    normalized_head: str | None = None,
    canonical_entity_id: str | None = None,
    beneficiary_entity_id: str | None = None,
    target_entity_id: str | None = None,
    event: ActionEvent | None = None,
    qualifiers: list[str] | None = None,
    terms: Iterable[str] = (),
    token_ids: Iterable[str] = (),
    other_ids: Iterable[str] = (),
    explicitness: str = "EXPLICIT",
    inference_step: str | None = None,
    note: str = "",
) -> None:
    evidence = _evidence(draft.packet, terms=terms, token_ids=token_ids, other_ids=other_ids)
    ordinal = len(draft.assertions) + len(draft.ontology_gaps)
    candidate_id = deterministic_object_candidate_id(
        run_id=draft.run_id,
        mantra_id=draft.packet.passage_key,
        predicate=predicate,
        evidence=evidence,
        ordinal=ordinal,
        legacy_object_id=None,
    )
    status = (
        SemanticObjectNormalizationStatus.CANONICAL_REF
        if kind is SemanticObjectKind.CANONICAL_ENTITY_REF
        else SemanticObjectNormalizationStatus.NORMALIZED_CANDIDATE
    )
    object_candidate = SemanticObjectCandidate(
        candidate_id=candidate_id,
        object_kind=kind,
        normalized_head=normalized_head
        or (None if canonical_entity_id else normalize_label(label)),
        display_label=label,
        qualifiers=qualifiers or [],
        canonical_entity_id=canonical_entity_id,
        beneficiary_entity_id=beneficiary_entity_id,
        target_entity_id=target_entity_id,
        event=event,
        source_passage_id=draft.packet.passage_key,
        evidence=evidence,
        extraction_model=BASELINE_PROVENANCE,
        prompt_version=PROMPT_VERSION,
        normalization_status=status,
        schema_version=OBJECT_SCHEMA_VERSION,
    )
    assertion = StructuredSemanticAssertion(
        assertion_id=f"V3ASSERT:{candidate_id}",
        source_run_id=draft.run_id,
        subject_id=draft.packet.passage_key,
        predicate=predicate,
        object=object_candidate,
        evidence=evidence,
        explicitness=explicitness,
        inference_step=inference_step,
        legacy_assertion_id=f"V3ASSERT:{candidate_id}",
        schema_version=OBJECT_SCHEMA_VERSION,
    )
    draft.assertions.append(assertion)
    draft.status[predicate.value] = "SUPPORTED"
    if note:
        draft.notes[predicate.value] = note


def _add_gap(
    draft: V3Draft,
    *,
    label: str,
    code: SemanticOntologyGapCode,
    terms: Iterable[str],
    note: str,
) -> None:
    evidence = _evidence(draft.packet, terms=terms, token_ids=_tokens_for(draft.packet, terms))
    ordinal = len(draft.assertions) + len(draft.ontology_gaps)
    candidate = SemanticObjectCandidate(
        candidate_id=deterministic_object_candidate_id(
            run_id=draft.run_id,
            mantra_id=draft.packet.passage_key,
            predicate=SemanticPredicate.DESCRIBES,
            evidence=evidence,
            ordinal=ordinal,
            legacy_object_id=code.value,
        ),
        object_kind=SemanticObjectKind.ONTOLOGY_GAP_REF,
        normalized_head=normalize_label(label),
        display_label=label,
        source_passage_id=draft.packet.passage_key,
        evidence=evidence,
        extraction_model=BASELINE_PROVENANCE,
        prompt_version=PROMPT_VERSION,
        normalization_status=SemanticObjectNormalizationStatus.ONTOLOGY_GAP,
        ontology_gap_code=code,
        schema_version=OBJECT_SCHEMA_VERSION,
    )
    draft.ontology_gaps.append(candidate)
    draft.notes[f"GAP_{len(draft.ontology_gaps)}"] = note


def _canonical_mentions(packet: EvidencePacket) -> list[tuple[str, str, list[str]]]:
    return [(item.entity_key, item.entity_label, item.token_keys) for item in packet.mentions]


def extract_packet(
    packet: EvidencePacket, *, run_id: str
) -> tuple[SemanticExtractionV3, dict[str, Any]]:
    """Run the cue matcher over one packet. The caller must name the run it belongs to.

    There is no default run id: a payload that does not know which run authored it is
    exactly the artefact this module exists to stop being mistaken for a model run.
    """
    draft = V3Draft(
        packet=packet,
        run_id=run_id,
        assertions=[],
        ontology_gaps=[],
        status={family: "NOT_SUPPORTED" for family in PREDICATE_CHECKS},
        notes={},
    )
    text = draft.folded
    raw_text = draft.text

    for entity_id, label, token_ids in _canonical_mentions(packet):
        label_present = _has_label(text, label)
        direct = label_present and bool(re.search(r"\b(?:o|hail)\b", text))
        call = label_present and bool(
            re.search(r"\b(?:call|calls|invoke|invokes|entreat|entreats|come nigh|pray)\b", text)
        )
        praise = label_present and bool(
            re.search(r"\b(?:praise|praises|praised|laud|lauds|extol|extols|glorif\w*)\b", text)
        )
        terms = [label]
        if direct or call:
            _add(
                draft,
                SemanticPredicate.INVOKES,
                kind=SemanticObjectKind.CANONICAL_ENTITY_REF,
                label=label,
                canonical_entity_id=entity_id,
                terms=terms,
                token_ids=token_ids,
                other_ids=[f"LEXICAL_MENTION:{entity_id}"],
                note="Direct address or calling language and a deterministic lexical mention are supplied.",
            )
        if praise:
            _add(
                draft,
                SemanticPredicate.PRAISES,
                kind=SemanticObjectKind.CANONICAL_ENTITY_REF,
                label=label,
                canonical_entity_id=entity_id,
                terms=terms,
                token_ids=token_ids,
                other_ids=[f"LEXICAL_MENTION:{entity_id}"],
                note="Laudatory language directly targets a deterministic lexical mention.",
            )
        descriptive = bool(
            re.search(
                r"\b(?:who|which|that|lord|giver|strong|mighty|divine|born|stands|dwells|holds|brings|gives)\b",
                text,
            )
        )
        if descriptive and not direct and not call and not praise:
            _add(
                draft,
                SemanticPredicate.DESCRIBES,
                kind=SemanticObjectKind.CANONICAL_ENTITY_REF,
                label=label,
                canonical_entity_id=entity_id,
                terms=terms,
                token_ids=token_ids,
                other_ids=[f"LEXICAL_MENTION:{entity_id}"],
                note="The supplied wording describes the deterministically mentioned entity.",
            )

    request_patterns = (
        (r"\b(?:protect(?:ion|ing)?|guard(?:ed|s|ing)?|keep .* safe)\b", "protection", "terms"),
        (r"\b(?:wealth|abundance|riches)\b", "wealth", "terms"),
        (r"\b(?:health|wellbeing|well-being)\b", "health", "terms"),
        (r"\b(?:succour|assistance|aid|help)\b", "assistance", "terms"),
        (r"\b(?:shelter|dwelling-place)\b", "shelter", "terms"),
        (r"\b(?:strength|might)\b", "strength", "terms"),
        (r"\b(?:long life|long .* see)\b", "long life", "terms"),
        (r"\b(?:victory|conquer|subdue the foe)\b", "victory", "terms"),
        (r"\b(?:offspring|sons?)\b", "offspring", "terms"),
        (r"\b(?:presence|come nigh|stand by us)\b", "presence", "terms"),
    )
    request_cue = bool(
        re.search(r"\b(?:may|grant|give|send|vouchsafe|bestow|bring|come|keep|let|pray)\b", text)
    )
    for pattern, label, _ in request_patterns:
        match = re.search(pattern, text)
        if request_cue and match:
            _add(
                draft,
                SemanticPredicate.REQUESTS,
                kind=SemanticObjectKind.REQUESTED_OUTCOME,
                label=label,
                terms=[match.group(0)],
                token_ids=_tokens_for(packet, [match.group(0)]),
                explicitness="EXPLICIT",
                note="The supplied translation directly states a desired outcome and its concise head.",
            )

    action_patterns = (
        (r"\b(?:slay|slays|slew|smitten|smiting|destroy|destroys|destroyed|destroying)\b", "slay"),
        (r"\b(?:release|released|releasing|opening|opened|unlock|unlocks)\b", "release"),
        (r"\b(?:pour|pours|poured|pouring|effused)\b", "pour"),
        (r"\b(?:sent|sends|sending|brought|brings|bringing)\b", "send"),
        (r"\b(?:protected|protects|protecting|guarded|guards|keeping)\b", "protect"),
        (r"\b(?:fed|feeds|feeding)\b", "feed"),
        (r"\b(?:pressed|pressing|washed|washing|filtered|filtering|flowing)\b", "process"),
    )
    for pattern, head in action_patterns:
        match = re.search(pattern, text)
        if match:
            _add(
                draft,
                SemanticPredicate.DESCRIBES_ACTION,
                kind=SemanticObjectKind.EVENT,
                label=f"{head} action",
                normalized_head=head,
                event=ActionEvent(action_head=head),
                terms=[match.group(0)],
                token_ids=_tokens_for(packet, [match.group(0)]),
                note="The concise action head is directly present in supplied translation evidence.",
            )
            break

    ritual = re.search(
        r"\b(?:sacrifice|sacrificial|oblation|libation|ritual|rite|altar|press\w*|offering)\w*\b",
        text,
    )
    if ritual:
        ritual_label = (
            "Soma pressing" if "press" in ritual.group(0) and "soma" in text else ritual.group(0)
        )
        _add(
            draft,
            SemanticPredicate.INVOLVES_RITUAL,
            kind=SemanticObjectKind.RITUAL_EVENT,
            label=ritual_label,
            terms=[ritual.group(0)],
            token_ids=_tokens_for(packet, [ritual.group(0)]),
            note="A named ritual act is present in the supplied translation.",
        )
    offering = re.search(
        r"\b(?:oblation|libation|offering|sacrifice|juices? poured|meath-drops?)\b", text
    )
    if offering:
        _add(
            draft,
            SemanticPredicate.INVOLVES_OFFERING,
            kind=SemanticObjectKind.OFFERING_REF,
            label="oblation" if offering.group(0) == "oblation" else "offering",
            terms=[offering.group(0)],
            token_ids=_tokens_for(packet, [offering.group(0)]),
            note="The supplied wording presents a thing in an offering role.",
        )

    for pattern, label in (
        (r"\bpavamana soma\b", "Pavamana Soma"),
        (r"\bsoma\b", "Soma"),
        (r"\bmeath\b|\bjuices?\b", "meath"),
        (r"\bmilk\b", "milk"),
        (r"\bwaters?\b", "water"),
        (r"\bmedicines?\b", "medicine"),
        (r"\bfood\b", "food"),
    ):
        match = re.search(pattern, text)
        if match:
            _add(
                draft,
                SemanticPredicate.INVOLVES_SUBSTANCE,
                kind=SemanticObjectKind.SUBSTANCE_REF,
                label=label,
                terms=[match.group(0)],
                token_ids=_tokens_for(packet, [match.group(0)]),
                note="A physical material is directly named in the supplied translation.",
            )

    for pattern, label in (
        (r"\bdawn\b|\bmorn\b|\bsunrise\b", "dawn"),
        (r"\brain\b|\brains\b", "rain"),
        (r"\bwind\b|\bwind's\b", "wind"),
        (r"\bwaters?\b|\bfloods?\b", "waters"),
        (r"\blightning\b|\bthunder\b|\bclouds?\b", "storm"),
    ):
        match = re.search(pattern, text)
        if match:
            _add(
                draft,
                SemanticPredicate.REFERS_TO_NATURAL_PHENOMENON,
                kind=SemanticObjectKind.NATURAL_PHENOMENON_REF,
                label=label,
                terms=[match.group(0)],
                token_ids=_tokens_for(packet, [match.group(0)]),
                note="The phenomenon is directly named in the supplied translation; Devata metadata is not used as identity.",
            )
            break

    place = re.search(r"\b(?:river|rivers|pastures|cave|caves|heaven|land)\b", text)
    if place:
        label = place.group(0).rstrip("s")
        _add(
            draft,
            SemanticPredicate.REFERS_TO_PLACE,
            kind=SemanticObjectKind.PLACE_REF,
            label=label,
            terms=[place.group(0)],
            token_ids=_tokens_for(packet, [place.group(0)]),
            note="The supplied translation names a defensible spatial referent.",
        )
    elif re.search(r"\b(?:seat|dwelling|house|station|world|mansion)\b", text):
        draft.status["REFERS_TO_PLACE"] = "UNCERTAIN"
        draft.notes["REFERS_TO_PLACE"] = (
            "Spatial wording is present, but place status is not sufficiently clear; no place assertion was forced."
        )

    state = re.search(
        r"\b(?:yearning|fain|long for|fear|afraid|need|desire|wish|glad|joy|hope)\w*\b",
        raw_text,
        flags=re.IGNORECASE,
    )
    if state:
        head = (
            "yearning" if state.group(0).lower() == "long for" else normalize_label(state.group(0))
        )
        _add(
            draft,
            SemanticPredicate.EXPRESSES,
            kind=SemanticObjectKind.STATE_REF,
            label=head,
            terms=[state.group(0)],
            token_ids=_tokens_for(packet, [state.group(0)]),
            note="A mental or affective state is directly expressed in the supplied translation.",
        )

    if re.search(r"\b(?:person|man|men|woman|women)\b", text):
        _add_gap(
            draft,
            label="person-like referent",
            code=SemanticOntologyGapCode.PERSON_LIKE_REFERENT_UNMODELED,
            terms=["person", "man", "men", "woman", "women"],
            note="A person-like referent is evidenced but not represented as a typed ontology entity.",
        )
    if re.search(r"\b(?:patron|giver)\b", text):
        _add_gap(
            draft,
            label="patron role",
            code=SemanticOntologyGapCode.PATRON_ROLE_UNMODELED,
            terms=["patron", "giver"],
            note="A patron/giver role is evidenced without forcing a person node.",
        )
    if re.search(r"\b(?:ancestor|forefather)\b", text):
        _add_gap(
            draft,
            label="ancestor role",
            code=SemanticOntologyGapCode.ANCESTOR_ROLE_UNMODELED,
            terms=["ancestor", "forefather"],
            note="An ancestor role is evidenced without forcing an unmodeled person node.",
        )
    if re.search(r"\b(?:kinsman|kindred|brother|sister)\b", text):
        _add_gap(
            draft,
            label="kinship role",
            code=SemanticOntologyGapCode.KINSHIP_ROLE_UNMODELED,
            terms=["kinsman", "kindred", "brother", "sister"],
            note="A kinship role is evidenced without forcing an unmodeled person node.",
        )

    no_claim_reasons = (
        []
        if draft.assertions
        else [
            "No predicate family received sufficiently direct packet evidence after the complete fourteen-family checklist."
        ]
    )
    payload = SemanticExtractionV3(
        mantra_id=packet.citation,
        assertions=draft.assertions,
        ontology_gaps=draft.ontology_gaps,
        no_claim_reasons=no_claim_reasons,
    )
    trace = {
        "passage_key": packet.passage_key,
        "checklist_completed": True,
        "families": {
            family: {"status": draft.status[family], "note": draft.notes.get(family, "")}
            for family in PREDICATE_CHECKS
        },
        "assertion_count": len(draft.assertions),
        "ontology_gap_count": len(draft.ontology_gaps),
        "ontology_gap_codes": [
            code.value
            for gap in draft.ontology_gaps
            for code in ([gap.ontology_gap_code] if gap.ontology_gap_code else [])
        ],
    }
    return payload, trace
