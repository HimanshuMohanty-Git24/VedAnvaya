"""Correct the public claims GAP-SEMANTICS-003 and GAP-PRODUCT_SURFACE-005 falsified.

Enumerated from what this pass MOVED, not grepped for what I expected to find -- this
registry has recorded two stale-claim audits that certified absence falsely, one by looking
only under ``docs/`` and one by grepping the value it expected instead of the field's value
space.

MEASURED AFTER THE MIGRATION:

    ASSERTION_AGENT      2,502 -> 2,660   (RV 2,406, AV 124, YV 34, no-veda 96)
    ASSERTION_TARGET       799 ->   918   (no-veda 799, AV 85, YV 34)
    nodes              164,597 -> 164,599
    relationships      509,486 -> 509,769
    DerivedMetric        1,481 ->  1,483

DELIBERATELY NOT CHANGED, because they are still TRUE. ``queries.py`` and
``insight_queries.py`` both say "Only 799 of these carry an ASSERTION_TARGET" inside a
caveat SCOPED TO ``MODEL_EXTRACTION``, and the model layer still carries exactly 799
targets, all of them ``:Devata``. Rewriting a correct sentence because a neighbouring
figure moved is how a sweep introduces the defect it was run to remove.

THE CLAIM THAT BECAME FALSE IN KIND, not merely in figure: "2,502 assertions carry an
ASSERTION_AGENT and every one of them is Rigvedic". The agentive reading is no longer
Rigveda-only -- 124 Atharvavedic and 34 Yajurvedic assertions now carry an agent, from the
DCS dependency annotation the projection reads. That is a change to what the product can
answer, not a count, so the prose is rewritten rather than renumbered.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]

EDITS: list[tuple[str, str, str]] = [
    # ---- scripts/wave3_readback.py: a hard-coded invariant that would now fail -------
    (
        "scripts/wave3_readback.py",
        """#: Edge counts the migration cards promised would not change, and the one that changes by
