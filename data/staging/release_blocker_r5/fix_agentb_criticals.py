"""Agent B's seven criticals and the material majors. Each fix names the finding it answers.

Agent B's verdict on the graph work was that it survives independent re-derivation. Its
verdict on the PUBLIC SURFACES was that they do not, and it was right: five documents, two
OpenAPI descriptions and a shipped disclosure query still asserted the pre-closure state as
current measured fact. A reader acts on those.

MEASURED LIVE, and every figure below was re-read after the migration and increment 2:

    strength-bearing edges                             76,838
      of which value 1.0                               51,364  (source_explicit_tier_marker)
      of which value 0.85                              12,781
      of which value 0.80                              11,203
      the three clusters together                      75,348  = 98.1%
    predicates whose figure is a single constant             9  (7 tier + 2 uncalibrated)
    edges still carrying `confidence`                  25,470  (11 predicates, all varying)
    SemanticAssertion.human_gold_status null           32,672
    SemanticAssertion.human_gold_status UNANNOTATED     2,459
    SemanticAssertion.review_state UNREVIEWED          35,131  (all)
    ASSERTION_AGENT / ASSERTION_TARGET                  2,660 / 918
    all-three-slot assertions                              10
    non-Devata agents / targets                          58 / 103
    SV mantras carrying HAS_TRANSLATION                    173  (all REUSED_RENDERING)
    SV independent English                                   0
    nodes / relationships                            164,601 / 509,769
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# C01 -- the shipped disclosure query went blind, and its caveat is superseded
# ---------------------------------------------------------------------------

C01_QUERY_OLD = """        cypher=\"\"\"
        MATCH ()-[r]->()
        WHERE r.confidence IS NOT NULL
        WITH type(r) AS predicate, r.confidence AS value, count(*) AS edges
        WITH predicate, collect({value: value, edges: edges}) AS spread,
             sum(edges) AS predicate_total
        WITH predicate, predicate_total, spread,
             reduce(top = 0, s IN spread | CASE WHEN s.edges > top THEN s.edges ELSE top END)
               AS modal_edges
        RETURN predicate, predicate_total, size(spread) AS distinct_values,
               modal_edges,
               round(1000.0 * modal_edges / predicate_total) / 10 AS modal_share_pct,
               CASE WHEN size(spread) = 1 THEN 'SINGLE_CONSTANT'
                    WHEN modal_edges * 2 > predicate_total THEN 'MAJORITY_ONE_CONSTANT'
                    ELSE 'DISTRIBUTED' END AS guard_verdict,
               'PIPELINE_PRIOR, NOT A CALIBRATED CONFIDENCE' AS what_this_field_is,
               'NONE: no labelled evaluation set and no reliability curve exist in this '
               + 'graph' AS calibration_evidence
        ORDER BY predicate_total DESC
        \"\"\","""

C01_QUERY_NEW = """        cypher=\"\"\"
        // Reads all THREE strength fields, not just `confidence`. GAP-QUALITY-003 withdrew
        // `confidence` from the seven source-explicit predicates, and a `confidence IS NOT
        // NULL` filter therefore reported zero SINGLE_CONSTANT rows while 51,364 edges
        // still carried exactly 1.0 under another name -- making the one query whose job is
        // to disclose the constants blind to the largest block of them. Agent B's C01.
        MATCH ()-[r]->()
        WHERE r.confidence IS NOT NULL
           OR r.source_explicit_tier_marker IS NOT NULL
           OR r.uncalibrated_pipeline_score IS NOT NULL
        WITH type(r) AS predicate,
             coalesce(r.confidence, r.source_explicit_tier_marker,
                      r.uncalibrated_pipeline_score) AS value,
             CASE WHEN r.confidence IS NOT NULL THEN 'confidence'
                  WHEN r.source_explicit_tier_marker IS NOT NULL
                       THEN 'source_explicit_tier_marker'
                  ELSE 'uncalibrated_pipeline_score' END AS field,
             r.calibration_status AS calibration_status,
             count(*) AS edges
        WITH predicate, field, calibration_status,
             collect({value: value, edges: edges}) AS spread,
             sum(edges) AS predicate_total
        WITH predicate, field, calibration_status, predicate_total, spread,
             reduce(top = 0, s IN spread | CASE WHEN s.edges > top THEN s.edges ELSE top END)
               AS modal_edges
        RETURN predicate, field, predicate_total, size(spread) AS distinct_values,
               modal_edges,
               round(1000.0 * modal_edges / predicate_total) / 10 AS modal_share_pct,
               CASE WHEN size(spread) = 1 THEN 'SINGLE_CONSTANT'
                    WHEN modal_edges * 2 > predicate_total THEN 'MAJORITY_ONE_CONSTANT'
                    ELSE 'DISTRIBUTED' END AS guard_verdict,
               CASE WHEN field = 'source_explicit_tier_marker'
                      THEN 'AN EVIDENCE TIER, NOT A PROBABILITY'
                    WHEN field = 'uncalibrated_pipeline_score'
                      THEN 'AN UNCALIBRATED PIPELINE SCORE, NOT A PROBABILITY'
                    ELSE 'PIPELINE_PRIOR, NOT A CALIBRATED CONFIDENCE' END
                 AS what_this_field_is,
               coalesce(calibration_status,
                        'NOT_CALIBRATED_NO_HUMAN_LABELLED_SAMPLE') AS calibration_evidence
        ORDER BY predicate_total DESC
        \"\"\","""

