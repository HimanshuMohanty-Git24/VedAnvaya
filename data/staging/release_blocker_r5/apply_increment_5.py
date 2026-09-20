"""R5 increment 5: disclose the one edge whose figures I cannot reproduce, without inventing any.

Increment 4's reproduce-then-apply guard REFUSED to write this edge, and it was right to.
``VG:SV:KAU:CHANDA:P01:D08:V04`` <-> ``VSM 12.51`` stores
``similarity 0.913866`` and ``ngram_jaccard 0.857143``, and
``vedagraph.enrich.crossveda.score_pair`` does not produce those numbers from ANY pairing of
the six stored text versions -- I tried all six SV-role x YV-role combinations and the
closest, PRIMARY_TEXT x SEARCH_DERIVATIVE, gives similarity 0.969988 and ngram_jaccard
0.969388. Only ``lcs_ratio`` reproduces.

WHY, and it is visible on the edge itself: this row is not from the same code path as the
other 13. It carries ``wave3_group: FORMULA_RELATION_TYPOLOGY`` and a full set of
``formula_*`` fields, its ``method`` reads
``crossveda-parallels:near:minhash-char4+lcs:SANDHI_INSENSITIVE``, and -- decisively --
``cross_veda_changed_by_anusvara_correction`` is **true** on this edge and **false** on the
RV-SV thirteen. Its figures were computed before or across a fold correction I cannot
reconstruct from ``src``.

SO NOTHING IS RECOMPUTED HERE. What is done instead is the only honest thing available:

*   the CLASS, which is known false on read evidence, stops being published as current. It
    was ``HEAD_TRUNCATION``, and the truncated head was a Wikisource cross-reference line
    belonging to the PRECEDING verse. One of only two HEAD_TRUNCATION rows in all 6,596.
*   the contaminated quote, which still reads ``draiḍāmagne...``, is withdrawn with the old
    value preserved.
*   the METRICS are marked unverifiable against the corrected text, naming the exact reason
    and the closest reproduction, so a reader is not told they were checked. They are LEFT
    AT THEIR STORED VALUES rather than replaced by a figure I cannot defend.

A wrong number replaced by a number nobody can reproduce is worse than a wrong number
labelled as unreproducible.
"""

from __future__ import annotations

import datetime
import json
import pathlib
from typing import Any

from neo4j import Query

import _q

HERE = pathlib.Path(__file__).resolve().parent
SUBJECT = "VG:SV:KAU:CHANDA:P01:D08:V04"
OBJECT = "VG:YV:VSM:A12:V051"
STALE = "STALE_PENDING_REDERIVATION"
CONTRACT = "VG:R5_CLOSURE:V1"


