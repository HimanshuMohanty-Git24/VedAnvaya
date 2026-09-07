"""Build the Atharvaveda-Samhita (Saunaka) representative pilot.

Deliberately a standalone script rather than a function inside ``vedagraph.corpus``:
``corpus.py`` is shared infrastructure owned elsewhere, and this pilot needs to prove the
AVS source stack end to end without perturbing the Rigveda pipeline.

What the pilot proves
---------------------
acquisition (PoliteFetcher, immutable hashed snapshots) -> recension verification ->
parsing (kanda/sukta/mantra + two numbering systems + prose) -> canonical identity via the
frozen ``avs_*_identity`` functions -> accented source preservation alongside derived
surfaces -> independent translation records -> deterministic rebuild.

Sample design
-------------
Whole suktas only, so ``sequence_in_parent`` stays contiguous inside every parent.  The
sample is chosen to *stress* the parser rather than to flatter it: every structural anomaly
class found in the whole file is represented, plus early, middle and late kandas.  See
``SAMPLE`` for the per-sukta rationale.

Book 20 is included but its Rigvedic parallels are NOT deduplicated and NOT sourced from
the Rigveda.  AVS 20 text is AVS text; a cross-work parallel is a separate derived layer.
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

import orjson
from pydantic import BaseModel

from vedagraph.compare.text import COMPARATOR_VERSION, VersionReading, compare_readings
from vedagraph.config import Settings
from vedagraph.config.registry import load_source_artifacts, load_sources, load_works
from vedagraph.identity import (
    avs_kanda_identity,
    avs_mantra_identity,
    avs_sukta_identity,
    uuid_for_urn,
)
from vedagraph.ingest.adapters.atharvaveda_gretil import (
    PARSER_VERSION,
    SNAPSHOT_SOURCE_ID,
    SOURCE_ID,
    WORK_ID,
    AVSHeaderMetadata,
    AVSUnit,
    GretilAVSAdapter,
)
from vedagraph.ingest.fetcher import PoliteFetcher
from vedagraph.models import (
    Citation,
    Passage,
    Source,
    SourceArtifact,
    SourceAssertion,
    TextVersion,
    Translation,
)
from vedagraph.models.enums import (
    AlignmentLevel,
    AssertionStatus,
    EntityType,
    PassageStatus,
    QAStatus,
    QualityStatus,
    RightsStatus,
    TextForm,
    TextRole,
    TranslationAlignment,
)
from vedagraph.normalize import (
    ComparisonForm,
    comparison_form,
    has_vedic_accents,
    normalize_nfc,
)
from vedagraph.storage import write_jsonl
from vedagraph.storage.manifest import build_manifest, file_sha256

BUILD_ID = "atharvaveda_pilot_v1"
BUILD_VERSION = "0.1.0-avs-pilot.1"

#: The translation layer's registered source and its local snapshot namespace, kept in
#: step with scripts/fetch_atharvaveda_translation.py.
TRANSLATION_SOURCE_ID = "VEDAWEB"
TRANSLATION_SNAPSHOT_SOURCE_ID = "VEDAWEB_AVS"

ACCENTED_VERSION_ID = "GRETIL.AVS.SAUNAKA.ACCENTED"
UNACCENTED_VERSION_ID = "GRETIL.AVS.SAUNAKA.UNACCENTED"
SEARCH_VERSION_ID = "VEDAGRAPH.AVS.SEARCH_NORMALIZED"

#: Whole suktas, with the reason each one is in the sample.  Nothing here is decorative.
SAMPLE: dict[tuple[int, int], str] = {
    (1, 1): "earliest kanda, short four-verse metrical hymn: the easy baseline case",
    (4, 1): "early-middle kanda, ordinary metrical hymn",
    (6, 1): "kanda 6 is the extreme short-hymn book (142 suktas); three-verse hymn",
    (7, 6): "kanda 7 carries label-vs-marker divergence: 7.6.3 prints ||1||, 7.6.4 prints ||2||",
    (8, 5): "contains AVS 8.5.11 whose pada letter is a corrupt retroflex d where c is meant",
    (13, 4): (
        "long-hymn kanda; paryaya prose; the 13.4.26 locator collision (first verse of the "
        "sukta is mislabelled 26 and prints ||1||); and 13.4.22 prints ||2||"
    ),
    (15, 2): (
        "kanda 15 Vratya paryaya: one Roth/Whitney verse equals eight Vishva Bandhu verses, "
        "so the alternate numbering is per-pada, not per-verse"
    ),
    (16, 1): "kanda 16 is prose; every unit here is single-pada and non-metrical",
    (19, 1): "kanda 19 is structurally atypical (supplementary book)",
    (20, 96): (
        "kanda 20; AVS 20.96.22 is TWO different verses both numbered 22, distinguished "
        "only by the [-] absence marker in the other edition"
    ),
    (20, 127): "kanda 20 kuntapa hymn; largely Rigvedic in character and NOT deduplicated",
}


@dataclass(frozen=True)
class ArtifactSnapshot:
    variant: str
    artifact_id: str
    snapshot_id: str
    content_path: Path
    sha256: str
    retrieved_at: datetime
    url: str
    header: AVSHeaderMetadata
    units: list[AVSUnit]


def _derived_uuid(kind: str, *parts: object) -> UUID:
    return uuid_for_urn(f"urn:vedagraph:{kind}:{':'.join(str(part) for part in parts)}")


def _passage(**kwargs: Any) -> Passage:
    """Construct a Passage, passing optional descriptive fields only if the model has them.

    ``native_labels`` / ``structural_path`` are additive fields owned by Agent A.  Filtering
    on ``model_fields`` keeps this build working both before and after they land, instead of
    hard-failing on a contract that is still moving.
    """
    known = set(Passage.model_fields)
    return Passage(**{key: value for key, value in kwargs.items() if key in known})


async def _load_artifact(variant: str, fetcher: PoliteFetcher) -> ArtifactSnapshot:
    adapter = GretilAVSAdapter(variant=variant)
    resource = (await adapter.discover("AVS"))[0]
    snapshot = await adapter.fetch(resource, fetcher)
    # Recension is proved inside parse_units; extract_header_metadata gives the evidence.
    header = adapter.extract_header_metadata(snapshot.content_path)
    units = adapter.parse_units(snapshot.content_path, suktas=frozenset(SAMPLE))
    return ArtifactSnapshot(
        variant=variant,
        artifact_id=adapter.source_artifact_id,
        snapshot_id=snapshot.metadata.snapshot_id,
        content_path=snapshot.content_path,
        sha256=snapshot.metadata.sha256,
        retrieved_at=snapshot.metadata.retrieved_at,
        url=adapter.url,
        header=header,
        units=units,
    )


def _select_canonical(
    units: list[AVSUnit],
) -> tuple[dict[tuple[int, int, int], AVSUnit], list[AVSUnit]]:
    """Split parsed units into one canonical unit per triple, plus explicit divergences.

    Rule, applied identically every run and never inventing a number: when two units claim
    the same (kanda, sukta, mantra), keep the one whose *own in-text* ``||N||`` marker
    agrees with its locator, if exactly one does.  Otherwise keep the first in file order.
    The loser is returned as a divergence, not discarded.
    """
    grouped: dict[tuple[int, int, int], list[AVSUnit]] = defaultdict(list)
    for unit in units:
        grouped[(unit.kanda, unit.sukta, unit.mantra)].append(unit)
    canonical: dict[tuple[int, int, int], AVSUnit] = {}
    divergences: list[AVSUnit] = []
    for triple, candidates in grouped.items():
        if len(candidates) == 1:
            canonical[triple] = candidates[0]
            continue
        agreeing = [item for item in candidates if item.label_agrees_with_source_marker is True]
        chosen = agreeing[0] if len(agreeing) == 1 else candidates[0]
        canonical[triple] = chosen
        divergences.extend(item for item in candidates if item is not chosen)
    return canonical, divergences


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _load_staged_translations(path: Path) -> dict[tuple[int, int, int], dict[str, Any]]:
    """Read translations staged by ``fetch_atharvaveda_translation.py``, if present.

    Translations are aligned by the *source's own printed hymn and verse numbers*, never by
    sequence position, so a missing or renumbered verse yields no record instead of a
    silently shifted one (ADR-010).
    """
    if not path.exists():
        return {}
    payload = orjson.loads(path.read_bytes())
    return {
        (int(item["kanda"]), int(item["sukta"]), int(item["mantra"])): item
        for item in payload["verses"]
    }


def _load_staged_snapshot_ids(path: Path) -> tuple[str, ...]:
    """Snapshot ids the translation stage actually read, for the namespace mapping."""
    if not path.exists():
        return ()
    return tuple(orjson.loads(path.read_bytes()).get("snapshot_ids", ()))


def build(settings: Settings, *, translation_stage: Path) -> dict[str, Any]:
    fetcher = PoliteFetcher(settings)
    accented, unaccented = asyncio.run(_gather(fetcher))

    canonical, divergences = _select_canonical(accented.units)
    unaccented_by_triple, _ = _select_canonical(unaccented.units)
    staged_translations = _load_staged_translations(translation_stage)
    staged_snapshot_ids = _load_staged_snapshot_ids(translation_stage)

    ordered = sorted(canonical)
    kandas = sorted({kanda for kanda, _, _ in ordered})
    suktas = sorted({(kanda, sukta) for kanda, sukta, _ in ordered})

    passages: list[Passage] = []
    texts: list[TextVersion] = []
    citations: list[Citation] = []
    assertions: list[SourceAssertion] = []
    translations: list[Translation] = []

    # -- containers ----------------------------------------------------------------
    # sequence_in_parent for a kanda is the kanda number itself: the sample is a subset of
    # kandas, and renumbering 1..N would assert a false position inside the Samhita.
    kanda_keys: dict[int, str] = {}
    for kanda in kandas:
        key, urn, entity_id = avs_kanda_identity(kanda)
        kanda_keys[kanda] = key
        passages.append(
            _passage(
                entity_id=entity_id,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.SECTION,
                work_id=WORK_ID,
                hierarchy={"kanda": kanda},
                canonical_citation=f"AVS {kanda}",
                sequence_in_parent=kanda,
                status=PassageStatus.CANONICAL,
                native_labels=["Kanda"],
                structural_path=[str(kanda)],
            )
        )

    sukta_keys: dict[tuple[int, int], str] = {}
    sukta_ids: dict[tuple[int, int], UUID] = {}
    for kanda, sukta in suktas:
        key, urn, entity_id = avs_sukta_identity(kanda, sukta)
        sukta_keys[(kanda, sukta)] = key
        sukta_ids[(kanda, sukta)] = entity_id
        passages.append(
            _passage(
                entity_id=entity_id,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.HYMN,
                work_id=WORK_ID,
                hierarchy={"kanda": kanda, "sukta": sukta},
                canonical_citation=f"AVS {kanda}.{sukta}",
                parent_key=kanda_keys[kanda],
                sequence_in_parent=sukta,
                status=PassageStatus.CANONICAL,
                native_labels=["Kanda", "Sukta"],
                structural_path=[str(kanda), str(sukta)],
            )
        )

    # -- mantras -------------------------------------------------------------------
    for triple in ordered:
        kanda, sukta, mantra = triple
        unit = canonical[triple]
        key, urn, passage_id = avs_mantra_identity(kanda, sukta, mantra)
        citation_label = f"AVS {kanda}.{sukta}.{mantra}"
        passages.append(
            _passage(
                entity_id=passage_id,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.MANTRA,
                work_id=WORK_ID,
                hierarchy={"kanda": kanda, "sukta": sukta, "mantra": mantra},
                canonical_citation=citation_label,
                parent_key=sukta_keys[(kanda, sukta)],
                sequence_in_parent=mantra,
                status=PassageStatus.CANONICAL,
                native_labels=["Kanda", "Sukta", "Mantra"],
                structural_path=[str(kanda), str(sukta), str(mantra)],
            )
        )

        # Accented source text: PRIMARY. Stored verbatim, apparatus included.
        accented_text = unit.text_original
        texts.append(
            _text_version(
                passage_id=passage_id,
                version_id=ACCENTED_VERSION_ID,
                text=accented_text,
                role=TextRole.PRIMARY_TEXT,
                artifact=accented,
                locator=" ".join(unit.locators),
            )
        )
        # Unaccented sibling artifact: PARALLEL, never a replacement for the accented text.
        sibling = unaccented_by_triple.get(triple)
        if sibling is not None:
            texts.append(
                _text_version(
                    passage_id=passage_id,
                    version_id=UNACCENTED_VERSION_ID,
                    text=sibling.text_original,
                    role=TextRole.PARALLEL_TEXT,
                    artifact=unaccented,
                    locator=" ".join(sibling.locators),
                )
            )
        # Derived searchable surface. Derived from the accented text, marked as derived,
        # and never written back over it.
        search_text = comparison_form(accented_text, ComparisonForm.SEARCH_NORMALIZED)
        if search_text:
            texts.append(
                _text_version(
                    passage_id=passage_id,
                    version_id=SEARCH_VERSION_ID,
                    text=search_text,
                    role=TextRole.SEARCH_DERIVATIVE,
                    artifact=accented,
                    locator=f"derived:{ComparisonForm.SEARCH_NORMALIZED.value}",
                    rights_override=RightsStatus.REFERENCE_ONLY,
                )
            )

        citations.append(
            Citation(
                citation_id=_derived_uuid("citation", passage_id, "avs-roth-whitney"),
                passage_id=passage_id,
                label=citation_label,
                system="AVS_ROTH_WHITNEY_1856",
                source_id=SOURCE_ID,
                is_canonical=True,
            )
        )
        alternate = unit.alternate_citation_label
        if alternate is not None:
            citations.append(
                Citation(
                    citation_id=_derived_uuid("citation", passage_id, "avs-vishva-bandhu"),
                    passage_id=passage_id,
                    label=alternate,
                    system="AVS_VISHVA_BANDHU_1960",
                    source_id=SOURCE_ID,
                    is_canonical=False,
                )
            )
        elif unit.alternate_absent:
            # Agent A declined an absence flag on Citation on purpose: an absence is an
            # assertion about a source, so it belongs here with its locator and marker.
            assertions.append(
                SourceAssertion(
                    assertion_id=_derived_uuid("assertion", passage_id, "alt-numbering-absent"),
                    subject_id=key,
                    predicate="ALTERNATE_NUMBERING_ABSENT",
                    value={"system": "AVS_VISHVA_BANDHU_1960", "printed_marker": "[-]"},
                    source_id=SOURCE_ID,
                    source_artifact_id=accented.artifact_id,
                    source_locator=" ".join(unit.locators),
                    status=AssertionStatus.UNREVIEWED,
                    evidence=(
                        "the locator prints an explicit [-] where the Vishva Bandhu number "
                        "would stand, i.e. the edition asserts there is no counterpart"
                    ),
                )
            )

        # Structural facts the source actually asserts. No metrical classification.
        assertions.append(
            SourceAssertion(
                assertion_id=_derived_uuid("assertion", passage_id, "unit-shape"),
                subject_id=key,
                predicate="SOURCE_UNIT_SHAPE",
                value={
                    "pada_labels": unit.pada_labels,
                    "pada_count": len(unit.pada_texts),
                    "single_pada_unit": unit.is_single_pada_unit,
                    "source_verse_marker": unit.source_verse_marker,
                    "label_agrees_with_source_marker": unit.label_agrees_with_source_marker,
                    "anuvaka_group_marker_closed_here": unit.group_marker,
                    "alternate_unit_markers": unit.alternate_unit_markers,
                    "occurrence": unit.occurrence,
                },
                source_id=SOURCE_ID,
                source_artifact_id=accented.artifact_id,
                source_locator=" ".join(unit.locators),
                status=AssertionStatus.UNREVIEWED,
                evidence=(
                    "pada letters and the in-text ||N|| / {N} markers as printed; "
                    "single_pada_unit is a source fact and is NOT a claim that the unit is "
                    "prose or that it is verse"
                ),
            )
        )
        if unit.label_agrees_with_source_marker is False:
            assertions.append(
                SourceAssertion(
                    assertion_id=_derived_uuid("assertion", passage_id, "marker-disagreement"),
                    subject_id=key,
                    predicate="SOURCE_INTERNAL_NUMBERING_DISAGREEMENT",
                    value={
                        "locator_mantra": mantra,
                        "printed_verse_marker": unit.source_verse_marker,
                    },
                    source_id=SOURCE_ID,
                    source_artifact_id=accented.artifact_id,
                    source_locator=" ".join(unit.locators),
                    status=AssertionStatus.UNREVIEWED,
                    evidence=(
                        "the locator and the printed verse marker disagree; neither witness "
                        "is corrected and neither is treated as authoritative"
                    ),
                )
            )

        staged = staged_translations.get(triple)
        if staged is not None:
            translations.append(
                Translation(
                    translation_id=_derived_uuid(
                        "translation", passage_id, staged["source_id"], staged["year"]
                    ),
                    passage_id=passage_id,
                    language=staged["language"],
                    translator=staged["translator"],
                    work_edition=staged["work_edition"],
                    year=staged["year"],
                    text=normalize_nfc(staged["text"]),
                    source_id=staged["source_id"],
                    source_artifact_id=staged.get("source_artifact_id"),
                    rights_status=RightsStatus(staged["rights_status"]),
                    alignment_level=AlignmentLevel.MANTRA,
                    alignment=TranslationAlignment(staged["alignment"]),
                    quality_status=QualityStatus.UNREVIEWED,
                    source_page_title=staged.get("page_title"),
                    canonical_page_url=staged.get("page_url"),
                )
            )

    # -- per-sukta computed counts, as data ----------------------------------------
    mantra_counts = Counter((kanda, sukta) for kanda, sukta, _ in ordered)
    for kanda, sukta in suktas:
        assertions.append(
            SourceAssertion(
                assertion_id=_derived_uuid("assertion", sukta_ids[(kanda, sukta)], "count"),
                subject_id=sukta_keys[(kanda, sukta)],
                predicate="COMPUTED_MANTRA_COUNT",
                value=mantra_counts[(kanda, sukta)],
                source_id=SOURCE_ID,
                source_artifact_id=accented.artifact_id,
                source_locator=f"AVS {kanda}.{sukta}",
                status=AssertionStatus.UNREVIEWED,
                evidence=(
                    "computed by counting distinct locators in the snapshot; the artifact "
                    "states no count of its own to reconcile against"
                ),
            )
        )

    # -- artifact-level provenance and rights, verbatim ----------------------------
    for artifact in (accented, unaccented):
        assertions.append(
            SourceAssertion(
                assertion_id=_derived_uuid("assertion", artifact.artifact_id, "provenance"),
                subject_id=artifact.artifact_id,
                predicate="ARTIFACT_PROVENANCE",
                value={
                    "url": artifact.url,
                    "sha256": artifact.sha256,
                    "snapshot_id": artifact.snapshot_id,
                    "retrieved_at": artifact.retrieved_at.isoformat(),
                    "title": artifact.header.title,
                    "accent_declaration": artifact.header.accent_declaration,
                    "edition_basis": list(artifact.header.edition_basis),
                    "input_credits": list(artifact.header.input_credits),
                    "alternate_numbering_note": list(artifact.header.alternate_numbering_note),
                    "licence_statement_verbatim": artifact.header.licence_statement_verbatim,
                    "stated_total_counts_found": list(artifact.header.stated_total_counts),
                    "parser_version": PARSER_VERSION,
                },
                source_id=SOURCE_ID,
                source_artifact_id=artifact.artifact_id,
                source_locator=artifact.url,
                status=AssertionStatus.UNREVIEWED,
                evidence="read from the artifact preamble; the licence sentence is verbatim",
            )
        )

    # Staged translations with no canonical passage to attach to. NOT silently dropped:
    # each one is a real disagreement between the translation's edition and the primary
    # artifact's numbering, and each is the kind of thing a zip()-based aligner would have
    # hidden by shifting every subsequent verse.
    translated_triples = {
        (int(item["kanda"]), int(item["sukta"]), int(item["mantra"]))
        for item in staged_translations.values()
    }
    for triple in sorted(translated_triples - set(canonical)):
        kanda, sukta, mantra = triple
        staged = staged_translations[triple]
        assertions.append(
            SourceAssertion(
                assertion_id=_derived_uuid("assertion", *triple, "unaligned-translation"),
                subject_id=f"AVS {kanda}.{sukta}.{mantra}",
                predicate="TRANSLATION_HAS_NO_CANONICAL_PASSAGE",
                value={
                    "citation_in_translation_edition": staged["source_alias"],
                    "translator": staged["translator"],
                    "source_id": staged["source_id"],
                    "text": staged["text"],
                },
                source_id=staged["source_id"],
                source_artifact_id=staged.get("source_artifact_id"),
                source_locator=staged["source_alias"],
                status=AssertionStatus.UNREVIEWED,
                evidence=(
                    "the translation's edition numbers this verse but the primary Sanskrit "
                    "artifact does not, so no Translation record was emitted and the verse "
                    "was NOT re-attached to a neighbouring mantra"
                ),
            )
        )

    # Make the snapshot-namespace divergence RESOLVABLE, not merely documented.
    #
    # PoliteFetcher derives three things from one argument -- the raw directory, the
    # snapshot_id prefix, and the source_id written into the metadata sidecar -- so a caller
    # cannot namespace the storage directory without also writing a non-registry value into
    # the recorded provenance. That coupling lives in ingest/fetcher/http.py, which this
    # agent does not own, and it is filed as a contract request rather than patched here.
    #
    # Its consequence is real: every snapshot sidecar for this build records source_id
    # GRETIL_AVS or VEDAWEB_AVS, neither of which resolves against data/registry/sources.yaml,
    # so a snapshot-to-rights join over the raw tree silently finds nothing. Emitting the
    # mapping as an assertion closes that join TODAY, from the release side, without waiting
    # on a fetcher change and without inventing a registry entry.
    for namespace, registered in (
        (SNAPSHOT_SOURCE_ID, SOURCE_ID),
        (TRANSLATION_SNAPSHOT_SOURCE_ID, TRANSLATION_SOURCE_ID),
    ):
        every_snapshot_id = (
            accented.snapshot_id,
            unaccented.snapshot_id,
            *staged_snapshot_ids,
        )
        namespaced = sorted(
            snapshot_id
            for snapshot_id in every_snapshot_id
            if snapshot_id.startswith(f"{namespace}:")
        )
        if not namespaced:
            continue
        assertions.append(
            SourceAssertion(
                assertion_id=_derived_uuid("assertion", BUILD_ID, "snapshot-namespace", namespace),
                subject_id=namespace,
                predicate="SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE",
                value={
                    "snapshot_namespace": namespace,
                    "registered_source_id": registered,
                    "raw_directory": f"data/raw/{namespace.lower()}/",
                    "snapshot_ids": namespaced,
                    "snapshot_count": len(namespaced),
                },
                source_id=registered,
                source_locator=f"data/raw/{namespace.lower()}/",
                status=AssertionStatus.UNREVIEWED,
                evidence=(
                    "the raw snapshot tree records this namespace as its source_id, which is "
                    "NOT a registered source; it resolves to the registered source named "
                    "here. The namespace is deliberate storage layout - it keeps Atharvaveda "
                    "snapshots out of the Rigveda's raw directory - and is NOT a rights "
                    "claim. Rights attach to the artifact ids in source_artifacts.jsonl."
                ),
            )
        )

    # These two were originally attributed to a "VEDAGRAPH" source_id, which is not a
    # registered source -- and AuthorityTier has no member that describes this project, which
    # is the model saying that a build decision is not a source assertion. Rather than push
    # for a registry entry that would not fit, both are restated as what a SourceAssertion
    # actually means: verifiable facts about the artifact this build read. The *policy*
    # framing lives in data/builds/atharvaveda_pilot_v1.yaml under `policies:`, which is
    # hashed into the manifest as build_config_sha256, so nothing is lost.
    assertions.append(
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", BUILD_ID, "traditional-metadata"),
            subject_id=accented.artifact_id,
            predicate="ARTIFACT_SUPPLIES_NO_TRADITIONAL_METADATA",
            value={
                "rishi": False,
                "devata": False,
                "chandas": False,
                "scope_checked": "whole artifact, all 20 kandas",
                "consequence": (
                    "this build emits ZERO TraditionalMetadataAssertion records. That is an "
                    "absence of evidence, recorded as such. It is NOT licence to infer AVS "
                    "metadata from Rigvedic Anukramani rules, which do not transfer, and NOT "
                    "licence to generate it with a language model."
                ),
                "wider_finding": (
                    "no rights-clear, machine-readable, per-mantra rishi/devata/chandas "
                    "source for AVS exists at all; see the gap "
                    "NO_RIGHTS_CLEAR_PER_MANTRA_TRADITIONAL_METADATA_EXISTS in "
                    "data/source_registry/atharvaveda_sources.yaml"
                ),
            },
            source_id=SOURCE_ID,
            source_artifact_id=accented.artifact_id,
            source_locator=accented.url,
            status=AssertionStatus.UNREVIEWED,
            evidence=(
                "the artifact carries pada text and numbering only; it contains no rishi, "
                "devata or chandas field anywhere, verified over the whole file"
            ),
        )
    )
    kanda_20_mantras = sorted(triple for triple in ordered if triple[0] == 20)
    assertions.append(
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", BUILD_ID, "rv-parallel-policy"),
            subject_id=accented.artifact_id,
            predicate="KANDA_20_TEXT_READ_ONLY_FROM_THIS_ARTIFACT",
            value={
                "kanda_20_mantras_in_build": len(kanda_20_mantras),
                "kanda_20_suktas_in_build": sorted({sukta for _, sukta, _ in kanda_20_mantras}),
                "deduplicated_against_rigveda": False,
                "records_sourced_from_rigveda": 0,
                "note": (
                    "AVS kanda 20 overlaps the Rigveda extensively. Every kanda 20 mantra "
                    "here was read from this AVS artifact. An RV parallel is a candidate for "
                    "the derived parallels layer only, never the source of an AVS mantra."
                ),
            },
            source_id=SOURCE_ID,
            source_artifact_id=accented.artifact_id,
            source_locator=accented.url,
            status=AssertionStatus.UNREVIEWED,
            evidence=(
                "every text_versions record for a kanda 20 passage in this build cites this "
                "artifact id and no other; no VG:WORK:RV:SAK record is referenced anywhere"
            ),
        )
    )

    # -- cross-artifact comparison (D5) --------------------------------------------
    comparisons = []
    for triple in ordered:
        sibling = unaccented_by_triple.get(triple)
        if sibling is None:
            continue
        kanda, sukta, mantra = triple
        comparisons.append(
            compare_readings(
                passage_key=avs_mantra_identity(kanda, sukta, mantra)[0],
                citation=f"AVS {kanda}.{sukta}.{mantra}",
                left=VersionReading(
                    ACCENTED_VERSION_ID, canonical[triple].text_original, TextRole.PRIMARY_TEXT
                ),
                right=VersionReading(
                    UNACCENTED_VERSION_ID, sibling.text_original, TextRole.PARALLEL_TEXT
                ),
            )
        )

    # -- divergent occurrences, kept rather than dropped ---------------------------
    divergence_records = [
        SourceAssertion(
            assertion_id=_derived_uuid(
                "assertion", unit.kanda, unit.sukta, unit.mantra, unit.occurrence, "divergence"
            ),
            subject_id=avs_mantra_identity(unit.kanda, unit.sukta, unit.mantra)[0],
            predicate="NON_CANONICAL_DUPLICATE_OCCURRENCE",
            value={
                "locators": unit.locators,
                "pada_labels": unit.pada_labels,
                "printed_verse_marker": unit.source_verse_marker,
                "alternate_numbering_absent": unit.alternate_absent,
                "text_original": unit.text_original,
                "reason_not_canonical": (
                    "a second unit in the snapshot claims the same (kanda, sukta, mantra); "
                    "the unit whose printed ||N|| marker agrees with its locator was kept "
                    "and this one is preserved here in full rather than discarded"
                ),
            },
            source_id=SOURCE_ID,
            source_artifact_id=accented.artifact_id,
            source_locator=" ".join(unit.locators),
            status=AssertionStatus.UNREVIEWED,
            evidence="verbatim second occurrence, including its full Sanskrit text",
        )
        for unit in divergences
    ]

    # -- write --------------------------------------------------------------------
    output_dir = settings.data_dir / "canonical" / BUILD_ID
    collections: dict[str, list[BaseModel]] = {
        "works.jsonl": [work for work in load_works() if work.work_id == WORK_ID],
        "passages.jsonl": passages,
        "text_versions.jsonl": texts,
        "translations.jsonl": translations,
        "traditional_metadata.jsonl": [],
        # Provenance read from the rights registry, which is the single authority.
        "sources.jsonl": _release_sources(),
        "source_artifacts.jsonl": _release_artifacts(),
        "citations.jsonl": citations,
        "source_assertions.jsonl": assertions + divergence_records,
        "text_comparisons.jsonl": comparisons,
        "audio_recordings.jsonl": [],
        "audio_segments.jsonl": [],
    }
    # Cross-check: the registry's pinned checksums must match the bytes actually read.
    registered_artifacts = {item.artifact_id: item for item in _release_artifacts()}
    for artifact in (accented, unaccented):
        pinned = registered_artifacts[artifact.artifact_id].checksum_sha256
        if pinned is not None and pinned != artifact.sha256:
            raise ValueError(
                f"registry checksum mismatch for {artifact.artifact_id}: "
                f"registry {pinned}, snapshot {artifact.sha256}"
            )

    # Every assertion must cite a REGISTERED source. This is the check that would have
    # caught the "VEDAGRAPH" pseudo-source before it reached a release.
    registered_source_ids = {source.source_id for source in load_sources()}
    unregistered = sorted(
        {
            item.source_id
            for item in assertions + divergence_records
            if item.source_id not in registered_source_ids
        }
    )
    if unregistered:
        raise ValueError(f"assertions cite unregistered source_id(s): {unregistered}")

    qa_findings, qa_state = run_local_qa(
        passages=passages,
        texts=texts,
        citations=citations,
        comparisons=comparisons,
        parsed_units=accented.units,
        canonical=canonical,
    )
    shared_gate_error = _try_shared_gate(
        passages=passages,
        texts=texts,
        citations=citations,
        translations=translations,
        sources=_release_sources(),
    )

    generated: dict[Path, int] = {}
    for name, values in collections.items():
        path = output_dir / name
        generated[path] = write_jsonl(path, values)
    qa_path = output_dir / "qa_issues.jsonl"
    with qa_path.open("wb") as handle:
        for finding in qa_findings:
            handle.write(orjson.dumps(finding, option=orjson.OPT_SORT_KEYS) + b"\n")
    generated[qa_path] = len(qa_findings)

    # built_at is pinned to the newest snapshot retrieval time, not to "now", so a rebuild
    # from the same immutable snapshots is byte-identical including the manifest.
    built_at = max(accented.retrieved_at, unaccented.retrieved_at)
    manifest = build_manifest(
        root=settings.data_dir,
        version=BUILD_VERSION,
        works=[WORK_ID],
        passage_count=len(ordered),
        source_snapshot_ids=[
            accented.snapshot_id,
            unaccented.snapshot_id,
            *staged_snapshot_ids,
        ],
        generated=generated,
        qa_status=qa_state,
        built_at=built_at,
        source_artifact_ids=[artifact.artifact_id for artifact in _release_artifacts()],
        raw_snapshot_hashes={
            accented.artifact_id: accented.sha256,
            unaccented.artifact_id: unaccented.sha256,
        },
        parser_versions={SOURCE_ID: PARSER_VERSION},
        comparison_version=COMPARATOR_VERSION,
        software_git_commit=_git_commit(),
        build_config_sha256=sha256(
            orjson.dumps(
                {"sample": {f"{k}.{s}": r for (k, s), r in sorted(SAMPLE.items())}},
                option=orjson.OPT_SORT_KEYS,
            )
        ).hexdigest(),
        rights_summary={
            accented.artifact_id: RightsStatus.REFERENCE_ONLY.value,
            unaccented.artifact_id: RightsStatus.REFERENCE_ONLY.value,
        },
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_bytes(
        orjson.dumps(
            manifest.model_dump(mode="json", exclude_none=True),
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
        + b"\n"
    )

    category_counts = Counter(item.category.value for item in comparisons)
    return {
        "qa_status": qa_state.value,
        "qa_findings": qa_findings,
        "shared_qa_gate_result": shared_gate_error,
        "output_dir": str(output_dir),
        "kandas_sampled": kandas,
        "suktas_sampled": len(suktas),
        "parsed_units": len(accented.units),
        "canonical_mantras": len(ordered),
        "divergent_occurrences": len(divergences),
        "passages": len(passages),
        "text_versions": len(texts),
        "citations": len(citations),
        "translations": len(translations),
        "source_assertions": len(assertions) + len(divergence_records),
        "comparisons": len(comparisons),
        "comparison_categories": dict(sorted(category_counts.items())),
        "snapshot_sha256": {
            accented.artifact_id: accented.sha256,
            unaccented.artifact_id: unaccented.sha256,
        },
        "manifest_sha256": file_sha256(manifest_path),
    }


async def _gather(fetcher: PoliteFetcher) -> tuple[ArtifactSnapshot, ArtifactSnapshot]:
    accented = await _load_artifact("ACCENTED", fetcher)
    unaccented = await _load_artifact("UNACCENTED", fetcher)
    return accented, unaccented


#: Artifact ids registered by the rights authority in data/registry/source_artifacts.yaml.
#: Named explicitly rather than filtered by work_id so that a registry rename fails loudly
#: here instead of silently emitting an empty provenance set.
RELEASE_ARTIFACT_IDS = (
    "GRETIL.AV.SAUNAKA.ACCENTED.HTML",
    "GRETIL.AV.SAUNAKA.UNACCENTED.HTML",
    "VEDAWEB.AVS.WHITNEY_LANMAN_1905.PLAINTEXT.L2",
)
RELEASE_SOURCE_IDS = ("GRETIL", "VEDAWEB")


def _release_sources() -> list[Source]:
    """Source records read from the rights registry, never constructed locally.

    Earlier revisions of this build invented ``GRETIL_AVS`` and ``VEDAWEB_AVS`` source rows
    because the registry had no Atharvaveda entries yet.  The rights authority overruled
    that, correctly: these files are further *artifacts* of GRETIL and VEDAWEB, not new
    sources.  Rights differ per file within one host -- GRETIL's Rigveda TEI is CC BY-NC-SA
    while its Atharvaveda files are REFERENCE_ONLY, and VedaWeb's AVS Sanskrit resource
    carries the TITUS no-republication clause while its Whitney translation does not -- so a
    source-level rights value for an "AVS" pseudo-source could not have been correct.
    """
    registered = {source.source_id: source for source in load_sources()}
    missing = [name for name in RELEASE_SOURCE_IDS if name not in registered]
    if missing:
        raise ValueError(f"sources not registered: {missing}")
    return [registered[name] for name in RELEASE_SOURCE_IDS]


def _release_artifacts() -> list[SourceArtifact]:
    """Artifact records read from the rights registry, with the pinned checksums verified.

    The registry is the authority on rights; this build is the authority on which bytes it
    actually read.  Where both state a checksum they must agree, so a registry edit that
    silently repointed an artifact at different bytes would fail the build rather than
    produce a release whose provenance is a fiction.
    """
    registered = {artifact.artifact_id: artifact for artifact in load_source_artifacts()}
    missing = [name for name in RELEASE_ARTIFACT_IDS if name not in registered]
    if missing:
        raise ValueError(f"artifacts not registered: {missing}")
    return [registered[name] for name in RELEASE_ARTIFACT_IDS]


def _try_shared_gate(
    *,
    passages: list[Passage],
    texts: list[TextVersion],
    citations: list[Citation],
    translations: list[Translation],
    sources: list[Source],
) -> str:
    """Actually invoke the shared cross-Veda gate and report what really happens.

    Reported rather than skipped, so the AVS pilot is concrete evidence about whether the
    shared contract generalises beyond the Rigveda.
    """
    try:
        from vedagraph.qa import CorpusRecords, validate_corpus

        issues = validate_corpus(
            CorpusRecords(
                passages=passages,
                texts=texts,
                translations=translations,
                metadata=[],
                sources=sources,
                citations=citations,
                audio_recordings=[],
                audio_segments=[],
                source_assertions=[],
            )
        )
    except Exception as error:
        return f"{type(error).__name__}: {error}"
    return f"ran; {len(issues)} issue(s)"


def run_local_qa(
    *,
    passages: list[Passage],
    texts: list[TextVersion],
    citations: list[Citation],
    comparisons: list[Any],
    parsed_units: list[AVSUnit],
    canonical: dict[tuple[int, int, int], AVSUnit],
) -> tuple[list[dict[str, Any]], QAStatus]:
    """AVS-local QA gates, run here because the shared gate cannot run on AVS yet.

    ``vedagraph.qa.checks.validate_corpus`` reads ``passage.hierarchy["mandala"]`` for every
    MANTRA without gating on the Rigveda, so it raises KeyError on an AVS mantra.  That is
    Agent F's file to fix.  Rather than skip QA or pretend it passed, the checks that matter
    for this pilot are implemented here and their real results are reported.
    """
    findings: list[dict[str, Any]] = []

    def record(check: str, severity: str, message: str, **details: Any) -> None:
        findings.append(
            {"check_id": check, "severity": severity, "message": message, "details": details}
        )

    keys = [passage.canonical_key for passage in passages]
    if len(keys) != len(set(keys)):
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        record("unique_structural_ids", "ERROR", "duplicate canonical_key", keys=duplicates)

    urns = [passage.canonical_urn for passage in passages]
    if len(urns) != len(set(urns)):
        record("unique_structural_ids", "ERROR", "duplicate canonical_urn")

    entity_ids = [str(passage.entity_id) for passage in passages]
    if len(entity_ids) != len(set(entity_ids)):
        record("unique_structural_ids", "ERROR", "duplicate entity_id")

    for passage in passages:
        if uuid_for_urn(passage.canonical_urn) != passage.entity_id:
            record(
                "uuid_determinism",
                "ERROR",
                "entity_id is not uuid5(namespace, canonical_urn)",
                key=passage.canonical_key,
            )

    known = set(keys)
    for passage in passages:
        if passage.parent_key is not None and passage.parent_key not in known:
            record(
                "parent_ref_integrity",
                "ERROR",
                "parent_key does not resolve in this build",
                key=passage.canonical_key,
                parent=passage.parent_key,
            )

    # Sequence continuity. Gaps are REPORTED, never filled. A gap here is a real source
    # defect (a mislabelled first verse leaves its slot empty) and must stay visible.
    by_parent: dict[str | None, list[int]] = defaultdict(list)
    for passage in passages:
        if passage.entity_type == EntityType.MANTRA:
            by_parent[passage.parent_key].append(passage.sequence_in_parent)
    for parent, sequences in sorted(by_parent.items(), key=lambda item: item[0] or ""):
        expected = set(range(1, max(sequences) + 1))
        missing = sorted(expected - set(sequences))
        if missing:
            record(
                "sequence_continuity",
                "WARNING",
                "mantra sequence has gaps; reported, not filled",
                parent=parent,
                missing=missing,
                observed=len(sequences),
                highest=max(sequences),
            )

    for text in texts:
        if normalize_nfc(text.text_nfc) != text.text_nfc:
            record("unicode_nfc_stability", "ERROR", "text_nfc is not NFC-stable")
        if normalize_nfc(normalize_nfc(text.text_original)) != normalize_nfc(text.text_original):
            record("normalization_determinism", "ERROR", "NFC is not idempotent")

    primary = [text for text in texts if text.text_role == TextRole.PRIMARY_TEXT]
    if not all(text.accented for text in primary):
        record(
            "accent_preservation",
            "ERROR",
            "a PRIMARY_TEXT record from the accented artifact lost its accents",
            unaccented=sum(1 for text in primary if not text.accented),
        )
    for text in texts:
        if text.text_role == TextRole.SEARCH_DERIVATIVE and text.accented:
            record("accent_preservation", "WARNING", "search surface still carries accents")

    canonical_labels = {
        citation.passage_id for citation in citations if citation.system == "AVS_ROTH_WHITNEY_1856"
    }
    mantra_ids = {
        passage.entity_id for passage in passages if passage.entity_type == EntityType.MANTRA
    }
    if canonical_labels != mantra_ids:
        record(
            "citation_coverage",
            "ERROR",
            "not every mantra carries its canonical citation",
            missing=len(mantra_ids - canonical_labels),
        )

    # No silently missing records: parsed units must equal canonical units plus divergences.
    accounted = sum(1 for _ in canonical)
    if accounted != len(parsed_units):
        deficit = len(parsed_units) - accounted
        record(
            "no_silently_missing_records",
            "INFO",
            "parsed units exceed canonical mantras; the surplus is retained as explicit "
            "NON_CANONICAL_DUPLICATE_OCCURRENCE assertions",
            parsed_units=len(parsed_units),
            canonical_mantras=accounted,
            retained_as_divergences=deficit,
        )

    severities = {finding["severity"] for finding in findings}
    if "ERROR" in severities:
        status = QAStatus.FAILED
    elif severities:
        status = QAStatus.PASSED_WITH_WARNINGS
    else:
        status = QAStatus.PASSED
    return findings, status


def _text_version(
    *,
    passage_id: UUID,
    version_id: str,
    text: str,
    role: TextRole,
    artifact: ArtifactSnapshot,
    locator: str,
    rights_override: RightsStatus | None = None,
) -> TextVersion:
    normalized = normalize_nfc(text)
    return TextVersion(
        text_id=_derived_uuid("text", passage_id, version_id),
        passage_id=passage_id,
        language="sa",
        script="Latin",
        text_form=TextForm.SAMHITA,
        text_role=role,
        text_version_id=version_id,
        text_original=text,
        text_nfc=normalized,
        accented=has_vedic_accents(text),
        transliteration_scheme="GRETIL_TITUS_LATIN_AVS",
        source_id=SOURCE_ID,
        source_artifact_id=artifact.artifact_id,
        source_locator=locator,
        content_sha256=sha256(normalized.encode("utf-8")).hexdigest(),
        rights_status=rights_override or RightsStatus.REFERENCE_ONLY,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--translation-stage",
        type=Path,
        default=Path("data/staged/atharvaveda_translation_stage.json"),
        help="optional staged translation payload; absent means zero Translation records",
    )
    args = parser.parse_args()
    summary = build(Settings(), translation_stage=args.translation_stage)
    print(orjson.dumps(summary, option=orjson.OPT_INDENT_2).decode())


if __name__ == "__main__":
    main()
