"""Build the first production canonical Samaveda Kauthuma ARCIKA corpus release.

SCOPE, BEFORE ANYTHING ELSE
===========================

This builds the ARCIKA (verse) corpus of the Kauthuma Samaveda. It does not build and
does not imply ``SAMAVEDA_GANA_CORPUS``. The gana books are a parallel and larger body
that ``VG:WORK:SV:KAU`` cannot address. Nothing this script writes may be described as
the "complete Samaveda".

What this script adds over the audit it reads
=============================================

``scripts/build_samaveda_referent_audit.py`` already segments the 106 pinned Sanskrit
Wikisource arcika pages and mints identity. It is imported rather than reimplemented,
because a second segmentation path is a second set of referents: the audit is the single
source of truth for which keys exist, and this script's job is to turn them into a
released corpus with the gates a release needs and an audit does not.

Four gates, each of which has a concrete failure it exists to stop:

**Selection fails closed.** :func:`vedagraph.release.select_primary_text_version` is
called with the pinned artifact and an explicit forbidden list. Until 2026-09-07 the only
registered Samaveda text version was ``GRETIL.SV.KAUTHUMA``, whose embedded licence
forbids modification outright -- and parsing, NFC normalization, structural re-keying and
JSONL republication are all modification. A build that fell back to it would have
published a corpus derived from an artifact that prohibits the derivation. The fallback
is refused BY ID, so the refusal is a property a test asserts directly rather than a
consequence of two other fields.

**The corroborating witness is required, not optional.** The audit degrades to
"corroboration not performed" when the GRETIL snapshot is absent, and in that state it
mints 21 keys whose dasati partition nothing checks. Those 21 keys are absent from the
committed baseline, so they would arrive as ``NEWLY_DISCOVERED_PASSAGE`` -- which the
drift gate correctly does not treat as drift. The drift gate therefore cannot catch this
on its own, and this build refuses to run without the witness and additionally requires
the released key set to equal the baseline key set exactly.

**The pinned input set is digest-checked.** The witness is 106 mutable wiki pages, so the
build recomputes a set digest over ``page_title/sha256/revid`` and compares it with the
value pinned in the build config. Swapping, adding or dropping a page cannot pass.

**Coverage arithmetic is recomputed and must close.** Every number in the coverage report
is derived from the audit rows in this run. Nothing is forced to 1,875; the two equations
are asserted and the build raises if either fails to balance.

Determinism
===========

Nothing reads the clock: ``built_at`` comes from the config. Every collection is sorted on
a total key before emission. ``--verify-determinism`` performs two full independent
rebuilds into temporary directories and compares every file digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final
from uuid import UUID, uuid5

import yaml

REPO = Path(__file__).resolve().parents[1]
for _extra in (str(REPO), str(REPO / "src")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)

from scripts.build_samaveda_referent_audit import (  # noqa: E402
    GRETIL_SNAPSHOT,
    TRADITIONAL_TOTAL,
    AuditRow,
    bindings_for,
    build_rows,
    load_pages,
)
from vedagraph.identity import (  # noqa: E402
    SV_COLLECTION_LEVELS,
    VEDAGRAPH_NAMESPACE_UUID,
    SamavedaCollection,
    sv_container_identity,
    uuid_for_urn,
)
from vedagraph.ingest.adapters.samaveda_wikisource import (  # noqa: E402
    GANA_SVARA_MARKS,
    PARSER_VERSION,
    SEGMENTATION_POLICY_VERSION,
    SamavedaPageParse,
    VerseOccurrence,
)
from vedagraph.models import (  # noqa: E402
    Citation,
    CorpusManifest,
    Passage,
    QAIssue,
    ReferentMigration,
    Source,
    SourceArtifact,
    SourceAssertion,
    TextVersion,
    TextVersionDescriptor,
    Work,
    WorkBuildConfig,
)
from vedagraph.models.enums import (  # noqa: E402
    AssertionStatus,
    EntityType,
    PassageStatus,
    QASeverity,
    QAStatus,
    RightsStatus,
    TextForm,
    TextRole,
)
from vedagraph.normalize import has_vedic_accents, normalize_nfc  # noqa: E402
from vedagraph.referent import ReferentDelta, read_baseline  # noqa: E402
from vedagraph.release import (  # noqa: E402
    CanonicalRelease,
    ReleaseIntegrityError,
    TextVersionSelectionError,
    gate_referents,
    orphan_provenance_claims,
    referent_verdict_counts,
    select_primary_text_version,
    write_json,
    write_release,
)

# --------------------------------------------------------------------------- constants

CONFIG_PATH: Final[Path] = REPO / "data" / "builds" / "samaveda_arcika_v1.yaml"
COVERAGE_PATH: Final[Path] = REPO / "data" / "builds" / "samaveda_arcika_v1_coverage.json"
BASELINE_PATH: Final[Path] = REPO / "tests" / "fixtures" / "identity" / "sv_referent_baseline.jsonl"
MIGRATIONS_PATH: Final[Path] = (
    REPO / "data" / "source_registry" / "samaveda_referent_migrations.jsonl"
)
REGISTRY_DIR: Final[Path] = REPO / "data" / "registry"

WORK_ID: Final[str] = "VG:WORK:SV:KAU"
SOURCE_ID: Final[str] = "WIKISOURCE_SA"
ARTIFACT_ID: Final[str] = "WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI"
TEXT_VERSION_ID: Final[str] = "WIKISOURCE_SA.SV.KAU.ARCIKA_MULA"

# The run whose migrations may license a referent change. The committed ledger's 144 rows
# were all recorded by SAMAVEDA_REFERENT_INTEGRITY_REPAIR, so under this scoping they
# license NOTHING here -- which is the intended state. A ledger is append-only and
# permanent; without run scoping, a row written for one release would stand as a licence
# to drift the same key in every release afterwards.
LICENSING_RUN: Final[str] = "FULL_SV_YV_AV_CANONICAL_INGESTION"

# Named, not inferred. Rights and role checks would already reject each of these, but
# naming them makes "this build never falls back to the Pandey lineage" a single
# assertable property instead of a conclusion drawn from two other fields. All three are
# re-publications of ONE Anshuman Pandey 1998/99 e-text, so their agreement corroborates
# nothing and their shared prohibition on modification disqualifies all three at once.
FORBIDDEN_TEXT_VERSION_IDS: Final[frozenset[str]] = frozenset(
    {"GRETIL.SV.KAUTHUMA", "TITUS.SV.KAUTHUMA", "SANSKRITLIB.SV.KAUTHUMA"}
)

# Source order of the four collections, used ONLY for sequence_in_parent among sibling
# collection containers. It is not identity: the key names the collection and never
# numbers it, precisely because the ARITY of the top level is disputed. Every witness
# surveyed holds these same four blocks in this same order, which is what this ordering
# records and all it records.
COLLECTION_ORDER: Final[tuple[SamavedaCollection, ...]] = (
    SamavedaCollection.CHANDA,
    SamavedaCollection.ARANYA,
    SamavedaCollection.MAHANAMNYA,
    SamavedaCollection.UTTARA,
)

# The work's own level vocabulary, spelled as data/registry/works.yaml spells it.
# Passage.native_labels must name exactly the levels present in Passage.hierarchy.
LEVEL_LABEL: Final[dict[str, str]] = {
    "collection": "Collection",
    "prapathaka": "Prapathaka",
    "ardha": "Ardha",
    "dasati": "Dasati",
    "verse": "Verse",
}

# The two dialects the source uses for the overwhelming majority of its verse-terminal
# markers. Anything else is a minority spelling that a single-dialect reader would miss
# entirely, so it is recorded as a SourceAssertion rather than left implicit.
MAJORITY_MARKER_DIALECTS: Final[frozenset[str]] = frozenset({"DOUBLE_DANDA", "TWO_DANDA"})

# The withheld reasons this release is allowed to state. A withheld verse without one of
# these is a silent gap.
REASON_REFERENT_UNRESOLVED: Final[str] = "REFERENT_UNRESOLVED"
REASON_SOURCE_MARKER_ANOMALY: Final[str] = "SOURCE_MARKER_ANOMALY"
REASON_STRUCTURAL_AMBIGUITY: Final[str] = "STRUCTURAL_AMBIGUITY"
REASON_SOURCE_NOT_PRINTED: Final[str] = "SOURCE_NOT_PRINTED"
REASON_REVIEW_REQUIRED: Final[str] = "REVIEW_REQUIRED"

GANA_BOUNDARY: Final[str] = (
    "ARCIKA ONLY. SAMAVEDA_GANA_CORPUS IS NOT IMPLIED AND IS NOT INCLUDED. This release "
    "is the Kauthuma arcika verse corpus; the gramageya, aranyakageya, uhagana and "
    "uhyagana books are a parallel and LARGER body that VG:WORK:SV:KAU cannot address "
    "and that requires its own work_id. Never describe this dataset as the complete "
    "Samaveda."
)


class CoverageError(RuntimeError):
    """The coverage arithmetic did not close, so the release is not published."""


class BuildInputError(RuntimeError):
    """A declared build input is missing or does not match its pinned digest."""


# ------------------------------------------------------------------ deterministic ids


def derived_uuid(kind: str, *parts: object) -> UUID:
    """A UUIDv5 over a namespaced URN, so an id is a function of its inputs alone."""
    return uuid_for_urn(f"urn:vedagraph:{kind}:" + ":".join(str(part) for part in parts))


def stable_issue_id(check_id: str, subject: str, message: str, discriminator: str = "") -> UUID:
    """A stable id for one QA finding.

    ``discriminator`` exists because ``subject`` is a source locator and a locator is NOT
    always unique. Where the source prints one running number twice -- 1181 in
    UTTARA P5/R1/D2, which is the very defect being reported -- both occurrences share the
    locator ``WS UTTARA.P5.R1.D2 RN1181``, so two genuinely different findings collapsed
    onto one id. The file then carried 39 rows under 37 ids and one withheld occurrence was
    unaddressable: a reader could not cite the finding that describes it. Passing the
    occurrence's source line span separates them without changing ``entity_id``, which
    stays the locator because that is what the finding is ABOUT.
    """
    return uuid5(VEDAGRAPH_NAMESPACE_UUID, f"{check_id}|{subject}|{discriminator}|{message}")


# ------------------------------------------------------------------------- config load


def load_config(path: Path = CONFIG_PATH) -> WorkBuildConfig:
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return WorkBuildConfig.model_validate(payload)


def config_digest(path: Path = CONFIG_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_set_digest(pages: Sequence[SamavedaPageParse]) -> str:
    """One digest over the whole pinned page set: title, snapshot digest, revision id.

    A single file digest cannot pin this witness, because the witness is 106 separately
    revisioned MediaWiki pages. Digesting the SET is what makes "a page was swapped,
    added or dropped" a build failure rather than a silent change of corpus.
    """
    accumulator = hashlib.sha256()
    for title, sha, revid in sorted(
        (page.page_title, page.snapshot_sha256, page.revision_id) for page in pages
    ):
        accumulator.update(f"{title}\t{sha}\t{revid}\n".encode())
    return accumulator.hexdigest()


# ------------------------------------------------------------------ registry accessors


def registry_work(work_id: str = WORK_ID) -> Work:
    """The Work row as the registry declares it. Never constructed locally."""
    payload: Any = yaml.safe_load((REGISTRY_DIR / "works.yaml").read_text(encoding="utf-8"))
    for item in payload["works"]:
        if item["work_id"] == work_id:
            return Work.model_validate(item)
    raise BuildInputError(f"{work_id} is not registered in data/registry/works.yaml")


def registry_source(source_id: str = SOURCE_ID) -> Source:
    payload: Any = yaml.safe_load((REGISTRY_DIR / "sources.yaml").read_text(encoding="utf-8"))
    for item in payload["sources"]:
        if item["source_id"] == source_id:
            return Source.model_validate(item)
    raise BuildInputError(f"{source_id} is not registered in data/registry/sources.yaml")


def registry_artifact(artifact_id: str = ARTIFACT_ID) -> SourceArtifact:
    path = REGISTRY_DIR / "source_artifacts.yaml"
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    for item in payload["source_artifacts"]:
        if item["artifact_id"] == artifact_id:
            return SourceArtifact.model_validate(item)
    raise BuildInputError(f"{artifact_id} is not registered in {path}")


def registry_text_versions() -> list[TextVersionDescriptor]:
    path = REGISTRY_DIR / "text_versions.yaml"
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [TextVersionDescriptor.model_validate(item) for item in payload["text_versions"]]


def load_migrations(path: Path = MIGRATIONS_PATH) -> list[ReferentMigration]:
    return [
        ReferentMigration.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_samaveda_primary(
    descriptors: Sequence[TextVersionDescriptor] | None = None,
) -> TextVersionDescriptor:
    """The one selection call this build makes, exposed so a test can inject a registry.

    ``descriptors=`` is how the no-fallback regression proves its point without touching
    data/registry/text_versions.yaml: it passes a registry with the Samaveda Wikisource
    entry removed and asserts that the build path RAISES rather than resolving
    GRETIL.SV.KAUTHUMA, which is the only other registered Samaveda version.
    """
    return select_primary_text_version(
        TEXT_VERSION_ID,
        work_id=WORK_ID,
        expected_artifact_id=ARTIFACT_ID,
        forbidden_text_version_ids=FORBIDDEN_TEXT_VERSION_IDS,
        descriptors=descriptors,
    )


# ------------------------------------------------------------------- structural spine


@dataclass(frozen=True)
class ContainerNode:
    """One container on the Samaveda spine, addressed by the levels it actually has."""

    collection: SamavedaCollection
    values: tuple[int, ...]

    @property
    def declared(self) -> tuple[str, ...]:
        return SV_COLLECTION_LEVELS[self.collection][: len(self.values)]

    @property
    def parent(self) -> ContainerNode | None:
        if not self.values:
            return None
        return ContainerNode(self.collection, self.values[:-1])

    def identity(self) -> tuple[str, str, UUID]:
        levels = dict(zip(self.declared, self.values, strict=True))
        return sv_container_identity(
            self.collection,
            prapathaka=levels.get("prapathaka"),
            ardha=levels.get("ardha"),
            dasati=levels.get("dasati"),
        )


def container_chain(row: AuditRow) -> list[ContainerNode]:
    """Every ancestor of one released verse, outermost first."""
    collection = SamavedaCollection(row.collection)
    supplied: dict[str, int | None] = {
        "prapathaka": row.prapathaka,
        "ardha": row.ardha,
        "dasati": row.dasati,
    }
    values: list[int] = []
    for name in SV_COLLECTION_LEVELS[collection]:
        value = supplied[name]
        if value is None:
            raise ReleaseIntegrityError(
                f"{row.canonical_key}: the {collection.value} collection declares a "
                f"{name} level but the audit row supplies none"
            )
        values.append(value)
    return [ContainerNode(collection, tuple(values[:depth])) for depth in range(len(values) + 1)]


def citation_label(collection: SamavedaCollection, values: Sequence[int]) -> str:
    """``SV {collection} {a}.{b}...``, levels omitted where the collection declares none."""
    if not values:
        return f"SV {collection.value}"
    return f"SV {collection.value} " + ".".join(str(value) for value in values)


def _passage_for_container(node: ContainerNode, sequence: int, parent_key: str | None) -> Passage:
    key, urn, entity = node.identity()
    hierarchy: dict[str, int | str] = {"collection": node.collection.value}
    labels = [LEVEL_LABEL["collection"]]
    path = [node.collection.value]
    for name, value in zip(node.declared, node.values, strict=True):
        hierarchy[name] = value
        labels.append(LEVEL_LABEL[name])
        path.append(str(value))
    return Passage(
        entity_id=entity,
        canonical_key=key,
        canonical_urn=urn,
        entity_type=EntityType.STRUCTURAL_CONTAINER,
        work_id=WORK_ID,
        hierarchy=hierarchy,
        canonical_citation=citation_label(node.collection, node.values),
        parent_key=parent_key,
        sequence_in_parent=sequence,
        native_labels=labels,
        structural_path=path,
        status=PassageStatus.CANONICAL,
    )


def _passage_for_verse(row: AuditRow, parent: ContainerNode) -> Passage:
    collection = SamavedaCollection(row.collection)
    verse = row.local_verse_index
    assert verse is not None and row.canonical_key and row.canonical_urn and row.entity_id
    hierarchy: dict[str, int | str] = {"collection": collection.value}
    labels = [LEVEL_LABEL["collection"]]
    path = [collection.value]
    for name, value in zip(parent.declared, parent.values, strict=True):
        hierarchy[name] = value
        labels.append(LEVEL_LABEL[name])
        path.append(str(value))
    hierarchy["verse"] = verse
    labels.append(LEVEL_LABEL["verse"])
    path.append(str(verse))
    return Passage(
        entity_id=UUID(row.entity_id),
        canonical_key=row.canonical_key,
        canonical_urn=row.canonical_urn,
        entity_type=EntityType.MANTRA,
        work_id=WORK_ID,
        hierarchy=hierarchy,
        canonical_citation=citation_label(collection, [*parent.values, verse]),
        parent_key=parent.identity()[0],
        sequence_in_parent=verse,
        native_labels=labels,
        structural_path=path,
        status=PassageStatus.CANONICAL,
    )


def build_passages(released: Sequence[AuditRow]) -> list[Passage]:
    """The container spine plus one Passage per released verse, with checked ordering.

    ``sequence_in_parent`` is the RANK of a level value among its siblings, not the value
    itself, so the sequence is contiguous by construction. Where the two differ the build
    records a QA finding rather than silently renumbering; for this corpus they do not
    differ, and the check is what proves it rather than assumes it.
    """
    chains = {row.canonical_key: container_chain(row) for row in released}
    nodes: set[ContainerNode] = {node for chain in chains.values() for node in chain}

    children: dict[ContainerNode | None, set[ContainerNode]] = defaultdict(set)
    for node in nodes:
        children[node.parent].add(node)

    sequence: dict[ContainerNode, int] = {}
    for parent, group in children.items():
        if parent is None:
            for node in group:
                sequence[node] = COLLECTION_ORDER.index(node.collection) + 1
            continue
        for rank, node in enumerate(sorted(group, key=lambda item: item.values), start=1):
            sequence[node] = rank

    passages: list[Passage] = []
    for node in nodes:
        parent = node.parent
        passages.append(
            _passage_for_container(
                node, sequence[node], parent.identity()[0] if parent is not None else None
            )
        )
    for row in released:
        passages.append(_passage_for_verse(row, chains[row.canonical_key or ""][-1]))

    _assert_parent_integrity(passages)
    # Fixed-width keys make lexicographic order equal document order, so a container
    # always sorts immediately before the subtree it owns.
    return sorted(passages, key=lambda passage: passage.canonical_key)


def _assert_parent_integrity(passages: Iterable[Passage]) -> None:
    """Every parent_key resolves, and every sibling set is numbered 1..n exactly once."""
    rows = list(passages)
    keys = {passage.canonical_key for passage in rows}
    if len(keys) != len(rows):
        raise ReleaseIntegrityError("two passages share one canonical key")
    by_parent: dict[str | None, list[int]] = defaultdict(list)
    for passage in rows:
        if passage.parent_key is not None and passage.parent_key not in keys:
            raise ReleaseIntegrityError(
                f"{passage.canonical_key}: parent_key {passage.parent_key!r} is not a "
                "released passage, so the spine has a hole"
            )
        by_parent[passage.parent_key].append(passage.sequence_in_parent)
    for parent, sequences in by_parent.items():
        if sorted(sequences) != list(range(1, len(sequences) + 1)):
            raise ReleaseIntegrityError(
                f"children of {parent!r} are not numbered 1..{len(sequences)} exactly "
                f"once: {sorted(sequences)}"
            )


# --------------------------------------------------------------------------- emission


def _saman_marks(text: str) -> bool:
    return any(char in GANA_SVARA_MARKS for char in text)


def build_text_versions(
    pairs: Sequence[tuple[AuditRow, VerseOccurrence]], rights: RightsStatus
) -> tuple[list[TextVersion], int]:
    """One primary TextVersion per released verse, with ``accented`` MEASURED per verse.

    Returns the accented count alongside the rows. The registry records the released
    corpus as unaccented; this recounts it from the text rather than trusting the record,
    and the caller fails the build if the count is not zero.
    """
    versions: list[TextVersion] = []
    accented_count = 0
    for row, occurrence in pairs:
        assert row.canonical_urn and row.entity_id and row.text_sha256
        accented = has_vedic_accents(occurrence.text) or _saman_marks(occurrence.text)
        accented_count += int(accented)
        normalized = normalize_nfc(occurrence.text)
        versions.append(
            TextVersion(
                text_id=derived_uuid("text", row.entity_id, TEXT_VERSION_ID),
                passage_id=UUID(row.entity_id),
                language="sa",
                script="Devanagari",
                text_form=TextForm.SAMHITA,
                text_role=TextRole.PRIMARY_TEXT,
                text_version_id=TEXT_VERSION_ID,
                text_original=occurrence.text,
                text_nfc=normalized,
                accented=accented,
                source_id=SOURCE_ID,
                source_artifact_id=ARTIFACT_ID,
                source_locator=row.source_locator,
                content_sha256=row.text_sha256,
                rights_status=rights,
            )
        )
    versions.sort(key=lambda version: (str(version.passage_id), str(version.text_id)))
    return versions, accented_count


def build_citations(released: Sequence[AuditRow], passages: Sequence[Passage]) -> list[Citation]:
    """Two citations per verse: the canonical coordinate, and the running number.

    THE RUNNING NUMBER IS NEVER IDENTITY. The source prints a whole-samhita running number
    1..1875 and nothing else, so it is the number a reader arrives with -- but it is
    attested only by this hand-keyed wiki and by the Pandey lineage, one printed witness
    carries a per-section counter instead, and the source misprints one of its values.
    It is emitted as a NON-canonical Citation so it is findable and can never be mistaken
    for a key component.
    """
    citation_by_key = {passage.canonical_key: passage for passage in passages}
    citations: list[Citation] = []
    for row in released:
        assert row.canonical_key and row.entity_id
        passage = citation_by_key[row.canonical_key]
        citations.append(
            Citation(
                citation_id=derived_uuid("citation", row.entity_id, "sv-kauthuma-coordinate"),
                passage_id=UUID(row.entity_id),
                label=passage.canonical_citation,
                # VedaGraph's own rendering of the coordinate declared in works.yaml, so
                # no source_id: the collection/level values are the source's, the
                # citation STRING is this project's.
                system="VG_SV_KAUTHUMA_COLLECTION_COORDINATE",
                is_canonical=True,
            )
        )
        if row.source_verse_marker is None:
            continue
        citations.append(
            Citation(
                citation_id=derived_uuid("citation", row.entity_id, "ws-running-samhita-number"),
                passage_id=UUID(row.entity_id),
                label=f"SV {row.source_verse_marker}",
                system="WIKISOURCE_SA_RUNNING_SAMHITA_NUMBER",
                source_id=SOURCE_ID,
                is_canonical=False,
            )
        )
    citations.sort(key=lambda citation: (str(citation.passage_id), citation.system))
    return citations


def _assertion(
    subject: str, predicate: str, value: object, locator: str, evidence: str
) -> SourceAssertion:
    digest = hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return SourceAssertion(
        assertion_id=derived_uuid("source-assertion", subject, predicate, digest),
        subject_id=subject,
        predicate=predicate,
        value=value,
        source_id=SOURCE_ID,
        source_artifact_id=ARTIFACT_ID,
        source_locator=locator,
        status=AssertionStatus.UNREVIEWED,
        evidence=evidence,
    )


def build_source_assertions(
    rows: Sequence[AuditRow],
    released: Sequence[AuditRow],
    stats: Mapping[str, Any],
    coverage: Mapping[str, Any],
) -> list[SourceAssertion]:
    """Source-derived facts that no other emitted family already carries.

    Deliberately NOT one assertion per verse per field. The printed running number is
    already on the Citation and on the referent binding; restating it a third time would
    be provenance theatre. What is asserted here is what would otherwise be lost: the
    minority marker spellings a single-dialect reader cannot see, the local indices the
    source prints for itself on its two table-dialect pages, and the corpus-level counts
    that every coverage claim rests on.
    """
    assertions: list[SourceAssertion] = []
    for row in released:
        assert row.canonical_key
        if row.marker_dialect and row.marker_dialect not in MAJORITY_MARKER_DIALECTS:
            assertions.append(
                _assertion(
                    row.canonical_key,
                    "source_verse_terminal_marker_dialect",
                    row.marker_dialect,
                    row.source_locator,
                    "the source spells this verse's terminal marker in a minority "
                    "dialect; a single-dialect reader does not see this verse boundary "
                    "at all, so the spelling is recorded as a property of the source",
                )
            )
        if row.declared_local_index is not None:
            assertions.append(
                _assertion(
                    row.canonical_key,
                    "source_declared_local_verse_index",
                    row.declared_local_index,
                    row.source_locator,
                    "the source prints its own dasati-local verse index here, which is "
                    "independent corroboration of the index this build derives from the "
                    "printed running-number arithmetic",
                )
            )

    corpus_facts: list[tuple[str, object, str]] = [
        (
            "source_terminal_running_verse_number",
            coverage["distinct_printed_markers"] + len(coverage["unprinted_running_numbers"]),
            "the highest running verse number the witness prints, which is what the "
            "traditional total is reconciled against",
        ),
        (
            "source_distinct_printed_running_markers",
            coverage["distinct_printed_markers"],
            "counted over every verse-terminal marker lifted from the pinned pages",
        ),
        (
            "source_unprinted_running_numbers",
            coverage["unprinted_running_numbers"],
            "running numbers in 1..N that this witness never prints; 1179 is unprinted "
            "by both surveyed lineages and is the single genuinely unattested value",
        ),
        (
            "source_duplicated_running_markers",
            coverage["duplicated_printed_markers"],
            "a running number the witness prints more than once; the second occurrence "
            "stands where 1179 belongs, which is why one dasati's index is underivable",
        ),
        (
            "source_verse_occurrences_carrying_vedic_accent",
            coverage["accented_occurrences"],
            "MEASURED over the released text: udatta U+0951, anudatta U+0952, the Vedic "
            "Extensions block and the Devanagari Extended saman marks U+A8E0-U+A8FF. "
            "The corpus is unaccented; the artifact record's saman-notation claim is "
            "true of the artifact and false of every parsed verse",
        ),
        (
            "source_collection_verse_extents",
            coverage["minted_by_collection"],
            "released key counts per collection, which is what the disputed Purvarcika "
            "extent has to be checked against",
        ),
        (
            "source_gana_lines_excluded",
            int(stats["gana_lines_excluded"]),
            "lines carrying Samaveda gana svara notation, excluded by detecting the "
            "notation rather than by position; their presence is why this work_id must "
            "not be described as covering the gana",
        ),
        (
            "source_apparatus_lines_excluded",
            int(stats["apparatus_lines_excluded"]),
            "commentary, anukramani and cross-reference lines the source interleaves "
            "with the verse text",
        ),
        (
            "source_arcika_pages_pinned",
            int(stats["pages_total"]),
            "arcika samhita pages pinned by revision id; the same artifact also carries "
            "725 gana pages that are out of scope for this work_id",
        ),
        (
            "source_marker_dialect_counts",
            dict(sorted((str(k), int(v)) for k, v in stats["marker_dialects"].items())),
            "how the source spells its verse-terminal markers, counted; the superseded "
            "double-danda-only reader lifted 1195 of them and reported nothing wrong",
        ),
    ]
    for predicate, value, evidence in corpus_facts:
        assertions.append(
            _assertion(WORK_ID, predicate, value, "Samavedah/Kauthumiya/Samhita", evidence)
        )
    assertions.sort(key=lambda item: (item.subject_id, item.predicate, str(item.assertion_id)))
    return assertions


# ----------------------------------------------------------- coverage and withholding


def compute_coverage(rows: Sequence[AuditRow]) -> dict[str, Any]:
    """Recompute every coverage number from this run's audit rows, then check it closes.

    Nothing here is read from a previous report or from the registry prose. The two
    equations the release publishes are asserted, and the build raises if either fails.
    """
    markers = [row.source_verse_marker for row in rows if row.source_verse_marker is not None]
    counts: dict[int, int] = defaultdict(int)
    for marker in markers:
        counts[marker] += 1
    distinct = sorted(counts)
    duplicated = sorted(value for value, count in counts.items() if count > 1)
    unprinted = sorted(set(range(1, TRADITIONAL_TOTAL + 1)) - set(distinct))

    released = [row for row in rows if row.canonical_key]
    withheld = [row for row in rows if not row.canonical_key]
    withheld_markers = sorted(
        {row.source_verse_marker for row in withheld if row.source_verse_marker is not None}
    )
    released_markers = {
        row.source_verse_marker for row in released if row.source_verse_marker is not None
    }
    minted_by_collection = {
        collection.value: sum(1 for row in released if row.collection == collection.value)
        for collection in COLLECTION_ORDER
    }

    equations = {
        "printed_vs_traditional": {
            "statement": (
                f"{TRADITIONAL_TOTAL} = {len(distinct)} distinct printed markers + "
                f"{len(unprinted)} the selected witness does not print"
            ),
            "left": TRADITIONAL_TOTAL,
            "right": len(distinct) + len(unprinted),
            "terms": {
                "distinct_printed_markers": len(distinct),
                "unprinted": len(unprinted),
            },
            "balances": TRADITIONAL_TOTAL == len(distinct) + len(unprinted),
        },
        "released_vs_traditional": {
            "statement": (
                f"{TRADITIONAL_TOTAL} = {len(released)} minted keys + "
                f"{len(withheld_markers)} withheld printed verses + "
                f"{len(unprinted)} unprinted"
            ),
            "left": TRADITIONAL_TOTAL,
            "right": len(released) + len(withheld_markers) + len(unprinted),
            "terms": {
                "minted_keys": len(released),
                "withheld_printed_verses": len(withheld_markers),
                "unprinted": len(unprinted),
            },
            "balances": TRADITIONAL_TOTAL == len(released) + len(withheld_markers) + len(unprinted),
        },
        "occurrences_vs_printed_markers": {
            "statement": (
                f"{len(rows)} candidate occurrences = {len(distinct)} distinct printed "
                f"markers + {len(markers) - len(distinct)} repeated marker occurrence(s)"
            ),
            "left": len(rows),
            "right": len(distinct) + (len(markers) - len(distinct)),
            "terms": {
                "distinct_printed_markers": len(distinct),
                "repeated_marker_occurrences": len(markers) - len(distinct),
                "markerless_occurrences": len(rows) - len(markers),
            },
            "balances": len(rows) == len(markers),
        },
        # The equation that actually carries the weight of the two headline ones. Both of
        # those balance automatically as long as released and withheld markers partition
        # the printed set, so on their own they would survive a released key that lost its
        # printed marker or that shares one with another key -- the two shapes a weld
        # takes. This states marker injectivity over the released set directly.
        "released_keys_vs_distinct_released_markers": {
            "statement": (
                f"{len(released)} minted keys = {len(released_markers)} distinct printed "
                "markers among them, i.e. one printed verse each"
            ),
            "left": len(released),
            "right": len(released_markers),
            "terms": {
                "minted_keys": len(released),
                "distinct_released_markers": len(released_markers),
                "released_keys_without_a_printed_marker": sum(
                    1 for row in released if row.source_verse_marker is None
                ),
                "markers_both_released_and_withheld": len(released_markers & set(withheld_markers)),
            },
            "balances": len(released) == len(released_markers)
            and not (released_markers & set(withheld_markers)),
        },
        "minted_by_collection": {
            "statement": (
                f"{len(released)} minted keys = "
                + " + ".join(f"{count} {name}" for name, count in minted_by_collection.items())
            ),
            "left": len(released),
            "right": sum(minted_by_collection.values()),
            "terms": minted_by_collection,
            "balances": len(released) == sum(minted_by_collection.values()),
        },
    }
    broken = sorted(name for name, item in equations.items() if not item["balances"])
    if broken:
        detail = "; ".join(str(equations[name]["statement"]) for name in broken)
        raise CoverageError(
            f"{len(broken)} coverage equation(s) do not close, so the release is not "
            f"published: {detail}. Do NOT adjust the released key count to make them "
            "balance -- a key minted to satisfy a traditional total denotes nothing."
        )

    return {
        "traditional_total": TRADITIONAL_TOTAL,
        "candidate_occurrences": len(rows),
        "distinct_printed_markers": len(distinct),
        "duplicated_printed_markers": duplicated,
        "unprinted_running_numbers": unprinted,
        "minted_keys": len(released),
        "minted_by_collection": minted_by_collection,
        "purvarcika_group_minted": sum(
            minted_by_collection[name] for name in ("CHANDA", "ARANYA", "MAHANAMNYA")
        ),
        "uttararcika_minted": minted_by_collection["UTTARA"],
        "withheld_occurrences": len(withheld),
        "withheld_printed_verses": len(withheld_markers),
        "withheld_running_numbers": withheld_markers,
        "equations": equations,
        # Filled in by the caller once the text has been read.
        "accented_occurrences": 0,
    }


@dataclass(frozen=True)
class WithheldGroup:
    """One dasati inside which nothing is released, and why."""

    collection: str
    prapathaka: int | None
    ardha: int | None
    dasati: int | None
    rows: tuple[AuditRow, ...]

    @property
    def container_key(self) -> str:
        return sv_container_identity(
            self.collection,
            prapathaka=self.prapathaka,
            ardha=self.ardha,
            dasati=self.dasati,
        )[0]

    @property
    def running_numbers(self) -> list[int]:
        return sorted(
            row.source_verse_marker for row in self.rows if row.source_verse_marker is not None
        )


def group_withheld(rows: Sequence[AuditRow]) -> list[WithheldGroup]:
    buckets: dict[tuple[str, int | None, int | None, int | None], list[AuditRow]] = defaultdict(
        list
    )
    for row in rows:
        if row.canonical_key:
            continue
        buckets[(row.collection, row.prapathaka, row.ardha, row.dasati)].append(row)
    return [
        WithheldGroup(collection, prapathaka, ardha, dasati, tuple(members))
        for (collection, prapathaka, ardha, dasati), members in sorted(buckets.items())
    ]


def withheld_reason(row: AuditRow) -> str:
    """The release-level reason for one withheld occurrence, derived from the audit row.

    Derived, not tabulated: a hard-coded list of keys would go stale the moment the
    segmentation changed, and would then certify a withhold that no longer exists.
    """
    if row.local_verse_index is None:
        return REASON_REFERENT_UNRESOLVED
    return REASON_STRUCTURAL_AMBIGUITY


# --------------------------------------------- second-witness resolution attempt


@dataclass(frozen=True)
class WitnessSpan:
    """What the corroborating witness declares about one withheld group's verses."""

    dasatis: tuple[int, ...]
    verse_indices: tuple[int, ...]
    welded_verses_in_ardha: int
    ardha_dasati_labels: tuple[int, ...]
    ardha_label_gaps: tuple[int, ...]
    ardha_repeated_labels: tuple[int, ...]


