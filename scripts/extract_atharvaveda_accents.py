"""Extract the Vedic accent layer of a 1856 Atharvaveda leaf geometrically.

Three independent readers, given one printed line at 1:1, placed its accent
marks identically (1.000 agreement, against 0.098-0.306 at whole-leaf band
presentation). Reading their accounts, none of them did anything linguistic.
All three projected rows, found the band the anudatta bars sit in, and
attributed each bar to the headline a fixed distance above it:

    "the middle line's baseline sits at y~180, its own bars form a tight band
     at y~205-225, while a second bar band at y~38-55 is a full line-pitch too
     high and belongs to the line above -- no bar was borderline"

That is deterministic image processing, and it is the affordable half of the
problem: reading one line per model call solves the accent layer but costs
about 2.5 billion tokens for the corpus. This module does the geometry in
code so that a model only has to read the skeleton, which already agrees to
98.7% at band presentation.

What this does NOT do is decide which aksara a mark belongs to. It reports
marks with their x extents; binding them to positions in a transcribed
skeleton is a separate step and a harder one.

Usage:
    python scripts/extract_atharvaveda_accents.py 32 --line 12
    python scripts/extract_atharvaveda_accents.py 32 --all
"""

from __future__ import annotations

import argparse
import json

from crop_atharvaveda_leaf import find_text_block, leaf_path
from crop_atharvaveda_line import VERTICAL_PAD, find_lines
from PIL import Image

INK = 128

# A svarita is a short upright stroke standing above the headline; an anudatta
# is a short horizontal dash sitting below the glyph body. Both are small, and
# nearly everything else in the gutter between two lines is either a descender
# or a piece of the neighbouring line.
#
# The readers rejected false positives by shape rather than position, and gave
# the measurements: the vocalic-r descenders under kr and pr are curved and
# 21-33px tall, against an anudatta dash that is straight and about 10px.
# The two marks are not variants of one shape and cannot share one size rule.
# Measured on canvas n32 line 12, against a reading three independent readers
# agreed on exactly:
#
#   anudatta  a broad flat dash under the body   w 35-39  h  9-13  aspect ~3.5
#   svarita   a narrow upright stroke above      w  9-12  h 31-35  aspect ~0.3
#
# Everything else in those bands is one of three things, and each is excluded
# by shape rather than position: the upper halves of ordinary aksaras (wide
# *and* tall, w 53-69), the vocalic-r descenders under kr and pr that the
# readers had to reject by hand (curved, too tall for a dash), and slices of
# the terminal dandas (which run out of the band at both ends).
SHAPES = {
    "anudatta": {"w": (20, 45), "h": (5, 18), "aspect": (1.2, 8.0)},
    "svarita": {"w": (6, 16), "h": (20, 45), "aspect": (0.15, 0.7)},
}


def binarise(image: Image.Image) -> tuple[list[bool], int, int]:
    w, h = image.size
    data = list(image.get_flattened_data())
    return [v < INK for v in data], w, h


def row_ink(mask: list[bool], w: int, h: int) -> list[int]:
    return [sum(mask[y * w : (y + 1) * w]) for y in range(h)]


def find_headline(rows: list[int]) -> int:
    """The single densest row of the line: the middle of the sirorekha."""
    return max(range(len(rows)), key=lambda y: rows[y])


def find_headline_band(rows: list[int], share: float = 0.35) -> tuple[int, int]:
    """The full vertical extent of the sirorekha, not just its densest row.

    Devanagari hangs from a continuous horizontal rule, and in this print that
    rule is about eighteen pixels thick. Taking only its densest row and
    treating everything above as clear is wrong by most of its thickness, and
    the error is not cosmetic: a svarita band that reaches down into the rule
    lets a flood fill run the whole width of the line, so every svarita is
    swallowed into one line-long component and then discarded for being too
    big. That is why the first version of this module found seven of seven
    anudatta and none of three svarita.
    """
    peak = find_headline(rows)
    floor = rows[peak] * share
    top = peak
    while top > 0 and rows[top - 1] >= floor:
        top -= 1
    bottom = peak
    while bottom < len(rows) - 1 and rows[bottom + 1] >= floor:
        bottom += 1
    return top, bottom