C01_CAVEAT_OLD = '''        caveat=(
            "THE FIELD IS NAMED `confidence` AND IS NOT ONE. It is a pipeline prior: a "
            "constant stamped per branch. Measured, 75,997 of 77,518 confidence-bearing "
            "edges -- 98.0% -- sit at exactly one of three values (1.0 on 50,468, 0.85 on "
            "12,809, 0.80 on 12,720). A researcher who filters `confidence >= 0.8` "
            "believes they have raised precision and has selected a set of pipeline "
            "branches. This got WORSE in V3, not better: the baseline's 0.42 cluster was "
            "replaced by a 1.0 cluster of 50,468 edges. "
            "`guard_verdict` is the constant-value guard, and it is returned per row "
            "rather than described here: SINGLE_CONSTANT means the value carries no "
            "information at all for that predicate, MAJORITY_ONE_CONSTANT means one value "
            "covers over half of it. "
            "There is NO calibrated uncertainty in this graph. There is no labelled "
            "evaluation set and no reliability diagram; `human_gold_status` is "
            "UNANNOTATED on 2,459 SemanticAssertion nodes and null on the other 2,406, "
            "and `review_state` is UNREVIEWED on all of them. Calibration is HUMAN_BLOCKED "
            "and cannot be produced by a model run. "
            "For real per-edge uncertainty use `quality_tier`, `evidence_basis` and "
            "`attribution_precision`, which are derived from what the edge actually rests "
            "on. The field SHOULD be renamed to `pipeline_prior`; that rename is bounded "
            "backlog rather than done, because `confidence` appears in 38 source files "
            "and one of them, src/vedagraph/semantic/ontology.py, is inside the semantic "
            "hash seal, where the same word means a model's own output rather than a "
            "pipeline constant. A blanket rename would break the seal and conflate two "
            "different quantities, so it needs a scoped pass over the edge writers alone."
        ),'''

C01_CAVEAT_NEW = '''        caveat=(
            "NO FIELD IN THIS GRAPH IS A CALIBRATED CONFIDENCE, and three different fields "
            "carry the three different things that were all once called one. Measured after "
            "GAP-QUALITY-003: 76,838 edges carry a strength figure, and 75,348 of them -- "
            "98.1% -- sit at exactly one of three values (1.0 on 51,364, 0.85 on 12,781, "
            "0.80 on 11,203). A researcher who filters on 0.8 believes they have raised "
            "precision and has selected a set of pipeline branches. "
            "WHICH FIELD an edge uses is returned per row, because the three are not the "
            "same claim. `source_explicit_tier_marker` (51,364 edges over 7 predicates, all "
            "at 1.0) is an EVIDENCE TIER: the source states the relation, and the figure "
            "carries no per-edge information at all. It was called `confidence` until R5 "
            "renamed it, because a constant stamped on every edge of a predicate offers a "
            "threshold that keeps all of them or none. `uncalibrated_pipeline_score` (4 "
            "edges over 2 predicates) is a pipeline default on a population too small to "
            "vary -- 3 edges and 1 -- which is a sample size and not a tier, which is why "
            "those two did NOT get the tier marker. `confidence` (25,470 edges over 11 "
            "predicates) is the only one where the value genuinely varies edge to edge, and "
            "every one of those edges carries "
            "`calibration_status = NOT_CALIBRATED_NO_HUMAN_LABELLED_SAMPLE`. "
            "`guard_verdict` is the constant-value guard, returned per row rather than "
            "described here: SINGLE_CONSTANT means the value carries no information for "
            "that predicate, MAJORITY_ONE_CONSTANT means one value covers over half of it. "
            "Nine predicates read SINGLE_CONSTANT. "
            "CALIBRATION IS HUMAN-BLOCKED and cannot be produced by a model run. There is "
            "no labelled evaluation set and no reliability diagram anywhere in this graph: "
            "`human_gold_status` is UNANNOTATED on 2,459 SemanticAssertion nodes and null "
            "on the other 32,672, and `review_state` is UNREVIEWED on all 35,131. The "
            "reference set that does exist is an "
            "INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET and is NOT human gold; 0 nodes "
            "in this graph claim to be. "
            "For real per-edge uncertainty use `quality_tier`, `evidence_basis` and "
            "`attribution_precision`, which are derived from what the edge actually rests "
            "on. The remaining `confidence` spelling is NOT renamed further, and the reason "
            "is a boundary rather than a backlog: src/vedagraph/semantic/ontology.py is "
            "inside the semantic hash seal, where the same word means a model's own output "
            "rather than a pipeline constant, so a blanket rename would break the seal and "
            "conflate two quantities."
        ),'''