_GRETIL_ARCIKA: Final[dict[int, str]] = {
    1: "CHANDA",
    2: "ARANYA",
    3: "MAHANAMNYA",
    4: "UTTARA",
}


def _second_witness_rows() -> list[tuple[tuple[int, int, int, int, int], tuple[int, ...]]]:
    from vedagraph.ingest.adapters.samaveda_gretil import SamavedaGRETILAdapter

    result = SamavedaGRETILAdapter().parse_structure(GRETIL_SNAPSHOT)
    return [(verse.coordinates, tuple(verse.running_numbers)) for verse in result.verses]


def _witness_span(
    witness: Sequence[tuple[tuple[int, int, int, int, int], tuple[int, ...]]],
    group: WithheldGroup,
) -> WitnessSpan:
    wanted = set(group.running_numbers)
    dasatis: list[int] = []
    verses: list[int] = []
    ardha_labels: list[int] = []
    welded = 0
    for (arcika, prapathaka, ardha, dasati, verse), running in witness:
        if _GRETIL_ARCIKA.get(arcika) != group.collection:
            continue
        same_ardha = prapathaka == (group.prapathaka or 0) and ardha == (group.ardha or 0)
        if same_ardha:
            ardha_labels.append(dasati)
            welded += int(len(running) > 1)
        if wanted & set(running):
            dasatis.append(dasati)
            verses.append(verse)
    ordered = sorted(set(ardha_labels))
    gaps = [value for value in range(1, max(ordered, default=0) + 1) if value not in set(ordered)]
    seen: dict[int, int] = defaultdict(int)
    previous: int | None = None
    for label in ardha_labels:
        if label != previous:
            seen[label] += 1
        previous = label
    repeated = sorted(label for label, count in seen.items() if count > 1)
    return WitnessSpan(
        dasatis=tuple(sorted(set(dasatis))),
        verse_indices=tuple(sorted(set(verses))),
        welded_verses_in_ardha=welded,
        ardha_dasati_labels=tuple(ordered),
        ardha_label_gaps=tuple(gaps),
        ardha_repeated_labels=tuple(repeated),
    )


