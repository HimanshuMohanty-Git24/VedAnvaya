"""Three corrections to stage_mutations.py, each caught by a check before anything applied.

1.  TRANSLATION-004 was classifying verses with a hand-rolled state machine, and it got the
    Samaveda WRONG in the one way the brief forbids by name: all 173 SV renderings carry
    ``reuse_kind = REUSED_RENDERING`` from VEDAGRAPH_CANONICAL_RV_GRIFFITH, so the Samaveda
    has ZERO independent English translations, and my draft labelled them ``OWN_ENGLISH``.
    It also called 1,488 SV verses ``REUSED_RENDERING_FROM_A_PARALLEL_VERSE`` when they
    carry no rendering at all and merely have a reusable parallel -- an overstatement of
    1,488 verses. Replaced with the production classifier
    ``translation_semantics.verse_coverage_state``, so there is one contract and not two.

2.  ENTITY_COVERAGE-006's metric reported ``eligible_denominator`` 163 below
    ``tested_population`` 164, which reads as an arithmetic error. It is not: ayas is
    lexically tested against the RV annotation AND source-attested outside lexical
    recoverability in the YV, so it belongs to both. The overlap is now stated instead of
    left to look like a mistake.

3.  RITUAL-005 read ``receives_offering_rejected.jsonl`` (7 deity-offering rejects) for the
    rite-offering candidate population. The real population is the 258 ``USES_OFFERING``
    rows of ``data/staging/ritual/rite_edges.jsonl``, every one ``mapping_confidence:
    PROBABLE``, over 58 distinct rites.
"""

from __future__ import annotations

import pathlib

TARGET = pathlib.Path(__file__).resolve().parent / "stage_mutations.py"


