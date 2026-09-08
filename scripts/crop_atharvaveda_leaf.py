"""Render accent-legible crops of a Roth & Whitney 1856 Atharvaveda leaf.

The 1856 print marks Vedic accent with a subscript bar (anudatta) and a
superscript stroke (svarita).  Both are a few pixels tall in the 4000px BSB
scan, so a whole-page render loses them: the multimodal reader is capped at
about 1568px on the long edge, and a full leaf downsamples past the point
where the marks survive.  This tool finds the inked text block and emits it
as horizontal bands whose width is small enough that the accent layer is
still resolved after that cap.

Usage:
    python scripts/crop_atharvaveda_leaf.py 32 [outdir] [--bands N]
"""

from __future__ import annotations

import argparse
import math
import pathlib

from PIL import Image

# Anchored to the repository rather than the working directory. As a relative
# path this resolved against the CWD, so running the calibration from anywhere
# but the repo root reported LEAF_ABSENT for all 81 lines and the gate emitted
# NEEDS_REVISION for want of a scan that was on disk the whole time.
_REPO = pathlib.Path(__file__).resolve().parents[1]
SCAN_DIR = _REPO / "data/raw/bsb_mdz/2026-09-07/bsb10219750"
BSB_ID = "bsb10219750"
# The reader downsamples to this long edge; bands are cut so that the
# post-downsample line height stays above what the accent marks need.
READER_LONG_EDGE = 1568


def leaf_path(canvas_index: int) -> pathlib.Path:
    return SCAN_DIR / f"{BSB_ID}_{canvas_index:05d}.jpg"


def find_text_block(image: Image.Image) -> tuple[int, int, int, int]:
    """Return (left, top, right, bottom) of the inked block in image pixels.

    Projection runs on a small thumbnail; the block edges are only needed to
    about a millimetre of print, and the full 4000px raster is far more
    detail than that costs to scan in Python.
    """
    full_w, full_h = image.size
    scale = 400 / full_w
    thumb = image.resize((400, max(1, round(full_h * scale))), Image.BILINEAR)
    w, h = thumb.size
    pixels = list(thumb.get_flattened_data())

    # Ignore the scanner's dark gutter and page edges before projecting.
    inset_v, inset_h = int(h * 0.02), int(w * 0.02)
    rows = [0] * h
    cols = [0] * w
    for y in range(inset_v, h - inset_v):
        base = y * w
        for x in range(inset_h, w - inset_h):
            if pixels[base + x] < 128:
                rows[y] += 1
                cols[x] += 1

    row_thresh = max(1, max(rows) * 0.02)
    col_thresh = max(1, max(cols) * 0.02)
    row_hits = [y for y, v in enumerate(rows) if v > row_thresh]
    col_hits = [x for x, v in enumerate(cols) if v > col_thresh]
    if not row_hits or not col_hits:
        return 0, 0, full_w, full_h

    pad = w * 0.012
    return (
        max(0, round((col_hits[0] - pad) / scale)),
        max(0, round((row_hits[0] - pad) / scale)),
        min(full_w, round((col_hits[-1] + pad) / scale)),
        min(full_h, round((row_hits[-1] + pad) / scale)),
    )


def render(canvas_index: int, outdir: pathlib.Path, bands: int | None = None) -> list[pathlib.Path]:
    src = leaf_path(canvas_index)
    image = Image.open(src).convert("L")
    left, top, right, bottom = find_text_block(image)
    block = image.crop((left, top, right, bottom))

    if bands is None:
        # The reader caps the LONG edge.  A band taller than it is wide would
        # be shrunk on its height instead of its width, and the accent layer
        # would go with it, so cut enough bands to keep every one landscape.
        bands = max(1, math.ceil(block.height / block.width))

    outdir.mkdir(parents=True, exist_ok=True)
    written: list[pathlib.Path] = []
    step = block.height / bands
    for index in range(bands):
        band_top = int(index * step)
        band_bottom = block.height if index == bands - 1 else int((index + 1) * step)
        # Overlap so no printed line is bisected between two bands.
        overlap = int(step * 0.04)
        band = block.crop(
            (0, max(0, band_top - overlap), block.width, min(block.height, band_bottom + overlap))
        )
        if band.width > READER_LONG_EDGE:
            scale = READER_LONG_EDGE / band.width
            band = band.resize((READER_LONG_EDGE, round(band.height * scale)), Image.LANCZOS)
        path = outdir / f"leaf_{canvas_index:05d}_band{index + 1}.png"
        band.save(path)
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canvas_index", type=int)
    parser.add_argument("outdir", nargs="?", default="scratch_av_crops")
    parser.add_argument("--bands", type=int, default=None)
    args = parser.parse_args()
    for path in render(args.canvas_index, pathlib.Path(args.outdir), args.bands):
        print(path)


if __name__ == "__main__":
    main()