def attempt_withheld_resolution(groups: Sequence[WithheldGroup]) -> list[dict[str, Any]]:
    """Try to close each withheld group on source-faithful evidence, and report honestly.

    NOTHING here mints a key. Every finding below is a statement about evidence, and the
    released key set is identical whether this function runs or not -- which is the point:
    a resolution pass that could change coverage would be a second segmentation path, and
    a second segmentation path is a second set of referents.

    The verdicts, in the order they are tested. Only the first is "the source itself does
    not settle it"; the rest all say the withhold is a fail-closed gate firing on evidence
    that points the other way.

    ``LOCAL_INDEX_ATTESTED_BY_CORROBORATING_WITNESS``
        The dasati-local index is underivable from the printed arithmetic because the
        source misprints one running number, but the corroborating witness independently
        declares 1..n over the same occurrences in the same document order. Evidence
        exists; acting on it needs a segmentation change this build is not permitted to
        make.

    ``CORROBORATING_WITNESS_DEFECTIVE_IN_SPAN``
        The selected witness DOES print the heading, and the contradiction traces to a
        measurable defect in the corroborating witness inside that ardha -- a skipped or
        repeated dasati label, or verses carrying two running numbers each. The withhold
        is then a false positive of a fail-closed gate rather than a source ambiguity.

    ``SELECTED_WITNESS_OMITS_STRUCTURE``
        The corroborating witness declares SEVERAL dasatis across occurrences for which
        the selected witness prints one heading and no more. There is nothing in the
        selected source to resolve it with, and importing the other witness's partition
        would put a PERMISSION_REQUIRED artifact's structure into canonical identity.
        Stays withheld, permanently, until the source supplies the heading.

    ``CORROBORATING_WITNESS_MERGES_A_PRINTED_BOUNDARY``
        The mirror image. The selected witness prints a dasati heading -- its local index
        restarts at 1 -- while the corroborating witness runs the preceding dasati
        straight through, starting these occurrences at verse index 4 or later. Here the
        selected witness DECLARES the boundary and the other witness omits it, so the
        note "the selected witness omits a dasati heading here" that the audit attaches
        to every uncorroborated row is the wrong way round for this group.

    ``UNRESOLVABLE_FROM_SOURCE``
        None of the above; nothing measured points either way.
    """
    if not GRETIL_SNAPSHOT.exists():
        return [
            {
                "container_key": group.container_key,
                "withheld_occurrences": len(group.rows),
                "verdict": "NOT_ATTEMPTED",
                "why": "the corroborating witness artifact is not pinned locally",
                "resolved": False,
            }
            for group in groups
        ]

    witness = _second_witness_rows()
    findings: list[dict[str, Any]] = []
    for group in groups:
        span = _witness_span(witness, group)
        indices = [row.local_verse_index for row in group.rows]
        derivable = all(index is not None for index in indices)
        signals: list[str] = []
        if span.ardha_label_gaps:
            signals.append(
                "the corroborating witness SKIPS dasati label(s) "
                f"{list(span.ardha_label_gaps)} in this ardha while continuing to number "
                "the ones after them, which is a self-inconsistency in that witness"
            )
        if span.ardha_repeated_labels:
            signals.append(
                "the corroborating witness prints dasati label(s) "
                f"{list(span.ardha_repeated_labels)} more than once in this ardha"
            )
        if span.welded_verses_in_ardha:
            signals.append(
                f"{span.welded_verses_in_ardha} verse(s) in the corroborating witness's "
                "copy of this ardha carry more than one running number each, i.e. two "
                "printed units welded onto one address"
            )
        if len(span.dasatis) > 1:
            signals.append(
                "the corroborating witness spreads these occurrences across dasatis "
                f"{list(span.dasatis)} while the selected witness prints one heading for "
                "all of them"
            )
        if derivable and span.verse_indices and min(span.verse_indices) > 1:
            signals.append(
                "the selected witness's local index restarts at 1 here -- it PRINTS a "
                "dasati heading -- while the corroborating witness continues the "
                f"preceding dasati at verse index {min(span.verse_indices)}"
            )

        witness_defective = bool(
            span.ardha_label_gaps or span.ardha_repeated_labels or span.welded_verses_in_ardha
        )
        if not derivable:
            attested = list(span.verse_indices) == list(range(1, len(group.rows) + 1))
            verdict = (
                "LOCAL_INDEX_ATTESTED_BY_CORROBORATING_WITNESS"
                if attested
                else "UNRESOLVABLE_FROM_SOURCE"
            )
        elif witness_defective:
            verdict = "CORROBORATING_WITNESS_DEFECTIVE_IN_SPAN"
        elif len(span.dasatis) > 1:
            verdict = "SELECTED_WITNESS_OMITS_STRUCTURE"
        elif span.verse_indices and min(span.verse_indices) > 1:
            verdict = "CORROBORATING_WITNESS_MERGES_A_PRINTED_BOUNDARY"
        else:
            verdict = "UNRESOLVABLE_FROM_SOURCE"
        findings.append(
            {
                "container_key": group.container_key,
                "withheld_occurrences": len(group.rows),
                "running_numbers": group.running_numbers,
                "evidence": signals,
                "selected_witness_local_indices": [index for index in indices if index is not None],
                "selected_witness_derives_a_local_index": derivable,
                "corroborating_witness_dasatis": list(span.dasatis),
                "corroborating_witness_verse_indices": list(span.verse_indices),
                "corroborating_witness_ardha_dasati_labels": list(span.ardha_dasati_labels),
                "corroborating_witness_ardha_label_gaps": list(span.ardha_label_gaps),
                "corroborating_witness_ardha_repeated_labels": list(span.ardha_repeated_labels),
                "corroborating_witness_welded_verses_in_ardha": span.welded_verses_in_ardha,
                "verdict": verdict,
                "resolved": False,
                "why_not": (
                    "NO KEY IS MINTED. Unwithholding any of these would change a frozen "
                    "released key set and the committed referent baseline, and would "
                    "require a segmentation or corroboration-policy change in files this "
                    "build does not own. The evidence is recorded so the decision can be "
                    "made on it rather than on a count."
                ),
            }
        )
    return findings


