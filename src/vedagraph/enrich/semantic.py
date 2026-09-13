"""The bounded, model-based layer: packet selection in, validated candidates out.

This is the only part of the enrichment release that is not deterministic, and it is
built so that the non-determinism is contained rather than pervasive. Three stages, and
the model only touches the middle one:

1. :func:`select_passages` and :func:`build_packets` choose which passages to ask about
   and assemble exactly what the model may see. Both are deterministic: the same corpus
   produces the same packets in the same order, so a run is reproducible up to the model
   call and the selection can be audited without an API key.
2. The model reads a packet and proposes relations. That step is not byte-deterministic
   and this module never pretends it is -- the run record stores the model id, the prompt
   policy and the packet digest, which is what reproducibility means for this layer.
3. :func:`ingest_extractions` validates every proposal against the controlled vocabulary
   and against the packet it came from, and writes what survives as
   ``LLM_EXTRACTED`` / ``CANDIDATE``. Nothing here can produce an ``ACCEPTED`` row:
   :class:`~vedagraph.enrich.provenance.Provenance` refuses the combination outright.

The rejection rules are the substance of the module. A proposal is rejected when it names
a predicate outside the frozen whitelist, when it names a passage that was not in its own
packet, when its evidence quote does not occur in the packet's text, or when it exceeds
the per-passage cap. The last two matter most: an unquoted assertion cannot be checked, and
a model given room to enumerate will enumerate.

Selection is deliberately biased toward the passages where a semantic layer is worth the
most: ones that have a translation to read, that participate in a cross-Veda parallel, that
carry an identified deity, and that come from a Veda other than the Rigveda -- because the
Rigveda already has a semantic pilot and the other three have nothing.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import orjson

from vedagraph.enrich.corpus import Corpus, MantraRecord
from vedagraph.enrich.guards import (
    MAX_SEMANTIC_ASSERTIONS_PER_PASSAGE,
    MAX_SEMANTIC_PASSAGES,
)
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    RunReport,
    TrustClass,
    run_id,
)
from vedagraph.enrich.records import SemanticCandidateRow
from vedagraph.semantic.ontology import (
    ALLOWED_PREDICATES,
    FORBIDDEN_PREDICATES,
    ONTOLOGY_VERSION,
    SemanticNodeType,
    SemanticPredicate,
    predicate_rule,
)

PACKET_VERSION = "vedagraph-enrichment-semantic-packet-v1"
PROMPT_POLICY = "vedagraph-enrichment-semantic-prompt-v1"


@dataclass(frozen=True)
class SemanticPacket:
    """Everything the model is shown about one passage, and nothing else.

    The digest is over the packet's own content. It is stored on every assertion derived
    from the packet, so a candidate can be tied back to the exact evidence that produced
    it even after the corpus moves on.
    """

    passage_key: str
    veda: str
    citation: str
    sanskrit: str
    translations: tuple[str, ...]
    devatas: tuple[str, ...]
    rishis: tuple[str, ...]
    chandas: tuple[str, ...]
    concepts: tuple[str, ...]
    cross_veda_parallels: tuple[str, ...]

    @property
    def digest(self) -> str:
        payload = orjson.dumps(self.as_dict(), option=orjson.OPT_SORT_KEYS)
        return hashlib.blake2b(payload, digest_size=16).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "passage_key": self.passage_key,
            "veda": self.veda,
            "citation": self.citation,
            "sanskrit": self.sanskrit,
            "translations": list(self.translations),
            "devatas": list(self.devatas),
            "rishis": list(self.rishis),
            "chandas": list(self.chandas),
            "concepts": list(self.concepts),
            "cross_veda_parallels": list(self.cross_veda_parallels),
        }

    def quotable_text(self) -> str:
        """The text an evidence quote must be found in.

        Both the Sanskrit and the translations, because a claim may be grounded in either.
        Nothing else: a quote from the deity name or the citation is not evidence about
        what the passage says.
        """
        return "\n".join([self.sanskrit, *self.translations])


def _priority(mantra: MantraRecord, parallel_partners: dict[str, list[str]]) -> tuple[int, ...]:
    """Sort key for packet selection. Lower is selected first.

    Ranked, not scored, because the criteria are not commensurable and a weighted sum
    would just hide the ordering decision inside three arbitrary constants.
    """
    return (
        0 if mantra.has_translation else 1,
        0 if parallel_partners.get(mantra.passage_key) else 1,
        0 if mantra.veda != "RV" else 1,
        0 if mantra.devatas else 1,
        # Final tiebreak on a content hash rather than on canonical key: keying on the key
        # would fill the whole budget from the front of Mandala 1.
        int(hashlib.blake2b(mantra.passage_key.encode(), digest_size=4).hexdigest(), 16),
    )


def select_passages(
    corpus: Corpus,
    parallel_partners: dict[str, list[str]],
    limit: int = MAX_SEMANTIC_PASSAGES,
) -> list[MantraRecord]:
    """Choose the bounded set of passages worth asking a model about."""
    ranked = sorted(corpus.mantras, key=lambda m: _priority(m, parallel_partners))
    return ranked[:limit]


def build_packets(
    passages: Sequence[MantraRecord],
    parallel_partners: dict[str, list[str]],
    concepts_by_passage: dict[str, list[str]],
) -> list[SemanticPacket]:
    """Assemble one packet per selected passage, in a stable order."""
    return [
        SemanticPacket(
            passage_key=m.passage_key,
            veda=m.veda,
            citation=m.citation,
            sanskrit=m.surfaces.source,
            translations=m.translations[:2],
            devatas=m.devatas,
            rishis=m.rishis,
            chandas=m.chandas,
            concepts=tuple(sorted(concepts_by_passage.get(m.passage_key, ()))),
            cross_veda_parallels=tuple(sorted(parallel_partners.get(m.passage_key, ()))),
        )
        for m in sorted(passages, key=lambda m: m.passage_key)
    ]


@dataclass
class Extraction:
    """One proposal, exactly as the model returned it, before any validation."""

    passage_key: str
    predicate: str
    object_label: str
    object_type: str
    evidence_quote: str
    confidence: float
    notes: str = ""


@dataclass
class IngestReport:
    """What survived validation and, more usefully, what did not."""

    report: RunReport = field(default_factory=lambda: RunReport("semantic_candidates"))
    rejected_examples: dict[str, list[str]] = field(default_factory=dict)

    def reject(self, reason: str, detail: str) -> None:
        self.report.reject(reason)
        self.rejected_examples.setdefault(reason, []).append(detail)


@dataclass(frozen=True)
class ObjectVocabulary:
    """The nodes a semantic assertion is allowed to point at.

    Closed on purpose. An earlier shape of this module minted an object key from whatever
    label the model returned, which meant every proposal succeeded and the graph grew a new
    node type whose members existed only because a model had named them once. That is the
    failure the whole enrichment brief is written against: it produces edges that look like
    findings, resolve to nothing, and cannot be validated.

    So a proposal must name a Concept from the registry or a Devata from the entity
    registry, and anything else is rejected and counted. The cost is real -- the model
    cannot report a relation to something the ontology has no node for -- and it is the
    right cost, because that gap is then visible in the rejection report as a concrete
    request for a new concept rather than invisible as a stray node.
    """

    concepts: dict[str, str]
    devatas: dict[str, str]

    def resolve(self, label: str) -> tuple[str, str] | None:
        """Return ``(node_kind, key)`` for a label the vocabulary knows, else ``None``.

        Matches on the key itself and on the registered labels, casefolded. Deliberately
        not fuzzy: a near-miss resolved by edit distance is a guess about what the model
        meant, and a rejected proposal costs less than a wrong edge.
        """
        needle = label.strip().casefold()
        for key, name in self.concepts.items():
            if needle in (key.casefold(), name.casefold()):
                return "Concept", key
        for key, name in self.devatas.items():
            if needle in (key.casefold(), name.casefold()):
                return "Devata", key
        return None


def _normalise_for_quote_check(text: str) -> str:
    """Casefolded, whitespace-collapsed text for containment checking.

    Not a semantic comparison: the only question is whether the quoted string is present
    in what the model was shown. A model that paraphrases its evidence has not supplied
    evidence, and this is the check that says so.
    """
    return " ".join(text.casefold().split())


def ingest_extractions(
    extractions: Sequence[Extraction],
    packets: Sequence[SemanticPacket],
    vocabulary: ObjectVocabulary,
    model: str,
) -> tuple[list[SemanticCandidateRow], IngestReport]:
    """Validate model proposals and turn the survivors into candidate rows."""
    by_key = {packet.passage_key: packet for packet in packets}
    ingest = IngestReport()
    per_passage: dict[str, int] = {}
    rows: list[SemanticCandidateRow] = []
    stage_run = run_id("semantic", model, PROMPT_POLICY, ONTOLOGY_VERSION, len(packets))

    for extraction in sorted(
        extractions, key=lambda e: (e.passage_key, e.predicate, e.object_label)
    ):
        packet = by_key.get(extraction.passage_key)
        if packet is None:
            ingest.reject("passage_not_in_any_packet", extraction.passage_key)
            continue

        try:
            predicate = SemanticPredicate(extraction.predicate)
        except ValueError:
            ingest.reject("predicate_unknown", extraction.predicate)
            continue
        if predicate in FORBIDDEN_PREDICATES:
            ingest.reject("predicate_refused_by_name", str(predicate))
            continue
        if predicate not in ALLOWED_PREDICATES:
            ingest.reject("predicate_not_whitelisted", str(predicate))
            continue

        rule = predicate_rule(predicate)
        if rule is None:
            ingest.reject("predicate_has_no_rule", str(predicate))
            continue

        try:
            node_type = SemanticNodeType(extraction.object_type)
        except ValueError:
            ingest.reject("object_type_unknown", extraction.object_type)
            continue
        if node_type not in rule.object_types:
            ingest.reject("object_type_invalid_for_predicate", f"{predicate} <- {node_type}")
            continue

        quote = extraction.evidence_quote.strip()
        if not quote:
            ingest.reject("evidence_missing", f"{extraction.passage_key}/{predicate}")
            continue
        if _normalise_for_quote_check(quote) not in _normalise_for_quote_check(
            packet.quotable_text()
        ):
            ingest.reject("evidence_not_in_packet", f"{extraction.passage_key}: {quote[:60]}")
            continue

        resolved = vocabulary.resolve(extraction.object_label)
        if resolved is None:
            ingest.reject(
                "object_not_in_vocabulary",
                f"{extraction.passage_key}: {extraction.object_label!r}",
            )
            continue
        object_kind, object_key = resolved

        used = per_passage.get(extraction.passage_key, 0)
        if used >= MAX_SEMANTIC_ASSERTIONS_PER_PASSAGE:
            ingest.report.cap("assertions_per_passage")
            continue
        per_passage[extraction.passage_key] = used + 1

        confidence = max(0.0, min(1.0, float(extraction.confidence)))
        rows.append(
            SemanticCandidateRow(
                passage_key=packet.passage_key,
                veda=packet.veda,
                predicate=str(predicate),
                object_kind=object_kind,
                object_key=object_key,
                object_label=extraction.object_label.strip(),
                confidence=confidence,
                provenance=Provenance(
                    trust=TrustClass.LLM_EXTRACTED,
                    method=f"semantic-extraction/{ONTOLOGY_VERSION}",
                    score=confidence,
                    evidence=(
                        EvidenceSpan(
                            locator=packet.passage_key,
                            surface=f"packet:{packet.digest}",
                            quote=quote[:500],
                        ),
                    ),
                    state=AssertionState.CANDIDATE,
                    run_id=stage_run,
                    model=model,
                    prompt_policy=PROMPT_POLICY,
                    notes=extraction.notes[:300],
                ),
            )
        )

    ingest.report.produced = len(rows)
    ingest.report.notes = {
        "packets": len(packets),
        "proposals": len(extractions),
        "ontology_version": ONTOLOGY_VERSION,
        "packet_version": PACKET_VERSION,
        "model": model,
        "rejected_examples": {
            reason: examples[:5] for reason, examples in sorted(ingest.rejected_examples.items())
        },
    }
    return rows, ingest
