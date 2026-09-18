"""Can the cross-Veda scores be reproduced exactly? Reproduce-then-apply, on the four SV rows.

The staged SV apparatus correction records that derived edges "were built over the apparatus
and should be rebuilt for these four passages". Measuring what that actually costs:

*   The FORMULA layer is provably untouched. A whole-token scan of all 4,825 ``:Formula``
    nodes finds 0 containing any of the apparatus tokens (``dra``, ``āraṇyakagānam``,
    ``ārṣeyabrāhmaṇam``, ``bhāṣyam``, ``āraṇyakam``), and the corrected text is a strict
    suffix of the contaminated text, so the set of token n-grams can only shrink by n-grams
    containing those tokens -- of which none is a formula. No formula gains or loses a member.

*   The CROSS-VEDA layer IS touched, and materially. The stored ``evidence`` quote on
    VG:SV:KAU:CHANDA:P01:D08:V04's reuse edges begins ``draiḍāmagne...`` -- the apparatus is
    inside the published evidence -- and the similarity metrics are computed over it. Worse,
    the NEAR_PARALLEL_OF edge to VSM 12.51 records
    ``cross_veda_transformation: HEAD_TRUNCATION`` with a difference span claiming
    ``इडामग्ने`` was INSERTED. That is a scholarly claim about Vedic textual variation, and
    its whole cause is our own parser attaching a Wikisource apparatus line to the wrong
    verse.

This probe does NOT write. It answers one question: does
``vedagraph.enrich.crossveda.score_pair`` reproduce the stored numbers when fed the
CONTAMINATED text? If it does, the same function on the CORRECTED text is trustworthy. If it
does not, my reimplementation differs from the pipeline's and no edge may be recomputed here.
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))

from vedagraph.enrich.crossveda import score_pair  # noqa: E402
from vedagraph.enrich.surfaces import build_surfaces  # noqa: E402

import _q  # noqa: E402

PROPOSAL = (
    pathlib.Path(__file__).resolve().parents[1]
    / "final_closure_sprint"
    / "agent6"
    / "gap005_sv_apparatus_corrections.json"
)


def go(session):
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    corrections = {c["canonical_key"]: c for c in proposal["corrections"]}
    out: dict[str, object] = {"corrections": sorted(corrections)}

    edges = _q.rows(
        session,
        """
        MATCH (p:Passage)-[r]->(o:Passage)
        WHERE p.canonical_key IN $keys
          AND type(r) IN ['REUSES_TEXT_FROM', 'NEAR_PARALLEL_OF', 'EXACT_PARALLEL_OF', 'VARIANT_OF']
        RETURN p.canonical_key AS subject, type(r) AS rel, o.canonical_key AS object,
               r.lcs_ratio AS lcs_ratio, r.similarity AS similarity,
               r.edit_ratio AS edit_ratio, r.token_jaccard AS token_jaccard,
               r.ngram_jaccard AS ngram_jaccard,
               r.cross_veda_transformation AS transformation
        UNION
        MATCH (o:Passage)-[r]->(p:Passage)
        WHERE p.canonical_key IN $keys
          AND type(r) IN ['REUSES_TEXT_FROM', 'NEAR_PARALLEL_OF', 'EXACT_PARALLEL_OF', 'VARIANT_OF']
        RETURN o.canonical_key AS subject, type(r) AS rel, p.canonical_key AS object,
               r.lcs_ratio AS lcs_ratio, r.similarity AS similarity,
               r.edit_ratio AS edit_ratio, r.token_jaccard AS token_jaccard,
               r.ngram_jaccard AS ngram_jaccard,
               r.cross_veda_transformation AS transformation
        """,
        keys=sorted(corrections),
    )
    out["affected_parallel_edges"] = len(edges)

    keys = sorted({e["subject"] for e in edges} | {e["object"] for e in edges})
    # build_surfaces takes the PRIMARY_TEXT with its script, exactly as the pipeline does.
    # Feeding it the SEARCH_DERIVATIVE would fold an already-folded surface.
    texts = {
        r["key"]: r
        for r in _q.rows(
            session,
            """
            MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE p.canonical_key IN $keys AND t.text_role = 'PRIMARY_TEXT'
            RETURN p.canonical_key AS key, p.veda AS veda, t.script AS script,
                   coalesce(t.text_original, t.text_nfc) AS text
            """,
            keys=keys,
        )
    }
    out["texts_available"] = len(texts)

    checks: list[dict[str, object]] = []
    for e in edges:
        left, right = texts.get(e["subject"]), texts.get(e["object"])
        if not left or not right:
            checks.append({**e, "reproduced": None, "why": "text missing"})
            continue
        scored = score_pair(
            build_surfaces(e["subject"], left["veda"], left["script"], left["text"]),
            build_surfaces(e["object"], right["veda"], right["script"], right["text"]),
        )
        got = {
            "lcs_ratio": round(scored.lcs_ratio, 6),
            "similarity": round(scored.similarity, 6),
            "edit_ratio": round(scored.edit_ratio, 6),
            "token_jaccard": round(scored.token_jaccard, 6),
            "ngram_jaccard": round(scored.ngram_jaccard, 6),
        }
        stored = {
            k: (round(float(e[k]), 6) if e[k] is not None else None)
            for k in ("lcs_ratio", "similarity", "edit_ratio", "token_jaccard", "ngram_jaccard")
        }
        matches = {k: (got[k] == stored[k]) for k in got}
        checks.append(
            {
                "subject": e["subject"],
                "rel": e["rel"],
                "object": e["object"],
                "stored": stored,
                "recomputed_on_contaminated_text": got,
                "field_matches": matches,
                "reproduced": all(matches.values()),
            }
        )

    reproduced = [c for c in checks if c.get("reproduced") is True]
    out["checks"] = checks
    out["edges_checked"] = len([c for c in checks if c.get("reproduced") is not None])
    out["edges_reproduced_exactly"] = len(reproduced)
    out["verdict"] = (
        "REPRODUCED_SAFE_TO_RECOMPUTE"
        if checks and len(reproduced) == len([c for c in checks if c.get("reproduced") is not None])
        else "NOT_REPRODUCED_DO_NOT_RECOMPUTE"
    )
    return out


if __name__ == "__main__":
    result = _q.run(go)
    pathlib.Path(__file__).with_name("probe_sv_rederivation.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