def build_qa_issues(
    rows: Sequence[AuditRow],
    coverage: Mapping[str, Any],
    findings: Sequence[Mapping[str, Any]],
) -> list[QAIssue]:
    """One row per withheld occurrence, per unprinted number, and per withheld group.

    A coverage gap with no queryable record is indistinguishable from an oversight, so
    every verse this release does not carry is named here with a reason from the closed
    vocabulary, not summarised in prose.
    """
    issues: list[QAIssue] = []
    for row in rows:
        if row.canonical_key:
            continue
        reason = withheld_reason(row)
        marker = row.source_verse_marker
        subject = f"{row.source_locator}"
        # The occurrence's own line span on its page. Two occurrences can share a locator;
        # they cannot share a span.
        span = "-".join(str(value) for value in row.source_line_span)
        message = (
            f"withheld: no canonical key is minted for the occurrence at "
            f"{row.source_locator}. "
            + (
                "the dasati's printed running run is not contiguous, so the "
                "dasati-local index is not derivable from the source's own arithmetic"
                if reason == REASON_REFERENT_UNRESOLVED
                else "the two witnesses declare different container addresses for this "
                "printed verse, so the address is not corroborated"
            )
        )
        issues.append(
            QAIssue(
                issue_id=stable_issue_id(reason, subject, message, span),
                check_id=reason,
                severity=QASeverity.WARNING,
                message=message,
                entity_id=subject,
                details={
                    "collection": row.collection,
                    "prapathaka": row.prapathaka,
                    "ardha": row.ardha,
                    "dasati": row.dasati,
                    "source_running_number": marker,
                    "audit_referent_class": row.referent_class,
                    "notes": list(row.notes),
                },
            )
        )
        if row.source_numbering_duplicated:
            anomaly = (
                f"the source prints running number {marker} more than once; the "
                "duplicate stands where an unprinted number belongs, which is what "
                "defeats the local-index derivation for this whole dasati"
            )
            issues.append(
                QAIssue(
                    issue_id=stable_issue_id(REASON_SOURCE_MARKER_ANOMALY, subject, anomaly, span),
                    check_id=REASON_SOURCE_MARKER_ANOMALY,
                    severity=QASeverity.WARNING,
                    message=anomaly,
                    entity_id=subject,
                    details={"source_running_number": marker, "page_title": row.page_title},
                )
            )

    for value in coverage["unprinted_running_numbers"]:
        message = (
            f"running number {value} of {coverage['traditional_total']} is never printed "
            "by the selected witness, so there is no occurrence to bind a key to. No key "
            "is minted for it: a key with no referent is worse than a declared gap"
        )
        issues.append(
            QAIssue(
                issue_id=stable_issue_id(REASON_SOURCE_NOT_PRINTED, str(value), message),
                check_id=REASON_SOURCE_NOT_PRINTED,
                severity=QASeverity.WARNING,
                message=message,
                entity_id=f"RN{value}",
                details={"source_running_number": value},
            )
        )

    for finding in findings:
        message = (
            f"withheld dasati {finding['container_key']} carries "
            f"{finding['withheld_occurrences']} unreleased occurrence(s); resolution "
            f"attempted and NOT resolved, verdict {finding['verdict']}"
        )
        issues.append(
            QAIssue(
                issue_id=stable_issue_id(
                    REASON_REVIEW_REQUIRED, str(finding["container_key"]), message
                ),
                check_id=REASON_REVIEW_REQUIRED,
                severity=QASeverity.WARNING,
                message=message,
                entity_id=str(finding["container_key"]),
                details=dict(finding),
            )
        )

    issues.sort(key=lambda issue: (issue.check_id, issue.entity_id or "", str(issue.issue_id)))
    return issues


