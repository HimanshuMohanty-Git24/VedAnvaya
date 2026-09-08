"""Render the source evidence one Atharvaveda skeleton reader is given.

A reader is not shown a modern edition, a previous reading, or a structural
guess. It is shown the printed page, cut so the type is large enough to read,
plus the leaf's own running head and margin so it can state where on the page
it thinks it is. Everything else it must derive from the ink.

Two presentations exist because they cost very different amounts and it is not
obvious in advance which one a reader needs:

``lines``
    Every printed line, cut into overlapping horizontal segments. Each segment
    fills the reader's long edge on its own, so the type appears about twice
    native size. This is the presentation the accent work settled on.

``halves``
    The text block downsampled to the resolution of the real IIIF master and
    split top/bottom. This carries the *same information* as ``lines`` -- it is
    the master, unenlarged -- for roughly a fifth of the tokens, but the type
    appears at native size.

Neither presentation adds detail. The stored 4000px leaves are a server-side
upscale of a 2024px master (see ``fetch_atharvaveda_bsb_scan.py``), so native
resolution is the ceiling and ``halves`` sits exactly on it.

Usage:
    python scripts/av_reader_packet.py 32 <outdir> [--mode lines|halves]
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

from crop_atharvaveda_leaf import READER_LONG_EDGE, find_text_block, leaf_path
from crop_atharvaveda_line import find_lines
from PIL import Image

#: The stored leaves are this many times wider than the IIIF master they were
#: upscaled from. Dividing by it returns a crop to the real pixels.
UPSCALE_FACTOR = 4000 / 2024

#: Vertical padding around a line, as a share of its measured height. A skeleton
#: reader needs the matras above the headline and the descenders below it, and a
#: crop that hugs the ink shaves both.
LINE_PAD = 0.45

#: Segments overlap by this share of their width so no aksara is bisected by a
#: cut and unreadable in both halves.
SEGMENT_OVERLAP = 0.06


def render_lines(
    image: Image.Image, block: tuple[int, int, int, int], outdir: pathlib.Path, canvas: int
) -> list[dict[str, Any]]:
    top = block[1]
    body = image.crop(block)
    rendered: list[dict[str, Any]] = []
    for index, (line_top, line_bottom) in enumerate(find_lines(body)):
        height = line_bottom - line_top
        pad = round(height * LINE_PAD)
        y0 = max(0, line_top - pad)
        y1 = min(body.height, line_bottom + pad)
        strip = body.crop((0, y0, body.width, y1))

        # Two segments is about 1:1 with the master; more is interpolation.
        overlap = round(strip.width * SEGMENT_OVERLAP)
        midpoint = strip.width // 2
        cuts = [(0, midpoint + overlap), (midpoint - overlap, strip.width)]
        files: list[str] = []
        for segment_number, (x0, x1) in enumerate(cuts, start=1):
            segment = strip.crop((x0, 0, x1, strip.height))
            if segment.width > READER_LONG_EDGE:
                scale = READER_LONG_EDGE / segment.width
                segment = segment.resize(
                    (READER_LONG_EDGE, max(1, round(segment.height * scale))),
                    Image.Resampling.LANCZOS,
                )
            path = outdir / f"leaf_{canvas:05d}_line{index:02d}_seg{segment_number}.png"
            segment.save(path)
            files.append(str(path))
        rendered.append(
            {
                "line_index": index,
                "block_y": [y0 + top, y1 + top],
                "height": height,
                "segments": files,
            }
        )
    return rendered


def render_halves(
    image: Image.Image, block: tuple[int, int, int, int], outdir: pathlib.Path, canvas: int
) -> list[dict[str, Any]]:
    body = image.crop(block)
    native = body.resize(
        (round(body.width / UPSCALE_FACTOR), round(body.height / UPSCALE_FACTOR)),
        Image.Resampling.LANCZOS,
    )
    rendered: list[dict[str, Any]] = []
    midpoint = native.height // 2
    overlap = round(native.height * 0.03)
    cuts = [(0, midpoint + overlap), (midpoint - overlap, native.height)]
    for half_number, (y0, y1) in enumerate(cuts, start=1):
        half = native.crop((0, y0, native.width, y1))
        if half.width > READER_LONG_EDGE:
            scale = READER_LONG_EDGE / half.width
            half = half.resize(
                (READER_LONG_EDGE, max(1, round(half.height * scale))), Image.Resampling.LANCZOS
            )
        path = outdir / f"leaf_{canvas:05d}_half{half_number}.png"
        half.save(path)
        rendered.append({"half_index": half_number, "native_y": [y0, y1], "image": str(path)})
    return rendered


def build_packet(canvas: int, outdir: pathlib.Path, mode: str) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    path = leaf_path(canvas)
    with Image.open(path) as handle:
        image = handle.convert("L")
    block = find_text_block(image)

    # `find_text_block` keeps enough margin that the printed page number and the
    # marginal sukta numeral fall inside the crop, so a reader can state its own
    # structural position without a second image. `halves` therefore ships no
    # orientation view; `lines` does, because a line strip shows one line and
    # nothing about where on the leaf it sits.
    orientation: str | None = None
    if mode == "lines":
        whole = image.copy()
        scale = READER_LONG_EDGE / max(whole.size)
        whole = whole.resize(
            (max(1, round(whole.width * scale)), max(1, round(whole.height * scale))),
            Image.Resampling.LANCZOS,
        )
        path_whole = outdir / f"leaf_{canvas:05d}_whole.png"
        whole.save(path_whole)
        orientation = str(path_whole)
        units = render_lines(image, block, outdir, canvas)
    elif mode == "halves":
        units = render_halves(image, block, outdir, canvas)
    else:  # pragma: no cover - argparse constrains this
        raise ValueError(f"unknown mode {mode}")

    return {
        "canvas_index": canvas,
        "mdz_image_id": f"bsb10219750_{canvas:05d}",
        "source_artifact": "BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN",
        "leaf_file": str(path),
        "leaf_size": list(image.size),
        "text_block": list(block),
        "mode": mode,
        "orientation_image": orientation,
        "units": units,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canvas_index", type=int)
    parser.add_argument("outdir", type=pathlib.Path)
    parser.add_argument("--mode", choices=("lines", "halves"), default="lines")
    args = parser.parse_args()
    packet = build_packet(args.canvas_index, args.outdir, args.mode)
    destination = args.outdir / f"packet_{args.canvas_index:05d}_{args.mode}.json"
    destination.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(destination)


if __name__ == "__main__":
    main()
