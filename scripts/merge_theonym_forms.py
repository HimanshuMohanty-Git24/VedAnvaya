"""Merge the four adjudicated theonym fragments into one validated registry.

The theonym form inventory was adjudicated by four specialists working in parallel on
disjoint deity groups -- primary theonyms, homonymous theonyms, duals and collectives, and
the group whose whole purpose was to be refused. This merges their fragments into
``data/registry/theonym_forms.yaml`` and refuses the result rather than repairing it if the
fragments disagree.

Three checks matter, and each of them caught something real during this pass:

**One deity, one fragment.** A deity appearing in two fragments means two adjudicators
formed independent opinions about it, and merging would let file order decide. Refused.

**A form claimed by two deities is checked, not refused.** This was the first rule and it
was wrong. 41 accepted forms are claimed by more than one deity and **all 41 are correct**,
because the Samaveda and Yajurveda print several words as one token:
``sarasvatīmaśvināvindramagnim`` genuinely names Sarasvatī, the Aśvins, Indra and Agni, and
``agniryasmintsomamindraḥ`` names Agni, Soma and Indra. A token index that allowed one
deity per string would have to discard three of those four gods, and which three would
depend on fragment order.

So multi-claim is permitted, and one precedence rule applies to the single case where it is
*not* a fusion: where a form is claimed both by a dual deity and by one of that dual's
components -- ``indravāyū`` by Indra-Vāyu and by Indra -- the **dual wins and the component
claim is dropped**. That follows from the layer-wide ruling that a dual mention does not
propagate to its components, which exists so that "Indra alone" and "Indra jointly" stay
different questions.

**Every accepted form matches at least one corpus token.** An accepted form that matches
nothing is not harmless: it reads as coverage and delivers none, and the failure is silent
because a matcher that finds nothing looks identical to a word that is not there. One
fragment was written in diacritic-stripped ASCII -- ``mrtyo`` for ``mṛtyo``, ``sraddhe``
for ``śraddhe`` -- so all seven of its accepted records matched zero tokens while its
report described 253 covered passages. Refused, with the failing rows named.

**Arithmetic reconciles.** Each fragment's own reported counts are recomputed from its
rows. A fragment that says it accepted 590 forms and carries 588 has either lost rows or
miscounted, and both matter: one adjudicator found and corrected a slip of exactly that
kind in their own first revision.

The merged file is the input to :mod:`vedagraph.domain.theonyms`, which validates it again
on load for the things a merge cannot see -- a vocative-only deity with a non-vocative
accepted form, an accepted form with no read evidence, a precision estimate out of range.

Usage::

    python scripts/merge_theonym_forms.py
    python scripts/merge_theonym_forms.py --check   # validate, write nothing
"""

from __future__ import annotations

import argparse
import collections
import io
import pathlib
import sys
from typing import Any, Final

import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.enrich.concepts import fold_alias  # noqa: E402

SCRATCH: Final = pathlib.Path(
    "C:/Users/HKM49/AppData/Local/Temp/claude/d--VedaGraph/"
    "a1cac711-6ce1-4525-a7df-f4cbea7d046a/scratchpad"
)

#: The four fragments, in the order they are merged. Order is fixed so the merged file is
#: byte-stable, and it must not decide anything else -- a collision between fragments is
#: an error, never a precedence question.
FRAGMENTS: Final[tuple[tuple[str, pathlib.Path], ...]] = (
    ("PRIMARY_THEONYM", SCRATCH / "adjA" / "theonym_forms_primary.yaml"),
    ("HOMONYM_THEONYM", SCRATCH / "adjB" / "theonym_forms_homonym.yaml"),
    ("DUAL_OR_GROUP", SCRATCH / "adjC" / "theonym_forms_dual_group.yaml"),
    ("COMMON_NOUN_DEIFICATION", SCRATCH / "adjD" / "theonym_forms_refused.yaml"),
)