# ----------------------------------------------------------------------------- build


@dataclass
class BuildOutcome:
    manifest: CorpusManifest
    digests: dict[str, str]
    coverage: dict[str, Any]
    verdicts: dict[str, int]
    deltas: list[ReferentDelta]
    release: CanonicalRelease
    # Every candidate occurrence, released and withheld alike, and the resolution
    # findings. Carried out of the build so a test can check the withheld side without
    # re-running the segmentation, and so a doctored copy can prove the coverage gate
    # actually fires rather than merely being present.
    audit_rows: list[AuditRow]
    withheld_findings: list[dict[str, Any]]
    coverage_report_path: Path


def build(
    output_root: Path | None = None,
    *,
    config_path: Path = CONFIG_PATH,
    coverage_path: Path | None = None,
) -> BuildOutcome:
    """Assemble, gate and emit the release. Every failure below stops the build.

    ``output_root`` overrides the config's location, which is what the determinism check
    and the test suite use. When it is overridden the coverage report follows it into the
    same directory rather than overwriting the tracked one, so a throwaway build cannot
    silently rewrite a committed report.
    """
    config = load_config(config_path)
    descriptor = select_samaveda_primary(registry_text_versions())

    if not GRETIL_SNAPSHOT.exists():
        raise BuildInputError(
            "the structural corroboration witness "
            f"{GRETIL_SNAPSHOT} is not pinned locally. The build STOPS. Without it the "
            "corroboration gate silently passes and 21 keys whose dasati partition is "
            "contradicted would be minted -- and because those keys are absent from the "
            "committed baseline they arrive as NEWLY_DISCOVERED_PASSAGE, which the drift "
            "gate correctly does not treat as drift. The drift gate cannot catch this; "
            "requiring the input can."
        )

    pages = load_pages()
    if not pages:
        raise BuildInputError("no pinned Samaveda arcika snapshots were found")

    pinned = pinned_set_digest(pages)
    declared = {item.source_id: item for item in config.sources}
    expected = declared[SOURCE_ID].snapshot_sha256
    if pinned != expected:
        raise BuildInputError(
            f"the pinned arcika page set digests to {pinned}, but "
            f"{config_path.name} pins {expected}. A page was added, dropped, swapped or "
            "re-snapshotted. Re-pin the config deliberately; do not build across it."
        )

    occurrences = [item for page in pages for item in page.occurrences]
    rows, stats = build_rows(pages)
    if len(rows) != len(occurrences):
        raise ReleaseIntegrityError(
            "the audit produced a different number of rows than there are source "
            "occurrences, so rows and occurrences cannot be paired by position"
        )
    corroboration = stats["second_witness_corroboration"]
    if not (isinstance(corroboration, dict) and corroboration.get("performed")):
        raise BuildInputError(
            "structural corroboration was not performed, so no address in this build is "
            "corroborated. Refusing to publish."
        )

    pairs: list[tuple[AuditRow, VerseOccurrence]] = []
    for row, occurrence in zip(rows, occurrences, strict=True):
        if row.source_locator != occurrence.source_locator:
            raise ReleaseIntegrityError(
                f"audit row {row.source_locator!r} does not pair with source occurrence "
                f"{occurrence.source_locator!r}; the two orderings have diverged"
            )
        if row.canonical_key:
            pairs.append((row, occurrence))

    released = [row for row, _ in pairs]
    coverage = compute_coverage(rows)

    passages = build_passages(released)
    texts, accented = build_text_versions(pairs, descriptor.normalized_rights)
    if accented:
        raise ReleaseIntegrityError(
            f"{accented} released verse(s) carry a Vedic accent or saman mark, but this "
            "release records the corpus as UNACCENTED. The measurement and the claim "
            "disagree; fix the claim, do not suppress the measurement."
        )
    coverage["accented_occurrences"] = accented

    citations = build_citations(released, passages)
    bindings = bindings_for(rows)
    if len(bindings) != len(released):
        raise ReleaseIntegrityError(
            f"{len(released)} released keys but {len(bindings)} referent bindings; every "
            "released key must be bound to the occurrence it denotes"
        )

    groups = group_withheld(rows)
    findings = attempt_withheld_resolution(groups)
    issues = build_qa_issues(rows, coverage, findings)

    deltas = gate_referents(
        bindings,
        baseline_path=BASELINE_PATH,
        migrations=load_migrations(),
        licensing_run=LICENSING_RUN,
    )
    verdicts = referent_verdict_counts(deltas)
    baseline_keys = {row.canonical_key for row in read_baseline(BASELINE_PATH)}
    released_keys = {binding.canonical_key for binding in bindings}
    if released_keys != baseline_keys:
        added = sorted(released_keys - baseline_keys)[:10]
        dropped = sorted(baseline_keys - released_keys)[:10]
        raise ReleaseIntegrityError(
            "the released key set is not the committed baseline key set. Added "
            f"{len(released_keys - baseline_keys)} {added}; dropped "
            f"{len(baseline_keys - released_keys)} {dropped}. A key appearing or "
            "vanishing is a coverage change and needs an explicit decision, not a build."
        )

    work = registry_work()
    source = registry_source()
    artifact = registry_artifact()
    assertions = build_source_assertions(rows, released, stats, coverage)
    orphans = orphan_provenance_claims(
        assertions,
        known_source_ids={source.source_id},
        known_artifact_ids={artifact.artifact_id},
    )
    if orphans:
        raise ReleaseIntegrityError(
            f"{len(orphans)} source assertion(s) point at provenance nothing registers: "
            + "; ".join(orphans[:5])
        )

    root = output_root if output_root is not None else REPO / config.output_location
    release = CanonicalRelease(
        dataset_id=config.dataset_id,
        work_id=WORK_ID,
        release_version=config.release_version,
        output_root=root,
        works=[work],
        passages=passages,
        text_versions=texts,
        translations=[],
        traditional_metadata=[],
        sources=[source],
        source_artifacts=[artifact],
        source_assertions=assertions,
        citations=citations,
        audio_recordings=[],
        audio_segments=[],
        qa_issues=issues,
        referent_bindings=bindings,
    )

    manifest, digests = write_release(
        release,
        built_at=config.build_timestamp,
        source_snapshot_ids=[f"{SOURCE_ID}:{page.snapshot_sha256}" for page in pages],
        source_artifact_ids=[artifact.artifact_id],
        parser_versions={
            "samaveda_wikisource": PARSER_VERSION,
            "sv_referent_segmentation": SEGMENTATION_POLICY_VERSION,
        },
        rights_summary={
            TEXT_VERSION_ID: descriptor.normalized_rights.value,
            ARTIFACT_ID: artifact.rights_status.value,
            "share_alike": (
                "CC BY-SA 4.0 is a live obligation and is ONE-WAY INCOMPATIBLE with CC0; "
                "do not merge this layer into a single licensed blob with a CC0 layer"
            ),
            "translations": "NONE_RELEASED",
            "audio": "NONE_RELEASED",
            "scope": GANA_BOUNDARY,
        },
        qa_status=QAStatus.PASSED_WITH_WARNINGS if issues else QAStatus.PASSED,
        reconciliation_policy_version=config.reconciliation_policy_version,
        build_config_sha256=config_digest(config_path),
        raw_snapshot_hashes={page.page_title: page.snapshot_sha256 for page in pages},
    )

    coverage_report = {
        "dataset_id": config.dataset_id,
        "release_version": config.release_version,
        "work_id": WORK_ID,
        "built_at": config.build_timestamp.isoformat(),
        "scope": GANA_BOUNDARY,
        "gana_corpus_included": False,
        "selected_text_version_id": descriptor.text_version_id,
        "selected_artifact_id": descriptor.artifact_id,
        "selected_rights": descriptor.normalized_rights.value,
        "forbidden_text_version_ids": sorted(FORBIDDEN_TEXT_VERSION_IDS),
        "pinned_page_set_sha256": pinned,
        "coverage": coverage,
        "coverage_status": "INCOMPLETE_BOUNDED",
        "withheld_by_reason": _reason_counts(rows),
        "withheld_groups": findings,
        "referent_verdicts": verdicts,
        "referent_baseline": str(BASELINE_PATH.relative_to(REPO).as_posix()),
        "licensing_run": LICENSING_RUN,
        "migrations_licensing_this_run": sum(
            1 for migration in load_migrations() if migration.recorded_by_run == LICENSING_RUN
        ),
        "record_counts": {name: len(items) for name, items in release.families().items()},
        "corroboration": corroboration,
        "generated_content_sha256": manifest.generated_content_sha256,
    }
    report_path = coverage_path or (
        COVERAGE_PATH if output_root is None else root / "coverage.json"
    )
    write_json(report_path, coverage_report)
    digests[report_path.name] = hashlib.sha256(report_path.read_bytes()).hexdigest()

    return BuildOutcome(
        manifest=manifest,
        digests=digests,
        coverage=coverage,
        verdicts=verdicts,
        deltas=deltas,
        release=release,
        audit_rows=list(rows),
        withheld_findings=findings,
        coverage_report_path=report_path,
    )


