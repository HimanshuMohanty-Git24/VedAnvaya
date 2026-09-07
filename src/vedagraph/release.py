"""Work-agnostic canonical release assembly.

Why this module exists
======================

:mod:`vedagraph.build` is the sealed Rigveda builder. It reads ``config.mandala`` and
``config.selected_suktas`` as plain ints and mints identity through ``rv_*_identity``, so
it cannot build the Samaveda, the Vajasaneyi Samhita or the Atharvaveda, and loosening it
would put the frozen Rigveda corpus at risk for no gain. :class:`WorkBuildConfig` already
declares the shared shape for every other work (ADR-018) but had no builder behind it.
This module is that builder's shared core: the parts every non-Rigveda release needs and
must not each reinvent -- selection, gating, emission, and the cross-work collision audit.

The three gates this module adds, and why each one exists
=========================================================

**Selection fails closed.** ``build.py`` resolves rights with
``rights_by_version.get(text_version_id, RightsStatus.UNKNOWN)``, which fails OPEN: an
unregistered id silently yields UNKNOWN instead of stopping the build. For the Samaveda
that failure mode is concrete rather than theoretical. The Kauthuma adapter stamps
``WIKISOURCE_SA.SV.KAU.ARCIKA_MULA`` on every row; had that id stayed unregistered, the
only registered Samaveda version was ``GRETIL.SV.KAUTHUMA``, whose licence forbids
modification outright. A build that quietly fell back to it would have published a
corpus derived from an artifact that prohibits the derivation.
:func:`select_primary_text_version` therefore raises rather than defaulting, and refuses
a named fallback set by id so the refusal is checkable in a test rather than implied.

**Rights are read, never assumed.** The selected descriptor's ``normalized_rights`` has
to be in an explicitly passed allow-list. A caller that wants to release under a
restrictive licence has to say so at the call site, where a reviewer sees it.

**Referent stability is enforced at release time.** ``assert_no_referent_drift`` exists
in :mod:`vedagraph.referent` but nothing in ``build.py`` calls it, so the gate could pass
in a test while a release shipped drifted keys. :func:`gate_referents` wires it into the
release path itself.

Determinism
===========

Nothing here reads the clock. ``built_at`` comes from the config, every collection is
sorted on a total key before emission, and :func:`write_release` returns the digests it
wrote so a second independent rebuild can be compared byte for byte.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

import orjson
from pydantic import BaseModel

from vedagraph.config.registry import load_text_versions
from vedagraph.models import (
    AudioRecording,
    AudioSegment,
    Citation,
    CorpusManifest,
    Passage,
    PassageReferentBinding,
    QAIssue,
    ReferentMigration,
    Source,
    SourceArtifact,
    SourceAssertion,
    TextVersion,
    TextVersionDescriptor,
    TraditionalMetadataAssertion,
    Translation,
    Work,
)
from vedagraph.models.enums import QAStatus, RightsStatus, TextRole
from vedagraph.referent import (
    ReferentDelta,
    ReferentVerdict,
    assert_no_referent_drift,
    compare_referents,
    duplicate_referents,
    fingerprint_of,
    read_baseline,
)
from vedagraph.storage.jsonl import write_jsonl
from vedagraph.storage.manifest import build_manifest

# Licences under which VedaGraph may publish a segmented, re-keyed derivative of a
# primary text. PERMISSION_REQUIRED, REFERENCE_ONLY and RESEARCH_ONLY are absent
# deliberately: the pipeline itself -- parsing, NFC normalization, structural re-keying,
# JSONL republication -- is modification and publication, so a licence that forbids
# either cannot host a canonical layer no matter how convenient the text is.
REDISTRIBUTABLE_RIGHTS: Final[frozenset[RightsStatus]] = frozenset(
    {
        RightsStatus.PUBLIC_DOMAIN,
        RightsStatus.CC0,
        RightsStatus.CC_BY,
        RightsStatus.CC_BY_SA,
        RightsStatus.PERMISSION_GRANTED,
    }
)


class TextVersionSelectionError(RuntimeError):
    """The primary text layer a release asked for cannot be used, so nothing is built."""


class ReleaseIntegrityError(RuntimeError):
    """A release-blocking invariant failed after the records were assembled."""


def select_primary_text_version(
    text_version_id: str,
    *,
    work_id: str,
    expected_artifact_id: str | None = None,
    forbidden_text_version_ids: Collection[str] = (),
    allowed_rights: Collection[RightsStatus] = REDISTRIBUTABLE_RIGHTS,
    allowed_roles: Collection[TextRole] = (TextRole.PRIMARY_TEXT,),
    descriptors: Sequence[TextVersionDescriptor] | None = None,
) -> TextVersionDescriptor:
    """Resolve the selected primary layer, or refuse to build.

    Every failure below raises. None of them degrades to a default, and in particular
    none of them falls through to another registered version of the same work: silently
    selecting a *different* witness is worse than not building, because the resulting
    corpus looks complete and cites the wrong provenance.

    ``forbidden_text_version_ids`` states the rejected witnesses by name. Rights and role
    checks would already stop most of them, but naming them makes the refusal a property
    a test can assert directly instead of a consequence of two other fields.
    """
    if not text_version_id:
        raise TextVersionSelectionError(
            f"{work_id}: no primary text_version_id was selected. A canonical build "
            "requires an explicitly selected primary layer; there is no default."
        )

    available = list(descriptors) if descriptors is not None else load_text_versions()
    by_id = {descriptor.text_version_id: descriptor for descriptor in available}

    if text_version_id in set(forbidden_text_version_ids):
        raise TextVersionSelectionError(
            f"{work_id}: text version {text_version_id!r} is on this build's forbidden "
            "list and must never become canonical primary text."
        )

    descriptor = by_id.get(text_version_id)
    if descriptor is None:
        siblings = sorted(
            other for other in by_id if other.split(".")[1:2] == text_version_id.split(".")[1:2]
        )
        raise TextVersionSelectionError(
            f"{work_id}: the selected primary text version {text_version_id!r} is not "
            f"registered in data/registry/text_versions.yaml. Registered versions for "
            f"this work: {siblings or 'none'}. The build STOPS here rather than binding "
            "its rows to another registered version, which would attach the wrong "
            "provenance and possibly the wrong licence to the whole corpus."
        )

    if descriptor.text_role not in set(allowed_roles):
        raise TextVersionSelectionError(
            f"{work_id}: {text_version_id!r} has text_role {descriptor.text_role.value}, "
            f"but this build accepts only {sorted(role.value for role in allowed_roles)}. "
            "A layer whose unit boundaries are an editorial judgement rather than a "
            "source declaration must not be relabelled to make the statistics uniform."
        )

    if descriptor.normalized_rights not in set(allowed_rights):
        raise TextVersionSelectionError(
            f"{work_id}: {text_version_id!r} carries rights "
            f"{descriptor.normalized_rights.value}, which does not permit publishing a "
            "segmented derivative. Parsing, re-keying and JSONL republication are "
            "modification and publication, so this layer cannot be canonical primary."
        )

    if expected_artifact_id is not None and descriptor.artifact_id != expected_artifact_id:
        raise TextVersionSelectionError(
            f"{work_id}: {text_version_id!r} resolves to artifact "
            f"{descriptor.artifact_id!r}, but this build pinned "
            f"{expected_artifact_id!r}. Refusing to build against an unpinned artifact."
        )

    return descriptor


def gate_referents(
    bindings: Sequence[PassageReferentBinding],
    *,
    baseline_path: Path,
    migrations: Iterable[ReferentMigration] = (),
    licensing_run: str | None = None,
) -> list[ReferentDelta]:
    """Compare this build's bindings against the committed baseline and refuse drift.

    Also refuses a one-referent/two-key split, which drift comparison alone cannot see:
    a split produces two keys that are each individually unchanged.
    """
    current = [fingerprint_of(binding) for binding in bindings]

    shared = duplicate_referents(current)
    if shared:
        detail = "; ".join(f"{locator} -> {keys}" for locator, keys in sorted(shared.items())[:10])
        raise ReleaseIntegrityError(
            f"{len(shared)} source occurrence(s) are claimed by more than one canonical "
            f"key, so at least one key does not denote a single verse: {detail}"
        )

    if not baseline_path.exists():
        raise ReleaseIntegrityError(
            f"no committed referent baseline at {baseline_path}. A release cannot prove "
            "referent stability against a baseline that does not exist; write one with "
            "the work's audit script before releasing."
        )

    deltas = compare_referents(
        read_baseline(baseline_path),
        current,
        migrations,
        licensing_run=licensing_run,
    )
    assert_no_referent_drift(deltas)
    return deltas


def referent_verdict_counts(deltas: Iterable[ReferentDelta]) -> dict[str, int]:
    counts: dict[str, int] = {verdict.value: 0 for verdict in ReferentVerdict}
    for delta in deltas:
        counts[delta.verdict.value] += 1
    return counts


@dataclass
class CanonicalRelease:
    """One work's canonical record families, kept as distinct layers.

    The families are deliberately not collapsed into a single "records" bag. Each answers
    a different question and carries different rights: a Translation is not a TextVersion
    with another language, and an AudioRecording that is reference-only must never be
    emitted as if the bytes were held.
    """

    dataset_id: str
    work_id: str
    release_version: str
    output_root: Path

    works: list[Work] = field(default_factory=list)
    passages: list[Passage] = field(default_factory=list)
    text_versions: list[TextVersion] = field(default_factory=list)
    translations: list[Translation] = field(default_factory=list)
    traditional_metadata: list[TraditionalMetadataAssertion] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    source_artifacts: list[SourceArtifact] = field(default_factory=list)
    source_assertions: list[SourceAssertion] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    audio_recordings: list[AudioRecording] = field(default_factory=list)
    audio_segments: list[AudioSegment] = field(default_factory=list)
    qa_issues: list[QAIssue] = field(default_factory=list)
    referent_bindings: list[PassageReferentBinding] = field(default_factory=list)

    def families(self) -> dict[str, list[BaseModel]]:
        """Every family in a stable order, including the empty ones.

        Empty families are still written. An absent ``translations.jsonl`` is ambiguous
        between "no translation exists" and "the build forgot"; a zero-length file that
        the manifest counts is not.
        """
        return {
            "works": list(self.works),
            "passages": list(self.passages),
            "text_versions": list(self.text_versions),
            "translations": list(self.translations),
            "traditional_metadata": list(self.traditional_metadata),
            "sources": list(self.sources),
            "source_artifacts": list(self.source_artifacts),
            "source_assertions": list(self.source_assertions),
            "citations": list(self.citations),
            "audio_recordings": list(self.audio_recordings),
            "audio_segments": list(self.audio_segments),
            "qa_issues": list(self.qa_issues),
            "referent_bindings": list(self.referent_bindings),
        }


def _content_digest(paths: Mapping[str, Path]) -> str:
    """One digest over every emitted file, so two rebuilds compare in a single value."""
    accumulator = hashlib.sha256()
    for name in sorted(paths):
        accumulator.update(name.encode("utf-8"))
        accumulator.update(hashlib.sha256(paths[name].read_bytes()).digest())
    return accumulator.hexdigest()


def write_release(
    release: CanonicalRelease,
    *,
    built_at: object,
    source_snapshot_ids: Sequence[str],
    source_artifact_ids: Sequence[str],
    parser_versions: Mapping[str, str],
    rights_summary: Mapping[str, str],
    qa_status: QAStatus,
    reconciliation_policy_version: str,
    build_config_sha256: str | None = None,
    raw_snapshot_hashes: Mapping[str, str] | None = None,
) -> tuple[CorpusManifest, dict[str, str]]:
    """Emit every family plus a manifest, and return the per-file digests.

    ``built_at`` is passed through to the manifest untouched. It is typed loosely because
    the only requirement this function places on it is that the caller, not the clock,
    decided it.
    """
    root = release.output_root
    root.mkdir(parents=True, exist_ok=True)

    written: dict[Path, int] = {}
    paths: dict[str, Path] = {}
    for name, records in release.families().items():
        path = root / f"{name}.jsonl"
        written[path] = write_jsonl(path, records)
        paths[name] = path

    manifest = build_manifest(
        root=root,
        version=release.release_version,
        works=[release.work_id],
        passage_count=len(release.passages),
        source_snapshot_ids=list(source_snapshot_ids),
        generated=written,
        qa_status=qa_status,
        built_at=built_at,  # type: ignore[arg-type]
        source_artifact_ids=list(source_artifact_ids),
        raw_snapshot_hashes=dict(raw_snapshot_hashes or {}),
        build_config_sha256=build_config_sha256,
        parser_versions=dict(parser_versions),
        reconciliation_policy_version=reconciliation_policy_version,
        rights_summary=dict(rights_summary),
        generated_content_sha256=_content_digest(paths),
    )
    manifest_path = root / "manifest.json"
    manifest_path.write_bytes(
        orjson.dumps(
            manifest.model_dump(mode="json", exclude_none=True),
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
        + b"\n"
    )

    digests = {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}
    digests["manifest.json"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return manifest, digests


@dataclass(frozen=True)
class CollisionReport:
    """Cross-work uniqueness findings, one entry per colliding value."""

    canonical_keys: dict[str, list[str]]
    canonical_urns: dict[str, list[str]]
    entity_ids: dict[str, list[str]]

    @property
    def clean(self) -> bool:
        return not (self.canonical_keys or self.canonical_urns or self.entity_ids)

    def as_dict(self) -> dict[str, dict[str, list[str]]]:
        return {
            "canonical_keys": self.canonical_keys,
            "canonical_urns": self.canonical_urns,
            "entity_ids": self.entity_ids,
        }


def audit_cross_work_collisions(
    passages_by_work: Mapping[str, Iterable[Passage]],
) -> CollisionReport:
    """Prove no two works claim one key, URN or UUID.

    UUIDs are checked as well as URNs even though the UUID is a pure function of the URN.
    That is not redundancy: it is the only check that would survive somebody minting an
    id through a path other than ``uuid_for_urn``, which is exactly the kind of shortcut
    a hand-written fixture takes.
    """
    keys: dict[str, list[str]] = {}
    urns: dict[str, list[str]] = {}
    ids: dict[str, list[str]] = {}
    for work_id, passages in sorted(passages_by_work.items()):
        for passage in passages:
            keys.setdefault(passage.canonical_key, []).append(work_id)
            urns.setdefault(passage.canonical_urn, []).append(work_id)
            ids.setdefault(str(passage.entity_id), []).append(work_id)
    return CollisionReport(
        canonical_keys={k: v for k, v in keys.items() if len(v) > 1},
        canonical_urns={k: v for k, v in urns.items() if len(v) > 1},
        entity_ids={k: v for k, v in ids.items() if len(v) > 1},
    )


def orphan_provenance_claims(
    assertions: Iterable[SourceAssertion],
    *,
    known_source_ids: Collection[str],
    known_artifact_ids: Collection[str],
) -> list[str]:
    """Assertions whose provenance points at a source or artifact nothing registers.

    An assertion with an unresolvable ``source_id`` is an orphan claim: it looks
    provenanced and is not.
    """
    sources = set(known_source_ids)
    artifacts = set(known_artifact_ids)
    orphans: list[str] = []
    for assertion in assertions:
        if assertion.source_id not in sources:
            orphans.append(f"{assertion.assertion_id}: unknown source_id {assertion.source_id!r}")
        elif assertion.source_artifact_id and assertion.source_artifact_id not in artifacts:
            orphans.append(
                f"{assertion.assertion_id}: unknown source_artifact_id "
                f"{assertion.source_artifact_id!r}"
            )
        elif not assertion.source_locator:
            orphans.append(f"{assertion.assertion_id}: empty source_locator")
    return sorted(orphans)


def write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON report: sorted keys, LF endings, trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        handle.write("\n")