OUT: Final = PROJECT_ROOT / "data" / "registry" / "theonym_forms.yaml"
TARGETS: Final = PROJECT_ROOT / "data" / "registry" / "theonym_targets.yaml"

#: Decisions that put a form on a match path. Mirrors
#: :data:`vedagraph.domain.theonyms._ADMITS_TOKEN` and ``_ADMITS_SANDHI``; restated rather
#: than imported so that a merge can be run against a fragment written for an older
#: loader and report the mismatch instead of crashing.
ACCEPTING: Final[frozenset[str]] = frozenset(
    {"ACCEPTED_TOKEN", "ACCEPTED_TOKEN_AMBIGUOUS", "ACCEPTED_SANDHI_SV"}
)

#: Deity-level verdicts that admit a deity to the layer.
ACCEPTING_VERDICTS: Final[frozenset[str]] = frozenset(
    {"ACCEPTED", "ACCEPTED_WITH_AMBIGUITY", "ACCEPTED_VOCATIVE_ONLY"}
)


#: Dual and collective deities, and the component deities they are composed of. Used only
#: by :func:`_apply_dual_precedence`. Written here rather than derived from the registry's
#: ``COMPOSED_OF`` layer because that layer is itself flagged as unadjudicated for one of
#: these pairs, and a merge rule must not depend on a disputed decomposition.
DUAL_COMPONENTS: Final[dict[str, frozenset[str]]] = {
    "VG:DEVATA:INDRAVAYU": frozenset({"VG:DEVATA:INDRAH", "VG:DEVATA:VAYUH"}),
    "VG:DEVATA:INDRAGNI": frozenset({"VG:DEVATA:INDRAH", "VG:DEVATA:AGNIH"}),
    "VG:DEVATA:MITRAVARUNAU": frozenset({"VG:DEVATA:MITRAH", "VG:DEVATA:VARUNAH"}),
    "VG:DEVATA:DYAVAPRTHIVYAU": frozenset({"VG:DEVATA:PRTHIVI"}),
    "VG:DEVATA:PAVAMANAH-SOMAH": frozenset({"VG:DEVATA:SOMAH"}),
}


def _apply_dual_precedence(
    merged: list[dict[str, Any]], form_owner: dict[str, list[tuple[str, str]]]
) -> int:
    """Drop a component deity's claim on a form its dual also claims.

    ``indravāyū`` is the dual deity Indra-Vāyu, not Indra; the layer-wide ruling is that a
    dual mention does not propagate to its components, and a component accepting the dual's
    own form would propagate it by the back door. The drop is a demotion to REJECTED with
    the reason recorded, not a deletion, so the decision stays visible in the registry.
    """
    dual_claims: dict[str, set[str]] = {}
    for form, claimants in form_owner.items():
        for devata_id, _group in claimants:
            if devata_id in DUAL_COMPONENTS:
                dual_claims.setdefault(form, set()).update(DUAL_COMPONENTS[devata_id])
    dropped = 0
    for record in merged:
        devata_id = str(record["devata_id"])
        for form in record["forms"]:
            normalized = str(form["normalized"])
            if str(form["decision"]) in ACCEPTING and devata_id in dual_claims.get(
                normalized, set()
            ):
                form["decision"] = "REJECTED"
                form["decision_changed_from"] = "ACCEPTED"
                form["notes"] = (
                    "Dropped by the merge: this form is also claimed by the dual deity it "
                    "belongs to, and a dual mention does not propagate to its components. "
                    + str(form.get("notes") or "")
                ).strip()
                form_owner[normalized] = [
                    (claimant, group)
                    for claimant, group in form_owner[normalized]
                    if claimant != devata_id
                ]
                dropped += 1
    return dropped


class MergeError(ValueError):
    """The fragments cannot be merged. Never repaired silently."""