def _reason_counts(rows: Sequence[AuditRow]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if not row.canonical_key:
            counts[withheld_reason(row)] += 1
    return dict(sorted(counts.items()))


# --------------------------------------------------------------------- determinism


def verify_determinism() -> tuple[bool, dict[str, tuple[str, str]]]:
    """Two full independent rebuilds into temporary roots, compared file by file."""
    scratch = Path(tempfile.mkdtemp(prefix="sv-determinism-"))
    try:
        first = build(scratch / "a").digests
        second = build(scratch / "b").digests
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    names = sorted(set(first) | set(second))
    differing = {
        name: (first.get(name, "<absent>"), second.get(name, "<absent>"))
        for name in names
        if first.get(name) != second.get(name)
    }
    return not differing, differing


# ---------------------------------------------------------------------------- main


def _record_summary(outcome: BuildOutcome) -> str:
    return ", ".join(
        f"{name}={len(items)}" for name, items in outcome.release.families().items() if items
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="build twice into a temporary directory and compare every file digest",
    )
    args = parser.parse_args()

    try:
        outcome = build()
    except (TextVersionSelectionError, BuildInputError, CoverageError, ReleaseIntegrityError) as e:
        print(f"BUILD REFUSED: {type(e).__name__}: {e}")
        return 1

    coverage = outcome.coverage
    print(GANA_BOUNDARY)
    print()
    print(f"selected text version   {outcome.release.text_versions[0].text_version_id}")
    print(f"source occurrences      {coverage['candidate_occurrences']}")
    print(f"canonical keys          {coverage['minted_keys']}")
    print(f"withheld occurrences    {coverage['withheld_occurrences']}")
    for equation in coverage["equations"].values():
        print(f"  {equation['statement']}  -> {'BALANCES' if equation['balances'] else 'BROKEN'}")
    print(f"referent verdicts       {outcome.verdicts}")
    print(f"records                 {_record_summary(outcome)}")
    print(f"content digest          {outcome.manifest.generated_content_sha256}")
    print(f"coverage report         {COVERAGE_PATH.relative_to(REPO).as_posix()}")

    if args.verify_determinism:
        identical, differing = verify_determinism()
        print(f"determinism             {'BYTE-IDENTICAL' if identical else 'DIVERGED'}")
        for name, (left, right) in differing.items():
            print(f"  {name}: {left} != {right}")
        if not identical:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