#: exactly one. M1's card states ASSERTION_AGENT 2,502 and ASSERTION_TARGET 799; M5's
#: states EPITHET_VARIANT_OF goes 11 to 10 and SPECIALIZED_FORM_OF becomes 1.
PROMISED: dict[str, int] = {
    "ASSERTION_AGENT": 2502,
    "ASSERTION_TARGET": 799,""",
        """#: Edge counts the migration cards promised would not change, and the one that changes by
#: exactly one. M1's card states ASSERTION_AGENT 2,502 and ASSERTION_TARGET 799; M5's
#: states EPITHET_VARIANT_OF goes 11 to 10 and SPECIALIZED_FORM_OF becomes 1.
#:
#: R5 MOVED THE FIRST TWO, and this readback is the reason the move is visible rather than
#: silent. GAP-SEMANTICS-003 projected the existing RoleFiller REFERS_TO resolution onto the
#: assertion as agent and target -- 158 agents and 119 targets, all derivation
#: ``TREEBANK_DEPREL_ROLE_PROJECTION``. The figures below are the post-R5 populations. The
#: Wave 3 card's own promise is unbroken: nothing R5 did altered a Wave 3 edge, it added a
#: layer beside them, and the derivation on every added edge is what keeps the two
#: separable by query.
PROMISED: dict[str, int] = {
    "ASSERTION_AGENT": 2660,
    "ASSERTION_TARGET": 918,""",
    ),
    # ---- graph_service: the non-traversable docstring figures ------------------------
    (
        "src/vedagraph/api/services/graph_service.py",
        """#: itself to passages and is never product content. ``ASSERTION_PREDICATE`` (2,672),
#: ``ASSERTION_AGENT`` (2,502) and ``ASSERTION_TARGET`` (799) are the internal wiring of the""",
        """#: itself to passages and is never product content. ``ASSERTION_PREDICATE`` (2,672),
#: ``ASSERTION_AGENT`` (2,660) and ``ASSERTION_TARGET`` (918) are the internal wiring of the""",
    ),
    # ---- queries.py module docstring: Rigveda-only is no longer true -----------------
    (
        "src/vedagraph/domain/queries.py",
        """``HAS_SEMANTIC_ASSERTION`` is *not* in that set any more: it carries 35,131 edges and
reaches all four corpora. What remains Rigveda-only inside it is the agentive reading --
2,502 assertions carry an ``ASSERTION_AGENT`` and every one of them is Rigvedic. ``HAS_RISHI`` and""",
        """``HAS_SEMANTIC_ASSERTION`` is *not* in that set any more: it carries 35,131 edges and
reaches all four corpora. The agentive reading inside it was Rigveda-only and is not any
more: ``ASSERTION_AGENT`` carries 2,660 edges over RV 2,406, AV 124 and YV 34, because
GAP-SEMANTICS-003 projected the DCS dependency annotation's own role resolution onto the
assertion. The Sāmaveda still carries no agent. ``HAS_RISHI`` and""",
    ),
    # ---- queries.py: the Devata-typed pattern that would now under-report ------------
    (
        "src/vedagraph/domain/queries.py",
        """        OPTIONAL MATCH (s)-[:ASSERTION_AGENT]->(agent:Devata)
        OPTIONAL MATCH (s)-[:ASSERTION_PREDICATE]->(ap:ActionPredicate)
        OPTIONAL MATCH (s)-[:ASSERTION_TARGET]->(target:Devata)""",
        """        // Untyped on purpose. Both predicates are declared over
        // {Devata, DomainEntity} and GAP-SEMANTICS-003 populated the second half, so a
        // :Devata-typed pattern here would silently drop 103 non-deity targets and 58
        // non-deity agents -- reporting a slot as empty because the filler is a substance
        // rather than a god.
        OPTIONAL MATCH (s)-[:ASSERTION_AGENT]->(agent)
        OPTIONAL MATCH (s)-[:ASSERTION_PREDICATE]->(ap:ActionPredicate)
        OPTIONAL MATCH (s)-[:ASSERTION_TARGET]->(target)""",
    ),
    # ---- passage.py: the same Rigveda-only claim, in the reader's own words ----------
    (
        "src/vedagraph/api/models/passage.py",
        """    What remains Rigveda-only is the *agentive* reading: 2,502 assertions over 2,254
    Rigvedic passages carry an ``ASSERTION_AGENT``, because that reading is derived from a
    morphological annotation covering the Rigveda alone.""",
        """    The *agentive* reading was Rigveda-only and is not any more. 2,660 assertions carry
    an ``ASSERTION_AGENT``: 2,406 Rigvedic, from a morphological annotation covering the
    Rigveda alone, plus 124 Atharvavedic and 34 Yajurvedic projected from the DCS
    dependency annotation's own role resolution by GAP-SEMANTICS-003. The Sāmaveda carries
    no agent at all. The two derivations are separable on every edge -- the projected ones
    carry ``derivation = TREEBANK_DEPREL_ROLE_PROJECTION`` and the morphological ones carry
    none -- so a reader is never shown one tier as the other.""",
    ),
    # ---- passage_service caveat -------------------------------------------------------
    (
        "src/vedagraph/api/services/passage_service.py",
        '''        "Reaches all four corpora unevenly -- RV 27,057 assertions, AV 6,167, YV 1,543, "
        "SV 364 -- and the agentive reading inside it does not. Only 2,502 assertions over "
        "2,254 Rigvedic passages carry an agent, so 'who does what to whom' is Rigveda-only "
        "even where the layer is not, and the Samavedic 364 are projected from "
        "letter-identical Rigvedic verses rather than annotated in their own corpus.",''',
        '''        "Reaches all four corpora unevenly -- RV 27,057 assertions, AV 6,167, YV 1,543, "
        "SV 364 -- and the agentive reading inside it reaches three. 2,660 assertions carry "
        "an agent: 2,406 Rigvedic from the morphological annotation, and 124 Atharvavedic "
        "plus 34 Yajurvedic projected from the DCS dependency annotation's own role "
        "resolution. The Samaveda carries no agent, so 'who does what to whom' is "
        "unanswerable there, and its 364 assertions are projected from letter-identical "
        "Rigvedic verses rather than annotated in their own corpus.",''',
    ),
]

DOC_EDITS: list[tuple[str, str, str]] = [
    (
        "docs/reports/data-completeness/quality.md",
        """only at `:Devata` (2,502 edges), `ASSERTION_TARGET` only at `:Devata` (799), and""",
        """only at `:Devata` (2,502 edges), `ASSERTION_TARGET` only at `:Devata` (799), and""",
    ),
]

