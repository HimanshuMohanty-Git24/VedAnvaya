"""Build the complete Atharvaveda-Samhita (Saunaka) WORKING PRIVATE corpus.

What this is, stated plainly
---------------------------
This is the whole Saunaka Atharvaveda, ingested from an existing machine-readable Sanskrit
source, for VedaGraph product development.  It is **not** an independent transcription of
Roth & Whitney, Berlin 1856, and nothing in it may be described as one.  The lineage is:

    Orlandi 1991 (Pisa) transliteration, collated with Roth/Whitney 1856
      -> TITUS redaction (Gippert 1997; books 11-20 improved by Griffiths 2000,
         Kubisch 2007, revised Griffiths 2009)
      -> GRETIL legacy-HTML re-host
      -> this build

The earlier image-based pipeline (``build_atharvaveda_canonical.py``,
``data/canonical/atharvaveda_saunaka_1856_*``) attempted that independent transcription and
did not clear calibration.  It is cancelled.  Its outputs are stale and are neither read nor
regenerated here.  This build supersedes them as the AV working corpus; it does not
supersede them as a scholarly edition, because it does not claim to be one.

Relationship to ``build_atharvaveda_pilot.py``
----------------------------------------------
The pilot proved the AVS source stack on 11 deliberately awkward suktas.  Everything it
proved is reused here by direct import rather than reimplemented: identity, the canonical
selection rule for duplicate locators, the TextVersion shape, the QA gates, the rights
registry reads.  The differences are scope and labelling:

* scope -- every kanda, no ``suktas=`` filter on the parser;
* labelling -- the corpus carries an explicit ``WORKING_PRIVATE`` status assertion and a
  ``TEXT_LINEAGE_IS_NOT_AN_INDEPENDENT_1856_TRANSCRIPTION`` assertion, so a downstream
  reader cannot mistake it for the abandoned transcription project's output;
* structural audit -- the anomaly classes the pilot sampled are now counted over the whole
  corpus and written to ``qa_issues.jsonl`` as bounded, named backlog rather than blockers.

Rights
------
Unchanged and still binding.  The GRETIL/TITUS artifacts are ``REFERENCE_ONLY`` and the
upstream TITUS clause forbids republication; the Whitney & Lanman 1905 translation layer is
public domain in the US.  Those values are read from ``data/registry``, never asserted here.
This corpus is for PRIVATE development use.  Publishing it, or anything derived from the
Sanskrit layer, is not authorised by this build.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

import orjson
from pydantic import BaseModel

# The pilot is a sibling script, not a package module.  Importing it is deliberate: the
# working corpus must be built by the SAME builders the pilot was audited on, so that a
# change to identity, canonical selection or QA cannot silently apply to one and not the
# other.  Reimplementing them here would have created exactly the second architecture the
# build brief forbids.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_atharvaveda_pilot import (
    ACCENTED_VERSION_ID,
    SEARCH_VERSION_ID,
    TRANSLATION_SNAPSHOT_SOURCE_ID,
    TRANSLATION_SOURCE_ID,
    UNACCENTED_VERSION_ID,
    ArtifactSnapshot,
    _derived_uuid,
    _git_commit,
    _passage,
    _release_artifacts,
    _release_sources,
    _select_canonical,
    _text_version,
    _try_shared_gate,
    run_local_qa,
)

from vedagraph.compare.text import (
    COMPARATOR_VERSION,
    VersionReading,
    compare_readings,
)
from vedagraph.config import Settings
from vedagraph.config.registry import load_sources, load_works
from vedagraph.identity import (
    avs_kanda_identity,
    avs_mantra_identity,
    avs_sukta_identity,
)
from vedagraph.ingest.adapters.atharvaveda_gretil import (
    PARSER_VERSION,
    SNAPSHOT_SOURCE_ID,
    SOURCE_ID,
    WORK_ID,
    AVSUnit,
    GretilAVSAdapter,
)
from vedagraph.ingest.fetcher import PoliteFetcher
from vedagraph.models import (
    Citation,
    Passage,
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
    TextRole,
    TranslationAlignment,
)
from vedagraph.normalize import ComparisonForm, comparison_form, normalize_nfc
from vedagraph.storage import write_jsonl
from vedagraph.storage.manifest import build_manifest, file_sha256

BUILD_ID = "atharvaveda_saunaka_digital_working_v1"
BUILD_VERSION = "1.0.0-avs-digital-working.1"

#: The corpus label required by the build brief.  It names the *corpus*, not a new
#: TextVersion id: the three per-layer text_version_ids below are already registered in
#: data/registry/text_versions.yaml and are NOT redesigned here.
WORKING_CORPUS_ID = "ATHARVAVEDA_SAUNAKA_DIGITAL_WORKING_V1"
WORKING_STATUS = "WORKING_PRIVATE"

TRANSLATION_STAGE = Path("data/staged/atharvaveda_translation_stage_full_v1.json")

#: Comparison values from the reference literature.  Recorded so the computed counts can be
#: checked against them; NEVER used to correct, pad or truncate the computed counts.
REFERENCE_COUNTS = {"kandas": 20, "suktas": 731, "mantras": 5839}

#: Verbatim lineage, kept as data so the honesty requirement survives a docstring edit.
LINEAGE = (
    "Gli inni dell' Atharvaveda (Saunaka), transliteration by Chatia Orlandi, Pisa 1991, "
    "collated with R. Roth and W. D. Whitney, Atharva Veda Sanhita, Berlin 1856; input by "
    "Vladimir Petr and Petr Vavrousek; TITUS redaction by Jost Gippert 1997; books 11-20 "
    "improved by Arlo Griffiths 2000 and Philipp Kubisch 2007, revised by Arlo Griffiths "
    "2009; re-hosted by GRETIL as legacy HTML"
)


async def _load_full_artifact(variant: str, fetcher: PoliteFetcher) -> ArtifactSnapshot:
    """Same load path as the pilot, with the sukta filter removed.

    ``parse_units`` applies bounding *after* run detection, so an unbounded parse sees
    exactly the units a bounded parse would have seen for the suktas it kept.  Dropping the
    filter therefore widens the corpus without changing how any unit is formed.
    """
    adapter = GretilAVSAdapter(variant=variant)
    resource = (await adapter.discover("AVS"))[0]
    snapshot = await adapter.fetch(resource, fetcher)
    header = adapter.extract_header_metadata(snapshot.content_path)
    units = adapter.parse_units(snapshot.content_path)
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


async def _gather_full(fetcher: PoliteFetcher) -> tuple[ArtifactSnapshot, ArtifactSnapshot]:
    return (
        await _load_full_artifact("ACCENTED", fetcher),
        await _load_full_artifact("UNACCENTED", fetcher),
    )


def _load_stage(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"verses": [], "snapshot_ids": [], "scope": "ABSENT"}
    return orjson.loads(path.read_bytes())


def structural_audit(
    *,
    canonical: dict[tuple[int, int, int], AVSUnit],
    divergences: list[AVSUnit],
    units: list[AVSUnit],
) -> dict[str, Any]:
    """Count every structural anomaly class over the whole corpus.

    Reporting only.  Nothing here renumbers, fills or removes a record: a gap in this corpus
    is a fact about the edition's numbering and stays visible.
    """
    ordered = sorted(canonical)
    kandas = sorted({k for k, _, _ in ordered})
    suktas = sorted({(k, s) for k, s, _ in ordered})

    suktas_by_kanda: dict[int, list[int]] = defaultdict(list)
    for kanda, sukta in suktas:
        suktas_by_kanda[kanda].append(sukta)
    # Keys are stringified throughout: these dicts are serialised into a SourceAssertion
    # value and into qa_issues.jsonl, and JSON has no integer keys.
    sukta_gaps = {
        str(kanda): sorted(set(range(1, max(numbers) + 1)) - set(numbers))
        for kanda, numbers in sorted(suktas_by_kanda.items())
        if set(range(1, max(numbers) + 1)) - set(numbers)
    }

    mantras_by_sukta: dict[tuple[int, int], list[int]] = defaultdict(list)
    for kanda, sukta, mantra in ordered:
        mantras_by_sukta[(kanda, sukta)].append(mantra)
    mantra_gaps = {
        f"{kanda}.{sukta}": sorted(set(range(1, max(numbers) + 1)) - set(numbers))
        for (kanda, sukta), numbers in sorted(mantras_by_sukta.items())
        if set(range(1, max(numbers) + 1)) - set(numbers)
    }

    single_pada_by_kanda = Counter(
        unit.kanda for unit in canonical.values() if unit.is_single_pada_unit
    )
    units_by_kanda = Counter(unit.kanda for unit in canonical.values())

    return {
        "kandas": len(kandas),
        "kanda_numbers": kandas,
        "suktas": len(suktas),
        "suktas_per_kanda": {str(k): len(v) for k, v in sorted(suktas_by_kanda.items())},
        "mantras": len(ordered),
        "padas": sum(len(unit.pada_texts) for unit in units),
        "parsed_units": len(units),
        "duplicate_locator_triples": sorted(
            f"{u.kanda}.{u.sukta}.{u.mantra}" for u in divergences
        ),
        "sukta_number_gaps": sukta_gaps,
        "mantra_number_gaps": mantra_gaps,
        "label_vs_printed_marker_disagreements": sorted(
            f"{u.kanda}.{u.sukta}.{u.mantra}"
            for u in canonical.values()
            if u.label_agrees_with_source_marker is False
        ),
        "units_with_no_printed_verse_marker": sum(
            1 for u in canonical.values() if u.source_verse_marker is None
        ),
        "single_pada_units": sum(single_pada_by_kanda.values()),
        "single_pada_units_by_kanda": {
            str(k): v for k, v in sorted(single_pada_by_kanda.items())
        },
        "units_by_kanda": {str(k): v for k, v in sorted(units_by_kanda.items())},
        "units_with_alternate_numbering": sum(
            1 for u in canonical.values() if u.alternate_citation_label is not None
        ),
        "units_with_explicit_alternate_absence": sum(
            1 for u in canonical.values() if u.alternate_absent
        ),
        "kanda_19_mantras": sum(1 for k, _, _ in ordered if k == 19),
        "kanda_19_suktas": sum(1 for k, _ in suktas if k == 19),
        "kanda_20_mantras": sum(1 for k, _, _ in ordered if k == 20),
        "kanda_20_suktas": sum(1 for k, _ in suktas if k == 20),
        "reference_counts": REFERENCE_COUNTS,
        "matches_reference_counts": {
            "kandas": len(kandas) == REFERENCE_COUNTS["kandas"],
            "suktas": len(suktas) == REFERENCE_COUNTS["suktas"],
            "mantras": len(ordered) == REFERENCE_COUNTS["mantras"],
        },
    }


def _structural_qa_issues(audit: dict[str, Any], stage: dict[str, Any]) -> list[dict[str, Any]]:
    """Bounded, named backlog entries.  None of these blocks the working corpus."""
    issues: list[dict[str, Any]] = []

    def add(check: str, severity: str, message: str, **details: Any) -> None:
        issues.append(
            {"check_id": check, "severity": severity, "message": message, "details": details}
        )

    if audit["duplicate_locator_triples"]:
        add(
            "av_duplicate_locator_triples",
            "WARNING",
            "the edition prints two different units under one (kanda, sukta, mantra); the "
            "second occurrence is retained verbatim as a NON_CANONICAL_DUPLICATE_OCCURRENCE "
            "assertion and is NOT renumbered",
            triples=audit["duplicate_locator_triples"],
        )
    if audit["mantra_number_gaps"]:
        add(
            "av_mantra_number_gaps",
            "WARNING",
            "mantra numbering has gaps in the source edition; reported, never filled",
            suktas_affected=len(audit["mantra_number_gaps"]),
            gaps=audit["mantra_number_gaps"],
        )
    if audit["sukta_number_gaps"]:
        add(
            "av_sukta_number_gaps",
            "WARNING",
            "sukta numbering has gaps in the source edition; reported, never filled",
            gaps=audit["sukta_number_gaps"],
        )
    if audit["label_vs_printed_marker_disagreements"]:
        add(
            "av_label_marker_disagreement",
            "WARNING",
            "the parsed locator and the edition's own printed ||N|| marker disagree; both "
            "witnesses are kept and neither is treated as authoritative",
            units=audit["label_vs_printed_marker_disagreements"],
        )
    add(
        "av_prose_paryaya_not_classified",
        "INFO",
        "the source marks no unit as prose or as verse, so this corpus asserts no metrical "
        "classification anywhere. single_pada_unit is a fact about the printed line count "
        "and is NOT a prose claim. Classifying the paryaya material of kandas 15 and 16 "
        "(and 8.10, 9.6, 11.3, 12.5, 13.4, 18.4) is open backlog",
        single_pada_units=audit["single_pada_units"],
        single_pada_units_by_kanda=audit["single_pada_units_by_kanda"],
    )
    add(
        "av_traditional_metadata_absent",
        "INFO",
        "the source carries no rishi, devata or chandas field anywhere, so this corpus emits "
        "zero traditional-metadata records. Absence of evidence, recorded as such; it is NOT "
        "licence to infer AV metadata from Rigvedic Anukramani rules or to generate it",
        rishi=0,
        devata=0,
        chandas=0,
    )
    if stage.get("scope") == "ABSENT":
        add(
            "av_translation_layer_absent",
            "WARNING",
            "no staged translation payload was found, so this build emits zero Translation "
            "records",
            expected_path=str(TRANSLATION_STAGE),
        )
    for key in ("kanda_alias_misses", "sukta_alias_misses", "truncated_stanza_pages"):
        values = stage.get(key) or []
        if values:
            add(
                f"av_translation_{key}",
                "WARNING",
                f"translation staging reported {key}",
                values=values,
            )
    return issues


def build(settings: Settings, *, translation_stage: Path) -> dict[str, Any]:
    fetcher = PoliteFetcher(settings)
    accented, unaccented = asyncio.run(_gather_full(fetcher))

    canonical, divergences = _select_canonical(accented.units)
    unaccented_by_triple, unaccented_divergences = _select_canonical(unaccented.units)
    stage = _load_stage(translation_stage)
    staged_translations = {
        (int(v["kanda"]), int(v["sukta"]), int(v["mantra"])): v for v in stage["verses"]
    }
    staged_snapshot_ids = tuple(stage.get("snapshot_ids", ()))

    ordered = sorted(canonical)
    kandas = sorted({k for k, _, _ in ordered})
    suktas = sorted({(k, s) for k, s, _ in ordered})

    passages: list[Passage] = []
    texts: list[TextVersion] = []
    citations: list[Citation] = []
    assertions: list[SourceAssertion] = []
    translations: list[Translation] = []

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

    audit = structural_audit(canonical=canonical, divergences=divergences, units=accented.units)

    # -- the two assertions that keep this corpus honestly labelled --------------------
    assertions.append(
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", BUILD_ID, "working-status"),
            subject_id=WORKING_CORPUS_ID,
            predicate="CORPUS_STATUS",
            value={
                "status": WORKING_STATUS,
                "build_id": BUILD_ID,
                "work_id": WORK_ID,
                "recension": "Shaunaka",
                "purpose": "VedaGraph product development on a private build",
                "sanskrit_layer_rights": RightsStatus.REFERENCE_ONLY.value,
                "publication_authorised": False,
                "note": (
                    "the Sanskrit layer is REFERENCE_ONLY and its upstream TITUS clause "
                    "forbids republication, so this corpus may be read, keyed and compared "
                    "against locally and may NOT be published or redistributed"
                ),
            },
            source_id=SOURCE_ID,
            source_artifact_id=accented.artifact_id,
            source_locator=accented.url,
            status=AssertionStatus.UNREVIEWED,
            evidence=(
                "rights read from data/registry/text_versions.yaml and "
                "data/registry/source_artifacts.yaml, not asserted by this build"
            ),
        )
    )
    assertions.append(
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", BUILD_ID, "lineage-honesty"),
            subject_id=WORKING_CORPUS_ID,
            predicate="TEXT_LINEAGE_IS_NOT_AN_INDEPENDENT_1856_TRANSCRIPTION",
            value={
                "lineage": LINEAGE,
                "is_independent_roth_whitney_1856_transcription": False,
                "roth_whitney_1856_role": (
                    "the 1856 edition is a COLLATION BASIS inside the Orlandi/TITUS lineage, "
                    "not the text this corpus was read from"
                ),
                "superseded_build": "atharvaveda_saunaka_1856_provisional",
                "superseded_reason": (
                    "the image-based independent transcription project was cancelled before "
                    "it cleared accent calibration; its artifacts are stale and are neither "
                    "read nor regenerated by this build"
                ),
            },
            source_id=SOURCE_ID,
            source_artifact_id=accented.artifact_id,
            source_locator=accented.url,
            status=AssertionStatus.UNREVIEWED,
            evidence=(
                "the artifact preamble names Orlandi 1991 collated with Roth/Whitney 1856 "
                "and the TITUS redaction chain, read verbatim from the snapshot header"
            ),
        )
    )
    assertions.append(
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", BUILD_ID, "structural-audit"),
            subject_id=WORKING_CORPUS_ID,
            predicate="COMPUTED_STRUCTURAL_AUDIT",
            value=audit,
            source_id=SOURCE_ID,
            source_artifact_id=accented.artifact_id,
            source_locator=accented.url,
            status=AssertionStatus.UNREVIEWED,
            evidence=(
                "every number computed from the snapshot this build read; the reference "
                "counts are recorded for comparison and were not used to adjust anything"
            ),
        )
    )
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
    assertions.append(
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", BUILD_ID, "rv-parallel-policy"),
            subject_id=accented.artifact_id,
            predicate="KANDA_20_TEXT_READ_ONLY_FROM_THIS_ARTIFACT",
            value={
                "kanda_20_mantras_in_build": audit["kanda_20_mantras"],
                "kanda_20_suktas_in_build": audit["kanda_20_suktas"],
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

    # Translations whose printed citation has no passage here. Never re-attached.
    for triple in sorted(set(staged_translations) - set(canonical)):
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

    for namespace, registered in (
        (SNAPSHOT_SOURCE_ID, SOURCE_ID),
        (TRANSLATION_SNAPSHOT_SOURCE_ID, TRANSLATION_SOURCE_ID),
    ):
        every_snapshot_id = (accented.snapshot_id, unaccented.snapshot_id, *staged_snapshot_ids)
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
                    "here. The namespace is deliberate storage layout and is NOT a rights "
                    "claim. Rights attach to the artifact ids in source_artifacts.jsonl."
                ),
            )
        )

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

    output_dir = settings.data_dir / "canonical" / BUILD_ID
    collections: dict[str, list[BaseModel]] = {
        "works.jsonl": [work for work in load_works() if work.work_id == WORK_ID],
        "passages.jsonl": passages,
        "text_versions.jsonl": texts,
        "translations.jsonl": translations,
        "traditional_metadata.jsonl": [],
        "sources.jsonl": _release_sources(),
        "source_artifacts.jsonl": _release_artifacts(),
        "citations.jsonl": citations,
        "source_assertions.jsonl": assertions + divergence_records,
        "text_comparisons.jsonl": comparisons,
        "audio_recordings.jsonl": [],
        "audio_segments.jsonl": [],
    }

    registered_artifacts = {item.artifact_id: item for item in _release_artifacts()}
    for artifact in (accented, unaccented):
        pinned = registered_artifacts[artifact.artifact_id].checksum_sha256
        if pinned is not None and pinned != artifact.sha256:
            raise ValueError(
                f"registry checksum mismatch for {artifact.artifact_id}: "
                f"registry {pinned}, snapshot {artifact.sha256}"
            )

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
    qa_findings = qa_findings + _structural_qa_issues(audit, stage)
    if any(finding["severity"] == "ERROR" for finding in qa_findings):
        qa_state = QAStatus.FAILED
    elif qa_state is QAStatus.PASSED and qa_findings:
        qa_state = QAStatus.PASSED_WITH_WARNINGS

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

    built_at = max(accented.retrieved_at, unaccented.retrieved_at)
    manifest = build_manifest(
        root=settings.data_dir,
        version=BUILD_VERSION,
        works=[WORK_ID],
        passage_count=len(ordered),
        source_snapshot_ids=[accented.snapshot_id, unaccented.snapshot_id, *staged_snapshot_ids],
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
                {
                    "build_id": BUILD_ID,
                    "working_corpus_id": WORKING_CORPUS_ID,
                    "status": WORKING_STATUS,
                    "scope": "FULL_CORPUS",
                    "lineage": LINEAGE,
                    "translation_stage": str(translation_stage),
                },
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

    accented_texts = [t for t in texts if t.text_version_id == ACCENTED_VERSION_ID]
    return {
        "build_id": BUILD_ID,
        "working_corpus_id": WORKING_CORPUS_ID,
        "status": WORKING_STATUS,
        "qa_status": qa_state.value,
        "qa_findings": len(qa_findings),
        "qa_severities": dict(Counter(f["severity"] for f in qa_findings)),
        "shared_qa_gate_result": shared_gate_error,
        "output_dir": str(output_dir),
        "structural_audit": audit,
        "unaccented_divergent_occurrences": len(unaccented_divergences),
        "passages": len(passages),
        "text_versions": len(texts),
        "sanskrit_coverage": {
            "mantras": len(ordered),
            "with_accented_primary_text": len(accented_texts),
            "accented_primary_text_carrying_accents": sum(1 for t in accented_texts if t.accented),
            "empty_primary_texts": sum(1 for t in accented_texts if not t.text_nfc.strip()),
        },
        "citations": len(citations),
        "translations": len(translations),
        "translations_unaligned": len(set(staged_translations) - set(canonical)),
        "source_assertions": len(assertions) + len(divergence_records),
        "comparisons": len(comparisons),
        "comparison_categories": dict(
            sorted(Counter(item.category.value for item in comparisons).items())
        ),
        "snapshot_sha256": {
            accented.artifact_id: accented.sha256,
            unaccented.artifact_id: unaccented.sha256,
        },
        "manifest_sha256": file_sha256(manifest_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--translation-stage",
        type=Path,
        default=TRANSLATION_STAGE,
        help="staged translation payload; absent means zero Translation records",
    )
    args = parser.parse_args()
    summary = build(Settings(), translation_stage=args.translation_stage)
    print(orjson.dumps(summary, option=orjson.OPT_INDENT_2).decode())


if __name__ == "__main__":
    main()
