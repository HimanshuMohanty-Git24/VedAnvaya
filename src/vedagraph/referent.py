"""Referent-integrity gate: prove a canonical key still denotes the same occurrence.

A canonical identifier has to be three things at once. Syntactic determinism and
structural validity were already enforced. This module adds the third: **referent
stability**, the property that a key denotes the same textual occurrence across builds.

Why a new gate was needed
=========================

The existing identity checks recompute a UUID from its URN. That is a closed loop: it
proves the URN hashes consistently, and it says nothing at all about what the URN
addresses. ``Passage`` stores no text, so when a segmentation change moved five Samaveda
referents under unchanged UUIDs, every gate in the build reported success. Renumbering is
at least visible in a diff; a referent migration under a stable key is not.

What this module does NOT do
============================

It does not put source text into identity. ``PassageReferentBinding.text_sha256`` is
never an input to ``uuid_for_urn``, canonical keys never mention a source, and replacing a
TextVersion cannot change a key. The fingerprint is compared against the *previous
release's* fingerprint for the *same* key, and a difference is a finding to be adjudicated
rather than an identity input.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

from vedagraph.models import PassageReferentBinding, ReferentMigration
from vedagraph.normalize import ComparisonForm, comparison_form


class ReferentVerdict(StrEnum):
    """How one canonical key's referent compares between two builds."""

    UNCHANGED_REFERENT = "UNCHANGED_REFERENT"
    INTENTIONAL_REFERENT_CORRECTION = "INTENTIONAL_REFERENT_CORRECTION"
    REFERENT_DRIFT = "REFERENT_DRIFT"
    REMOVED_INVALID_PASSAGE = "REMOVED_INVALID_PASSAGE"
    NEWLY_DISCOVERED_PASSAGE = "NEWLY_DISCOVERED_PASSAGE"


class MigrationClass(StrEnum):
    REFERENT_CORRECTED = "REFERENT_CORRECTED"
    PASSAGE_REMOVED_AS_SPURIOUS = "PASSAGE_REMOVED_AS_SPURIOUS"
    PASSAGE_SPLIT = "PASSAGE_SPLIT"
    PASSAGE_MERGED = "PASSAGE_MERGED"
    KEY_REASSIGNED_BEFORE_FREEZE = "KEY_REASSIGNED_BEFORE_FREEZE"
    SOURCE_NUMBERING_CORRECTION = "SOURCE_NUMBERING_CORRECTION"


# Which migration classes license a change to an existing key's referent, and which
# license its disappearance. A drift with no covering migration fails the build.
#
# KEY_REASSIGNED_BEFORE_FREEZE is deliberately NOT a correction class. A reassignment says
# "the old key is retired and a different key appears"; the appearing key is
# NEWLY_DISCOVERED_PASSAGE and needs no licence. Listing it here let the 137 shape-change
# rows of the Samaveda ledger pre-license referent CHANGE on 105 already-released keys and
# removal on 99 of them, permanently, via a committed file -- a standing licence to drift.
_CORRECTION_CLASSES = frozenset(
    {
        MigrationClass.REFERENT_CORRECTED,
        MigrationClass.PASSAGE_SPLIT,
        MigrationClass.PASSAGE_MERGED,
        MigrationClass.SOURCE_NUMBERING_CORRECTION,
    }
)
_REMOVAL_CLASSES = frozenset(
    {
        MigrationClass.PASSAGE_REMOVED_AS_SPURIOUS,
        MigrationClass.KEY_REASSIGNED_BEFORE_FREEZE,
        MigrationClass.PASSAGE_MERGED,
    }
)


def text_fingerprints(text: str) -> tuple[str, str]:
    """``(text_sha256, comparison_sha256)`` for one source text.

    The first digest is over the bytes the source actually spells, so any change to the
    stored text is visible. The second is over a normalization-independent comparison
    surface, so a pure re-encoding, accent-notation change or whitespace change can be
    told apart from a genuine change of which verse a key denotes.
    """
    raw = hashlib.sha256(text.encode("utf-8")).hexdigest()
    folded = comparison_form(text, ComparisonForm.SEARCH_NORMALIZED)
    return raw, hashlib.sha256(folded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReferentFingerprint:
    """The minimum a drift gate needs about one released key.

    The committed baseline stores this rather than a whole
    :class:`~vedagraph.models.PassageReferentBinding`. A full binding carries the parser
    version, snapshot digest, revision id and structural coordinates, all of which are
    reproducible from the build; storing them for every key would make the baseline the
    largest tracked file in the repository while adding nothing the comparison reads.
    """

    canonical_key: str
    source_locator: str
    text_sha256: str
    comparison_sha256: str
    source_verse_marker: int | None = None


def fingerprint_of(binding: PassageReferentBinding) -> ReferentFingerprint:
    return ReferentFingerprint(
        canonical_key=binding.canonical_key,
        source_locator=binding.source_locator,
        text_sha256=binding.text_sha256,
        comparison_sha256=binding.comparison_sha256,
        source_verse_marker=binding.source_verse_marker,
    )


def write_baseline(path: Path, bindings: Iterable[PassageReferentBinding]) -> int:
    rows = sorted(
        (fingerprint_of(binding) for binding in bindings),
        key=lambda row: row.canonical_key,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True))
            handle.write("\n")
    return len(rows)


