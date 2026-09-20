"""Apply declared upstream source corrections while projecting the corpus into the graph.

Two classes of correction exist. The first made the graph lose data; the second made it
publish another verse's translation as this verse's.

CLASS TWO: THE VERSE SPINE (``GAP-TRANSLATION-006``)
=====================================================

A typo is not the only way a source coordinate can be wrong about our corpus. In RV
1.65-1.70 Griffith's page is entirely correct and so is ours -- **the two editions simply do
not count verses the same way.** Those six hymns are in ``dvipada viraj``, a two-pada metre:
our canonical verses are single hemistichs, and Griffith's edition numbers the four-pada
GROUP as one verse. His page prints 5 units against our 10 verses, 6 against our 11.

The ingest bound his unit index straight onto our verse number, so unit 2 -- which renders our
verses 3 and 4 -- shipped as the translation of our verse 2. 25 of the span's 31 rows read
against the wrong Sanskrit on a public page.

**This is not a typographical correction and must not be filed as one.** Nothing about the
source is defective, so ``wrong_passage_key`` would be a false description: the row was never
where the source said it was, because the source never spoke in our coordinates at all. A
spine correction therefore names the HYMN and the spine, and derives each row's target from
it -- one declaration per hymn rather than one per row, because the fact being recorded is a
fact about the hymn.

**Why not fix it in the parser.** The corpus is byte-sealed (see WHY NOT FIX THE CORPUS
below), and a parser that resolved spans would have to rewrite ``translations.jsonl``. The
declaration route reaches the graph without touching a sealed byte, and
:func:`verify_corrections_applied` makes a stale declaration an error rather than decoration.

**What a spine correction does NOT do.** It does not split the unit across the verses it
covers. Griffith's unit 1 for RV 1.65 interleaves verses 1 and 2 -- "ONE-MINDED, wise, they
tracked thee" renders verse 2's ``sajosa dhirah padair anu gmann`` while "like a thief lurking
in dark cave" renders verse 1's ``pasva na tayum guha catantam`` -- because the two verses are
one syntactic period. Splitting at his line break would attach half of verse 2's sense to
verse 1. So the unit is anchored on the FIRST verse of its span and declares the span it
covers; the second verse keeps no translation, which is the honest state and is counted in
``GAP-TRANSLATION-004``.

CLASS ONE: THE MIS-PRINTED VERSE NUMBER
=======================================

The one that made the graph lose data.

Griffith's Rigveda translation was parsed from Wikisource, and two of those pages print a
verse number twice. The parser recorded what the page said, so two different verses of one
hymn were both filed under one mantra. ``translation_id`` is derived from
``(passage_id, artifact, revision)``, so both rows derived the *same* id, and the loader's
``MERGE (t:Translation {translation_id: ...})`` quietly folded the second onto the first.
The graph held 17,281 Translation nodes where the corpus holds 17,283 rows, and the two
that vanished did so without any error.

The fix is not to renumber the corpus. ``data/registry/upstream_corrections.yaml`` declares
which row belongs where and why the source proves it; this module reads that file and
re-targets the row on the way past. Three properties make that safe:

* **The corpus is untouched.** Its bytes still say what Wikisource said, which keeps the
  provenance chain honest and keeps the sealed semantic freeze intact.
* **A correction is identified by content, not by id.** The colliding ``translation_id``
  cannot distinguish the two rows -- that it cannot is the defect -- so a correction names
  a text prefix, and applying it to the wrong row is impossible.
* **A declared correction that matches nothing is an error.** If the corpus changes such
  that a correction no longer applies, :func:`verify_corrections_applied` fails rather
  than letting a stale entry sit in the registry looking effective. A recorded correction
  that was never actually written to a row is the exact failure mode this project has hit
  before.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any

import yaml

from vedagraph.identity import uuid_for_urn
from vedagraph.models.enums import AlignmentLevel, TranslationAlignment

REGISTRY_PATH = pathlib.Path("data") / "registry" / "upstream_corrections.yaml"


@dataclass(frozen=True)
class VerseNumberCorrection:
    """One translation row that belongs to a different mantra than its number said."""

    correction_id: str
    source_artifact_id: str
    source_revision_id: int
    wrong_passage_key: str
    correct_passage_key: str
    text_prefix: str
    reason: str

    def matches(self, passage_key: str, text: str) -> bool:
        return passage_key == self.wrong_passage_key and text.startswith(self.text_prefix)


#: Spines a source edition can use relative to ours. Declared, because "the counts differ"
#: is not a spine: RV 9.7 has 8 units against 9 verses and every one of its attachments is
#: correct, since there the merge falls on the last unit. A rule derived from the counts alone
#: would have moved eight correct rows.
PAIRED_DVIPADA = "PAIRED_DVIPADA"


@dataclass(frozen=True)
class VerseSpineCorrection:
    """One hymn whose source edition counts verses differently from ours.

    Hymn-scoped rather than row-scoped: the fact recorded is that this hymn's source numbers
    pairs of our verses as one, which is true of the hymn and derives every row's target.
    """

    correction_id: str
    source_artifact_id: str
    source_revision_id: int
    hymn_key: str
    spine: str
    source_unit_count: int
    canonical_verse_count: int
    reason: str

    def __post_init__(self) -> None:
        if self.spine != PAIRED_DVIPADA:
            raise ValueError(
                f"{self.correction_id}: unknown spine {self.spine!r}. A spine must be "
                "declared here with its span rule, never inferred from a count."
            )
        expected = (self.canonical_verse_count + 1) // 2
        if self.source_unit_count != expected:
            raise ValueError(
                f"{self.correction_id}: {self.spine} requires "
                f"ceil({self.canonical_verse_count}/2) = {expected} source units, "
                f"but {self.source_unit_count} are declared. The declaration and the "
                "span rule must agree or the derived targets are arbitrary."
            )

    def covers(self, unit: int) -> tuple[str, ...]:
        """The canonical verse keys source ``unit`` renders, strongest first.

        Under ``PAIRED_DVIPADA`` unit N covers our verses 2N-1 and 2N, and the final unit of
        an odd-length hymn covers 2N-1 alone. The first entry is the anchor.
        """
        first = 2 * unit - 1
        return tuple(
            f"{self.hymn_key}:V{n:03d}"
            for n in (first, first + 1)
            if n <= self.canonical_verse_count
        )

    def matches(self, passage_key: str, revision_id: int) -> bool:
        """True when this row is one of the hymn's rows, at the declared source revision.

        The unit index is read off the row's CURRENT verse number, because the ingest wrote
        it there -- that it did is the defect, and it is the only place the source coordinate
        survived into the corpus. Pinning the revision is what stops the correction applying
        to a re-fetched page that might number differently.
        """
        if revision_id != self.source_revision_id:
            return False
        prefix = f"{self.hymn_key}:V"
        if not passage_key.startswith(prefix):
            return False
        unit = int(passage_key[len(prefix) :])
        return 1 <= unit <= self.source_unit_count


def load_corrections(project_root: pathlib.Path) -> tuple[VerseNumberCorrection, ...]:
    """Read the correction registry. Absent file means no corrections, not an error."""
    path = project_root / REGISTRY_PATH
    if not path.exists():
        return ()
    with open(path, encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}

    corrections = tuple(
        VerseNumberCorrection(
            correction_id=entry["correction_id"],
            source_artifact_id=entry["source_artifact_id"],
            source_revision_id=int(entry["source_revision_id"]),
            wrong_passage_key=entry["wrong_passage_key"],
            correct_passage_key=entry["correct_passage_key"],
            text_prefix=entry["text_prefix"],
            reason=" ".join(entry["reason"].split()),
        )
        for entry in data.get("translation_verse_number", [])
    )

    ids = [c.correction_id for c in corrections]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate correction_id in the upstream correction registry")
    return corrections


def load_spine_corrections(project_root: pathlib.Path) -> tuple[VerseSpineCorrection, ...]:
    """Read the verse-spine section. Absent file means none declared, not an error."""
    path = project_root / REGISTRY_PATH
    if not path.exists():
        return ()
    with open(path, encoding="utf-8") as handle:
        data: dict[str, Any] = yaml.safe_load(handle) or {}

    corrections = tuple(
        VerseSpineCorrection(
            correction_id=entry["correction_id"],
            source_artifact_id=entry["source_artifact_id"],
            source_revision_id=int(entry["source_revision_id"]),
            hymn_key=entry["hymn_key"],
            spine=entry["spine"],
            source_unit_count=int(entry["source_unit_count"]),
            canonical_verse_count=int(entry["canonical_verse_count"]),
            reason=" ".join(entry["reason"].split()),
        )
        for entry in data.get("translation_verse_spine", [])
    )

    ids = [c.correction_id for c in corrections]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate correction_id in the verse-spine registry")
    hymns = [c.hymn_key for c in corrections]
    if len(hymns) != len(set(hymns)):
        raise ValueError(
            "two spine corrections claim one hymn; a hymn has exactly one source spine"
        )
    return corrections


def corrected_translation_id(passage_id: str, artifact_id: str, revision_id: int) -> str:
    """Re-derive a translation id for a re-targeted row.

    Uses the same derivation the corpus builder uses -- ``urn:vedagraph:translation:``
    over passage, artifact and revision -- so the corrected id is the id the row would
    have had if the source page had printed the right number. It is not a new id scheme
    and not a de-collision suffix: with the passage corrected, the derivation produces a
    distinct value on its own.
    """
    urn = f"urn:vedagraph:translation:{passage_id}:{artifact_id}:{revision_id}"
    return str(uuid_for_urn(urn))


@dataclass
class CorrectionOutcome:
    """What a correction actually did, so the claim can be checked against the rows."""

    correction_id: str
    applied: bool = False
    old_translation_id: str = ""
    new_translation_id: str = ""
    new_passage_key: str = ""


class CorrectionApplier:
    """Applies verse-number corrections to translation rows as they stream past.

    Stateful on purpose: it records what it did, and :func:`verify_corrections_applied`
    reads that record. A correction registry whose entries are never exercised is worse
    than no registry, because it reads as though the data were fixed.
    """

    def __init__(
        self,
        corrections: tuple[VerseNumberCorrection, ...],
        passage_key_by_id: dict[str, str],
        passage_id_by_key: dict[str, str],
        spine_corrections: tuple[VerseSpineCorrection, ...] = (),
    ) -> None:
        self._corrections = corrections
        self._key_by_id = passage_key_by_id
        self._id_by_key = passage_id_by_key
        self._spines = spine_corrections
        declared: tuple[VerseNumberCorrection | VerseSpineCorrection, ...] = (
            *corrections,
            *spine_corrections,
        )
        self.outcomes: dict[str, CorrectionOutcome] = {
            c.correction_id: CorrectionOutcome(c.correction_id) for c in declared
        }
        #: Every row a spine correction re-targeted, keyed by the row's original key. Read by
        #: the migration and by the readback, so neither has to recompute the mapping.
        self.spine_moves: list[dict[str, Any]] = []

    def _apply_spine(
        self, record: dict[str, Any], passage_key: str
    ) -> dict[str, Any] | None:
        """Re-anchor a row whose source edition uses a different verse spine."""
        revision = int(record.get("source_revision_id") or 0)
        for spine in self._spines:
            if not spine.matches(passage_key, revision):
                continue
            unit = int(passage_key.rsplit(":V", 1)[1])
            covers = spine.covers(unit)
            anchor = covers[0]
            anchor_id = self._id_by_key.get(anchor)
            if anchor_id is None:
                raise ValueError(
                    f"{spine.correction_id}: anchor passage {anchor} does not exist in the "
                    "corpus"
                )
            new_id = corrected_translation_id(
                anchor_id, spine.source_artifact_id, spine.source_revision_id
            )
            outcome = self.outcomes[spine.correction_id]
            outcome.applied = True
            outcome.old_translation_id = str(record.get("translation_id", ""))
            outcome.new_translation_id = new_id
            outcome.new_passage_key = anchor
            self.spine_moves.append(
                {
                    "correction_id": spine.correction_id,
                    "source_unit": unit,
                    "from_canonical_key": passage_key,
                    "to_canonical_key": anchor,
                    "covers_canonical_keys": list(covers),
                    "old_translation_id": str(record.get("translation_id", "")),
                    "new_translation_id": new_id,
                    "moved": anchor != passage_key,
                }
            )
            corrected = dict(record)
            corrected["passage_id"] = anchor_id
            corrected["translation_id"] = new_id
            corrected["upstream_correction_id"] = spine.correction_id
            corrected["upstream_correction_reason"] = spine.reason
            corrected["source_unit"] = unit
            corrected["source_verse_spine"] = spine.spine
            corrected["covers_canonical_keys"] = list(covers)
            # The claim on the row has to match what the row covers. A unit spanning two
            # verses is not a mantra-exact alignment, and saying it is was half the defect.
            if len(covers) > 1:
                corrected["alignment_level"] = AlignmentLevel.MANTRA_RANGE.value
                corrected["alignment"] = TranslationAlignment.RANGE_ALIGNMENT.value
            return corrected
        return None

    def apply(self, record: dict[str, Any]) -> dict[str, Any]:
        """Return ``record``, re-targeted if a correction claims it.

        Returns the input unchanged when nothing matches, which is the case for 17,252 of
        the 17,283 rows.
        """
        if not self._corrections and not self._spines:
            return record
        passage_key = self._key_by_id.get(str(record.get("passage_id", "")))
        if passage_key is None:
            return record
        text = str(record.get("text", ""))

        spined = self._apply_spine(record, passage_key)
        if spined is not None:
            return spined

        for correction in self._corrections:
            if not correction.matches(passage_key, text):
                continue
            new_passage_id = self._id_by_key.get(correction.correct_passage_key)
            if new_passage_id is None:
                raise ValueError(
                    f"{correction.correction_id}: target passage "
                    f"{correction.correct_passage_key} does not exist in the corpus"
                )
            new_id = corrected_translation_id(
                new_passage_id, correction.source_artifact_id, correction.source_revision_id
            )
            outcome = self.outcomes[correction.correction_id]
            outcome.applied = True
            outcome.old_translation_id = str(record.get("translation_id", ""))
            outcome.new_translation_id = new_id
            outcome.new_passage_key = correction.correct_passage_key

            corrected = dict(record)
            corrected["passage_id"] = new_passage_id
            corrected["translation_id"] = new_id
            corrected["upstream_correction_id"] = correction.correction_id
            corrected["upstream_correction_reason"] = correction.reason
            return corrected

        return record

    def unapplied(self) -> list[str]:
        return sorted(cid for cid, outcome in self.outcomes.items() if not outcome.applied)


def verify_corrections_applied(applier: CorrectionApplier) -> None:
    """Raise if any declared correction never matched a row.

    Called at the end of a projection pass. The alternative -- letting an unmatched
    correction pass silently -- produces a registry that documents fixes the data does not
    contain, which is indistinguishable from the data being fixed until someone reads the
    rows.
    """
    missing = applier.unapplied()
    if missing:
        raise ValueError(
            "declared upstream corrections matched no corpus row: "
            + ", ".join(missing)
            + ". Either the corpus changed or the correction is wrong; a correction that "
            "does not apply must be removed, not left in place."
        )
