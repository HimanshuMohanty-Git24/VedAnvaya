#!/usr/bin/env python3
"""The one place a staged translation row is given its terminal disposition.

Round 2 produced a decision packet whose headline read "evidence-safe = 1,144" beside a
Gate C report reading "C_PASS = 922", and the two figures were computed over different
populations: 922 counts ``C_PASS`` inside the 1,187 rows that passed Gate B, and 1,144
counts every row the matrix judged safe regardless of which gate had parked it. Neither
figure was wrong and neither was a count of what may be imported, which is why this module
exists: one function assigns one terminal class to one row, and every downstream artifact
-- reconciliation, plan, dry run, executor, readback -- reads it rather than re-deriving
its own.

Three owner decisions are encoded here and nowhere else:

``OWNER_DECISION_C_FORCED_ADDRESSES``
    36 independently verified Yajurvedic forced-address rows are approved. Exactly three
    are withheld by canonical key, listed in :data:`OWNER_WITHHELD_FORCED_ADDRESS_KEYS`.
    The three are named rather than counted, because "withhold the three that failed" and
    "withhold these three" are different instructions the moment a re-run changes which
    rows fail, and the owner gave the second one.

``REUSED_RENDERING_POLICY``
    A Rigvedic rendering reused for a Samavedic or Atharvavedic parallel is importable
    only as ``REUSED_RENDERING``, and never counts as independent English for its target
    corpus. The policy is carried by the import class, so a consumer cannot lose it by
    forgetting to read a flag.

``LATIN_SUBSTITUTION_POLICY``
    Rows declaring ``language='en'`` over a Latin literal are Latin, not English. They are
    importable once the product can name a language, and they never increase English
    coverage. The owner decision names 22 such rows, which is the figure Gate C measured;
    re-reading the pinned source pages found 24. The policy is applied to the measured
    population rather than to the quoted count, because a Latin row left in the English
    layer is the single outcome the decision rules out. See
    ``translation_integration_language.py`` for the two it adds and the evidence.

The range classes deserve their own note, because the staged rows and the graph model
disagree about what a row is. Griffith prints one rendering over two Atharvavedic verses,
and staging wrote that as two rows carrying the same literal. Importing both would create
the "separate fake 1:1 translations" the owner forbade, so 68 rows collapse to 34
``Translation`` nodes on the model M13 already established: the node anchors on the lower
verse and enumerates its whole span in ``covers_canonical_keys``. A row is therefore not a
node, and every count here says which of the two it is counting.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Final

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

STAGING = REPO / "data" / "staging" / "translation"
PACKET = STAGING / "gate_bc"
INTEGRATION = STAGING / "integration"

# --------------------------------------------------------------------------------------
# Owner decisions
# --------------------------------------------------------------------------------------

#: The three Yajurvedic forced-address rows the owner withheld by name. Not "the rows that
#: failed": the owner inspected these three and said no to each for its own reason.
OWNER_WITHHELD_FORCED_ADDRESS_KEYS: Final[dict[str, str]] = {
    "VG:YV:VSM:A20:V085": "ambiguous source glyph S5",
    "VG:YV:VSM:A36:V024": "not independently machine-located",
    "VG:YV:VSM:A21:V045": (
        "address is correct but the literal is an editorial cross-reference, not a "
        "translation of the verse"
    ),
}

#: The language the substituted rows are actually in. ISO 639-1, matching the "en" the rest
#: of the corpus uses, so one field holds both and a client needs no second rule.
LATIN_LANGUAGE_CODE: Final = "la"

OWNER_DECISION_A_RV_SPAN: Final = "CLOSE"
OWNER_DECISION_C_FORCED_ADDRESSES: Final = "MIXED"

# --------------------------------------------------------------------------------------
# Terminal classes
# --------------------------------------------------------------------------------------

IMPORT_CLASSES: Final[tuple[str, ...]] = (
    "IMPORT_SOURCE_EXPLICIT",
    "IMPORT_MANTRA_RANGE",
    "IMPORT_REUSED_RENDERING",
    "IMPORT_VERIFIED_FORCED_ADDRESS",
    "IMPORT_NON_ENGLISH_TRANSLATION",
)

WITHHOLD_CLASSES: Final[tuple[str, ...]] = (
    "WITHHOLD_POLICY_PROBABLE",
    "WITHHOLD_POLICY_UNVERIFIED",
    "WITHHOLD_SOURCE_COORDINATE",
    "WITHHOLD_PROVENANCE",
    "WITHHOLD_FORCED_ADDRESS",
)

REJECT_CLASSES: Final[tuple[str, ...]] = (
    "REJECT_NOT_TRANSLATION",
    "REJECT_WRONG_TARGET",
    "CONFLICT_EXISTING_TRANSLATION",
)

#: Declared for the reconciliation report even at zero. A class that simply does not appear
#: lets a reader infer it was never considered; a class reported as 0 says it was measured.
ALL_CLASSES: Final[tuple[str, ...]] = IMPORT_CLASSES + WITHHOLD_CLASSES + REJECT_CLASSES

#: The import classes whose rows are English translations of their own target. The reused
#: and Latin classes are deliberately absent: both are real translations and neither is
#: independent English for the verse it is attached to.
INDEPENDENT_ENGLISH_CLASSES: Final[frozenset[str]] = frozenset(
    {"IMPORT_SOURCE_EXPLICIT", "IMPORT_MANTRA_RANGE", "IMPORT_VERIFIED_FORCED_ADDRESS"}
)

EXPECTED_ROWS: Final = 2254


class AccountingError(RuntimeError):
    """Raised when the 2,254 rows cannot be accounted for one-for-one."""


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------


def _jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    out = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def load_packet() -> dict[str, Any]:
    """Every row-level Gate B/C artifact, keyed by staged row id.

    Raises rather than dropping a row: a staged row absent from an adjudication table is
    the STOP condition the task names, and it is much easier to see here than as a total
    that is quietly 12 short.
    """
    import gate_bc_common as G

    staged = {r["_staged_row_id"]: r for r in G.load_rows()}
    gate_b = {r["staged_row_id"]: r for r in _jsonl(PACKET / "gate_b_rows.jsonl")}
    gate_c = {r["staged_row_id"]: r for r in _jsonl(PACKET / "gate_c_rows.jsonl")}
    matrix = json.loads((PACKET / "translation_decision_matrix.json").read_text(encoding="utf-8"))
    prior = {r["staged_row_id"]: r for r in matrix["per_row"]}

    ids = sorted(staged)
    for name, table in (("gate_b", gate_b), ("gate_c", gate_c), ("decision_matrix", prior)):
        missing = [i for i in ids if i not in table]
        if missing:
            raise AccountingError(
                f"{len(missing)} staged rows are absent from {name} adjudication: {missing[:8]}"
            )
        extra = [i for i in table if i not in staged]
        if extra:
            raise AccountingError(f"{name} adjudicates {len(extra)} rows that are not staged")
    return {
        "ids": ids,
        "staged": staged,
        "gate_b": gate_b,
        "gate_c": gate_c,
        "prior": prior,
        "prior_matrix": matrix,
    }


# --------------------------------------------------------------------------------------
# Latin detection
# --------------------------------------------------------------------------------------


def language_verdict(gate_c_row: dict[str, Any]) -> str | None:
    """Gate C's own per-row language verdict, read rather than recomputed.

    Gate C measured English function-word density against Latin marker density over each
    literal. Re-deriving it here would let this module and the packet disagree about which
    rows are meant, and the owner decision names a population of 22.
    """
    literal = (gate_c_row.get("evidence") or {}).get("literal_integrity") or {}
    verdict = literal.get("language_verdict")
    if verdict:
        return str(verdict)
    # The artifact carries the verdict only in the withhold reason for this category.
    if gate_c_row.get("gate_c_category") == "C_WITHHOLD_AMBIGUOUS":
        for reason in gate_c_row.get("gate_c_reasons") or []:
            if "reads as LATIN" in reason:
                return "LATIN"
    return None


def latin_row_ids(packet: dict[str, Any]) -> list[str]:
    """Every staged row whose literal is Latin, measured here and not inherited.

    Gate C's verdict is kept alongside for comparison but is not the authority, because it
    under-counted. It flagged 22 rows and the owner decision names 22; re-reading the
    pinned source pages found 24. The two it missed are Atharvaveda 20.136.1 and Rigveda
    10.61.6, both of which were classified ``SAFE_IMPORT_SOURCE_EXPLICIT`` and would have
    been imported as English -- which is the one thing the Latin policy forbids. The
    printed hymn at AV 20.136 is headed "Erotica" and runs 1-16 in Latin; reading it as
    2-16 leaves its first verse in the English layer.

    The import is function-local because ``translation_integration_language`` imports this
    module for its class vocabulary, and the detector is the only thing needed from it.
    """
    from translation_integration_language import score

    return [
        i
        for i in packet["ids"]
        if score(packet["staged"][i]["payload"]["text"])["verdict"] == "LATIN"
    ]


# --------------------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------------------


def classify(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Assign exactly one terminal class to each of the 2,254 staged rows.

    The branch order is the precedence and it is deliberate. A row barred by the central
    importability policy is withheld on that ground even when its coordinate also failed,
    because the policy is the finding an owner would have to overturn to import it.
    """
    latin = set(latin_row_ids(packet))
    out: dict[str, dict[str, Any]] = {}

    for row_id in packet["ids"]:
        staged = packet["staged"][row_id]
        gb = packet["gate_b"][row_id]
        gc = packet["gate_c"][row_id]
        key = staged["canonical_key"]
        veda = staged["veda"]
        b = gb["gate_b_category"]
        c = gc["gate_c_category"]
        confidence = staged["mapping_confidence"]

        owner_dep = "none"
        product_dep = "none"

        # 1. The owner named three rows to withhold. Named, so this is checked first and by
        #    key: it must hold whatever the gates say about them on any later run.
        if key in OWNER_WITHHELD_FORCED_ADDRESS_KEYS:
            reason = OWNER_WITHHELD_FORCED_ADDRESS_KEYS[key]
            final = (
                "REJECT_NOT_TRANSLATION"
                if "cross-reference" in reason
                else "WITHHOLD_FORCED_ADDRESS"
            )
            owner_dep = "OWNER_DECISION_C_FORCED_ADDRESSES"
            note = f"owner-withheld by name: {reason}"

        # 2. The central importability policy.
        elif confidence == "PROBABLE":
            final = "WITHHOLD_POLICY_PROBABLE"
            note = "mapping_confidence is PROBABLE; the central importability policy bars it"
        elif confidence == "UNVERIFIED":
            final = "WITHHOLD_POLICY_UNVERIFIED"
            note = "mapping_confidence is UNVERIFIED; the central importability policy bars it"

        # 3. Gate B structural failures.
        elif b == "B_FAIL_SOURCE_COORDINATE":
            final = "WITHHOLD_SOURCE_COORDINATE"
            note = "the printed locator does not address exactly one canonical target"
        elif b == "B_FAIL_PROVENANCE":
            final = "WITHHOLD_PROVENANCE"
            note = "the bytes read cannot be pinned to an identified source revision"

        # 4. Gate C failures, which outrank every import class below.
        elif c == "C_FAIL_ARCHIVE_EVIDENCE":
            final = "WITHHOLD_PROVENANCE"
            note = "cites an archive capture absent from the artifact's own page proofs"
        elif c == "C_FAIL_UNVERIFIED_FORCED_ADDRESS":
            final = "WITHHOLD_FORCED_ADDRESS"
            owner_dep = "OWNER_DECISION_C_FORCED_ADDRESSES"
            note = "forced address with no independent source-local control"
        elif c == "C_FAIL_SOURCE_GRANULARITY":
            final = "REJECT_NOT_TRANSLATION"
            note = "the literal at the verified address is not a translation of the verse"
        elif c == "C_FAIL_WRONG_TARGET":
            final = "REJECT_WRONG_TARGET"
            note = "adversarially located at a different verse than the one claimed"
        elif c == "C_FAIL_DUPLICATE_GENERATION":
            final = "REJECT_WRONG_TARGET"
            note = "one literal generated onto several targets without a declared span"
        elif c == "C_FAIL_CROSS_CORPUS_CONTAMINATION":
            final = "REJECT_WRONG_TARGET"
            note = "the literal belongs to another corpus and no reuse was declared"

        # 5. Conflict with something already canonical.
        elif gb["evidence"]["target_state"]["state"] != "TARGET_HAS_NO_TRANSLATION":
            final = "CONFLICT_EXISTING_TRANSLATION"
            note = (
                "the target already carries a translation: "
                f"{gb['evidence']['target_state']['state']}"
            )

        # 6. The import classes.
        elif row_id in latin:
            final = "IMPORT_NON_ENGLISH_TRANSLATION"
            owner_dep = "OWNER_DECISION_LATIN_SUBSTITUTION"
            product_dep = "LANGUAGE_MUST_BE_REPRESENTED_DISTINCTLY"
            note = (
                "Griffith renders this explicit passage into Latin; the literal is his real "
                f"text but not English, so it imports as language='{LATIN_LANGUAGE_CODE}'"
            )
        elif c == "C_WITHHOLD_REUSED_RENDERING_POLICY":
            final = "IMPORT_REUSED_RENDERING"
            owner_dep = "OWNER_DECISION_D_REUSED_RENDERING_POLICY"
            product_dep = "REUSE_MUST_BE_DISCLOSED"
            note = (
                "Griffith's Rigvedic rendering of a verse whose Sanskrit is verified "
                f"identical; importable only with the reuse disclosed, never as independent "
                f"{veda} English"
            )
        elif gb["evidence"]["granularity"]["measured_grain"] == "MANTRA_RANGE":
            final = "IMPORT_MANTRA_RANGE"
            product_dep = "RANGE_COVERAGE_MUST_BE_REPRESENTED"
            note = "an explicitly numbered multi-verse print unit, complete over its span"
        elif b == "B_NEEDS_INDEPENDENT_CONTENT_CONTROL" or _is_forced(gb):
            final = "IMPORT_VERIFIED_FORCED_ADDRESS"
            owner_dep = "OWNER_DECISION_C_FORCED_ADDRESSES"
            note = "forced address, independently verified against the printed source"
        else:
            final = "IMPORT_SOURCE_EXPLICIT"
            note = "the source prints this verse's own label and its own translation"

        if final not in ALL_CLASSES:
            raise AccountingError(f"{row_id}: class {final!r} is not declared")

        out[row_id] = {
            "row_id": row_id,
            "canonical_key": key,
            "veda": veda,
            "source_id": staged["source_id"],
            "source_locator": staged["source_locator"],
            "gate_b_verdict": b,
            "gate_c_verdict": c,
            "prior_final_class": packet["prior"][row_id]["final_class"],
            "final_class": final,
            "owner_policy_dependency": owner_dep,
            "product_semantics_dependency": product_dep,
            "importable": final in IMPORT_CLASSES,
            "mapping_confidence": confidence,
            "measured_grain": gb["evidence"]["granularity"]["measured_grain"],
            "staged_language": staged["payload"].get("language"),
            "import_language": (
                LATIN_LANGUAGE_CODE if final == "IMPORT_NON_ENGLISH_TRANSLATION" else "en"
            ),
            "counts_as_independent_english": final in INDEPENDENT_ENGLISH_CLASSES,
            "note": note,
        }
    return out


