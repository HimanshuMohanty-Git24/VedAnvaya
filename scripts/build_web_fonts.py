"""Vendor and subset the verse face, because no CDN can serve it.

## The finding this exists to work around

The Rigveda and the Atharvaveda are held in romanised IAST, and their accents are combining
marks on Latin bases: U+0331 macron below for anudatta, U+030D vertical line above for
udatta in the GRETIL witness, U+0301 acute in the VedaWeb one, plus U+0325 ring below and
U+0310 candrabindu.

The Google Fonts CDN serves **none** of U+0331, U+030D or U+0325, for **any** Latin font.
That was checked rather than assumed: fetch the `css2` stylesheet for Charis SIL, Gentium
Book Plus, Noto Serif, Inter, Newsreader and Tiro Devanagari Sanskrit and read the
`unicode-range` on every `@font-face` it returns. Each one enumerates U+0304, U+0308 and
U+0329 out of the combining block and stops. The fonts contain the other marks; the subsets
do not.

The consequence is that `next/font/google` cannot deliver a working verse face at all, and
the failure is close to invisible: the browser falls back per character, so the marks still
appear, drawn by whatever system font happened to answer, positioned by a shaper that has
lost the run. It looks approximately right and is wrong. That is why the current build ships
verses in Newsreader and nobody noticed.

So the verse face is vendored here, subsetted from the upstream release, and self-hosted.

## Why Charis SIL

Measured against the corpus's own bytes it carries every one of the six combining marks
natively, and it has real GPOS `mark` and `mkmk` tables, so a mark that lands on a letter
that already carries one is placed rather than stacked at offset zero. It is SIL's text face
for exactly this work and it is OFL.

Fraunces, the brand display face, is not a candidate: it has no `mark` table, it is missing
anusvara and n-with-dot-above, and rendering RV 1.1.1 in it detaches the macron from the a
in `visva` and drops it between the words.

Devanagari is not subsetted here. The Samavedic and Yajurvedic surfaces are Devanagari, and
Noto Serif Devanagari covers their Vedic marks and is served correctly by the CDN, so it is
loaded the ordinary way through `next/font/google`.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# Into src rather than public, because next/font/local wants to own the file: it emits the
# @font-face, hashes the filename, adds a preload, and derives fallback metrics so the swap
# does not reflow the verse. A file in public/ would need all of that written by hand.
OUT_DIR = REPO_ROOT / "frontend" / "src" / "fonts"

# The upstream release, pinned. A font is a dependency and an unpinned one is a silent
# rendering change on somebody else's schedule.
RELEASE = "https://github.com/silnrsi/font-charis/releases/download/v6.200/CharisSIL-6.200.zip"
VERSION = "6.200"
FACES = {"CharisSIL-Regular.ttf": "charis-regular", "CharisSIL-Italic.ttf": "charis-italic"}

# What the subset keeps. Ranges rather than a corpus census on purpose: a census would be
# exactly right for today's data and would silently drop a glyph the moment a new witness is
# ingested, which is a failure mode that surfaces as tofu in a verse rather than as an error.
UNICODE_RANGES: list[tuple[int, int, str]] = [
    (0x0020, 0x007E, "Basic Latin"),
    (0x00A0, 0x00FF, "Latin-1 Supplement"),
    (0x0100, 0x017F, "Latin Extended-A"),
    (0x0180, 0x024F, "Latin Extended-B"),
    (0x0250, 0x02AF, "IPA Extensions"),
    (0x02B0, 0x02FF, "Spacing Modifier Letters"),
    # The reason this file exists.
    (0x0300, 0x036F, "Combining Diacritical Marks"),
    (0x1E00, 0x1EFF, "Latin Extended Additional"),
    (0x2000, 0x206F, "General Punctuation"),
    (0x2070, 0x209F, "Super and Subscripts"),
    (0x20A0, 0x20BF, "Currency Symbols"),
    (0x2100, 0x214F, "Letterlike Symbols"),
    (0x2190, 0x21FF, "Arrows"),
    (0x2212, 0x2212, "Minus sign"),
    (0x25CC, 0x25CC, "Dotted circle, the shaper's own failure glyph"),
]

# Kept even though a general subsetter would drop them: these are the tables that place a
# mark relative to its base and to the mark under it. Without them every accent renders at
# the glyph origin, which is what "the font has the character" hides.
LAYOUT_FEATURES = ["ccmp", "mark", "mkmk", "kern", "liga", "calt", "locl", "rlig"]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    from fontTools import subset  # imported here so --help works without fonttools
    from fontTools.ttLib import TTFont

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"  fetching Charis SIL {VERSION}")
    archive = zipfile.ZipFile(io.BytesIO(fetch(RELEASE)))

    unicodes: list[int] = []
    for start, end, _ in UNICODE_RANGES:
        unicodes.extend(range(start, end + 1))

    manifest: list[dict[str, object]] = []
    for member, slug in FACES.items():
        path = next(n for n in archive.namelist() if n.endswith(f"/{member}"))
        raw = archive.read(path)
        source_sha = hashlib.sha256(raw).hexdigest()

        font = TTFont(io.BytesIO(raw))
        before = len(font.getGlyphOrder())

        options = subset.Options()
        options.layout_features = LAYOUT_FEATURES
        options.notdef_outline = True
        options.recalc_bounds = True
        options.drop_tables += ["DSIG"]
        options.name_IDs = ["*"]  # keep the licence in the file, as the OFL requires
        options.name_legacy = True
        options.desubroutinize = False
        options.flavor = "woff2"

        subsetter = subset.Subsetter(options=options)
        subsetter.populate(unicodes=unicodes)
        subsetter.subset(font)
        after = len(font.getGlyphOrder())

        out_path = args.out / f"{slug}.woff2"
        font.flavor = "woff2"
        font.save(out_path)
        font.close()

        size = out_path.stat().st_size
        manifest.append(
            {
                "file": f"src/fonts/{slug}.woff2",
                "family": "Charis SIL",
                "style": "italic" if "italic" in slug else "normal",
                "weight": 400,
                "version": VERSION,
                "licence": "SIL Open Font License 1.1",
                "source": RELEASE,
                "source_member": member,
                "source_sha256": source_sha,
                "glyphs_before": before,
                "glyphs_after": after,
                "bytes": size,
            }
        )
        print(f"  {slug:16} {before} glyphs -> {after}, {size / 1024:.0f} KB")

    (args.out / "manifest.json").write_text(
        json.dumps(
            {
                "note": (
                    "Generated by scripts/build_web_fonts.py. Self-hosted because the Google "
                    "Fonts CDN serves none of U+0331, U+030D or U+0325 for any Latin font, "
                    "and those are the marks this corpus writes its Vedic accents with."
                ),
                "kept_ranges": [
                    {"from": f"U+{a:04X}", "to": f"U+{b:04X}", "block": name}
                    for a, b, name in UNICODE_RANGES
                ],
                "kept_layout_features": LAYOUT_FEATURES,
                "faces": manifest,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"  manifest: {(args.out / 'manifest.json').relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
