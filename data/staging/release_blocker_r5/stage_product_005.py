"""Stage GAP-PRODUCT_SURFACE-005: the four apparatus-contaminated Samavedic verses.

The staged proposal at ``data/staging/final_closure_sprint/agent6/
gap005_sv_apparatus_corrections.json`` is complete, evidenced and reversible: each
correction deletes a leading apparatus substring and changes no other codepoint, and each
carries the pinned Wikisource wikitext showing the apparatus standing on its own line AFTER
the preceding verse's number marker. Its own ``not_applied_because`` records a permission
boundary, not missing evidence.

TWO THINGS THE STAGED PROPOSAL MISSED, both measured here before anything is written.

1.  It corrects the TextVersion matching ``old_sha256``, which is the ``PRIMARY_TEXT`` row.
    The apparatus also sits in the ``SEARCH_DERIVATIVE`` row, folded -- ``dra iḍāmagne...``,
    ``āraṇyakagānam ya vtreṣu...`` -- where it is a SEARCHABLE TOKEN. Correcting only the
    primary leaves the search layer matching apparatus words as verse text.

2.  It says derived edges "should be rebuilt". Measuring what that means:

    *   FORMULA: provably untouched. A whole-token scan of all 4,825 ``:Formula`` nodes
        finds 0 containing any apparatus token, and the corrected text is a strict suffix of
        the contaminated text, so the token n-gram set can only lose n-grams containing
        those tokens -- none of which is a formula. No formula gains or loses a member.

    *   CROSS-VEDA: touched, and materially. 13 parallel edges carry similarity metrics and
        published ``evidence`` quotes computed over the apparatus, and the SV-YV near
        parallel VG:SV:KAU:CHANDA:P01:D08:V04 <-> VSM 12.51 is classed
        ``cross_veda_transformation: HEAD_TRUNCATION`` with a difference span claiming
        ``इडामग्ने`` was inserted. ``HEAD_TRUNCATION`` occurs exactly TWICE in the whole
        6,596-row transformation artifact, so one of the two instances of that class in this
        corpus is our own parser attaching a Wikisource apparatus line to the wrong verse.

REPRODUCE-THEN-APPLY. ``vedagraph.enrich.crossveda.score_pair`` fed the primary text
reproduced all five stored metrics on 13 of 13 edges, exactly, to six decimal places. That
is what licenses recomputing them on the corrected text. The transformation CLASS is not
recomputed: its 16-value vocabulary lives in the cross-Veda staging build and not in
``src``, and inferring the classifier would be a guess. Those fields are marked stale with
the old value preserved, which discloses the defect instead of publishing a false value as
current.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))

from vedagraph.enrich.crossveda import score_pair  # noqa: E402
from vedagraph.enrich.surfaces import build_surfaces  # noqa: E402
from vedagraph.normalize import (  # noqa: E402
    ComparisonForm,
    comparison_form,
    normalize_nfc,
)

import _q  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # release_blocker_r5 -> staging -> data -> VedaGraph
PROPOSAL = HERE.parents[0] / "final_closure_sprint" / "agent6" / "gap005_sv_apparatus_corrections.json"
CANONICAL = ROOT / "data" / "canonical" / "samaveda_arcika_v1"
BACKLOG_ID = "SV-APPARATUS-LIFT-01"
CONTRACT = "VG:R5_CLOSURE:V1"

PARALLEL_TYPES = ("REUSES_TEXT_FROM", "NEAR_PARALLEL_OF", "EXACT_PARALLEL_OF", "VARIANT_OF")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def go(session) -> dict[str, Any]:
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    corrections = {c["canonical_key"]: c for c in proposal["corrections"]}
    keys = sorted(corrections)
    out: dict[str, Any] = {
        "gap_id": "GAP-PRODUCT_SURFACE-005",
        "backlog_id": BACKLOG_ID,
        "proposal": str(PROPOSAL.relative_to(ROOT)).replace("\\", "/"),
        "keys": keys,
    }

    # ---- 1. verify the live text still matches what the proposal was written against ----
    live = _q.rows(
        session,
        """
        MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
        WHERE p.canonical_key IN $keys
        RETURN p.canonical_key AS key, p.veda AS veda, t.text_id AS text_id,
               t.text_version_id AS artifact_id,
               t.text_role AS role, t.script AS script, t.text_nfc AS text_nfc,
               t.content_sha256 AS sha
        ORDER BY key, role
        """,
        keys=keys,
    )
    text_updates: list[dict[str, Any]] = []
    preflight: list[dict[str, Any]] = []
    surface_proofs: list[dict[str, Any]] = []
    surface_failures: list[dict[str, Any]] = []
    corrected_primary: dict[str, str] = {}
    # PRIMARY_TEXT first, so a derivative row can read its own primary from `live`.
    live = sorted(live, key=lambda r: (r["key"], r["role"] != "PRIMARY_TEXT"))
    for row in live:
        corr = corrections[row["key"]]
        apparatus = corr["apparatus_removed"]["substring"]
        if row["role"] == "PRIMARY_TEXT":
            matches_old = row["sha"] == corr["current"]["content_sha256"]
            starts = (row["text_nfc"] or "").startswith(apparatus)
            new_text = corr["proposed"]["text_nfc"]
            declared_new_sha = corr["proposed"]["content_sha256"]
            recomputed = _sha256(new_text)
            preflight.append(
                {
                    "key": row["key"],
                    "role": row["role"],
                    "live_sha_matches_proposal_current": matches_old,
                    "live_text_starts_with_the_apparatus": starts,
                    "proposal_new_sha256_reproduces": recomputed == declared_new_sha,
                    "recomputed_new_sha256": recomputed,
                    "declared_new_sha256": declared_new_sha,
                }
            )
            corrected_primary[row["key"]] = new_text
            text_updates.append(
                {
                    "text_id": row["text_id"],
                    "artifact_id": row["artifact_id"],
                    "canonical_key": row["key"],
                    "role": row["role"],
                    "old_sha256": row["sha"],
                    "new_text_nfc": new_text,
                    "new_sha256": recomputed,
                    "codepoints_removed": corr["apparatus_removed"]["length_codepoints"],
                }
            )
        else:
            # Re-derive the non-primary surface from the CORRECTED primary through the
            # repository's own comparison_form, never by string-surgery on the folded text:
            # the folded surface carries private-use sentinels and an edit there would be
            # an edit to a surface nobody can audit.
            corr_row = corrections[row["key"]]
            primary = next(r for r in live if r["key"] == row["key"] and r["role"] == "PRIMARY_TEXT")
            # WHICH surface this row holds is established by REPRODUCTION, not by guessing.
            # Rebuild every surface from the CONTAMINATED primary and find the one that
            # equals what is stored; then rebuild that same surface from the corrected
            # primary. An earlier version assumed sandhi_insensitive and would have replaced
            # a space-separated surface with a boundary-free one -- silently destroying the
            # word divisions the token matcher depends on.
            contaminated = build_surfaces(
                row["key"],
                primary["veda"],
                primary["script"],
                primary["text_nfc"],
            )
            candidates = {
                "unicode_normalized": contaminated.unicode_normalized,
                "punctuation_normalized": contaminated.punctuation_normalized,
                "accent_insensitive": contaminated.accent_insensitive,
                "script_folded": contaminated.script_folded,
                "sandhi_insensitive": contaminated.sandhi_insensitive,
            }
            reproducing = [name for name, value in candidates.items() if value == row["text_nfc"]]
            if len(reproducing) != 1:
                surface_failures.append(
                    {
                        "key": row["key"],
                        "role": row["role"],
                        "reproducing_surfaces": reproducing,
                        "why": (
                            "the stored text matches no single surface, so which surface to "
                            "re-derive cannot be established. Refusing to guess."
                        ),
                    }
                )
                continue
            surface_name = reproducing[0]
            corrected = build_surfaces(
                row["key"], primary["veda"], primary["script"], corr_row["proposed"]["text_nfc"]
            )
            new_text = getattr(corrected, surface_name)
            surface_proofs.append(
                {
                    "key": row["key"],
                    "role": row["role"],
                    "surface_established_by_reproduction": surface_name,
                }
            )
            text_updates.append(
                {
                    "text_id": row["text_id"],
                    "artifact_id": row["artifact_id"],
                    "canonical_key": row["key"],
                    "role": row["role"],
                    "old_sha256": row["sha"],
                    "new_text_nfc": new_text,
                    "new_sha256": _sha256(new_text),
                    "rederived_surface": surface_name,
                    "rederived_from": "the corrected PRIMARY_TEXT via enrich.surfaces",
                }
            )
    out["preflight"] = preflight
    out["preflight_all_pass"] = all(
        p["live_sha_matches_proposal_current"]
        and p["live_text_starts_with_the_apparatus"]
        and p["proposal_new_sha256_reproduces"]
        for p in preflight
    )
    out["text_version_updates"] = text_updates
    out["derivative_surface_proofs"] = surface_proofs
    out["derivative_surface_failures"] = surface_failures

    # ---- 2. the cross-Veda edges -------------------------------------------
    edges = _q.rows(
        session,
        f"""
        MATCH (a:Passage)-[r]->(b:Passage)
        WHERE (a.canonical_key IN $keys OR b.canonical_key IN $keys)
          AND type(r) IN {list(PARALLEL_TYPES)!r}
        RETURN a.canonical_key AS subject, b.canonical_key AS object, type(r) AS rel,
               r.lcs_ratio AS lcs_ratio, r.similarity AS similarity, r.edit_ratio AS edit_ratio,
               r.token_jaccard AS token_jaccard, r.ngram_jaccard AS ngram_jaccard,
               r.evidence AS evidence, r.cross_veda_transformation AS transformation,
               r.cross_veda_transformation_basis AS transformation_basis,
               r.parallel_id AS parallel_id
        ORDER BY subject, rel, object
        """,
        keys=keys,
    )
    all_keys = sorted({e["subject"] for e in edges} | {e["object"] for e in edges})
    primaries = {
        r["key"]: r
        for r in _q.rows(
            session,
            """
            MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE p.canonical_key IN $keys AND t.text_role = 'PRIMARY_TEXT'
            RETURN p.canonical_key AS key, p.veda AS veda, t.script AS script,
                   coalesce(t.text_original, t.text_nfc) AS text
            """,
            keys=all_keys,
        )
    }

    def surfaces_for(key: str):
        row = primaries[key]
        text = corrected_primary.get(key, row["text"])
        return build_surfaces(key, row["veda"], row["script"], text)

    edge_updates: list[dict[str, Any]] = []
    reproduction: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for e in edges:
        if e["subject"] not in primaries or e["object"] not in primaries:
            skipped.append(
                {
                    "subject": e["subject"],
                    "rel": e["rel"],
                    "object": e["object"],
                    "why": (
                        "one end carries no PRIMARY_TEXT TextVersion, so the pair cannot be "
                        "rescored. Reported rather than skipped silently."
                    ),
                    "subject_has_primary": e["subject"] in primaries,
                    "object_has_primary": e["object"] in primaries,
                }
            )
            continue
        before = score_pair(
            build_surfaces(
                e["subject"],
                primaries[e["subject"]]["veda"],
                primaries[e["subject"]]["script"],
                primaries[e["subject"]]["text"],
            ),
            build_surfaces(
                e["object"],
                primaries[e["object"]]["veda"],
                primaries[e["object"]]["script"],
                primaries[e["object"]]["text"],
            ),
        )
        stored = {
            k: (round(float(e[k]), 6) if e[k] is not None else None)
            for k in ("lcs_ratio", "similarity", "edit_ratio", "token_jaccard", "ngram_jaccard")
        }
        rebuilt = {
            "lcs_ratio": round(before.lcs_ratio, 6),
            "similarity": round(before.similarity, 6),
            "edit_ratio": round(before.edit_ratio, 6),
            "token_jaccard": round(before.token_jaccard, 6),
            "ngram_jaccard": round(before.ngram_jaccard, 6),
        }
        reproduced = rebuilt == stored
        reproduction.append(
            {
                "subject": e["subject"],
                "rel": e["rel"],
                "object": e["object"],
                "reproduced_on_contaminated_text": reproduced,
                "stored": stored,
                "recomputed": rebuilt,
            }
        )
        if not reproduced:
            continue
        left, right = surfaces_for(e["subject"]), surfaces_for(e["object"])
        after = score_pair(left, right)
        new_props = {
            "lcs_ratio": round(after.lcs_ratio, 6),
            "similarity": round(after.similarity, 6),
            "score": round(after.similarity, 6),
            "edit_ratio": round(after.edit_ratio, 6),
            "token_jaccard": round(after.token_jaccard, 6),
            "ngram_jaccard": round(after.ngram_jaccard, 6),
            "cross_veda_stored_similarity": round(after.similarity, 6),
            "evidence": json.dumps(
                [
                    {
                        "locator": e["subject"],
                        "quote": left.sandhi_insensitive,
                        "surface": "SANDHI_INSENSITIVE",
                    },
                    {
                        "locator": e["object"],
                        "quote": right.sandhi_insensitive,
                        "surface": "SANDHI_INSENSITIVE",
                    },
                ],
                ensure_ascii=False,
            ),
            "cross_veda_metrics_recomputed_by": "R5 " + BACKLOG_ID,
            "cross_veda_metrics_recomputed_because": (
                "The stored metrics and the published evidence quote were computed over a "
                "Wikisource apparatus line the parser attached to this verse. Recomputed by "
                "vedagraph.enrich.crossveda.score_pair, which reproduced every stored metric "
                "exactly on the contaminated text before being trusted on the corrected one."
            ),
            "r5_contract": CONTRACT,
        }
        if e["transformation"] is not None:
            new_props |= {
                "cross_veda_transformation_status": "STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED",
                "cross_veda_transformation_superseded": e["transformation"],
                "cross_veda_transformation_superseded_basis": e["transformation_basis"],
                "cross_veda_transformation_stale_reason": (
                    "The class was derived from a text carrying an apparatus prefix that has "
                    "now been removed. The 16-value transformation vocabulary is produced by "
                    "the cross-Veda staging build and not by anything in src, so a value "
                    "inferred here would be a guess. The old value is preserved beside this "
                    "marker rather than published as current, and the class is re-derived "
                    "when the cross-Veda stage next runs."
                ),
            }
        edge_updates.append(
            {
                "subject": e["subject"],
                "object": e["object"],
                "rel": e["rel"],
                "parallel_id": e["parallel_id"],
                "properties": new_props,
                "metric_delta": {
                    k: [stored[k], new_props[k]] for k in stored if stored[k] != new_props[k]
                },
            }
        )

    out["parallel_edges_found"] = len(edges)
    out["parallel_edges_reproduced"] = sum(
        1 for r in reproduction if r["reproduced_on_contaminated_text"]
    )
    out["parallel_edge_reproduction"] = reproduction
    out["parallel_edges_skipped"] = skipped
    out["parallel_edges_accounted_for"] = len(reproduction) + len(skipped) == len(edges)
    out["parallel_edge_updates"] = edge_updates
    out["transformation_classes_marked_stale"] = sum(
        1 for u in edge_updates if "cross_veda_transformation_status" in u["properties"]
    )

    # ---- 3. formula layer: proof, not a rebuild ----------------------------
    # Derived as the token DELTA between the contaminated and the corrected search surface,
    # not by folding the apparatus substring on its own. An earlier version of this proof
    # passed the script code "DEVA" where the store uses "Devanagari", so build_surfaces
    # never transliterated, the tokens came out in Devanagari, and the scan against IAST
    # formula text could not have matched anything -- a validator that silently skips,
    # reporting 0 for the wrong reason. The delta needs no script argument at all.
    apparatus_tokens_by_key: dict[str, list[str]] = {}
    for row in live:
        if row["role"] != "SEARCH_DERIVATIVE":
            continue
        # Keyed on text_id. text_version_id is the ARTIFACT id: 58,786 TextVersion nodes
        # share just 12 of them and the two in play here cover 1,844 nodes each, so a lookup
        # (or a Cypher SET) keyed on it reaches every row of the artifact instead of one
        # verse. An earlier version of this block did exactly that and silently handed three
        # of the four rows a fourth row's text, which is why the token delta came back as
        # the whole verse. text_id is unique: 58,786 distinct over 58,786 nodes.
        after = next(
            u["new_text_nfc"] for u in text_updates if u["text_id"] == row["text_id"]
        )
        before_tokens = (row["text_nfc"] or "").split()
        after_tokens = after.split()
        apparatus_tokens_by_key[row["key"]] = sorted(set(before_tokens) - set(after_tokens))
    apparatus_tokens = sorted({t for v in apparatus_tokens_by_key.values() for t in v})
    formulas = _q.rows(session, "MATCH (f:Formula) RETURN f.formula_normalized AS norm")
    contaminated = [
        f["norm"] for f in formulas if set((f["norm"] or "").split()) & set(apparatus_tokens)
    ]
    out["formula_layer"] = {
        "apparatus_tokens": apparatus_tokens,
        "apparatus_tokens_by_key": apparatus_tokens_by_key,
        "apparatus_tokens_are_in_the_same_surface_as_formula_normalized": bool(apparatus_tokens)
        and not any(ord(ch) > 0x0900 and ord(ch) < 0x0980 for t in apparatus_tokens for ch in t),
        "formulas_scanned": len(formulas),
        "formulas_containing_an_apparatus_token": len(contaminated),
        "match_is_whole_token_not_substring": True,
        "why_no_rebuild": (
            "0 of the formulas hold an apparatus token, and the corrected text is a strict "
            "suffix of the contaminated text, so the token n-gram set can only lose n-grams "
            "that contain one. No formula can gain or lose a member. Measured on whole tokens: "
            "a substring test reports 30+ false hits because 'dra' sits inside 'indra'."
        ),
    }

    # ---- 4. canonical artifact + manifest ---------------------------------
    tv_path = CANONICAL / "text_versions.jsonl"
    rb_path = CANONICAL / "referent_bindings.jsonl"
    manifest_path = CANONICAL / "manifest.json"
    old_shas = {c["current"]["content_sha256"] for c in corrections.values()}
    rb_rows = [
        json.loads(line)
        for line in rb_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rb_hits = [
        r
        for r in rb_rows
        if any(str(v) in old_shas for v in r.values() if isinstance(v, str))
    ]
    out["canonical_artifact"] = {
        "text_versions": str(tv_path.relative_to(ROOT)).replace("\\", "/"),
        "referent_bindings": str(rb_path.relative_to(ROOT)).replace("\\", "/"),
        "manifest": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "manifest_is_tracked_in_git": True,
        "referent_binding_rows_keyed_on_an_old_sha256": len(rb_hits),
        "referent_binding_keys": sorted({k for r in rb_hits for k in r}),
    }

    out["promised"] = {
        "text_version_nodes_updated": len(text_updates),
        "parallel_edges_updated": len(edge_updates),
        "nodes_created": 0,
        "relationships_created": 0,
        "relationships_deleted": 0,
        "canonical_records_updated": len(corrections),
        "referent_binding_records_updated": len(rb_hits),
    }
    return out


if __name__ == "__main__":
    result = _q.run(go)
    (HERE / "staged_product_005.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