def go(session) -> dict[str, Any]:
    before = _q.rows(
        session,
        """
        MATCH (a:Passage {canonical_key:$s})-[r:NEAR_PARALLEL_OF]->(b:Passage {canonical_key:$o})
        RETURN r.cross_veda_transformation AS transformation,
               r.cross_veda_transformation_status AS status,
               r.similarity AS similarity, r.lcs_ratio AS lcs_ratio,
               r.ngram_jaccard AS ngram_jaccard,
               r.cross_veda_changed_by_anusvara_correction AS anusvara_corrected,
               r.wave3_group AS wave3_group, r.method AS method,
               left(coalesce(r.evidence,''), 60) AS evidence_head,
               left(coalesce(r.formula_evidence,''), 60) AS formula_evidence_head
        """,
        s=SUBJECT,
        o=OBJECT,
    )
    if not before:
        raise SystemExit("the edge is not there; refusing")

    record = session.run(
        Query(
            """
            MATCH (a:Passage {canonical_key:$s})-[r:NEAR_PARALLEL_OF]->
                  (b:Passage {canonical_key:$o})
            SET r.cross_veda_transformation_superseded =
                  coalesce(r.cross_veda_transformation_superseded,
                           r.cross_veda_transformation),
                r.cross_veda_transformation = $stale,
                r.cross_veda_transformation_uncorrected_superseded =
                  coalesce(r.cross_veda_transformation_uncorrected_superseded,
                           r.cross_veda_transformation_uncorrected),
                r.cross_veda_transformation_uncorrected = $stale,
                r.cross_veda_transformation_status =
                  'STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED',
                r.cross_veda_transformation_stale_reason = $class_reason,

                r.evidence_superseded = coalesce(r.evidence_superseded, r.evidence),
                r.evidence = NULL,
                r.formula_evidence_superseded =
                  coalesce(r.formula_evidence_superseded, r.formula_evidence),
                r.formula_evidence = NULL,
                r.formula_difference_spans_superseded =
                  coalesce(r.formula_difference_spans_superseded,
                           r.formula_difference_spans),
                r.formula_difference_spans = NULL,
                r.evidence_status = 'STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED',
                r.evidence_stale_reason = $quote_reason,

                r.cross_veda_metrics_status = 'UNVERIFIABLE_AGAINST_THE_CORRECTED_TEXT',
                r.cross_veda_metrics_unverifiable_reason = $metrics_reason,
                r.r5_contract = $contract
            RETURN count(r) AS n
            """,
            timeout=600.0,
        ),
        s=SUBJECT,
        o=OBJECT,
        stale=STALE,
        contract=CONTRACT,
        class_reason=(
            "The class was HEAD_TRUNCATION and the truncated head was a Wikisource "
            "cross-reference line ('द्र. ') belonging to the PRECEDING verse, which the "
            "parser's unit boundary attached forward. It was not a textual variant. One of "
            "only two HEAD_TRUNCATION rows in the whole 6,596-row transformation artifact, "
            "so one of the two instances of that class in this corpus was this project's own "
            "segmentation. The replacement class is not inferred here: the 16-value "
            "vocabulary lives in the cross-Veda staging build and not in src."
        ),
        quote_reason=(
            "The published quote and the difference spans were computed over the apparatus "
            "line and began 'draiḍāmagne'. Withdrawn rather than left standing; the old "
            "values are preserved in the _superseded fields."
        ),
        metrics_reason=(
            "NOT RECOMPUTED, and not silently left as if checked. "
            "vedagraph.enrich.crossveda.score_pair does not reproduce this edge's stored "
            "metrics from any pairing of the six stored text versions -- all six SV-role x "
            "YV-role combinations were tried and the closest, PRIMARY_TEXT x "
            "SEARCH_DERIVATIVE, gives similarity 0.969988 and ngram_jaccard 0.969388 against "
            "a stored 0.913866 and 0.857143; only lcs_ratio reproduces at 0.970588. The "
            "reason is visible on this edge: it comes from the FORMULA_RELATION_TYPOLOGY path "
            "rather than the crossveda path the other 13 came from, and "
            "cross_veda_changed_by_anusvara_correction is TRUE here and FALSE on all 13, so "
            "its figures were computed across a fold correction that cannot be reconstructed "
            "from src. The stored values are therefore LEFT AS THEY ARE and labelled "
            "unverifiable, because a wrong number replaced by a number nobody can reproduce "
            "is worse than a wrong number labelled unreproducible. The metrics are re-derived "
            "when the formula and cross-Veda stages next run."
        ),
    ).single()

    after = _q.rows(
        session,
        """
        MATCH (a:Passage {canonical_key:$s})-[r:NEAR_PARALLEL_OF]->(b:Passage {canonical_key:$o})
        RETURN r.cross_veda_transformation AS transformation,
               r.cross_veda_transformation_status AS status,
               r.cross_veda_transformation_superseded AS superseded,
               r.cross_veda_metrics_status AS metrics_status,
               r.evidence AS evidence, r.formula_evidence AS formula_evidence,
               left(coalesce(r.evidence_superseded,''), 40) AS evidence_superseded_head
        """,
        s=SUBJECT,
        o=OBJECT,
    )

    keys = [
        "VG:SV:KAU:CHANDA:P01:D08:V04",
        "VG:SV:KAU:ARANYA:D01:V04",
        "VG:SV:KAU:CHANDA:P04:D05:V06",
        "VG:SV:KAU:CHANDA:P02:D07:V07",
    ]
    return {
        "artifact": "R5_INCREMENT_5",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "edge": {"subject": SUBJECT, "rel": "NEAR_PARALLEL_OF", "object": OBJECT},
        "before": before[0],
        "edges_written": record["n"],
        "after": after[0],
        "metrics_recomputed": False,
        "why_metrics_not_recomputed": "score_pair reproduces none of them; see the stored reason",
        "verification": {
            "head_truncation_anywhere": _q.one(
                session,
                "MATCH ()-[r]->() WHERE r.cross_veda_transformation = 'HEAD_TRUNCATION' "
                "RETURN count(r)",
            ),
            "head_truncation_on_a_corrected_verse": _q.one(
                session,
                """
                MATCH (a:Passage)-[r]->(b:Passage)
                WHERE (a.canonical_key IN $keys OR b.canonical_key IN $keys)
                  AND r.cross_veda_transformation = 'HEAD_TRUNCATION'
                RETURN count(r)
                """,
                keys=keys,
            ),
            "parallel_edges_on_the_four_without_a_status": _q.one(
                session,
                """
                MATCH (a:Passage)-[r]->(b:Passage)
                WHERE (a.canonical_key IN $keys OR b.canonical_key IN $keys)
                  AND type(r) IN ['REUSES_TEXT_FROM','NEAR_PARALLEL_OF','EXACT_PARALLEL_OF',
                                  'VARIANT_OF']
                  AND r.cross_veda_transformation_status IS NULL
                RETURN count(r)
                """,
                keys=keys,
            ),
            "edges_publishing_a_contaminated_quote": _q.one(
                session,
                """
                MATCH ()-[r]->()
                WHERE coalesce(r.evidence,'') CONTAINS 'draiḍāmagne'
                   OR coalesce(r.formula_evidence,'') CONTAINS 'draiḍāmagne'
                   OR coalesce(r.formula_difference_spans,'') CONTAINS 'draiḍāmagne'
                RETURN count(r)
                """,
            ),
            "apparatus_in_any_text_field_of_the_four": _q.one(
                session,
                """
                MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
                WHERE p.canonical_key IN $keys
                  AND (t.text_nfc STARTS WITH 'dra ' OR t.text_original STARTS WITH 'dra '
                       OR t.text_nfc STARTS WITH 'āraṇyaka'
                       OR t.text_original STARTS WITH 'āraṇyaka'
                       OR t.text_nfc CONTAINS 'द्र. ' OR t.text_original CONTAINS 'द्र. '
                       OR t.text_nfc STARTS WITH '(आरण्यक'
                       OR t.text_original STARTS WITH '(आरण्यक')
                RETURN count(t)
                """,
                keys=keys,
            ),
        },
    }


if __name__ == "__main__":
    result = _q.run(go)
    (HERE / "increment_5_receipt.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
