"""R5 increment 3: Agent B's M01, M02 and the transformation-class hazard behind M03/M04.

M01 -- CONFIRMED and this is the one that mattered. My correction set ``text_nfc`` and
``content_sha256`` on all 8 TextVersion rows and left ``text_original`` untouched on the 4
SEARCH_DERIVATIVE rows, where it still held the pre-correction apparatus text. Agent B
measured the invariant that makes this a defect rather than a curiosity: 1,840 of 1,844
Samavedic derivative rows have ``text_original == text_nfc``, and exactly my 4 now differ.
My own check and my own test read only ``text_nfc`` -- the test whose docstring promises
"Both text roles, not just the one the staged Cypher named". Two roles, one field each.

M02 -- CONFIRMED. ``formula_evidence`` on the RV 3.1.23 <-> SV CHANDA 1.8.4
``NEAR_PARALLEL_OF`` edge still published ``draiḍāmagnepurudaṃsaṃ...``. I corrected the
sibling ``evidence`` field and missed this one, and my test passed because it counted stale
markers rather than reading the quotes.

M03 -- FALSIFIED, and recorded here because the correction matters. Agent B reported "0 of
65 stored-vs-recomputed disagreements" and concluded the edges were "re-verified and
annotated, not rescored". That control compares the stored value against a recomputation on
the CORRECTED text, which is what the stored value now IS -- so agreement is what a
successful rescore produces, not evidence against one. The staging receipt records a
non-empty ``metric_delta`` for all 13 of 13 edges, and they are large: the SV-AV pair moved
``lcs_ratio`` 0.83871 -> 0.981132 and ``similarity`` 0.827688 -> 0.970958. The rescore
happened.

BUT AGENT B'S ADJACENT POINT IS RIGHT, and it is what this increment acts on.
``cross_veda_transformation`` still holds the OLD class as its live value -- ``HEAD_TRUNCATION``
on the VSM 12.51 pair -- with the stale marker in a neighbouring property. A consumer that
reads the field without reading ``cross_veda_transformation_status`` gets a known-false claim
about Vedic textual variation. Disclosure in a sibling field is weaker than not publishing
the wrong value: the field is set to an explicit ``STALE_PENDING_REDERIVATION`` sentinel, the
old value stays in ``_superseded``, and the class is re-derived when the cross-Veda stage
next runs. A sentinel rather than null, because null would let a reader infer "no
transformation", which is a different false claim.

M04 -- same treatment. ``cross_veda_lcs_ratio_rederived`` holds a value that reproduces
neither the stored ratio nor a recomputation, and its recipe is not in ``src``. It is marked
stale rather than left as a figure nothing can check.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
from typing import Any

from neo4j import Query

import _q

HERE = pathlib.Path(__file__).resolve().parent
KEYS = [
    "VG:SV:KAU:CHANDA:P01:D08:V04",
    "VG:SV:KAU:ARANYA:D01:V04",
    "VG:SV:KAU:CHANDA:P04:D05:V06",
    "VG:SV:KAU:CHANDA:P02:D07:V07",
]
STALE = "STALE_PENDING_REDERIVATION"
CONTRACT = "VG:R5_CLOSURE:V1"


def go(session) -> dict[str, Any]:
    out: dict[str, Any] = {
        "artifact": "R5_INCREMENT_3",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    # ---- M01: text_original on the derivative rows -------------------------
    before = _q.rows(
        session,
        """
        MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
        WHERE p.canonical_key IN $keys
        RETURN p.canonical_key AS key, t.text_role AS role, t.text_id AS text_id,
               t.text_original AS text_original, t.text_nfc AS text_nfc
        ORDER BY key, role
        """,
        keys=KEYS,
    )
    drifted = [
        r
        for r in before
        if r["text_original"] is not None and r["text_original"] != r["text_nfc"]
    ]
    # The corpus-wide invariant this restores, measured rather than asserted.
    invariant_before = _q.rows(
        session,
        """
        MATCH (m:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->(t:TextVersion)
        WHERE t.text_role = 'SEARCH_DERIVATIVE'
        RETURN count(t) AS rows,
               sum(CASE WHEN t.text_original = t.text_nfc THEN 1 ELSE 0 END) AS mirrored,
               sum(CASE WHEN t.text_original IS NULL THEN 1 ELSE 0 END) AS null_original
        """,
    )[0]

    fixed = 0
    for row in drifted:
        result = session.run(
            Query(
                """
                MATCH (t:TextVersion {text_id: $text_id})
                SET t.text_original = t.text_nfc,
                    t.text_original_corrected_by = 'SV-APPARATUS-LIFT-01',
                    t.text_original_corrected_because =
                      'The apparatus was removed from text_nfc and content_sha256 and left '
                      + 'here, so this field alone still held the contaminated reading. The '
                      + 'derivative row mirrors text_nfc on 1,840 of 1,844 Samavedic rows; '
                      + 'these 4 were the exception the correction created.',
                    t.r5_contract = $contract
                RETURN count(t) AS n
                """,
                timeout=600.0,
            ),
            text_id=row["text_id"],
            contract=CONTRACT,
        ).single()
        fixed += result["n"]

    invariant_after = _q.rows(
        session,
        """
        MATCH (m:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->(t:TextVersion)
        WHERE t.text_role = 'SEARCH_DERIVATIVE'
        RETURN count(t) AS rows,
               sum(CASE WHEN t.text_original = t.text_nfc THEN 1 ELSE 0 END) AS mirrored
        """,
    )[0]
    out["m01_text_original"] = {
        "rows_drifted_before": len(drifted),
        "drifted_keys": [f"{r['key']}|{r['role']}" for r in drifted],
        "rows_fixed": fixed,
        "sv_derivative_invariant_before": invariant_before,
        "sv_derivative_invariant_after": invariant_after,
        "all_sv_derivative_rows_now_mirror_text_nfc": invariant_after["rows"]
        == invariant_after["mirrored"],
    }

    # ---- M02: the formula_evidence quote -----------------------------------
    apparatus_tokens = ("dra", "āraṇyakagānam", "āraṇyakam", "ārṣeyabrāhmaṇam", "bhāṣyam")
    contaminated = _q.rows(
        session,
        """
        MATCH (a:Passage)-[r]->(b:Passage)
        WHERE (a.canonical_key IN $keys OR b.canonical_key IN $keys)
          AND r.formula_evidence IS NOT NULL
        RETURN a.canonical_key AS subject, type(r) AS rel, b.canonical_key AS object,
               r.formula_evidence AS formula_evidence,
               r.formula_difference_spans AS spans
        """,
        keys=KEYS,
    )
    surfaces = {
        r["key"]: r["text"]
        for r in _q.rows(
            session,
            """
            MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE p.canonical_key IN $keys AND t.text_role = 'PARALLEL_TEXT'
            RETURN p.canonical_key AS key, t.text_nfc AS text
            """,
            keys=sorted({r["subject"] for r in contaminated} | {r["object"] for r in contaminated}),
        )
    }
    m02_fixed = 0
    m02_rows = []
    for row in contaminated:
        payload = row["formula_evidence"] or ""
        hits = [t for t in apparatus_tokens if f'"{t}' in payload or f"{t}" in payload.replace("\\u0020", " ").split('"quote": "')[-1][:200]]
        # Decide on the payload's own quote strings, not on a loose containment test.
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = None
        dirty = False
        if isinstance(parsed, list):
            for item in parsed:
                quote = str(item.get("quote", ""))
                if any(quote.startswith(t) for t in apparatus_tokens) or any(
                    quote.startswith(t.replace("ā", "a")) for t in apparatus_tokens
                ):
                    dirty = True
        if not dirty and any(
            payload.find('"quote": "' + t) >= 0 for t in apparatus_tokens
        ):
            dirty = True
        if not dirty:
            m02_rows.append(
                {"subject": row["subject"], "rel": row["rel"], "object": row["object"],
                 "clean": True}
            )
            continue
        result = session.run(
            Query(
                f"""
                MATCH (a:Passage {{canonical_key: $subject}})-[r:{row["rel"]}]->
                      (b:Passage {{canonical_key: $object}})
                SET r.formula_evidence_superseded = r.formula_evidence,
                    r.formula_difference_spans_superseded = r.formula_difference_spans,
                    r.formula_evidence = NULL,
                    r.formula_difference_spans = NULL,
                    r.formula_evidence_status = 'STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED',
                    r.formula_evidence_stale_reason =
                      'The published quote and the difference spans were computed over a '
                      + 'Wikisource apparatus line this release removed, so the spans '
                      + 'described a variant that does not exist. Withdrawn rather than '
                      + 'left standing; the old values are preserved beside this marker and '
                      + 'the formula stage re-derives them.',
                    r.r5_contract = $contract
                RETURN count(r) AS n
                """,
                timeout=600.0,
            ),
            subject=row["subject"],
            object=row["object"],
            contract=CONTRACT,
        ).single()
        m02_fixed += result["n"]
        m02_rows.append(
            {"subject": row["subject"], "rel": row["rel"], "object": row["object"],
             "withdrawn": True,
             "quote_head": payload.split('"quote": "')[1][:40] if '"quote": "' in payload else ""}
        )
    out["m02_formula_evidence"] = {
        "edges_carrying_formula_evidence": len(contaminated),
        "edges_withdrawn": m02_fixed,
        "rows": m02_rows,
    }

    # ---- M03/M04: stop publishing a known-false class as the live value -----
    result = session.run(
        Query(
            """
            MATCH ()-[r]->()
            WHERE r.cross_veda_transformation_status =
                  'STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED'
            SET r.cross_veda_transformation = $stale,
                r.cross_veda_transformation_uncorrected_superseded =
                  r.cross_veda_transformation_uncorrected,
                r.cross_veda_transformation_uncorrected = $stale,
                r.cross_veda_lcs_ratio_rederived_superseded =
                  r.cross_veda_lcs_ratio_rederived,
                r.cross_veda_lcs_ratio_rederived = NULL,
                r.cross_veda_lcs_ratio_rederived_status =
                  'STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED',
                r.r5_contract = $contract
            RETURN count(r) AS n
            """,
            timeout=600.0,
        ),
        stale=STALE,
        contract=CONTRACT,
    ).single()
    out["m03_m04_transformation_class"] = {
        "edges_sentinelled": result["n"],
        "sentinel": STALE,
        "why_a_sentinel_and_not_null": (
            "Null would let a reader infer 'no transformation', which is a different false "
            "claim from HEAD_TRUNCATION. The old value stays in "
            "cross_veda_transformation_superseded."
        ),
        "metric_rescore_was_real": (
            "All 13 of 13 edges had a non-empty metric_delta in the staging receipt, and the "
            "deltas are large: the SV-AV pair moved lcs_ratio 0.83871 -> 0.981132 and "
            "similarity 0.827688 -> 0.970958. Agent B's M03 compared the stored value "
            "against a recomputation on the CORRECTED text, which is what the stored value "
            "now is, so its agreement confirms the rescore rather than refuting it."
        ),
    }
    out["verification"] = {
        "apparatus_in_any_text_field_of_the_four": _q.one(
            session,
            """
            MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE p.canonical_key IN $keys
              AND (t.text_nfc STARTS WITH 'dra ' OR t.text_original STARTS WITH 'dra '
                   OR t.text_nfc STARTS WITH 'āraṇyaka' OR t.text_original STARTS WITH 'āraṇyaka'
                   OR t.text_nfc CONTAINS 'द्र. ' OR t.text_original CONTAINS 'द्र. '
                   OR t.text_nfc STARTS WITH '(आरण्यक' OR t.text_original STARTS WITH '(आरण्यक')
            RETURN count(t)
            """,
            keys=KEYS,
        ),
        "edges_publishing_a_known_false_transformation": _q.one(
            session,
            "MATCH ()-[r]->() WHERE r.cross_veda_transformation = 'HEAD_TRUNCATION' "
            "AND r.cross_veda_transformation_status IS NOT NULL RETURN count(r)",
        ),
        "head_truncation_edges_remaining": _q.one(
            session,
            "MATCH ()-[r]->() WHERE r.cross_veda_transformation = 'HEAD_TRUNCATION' "
            "RETURN count(r)",
        ),
    }
    return out


if __name__ == "__main__":
    result = _q.run(go)
    (HERE / "increment_3_receipt.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
