"""Assemble the deterministic evidence packet one extraction request is built from.

The packet is the contract between the deterministic layers and the model. Everything in
it is read from a pinned build; nothing in it is generated. If a fact is not here, the
model has not been shown it and may not assert it — which is only enforceable because
the packet is small enough to check an assertion against.

Three deliberate limits:

**Window.** Previous mantra, target mantra, next mantra. Sūkta-level context is offered
as counts and identifiers, not as text. Sending a whole Maṇḍala would cost roughly two
orders of magnitude more per mantra and make every assertion unfalsifiable, because
enough text supports anything.

**No generated translation.** When Griffith has no verse for a mantra the packet says so
with ``translation_missing`` and carries the Sanskrit and its morphology alone. Asking
the model to translate would put a model-authored English sentence into the evidence
chain for every later claim, and the provenance would then be the model citing itself.

**Parallels are named, not resolved.** An exact textual parallel is supplied as an
identifier so the model knows the line recurs. It is not supplied as a licence to copy
an assertion across, because two identical lines in two hymns are not two identical
claims. Whether the extractions agree is measured afterwards, and disagreement is a
signal about the extractor.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from vedagraph.models import Passage, TextVersion, Translation
from vedagraph.models.enums import EntityType
from vedagraph.models.knowledge import KnowledgeAssertion, KnowledgeEntity
from vedagraph.models.lexical import MantraParallel, MentionAssertion, MorphologyToken
from vedagraph.models.semantic import (
    EvidencePacket,
    PacketMention,
    PacketNeighbour,
    PacketToken,
    PacketTranslation,
)
from vedagraph.storage.jsonl import read_jsonl

PACKET_VERSION = "rigveda-semantic-evidence-packet-v1"
CANONICAL_TEXT_VERSION_ID = "GRETIL.RV.AUFRECHT"
TRANSLATION_SOURCE_ID = "WIKISOURCE_GRIFFITH_RV"

#: Recorded on a packet whose mantra has no translation, so the gap is countable in the
#: run report instead of showing up later as unexplained low recall.
INPUT_TRANSLATION_MISSING = "INPUT_TRANSLATION_MISSING"

_METADATA_PREDICATES = {"HAS_RISHI", "HAS_DEVATA", "HAS_CHANDAS"}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PacketSources:
    """Every pinned input the packet builder reads. Assembled once, reused per mantra."""

    passage_ids: dict[str, UUID]
    citations: dict[str, str]
    sanskrit: dict[str, str]
    translations: dict[str, Translation]
    rishis: dict[str, list[str]]
    devatas: dict[str, list[str]]
    chandas: dict[str, list[str]]
    entity_labels: dict[str, str]
    tokens: dict[str, list[MorphologyToken]]
    mentions: dict[str, list[MentionAssertion]]
    exact_parallels: dict[str, list[str]]
    near_parallels: dict[str, list[str]]
    sukta_sizes: dict[str, int]

    @property
    def mantra_keys(self) -> list[str]:
        return sorted(self.passage_ids)


def _sukta_key(passage_key: str) -> str:
    return passage_key.rsplit(":", 1)[0]


def _neighbour_key(passage_key: str, offset: int) -> str:
    head, mantra = passage_key.rsplit(":V", 1)
    number = int(mantra) + offset
    return f"{head}:V{number:03d}" if number >= 1 else ""


def load_packet_sources(
    *,
    corpus_dir: Path,
    knowledge_dir: Path,
    lexical_dir: Path,
) -> PacketSources:
    """Read the three deterministic layers. Nothing here is written back to any of them."""
    passage_ids: dict[str, UUID] = {}
    citations: dict[str, str] = {}
    for passage in read_jsonl(corpus_dir / "passages.jsonl", Passage):
        if passage.entity_type is EntityType.MANTRA:
            passage_ids[passage.canonical_key] = passage.entity_id
            citations[passage.canonical_key] = passage.canonical_citation
    by_id = {value: key for key, value in passage_ids.items()}

    sanskrit: dict[str, str] = {}
    for version in read_jsonl(corpus_dir / "text_versions.jsonl", TextVersion):
        if version.text_version_id != CANONICAL_TEXT_VERSION_ID:
            continue
        key = by_id.get(version.passage_id)
        if key is not None:
            sanskrit[key] = version.text_original

    translations: dict[str, Translation] = {}
    for translation in read_jsonl(corpus_dir / "translations.jsonl", Translation):
        if translation.source_id != TRANSLATION_SOURCE_ID:
            continue
        key = by_id.get(translation.passage_id)
        # One translator, one verse: a later record for the same mantra would mean the
        # build produced two, which is a corpus bug and not something to paper over.
        if key is not None and key not in translations:
            translations[key] = translation

    entity_labels: dict[str, str] = {}
    for filename in ("entities_devatas.jsonl", "entities_rishis.jsonl", "entities_chandas.jsonl"):
        for entity in read_jsonl(knowledge_dir / filename, KnowledgeEntity):
            entity_labels[entity.entity_key] = entity.preferred_label

    grouped: dict[str, dict[str, list[str]]] = {
        predicate: defaultdict(list) for predicate in _METADATA_PREDICATES
    }
    for assertion in read_jsonl(knowledge_dir / "knowledge_assertions.jsonl", KnowledgeAssertion):
        predicate = assertion.predicate.value
        if predicate in grouped:
            grouped[predicate][assertion.subject_key].append(assertion.object_key)

    tokens: dict[str, list[MorphologyToken]] = defaultdict(list)
    for token in read_jsonl(lexical_dir / "tokens.jsonl", MorphologyToken):
        tokens[token.passage_key].append(token)
    for group in tokens.values():
        group.sort(key=lambda item: item.sequence)

    mentions: dict[str, list[MentionAssertion]] = defaultdict(list)
    for mention in read_jsonl(lexical_dir / "mentions.jsonl", MentionAssertion):
        mentions[mention.subject_key].append(mention)

    exact: dict[str, list[str]] = defaultdict(list)
    near: dict[str, list[str]] = defaultdict(list)
    for parallel in read_jsonl(lexical_dir / "mantra_parallels.jsonl", MantraParallel):
        bucket = exact if parallel.predicate.value == "EXACT_PARALLEL_OF" else near
        bucket[parallel.subject_key].append(parallel.object_key)
        bucket[parallel.object_key].append(parallel.subject_key)

    sukta_sizes: dict[str, int] = defaultdict(int)
    for key in passage_ids:
        sukta_sizes[_sukta_key(key)] += 1

    return PacketSources(
        passage_ids=passage_ids,
        citations=citations,
        sanskrit=sanskrit,
        translations=translations,
        rishis={key: sorted(value) for key, value in grouped["HAS_RISHI"].items()},
        devatas={key: sorted(value) for key, value in grouped["HAS_DEVATA"].items()},
        chandas={key: sorted(value) for key, value in grouped["HAS_CHANDAS"].items()},
        entity_labels=entity_labels,
        tokens=dict(tokens),
        mentions=dict(mentions),
        exact_parallels={key: sorted(set(value)) for key, value in exact.items()},
        near_parallels={key: sorted(set(value)) for key, value in near.items()},
        sukta_sizes=dict(sukta_sizes),
    )


def _packet_translation(sources: PacketSources, passage_key: str) -> PacketTranslation | None:
    translation = sources.translations.get(passage_key)
    if translation is None:
        return None
    return PacketTranslation(
        translation_id=str(translation.translation_id),
        translator=translation.translator,
        language=translation.language,
        text=translation.text,
        text_sha256=sha256_text(translation.text),
    )


def _neighbour(sources: PacketSources, passage_key: str, offset: int) -> PacketNeighbour | None:
    key = _neighbour_key(passage_key, offset)
    if not key or key not in sources.passage_ids or key not in sources.sanskrit:
        return None
    return PacketNeighbour(
        passage_key=key,
        citation=sources.citations[key],
        sanskrit=sources.sanskrit[key],
        translation=_packet_translation(sources, key),
    )


def _labels(sources: PacketSources, keys: list[str]) -> list[str]:
    return [sources.entity_labels.get(key, key) for key in keys]


def packet_input_hash(payload: dict[str, object]) -> str:
    """Hash of the packet exactly as sent, translation text included.

    This is what "reproducible" means for this layer, and it is a claim about the input
    only. The same hash guarantees the same evidence was shown; it guarantees nothing
    about what the model said in response, and no report may imply otherwise.
    """
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str))


def build_packet(sources: PacketSources, passage_key: str) -> EvidencePacket:
    """Assemble one packet. Raises if the mantra is not in the pinned corpus."""
    if passage_key not in sources.passage_ids:
        raise KeyError(f"{passage_key} is not a mantra in the pinned corpus")

    _, mandala, sukta, mantra = (
        passage_key.split(":")[2],
        int(passage_key.split(":")[3][1:]),
        int(passage_key.split(":")[4][1:]),
        int(passage_key.split(":")[5][1:]),
    )
    translation = _packet_translation(sources, passage_key)
    tokens = [
        PacketToken(
            token_key=token.token_key,
            pada=token.pada,
            sequence=token.sequence,
            surface=token.surface_form,
            lemma=token.lemma,
            part_of_speech=token.part_of_speech,
            morphology=dict(token.morphological_features),
        )
        for token in sources.tokens.get(passage_key, [])
    ]
    mentions = [
        PacketMention(
            entity_key=mention.object_key,
            entity_label=sources.entity_labels.get(mention.object_key, mention.object_key),
            occurrence_count=mention.occurrence_count,
            token_keys=[item.token_key for item in mention.evidence],
        )
        for mention in sorted(
            sources.mentions.get(passage_key, []), key=lambda item: item.object_key
        )
    ]

    fields: dict[str, object] = {
        "packet_version": PACKET_VERSION,
        "passage_key": passage_key,
        "passage_id": sources.passage_ids[passage_key],
        "citation": sources.citations[passage_key],
        "mandala": mandala,
        "sukta": sukta,
        "mantra": mantra,
        "sanskrit": sources.sanskrit[passage_key],
        "sanskrit_text_version_id": CANONICAL_TEXT_VERSION_ID,
        "translation": translation,
        "translation_missing": translation is None,
        "rishi_keys": sources.rishis.get(passage_key, []),
        "devata_keys": sources.devatas.get(passage_key, []),
        "chandas_keys": sources.chandas.get(passage_key, []),
        "rishi_labels": _labels(sources, sources.rishis.get(passage_key, [])),
        "devata_labels": _labels(sources, sources.devatas.get(passage_key, [])),
        "chandas_labels": _labels(sources, sources.chandas.get(passage_key, [])),
        "tokens": tokens,
        "mentions": mentions,
        "previous": _neighbour(sources, passage_key, -1),
        "next": _neighbour(sources, passage_key, +1),
        "sukta_mantra_count": sources.sukta_sizes[_sukta_key(passage_key)],
        "exact_parallel_passage_keys": sources.exact_parallels.get(passage_key, []),
        "near_parallel_passage_keys": sources.near_parallels.get(passage_key, []),
        "input_sha256": "0" * 64,
    }
    draft = EvidencePacket.model_validate(fields)
    payload = draft.model_dump(mode="json", exclude={"input_sha256"})
    return draft.model_copy(update={"input_sha256": packet_input_hash(payload)})