def read_baseline(path: Path) -> list[ReferentFingerprint]:
    return [
        ReferentFingerprint(**json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@dataclass(frozen=True)
class ReferentDelta:
    canonical_key: str
    verdict: ReferentVerdict
    detail: str
    old_locator: str | None = None
    new_locator: str | None = None
    old_text_sha256: str | None = None
    new_text_sha256: str | None = None
    covering_migration: str | None = None

    @property
    def blocks_release(self) -> bool:
        return self.verdict is ReferentVerdict.REFERENT_DRIFT


def _same_occurrence(before: ReferentFingerprint, after: ReferentFingerprint) -> bool:
    """Whether two fingerprints denote the same source occurrence.

    Text alone is NOT sufficient, and the Samaveda is why. Its Uttararcika repeats
    Purvarcika verses verbatim in gana context, so of 1,844 released keys only 1,651 have
    a distinct ``comparison_sha256``: 192 equivalence classes covering 385 keys share one,
    and 174 of those classes share a byte-identical ``text_sha256`` too. Comparing text
    alone therefore lets two genuinely different occurrences swap keys undetected -- and it
    also let a wholesale rewrite of every ``source_locator`` pass as 1,844 unchanged
    referents, because the locator was stored in the baseline and never read.

    CORRECTED 2026-09-07 by FULL_SV_YV_AV_CANONICAL_INGESTION: this paragraph read
    "1,658 ... 184 ... 369 ... 173". Those figures were measured against a superseded
    build; recounted against the committed baseline the values are 1,651 / 192 / 385 / 174.
    The argument is unaffected and is in fact slightly stronger -- MORE keys share a
    comparison digest than the stale note claimed, so text-only comparison is blinder than
    it said. Fixed because a gate whose rationale cites unreproducible numbers invites the
    next reader to distrust the gate rather than the numbers.

    The locator and the printed verse marker are what actually identify the occurrence, so
    they are compared too.
    """
    return (
        before.comparison_sha256 == after.comparison_sha256
        and before.source_locator == after.source_locator
        and before.source_verse_marker == after.source_verse_marker
    )


def compare_referents(
    previous: Iterable[ReferentFingerprint],
    current: Iterable[ReferentFingerprint],
    migrations: Iterable[ReferentMigration] = (),
    *,
    licensing_run: str | None = None,
) -> list[ReferentDelta]:
    """Classify every canonical key across two builds.

    A key whose source occurrence changes -- its comparison digest, its locator or its
    printed verse marker -- is denoting something else. That is ``REFERENT_DRIFT`` unless a
    recorded migration covers the key, in which case it is an
    ``INTENTIONAL_REFERENT_CORRECTION``. A key that changes only its ``text_sha256`` while
    everything identifying its occurrence holds has been re-encoded, not re-pointed, and is
    reported as unchanged with the re-encoding noted.

    ``licensing_run`` scopes which migrations may license anything. A migration ledger is
    append-only and permanent, so without this a row recorded for one release would license
    the same key to drift in every release afterwards. Pass the run currently being
    validated; omit it only for ad-hoc analysis of a whole ledger.
    """
    old = {row.canonical_key: row for row in previous}
    new = {row.canonical_key: row for row in current}

    covered_change: dict[str, ReferentMigration] = {}
    covered_removal: dict[str, ReferentMigration] = {}
    for migration in migrations:
        if licensing_run is not None and migration.recorded_by_run != licensing_run:
            continue
        try:
            kind = MigrationClass(migration.migration_class)
        except ValueError:
            continue
        old_key, new_key = migration.old_canonical_key, migration.new_canonical_key
        # A correction licenses only the key that KEEPS ITS NAME and changes meaning.
        # When the name also changed, the old key is simply gone and the new key did not
        # exist before, so neither needs a change licence -- the new one is
        # NEWLY_DISCOVERED_PASSAGE. Registering BOTH names here meant the six
        # shape-changing REFERENT_CORRECTED rows of the Samaveda ledger licensed referent
        # change on six already-RELEASED keys, which a test then failed to notice because
        # it compared a build against itself.
        if kind in _CORRECTION_CLASSES:
            if new_key is None or old_key == new_key:
                persisting = old_key or new_key
                if persisting is not None:
                    covered_change.setdefault(persisting, migration)
            elif old_key is not None:
                covered_removal.setdefault(old_key, migration)
        if kind in _REMOVAL_CLASSES and old_key is not None:
            covered_removal.setdefault(old_key, migration)

    deltas: list[ReferentDelta] = []

    for key in sorted(set(old) | set(new)):
        before, after = old.get(key), new.get(key)

        if before is None and after is not None:
            deltas.append(
                ReferentDelta(
                    canonical_key=key,
                    verdict=ReferentVerdict.NEWLY_DISCOVERED_PASSAGE,
                    detail="key is absent from the previous build",
                    new_locator=after.source_locator,
                    new_text_sha256=after.text_sha256,
                )
            )
            continue

        if before is not None and after is None:
            retirement = covered_removal.get(key)
            deltas.append(
                ReferentDelta(
                    canonical_key=key,
                    verdict=(
                        ReferentVerdict.REMOVED_INVALID_PASSAGE
                        if retirement is not None
                        else ReferentVerdict.REFERENT_DRIFT
                    ),
                    detail=(
                        f"key retired under {retirement.migration_class}: {retirement.reason}"
                        if retirement is not None
                        else "key present in the previous build has disappeared with no "
                        "recorded migration retiring it"
                    ),
                    old_locator=before.source_locator,
                    old_text_sha256=before.text_sha256,
                    covering_migration=(
                        retirement.migration_class if retirement is not None else None
                    ),
                )
            )
            continue

        assert before is not None and after is not None
        if _same_occurrence(before, after):
            reencoded = before.text_sha256 != after.text_sha256
            deltas.append(
                ReferentDelta(
                    canonical_key=key,
                    verdict=ReferentVerdict.UNCHANGED_REFERENT,
                    detail=(
                        "same occurrence; stored text re-encoded but the comparison "
                        "surface is identical"
                        if reencoded
                        else "same occurrence"
                    ),
                    old_locator=before.source_locator,
                    new_locator=after.source_locator,
                    old_text_sha256=before.text_sha256,
                    new_text_sha256=after.text_sha256,
                )
            )
            continue

        correction = covered_change.get(key)
        digest_verdict = (
            "unchanged" if before.comparison_sha256 == after.comparison_sha256 else "differs"
        )
        deltas.append(
            ReferentDelta(
                canonical_key=key,
                verdict=(
                    ReferentVerdict.INTENTIONAL_REFERENT_CORRECTION
                    if correction is not None
                    else ReferentVerdict.REFERENT_DRIFT
                ),
                detail=(
                    f"referent changed under {correction.migration_class}: {correction.reason}"
                    if correction is not None
                    else "the source occurrence this key denotes changed and no recorded "
                    f"migration covers it -- comparison digest {digest_verdict}, locator "
                    f"{before.source_locator!r} -> {after.source_locator!r}, marker "
                    f"{before.source_verse_marker} -> {after.source_verse_marker}"
                ),
                old_locator=before.source_locator,
                new_locator=after.source_locator,
                old_text_sha256=before.text_sha256,
                new_text_sha256=after.text_sha256,
                covering_migration=(correction.migration_class if correction is not None else None),
            )
        )

    return deltas


def assert_no_referent_drift(deltas: Iterable[ReferentDelta]) -> None:
    """Raise when any key changed what it denotes without a recorded migration."""
    drifted = [delta for delta in deltas if delta.blocks_release]
    if not drifted:
        return
    lines = "\n".join(
        f"  {delta.canonical_key}: {delta.detail} ({delta.old_locator} -> {delta.new_locator})"
        for delta in drifted[:25]
    )
    raise ReferentDriftError(
        f"{len(drifted)} canonical key(s) changed their textual referent with no "
        f"recorded migration. This is a breaking change even though the UUIDs are "
        f"unchanged.\n{lines}"
    )


class ReferentDriftError(RuntimeError):
    """A canonical key silently started denoting a different textual occurrence."""


def duplicate_referents(
    bindings: Iterable[ReferentFingerprint],
) -> dict[str, list[str]]:
    """Keys that share one source occurrence, and occurrences claimed by several keys.

    Returns a mapping of ``source_locator`` to the canonical keys bound to it, for every
    locator claimed more than once. A one-referent/two-key split shows up here; the
    two-referent/one-key merge cannot, because a merge produces one binding whose
    fingerprint no longer matches either constituent.
    """
    by_locator: dict[str, list[str]] = {}
    for row in bindings:
        by_locator.setdefault(row.source_locator, []).append(row.canonical_key)
    return {locator: sorted(keys) for locator, keys in by_locator.items() if len(keys) > 1}
