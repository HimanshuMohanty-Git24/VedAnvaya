#!/usr/bin/env python3
"""Independent source verification for the Yajurveda rows, against the pinned snapshot.

This exists because 31 staged rows declare `address_forced_without_content_control: true`
and carry a `mapping_method` asserting that "the source prints a corrupt or absent verse
label here, so the address is forced rather than read". That is a claim about the *source*,
and the source is on disk: 45 HTML pages under data/raw/sacred_texts/2026-09-07/wyv, each
named by the sha256 of its own bytes, and each staged row naming the hash of the page it
was read from. So the claim is checkable without trusting the generator -- which matters,
because the generator is not in version control and cannot be inspected or re-run.

The parse is deliberately dumb, because a clever one would be the thing under test. Griffith's
text on these pages is a run of <br>-separated lines in which a new mantra begins with its
printed number followed by a space. Page furniture is an anchor of the form <a>p. 48</a> in
its own paragraph. So: drop the page anchors first so a printed page number can never be
read as a verse label, convert the line breaks to newlines, and split the remaining text on
line-initial integers. Nothing here infers a label from position; a unit either carries a
printed number in the source bytes or it does not.
"""

from __future__ import annotations

import glob
import html as htmlmod
import json
import os
import re
import sys

from gate_bc_common import REPO, load_rows, write_json
from gate_bc_textfold import fold_english, token_dice

WYV_DIR = REPO / "data" / "raw" / "sacred_texts" / "2026-09-07" / "wyv"

PAGE_ANCHOR = re.compile(r"<p>\s*<a[^>]*>\s*p\.\s*\d+\s*</a>\s*</p>", re.I)
ANY_PAGE_ANCHOR = re.compile(r"<a[^>]*>\s*p\.\s*\d+\s*</a>", re.I)
BR = re.compile(r"<br\s*/?>", re.I)
BLOCK_END = re.compile(r"</(p|div|h\d|blockquote)>", re.I)
TAG = re.compile(r"<[^>]+>")
UNIT_START = re.compile(r"^\s*(\d{1,3})\s+(?=\S)")
#: The label is sometimes present but mis-transcribed, which is precisely what the staged
#: rows claim with LABEL_PRINTED_BUT_CORRUPT. Book 20 prints "S5" for 85 -- an S for an 8 --
#: and a digits-only reader silently merges that verse into the one above it, which is how
#: three rows first came back "literal not found in source" when in fact the source has them.
#: So a label made of digit-lookalike glyphs is read as present-but-corrupt, and its repaired
#: value is recorded separately from the glyphs actually printed.
CORRUPT_LABEL = re.compile(r"^\s*([0-9OoSsIilZB]{1,3})\s+(?=[A-ZÀ-ɏ])")
#: A mis-set glyph is ambiguous and must not be repaired by picking one answer. "S" stands in
#: for both 5 and 8 in this typeface, and an earlier version of this table mapped it to 5
#: only, turning the printed "S5" of VS 20.85 into 55 and reporting the row as undetermined.
#: So each ambiguous glyph expands to every digit it could be, the candidate set is reported
#: in full, and whether the canonical number is among the candidates is recorded as one
#: signal -- never as the deciding one, because a repair chosen because it matches the target
#: is not evidence about the target. The printed neighbours remain the actual control.
GLYPH_CANDIDATES = {
    "O": "0", "o": "0", "D": "0",
    "I": "1", "i": "1", "l": "1", "|": "1",
    "Z": "2",
    "S": "58", "s": "58",
    "B": "８8", "G": "6", "b": "6",
}
#: Not every book uses <br> between verses; book 36 runs them inline in one paragraph. There
#: a new unit is a number that follows sentence-ending punctuation and precedes a capital.
INLINE_UNIT = re.compile(r"(?<=[.!?])\s+(\d{1,3})\s+(?=[A-ZÀ-ɏ])")


def label_candidates(glyphs: str) -> list[int]:
    """Every integer the printed glyphs could be, under digit-lookalike substitution."""
    options: list[str] = [""]
    for ch in glyphs:
        digits = ch if ch.isdigit() else GLYPH_CANDIDATES.get(ch, "")
        if not digits:
            return []
        options = [prefix + d for prefix in options for d in digits]
    return sorted({int(o) for o in options if o.isdigit()})


