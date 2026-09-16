#!/usr/bin/env python3
"""Gate C -- adversarial falsification of the rows that survived Gate B.

Gate B asked whether a row is entitled to make an assertion. Gate C asks the opposite
question about the same row: granting that it is well-formed, how could it still be wrong?
So nothing here looks for confirmation. Each check is an attempt to produce a competing
explanation of the row's own evidence -- a neighbouring verse that fits the translation as
well or better, a source-local index that was minted rather than read, a rendering borrowed
from another corpus and presented as this corpus's own, a literal that is page furniture or
an editorial cross-reference rather than a translation.

Two rules this file follows deliberately.

**Translation similarity never decides anything.** It is used only to *raise* a row for
inspection. The campaign has already been bitten by normalised similarity standing in for
identity, and an English rendering of a Vedic verse resembles the rendering of its
neighbours for reasons that have nothing to do with which verse it is. So where a shift
attack finds a neighbour that scores as well as the claimed target, the row is marked
ambiguous and sent to a human, not reassigned.

**A systemic defect is reported as systemic.** If a defect is a property of how a source's
rows were generated rather than of one row, it is named at the source level and the whole
population is classified together. The campaign's instruction for that case is to fix the
generator and regenerate the population -- which is not available here, because the
generator is absent from version control at the manifest's own declared commit. That
unavailability is itself recorded as a finding rather than worked around, because a
population that cannot be regenerated also cannot be cleared by a code fix.
"""

from __future__ import annotations

import glob
import json
import os
import pathlib
import re
import sys
from collections import Counter, defaultdict

from gate_bc_common import PACKET, REPO, STAGING, load_rows, write_json, write_jsonl
from gate_bc_textfold import fold_english, fold_sanskrit, sandhi_insensitive, token_dice

CACHE = pathlib.Path(
    r"C:\Users\HKM49\AppData\Local\Temp\claude\d--VedaGraph"
    r"\9811a2e5-56d7-4f68-aa33-48f350e56c58\scratchpad\graph_facts.json"
)

CATEGORIES = (
    "C_PASS",
    "C_FAIL_WRONG_TARGET",
    "C_FAIL_DUPLICATE_GENERATION",
    "C_FAIL_CROSS_CORPUS_CONTAMINATION",
    "C_FAIL_UNVERIFIED_FORCED_ADDRESS",
    "C_FAIL_SOURCE_GRANULARITY",
    "C_FAIL_ARCHIVE_EVIDENCE",
    "C_WITHHOLD_REUSED_RENDERING_POLICY",
    "C_WITHHOLD_AMBIGUOUS",
)
PRECEDENCE = (
    "C_FAIL_WRONG_TARGET",
    "C_FAIL_ARCHIVE_EVIDENCE",
    "C_FAIL_SOURCE_GRANULARITY",
    "C_FAIL_DUPLICATE_GENERATION",
    "C_FAIL_UNVERIFIED_FORCED_ADDRESS",
    "C_FAIL_CROSS_CORPUS_CONTAMINATION",
    "C_WITHHOLD_REUSED_RENDERING_POLICY",
    "C_WITHHOLD_AMBIGUOUS",
)

# An editorial cross-reference is not a translation. Griffith abbreviates repeated liturgical
# formulae as "etc., as in XXII. 11", and a row that stages that string asserts it as the
# meaning of the verse. Gate B's literal checks passed it: it is long enough, it is prose,
# it has no markup. Only an adversarial reading catches it.
CROSS_REFERENCE = re.compile(
    r"\betc\.?,?\s*as in\b|\bas in\s+[IVXLC]+\.\s*\d|\bmutatis mutandis\b|"
    r"\bas (?:above|before) in\b|\bsee\s+[IVXLC]+\.\s*\d",
    re.I,
)
# Griffith renders sexually explicit passages into Latin rather than English, by Victorian
# convention. Those rows are genuine Griffith text, but they are not English, and every one
# of them declares language "en".
LATIN_MARKERS = frozenset(
    """est et te me magni bona quae qui cum non sed atque ad de ex ut sunt eius mihi tibi nos
    vos futue mulcta vacca femina viri digito producit obtineat opprimit pinguis macrum
    vanankaram marmelos aegle mentula mentulae membrum femora femoribus penis pene vaginam
    juvenis quum sederit fortis vero ille cujus laxe dependet inter tanquam testi faverunt
    intumescenti ostentat delectata arnica amice infelix fortunatus certe ubique glomerata
    ficus magna magnus flava puollula opere perfecto procurrit alloquitur silvae ignis
    inflammatur ardent mea membra fauste infixus arboris fructu celeriter fruamur nescimus
    bestia pudendum muliebre capite gerat circumcurrit fuste gallum solutus adveniens vocem
    edidit percute medium femur paratum cupido cepit illius tauri despicit utrum hinc illinc
    aliqua parte nata detrahit inutilis labor dii favent omnes aemulos aemulas vincamus
    superemus hac centum artium pugna duas partes convenientes""".split()
)
ENGLISH_FUNCTION = frozenset(
    """the and of to in for with be is are was were thou thy thee he she they we our you not
    that this all from as at by on or his her them him me my o may let us who which art hath
    have has do does did shall will their there then when where what who whom your""".split()
)


