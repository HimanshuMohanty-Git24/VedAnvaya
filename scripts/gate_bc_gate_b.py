#!/usr/bin/env python3
"""Gate B -- structural and semantic eligibility, over 100% of the staged translation rows.

Gate B asks one question per row: is this row *entitled* to make a canonical translation
assertion at all? It is not asking whether the translation is a good one, and it is not
asking whether the alignment is right -- that is Gate C's adversarial job. It is asking
whether the target exists and is the kind of thing a translation may attach to, whether the
source coordinate is a real coordinate rather than an artefact of the reading code, whether
the asserted grain matches the source's actual grain, whether the literal is a translation
rather than page furniture, whether the provenance would let a third party re-fetch the
evidence, and whether the central importability policy admits it.

Two design rules, both paid for earlier in this campaign.

**Every check reports its own coverage.** A check that silently skips the rows whose shape it
does not recognise converts absence of checking into evidence of correctness. So each check
carries `eligible` and `evaluated`, and a check whose coverage is under 100% of its eligible
population is itself reported as a defect, separately from the data's failures.

**The generator's own metadata is a claim, not evidence.** The artifact under test declares
similarity scores, a `recension_verified` boolean and a prose `mapping_method`. None of that
is treated as established here. Where a claim is recomputable from the graph -- and the
load-bearing ones are -- it is recomputed from the stored text versions, and the claimed and
measured values are both reported. This matters more than usual for this artifact because
the code that produced it is not in version control: at the manifest's own declared
`code_commit` no file in the repository emits `griffith_unit_index`,
`english_control_similarity` or `sanskrit_similarity`, so the adapter cannot be inspected
and no population can be regenerated. Independent recomputation is the only audit available.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter, defaultdict

from gate_bc_common import PACKET, load_rows, not_importable_confidences, write_json, write_jsonl
from gate_bc_textfold import fold_english, fold_sanskrit, sandhi_insensitive, token_dice

CACHE = pathlib.Path(
    r"C:\Users\HKM49\AppData\Local\Temp\claude\d--VedaGraph"
    r"\9811a2e5-56d7-4f68-aa33-48f350e56c58\scratchpad\graph_facts.json"
)

# Expected canonical shape per Veda: (recension segment, work_id).
EXPECTED = {
    "RV": ("SAK", "VG:WORK:RV:SAK"),
    "SV": ("KAU", "VG:WORK:SV:KAU"),
    "YV": ("VSM", "VG:WORK:YV:VSM"),
    "AV": ("SAU", "VG:WORK:AV:SAU"),
}

# Page furniture that a translation literal must not be. Matched against the whole folded
# literal, so a hymn that legitimately contains the word "next" is unaffected.
CHROME_EXACT = {
    "next",
    "previous",
    "index",
    "contents",
    "sacred texts",
    "hinduism",
    "buy this book",
    "next hymn",
    "previous hymn",
    "sacred texts hinduism index",
}
CHROME_SUBSTRINGS = (
    "sacred-texts.com",
    "click here",
    "buy this book at amazon",
    "this page last updated",
    "scanned at sacred-texts",
    "proofed at",
    "internet archive",
    "wayback machine",
)
HTML_ARTEFACT = re.compile(r"<[a-z/][^>]*>|&[a-z]{2,6};|&#\d+;", re.I)
# A translation that is only a numeral, a roman numeral, or a bare label.
LABEL_ONLY = re.compile(r"^(hymn\s+)?[ivxlcdm\d\s.,;:'\"-]+$", re.I)
CATEGORIES = (
    "B_PASS",
    "B_FAIL_TARGET",
    "B_FAIL_SOURCE_COORDINATE",
    "B_FAIL_GRANULARITY",
    "B_FAIL_UNEXPLAINED_SPINE",
    "B_FAIL_PROVENANCE",
    "B_FAIL_LITERAL",
    "B_FAIL_POLICY",
    "B_CONFLICT_EXISTING_TRANSLATION",
    "B_NEEDS_INDEPENDENT_CONTENT_CONTROL",
)
# Categories are ordered by precedence: a row that fails several ends in the first it hits,
# because a decision table needs one reason per row, and the earlier ones are the ones that
# make the later questions moot -- there is no point reporting a literal defect on a row
# whose target is in the wrong Veda.
PRECEDENCE = (
    "B_FAIL_POLICY",
    "B_FAIL_TARGET",
    "B_FAIL_SOURCE_COORDINATE",
    "B_FAIL_PROVENANCE",
    "B_FAIL_LITERAL",
    "B_FAIL_GRANULARITY",
    "B_FAIL_UNEXPLAINED_SPINE",
    "B_CONFLICT_EXISTING_TRANSLATION",
    "B_NEEDS_INDEPENDENT_CONTENT_CONTROL",
)


class Checks:
    """Per-check coverage and failure bookkeeping."""

    def __init__(self) -> None:
        self.eligible: Counter = Counter()
        self.evaluated: Counter = Counter()
        self.failed: Counter = Counter()

    def record(self, name: str, eligible: bool, evaluated: bool, ok: bool | None) -> None:
        if eligible:
            self.eligible[name] += 1
            if evaluated:
                self.evaluated[name] += 1
                if ok is False:
                    self.failed[name] += 1

    def report(self) -> dict:
        out = {}
        for name in sorted(self.eligible):
            el, ev, fa = self.eligible[name], self.evaluated[name], self.failed[name]
            out[name] = {
                "eligible": el,
                "evaluated": ev,
                "coverage": round(ev / el, 4) if el else None,
                "full_coverage": ev == el,
                "failed": fa,
                "passed": ev - fa,
            }
        return out


def primary_sanskrit(texts: list[dict]) -> dict | None:
    if not texts:
        return None
    for t in texts:
        if t.get("role") == "PRIMARY_TEXT":
            return t
    return texts[0]


def parse_key(key: str) -> dict:
    parts = key.split(":")
    return {
        "prefix": parts[0] if parts else None,
        "veda": parts[1] if len(parts) > 1 else None,
        "recension": parts[2] if len(parts) > 2 else None,
        "tail": parts[3:],
        "verse": next(
            (int(m.group(1)) for p in reversed(parts) if (m := re.fullmatch(r"V(\d+)", p))), None
        ),
    }


def locator_numbers(locator: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", locator or "")]


def classify_granularity(row: dict) -> tuple[str, dict]:
    """What grain is the source unit actually at, independent of what the row asserts?"""
    p = row["payload"]
    loc = row.get("source_locator") or ""
    span = p.get("printed_span")
    detail = {"printed_span": span, "locator": loc}
    span_len = None
    if isinstance(span, list) and len(span) == 2 and all(isinstance(x, int) for x in span):
        span_len = span[1] - span[0] + 1
        detail["span_length"] = span_len
    # An internal cross-corpus row cites its source as a canonical key, which is the most
    # precise coordinate in this system -- more precise than any printed locator. The first
    # version of this classifier had no pattern for that shape and returned OTHER for all
    # 194 of them, then failed them for being "not mantra-level". That was the classifier's
    # defect, not the rows'; a coordinate naming one :Mantra is mantra-grained by
    # construction.
    if re.search(r"\(VG:[A-Z]{2}:[A-Z]{3}:.*V\d+\)", loc):
        detail["coordinate_is_canonical_key"] = True
        return "MANTRA", detail
    # An explicit multi-verse print unit, however the row labels it.
    if span_len and span_len > 1:
        return "MANTRA_RANGE", detail
    if re.search(r"covering verses|printed as one unit|verses \d+\s*[-\u2013]\s*\d+", loc, re.I):
        return "MANTRA_RANGE", detail
    # A locator that names a hymn but no verse at all is hymn-grained.
    if re.search(r"\bhymn\b", loc, re.I) and not re.search(
        r"verse|printed label|label '|document unit|unit \d+", loc, re.I
    ):
        return "HYMN", detail
    if re.search(r"\b(book page|page)\b", loc, re.I) and not re.search(
        r"verse|printed label|label '|document unit", loc, re.I
    ):
        return "SECTION", detail
    if span_len == 1 or re.search(
        r"verse \d+|printed label|label '|document unit \d+", loc, re.I
    ):
        return "MANTRA", detail
    return "OTHER", detail


def main() -> int:
    facts = json.loads(CACHE.read_text(encoding="utf-8"))
    passages = facts["passages"]
    texts = facts["texts"]
    translations = facts["translations"]
    graph_rels = facts["graph_relations"]
    siblings = facts["siblings"]

    rows = load_rows()
    ni = not_importable_confidences()
    ck = Checks()

    # ---- population-level precomputation -------------------------------------------------
    # Locator collisions: one source coordinate string addressing several canonical keys.
    # This is not automatically a defect (a multi-verse print unit legitimately does it) but
    # a locator that cannot distinguish two targets cannot be the thing that identified them.
    loc_to_keys = defaultdict(set)
    for r in rows:
        loc_to_keys[(r["source_id"], r.get("source_locator") or "")].add(r["canonical_key"])

    # Identical literals across rows, for the duplication attack and the literal check.
    text_to_rows = defaultdict(list)
    for r in rows:
        text_to_rows[fold_english(r["payload"].get("text") or "")].append(r["_staged_row_id"])

    # Rows grouped by (source, canonical parent) so a range's completeness is checkable.
    by_key = {r["canonical_key"]: r for r in rows}

    out_rows: list[dict] = []
    for r in rows:
        p = r["payload"]
        key = r["canonical_key"]
        node = passages.get(key)
        kp = parse_key(key)
        reasons: list[str] = []
        cats: set[str] = set()
        ev: dict = {}

        # ---------------- B9 POLICY (first, it is the cheapest and most absolute) --------
        conf = r["mapping_confidence"]
        policy_ok = conf not in ni
        ck.record("B9.central_importability_policy", True, True, policy_ok)
        if not policy_ok:
            cats.add("B_FAIL_POLICY")
            reasons.append(f"mapping_confidence={conf} is in the central NOT_IMPORTABLE set")
        ev["policy"] = {"mapping_confidence": conf, "admitted_by_central_policy": policy_ok}

        # A forced address is withheld regardless of its declared confidence. The central
        # predicate keys on mapping_confidence alone, and every one of these rows is staged
        # EXACT, so policy alone does not stop them -- which is the defect, not the row's.
        forced = p.get("address_forced_without_content_control")
        has_control = bool(p.get("verification")) or bool(p.get("control_rv_key")) or bool(
            p.get("cross_corpus_source_key")
        )
        ck.record(
            "B9.forced_address_requires_content_control",
            forced is not None,
            forced is not None,
            None if forced is None else not (forced is True),
        )
        if forced is True:
            cats.add("B_NEEDS_INDEPENDENT_CONTENT_CONTROL")
            reasons.append(
                "payload declares address_forced_without_content_control=true; the central "
                "policy does not withhold it because the row is staged EXACT"
            )
        ev["forced_address"] = {
            "flag": forced,
            "declares_any_content_control": has_control,
            "verification": p.get("verification"),
        }

        # ---------------- B1 TARGET IDENTITY --------------------------------------------
        ck.record("B1.target_resolves", True, True, node is not None)
        if node is None:
            cats.add("B_FAIL_TARGET")
            reasons.append("canonical_key does not resolve to a :Passage in the graph")
            ev["target"] = {"resolves": False}
        else:
            labels = set(node["labels"])
            is_mantra = "Mantra" in labels
            is_internal = "Internal" in labels
            veda_key = kp["veda"]
            veda_row = r["veda"]
            veda_node = node["veda"]
            exp_rec, exp_work = EXPECTED.get(veda_key, (None, None))
            checks = {
                "is_mantra": is_mantra,
                "is_passage": "Passage" in labels,
                "not_internal": not is_internal,
                "veda_row_matches_key": veda_row == veda_key,
                "veda_node_matches_key": veda_node == veda_key,
                "payload_veda_matches": p.get("veda") == veda_key,
                "recension_expected": kp["recension"] == exp_rec,
                "work_id_expected": node["work_id"] == exp_work,
                "status_canonical": node["status"] == "CANONICAL",
                "parent_exists": bool(node.get("parent_key"))
                and node["parent_key"] in facts["parent_info"],
                "display_type_mantra": node.get("display_type") == "MANTRA",
            }
            for name, ok in checks.items():
                ck.record(f"B1.{name}", True, True, ok)
            bad = [n for n, ok in checks.items() if not ok]
            if bad:
                cats.add("B_FAIL_TARGET")
                reasons.append("target identity failed: " + ", ".join(bad))
            ev["target"] = {
                "resolves": True,
                "labels": node["labels"],
                "veda_node": veda_node,
                "work_id": node["work_id"],
                "citation": node.get("citation"),
                "checks": checks,
            }

        # ---------------- B2 SOURCE COORDINATE ------------------------------------------
        loc = r.get("source_locator") or ""
        nums = locator_numbers(loc)
        loc_present = bool(loc.strip())
        ck.record("B2.locator_present", True, True, loc_present)
        collide = loc_to_keys[(r["source_id"], loc)]
        gran, gran_detail = classify_granularity(r)
        # A collision is only a defect when the unit is not declared multi-verse: two
        # single-mantra rows sharing one coordinate means the coordinate did not address
        # either of them.
        #
        # An internal cross-corpus row is the one legitimate exception. Its "locator" is the
        # Rigveda verse whose rendering is being reused, and the Samaveda genuinely repeats
        # one Rigvedic verse in several ganas -- so three targets citing RV 1.7.1 is the
        # expected shape of the phenomenon, not a coordinate that failed to address them.
        # Each such target is addressed by its own recomputed Sanskrit identity, which is
        # checked separately below; the reuse itself is Gate C's question, not Gate B's.
        internal_reuse = r["source_id"] == "VEDAGRAPH_CANONICAL_RV_GRIFFITH"
        collision_ok = len(collide) == 1 or gran == "MANTRA_RANGE" or internal_reuse
        ck.record("B2.locator_addresses_one_target", loc_present, loc_present, collision_ok)
        # Where the printed locator is ambiguous, is there nevertheless a unique source-side
        # anchor? A source-local running index is a weaker anchor than a citable coordinate
        # -- nobody can re-find the unit from it without the generator -- but it is not the
        # same defect as having no anchor at all, and the owner needs the two separated.
        unit_index = p.get("griffith_unit_index")
        ev_anchor = {
            "printed_locator_ambiguous": len(collide) > 1 and not internal_reuse,
            "keys_sharing_locator": len(collide),
            "unique_source_unit_index_present": unit_index is not None,
            "declares_independent_content_control": has_control,
        }
        # Does the locator's own numbering agree with the canonical key, where the source is
        # the same corpus and prints comparable coordinates?
        agree = None
        if r["source_id"] == "IA_WAYBACK_GRIFFITH_AV_1895" and len(nums) >= 3:
            m = re.match(r"kanda (\d+), hymn (\d+)", loc)
            tailnums = re.findall(r"K(\d+):S(\d+):V(\d+)", key)
            if m and tailnums:
                k_s, s_s = int(m.group(1)), int(m.group(2))
                k_c, s_c, _ = (int(x) for x in tailnums[0])
                agree = (k_s == k_c) and (s_s == s_c)
        if r["source_id"] == "SACRED_TEXTS_WYV_SNAPSHOT_2026_09_07":
            m = re.search(r"wyvbk(\d+)\.htm", loc)
            a = re.findall(r"A(\d+)", key)
            if m and a:
                agree = int(m.group(1)) == int(a[0])
        if r["source_id"] == "IA_WAYBACK_GRIFFITH_RV_1896":
            m = re.search(r"rv(\d{2})(\d{3})\.htm", r.get("source_url") or "")
            mm = re.findall(r"M(\d+):S(\d+)", key)
            if m and mm:
                agree = (int(m.group(1)), int(m.group(2))) == (int(mm[0][0]), int(mm[0][1]))
        ck.record(
            "B2.locator_container_agrees_with_canonical_container",
            agree is not None,
            agree is not None,
            agree,
        )
        if loc_present and not collision_ok:
            cats.add("B_FAIL_SOURCE_COORDINATE")
            mitigation = (
                "a unique source unit index and an independent content control are present"
                if unit_index is not None and has_control
                else "a unique source unit index is present but no content control"
                if unit_index is not None
                else "no other source-side anchor is present"
            )
            reasons.append(
                f"printed source_locator addresses {len(collide)} canonical keys at grain "
                f"{gran} (it omits a hierarchy level), so it cannot re-find this unit; "
                f"{mitigation}: " + ", ".join(sorted(collide)[:4])
            )
        if agree is False:
            cats.add("B_FAIL_SOURCE_COORDINATE")
            reasons.append("source coordinate's container disagrees with the canonical key")
        if not loc_present:
            cats.add("B_FAIL_SOURCE_COORDINATE")
            reasons.append("source_locator is empty")
        ev["source_coordinate"] = {
            "locator": loc,
            "numbers": nums,
            "keys_sharing_this_locator": sorted(collide),
            "container_agrees": agree,
            "griffith_unit_index": unit_index,
            **ev_anchor,
        }

        # ---------------- B3 GRANULARITY -------------------------------------------------
        asserted = p.get("alignment")
        asserted_grain = {"EXACT_MANTRA_ALIGNMENT": "MANTRA", "RANGE_ALIGNMENT": "MANTRA_RANGE"}.get(
            asserted
        )
        grain_ok = asserted_grain == gran
        ck.record("B3.asserted_grain_matches_source_unit", True, True, grain_ok)
        ck.record("B3.grain_is_translation_bearing", True, True, gran in {"MANTRA", "MANTRA_RANGE"})
        if not grain_ok:
            cats.add("B_FAIL_GRANULARITY")
            reasons.append(f"asserts {asserted} (={asserted_grain}) but source unit is {gran}")
        if gran in {"HYMN", "SECTION", "OTHER"}:
            cats.add("B_FAIL_GRANULARITY")
            reasons.append(f"source unit is {gran}-grained; not a mantra-level translation")
        # A MANTRA_RANGE must enumerate its complete covered canonical keys. The rows carry
        # printed_span, which is a pair of printed labels, not canonical keys -- so the
        # completeness test is whether every canonical verse in the span is itself staged
        # with the same literal.
        range_complete = None
        covered_keys = None
        if gran == "MANTRA_RANGE" and isinstance(gran_detail.get("printed_span"), list):
            lo, hi = gran_detail["printed_span"]
            prefix = key.rsplit(":", 1)[0]
            width = len(key.rsplit(":", 1)[1]) - 1
            covered_keys = [f"{prefix}:V{n:0{width}d}" for n in range(lo, hi + 1)]
            present = [k for k in covered_keys if k in by_key]
            same_text = [
                k
                for k in present
                if fold_english(by_key[k]["payload"].get("text") or "")
                == fold_english(p.get("text") or "")
            ]
            range_complete = len(present) == len(covered_keys) and len(same_text) == len(
                covered_keys
            )
            ev["range"] = {
                "printed_span": [lo, hi],
                "derived_covered_keys": covered_keys,
                "staged_present": present,
                "same_literal": same_text,
                "complete": range_complete,
            }
        ck.record(
            "B3.range_enumerates_complete_covered_keys",
            gran == "MANTRA_RANGE",
            range_complete is not None,
            range_complete,
        )
        if range_complete is False:
            cats.add("B_FAIL_GRANULARITY")
            reasons.append("MANTRA_RANGE does not cover every canonical key in its printed span")
        ev["granularity"] = {
            "asserted": asserted,
            "asserted_grain": asserted_grain,
            "measured_grain": gran,
            "detail": gran_detail,
        }

        # ---------------- B4 SOURCE SPAN vs CANONICAL SPAN -------------------------------
        if gran == "MANTRA_RANGE":
            spine = "VERIFIED_RANGE" if range_complete else "UNEXPLAINED_MISMATCH"
        elif gran == "MANTRA":
            spine = "EXACT_SPINE"
        else:
            spine = "UNEXPLAINED_MISMATCH"
        ck.record("B4.span_classified", True, True, spine != "UNEXPLAINED_MISMATCH")
        if spine == "UNEXPLAINED_MISMATCH":
            cats.add("B_FAIL_UNEXPLAINED_SPINE")
            reasons.append(f"source/canonical span unexplained at grain {gran}")
        ev["span_class"] = spine

        # ---------------- B5 SOURCE LITERAL ---------------------------------------------
        raw = p.get("text") or ""
        folded = fold_english(raw)
        words = folded.split()
        lit = {
            "non_empty": bool(raw.strip()),
            "word_count": len(words),
            "char_count": len(raw),
            "not_chrome_exact": folded not in CHROME_EXACT,
            "no_chrome_substring": not any(c in raw.lower() for c in CHROME_SUBSTRINGS),
            "no_html_artefact": not bool(HTML_ARTEFACT.search(raw)),
            "not_label_only": not bool(LABEL_ONLY.fullmatch(raw.strip())),
            "materially_textual": len(words) >= 4,
            "has_letters": bool(re.search(r"[A-Za-z]{3,}", raw)),
        }
        for name, ok in lit.items():
            if isinstance(ok, bool):
                ck.record(f"B5.{name}", True, True, ok)
        litbad = [n for n, ok in lit.items() if ok is False]
        if litbad:
            cats.add("B_FAIL_LITERAL")
            reasons.append("literal rejected: " + ", ".join(litbad))
        ev["literal"] = {
            **lit,
            "text_sha256_prefix": None,
            "duplicate_row_count": len(text_to_rows[folded]),
        }

        # ---------------- B6 PROVENANCE --------------------------------------------------
        internal = r["source_id"] == "VEDAGRAPH_CANONICAL_RV_GRIFFITH"
        archive_ts = re.search(r"/web/(\d{14})/", r.get("source_url") or "")
        prov = {
            "translation_source_declared": bool(r.get("source_id")),
            "translator_declared": bool(p.get("translator")),
            "work_edition_declared": bool(p.get("work_edition")),
            "source_locator_declared": bool(loc.strip()),
            "quality_class_declared": bool(r.get("quality_class")),
            # Acquisition: either a retrievable URL, or an explicit internal graph read whose
            # referent key is named and resolvable.
            "acquisition_traceable": bool(r.get("source_url"))
            or (internal and bool(p.get("cross_corpus_source_key"))),
            # Revision identity: a content hash of the bytes read, or an immutable archive
            # timestamp, or -- for an internal read -- the referenced node's own text hash.
            "source_revision_identified": bool(p.get("snapshot_sha256"))
            or bool(archive_ts)
            or (internal and bool(p.get("cross_corpus_source_key"))),
        }
        for name, ok in prov.items():
            ck.record(f"B6.{name}", True, True, ok)
        provbad = [n for n, ok in prov.items() if not ok]
        if provbad:
            cats.add("B_FAIL_PROVENANCE")
            reasons.append("provenance incomplete: " + ", ".join(provbad))
        ev["provenance"] = {
            **prov,
            "source_id": r["source_id"],
            "source_url": r.get("source_url"),
            "snapshot_sha256": p.get("snapshot_sha256"),
            "archive_timestamp": archive_ts.group(1) if archive_ts else None,
            "internal_read": internal,
        }

        # ---------------- B7 CURRENT TARGET STATE ---------------------------------------
        existing = [t for t in translations.get(key, []) if (t.get("language") or "en") == "en"]
        if not existing:
            tstate = "TARGET_HAS_NO_TRANSLATION"
        else:
            same = [t for t in existing if t.get("source_id") == r["source_id"]]
            if same:
                identical = any(fold_english(t.get("text") or "") == folded for t in same)
                tstate = (
                    "TARGET_HAS_TRANSLATION_SAME_SOURCE_IDENTICAL_TEXT"
                    if identical
                    else "TARGET_HAS_TRANSLATION_SAME_SOURCE_CONFLICTING_TEXT"
                )
            else:
                tstate = "TARGET_HAS_TRANSLATION_DIFFERENT_SOURCE"
        ck.record("B7.target_state_classified", True, True, tstate == "TARGET_HAS_NO_TRANSLATION")
        if tstate != "TARGET_HAS_NO_TRANSLATION":
            cats.add("B_CONFLICT_EXISTING_TRANSLATION")
            reasons.append(f"target already carries an English translation: {tstate}")
        ev["target_state"] = {
            "state": tstate,
            "existing": [
                {
                    "source_id": t.get("source_id"),
                    "translator": t.get("translator"),
                    "alignment_level": t.get("alignment_level"),
                    "translation_id": t.get("translation_id"),
                }
                for t in existing
            ],
        }

        # ---------------- B8 CORRECTIONS -------------------------------------------------
        # Does this row depend on a correction, and is that correction a reproducible record
        # rather than a local exception? The M13 population is the live case: those verses
        # are already corrected in the graph, so a staged row landing on one must be
        # reconciled against the correction rather than layered on top of it.
        m13_span = bool(re.match(r"VG:RV:SAK:M01:S0(6[5-9]|70):", key))
        corr = {
            "declares_upstream_correction": bool(p.get("source_label_defect"))
            or bool(p.get("stage_gap_defect"))
            or bool(p.get("label_recovered")),
            "inside_m13_rv_span": m13_span,
            "graph_target_carries_upstream_correction_id": any(
                t.get("upstream_correction_id") for t in existing
            ),
        }
        ck.record("B8.correction_dependency_recorded", True, True, True)
        ev["corrections"] = corr

        # ---------------- recomputed identity claims ------------------------------------
        # The only load-bearing recomputable claim in the artifact: that the target's own
        # Sanskrit is surface-identical to the cited Rigveda verse. Recomputed here from the
        # graph's own two text versions, with the fold stated, because 528 rows' entire case
        # rests on it and 432 of those sit beside a graph relation that says the two
        # passages are a *variant*, not an exact parallel.
        ref = p.get("control_rv_key") or p.get("cross_corpus_source_key")
        if ref:
            a = primary_sanskrit(texts.get(key, []))
            b = primary_sanskrit(texts.get(ref, []))
            if a and b:
                fa = fold_sanskrit(a["text"], a["script"])
                fb = fold_sanskrit(b["text"], b["script"])
                measured_identical = fa == fb
                measured_sandhi_identical = sandhi_insensitive(fa) == sandhi_insensitive(fb)
                claimed = p.get("sanskrit_similarity")
                pair = f"{key}||{ref}"
                ev["recomputed_identity"] = {
                    "reference_key": ref,
                    "claimed_sanskrit_similarity": claimed,
                    "measured_token_dice": token_dice(fa, fb),
                    "measured_identical_after_fold": measured_identical,
                    "measured_identical_ignoring_word_division": measured_sandhi_identical,
                    "claim_is_identity": claimed == 1.0,
                    "identity_claim_reproduced": (claimed == 1.0) == measured_identical
                    if claimed is not None
                    else None,
                    "identity_claim_reproduced_allowing_sandhi": (claimed == 1.0)
                    <= measured_sandhi_identical
                    if claimed is not None
                    else None,
                    "staged_relation_asserted": p.get("relation_asserted"),
                    "graph_relations_between_pair": graph_rels.get(pair, []),
                    "target_script": a["script"],
                    "reference_script": b["script"],
                    "target_text_source": a["source_id"],
                    "reference_text_source": b["source_id"],
                }
                if claimed == 1.0:
                    ck.record(
                        "BX.claimed_sanskrit_identity_reproduced",
                        True,
                        True,
                        measured_sandhi_identical,
                    )
                    # For a cross-corpus reuse row the identity claim IS the justification:
                    # the argument is "this verse's Sanskrit is the same text, therefore a
                    # published translation of that verse is a published translation of
                    # this one". If the texts are not the same, nothing else in the row
                    # supports the assertion, so a false claim here is disqualifying rather
                    # than merely noted.
                    if not measured_sandhi_identical:
                        cats.add("B_FAIL_UNEXPLAINED_SPINE")
                        reasons.append(
                            "claims sanskrit_similarity=1.0 (surface-identical) but the "
                            f"graph's own primary texts differ: token Dice "
                            f"{token_dice(fa, fb)} and still unequal after folding word "
                            f"division, so the reuse of {ref}'s translation is not "
                            "justified by textual identity"
                        )
            else:
                ev["recomputed_identity"] = {"reference_key": ref, "error": "missing text version"}
                ck.record("BX.claimed_sanskrit_identity_reproduced", True, False, None)

        # ---------------- verdict --------------------------------------------------------
        category = "B_PASS"
        for c in PRECEDENCE:
            if c in cats:
                category = c
                break
        out_rows.append(
            {
                "staged_row_id": r["_staged_row_id"],
                "canonical_key": key,
                "veda": r["veda"],
                "source_id": r["source_id"],
                "translator": p.get("translator"),
                "work_edition": p.get("work_edition"),
                "mapping_confidence": conf,
                "resolution_tier": p.get("resolution_tier"),
                "alignment": asserted,
                "measured_grain": gran,
                "span_class": spine,
                "target_state": tstate,
                "gate_b_category": category,
                "gate_b_all_categories": sorted(cats) or ["B_PASS"],
                "gate_b_reasons": reasons,
                "evidence": ev,
            }
        )

    write_jsonl("gate_b_rows.jsonl", out_rows)
    write_jsonl(
        "gate_b_failures.jsonl", [r for r in out_rows if r["gate_b_category"] != "B_PASS"]
    )

    def tally(sel, keyfn):
        c = Counter(keyfn(r) for r in out_rows if sel(r))
        return dict(sorted(c.items(), key=lambda kv: -kv[1]))

    summary = {
        "phase": "2-3",
        "rows_assessed": len(out_rows),
        "rows_in_artifact": len(rows),
        "assessed_fraction": round(len(out_rows) / len(rows), 4),
        "by_category": tally(lambda r: True, lambda r: r["gate_b_category"]),
        "by_category_and_veda": tally(
            lambda r: True, lambda r: f"{r['gate_b_category']}|{r['veda']}"
        ),
        "by_category_and_source": tally(
            lambda r: True, lambda r: f"{r['gate_b_category']}|{r['source_id']}"
        ),
        "pass_by_veda": tally(lambda r: r["gate_b_category"] == "B_PASS", lambda r: r["veda"]),
        "pass_by_source": tally(
            lambda r: r["gate_b_category"] == "B_PASS", lambda r: r["source_id"]
        ),
        "fail_by_veda": tally(lambda r: r["gate_b_category"] != "B_PASS", lambda r: r["veda"]),
        "all_categories_multiset": tally(
            lambda r: True, lambda r: ",".join(r["gate_b_all_categories"])
        ),
        "measured_grain": tally(lambda r: True, lambda r: r["measured_grain"]),
        "span_class": tally(lambda r: True, lambda r: r["span_class"]),
        "target_state": tally(lambda r: True, lambda r: r["target_state"]),
        "checks": ck.report(),
        "checks_without_full_coverage": [
            n for n, d in ck.report().items() if not d["full_coverage"]
        ],
        "categories_declared": list(CATEGORIES),
        "precedence": list(PRECEDENCE),
    }
    write_json("gate_b_summary.json", summary)

    print(f"rows assessed: {len(out_rows)} / {len(rows)}")
    for k, v in summary["by_category"].items():
        print(f"   {v:6d}  {k}")
    print("-- pass by source --")
    for k, v in summary["pass_by_source"].items():
        print(f"   {v:6d}  {k}")
    print("-- checks lacking full coverage --")
    print("   ", summary["checks_without_full_coverage"] or "none")
    print("-- identity reproduction --")
    idc = ck.report().get("BX.claimed_sanskrit_identity_reproduced")
    print("   ", idc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