# ---------------------------------------------------------------------------
# C02 -- two OpenAPI-served descriptions
# ---------------------------------------------------------------------------

C02_OLD = """five predicates carry a single value on every edge they have: `HAS_RISHI` (17,889 edges, all 1.0), `HAS_CHANDAS` (16,298, all 1.0), `HAS_DEVATA` (10,558, all 1.0), `HAS_DEVATA_ASCRIPTION` (5,385, all 1.0) and `BELONGS_TO_FAMILY` (305, all 1.0)."""

C02_NEW = """SEVEN predicates stamp one value on every edge they have, and since GAP-QUALITY-003 they do not carry `confidence` at all -- the figure lives in `source_explicit_tier_marker`, because a constant on every edge encodes an evidence TIER and not a probability: `HAS_RISHI` (17,889 edges, all 1.0), `HAS_CHANDAS` (16,298), `HAS_DEVATA` (10,558), `HAS_DEVATA_ASCRIPTION` (5,385), `HAS_DEVATA_DERIVED` (882), `BELONGS_TO_FAMILY` (305) and `ASCRIBES_TO_DEVATA` (47). Those edges return `confidence: null` and the constant as `pipeline_prior`. The 25,470 edges whose confidence genuinely varies keep the field and each carries `calibration_status = NOT_CALIBRATED_NO_HUMAN_LABELLED_SAMPLE`."""

# ---------------------------------------------------------------------------
# C06 -- a release audit that aborts on the census
# ---------------------------------------------------------------------------

C06_OLD = '''    assert census == {"nodes": 164597, "relationships": 509486}, census'''
C06_NEW = '''    # 164,597/509,486 -> 164,601/509,769. Moved by two receipted R5 steps: the migration
    # (data/staging/release_blocker_r5/migration_receipt.json -- +2 DerivedMetric nodes and
    # +283 relationships, actual == promised on every counter) and the entity-coverage
    # consumer rebuild the dependency report then required (+2 DerivedMetric). Agent B's
    # C06: this assert aborted the whole public-identity audit, and because nothing wires
    # the script to a gate it failed by never being run rather than by going red.
    assert census == {"nodes": 164601, "relationships": 509769}, census'''

# ---------------------------------------------------------------------------
# C07 -- the ontology reference, under a header promising measured counts
# ---------------------------------------------------------------------------

C07_EDITS = [
    ("- **edges:** 2,502", "- **edges:** 2,660"),
    ("- **edges:** 799", "- **edges:** 918"),
]


def _rewrite(relative: str, pairs: list[tuple[str, str]], *, required: bool = True) -> int:
    path = ROOT / relative
    raw = path.read_bytes()
    is_crlf = b"\r\n" in raw
    text = raw.decode("utf-8")
    changed = 0
    for old, new in pairs:
        anchor = old.replace("\n", "\r\n") if is_crlf else old
        body = new.replace("\n", "\r\n") if is_crlf else new
        if anchor not in text:
            if body in text:
                continue
            if required:
                raise SystemExit(f"anchor not found in {relative}:\n{old[:200]}")
            continue
        text = text.replace(anchor, body, 1)
        changed += 1
    if changed:
        path.write_bytes(text.encode("utf-8"))
        after = path.read_bytes()
        if b"\r\n" in after and after.count(b"\n") != after.count(b"\r\n"):
            raise SystemExit(f"{relative} now has MIXED line endings")
    print(f"  {relative}: {changed} edit(s) (crlf={is_crlf})")
    return changed


