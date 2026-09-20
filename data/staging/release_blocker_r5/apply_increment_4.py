"""R5 increment 4: the one edge that carried the false claim, and that my own filter dropped.

MY DEFECT, found by following Agent B's line of attack past where Agent B stopped.

The whole reason GAP-PRODUCT_SURFACE-005's cross-Veda consequence mattered was ONE edge:
``VG:SV:KAU:CHANDA:P01:D08:V04`` <-> ``VSM 12.51``, classed
``cross_veda_transformation = HEAD_TRUNCATION`` with a difference span claiming ``इडामग्ने``
was inserted -- a published claim about Vedic textual variation whose entire cause was our
parser attaching a Wikisource apparatus line to the wrong verse, and one of only TWO
HEAD_TRUNCATION rows in all 6,596.

``stage_product_005.py`` selected edges where BOTH ends carry a ``PRIMARY_TEXT``
TextVersion. The Yajurveda does not use that role: its 1,975 source rows are
``EXTRACTED_FROM_CONTAINER``, because the Vajasaneyi text is lifted out of a container.
So the edge was skipped -- and to my staging's credit it was skipped LOUDLY, recorded in
``parallel_edges_skipped`` with ``object_has_primary: false`` and an accounting check that
13 + 1 = 14. I read that field, wrote "13 of 14 reproduced" into the receipt, and then did
not go back for the 1. The ruling and the cross-veda.md note both read as though all of it
had been handled.

Increment 3 then sentinelled the 13 that HAD been rescored and left this one reading
``HEAD_TRUNCATION`` with a null status: the only edge whose class was known false was the
only one still publishing it.

REPRODUCE-THEN-APPLY, per side, with the role each corpus actually uses:

    SV  PRIMARY_TEXT                 Devanagari
    YV  EXTRACTED_FROM_CONTAINER     Devanagari

The stored metrics must reproduce from the CONTAMINATED SV text against the YV text before
the corrected figures are trusted. If they do not, nothing is written.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))

from neo4j import Query  # noqa: E402

from vedagraph.enrich.crossveda import score_pair  # noqa: E402
from vedagraph.enrich.surfaces import build_surfaces  # noqa: E402

import _q  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
CONTRACT = "VG:R5_CLOSURE:V1"
STALE = "STALE_PENDING_REDERIVATION"

#: The source-text role each corpus actually uses. Measured, not assumed: SV and RV and AV
#: carry PRIMARY_TEXT; the Yajurveda carries EXTRACTED_FROM_CONTAINER on all 1,975 and
#: PRIMARY_TEXT on none.
SOURCE_ROLE_BY_VEDA = {
    "RV": "PRIMARY_TEXT",
    "SV": "PRIMARY_TEXT",
    "AV": "PRIMARY_TEXT",
    "YV": "EXTRACTED_FROM_CONTAINER",
}

METRICS = ("lcs_ratio", "similarity", "edit_ratio", "token_jaccard", "ngram_jaccard")


def go(session) -> dict[str, Any]:
    out: dict[str, Any] = {
        "artifact": "R5_INCREMENT_4",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    proposal = json.loads(
        (
            HERE.parents[0]
            / "final_closure_sprint"
            / "agent6"
            / "gap005_sv_apparatus_corrections.json"
        ).read_text(encoding="utf-8")
    )
    corrected = {
        c["canonical_key"]: c["proposed"]["text_nfc"] for c in proposal["corrections"]
    }
    contaminated_text = {
        c["canonical_key"]: c["current"]["text_nfc"] for c in proposal["corrections"]
    }

    # Every parallel edge touching the four, with NO role assumption in the join.
    edges = _q.rows(
        session,
        """
        MATCH (a:Passage)-[r]->(b:Passage)
        WHERE (a.canonical_key IN $keys OR b.canonical_key IN $keys)
          AND type(r) IN ['REUSES_TEXT_FROM','NEAR_PARALLEL_OF','EXACT_PARALLEL_OF','VARIANT_OF']
        RETURN a.canonical_key AS subject, a.veda AS subject_veda,
               b.canonical_key AS object, b.veda AS object_veda, type(r) AS rel,
               r.cross_veda_transformation AS transformation,
               r.cross_veda_transformation_status AS status,
               r.lcs_ratio AS lcs_ratio, r.similarity AS similarity,
               r.edit_ratio AS edit_ratio, r.token_jaccard AS token_jaccard,
               r.ngram_jaccard AS ngram_jaccard
        ORDER BY subject, rel, object
        """,
        keys=sorted(corrected),
    )
    out["parallel_edges_total"] = len(edges)
    outstanding = [e for e in edges if e["status"] is None]
    out["edges_left_unhandled_by_increment_1"] = [
        {"subject": e["subject"], "rel": e["rel"], "object": e["object"],
         "transformation": e["transformation"]}
        for e in outstanding
    ]

    # Source text per key, by the role its corpus actually uses.
    keys = sorted({e["subject"] for e in outstanding} | {e["object"] for e in outstanding})
    texts: dict[str, dict[str, Any]] = {}
    for key in keys:
        veda = next(
            e["subject_veda"] if e["subject"] == key else e["object_veda"]
            for e in outstanding
            if key in (e["subject"], e["object"])
        )
        role = SOURCE_ROLE_BY_VEDA[veda]
        rows = _q.rows(
            session,
            """
            MATCH (p:Passage {canonical_key: $key})-[:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE t.text_role = $role
            RETURN t.script AS script, coalesce(t.text_original, t.text_nfc) AS text
            """,
            key=key,
            role=role,
        )
        if not rows:
            raise SystemExit(f"{key}: no {role} TextVersion; refusing to guess a role")
        texts[key] = {"veda": veda, "role": role, **rows[0]}
    out["source_roles_used"] = {k: {"veda": v["veda"], "role": v["role"]} for k, v in texts.items()}

    applied: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for edge in outstanding:
        left, right = texts[edge["subject"]], texts[edge["object"]]
        # the text as it WAS, for the reproduction control
        left_before = contaminated_text.get(edge["subject"], left["text"])
        right_before = contaminated_text.get(edge["object"], right["text"])
        before = score_pair(
            build_surfaces(edge["subject"], left["veda"], left["script"], left_before),
            build_surfaces(edge["object"], right["veda"], right["script"], right_before),
        )
        stored = {m: (round(float(edge[m]), 6) if edge[m] is not None else None) for m in METRICS}
        rebuilt = {
            "lcs_ratio": round(before.lcs_ratio, 6),
            "similarity": round(before.similarity, 6),
            "edit_ratio": round(before.edit_ratio, 6),
            "token_jaccard": round(before.token_jaccard, 6),
            "ngram_jaccard": round(before.ngram_jaccard, 6),
        }
        if rebuilt != stored:
            refused.append(
                {
                    "subject": edge["subject"],
                    "rel": edge["rel"],
                    "object": edge["object"],
                    "stored": stored,
                    "recomputed_on_contaminated_text": rebuilt,
                    "why": (
                        "score_pair does not reproduce the stored metrics on the text as it "
                        "was, so it cannot be trusted on the text as it is. Nothing written."
                    ),
                }
            )
            continue

        after = score_pair(
            build_surfaces(
                edge["subject"],
                left["veda"],
                left["script"],
                corrected.get(edge["subject"], left["text"]),
            ),
            build_surfaces(
                edge["object"],
                right["veda"],
                right["script"],
                corrected.get(edge["object"], right["text"]),
            ),
        )
        new_left = build_surfaces(
            edge["subject"], left["veda"], left["script"],
            corrected.get(edge["subject"], left["text"]),
        )
        new_right = build_surfaces(
            edge["object"], right["veda"], right["script"],
            corrected.get(edge["object"], right["text"]),
        )
        props = {
            "lcs_ratio": round(after.lcs_ratio, 6),
            "similarity": round(after.similarity, 6),
            "score": round(after.similarity, 6),
            "edit_ratio": round(after.edit_ratio, 6),
            "token_jaccard": round(after.token_jaccard, 6),
            "ngram_jaccard": round(after.ngram_jaccard, 6),
            "cross_veda_stored_similarity": round(after.similarity, 6),
            "evidence": json.dumps(
                [
                    {"locator": edge["subject"], "quote": new_left.sandhi_insensitive,
                     "surface": "SANDHI_INSENSITIVE"},
                    {"locator": edge["object"], "quote": new_right.sandhi_insensitive,
                     "surface": "SANDHI_INSENSITIVE"},
                ],
                ensure_ascii=False,
            ),
            "cross_veda_metrics_recomputed_by": "R5 SV-APPARATUS-LIFT-01 increment 4",
            "cross_veda_metrics_recomputed_because": (
                "This edge was skipped by increment 1, whose join required a PRIMARY_TEXT "
                "TextVersion at both ends -- a role the Yajurveda does not use. It was the "
                "ONE edge whose transformation class was known false, so the only edge still "
                "publishing HEAD_TRUNCATION was the only one that mattered."
            ),
            "cross_veda_transformation_superseded": edge["transformation"],
            "cross_veda_transformation": STALE,
            "cross_veda_transformation_status": "STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED",
            "cross_veda_transformation_stale_reason": (
                "The class was HEAD_TRUNCATION and the truncated head was a Wikisource "
                "apparatus line belonging to the preceding verse, not a textual variant. "
                "One of only two HEAD_TRUNCATION rows in the whole 6,596-row transformation "
                "artifact. The 16-value vocabulary lives in the cross-Veda staging build and "
                "not in src, so a replacement class inferred here would be a guess; the old "
                "value is preserved and the class is re-derived when that stage next runs."
            ),
            "r5_contract": CONTRACT,
        }
        record = session.run(
            Query(
                f"""
                MATCH (a:Passage {{canonical_key: $subject}})-[r:{edge["rel"]}]->
                      (b:Passage {{canonical_key: $object}})
                SET r += $props
                SET r.formula_evidence_superseded =
                      coalesce(r.formula_evidence_superseded, r.formula_evidence),
                    r.formula_difference_spans_superseded =
                      coalesce(r.formula_difference_spans_superseded,
                               r.formula_difference_spans),
                    r.formula_evidence = NULL,
                    r.formula_difference_spans = NULL,
                    r.formula_evidence_status =
                      CASE WHEN r.formula_evidence_superseded IS NULL THEN NULL
                           ELSE 'STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED' END
                RETURN count(r) AS n
                """,
                timeout=600.0,
            ),
            subject=edge["subject"],
            object=edge["object"],
            props=props,
        ).single()
        applied.append(
            {
                "subject": edge["subject"],
                "rel": edge["rel"],
                "object": edge["object"],
                "edges_written": record["n"],
                "reproduced_on_contaminated_text": True,
                "transformation_was": edge["transformation"],
                "metric_delta": {m: [stored[m], props[m]] for m in METRICS if stored[m] != props[m]},
            }
        )

    out["applied"] = applied
    out["refused"] = refused
    out["verification"] = {
        "head_truncation_edges_remaining_anywhere": _q.one(
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
            keys=sorted(corrected),
        ),
        "parallel_edges_on_the_four_without_a_status": _q.one(
            session,
            """
            MATCH (a:Passage)-[r]->(b:Passage)
            WHERE (a.canonical_key IN $keys OR b.canonical_key IN $keys)
              AND type(r) IN ['REUSES_TEXT_FROM','NEAR_PARALLEL_OF','EXACT_PARALLEL_OF','VARIANT_OF']
              AND r.cross_veda_transformation_status IS NULL
            RETURN count(r)
            """,
            keys=sorted(corrected),
        ),
        "edges_publishing_a_contaminated_quote": _q.one(
            session,
            """
            MATCH ()-[r]->()
            WHERE r.evidence CONTAINS 'draiḍāmagne'
               OR coalesce(r.formula_evidence,'') CONTAINS 'draiḍāmagne'
            RETURN count(r)
            """,
        ),
    }
    return out


if __name__ == "__main__":
    result = _q.run(go)
    (HERE / "increment_4_receipt.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
