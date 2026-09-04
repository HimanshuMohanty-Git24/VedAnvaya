"""Bounded corpus build orchestration for the D1 Rigveda pilot."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import orjson
from pydantic import BaseModel

from vedagraph.config import Settings
from vedagraph.config.registry import load_sources, load_works
from vedagraph.identity import (
    rv_mandala_identity,
    rv_mantra_identity,
    rv_sukta_identity,
    uuid_for_urn,
)
from vedagraph.ingest.adapters import VHPAdapter, WikisourceTranslationAdapter
from vedagraph.ingest.fetcher import PoliteFetcher
from vedagraph.models import (
    AudioRecording,
    Citation,
    Passage,
    SourceAssertion,
    TextVersion,
    TraditionalMetadataAssertion,
    Translation,
)
from vedagraph.models.core import MetadataScope
from vedagraph.models.enums import (
    AlignmentLevel,
    AssertionStatus,
    AudioType,
    EntityType,
    MetadataPredicate,
    PassageStatus,
    QualityStatus,
    RightsStatus,
    ScopeType,
    StoragePolicy,
    TextForm,
)
from vedagraph.normalize import normalize_nfc
from vedagraph.qa import CorpusRecords, qa_status, validate_corpus, write_qa_json
from vedagraph.reconcile import canonical_mantra_count
from vedagraph.storage import write_jsonl
from vedagraph.storage.manifest import build_manifest


@dataclass(frozen=True)
class PilotBuildResult:
    output_dir: Path
    passage_count: int
    mantra_count: int
    text_count: int
    translation_count: int
    qa_issue_count: int
    snapshot_ids: tuple[str, ...]


def _derived_uuid(kind: str, *parts: object) -> UUID:
    component = ":".join(str(part) for part in parts)
    return uuid_for_urn(f"urn:vedagraph:{kind}:{component}")


async def build_rv_1_1_pilot(settings: Settings) -> PilotBuildResult:
    """Build RV 1.1 only from cached-or-live bounded source snapshots."""
    fetcher = PoliteFetcher(settings)
    vhp_adapter = VHPAdapter()
    wiki_adapter = WikisourceTranslationAdapter()
    vhp_resource = (await vhp_adapter.discover("RV.1.1"))[0]
    wiki_resource = (await wiki_adapter.discover("RV.1.1"))[0]
    vhp_snapshot = await vhp_adapter.fetch(vhp_resource, fetcher)
    wiki_snapshot = await wiki_adapter.fetch(wiki_resource, fetcher)
    staged_texts = vhp_adapter.parse(
        vhp_snapshot.content_path, snapshot_id=vhp_snapshot.metadata.snapshot_id
    )
    staged_translations = wiki_adapter.parse_translations(
        wiki_snapshot.content_path, snapshot_id=wiki_snapshot.metadata.snapshot_id
    )
    if len(staged_texts) != len(staged_translations):
        raise ValueError(
            "RV 1.1 source mismatch: "
            f"{len(staged_texts)} Sanskrit verses vs {len(staged_translations)} translations"
        )

    mandala_key, mandala_urn, mandala_id = rv_mandala_identity(1)
    sukta_key, sukta_urn, sukta_id = rv_sukta_identity(1, 1)
    passages = [
        Passage(
            entity_id=mandala_id,
            canonical_key=mandala_key,
            canonical_urn=mandala_urn,
            entity_type=EntityType.SECTION,
            work_id="VG:WORK:RV:SAK",
            hierarchy={"mandala": 1},
            canonical_citation="RV 1",
            sequence_in_parent=1,
            status=PassageStatus.CANONICAL,
        ),
        Passage(
            entity_id=sukta_id,
            canonical_key=sukta_key,
            canonical_urn=sukta_urn,
            entity_type=EntityType.HYMN,
            work_id="VG:WORK:RV:SAK",
            hierarchy={"mandala": 1, "sukta": 1},
            canonical_citation="RV 1.1",
            parent_key=mandala_key,
            sequence_in_parent=1,
        ),
    ]
    texts: list[TextVersion] = []
    translations: list[Translation] = []
    citations: list[Citation] = []
    passage_by_sequence: dict[int, UUID] = {}
    for staged_text, staged_translation in zip(staged_texts, staged_translations, strict=True):
        sequence = int(staged_text.hierarchy["mantra"])
        key, urn, passage_id = rv_mantra_identity(1, 1, sequence)
        passage_by_sequence[sequence] = passage_id
        passages.append(
            Passage(
                entity_id=passage_id,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.MANTRA,
                work_id="VG:WORK:RV:SAK",
                hierarchy={"mandala": 1, "sukta": 1, "mantra": sequence},
                canonical_citation=f"RV 1.1.{sequence}",
                parent_key=sukta_key,
                sequence_in_parent=sequence,
            )
        )
        normalized = normalize_nfc(staged_text.text_original)
        texts.append(
            TextVersion(
                text_id=_derived_uuid("text", passage_id, "vhp", "samhita"),
                passage_id=passage_id,
                language="sa",
                script="Devanagari",
                text_form=TextForm.SAMHITA,
                text_original=staged_text.text_original,
                text_nfc=normalized,
                accented=staged_text.accented,
                source_id="VHP",
                source_locator=staged_text.source_locator,
                content_sha256=sha256(normalized.encode("utf-8")).hexdigest(),
                rights_status=RightsStatus.PERMISSION_REQUIRED,
            )
        )
        translations.append(
            Translation(
                translation_id=_derived_uuid("translation", passage_id, "griffith", 1896),
                passage_id=passage_id,
                language="en",
                translator=staged_translation.translator,
                work_edition=staged_translation.work_edition,
                year=staged_translation.year,
                text=normalize_nfc(staged_translation.text_original),
                source_id="WIKISOURCE_GRIFFITH_RV",
                rights_status=RightsStatus.PUBLIC_DOMAIN,
                alignment_level=AlignmentLevel.MANTRA,
                quality_status=QualityStatus.UNREVIEWED,
            )
        )
        citations.append(
            Citation(
                citation_id=_derived_uuid("citation", passage_id, "rv-standard"),
                passage_id=passage_id,
                label=f"RV 1.1.{sequence}",
                system="RV_STANDARD",
                is_canonical=True,
            )
        )

    metadata = [
        TraditionalMetadataAssertion(
            assertion_id=_derived_uuid("assertion", sukta_id, "rishi", "madhucchanda"),
            predicate=MetadataPredicate.HAS_RISHI,
            value="Madhucchandas Vaishvamitra",
            scope=MetadataScope(scope_type=ScopeType.WHOLE_PASSAGE, passage_id=sukta_id),
            source_id="VHP",
            source_locator="RV 1.1 header",
        ),
        TraditionalMetadataAssertion(
            assertion_id=_derived_uuid("assertion", sukta_id, "devata", "agni"),
            predicate=MetadataPredicate.HAS_DEVATA,
            value="Agni",
            scope=MetadataScope(scope_type=ScopeType.WHOLE_PASSAGE, passage_id=sukta_id),
            source_id="VHP",
            source_locator="RV 1.1 header",
        ),
        TraditionalMetadataAssertion(
            assertion_id=_derived_uuid("assertion", sukta_id, "chandas", "gayatri"),
            predicate=MetadataPredicate.HAS_CHANDAS,
            value="Gayatri",
            scope=MetadataScope(scope_type=ScopeType.WHOLE_PASSAGE, passage_id=sukta_id),
            source_id="VHP",
            source_locator="RV 1.1 header",
        ),
    ]
    audio = [
        AudioRecording(
            audio_id=_derived_uuid("audio", sukta_id, "vhp", "RIGSS_01_001"),
            target_id=sukta_id,
            language="sa",
            audio_type=AudioType.VEDIC_RECITATION,
            recension="Shakala",
            source_id="VHP",
            source_media_id="RIGSS_01_001",
            source_url="https://vedicheritage.gov.in/video/RIGSS_01_001.mp4",
            storage_policy=StoragePolicy.EXTERNAL_REFERENCE,
            rights_status=RightsStatus.PERMISSION_REQUIRED,
            mime_type="video/mp4",
        )
    ]
    assertions = [
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", sukta_id, "vhp", "mantra-count"),
            subject_id=str(sukta_id),
            predicate="REPORTED_MANTRA_COUNT",
            value=len(staged_texts),
            source_id="VHP",
            source_locator="RV 1.1 heading metadata",
            status=AssertionStatus.UNREVIEWED,
            evidence="VHP page presents nine numbered mantras",
        )
    ]
    sources = load_sources()
    works = load_works()
    corpus_records = CorpusRecords(
        passages=passages,
        texts=texts,
        translations=translations,
        metadata=metadata,
        sources=sources,
        citations=citations,
        audio_recordings=audio,
        audio_segments=[],
        source_assertions=assertions,
    )
    issues = validate_corpus(corpus_records)

    output_dir = settings.data_dir / "canonical" / "rv_1_1_pilot"
    generated: dict[Path, int] = {}
    collections: dict[str, Sequence[BaseModel]] = {
        "works.jsonl": works,
        "passages.jsonl": passages,
        "text_versions.jsonl": texts,
        "translations.jsonl": translations,
        "traditional_metadata.jsonl": metadata,
        "sources.jsonl": sources,
        "source_assertions.jsonl": assertions,
        "citations.jsonl": citations,
        "audio_recordings.jsonl": audio,
        "audio_segments.jsonl": [],
        "qa_issues.jsonl": issues,
    }
    for name, values in collections.items():
        path = output_dir / name
        generated[path] = write_jsonl(path, values)
    qa_path = settings.data_dir / "qa" / "rv_1_1_pilot.json"
    write_qa_json(qa_path, issues)
    manifest = build_manifest(
        root=settings.data_dir,
        version="0.1.0-pilot.1",
        works=["VG:WORK:RV:SAK"],
        passage_count=canonical_mantra_count(passages),
        source_snapshot_ids=[
            vhp_snapshot.metadata.snapshot_id,
            wiki_snapshot.metadata.snapshot_id,
        ],
        generated=generated,
        qa_status=qa_status(issues),
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_bytes(
        orjson.dumps(
            manifest.model_dump(mode="json", exclude_none=True),
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
        + b"\n"
    )
    return PilotBuildResult(
        output_dir=output_dir,
        passage_count=len(passages),
        mantra_count=canonical_mantra_count(passages),
        text_count=len(texts),
        translation_count=len(translations),
        qa_issue_count=len(issues),
        snapshot_ids=(vhp_snapshot.metadata.snapshot_id, wiki_snapshot.metadata.snapshot_id),
    )
