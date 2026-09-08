"""Render one printed line of a 1856 Atharvaveda leaf at high magnification.

`crop_atharvaveda_leaf.py` cuts a leaf into landscape bands, which is enough to
make the accent layer *visible*. Calibration showed that is not enough to make
it *assignable*: two readers given band crops record accent marks densely and
agree on only 11-31% of their positions.

This tool exists to test whether magnification is the remaining variable. It
finds a single printed line and cuts it into horizontal segments, so each
segment fills the reader's long edge on its own.

**It adds no detail, and cannot.** The IIIF master for `bsb10219750` is
2024px wide; the stored 4000px scans are a server-side upscale of it (see
`fetch_atharvaveda_bsb_scan.py`). Two segments per line is already about 1:1
with the real pixels, and anything finer is interpolation. What magnification
does buy is perceptual: deciding whether an anudatta bar belongs to the line
above it or the line below it is a spatial judgement, and spatial judgements
get easier when the glyphs are larger, even at fixed information content.
Prefer `--segments 2`; treat 4 as a display convenience, not more evidence.

Usage:
    python scripts/crop_atharvaveda_line.py 32 --line 3 --segments 2 [outdir]
    python scripts/crop_atharvaveda_line.py 32 --list
"""

from __future__ import annotations

import argparse
import pathlib

from crop_atharvaveda_leaf import READER_LONG_EDGE, find_text_block, leaf_path
from PIL import Image

# An accent mark sits clear of the glyph body, so a line crop that hugs the
# ink drops the very thing this tool exists to show. Pad by a share of the
# measured line height rather than a fixed pixel count, because line height
# varies between the verse body and the running head.
VERTICAL_PAD = 0.6
# Lines in this print sit about seven source pixels apart per twenty of line
# height. Project too small and that gap rounds away: at width 400 the whole
# leaf reduces to a median inter-line gap of zero and every line merges into
# its neighbour. 1200 keeps the gap resolved with room to spare.
PROJECTION_WIDTH = 1200


def find_lines(block: Image.Image, min_height: float = 0.5) -> list[tuple[int, int]]:
    """Return (top, bottom) in block pixels for each printed line.

    A run of rows carrying ink is a candidate; runs shorter than `min_height`
    of the typical body-line height are accent strokes rather than lines and
    are dropped, since the crop's vertical padding recovers them anyway.
    """
    w, h = block.size
    scale = PROJECTION_WIDTH / w
    thumb = block.resize(
        (PROJECTION_WIDTH, max(1, round(h * scale))), Image.BILINEAR
    )
    tw, th = thumb.size
    pixels = list(thumb.get_flattened_data())

    inked = []
    for y in range(th):
        base = y * tw
        inked.append(sum(1 for x in range(tw) if pixels[base + x] < 128))

    threshold = max(1, max(inked) * 0.03)
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for y, value in enumerate(inked):
        if value > threshold and start is None:
            start = y
        elif value <= threshold and start is not None:
            runs.append((start, y))
            start = None
    if start is not None:
        runs.append((start, th))
    if not runs:
        return []

    # Accent strokes sit clear of the body and so project as their own short
    # runs. They cannot be told from a line break by gap size — on this leaf a
    # body-to-body gap and a body-to-stroke gap are both about 26 source pixels
    # — so classify by height instead: a run far shorter than a body line is a
    # mark, not a line. The generous VERTICAL_PAD on the crop then pulls those
    # marks back in with the line they belong to.
    heights = sorted(bottom - top for top, bottom in runs)
    body = heights[len(heights) // 2] or 1
    tall = [h for h in heights if h >= body * 0.5]
    if tall:
        body = sorted(tall)[len(tall) // 2]
    lines = [(top, bottom) for top, bottom in runs if (bottom - top) >= body * min_height]

    return [(round(top / scale), round(bottom / scale)) for top, bottom in lines]


def render_line(
    canvas_index: int,
    line_index: int,
    outdir: pathlib.Path,
    segments: int = 4,
) -> list[pathlib.Path]:
    image = Image.open(leaf_path(canvas_index)).convert("L")
    block = image.crop(find_text_block(image))
    lines = find_lines(block)
    if not 0 <= line_index < len(lines):
        raise SystemExit(f"leaf {canvas_index} has {len(lines)} lines; no line {line_index}")

    top, bottom = lines[line_index]
    pad = round((bottom - top) * VERTICAL_PAD)
    line = block.crop(
        (0, max(0, top - pad), block.width, min(block.height, bottom + pad))
    )

    outdir.mkdir(parents=True, exist_ok=True)
    written: list[pathlib.Path] = []
    step = line.width / segments
    for index in range(segments):
        left = int(index * step)
        right = line.width if index == segments - 1 else int((index + 1) * step)
        # Overlap so no aksara is split down the middle between two segments.
        overlap = int(step * 0.03)
        piece = line.crop(
            (max(0, left - overlap), 0, min(line.width, right + overlap), line.height)
        )
        if piece.width != READER_LONG_EDGE:
            scale = READER_LONG_EDGE / piece.width
            piece = piece.resize(
                (READER_LONG_EDGE, max(1, round(piece.height * scale))), Image.LANCZOS
            )
        path = outdir / f"leaf_{canvas_index:05d}_line{line_index:02d}_seg{index + 1}.png"
        piece.save(path)
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canvas_index", type=int)
    parser.add_argument("outdir", nargs="?", default="scratch_av_lines")
    parser.add_argument("--line", type=int, default=None)
    parser.add_argument("--segments", type=int, default=4)
    parser.add_argument("--list", action="store_true", help="report the lines found and stop")
    args = parser.parse_args()

    if args.list or args.line is None:
        image = Image.open(leaf_path(args.canvas_index)).convert("L")
        block = image.crop(find_text_block(image))
        lines = find_lines(block)
        print(f"leaf {args.canvas_index}: block {block.width}x{block.height}, {len(lines)} lines")
        for index, (top, bottom) in enumerate(lines):
            print(f"  line {index:2d}: y {top:5d}-{bottom:5d}  height {bottom - top}")
        return

    for path in render_line(
        args.canvas_index, args.line, pathlib.Path(args.outdir), args.segments
    ):
        print(path)


if __name__ == "__main__":
    main()