def page_units(path: str) -> list[dict]:
    """Split one Griffith page into printed units, each with its printed label or None."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    # Page furniture goes first: a printed page number must never be mistaken for a verse
    # label, which is the single most likely way this parse could invent an address.
    body = PAGE_ANCHOR.sub("\n", raw)
    body = ANY_PAGE_ANCHOR.sub("\n", body)
    body = BR.sub("\n", body)
    body = BLOCK_END.sub("\n", body)
    body = TAG.sub("", body)
    body = htmlmod.unescape(body)
    # Pages that run their verses inline rather than on <br> lines get the same treatment by
    # first breaking before each inline label.
    body = INLINE_UNIT.sub(lambda m: "\n" + m.group(1) + " ", body)
    lines = [ln.strip() for ln in body.split("\n")]

    units: list[dict] = []
    for ln in lines:
        if not ln:
            continue
        m = UNIT_START.match(ln)
        mc = None if m else CORRUPT_LABEL.match(ln)
        if m or mc:
            glyphs = (m or mc).group(1)
            cands = [int(glyphs)] if glyphs.isdigit() else label_candidates(glyphs)
            units.append(
                {
                    "printed_label": cands[0] if len(cands) == 1 else None,
                    "printed_label_candidates": cands,
                    "printed_label_glyphs": glyphs,
                    "label_was_printed": True,
                    "label_glyphs_corrupt": m is None,
                    "lines": [ln[(m or mc).end() :].strip()],
                    "document_unit_index": len(units),
                }
            )
        elif units:
            units[-1]["lines"].append(ln)
        else:
            units.append(
                {
                    "printed_label": None,
                    "printed_label_glyphs": None,
                    "label_was_printed": False,
                    "label_glyphs_corrupt": False,
                    "lines": [ln],
                    "document_unit_index": 0,
                }
            )
    for u in units:
        u["text"] = " ".join(x for x in u["lines"] if x).strip()
        del u["lines"]
    return units


def main() -> int:
    by_hash: dict[str, str] = {}
    for p in glob.glob(str(WYV_DIR / "*.html")):
        by_hash[os.path.basename(p).split(".")[0]] = p
    meta_by_hash: dict[str, dict] = {}
    for p in glob.glob(str(WYV_DIR / "*.metadata.json")):
        d = json.loads(open(p, encoding="utf-8").read())
        meta_by_hash[d["sha256"]] = d

    rows = [r for r in load_rows() if r["veda"] == "YV"]
    parsed: dict[str, list[dict]] = {}
    out = []
    for r in rows:
        p = r["payload"]
        key = r["canonical_key"]
        sha = p.get("snapshot_sha256")
        vnum = int(re.search(r"V(\d+)$", key).group(1))
        adhyaya = int(re.search(r"A(\d+)", key).group(1))
        rec = {
            "staged_row_id": r["_staged_row_id"],
            "canonical_key": key,
            "adhyaya": adhyaya,
            "canonical_verse_number": vnum,
            "mapping_confidence": r["mapping_confidence"],
            "address_forced_without_content_control": p.get(
                "address_forced_without_content_control"
            ),
            "source_label_defect": p.get("source_label_defect"),
            "stage_gap_defect": p.get("stage_gap_defect"),
            "declared_locator": r.get("source_locator"),
            "snapshot_sha256": sha,
        }
        if not sha:
            # The 12 adhyaya-12 rows name no page hash. The page is nevertheless on disk and
            # the locator names it, so resolve by book number rather than declaring the
            # evidence unavailable -- but record that the row did not pin its own bytes.
            m = re.search(r"wyvbk(\d+)\.htm", r.get("source_locator") or "")
            want = int(m.group(1)) if m else adhyaya
            cand = [h for h, d in meta_by_hash.items() if d.get("wyv_book") == want]
            sha = cand[0] if cand else None
            rec["snapshot_sha256_resolved_from_locator"] = sha
            rec["row_pins_its_own_bytes"] = False
        else:
            rec["row_pins_its_own_bytes"] = True

        if not sha or sha not in by_hash:
            rec["source_available"] = False
            out.append(rec)
            continue
        rec["source_available"] = True
        rec["page"] = meta_by_hash.get(sha, {}).get("retrieval_url")
        if sha not in parsed:
            parsed[sha] = page_units(by_hash[sha])
        units = parsed[sha]

        # Locate the staged literal in the page by content, not by position.
        staged = fold_english(p.get("text") or "")
        best, best_score = None, 0.0
        for u in units:
            sc = token_dice(staged, fold_english(u["text"]))
            if sc > best_score:
                best, best_score = u, sc
        rec["best_matching_unit"] = (
            {
                "document_unit_index": best["document_unit_index"],
                "printed_label": best["printed_label"],
                "printed_label_candidates": best.get("printed_label_candidates"),
                "printed_label_glyphs": best.get("printed_label_glyphs"),
                "label_glyphs_corrupt": best.get("label_glyphs_corrupt"),
                "label_was_printed": best["label_was_printed"],
                "match_score": round(best_score, 4),
                "unit_text_prefix": best["text"][:110],
            }
            if best
            else None
        )
        rec["literal_found_in_pinned_source"] = best_score >= 0.90
        # THE question: does the source print a label for this unit, and does it equal the
        # canonical verse number the row claims?
        if best and best_score >= 0.90:
            rec["printed_label_present_in_source"] = best["label_was_printed"]
            rec["printed_label"] = best["printed_label"]
            own_cands = best.get("printed_label_candidates") or []
            rec["printed_label_candidates"] = own_cands
            rec["printed_label_equals_canonical_verse"] = best["printed_label"] == vnum
            rec["canonical_among_printed_label_candidates"] = vnum in own_cands
            idx = best["document_unit_index"]
            nb = {}
            for off, name in ((-1, "previous"), (1, "next")):
                j = idx + off
                if 0 <= j < len(units):
                    nb[name] = {
                        "printed_label": units[j]["printed_label"],
                        "printed_label_candidates": units[j].get("printed_label_candidates") or [],
                        "printed_label_glyphs": units[j].get("printed_label_glyphs"),
                        "label_was_printed": units[j]["label_was_printed"],
                    }
            rec["neighbours"] = nb
            # Is the label unambiguous in its own neighbourhood: strictly between the
            # previous and next printed labels?
            pv = (nb.get("previous") or {}).get("printed_label")
            nx = (nb.get("next") or {}).get("printed_label")
            pv_c = (nb.get("previous") or {}).get("printed_label_candidates") or (
                [pv] if pv is not None else []
            )
            nx_c = (nb.get("next") or {}).get("printed_label_candidates") or (
                [nx] if nx is not None else []
            )
            rec["label_monotonic_with_neighbours"] = (
                pv is not None
                and nx is not None
                and best["printed_label"] is not None
                and pv < best["printed_label"] < nx
            )
            # The test that actually decides a forced address: do the source's own printed
            # neighbours bracket this canonical slot exactly, leaving it the only verse that
            # can sit here? prev == n-1 and next == n+1 is a source-local control that does
            # not depend on the unit's own (corrupt) label at all. Candidate sets are used on
            # both sides so that one mis-set glyph in a neighbour does not defeat the test.
            rec["neighbours_bracket_canonical_slot_exactly"] = (
                (vnum - 1) in pv_c and (vnum + 1) in nx_c
            )
            # A whole adhyaya can also sit at a constant offset from the canonical spine --
            # Griffith's adhyaya 12 prints label = mantra + 1 for eleven consecutive verses.
            # That is a different shape of determination from bracketing, and collapsing the
            # two would report an offset spine as undetermined.
            offs = sorted(
                {c - vnum for c in own_cands}
                & {c - (vnum - 1) for c in pv_c}
                & {c - (vnum + 1) for c in nx_c}
            )
            rec["constant_offset_consistent_with_neighbours"] = offs
            rec["monotone_offset_determined"] = len(offs) >= 1 and offs != [0]
            rec["source_local_address_determination"] = (
                "PRINTED_LABEL_READ_DIRECTLY"
                if best["printed_label"] == vnum and not best.get("label_glyphs_corrupt")
                else "CORRUPT_GLYPHS_REPAIR_TO_CANONICAL"
                if best["printed_label"] == vnum and best.get("label_glyphs_corrupt")
                else "UNIQUELY_BRACKETED_BY_PRINTED_NEIGHBOURS"
                if (vnum - 1) in pv_c and (vnum + 1) in nx_c
                else "CONSTANT_OFFSET_SPINE_WITH_NEIGHBOURS"
                if rec["monotone_offset_determined"]
                else "ORDER_AND_COUNT_ONLY"
            )
        out.append(rec)

    # Aggregate the answer the owner decision turns on.
    forced = [r for r in out if r["address_forced_without_content_control"] is True]
    controlled = [r for r in out if r["address_forced_without_content_control"] is False]
    unflagged = [r for r in out if r["address_forced_without_content_control"] is None]

    def summarise(group, label):
        return {
            "population": label,
            "rows": len(group),
            "source_available": sum(1 for r in group if r.get("source_available")),
            "literal_found_in_pinned_source": sum(
                1 for r in group if r.get("literal_found_in_pinned_source")
            ),
            "printed_label_present_in_source": sum(
                1 for r in group if r.get("printed_label_present_in_source")
            ),
            "printed_label_equals_canonical_verse": sum(
                1 for r in group if r.get("printed_label_equals_canonical_verse")
            ),
            "label_monotonic_with_neighbours": sum(
                1 for r in group if r.get("label_monotonic_with_neighbours")
            ),
            "rows_pinning_own_bytes": sum(1 for r in group if r.get("row_pins_its_own_bytes")),
        }

    result = {
        "phase": 5,
        "what_this_checks": (
            "whether the pinned Griffith White Yajurveda snapshot actually prints a verse "
            "label for each staged row's unit, independently of the generator's claim that "
            "it does not"
        ),
        "pages_on_disk": len(by_hash),
        "pages_parsed": len(parsed),
        "summaries": [
            summarise(forced, "address_forced_without_content_control=true"),
            summarise(controlled, "address_forced_without_content_control=false"),
            summarise(unflagged, "flag absent (adhyaya 12 population)"),
        ],
        "rows": out,
    }
    write_json("yv_source_verification.json", result)

    for s in result["summaries"]:
        print(f"\n== {s['population']}  (n={s['rows']})")
        for k, v in s.items():
            if k not in {"population", "rows"}:
                print(f"     {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