def components(mask: list[bool], w: int, top: int, bottom: int) -> list[tuple[int, int, int, int]]:
    """Connected ink blobs within a horizontal band, as (x0, y0, x1, y1).

    Iterative flood fill: a band is at most a few tens of rows, so this stays
    small, and recursion would not.
    """
    seen = bytearray((bottom - top) * w)
    boxes: list[tuple[int, int, int, int]] = []
    for sy in range(top, bottom):
        for sx in range(w):
            idx = (sy - top) * w + sx
            if seen[idx] or not mask[sy * w + sx]:
                continue
            stack = [(sx, sy)]
            seen[idx] = 1
            x0 = x1 = sx
            y0 = y1 = sy
            while stack:
                cx, cy = stack.pop()
                x0, x1 = min(x0, cx), max(x1, cx)
                y0, y1 = min(y0, cy), max(y1, cy)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if not (0 <= nx < w and top <= ny < bottom):
                        continue
                    nidx = (ny - top) * w + nx
                    if seen[nidx] or not mask[ny * w + nx]:
                        continue
                    seen[nidx] = 1
                    stack.append((nx, ny))
            boxes.append((x0, y0, x1, y1))
    return boxes


def classify(box: tuple[int, int, int, int], kind: str, band: tuple[int, int]) -> dict | None:
    x0, y0, x1, y1 = box
    width, height = x1 - x0 + 1, y1 - y0 + 1

    # Material entering from the top of either band belongs to the line above,
    # which is the attribution error this whole exercise exists to avoid.
    if y0 <= band[0]:
        return None
    # An anudatta floats free in the gutter, so a blob that also runs out of
    # the bottom is a descender or a danda passing through. A svarita is the
    # exception: it legitimately runs down to the rule and so must be allowed
    # to touch the bottom of its band.
    #
    # This matters more than it sounds. A vocalic-r descender clipped by the
    # band edge presents as a broad flat dash and passes every shape test --
    # it is exactly the false positive all three readers rejected by hand
    # under kr and pr.
    if kind == "anudatta" and y1 >= band[1] - 1:
        return None

    shape = SHAPES[kind]
    if not shape["w"][0] <= width <= shape["w"][1]:
        return None
    if not shape["h"][0] <= height <= shape["h"][1]:
        return None
    if not shape["aspect"][0] <= width / height <= shape["aspect"][1]:
        return None
    return {
        "type": kind,
        "codepoint": "U+0952" if kind == "anudatta" else "U+0951",
        "x0": x0,
        "x1": x1,
        "width": width,
        "height": height,
    }


