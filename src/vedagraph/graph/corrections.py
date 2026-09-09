"""Apply declared upstream source corrections while projecting the corpus into the graph.

One class of correction exists so far, and it is the one that made the graph lose data.

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
    ) -> None:
        self._corrections = corrections
        self._key_by_id = passage_key_by_id
        self._id_by_key = passage_id_by_key
        self.outcomes: dict[str, CorrectionOutcome] = {
            c.correction_id: CorrectionOutcome(c.correction_id) for c in corrections
        }

    def apply(self, record: dict[str, Any]) -> dict[str, Any]:
        """Return ``record``, re-targeted if a correction claims it.

        Returns the input unchanged when nothing matches, which is the case for 17,281 of
        the 17,283 rows.
        """
        if not self._corrections:
            return record
        passage_key = self._key_by_id.get(str(record.get("passage_id", "")))
        if passage_key is None:
            return record
        text = str(record.get("text", ""))

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