def _append(relative: str, marker: str, body: str) -> None:
    path = ROOT / relative
    raw = path.read_bytes()
    is_crlf = b"\r\n" in raw
    text = raw.decode("utf-8")
    if marker in text:
        print(f"  {relative}: note already present")
        return
    if not text.endswith("\n"):
        text += "\n"
    addition = body.replace("\r\n", "\n")
    if is_crlf:
        addition = addition.replace("\n", "\r\n")
    path.write_bytes(text.encode("utf-8") + addition.encode("utf-8"))
    after = path.read_bytes()
    if b"\r\n" in after and after.count(b"\n") != after.count(b"\r\n"):
        raise SystemExit(f"{relative} now has MIXED line endings")
    print(f"  {relative}: appended R5 note (crlf={is_crlf})")


def main() -> None:
    print("C01 -- the blinded disclosure query and its superseded caveat")
    _rewrite(
        "src/vedagraph/domain/queries.py",
        [(C01_QUERY_OLD, C01_QUERY_NEW), (C01_CAVEAT_OLD, C01_CAVEAT_NEW)],
    )

    print("C02 -- the OpenAPI-served descriptions")
    _rewrite("src/vedagraph/api/models/graph.py", [(C02_OLD, C02_NEW)], required=False)
    _rewrite("src/vedagraph/api/routes/graph.py", [(C02_OLD, C02_NEW)], required=False)
    _rewrite("frontend/src/lib/api-schema.ts", [(C02_OLD, C02_NEW)], required=False)

    print("C06 -- the release audit that aborts")
    _rewrite("scripts/audit_public_identity.py", [(C06_OLD, C06_NEW)])

    print("C07 -- the ontology reference")
    _rewrite("docs/reports/VEDAGRAPH_ONTOLOGY_REFERENCE_V3.md", C07_EDITS, required=False)
    _append(
        "docs/reports/VEDAGRAPH_ONTOLOGY_REFERENCE_V3.md",
        "## R5 correction",
        """

## R5 correction — three figures in this file are older than its own header

The header says *"Every count below is measured, not typed. Re-run it rather than editing
it."* Three counts were typed and had gone stale, two of them before R5 and one because of
it. Corrected in place and recorded here so the correction is not itself invisible:

| where | said | reads |
| --- | --- | --- |
| `ASSERTION_AGENT` edges | 2,502 | **2,660** |
| `ASSERTION_TARGET` edges | 799 | **918** |
| live graph header | 116,838 nodes / 281,257 relationships | **164,601 / 509,769** |
| `DerivedMetric` | 1,085 | **1,485** |

The two assertion-slot figures moved in R5, when `GAP-SEMANTICS-003` projected the
`:RoleFiller` `REFERS_TO` resolution onto the assertion: 158 agents and 119 targets, of
which 58 and 103 respectively point at a `:DomainEntity` rather than a `:Devata`. The
declared RANGE of both predicates has admitted `{Devata, DomainEntity}` throughout; only the
population was narrow. The other two figures were already stale before R5 and are corrected
here rather than left, because a file whose first line promises measured counts cannot carry
a count from a graph two thirds this size.

**`MUSICALIZED_AS` is unchanged and still carries 0 edges.** Its gloss in this file is what
`GAP-SAMAVEDA_MUSIC-003`'s clause 2 cites: the predicate is declared `Passage -> Passage`
and glossed Rigvedic-verse-to-Samavedic-melody, so it cannot honestly carry an
arcika-to-gāna edge without being widened, and no gāna node exists to be its object.
""",
    )

    print("C03 -- quality.md's Section 0 and its confidence tables")
    _rewrite(
        "docs/reports/data-completeness/quality.md",
        [
            (
                "50,468 of 76,050 confidence-bearing edges carry exactly `1.0`; five predicates stamp one value on every edge they have",
                "51,364 of 76,838 strength-bearing edges carry exactly `1.0`; SEVEN predicates stamp one value on every edge they have, and since R5 those seven carry `source_explicit_tier_marker` rather than `confidence`",
            ),
        ],
        required=False,
    )
    _append(
        "docs/reports/data-completeness/quality.md",
        "## R5 correction — every confidence figure in this report is superseded",
        """

## R5 correction — every confidence figure in this report is superseded

`GAP-QUALITY-003` closed in R5 and it moved the field this report is largely about. **Every
`confidence` figure above, including the one-sentence answer in Section 0 and the tables in
the confidence section, describes the graph BEFORE that closure.** They are left in place
because they are the finding the gap was opened for; read them as the state that was
corrected, not as the state that is.

What the graph reads now, measured after the closure:

| | before | now |
| --- | --- | --- |
| strength-bearing edges | 76,050 | **76,838** |
| edges at exactly 1.0 | 50,468 | **51,364**, and none of them under `confidence` |
| predicates stamping one value on every edge | 5 named (7 actual) | **7**, all under `source_explicit_tier_marker` |
| edges still carrying `confidence` | 76,050 | **25,470**, over 11 predicates whose value genuinely varies |
| those edges carrying a calibration disclosure | 0 | **25,470** |
| `human_gold_status` null | 2,406 | **32,672** |
| assertions carrying agent + predicate + target | 0 | **10** |
| `ASSERTION_AGENT` / `ASSERTION_TARGET` | 2,502 / 799, `:Devata` only | **2,660 / 918**, with 58 / 103 non-deity |

The 1.0 was never a probability. It recorded that the source states the relation — an
evidence TIER — and published as `confidence` it offered a filter that keeps all of a
predicate's edges or none. It is renamed rather than deleted, so the source-explicit fact
survives, and the seven writers that produce those edges were changed at source so a rebuild
reproduces the rename rather than reversing it.

**No human gold was manufactured.** Calibration curves still do not exist and cannot, because
no human-labelled sample exists in this repository: 0 nodes carry `is_human_gold = true`, and
the reference set that does exist is an `INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET`. What
changed is that the absence is now stated on all 25,470 edges instead of only in prose.
""",
    )

    print("C04 -- gap-census.md, which got no banner at all")
    _append(
        "docs/reports/data-completeness/gap-census.md",
        "## R5 correction — three census claims here are superseded",
        """

## R5 correction — three census claims here are superseded

This file was the one document in this directory that R5's first stale-claim sweep missed.
Three of its claims are now false, and two were false before R5 touched anything.

**"the role slots can only point at deities"** (§ on the semantic layer). They can and do
point elsewhere. The declared RANGE of `ASSERTION_AGENT` and `ASSERTION_TARGET` has admitted
`{Devata, DomainEntity}` throughout; only the population was narrow, and
`GAP-SEMANTICS-003` populated it in R5 by projecting the `:RoleFiller` `REFERS_TO`
resolution that already existed one hop away. Measured now: **2,660** agents of which 58
non-deity, **918** targets of which 103 non-deity.

**"Not one of the 4,865 assertions carries a complete agent-predicate-target triple"** is
wrong twice over. **10** assertions now carry all three slots, and the denominator was
already wrong when written: `:SemanticAssertion` is **35,131** nodes, not 4,865. The 4,865
was the population before R1's identity repair restored the other 30,266, and the same
mis-denominator is recorded and corrected in `layer_figures.py`.

**"The Samaveda has no translation at all: 0 of 1,844 mantras carry HAS_TRANSLATION"** is
false as a statement about the edge and true as a statement about the thing that matters.
**173** Samavedic mantras carry a `HAS_TRANSLATION` edge. Every one of the 173 is a
`REUSED_RENDERING`: Griffith's Rigvedic English attached to a Samavedic verse whose Sanskrit
is verified character-identical. So the Samaveda's INDEPENDENT English translation count is
**0**, which is what this sentence was reaching for — and the corrected form of it is that
0 of 1,844 Samavedic verses have been translated as Samavedic verses, while 173 display
another corpus's rendering and say so. `GAP-TRANSLATION-004` types this per verse:
`REUSED_RENDERING` is a terminal state of its own and is excluded from
`INDEPENDENT_ENGLISH_STATES`, so no total can quietly report 173 as Samaveda English.
""",
    )

    print("M20 -- the remaining prose that still says the Samaveda has none")
    _append(
        "docs/reports/GRAPH_ENRICHMENT_V1.md",
        "> **R5 correction.** The Samaveda",
        """

> **R5 correction.** The Samaveda now carries 173 `HAS_TRANSLATION` edges, every one a
> `REUSED_RENDERING` of Griffith's Rigvedic English on verified character-identical
> Sanskrit. Its count of INDEPENDENT Samavedic English translations is still 0, which is
> what the sentence above was reaching for; `GAP-TRANSLATION-004` types the distinction per
> verse so no total can report 173 as the Samaveda's own English.
""",
    )
    _append(
        "docs/reports/data-completeness/semantic-resemblance.md",
        "> **R5 correction.** The 173 Samavedic",
        """

> **R5 correction.** The 173 Samavedic renderings are no longer future tense: they are in
> the live graph, and the table row reading "Samavedic translations in the live graph | 0"
> is superseded. All 173 carry `reuse_kind = REUSED_RENDERING`, so the Samaveda's
> independent English count remains 0 and the two figures are not in conflict -- they
> measure different things, which is why `GAP-TRANSLATION-004` gives the verse-level state
> its own terminal value.
""",
    )


if __name__ == "__main__":
    main()