def line_pitch(lines: list[tuple[int, int]]) -> float:
    """Median distance between consecutive line tops.

    The bands are placed as fractions of this rather than of a line's own
    measured height, because a line's height is not stable: whether the
    anudatta bars merge into the body's ink run or stand apart from it varies
    line to line. On canvas n32 that made line 19's run 160px against line
    12's 121, and a band derived from the run bottom then searched the empty
    space *below* the bars. Pitch does not move.
    """
    if len(lines) < 2:
        return 0.0
    gaps = sorted(lines[i + 1][0] - lines[i][0] for i in range(len(lines) - 1))
    return float(gaps[len(gaps) // 2])


# Where the two marks sit relative to the top of the sirorekha, in units of
# line pitch. Measured on canvas n32 lines 12 and 19, whose bars fall at
# 0.61-0.70 and 0.58-0.63 of pitch below the rule respectively, and
# corroborated by three readers who each described the same fixed banding.
ANUDATTA_BAND = (0.50, 0.80)
SVARITA_BAND = (-0.25, 0.0)


def extract_line(block: Image.Image, top: int, bottom: int, pitch: float) -> dict:
    pad = round((bottom - top) * VERTICAL_PAD)
    crop_top = max(0, top - pad)
    line = block.crop((0, crop_top, block.width, min(block.height, bottom + pad)))
    mask, w, h = binarise(line)
    rows = row_ink(mask, w, h)

    body_top, body_bottom = top - crop_top, bottom - crop_top
    core = rows[body_top:body_bottom]
    if not core:
        return {"headline": None, "marks": []}
    rule_top, rule_bottom = (body_top + v for v in find_headline_band(core))
    headline = body_top + find_headline(core)

    # Both bands are placed off the rule, at fractions of line pitch. The
    # svarita band stops two rows short of the rule, or a flood fill escapes
    # along it and swallows every svarita into one line-long component.
    span = pitch if pitch else float(body_bottom - body_top)
    svarita_band = (
        max(0, rule_top + round(span * SVARITA_BAND[0])),
        rule_top - 2,
    )
    anudatta_band = (
        min(h, rule_top + round(span * ANUDATTA_BAND[0])),
        min(h, rule_top + round(span * ANUDATTA_BAND[1])),
    )

    marks: list[dict] = []
    for band, kind in ((svarita_band, "svarita"), (anudatta_band, "anudatta")):
        lo, hi = band
        if hi <= lo:
            continue
        for box in components(mask, w, lo, hi):
            found = classify(box, kind, (lo, hi))
            if found:
                marks.append(found)

    marks.sort(key=lambda m: m["x0"])
    word_spans = _word_spans_from_rule(mask, w, rule_top, rule_bottom)
    return {
        "headline": headline,
        "rule": [rule_top, rule_bottom],
        "body": [body_top, body_bottom],
        "svarita_band": list(svarita_band),
        "anudatta_band": list(anudatta_band),
        "marks": marks,
        "anudatta_count": sum(1 for m in marks if m["type"] == "anudatta"),
        "svarita_count": sum(1 for m in marks if m["type"] == "svarita"),
        "word_spans": word_spans,
    }


# Minimum gap width (pixels) to be treated as a word boundary rather than
# intra-word ink variation. Measured on canvas n32: word gaps are 28-60px;
# intra-word dark spots never exceed 8px.
#
# This is a minimum *gap*, and it has to be applied to the blank run between
# two inked runs. It was once applied to the width of the inked run instead,
# which is a different measurement and let any narrow break split a word.
# Canvas n32 never showed the difference -- its rule does not break inside a
# word -- but the sirorekha is a cast bar and elsewhere it does: 2px inside
# sadhriicii-rvishvaa on n411 line 9, 11px after the avagraha on n159 line 2,
# 5px in the double danda on n430 line 5. Splitting there put one extra span
# ahead of the marks and shifted every carrier assignment after it by a word.
_WORD_GAP_MIN_PX = 14


def _word_spans_from_rule(
    mask: list[bool], w: int, rule_top: int, rule_bottom: int
) -> list[tuple[int, int]]:
    """Word-level x spans from sirorekha column ink profile.

    The sirorekha (headline bar) runs continuously across every aksara within
    a word and breaks between words. A blank run of at least _WORD_GAP_MIN_PX
    columns is a word gap; anything narrower is a break in the cast rule and
    is bridged. Returns (x0, x1) in the same coordinate space as mark x0/x1.
    """
    col_ink = [
        sum(1 for y in range(rule_top, rule_bottom + 1) if mask[y * w + x]) for x in range(w)
    ]
    threshold = 1  # any ink at all counts as rule present
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for x, v in enumerate(col_ink):
        if v >= threshold and start is None:
            start = x
        elif v < threshold and start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, w - 1))

    # Bridge the narrow breaks. The test is on the blank run *between* two
    # inked runs, which is what a word gap actually is.
    spans: list[list[int]] = []
    for x0, x1 in runs:
        if spans and x0 - spans[-1][1] - 1 < _WORD_GAP_MIN_PX:
            spans[-1][1] = x1
        else:
            spans.append([x0, x1])
    return [(x0, x1) for x0, x1 in spans]


def extract(canvas_index: int, line_index: int | None = None) -> dict:
    image = Image.open(leaf_path(canvas_index)).convert("L")
    block = image.crop(find_text_block(image))
    lines = find_lines(block)
    pitch = line_pitch(lines)
    wanted = range(len(lines)) if line_index is None else [line_index]

    out = []
    for index in wanted:
        if not 0 <= index < len(lines):
            raise SystemExit(f"leaf {canvas_index} has {len(lines)} lines; no line {index}")
        top, bottom = lines[index]
        result = extract_line(block, top, bottom, pitch)
        result["line_index"] = index
        out.append(result)
    return {
        "canvas_index": canvas_index,
        "lines_detected": len(lines),
        "line_pitch": pitch,
        "lines": out,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canvas_index", type=int)
    parser.add_argument("--line", type=int, default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit the full record")
    args = parser.parse_args()

    result = extract(args.canvas_index, None if args.all else args.line)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for line in result["lines"]:
        print(
            f"line {line['line_index']:2d}: "
            f"{line['anudatta_count']:2d} anudatta, {line['svarita_count']:2d} svarita"
        )


if __name__ == "__main__":
    main()