APPENDED_NOTES: list[tuple[str, str]] = [
    (
        "docs/reports/data-completeness/quality.md",
        """

## R5 correction — the assertion slots no longer point only at `:Devata`

The paragraph above measured the graph as it stood, and `GAP-SEMANTICS-003` has since moved
it. The **declared range** was never narrow: `ontology.py` has admitted
`{Devata, DomainEntity}` on both `ASSERTION_AGENT` and `ASSERTION_TARGET` throughout, so
the entry's own `implementation_dependency` asking to "widen" them was asking for a widening
that had already happened. What was missing was any edge.

R5 projected the resolution that already existed one hop away: 2,052 `:RoleFiller` nodes
carry 348 `REFERS_TO` edges to registered entities, derived `TREEBANK_DEPREL` from DCS
dependency relations at `TIER_B` with the conllu `sent_id` on the edge. Measured after:

| predicate | before | after | non-`:Devata` after |
| --- | --- | --- | --- |
| `ASSERTION_AGENT` | 2,502 | 2,660 | 58 |
| `ASSERTION_TARGET` | 799 | 918 | 103 |

Only `AGENT` and `PATIENT` were projected. `BENEFICIARY`, `GOAL`, `INSTRUMENT`, `LOCATION`
and `SOURCE` stay on `ASSERTION_ROLE` alone: they are distinct roles, and folding five of
them into a slot called "target" would make the slot mean five things — which is the tier
blending the entry warned about.
""",
    ),
    (
        "docs/reports/data-completeness/SCHEMA_MIGRATION_CARDS.md",
        """

## R5 correction to the M1 card

The card's premise — "`ASSERTION_AGENT` and `ASSERTION_TARGET` point only at `:Devata` —
verified live, 2,502 and 799 edges" — was a true measurement of the POPULATION and was never
true of the DECLARED RANGE, which has admitted `{Devata, DomainEntity}` on both predicates
throughout. `GAP-SEMANTICS-003` populated the second half in R5: `ASSERTION_AGENT` reads
2,660 with 58 non-deity agents and `ASSERTION_TARGET` reads 918 with 103 non-deity targets.

Nothing the M1 card promised was broken. No edge it wrote was altered, no endpoint was
re-declared, and the added edges carry
`derivation = TREEBANK_DEPREL_ROLE_PROJECTION` so the two populations stay separable by
query rather than blending into one figure.
""",
    ),
    (
        "docs/reports/data-completeness/cross-veda.md",
        """

## R5 correction — one of the two `HEAD_TRUNCATION` rows was our own parser

The transformation table above is a faithful reading of
`data/staging/cross_veda/proofs/transformations.jsonl` as it stood. One cell in it is now
known to be an artefact of this project rather than a fact about the corpus.

`HEAD_TRUNCATION` occurs **twice** in all 6,596 rows, and one of the two is
`VG:SV:KAU:CHANDA:P01:D08:V04` ↔ `VSM 12.51`. That Samavedic verse carried a Wikisource
apparatus line — `द्र. `, a cross-reference annotation belonging to the PRECEDING verse,
which the parser's unit boundary attached forward. The similarity measures and the published
evidence quote were computed over it, and the difference classifier read the resulting
extra head as a truncation: a claim about Vedic textual variation whose whole cause was our
own segmentation.

`GAP-PRODUCT_SURFACE-005` corrected the text in R5, in the canonical artifact and in the
graph. The 13 affected cross-Veda edges were rescored from the corrected text by
`vedagraph.enrich.crossveda.score_pair`, which reproduced every stored metric exactly on the
contaminated text before being trusted on the corrected one. The transformation CLASS was
**not** re-derived — its sixteen-value vocabulary lives in the cross-Veda staging build and
not in `src`, so a value inferred here would have been a guess — and each affected edge
instead carries `cross_veda_transformation_status =
STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED` with the old value preserved beside it.

**So this table's `HEAD_TRUNCATION` row will read 1, not 2, when the cross-Veda stage next
runs.** The figure is left as measured rather than edited in place, because the table's value
is that it matches the artifact it was taken from.
""",
    ),
]


def main() -> None:
    for relative, old, new in EDITS:
        path = ROOT / relative
        raw = path.read_bytes()
        if b"\r\n" in raw:
            raise SystemExit(f"{relative} contains CRLF; refusing")
        text = raw.decode("utf-8")
        if old not in text:
            if new in text:
                print(f"  already applied: {relative}")
                continue
            raise SystemExit(f"anchor not found in {relative}:\n{old[:200]}")
        path.write_bytes(text.replace(old, new, 1).encode("utf-8"))
        print(f"  edited {relative}")

    lf = "\n"
    crlf_ending = "\r\n"
    for relative, addition in APPENDED_NOTES:
        path = ROOT / relative
        raw = path.read_bytes()
        # Each file keeps ITS OWN line ending. quality.md and cross-veda.md are 637 and 856
        # CRLF lines with no bare LF; SCHEMA_MIGRATION_CARDS.md is 493 LF. Appending LF to a
        # CRLF file, or normalising one, turns a two-paragraph note into a whole-file diff --
        # the mixed-line-ending defect this repository has recorded.
        is_crlf = crlf_ending.encode("utf-8") in raw
        text = raw.decode("utf-8")
        marker = addition.strip().splitlines()[0]
        if marker in text:
            print(f"  note already present: {relative}")
            continue
        if not text.endswith(lf):
            text += lf
        body = addition.replace(crlf_ending, lf)
        if is_crlf:
            body = body.replace(lf, crlf_ending)
        path.write_bytes(text.encode("utf-8") + body.encode("utf-8"))
        after = path.read_bytes()
        mixed = crlf_ending.encode("utf-8") in after and after.count(
            lf.encode("utf-8")
        ) != after.count(crlf_ending.encode("utf-8"))
        print(f"  appended R5 note to {relative} (crlf={is_crlf}, mixed_after={mixed})")
        if mixed:
            raise SystemExit(f"{relative} now has MIXED line endings; that is a defect")


if __name__ == "__main__":
    main()