def _is_forced(gate_b_row: dict[str, Any]) -> bool:
    forced = gate_b_row["evidence"]["forced_address"]
    return bool(forced.get("flag")) or bool(forced.get("verification"))


# --------------------------------------------------------------------------------------
# Invariants
# --------------------------------------------------------------------------------------


def class_counts(classified: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Counts for every declared class, including the classes measured at zero."""
    counts = dict.fromkeys(ALL_CLASSES, 0)
    for row in classified.values():
        counts[row["final_class"]] += 1
    return counts


def assert_one_disposition(classified: dict[str, dict[str, Any]]) -> None:
    """Every staged row appears exactly once, under exactly one declared class."""
    if len(classified) != EXPECTED_ROWS:
        raise AccountingError(f"{len(classified)} rows classified, expected {EXPECTED_ROWS}")
    ids = [r["row_id"] for r in classified.values()]
    if len(set(ids)) != EXPECTED_ROWS:
        raise AccountingError("duplicate row_id in the disposition table")
    total = sum(class_counts(classified).values())
    if total != EXPECTED_ROWS:
        raise AccountingError(f"final_class counts sum to {total}, expected {EXPECTED_ROWS}")


def write_json(path: pathlib.Path, obj: Any) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8"
    )
    return path


def write_jsonl(path: pathlib.Path, rows: list[dict[str, Any]]) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path