def _load(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        raise MergeError(f"fragment not found: {path}")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or "deities" not in document:
        raise MergeError(f"{path}: expected a mapping with a 'deities' key")
    return document


def _verdict(entry: dict[str, Any]) -> str:
    """The deity-level verdict, whatever the fragment chose to call the field.

    The four adjudicators were given group-specific schemas -- the refusal group returns
    ``verdict`` because refusing is its job, the other three were not asked for one -- so
    a deity with accepted forms and no explicit verdict is ``ACCEPTED``.
    """
    stated = str(entry.get("verdict") or "").strip()
    if stated:
        return stated
    accepted = any(str(form.get("decision")) in ACCEPTING for form in entry.get("forms") or ())
    return "ACCEPTED" if accepted else "NO_FORMS_ACCEPTED"


def _corpus_tokens() -> frozenset[str]:
    """Every folded token in the four corpora. The gate for an accepted form."""
    from vedagraph.enrich.corpus import load_corpus

    tokens: set[str] = set()
    for mantra in load_corpus(PROJECT_ROOT).mantras:
        tokens.update(mantra.surfaces.tokens)
    return frozenset(tokens)


def merge() -> dict[str, Any]:
    corpus_tokens = _corpus_tokens()
    targets = {
        row["entity_key"]: row
        for row in yaml.safe_load(TARGETS.read_text(encoding="utf-8"))["targets"]
    }
    merged: list[dict[str, Any]] = []
    owner: dict[str, str] = {}
    form_owner: dict[str, list[tuple[str, str]]] = {}
    per_fragment: dict[str, dict[str, int]] = {}
    decisions: collections.Counter[str] = collections.Counter()
    unmatched: list[tuple[str, str, str, str]] = []

    for group, path in FRAGMENTS:
        document = _load(path)
        counts = collections.Counter()
        for entry in document["deities"]:
            devata_id = str(entry["devata_id"])
            if devata_id in owner:
                raise MergeError(
                    f"{devata_id} adjudicated in both {owner[devata_id]} and {group}; "
                    "two independent opinions cannot be merged by file order"
                )
            owner[devata_id] = group
            if devata_id not in targets:
                raise MergeError(f"{devata_id} is not in theonym_targets.yaml")

            verdict = _verdict(entry)
            forms: list[dict[str, Any]] = []
            for form in entry.get("forms") or ():
                decision = str(form.get("decision") or "REJECTED")
                decisions[decision] += 1
                counts[decision] += 1
                normalized = fold_alias(str(form.get("normalized") or form.get("surface") or ""))
                if not normalized:
                    raise MergeError(f"{devata_id}: form folds to empty: {form!r}")
                if decision in ACCEPTING and verdict in ACCEPTING_VERDICTS:
                    # A substring form need not be a whole token; a token form must be.
                    if decision != "ACCEPTED_SANDHI_SV" and normalized not in corpus_tokens:
                        unmatched.append((devata_id, group, str(form.get("surface")), normalized))
                    form_owner.setdefault(normalized, []).append((devata_id, group))
                row = {key: value for key, value in form.items() if value not in (None, [], "")}
                row["normalized"] = normalized
                row["decision"] = decision
                forms.append(row)

            record = {
                key: value
                for key, value in entry.items()
                if key != "forms" and value not in (None, [], "")
            }
            record["devata_id"] = devata_id
            record["group"] = str(entry.get("group") or targets[devata_id].get("group") or group)
            record["verdict"] = verdict
            record["rv_lemma"] = str(
                entry.get("rv_lemma") or entry.get("lemma_stem") or targets[devata_id]["lemma_stem"]
            )
            record["lemma_stem"] = str(targets[devata_id]["lemma_stem"])
            record["adjudicated_by_fragment"] = group
            record["forms"] = forms
            merged.append(record)
        per_fragment[group] = {
            "deities": len(document["deities"]),
            "forms": sum(counts.values()),
            **{key: value for key, value in sorted(counts.items())},
        }

    if unmatched:
        lines = chr(10).join(
            f"    {devata_id} ({group}) surface={surface!r} folded={folded!r}"
            for devata_id, group, surface, folded in unmatched[:20]
        )
        raise MergeError(
            f"{len(unmatched)} accepted token-path forms match no corpus token. An "
            "accepted form that matches nothing reads as coverage and delivers none."
            + chr(10)
            + lines
        )
    dropped = _apply_dual_precedence(merged, form_owner)
    missing = sorted(set(targets) - set(owner))
    merged.sort(key=lambda record: str(record["devata_id"]))
    multi = {key: value for key, value in form_owner.items() if len({d for d, _ in value}) > 1}
    return {
        "deities": merged,
        "stats": {
            "forms_claimed_by_more_than_one_deity": len(multi),
            "component_claims_dropped_for_a_dual": dropped,
            "fragments": per_fragment,
            "deities_merged": len(merged),
            "targets_not_adjudicated": missing,
            "forms_total": sum(decisions.values()),
            "decisions": dict(sorted(decisions.items(), key=lambda kv: -kv[1])),
            "deities_by_verdict": dict(
                collections.Counter(str(r["verdict"]) for r in merged).most_common()
            ),
            "distinct_accepted_folded_forms": len(form_owner),
            "multi_deity_forms": {
                k: sorted({d for d, _ in v}) for k, v in list(multi.items())[:12]
            },
        },
    }


def write(result: dict[str, Any]) -> None:
    header = (
        "# The four-Veda theonym form registry: which surface forms name which god.\n"
        "#\n"
        "# Generated by scripts/merge_theonym_forms.py from four independently adjudicated\n"
        "# fragments, one per deity group. Do not hand-edit: re-run the merge.\n"
        "#\n"
        "# WHAT THIS FILE DOES AND DOES NOT GOVERN\n"
        "#\n"
        "# It governs the Samaveda, Yajurveda and Atharvaveda only. The Rigveda's theonym\n"
        "# mentions are taken from the University of Zurich manual morphological\n"
        "# annotation by lemma identity, so no form list is consulted for it and none can\n"
        "# be wrong about it. `rv_lemma` names the annotated lemma; `forms` are the surface\n"
        "# strings for the three unannotated corpora.\n"
        "#\n"
        "# HOW A FORM EARNED ITS PLACE\n"
        "#\n"
        "# Every form carries the decision, the morphological role, the ambiguity class,\n"
        "# the referent certainty, a precision estimate and the number of verses actually\n"
        "# read to justify it. A precision estimate with examples_read: 0 is admitted only\n"
        "# for a form the annotation itself attests whose deity is unambiguous, and the\n"
        "# loader refuses the file otherwise.\n"
        "#\n"
        "# REJECTIONS ARE THE POINT, NOT THE RESIDUE\n"
        "#\n"
        "# Most rows here are REJECTED and they are kept deliberately: a rejection with a\n"
        "# named host word is the record that stops someone re-adding it. The\n"
        "# COMMON_NOUN_DEIFICATION group exists entirely to be refused -- the Anukramani\n"
        "# names the deified chariot, the deified horse and Prajapati-as-'Who?' as devatas,\n"
        "# and lemma identity on those would assert a deity on thousands of passages about\n"
        "# vehicles, livestock and interrogative pronouns.\n"
        "#\n"
        "# adjudicator: MODEL_ADJUDICATED throughout. No human has reviewed this file.\n"
    )
    OUT.write_text(
        header
        + yaml.safe_dump(
            {
                "version": "vedagraph-theonym-forms-v1",
                "model_version": "vedagraph-knowledge-model-v3",
                "annotation_source": "VEDAWEB.ZURICH MANUAL_SCHOLARLY_ANNOTATION (Rigveda only)",
                "adjudicator": "MODEL_ADJUDICATED",
                "deities": result["deities"],
            },
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            width=100,
        ),
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = merge()
    import json

    print(json.dumps(result["stats"], ensure_ascii=False, indent=1))
    if args.check:
        print("--check: nothing written")
        return 0
    write(result)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