def detect_language(text: str) -> dict:
    words = re.findall(r"[A-Za-z']+", (text or "").lower())
    if not words:
        return {"tokens": 0, "verdict": "EMPTY"}
    en = sum(1 for w in words if w in ENGLISH_FUNCTION) / len(words)
    la = sum(1 for w in words if w in LATIN_MARKERS) / len(words)
    verdict = "ENGLISH"
    if la >= 0.05 and la > en:
        verdict = "LATIN"
    elif la >= 0.10:
        verdict = "MIXED_LATIN"
    elif en < 0.04 and len(words) >= 8:
        verdict = "NOT_RECOGNISABLY_ENGLISH"
    return {
        "tokens": len(words),
        "english_function_word_density": round(en, 4),
        "latin_marker_density": round(la, 4),
        "verdict": verdict,
    }


def primary_sanskrit(versions: list[dict]) -> dict | None:
    for t in versions or []:
        if t.get("role") == "PRIMARY_TEXT":
            return t
    return (versions or [None])[0]


def main() -> int:
    facts = json.loads(CACHE.read_text(encoding="utf-8"))
    texts, translations = facts["texts"], facts["translations"]
    siblings, passages = facts["siblings"], facts["passages"]
    graph_rels = facts["graph_relations"]

    rows = {r["_staged_row_id"]: r for r in load_rows()}
    gate_b = [
        json.loads(line)
        for line in (PACKET / "gate_b_rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    b_by_id = {r["staged_row_id"]: r for r in gate_b}
    b_pass = [r for r in gate_b if r["gate_b_category"] == "B_PASS"]

    yv_verif = {}
    p = PACKET / "yv_source_verification.json"
    if p.exists():
        yv_verif = {
            r["canonical_key"]: r for r in json.loads(p.read_text(encoding="utf-8"))["rows"]
        }

    # AV archive page proofs, for C5.
    proofs = json.loads((STAGING / "proofs" / "source_pages.json").read_text(encoding="utf-8"))
    page_by_sha = {pg["sha256"]: pg for pg in proofs["pages"]}
    page_by_url = {pg["request_url"]: pg for pg in proofs["pages"]}

    # Coverage bookkeeping, for the same reason Gate B has it. The first run of this file
    # reported the off-by-one attack as finding zero suspicious rows, which read as a clean
    # result and was actually a vacuous one: the fact cache held no translations for the
    # targets' canonical neighbours, so the check compared every row against nothing. A
    # check that evaluated no rows must report that, not a zero.
    cov: dict[str, dict[str, int]] = defaultdict(lambda: {"eligible": 0, "evaluated": 0})

    def covered(name: str, eligible: bool, evaluated: bool) -> None:
        if eligible:
            cov[name]["eligible"] += 1
            if evaluated:
                cov[name]["evaluated"] += 1

    findings: list[dict] = []

    def finding(check, severity, scope, summary, **kw):
        findings.append(
            {"check": check, "severity": severity, "scope": scope, "summary": summary, **kw}
        )

    # =====================================================================================
    # C2 / C7 population-level: was any source's addressing minted from a local index?
    # =====================================================================================
    by_source = defaultdict(list)
    for r in gate_b:
        by_source[r["source_id"]].append(r)

    source_diagnosis = {}
    for src, group in sorted(by_source.items()):
        idx = [
            r["evidence"]["source_coordinate"].get("griffith_unit_index")
            for r in group
            if r["evidence"]["source_coordinate"].get("griffith_unit_index") is not None
        ]
        ambiguous = sum(
            1 for r in group if r["evidence"]["source_coordinate"].get("printed_locator_ambiguous")
        )
        has_hash = sum(1 for r in group if r["evidence"]["provenance"].get("snapshot_sha256"))
        archived = sum(
            1 for r in group if r["evidence"]["provenance"].get("archive_timestamp")
        )
        # The M13 signature: the canonical verse number is a function of a source-local
        # running index, and no independent per-row control exists to corroborate it.
        controls = sum(
            1
            for r in group
            if (r["evidence"].get("recomputed_identity") or {}).get(
                "measured_identical_ignoring_word_division"
            )
            or r["evidence"]["forced_address"].get("verification")
        )
        source_diagnosis[src] = {
            "rows": len(group),
            "rows_carrying_source_local_running_index": len(idx),
            "rows_with_ambiguous_printed_locator": ambiguous,
            "rows_with_source_byte_hash": has_hash,
            "rows_with_immutable_archive_timestamp": archived,
            "rows_with_an_independent_per_row_control": controls,
            "addressing_rests_only_on_a_source_local_index": len(idx) > 0
            and ambiguous > 0
            and controls < len(group),
        }
        if source_diagnosis[src]["addressing_rests_only_on_a_source_local_index"]:
            finding(
                "C2.m13_pattern_search",
                "SYSTEMIC",
                src,
                "the canonical address for part of this source's population is carried by a "
                "source-local running index whose printed locator cannot re-find the unit, "
                "which is the same class of defect as the RV 1.65-1.70 (M13) failure: a "
                "source-local ordinal standing in for a canonical coordinate",
                rows=len(group),
                rows_with_ambiguous_locator=ambiguous,
                rows_with_independent_control=controls,
                generator_available_for_regeneration=False,
                why_regeneration_is_unavailable=(
                    "the manifest declares code_commit 381ba0e; at that commit no file in "
                    "the repository emits griffith_unit_index, english_control_similarity or "
                    "sanskrit_similarity, so the adapter cannot be inspected or re-run and "
                    "the campaign's prescribed remedy (fix generator, regenerate population) "
                    "cannot be executed"
                ),
            )

    # =====================================================================================
    # C6 duplication: identical literals, and one canonical target claimed twice
    # =====================================================================================
    text_groups = defaultdict(list)
    for r in gate_b:
        text_groups[fold_english(rows[r["staged_row_id"]]["payload"].get("text") or "")].append(r)
    key_groups = defaultdict(list)
    for r in gate_b:
        key_groups[r["canonical_key"]].append(r)

    dup_key = {k: v for k, v in key_groups.items() if len(v) > 1}
    if dup_key:
        finding(
            "C6.one_canonical_target_claimed_by_several_rows",
            "HIGH",
            "artifact",
            f"{len(dup_key)} canonical keys are targeted by more than one staged row",
            examples=sorted(dup_key)[:10],
        )

    # =====================================================================================
    # per-row adversarial assessment
    # =====================================================================================
    out_rows: list[dict] = []
    for b in gate_b:
        rid = b["staged_row_id"]
        r = rows[rid]
        p = r["payload"]
        key = b["canonical_key"]
        cats: set[str] = set()
        reasons: list[str] = []
        ev: dict = {}
        staged_en = fold_english(p.get("text") or "")

        # ---- CL literal integrity: is this actually a translation, in the declared tongue?
        xref = CROSS_REFERENCE.search(p.get("text") or "")
        lang = detect_language(p.get("text"))
        ev["literal_integrity"] = {
            "declared_language": p.get("language"),
            "detected": lang,
            "editorial_cross_reference": bool(xref),
            "cross_reference_match": xref.group(0) if xref else None,
        }
        if xref:
            cats.add("C_FAIL_SOURCE_GRANULARITY")
            reasons.append(
                "the literal is an editorial cross-reference, not a translation: "
                f"{xref.group(0)!r}. Griffith abbreviates a repeated formula by pointing at "
                "another verse; staged as this verse's English it asserts the pointer as the "
                "verse's meaning"
            )
        if lang["verdict"] in {"LATIN", "NOT_RECOGNISABLY_ENGLISH"}:
            cats.add("C_WITHHOLD_AMBIGUOUS")
            reasons.append(
                f"payload declares language={p.get('language')!r} but the literal reads as "
                f"{lang['verdict']} (english function-word density "
                f"{lang.get('english_function_word_density')}, latin marker density "
                f"{lang.get('latin_marker_density')}); Griffith renders explicit passages "
                "into Latin, so this is his real text but not an English translation"
            )

        # ---- C1 shift attack: does a canonical neighbour explain the translation as well?
        parent = (passages.get(key) or {}).get("parent_key")
        sibs = siblings.get(parent or "", [])
        pos = sibs.index(key) if key in sibs else None
        shift = {"sibling_spine_length": len(sibs), "position": pos}
        if pos is not None:
            for off, name in ((-1, "previous"), (1, "next")):
                j = pos + off
                if 0 <= j < len(sibs):
                    nk = sibs[j]
                    existing = [
                        t
                        for t in translations.get(nk, [])
                        if (t.get("language") or "en") == "en"
                    ]
                    best = max(
                        (token_dice(staged_en, fold_english(t.get("text") or "")) for t in existing),
                        default=None,
                    )
                    shift[name] = {
                        "key": nk,
                        "carries_translation": bool(existing),
                        "similarity_of_staged_text_to_that_translation": best,
                    }
            # A staged literal that matches a *neighbour's already-live* translation better
            # than chance is the signature of an off-by-one: the row may be one slot out.
            nbest = max(
                (
                    v["similarity_of_staged_text_to_that_translation"] or 0.0
                    for k, v in shift.items()
                    if isinstance(v, dict) and k in {"previous", "next"}
                ),
                default=0.0,
            )
            shift["max_neighbour_similarity"] = round(nbest, 4)
            shift["suspicious_shift"] = nbest >= 0.85
            shift["neighbours_carrying_a_translation"] = sum(
                1
                for k, v in shift.items()
                if isinstance(v, dict) and k in {"previous", "next"} and v.get("carries_translation")
            )
            if nbest >= 0.85:
                cats.add("C_WITHHOLD_AMBIGUOUS")
                reasons.append(
                    f"the staged literal matches a canonical neighbour's already-live "
                    f"translation at {nbest:.4f}; a shift of one slot would explain this row "
                    "as well as the claimed target, so it needs a human read rather than a "
                    "reassignment"
                )
        covered(
            "C1.shift_attack_had_a_neighbour_to_compare_against",
            pos is not None,
            bool(shift.get("neighbours_carrying_a_translation")),
        )
        ev["shift_attack"] = shift

        # ---- C1b shift attack along the *reference* axis
        #
        # The target-axis attack above can only run where a canonical neighbour already
        # carries an English translation, and it covers about 2% of this artifact -- because
        # the staged rows sit precisely in the regions that have no translations yet (the
        # Samaveda has none at all, and Griffith's Atharvaveda kanda 20 is the gap being
        # filled). A zero from a check with 2% coverage is not evidence of alignment.
        #
        # So the same attack is run along the other axis. A row whose unit was pinned by
        # matching Griffith's *Rigveda* rendering of a cited parallel can be tested against
        # the renderings of that parallel's own neighbours: if RV n-1 or n+1 explains the
        # staged English better than RV n does, the control that fixed this row is itself a
        # slot out. This is skipped for the reuse population, where the staged text IS the
        # reference's translation and the comparison would be circular by construction.
        ctrl = p.get("control_rv_key")
        ref_shift = {"control_rv_key": ctrl, "applicable": bool(ctrl)}
        if ctrl:
            rparent = (passages.get(ctrl) or {}).get("parent_key")
            rsibs = siblings.get(rparent or "", [])
            rpos = rsibs.index(ctrl) if ctrl in rsibs else None
            ref_shift["reference_spine_length"] = len(rsibs)

            def en_of(k):
                return [
                    t for t in translations.get(k, []) if (t.get("language") or "en") == "en"
                ]

            scored = {}
            for off, name in ((-1, "reference_minus_1"), (0, "reference"), (1, "reference_plus_1")):
                j = (rpos + off) if rpos is not None else None
                if j is not None and 0 <= j < len(rsibs):
                    nk = rsibs[j]
                    best = max(
                        (
                            token_dice(staged_en, fold_english(t.get("text") or ""))
                            for t in en_of(nk)
                        ),
                        default=None,
                    )
                    scored[name] = {"key": nk, "similarity": best}
            ref_shift["scores"] = scored
            claimed = (scored.get("reference") or {}).get("similarity")
            rivals = {
                k: v["similarity"]
                for k, v in scored.items()
                if k != "reference" and v.get("similarity") is not None
            }
            ref_shift["claimed_reference_similarity"] = claimed
            ref_shift["best_rival_similarity"] = max(rivals.values()) if rivals else None
            ref_shift["claimed_declared_by_row"] = p.get("english_control_similarity")
            # A rival strictly better than the claimed control means the row's own evidence
            # points at a different verse. Equal-or-worse is the expected, healthy shape.
            ref_shift["a_neighbour_explains_it_better"] = bool(
                claimed is not None and rivals and max(rivals.values()) > claimed
            )
            covered(
                "C1b.reference_axis_shift_attack_was_evaluable",
                True,
                claimed is not None and bool(rivals),
            )
            if ref_shift["a_neighbour_explains_it_better"]:
                cats.add("C_WITHHOLD_AMBIGUOUS")
                reasons.append(
                    "the Rigveda control that pinned this row is beaten by one of its own "
                    f"canonical neighbours: claimed {ctrl} scores {claimed}, while "
                    f"{max(rivals, key=rivals.get)} scores {max(rivals.values())}; the "
                    "control may be one slot out, so this needs a human read"
                )
            # Independently reproduce the row's own declared control score.
            declared = p.get("english_control_similarity")
            if declared is not None and claimed is not None:
                ref_shift["declared_minus_measured"] = round(declared - claimed, 4)
                ref_shift["declared_control_score_reproduced"] = abs(declared - claimed) <= 0.05
                covered("C1b.declared_control_score_reproducible", True, True)
        ev["reference_shift_attack"] = ref_shift

        # ---- C3 forced address
        yv = yv_verif.get(key)
        forced_flag = p.get("address_forced_without_content_control")
        if forced_flag is not None or yv:
            det = (yv or {}).get("source_local_address_determination")
            independent = det in {
                "PRINTED_LABEL_READ_DIRECTLY",
                "CORRUPT_GLYPHS_REPAIR_TO_CANONICAL",
                "UNIQUELY_BRACKETED_BY_PRINTED_NEIGHBOURS",
                "CONSTANT_OFFSET_SPINE_WITH_NEIGHBOURS",
            }
            has_rv_control = bool(p.get("verification"))
            ev["forced_address_attack"] = {
                "payload_flag": forced_flag,
                "payload_claims_no_content_control": forced_flag is True,
                "independent_source_verification": det,
                "printed_label_in_source": (yv or {}).get("printed_label"),
                "printed_label_glyphs": (yv or {}).get("best_matching_unit", {}).get(
                    "printed_label_glyphs"
                )
                if yv
                else None,
                "printed_label_equals_canonical": (yv or {}).get(
                    "printed_label_equals_canonical_verse"
                ),
                "neighbours_bracket_slot_exactly": (yv or {}).get(
                    "neighbours_bracket_canonical_slot_exactly"
                ),
                "literal_located_in_pinned_source": (yv or {}).get(
                    "literal_found_in_pinned_source"
                ),
                "row_pins_its_own_source_bytes": (yv or {}).get("row_pins_its_own_bytes"),
                "independent_rigveda_english_control": p.get("verification"),
                "verdict": (
                    "VERIFIED_INDEPENDENTLY"
                    if independent
                    else "NOT_VERIFIED"
                ),
                "controls_available": [
                    c
                    for c, ok in (
                        ("SOURCE_PRINTED_LABEL", det == "PRINTED_LABEL_READ_DIRECTLY"),
                        (
                            "SOURCE_PRINTED_NEIGHBOUR_BRACKET",
                            det == "UNIQUELY_BRACKETED_BY_PRINTED_NEIGHBOURS",
                        ),
                        (
                            "SOURCE_CONSTANT_OFFSET_SPINE",
                            det == "CONSTANT_OFFSET_SPINE_WITH_NEIGHBOURS",
                        ),
                        ("RIGVEDA_ENGLISH_PARALLEL_CONTROL", has_rv_control),
                    )
                    if ok
                ],
            }
            covered(
                "C3.forced_address_had_independent_source_evidence",
                True,
                det is not None,
            )
            if forced_flag is True and not independent:
                cats.add("C_FAIL_UNVERIFIED_FORCED_ADDRESS")
                reasons.append(
                    "forced address with no independent control: the pinned source neither "
                    "prints a usable label for this unit nor brackets the canonical slot "
                    f"uniquely (determination={det!r})"
                )

        # ---- C4 / C7 cross-corpus reuse and contamination
        ref = p.get("cross_corpus_source_key") or p.get("control_rv_key")
        if ref:
            ri = b["evidence"].get("recomputed_identity") or {}
            is_reuse = r["source_id"] == "VEDAGRAPH_CANONICAL_RV_GRIFFITH"
            ref_veda = ref.split(":")[1]
            same_veda = ref_veda == b["veda"]
            disclosed = bool(
                re.search(
                    r"cross-corpus reuse|not a (?:Samaveda|Atharvaveda|translation)|"
                    r"reuse of a Rigveda translation",
                    r.get("mapping_method") or "",
                    re.I,
                )
            )
            ev["cross_corpus"] = {
                "reference_key": ref,
                "reference_veda": ref_veda,
                "target_veda": b["veda"],
                "reference_is_another_corpus": not same_veda,
                "translation_text_taken_from_the_other_corpus": is_reuse,
                "reuse_disclosed_in_mapping_method": disclosed,
                "identity_reproduced": ri.get("measured_identical_ignoring_word_division"),
                "staged_relation_asserted": p.get("relation_asserted"),
                "graph_relations_between_pair": ri.get("graph_relations_between_pair"),
                "staged_relation_agrees_with_graph": p.get("relation_asserted")
                in (ri.get("graph_relations_between_pair") or []),
                "usable_as_independent_semantic_evidence": not is_reuse,
            }
            if is_reuse and not same_veda:
                if not ri.get("measured_identical_ignoring_word_division"):
                    cats.add("C_FAIL_CROSS_CORPUS_CONTAMINATION")
                    reasons.append(
                        f"the translation text is {ref_veda}'s, applied to a {b['veda']} "
                        "verse, and the textual identity that would justify it does not "
                        "reproduce"
                    )
                else:
                    cats.add("C_WITHHOLD_REUSED_RENDERING_POLICY")
                    reasons.append(
                        f"the translation text is Griffith's {ref_veda} rendering reused on a "
                        f"{b['veda']} verse whose Sanskrit is verified identical; legitimate "
                        "only as a disclosed reused rendering, and never as independent "
                        f"semantic evidence for {b['veda']}"
                    )
            if not is_reuse and ref and not same_veda:
                # The reference is used as a control, not as the text. That is legitimate,
                # but it means the row's addressing depends on another corpus's identity.
                ev["cross_corpus"]["reference_used_as_addressing_control_only"] = True

        # ---- C5 archive evidence
        url = r.get("source_url") or ""
        sha = p.get("snapshot_sha256")
        if "web.archive.org" in url:
            pg = page_by_sha.get(sha) or page_by_url.get(url)
            ts = re.search(r"/web/(\d{14})/", url)
            ev["archive_evidence"] = {
                "archive_url": url,
                "immutable_timestamp": ts.group(1) if ts else None,
                "row_declares_page_content_hash": bool(sha),
                "hash_present_in_source_page_proofs": sha in page_by_sha if sha else False,
                "url_present_in_source_page_proofs": url in page_by_url,
                "proof_http_status": (pg or {}).get("http_status"),
                "proof_page_id": (pg or {}).get("page_id"),
                "page_bytes_retained_on_disk": False,
            }
            covered("C5.archive_capture_traceable_to_a_page_proof", True, bool(sha))
            if not sha:
                cats.add("C_FAIL_ARCHIVE_EVIDENCE")
                reasons.append(
                    "the row cites an archive capture but declares no content hash for it, "
                    "so there is no way to show the capture held this text"
                )
            elif sha not in page_by_sha:
                cats.add("C_FAIL_ARCHIVE_EVIDENCE")
                reasons.append(
                    "the row's declared page hash is absent from proofs/source_pages.json, "
                    "so the capture it names is not among the pages this artifact proved it "
                    "fetched"
                )

        # ---- C6 duplication, per row
        #
        # The first version of this check treated "same literal, different parent" as the
        # defect. That is wrong twice over. The Vedic corpora genuinely repeat whole verses
        # across hymns and across Vedas -- that repetition is why a parallel layer exists at
        # all -- and the cross-corpus reuse population deliberately puts one Rigveda
        # rendering onto every verse verified identical to it, which by construction means
        # several parents. So the check reported 230 defects, almost all of them the corpus
        # behaving as the corpus does.
        #
        # The sound test is textual: identical English is *correct* when the two targets'
        # Sanskrit is identical, and suspicious only when it is not. That is decidable here,
        # because the graph holds a primary Sanskrit text for every staged target.
        my_sa = primary_sanskrit(texts.get(key, []))
        my_sa_folded = (
            sandhi_insensitive(fold_sanskrit(my_sa["text"], my_sa["script"])) if my_sa else None
        )
        same_text = [o for o in text_groups[staged_en] if o["staged_row_id"] != rid]
        same_sanskrit, diff_sanskrit, unknown_sanskrit = [], [], []
        for o in same_text:
            osa = primary_sanskrit(texts.get(o["canonical_key"], []))
            if not osa or not my_sa_folded:
                unknown_sanskrit.append(o)
            elif sandhi_insensitive(fold_sanskrit(osa["text"], osa["script"])) == my_sa_folded:
                same_sanskrit.append(o)
            else:
                diff_sanskrit.append(o)
        declared_range = b["measured_grain"] == "MANTRA_RANGE"
        covered(
            "C6.duplication_could_compare_target_sanskrit",
            bool(same_text),
            bool(same_text) and not unknown_sanskrit,
        )
        same_parent = [
            o
            for o in diff_sanskrit
            if (passages.get(o["canonical_key"]) or {}).get("parent_key")
            == (passages.get(key) or {}).get("parent_key")
        ]
        ev["duplication"] = {
            "rows_sharing_this_literal": len(same_text),
            "sharing_rows_whose_target_sanskrit_is_identical": len(same_sanskrit),
            "sharing_rows_whose_target_sanskrit_differs": len(diff_sanskrit),
            "sharing_rows_whose_target_sanskrit_is_unknown": len(unknown_sanskrit),
            "declared_multi_verse_unit": declared_range,
            "legitimate_repetition": len(diff_sanskrit) == 0 and len(same_text) > 0,
            "differing_examples": [o["canonical_key"] for o in diff_sanskrit[:5]],
            "identical_examples": [o["canonical_key"] for o in same_sanskrit[:5]],
        }
        # The discriminator is the *source unit*, not the text and not the parent.
        #
        # Two earlier versions of this check were both wrong. The first flagged "same
        # literal, different parent" and reported 230 defects. The second asked whether the
        # two targets' Sanskrit matched and reported 43 -- still wrong, because the corpora
        # repeat a verse with small variant readings and Griffith then printed a *separate*
        # translation for each occurrence, in each volume. AV 20.5.7 and the Samavedic
        # parallel read "Kundapāyya" and "Kundapayya"; AV 20.17.10 and AV 20.89.10 are one
        # hymn printed twice in kanda 20. Those are two source units and two renderings, and
        # folding away the diacritics is what made them look like one.
        #
        # Generator duplication is the opposite shape: ONE printed unit emitted onto several
        # canonical targets. So the defect is a shared source-unit identity, and a shared
        # literal from distinct units is the source repeating itself -- legitimate, but a
        # fact the product has to disclose, so it is recorded rather than dropped.
        def unit_identity(row_id: str) -> tuple:
            rr = rows[row_id]
            pp = rr["payload"]
            return (
                rr["source_id"],
                rr.get("source_locator"),
                json.dumps(pp.get("printed_span")),
                pp.get("griffith_unit_index"),
                pp.get("snapshot_sha256"),
            )

        # Scoped to *printed* units. The internal reuse source has no printed unit: its
        # "coordinate" is the Rigveda verse whose rendering is being reused, and applying one
        # such rendering to every verse verified identical to it is the population's whole
        # design, not a duplication. The corresponding defect for that source is a reuse onto
        # a target that is NOT verified identical, which C7 already catches.
        printed_source = r["source_id"] != "VEDAGRAPH_CANONICAL_RV_GRIFFITH"
        my_unit = unit_identity(rid)
        shared_unit = (
            [
                o
                for o in same_text
                if rows[o["staged_row_id"]]["source_id"] != "VEDAGRAPH_CANONICAL_RV_GRIFFITH"
                and unit_identity(o["staged_row_id"]) == my_unit
            ]
            if printed_source
            else []
        )
        ev["duplication"]["rows_sharing_this_source_unit"] = len(shared_unit)
        ev["duplication"]["shared_unit_examples"] = [o["canonical_key"] for o in shared_unit[:5]]
        ev["duplication"]["source_repeats_itself_across_distinct_units"] = (
            len(same_text) > 0 and len(shared_unit) == 0
        )
        if shared_unit and not declared_range:
            cats.add("C_FAIL_DUPLICATE_GENERATION")
            reasons.append(
                f"one printed source unit ({my_unit[1]!r}) is emitted onto "
                f"{len(shared_unit) + 1} canonical targets with no multi-verse unit declared "
                f"({', '.join(o['canonical_key'] for o in shared_unit[:3])}); that is the "
                "generator writing one unit several times, not the source repeating a verse"
            )
        elif diff_sanskrit and declared_range:
            # A declared range legitimately repeats one rendering over a span whose verses
            # differ -- that is what a multi-verse print unit is. It stays withheld from the
            # 1:1 class but is not a generator defect.
            ev["duplication"]["explained_by_declared_range"] = True

        # ---- C8 boundary flags (oversampling markers, not verdicts)
        hier = passages.get(key) or {}
        ev["boundary"] = {
            "first_in_parent": pos == 0 if pos is not None else None,
            "last_in_parent": pos == len(sibs) - 1 if pos is not None else None,
            "inside_m13_rv_span": bool(re.match(r"VG:RV:SAK:M01:S0(6[5-9]|70):", key)),
            "rv_9_7": key.startswith("VG:RV:SAK:M09:S007:"),
            "av_kanda_20": key.startswith("VG:AV:SAU:K20:"),
            "declared_range": declared_range,
            "forced_address": p.get("address_forced_without_content_control") is True,
        }

        category = "C_PASS"
        for c in PRECEDENCE:
            if c in cats:
                category = c
                break
        out_rows.append(
            {
                "staged_row_id": rid,
                "canonical_key": key,
                "veda": b["veda"],
                "source_id": b["source_id"],
                "gate_b_category": b["gate_b_category"],
                "gate_c_category": category,
                "gate_c_all_categories": sorted(cats) or ["C_PASS"],
                "gate_c_reasons": reasons,
                "assessed": b["gate_b_category"] == "B_PASS",
                "evidence": ev,
            }
        )

    write_jsonl("gate_c_rows.jsonl", out_rows)

    # Findings that only make sense in aggregate.
    latin = [r for r in out_rows if r["evidence"]["literal_integrity"]["detected"]["verdict"] in {"LATIN", "NOT_RECOGNISABLY_ENGLISH"}]
    if latin:
        finding(
            "CL.declared_language_disagrees_with_literal",
            "HIGH",
            "artifact",
            f"{len(latin)} rows declare language 'en' while the literal is Griffith's Latin "
            "substitution for an explicit passage; the text is genuine but it is not English",
            by_veda=dict(Counter(r["veda"] for r in latin)),
            examples=[r["canonical_key"] for r in latin[:8]],
        )
    xrefs = [r for r in out_rows if r["evidence"]["literal_integrity"]["editorial_cross_reference"]]
    if xrefs:
        finding(
            "CL.editorial_cross_reference_staged_as_translation",
            "HIGH",
            "artifact",
            f"{len(xrefs)} rows stage an editorial cross-reference as the verse's translation",
            examples=[
                {
                    "canonical_key": r["canonical_key"],
                    "literal": (rows[r["staged_row_id"]]["payload"].get("text") or "")[:120],
                }
                for r in xrefs
            ],
        )
    reused = [r for r in out_rows if r["gate_c_category"] == "C_WITHHOLD_REUSED_RENDERING_POLICY"]
    if reused:
        finding(
            "C4.cross_corpus_reused_rendering",
            "POLICY",
            "artifact",
            f"{len(reused)} rows would attach Griffith's Rigveda rendering to a non-Rigveda "
            "verse whose Sanskrit is verified identical; truthful only with disclosure, and "
            "never usable as independent semantic evidence for the target corpus",
            by_veda=dict(Counter(r["veda"] for r in reused)),
            all_disclosed_in_mapping_method=all(
                r["evidence"]["cross_corpus"]["reuse_disclosed_in_mapping_method"] for r in reused
            ),
        )

    assessed = [r for r in out_rows if r["assessed"]]
    summary = {
        "phase": "4-6",
        "rows_carried_into_gate_c": len(out_rows),
        "rows_that_passed_gate_b_and_were_adversarially_assessed": len(assessed),
        "note": (
            "every staged row is carried through Gate C's deterministic checks so the packet "
            "can report on the withheld populations too, but only the Gate B passes are "
            "eligible for an import recommendation"
        ),
        "by_category_assessed": dict(
            sorted(Counter(r["gate_c_category"] for r in assessed).items(), key=lambda kv: -kv[1])
        ),
        "by_category_and_veda_assessed": dict(
            sorted(
                Counter(f"{r['gate_c_category']}|{r['veda']}" for r in assessed).items(),
                key=lambda kv: -kv[1],
            )
        ),
        "by_category_and_source_assessed": dict(
            sorted(
                Counter(f"{r['gate_c_category']}|{r['source_id']}" for r in assessed).items(),
                key=lambda kv: -kv[1],
            )
        ),
        "source_level_diagnosis": source_diagnosis,
        "forced_address_verdicts": dict(
            Counter(
                (r["evidence"].get("forced_address_attack") or {}).get("verdict")
                for r in out_rows
                if r["evidence"].get("forced_address_attack")
            )
        ),
        "shift_attack": {
            "target_axis": {
                "rows_with_a_comparable_neighbour_translation": sum(
                    1
                    for r in out_rows
                    if (r["evidence"]["shift_attack"].get("max_neighbour_similarity") or 0) > 0
                ),
                "rows_flagged_suspicious": sum(
                    1 for r in out_rows if r["evidence"]["shift_attack"].get("suspicious_shift")
                ),
                "limitation": (
                    "only evaluable where a canonical neighbour already carries an English "
                    "translation; the staged rows sit in the regions that have none, so this "
                    "axis covers a small fraction and its zero is a coverage statement"
                ),
            },
            "reference_axis": {
                "rows_with_a_rigveda_control": sum(
                    1 for r in out_rows if r["evidence"]["reference_shift_attack"]["applicable"]
                ),
                "rows_evaluated": sum(
                    1
                    for r in out_rows
                    if r["evidence"]["reference_shift_attack"].get("best_rival_similarity")
                    is not None
                ),
                "rows_where_a_neighbour_explains_it_better": sum(
                    1
                    for r in out_rows
                    if r["evidence"]["reference_shift_attack"].get(
                        "a_neighbour_explains_it_better"
                    )
                ),
                "declared_control_score_reproduced": sum(
                    1
                    for r in out_rows
                    if r["evidence"]["reference_shift_attack"].get(
                        "declared_control_score_reproduced"
                    )
                ),
                "declared_control_score_not_reproduced": sum(
                    1
                    for r in out_rows
                    if r["evidence"]["reference_shift_attack"].get(
                        "declared_control_score_reproduced"
                    )
                    is False
                ),
            },
        },
        "duplication": {
            "rows_sharing_a_literal_with_another_row": sum(
                1 for r in out_rows if r["evidence"]["duplication"]["rows_sharing_this_literal"]
            ),
            "sharing_where_the_targets_sanskrit_is_identical": sum(
                1
                for r in out_rows
                if r["evidence"]["duplication"][
                    "sharing_rows_whose_target_sanskrit_is_identical"
                ]
            ),
            "sharing_where_the_targets_sanskrit_differs": sum(
                1
                for r in out_rows
                if r["evidence"]["duplication"]["sharing_rows_whose_target_sanskrit_differs"]
            ),
            "rows_sharing_one_printed_source_unit": sum(
                1
                for r in out_rows
                if r["evidence"]["duplication"].get("rows_sharing_this_source_unit")
            ),
            "rows_where_the_source_itself_repeats_the_verse": sum(
                1
                for r in out_rows
                if r["evidence"]["duplication"].get(
                    "source_repeats_itself_across_distinct_units"
                )
            ),
            "legitimate_repetition_rows": sum(
                1 for r in out_rows if r["evidence"]["duplication"]["legitimate_repetition"]
            ),
            "explained_by_a_declared_range": sum(
                1
                for r in out_rows
                if r["evidence"]["duplication"].get("explained_by_declared_range")
            ),
            "canonical_keys_claimed_twice": len(dup_key),
        },
        "archive_evidence": {
            "rows_citing_an_archive_capture": sum(
                1 for r in out_rows if r["evidence"].get("archive_evidence")
            ),
            "rows_whose_hash_is_in_the_page_proofs": sum(
                1
                for r in out_rows
                if (r["evidence"].get("archive_evidence") or {}).get(
                    "hash_present_in_source_page_proofs"
                )
            ),
        },
        "literal_integrity": {
            "language_verdicts": dict(
                Counter(
                    r["evidence"]["literal_integrity"]["detected"]["verdict"] for r in out_rows
                )
            ),
            "editorial_cross_references": len(xrefs),
        },
        "check_coverage": {
            name: {
                **d,
                "coverage": round(d["evaluated"] / d["eligible"], 4) if d["eligible"] else None,
                "vacuous": d["eligible"] > 0 and d["evaluated"] == 0,
            }
            for name, d in sorted(cov.items())
        },
        "vacuous_checks": [
            name for name, d in sorted(cov.items()) if d["eligible"] > 0 and d["evaluated"] == 0
        ],
        "categories_declared": list(CATEGORIES),
        "precedence": list(PRECEDENCE),
    }
    write_json("gate_c_summary.json", summary)
    write_jsonl("gate_c_findings.jsonl", findings)

    print(f"rows carried: {len(out_rows)}  adversarially assessed (B_PASS): {len(assessed)}")
    for k, v in summary["by_category_assessed"].items():
        print(f"   {v:6d}  {k}")
    print("-- forced address verdicts --", summary["forced_address_verdicts"])
    print("-- shift attack target axis --", summary["shift_attack"]["target_axis"]["rows_flagged_suspicious"],
          "suspicious of", summary["shift_attack"]["target_axis"]["rows_with_a_comparable_neighbour_translation"], "evaluable")
    print("-- shift attack reference axis --", summary["shift_attack"]["reference_axis"])
    print("-- duplication --", summary["duplication"])
    print("-- archive --", summary["archive_evidence"])
    print("-- literal --", summary["literal_integrity"])
    print("-- check coverage --")
    for name, d in summary["check_coverage"].items():
        flag = "  <-- VACUOUS" if d["vacuous"] else ""
        print(f"   {name}: {d['evaluated']}/{d['eligible']} ({d['coverage']}){flag}")
    print(f"-- findings: {len(findings)}")
    for f in findings:
        print(f"   [{f['severity']}] {f['check']} ({f['scope']}): {f['summary'][:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