REPLACEMENTS: list[tuple[str, str]] = [
    # ---- 1. translation_004 -------------------------------------------------
    (
    '''    rows = _q.rows(
        session,
        """
        MATCH (m:Mantra)
        OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(t:Translation)
        WITH m, collect({lang: t.language, level: t.alignment_level}) AS ts
        RETURN m.canonical_key AS key, m.veda AS veda, ts
        ORDER BY key
        """,
    )''',
    '''    rows = _q.rows(
        session,
        """
        MATCH (m:Mantra)
        OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(t:Translation)
        WITH m, collect(CASE WHEN t IS NULL THEN NULL ELSE properties(t) END) AS ts
        RETURN m.canonical_key AS key, m.veda AS veda,
               [x IN ts WHERE x IS NOT NULL] AS ts
        ORDER BY key
        """,
    )''',
    ),
    (
    '''    reused = {
        r["key"]
        for r in _q.rows(
            session,
            """
            MATCH (m:Mantra)-[:REUSES_TEXT_FROM]->(o:Mantra)-[:HAS_TRANSLATION]->(:Translation)
            WHERE NOT (m)-[:HAS_TRANSLATION]->()
            RETURN DISTINCT m.canonical_key AS key
            """,
        )
    }''',
    '''    reusable_parallel = {
        r["key"]
        for r in _q.rows(
            session,
            """
            MATCH (m:Mantra)-[:REUSES_TEXT_FROM]->(o:Mantra)-[:HAS_TRANSLATION]->(:Translation)
            WHERE NOT (m)-[:HAS_TRANSLATION]->()
            RETURN DISTINCT m.canonical_key AS key
            """,
        )
    }''',
    ),
    (
    '''    for r in rows:
        langs = {t["lang"] for t in r["ts"] if t["lang"]}
        levels = {t["level"] for t in r["ts"] if t["level"]}
        if "en" in langs and "MANTRA" in levels:
            state = "OWN_ENGLISH"
        elif "en" in langs and "MANTRA_RANGE" in levels:
            state = "OWN_ENGLISH_RANGE_ANCHOR"
        elif "en" in langs and "HYMN" in levels:
            state = "HYMN_GRAIN_ONLY"
        elif r["key"] in covered:
            state = "RANGE_COVERED_BY_A_PAIRED_UNIT"
        elif langs and "en" not in langs:
            state = "NON_ENGLISH_ONLY"
        elif r["key"] in reused:
            state = "REUSED_RENDERING_FROM_A_PARALLEL_VERSE"
        else:
            state = "UNCOVERED_ABSENT_FROM_THE_SOURCE_SPINE"
            uncovered.append(r["key"])
        dist[f"{r['veda']}|{state}"] += 1''',
    '''    for r in rows:
        # The production classifier, not a second copy of its rules. A verse's own
        # translations are passed through as property maps exactly as classify() expects.
        state = verse_coverage_state(
            r["key"],
            r["ts"],
            range_covered=r["key"] in covered,
            reusable_parallel=r["key"] in reusable_parallel,
        ).value
        if state in {s.value for s in UNCOVERED_STATES}:
            uncovered.append(r["key"])
        dist[f"{r['veda']}|{state}"] += 1''',
    ),
    (
    '''        "uncovered_rows": sorted(uncovered),
        "rv_uncovered": sum(1 for k in uncovered if k.startswith("VG:RV")),''',
    '''        "uncovered_rows": sorted(uncovered),
        "rv_uncovered": sum(1 for k in uncovered if k.startswith("VG:RV")),
        "independent_english_by_veda": {
            veda: sum(
                n
                for state, n in states.items()
                if state in {s.value for s in INDEPENDENT_ENGLISH_STATES}
            )
            for veda, states in sorted(by_veda.items())
        },
        "samaveda_independent_english": (
            "ZERO. All 173 Samavedic renderings carry reuse_kind=REUSED_RENDERING from "
            "VEDAGRAPH_CANONICAL_RV_GRIFFITH -- Griffith's Rigvedic English attached to "
            "verses whose Sanskrit is verified identical. A total that reports 173 English "
            "translations for the Samaveda is wrong, and an earlier draft of this very "
            "staging made that mistake before the reuse_kind column was checked."
        ),''',
    ),
    (
    '''            "terminal_states": [
                "OWN_ENGLISH",
                "OWN_ENGLISH_RANGE_ANCHOR",
                "HYMN_GRAIN_ONLY",
                "RANGE_COVERED_BY_A_PAIRED_UNIT",
                "REUSED_RENDERING_FROM_A_PARALLEL_VERSE",
                "NON_ENGLISH_ONLY",
                "UNCOVERED_ABSENT_FROM_THE_SOURCE_SPINE",
            ],
            "reused_rendering_is_not_own_english": (
                "REUSED_RENDERING_FROM_A_PARALLEL_VERSE is a separate terminal state and is "
                "NOT counted as an independent Samaveda English translation."
            ),''',
    '''            "terminal_states": [s.value for s in VerseCoverageState],
            "contract": "vedagraph.domain.translation_semantics.VerseCoverageState",
            "reused_rendering_is_not_own_english": (
                "REUSED_RENDERING is a terminal state of its own and is excluded from "
                "INDEPENDENT_ENGLISH_STATES, so it cannot be totalled into a corpus's own "
                "English coverage."
            ),''',
    ),
    (
    '        "new_metric": {\n            "cypher": (\n                "MATCH (m:Mantra {veda:\'RV\'}) "\n                "WHERE m.translation_coverage_state = \'UNCOVERED_ABSENT_FROM_THE_SOURCE_SPINE\' "\n                "RETURN count(m)"\n            ),',
    '        "new_metric": {\n            "cypher": (\n                "MATCH (m:Mantra {veda:\'RV\'}) "\n                "WHERE m.translation_coverage_state IN "\n                "[\'UNCOVERED_REUSABLE_PARALLEL_AVAILABLE\', \'UNCOVERED_NO_RENDERING_REACHES_IT\'] "\n                "RETURN count(m)"\n            ),',
    ),
    # ---- 2. entity_006 metric overlap --------------------------------------
    (
    '''    metric["classes_sum_to_population"] = (
        metric["eligible_denominator"]
        + metric["source_attested_outside_lexical_recoverability"]
        + metric["not_applicable_no_registered_sanskrit_alias"]
        + metric["insufficient_evidence_no_annotation_anchor"]
    ) == metric["registry_population"]''',
    '''    metric["classes_sum_to_population"] = (
        metric["eligible_denominator"]
        + metric["source_attested_outside_lexical_recoverability"]
        + metric["not_applicable_no_registered_sanskrit_alias"]
        + metric["insufficient_evidence_no_annotation_anchor"]
    ) == metric["registry_population"]
    # The applicability classes PARTITION the registry, so they sum to 384. The tested
    # population does not sit inside one class: ayas is lexically tested against the RV
    # annotation AND source-attested outside lexical recoverability in the YV, so it is
    # classed SOURCE_ATTESTED_NONLEXICAL and still contributes a tested row. Stated, so
    # that eligible_denominator < tested_population does not read as an arithmetic error.
    metric["tested_population_also_counted_under_source_attested"] = sum(
        1
        for u in updates
        if u["properties"]["recall_applicability"] == "SOURCE_ATTESTED_NONLEXICAL"
        and u["entity_key"] in {r["entity_key"] for r in rows if r["status"] == "MEASURED_AGAINST_RV_ANNOTATION"}
    )
    metric["why_tested_exceeds_eligible"] = (
        "An entity may be both lexically testable and source-attested outside lexical "
        "recoverability. ayas is: its RV recall is measured at 7 of 13 tokens, and its "
        "Yajurvedic occurrence at VG:YV:VSM:A18:V013 is real and not lexically recoverable. "
        "The applicability class records the STRONGER fact, so the row leaves the eligible "
        "denominator while remaining in the tested population."
    )''',
    ),
    # ---- 3. ritual_005 candidate population --------------------------------
    (
    '''    probable = SPRINT / "agent4" / "receives_offering_rejected.jsonl"
    rejected_rows = [
        json.loads(line)
        for line in probable.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rites_with_probable = {
        r.get("ritual_key") for r in rejected_rows if r.get("ritual_key")
    }''',
    '''    # The rite-to-offering candidate population is the 258 USES_OFFERING rows of the
    # sealed ritual staging, every one mapping_confidence PROBABLE, over 58 rites. An
    # earlier draft read receives_offering_rejected.jsonl instead, which holds 7
    # DEITY-offering rejects and is a different question.
    rite_edges = HERE.parents[0] / "ritual" / "rite_edges.jsonl"
    candidate_rows = [
        json.loads(line)
        for line in rite_edges.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    probable_offering_rows = [
        r
        for r in candidate_rows
        if r.get("predicate") == "USES_OFFERING" and r.get("mapping_confidence") == "PROBABLE"
    ]
    rites_with_probable = {
        r["ritual_key"] for r in probable_offering_rows if r.get("ritual_key")
    }
    rejected_rows = probable_offering_rows''',
    ),
    (
    '''        "probable_rows_left_unimported": len(rejected_rows),
        "edges_minted": 0,
    }''',
    '''        "probable_rows_left_unimported": len(probable_offering_rows),
        "probable_rows_source": "data/staging/ritual/rite_edges.jsonl, predicate USES_OFFERING",
        "rites_with_a_probable_candidate": len(rites_with_probable),
        "edges_minted": 0,
        "why_no_edge_minted": (
            "Every one of the 258 candidate rows is mapping_confidence PROBABLE, resting on "
            "one sutra naming both a rite and an offering. Clause 3 of this gap's own "
            "closure test forbids presenting co-occurrence as an asserted offering, and the "
            "historical rule that PROBABLE ritual material stays excluded is binding. Under "
            "OWNER_DECISIONS.md section 39 they are non-asserted candidates, not missing "
            "graph data."
        ),
    }''',
    ),
]

IMPORT_OLD = "from vedagraph.enrich.concepts import fold_alias  # noqa: E402"
IMPORT_NEW = """from vedagraph.domain.translation_semantics import (  # noqa: E402
    INDEPENDENT_ENGLISH_STATES,
    UNCOVERED_STATES,
    VerseCoverageState,
    verse_coverage_state,
)
from vedagraph.enrich.concepts import fold_alias  # noqa: E402"""


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if IMPORT_NEW in text:
        raise SystemExit("already patched")
    text = text.replace(IMPORT_OLD, IMPORT_NEW, 1)
    for old, new in REPLACEMENTS:
        if old not in text:
            raise SystemExit(f"anchor not found, refusing partial patch:\n{old[:160]}")
        text = text.replace(old, new, 1)
    TARGET.write_text(text, encoding="utf-8", newline="")
    print(f"patched {len(REPLACEMENTS)} anchors + 1 import")


if __name__ == "__main__":
    main()
