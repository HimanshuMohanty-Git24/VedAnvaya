"""Turn the generated VedAnvaya brand PNGs into web-ready texture derivatives.

Why this script exists rather than a manual export.

The generated library is sixteen PNGs totalling 21 MB, and three separate things are
wrong with shipping them as they stand.

**Weight.** Nine of them are full-bleed paper textures between 1.8 MB and 2.1 MB. A hero
that costs 1.9 MB fails the LCP budget on its own, before a single font or script loads.

**Tone.** The paper in those textures is not the brand's paper. Measured over a 160x160
resample, the hero's modal base is #EFE8DD, the footer's #F0E7DA, the Thread of Inquiry's
#EBDEC8 and the OpenGraph plate's #F1E4CE, against a declared manuscript ivory of #F4F0E7.
Laid against a #F4F0E7 page that is a visible seam at the edge of every texture, worst on
the two warmest plates. So each texture is white-balanced onto the brand ivory (or, for the
dark plate, onto carbon ink) before it is encoded: a per-channel multiply that fixes the
paper and leaves ink at ink, because black multiplied by anything is still black.

**Format.** AVIF first, WebP second, both at three widths, so the markup can hand the
browser a `<picture>` and let it choose. Every derivative is regenerated from the source
each run, so the encoder settings live here and not in someone's memory of an export dialog.

The sources are not in the repository. They are generated artwork living outside it, and
committing 21 MB of PNG to carry 900 KB of shipped texture is the wrong trade. What the
repository keeps instead is this script, the derivatives it produces, and a manifest
recording each source's SHA-256, so a later run can prove it started from the same artwork.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image

DEFAULT_SOURCE = Path.home() / "Downloads" / "Generated Asset"
REPO_ROOT = Path(__file__).resolve().parents[1]
TEXTURE_OUT = REPO_ROOT / "frontend" / "public" / "brand" / "textures"
MANIFEST_PATH = REPO_ROOT / "frontend" / "public" / "brand" / "textures" / "manifest.json"

MANUSCRIPT_IVORY = (0xF4, 0xF0, 0xE7)
CARBON_INK = (0x17, 0x18, 0x15)

# Quality settings. AVIF at 62 and WebP at 82 were chosen by encoding the hero plate across
# the range and looking at it: below those the paper grain posterises into flat bands, which
# is precisely the detail the texture exists to carry, and above them the file grows without
# a visible difference. Textures are decorative and sit behind text, so they are allowed to
# be lossy in a way a logo is not.
AVIF_QUALITY = 62
WEBP_QUALITY = 82


@dataclass(frozen=True)
class Texture:
    """One source plate and the shape we want it in."""

    source: str
    slug: str
    role: str
    tone: Literal["paper", "carbon", "none"]
    widths: tuple[int, ...]

    @property
    def target(self) -> tuple[int, int, int] | None:
        if self.tone == "paper":
            return MANUSCRIPT_IVORY
        if self.tone == "carbon":
            return CARBON_INK
        return None


# Widths are chosen per role, not uniformly. A full-bleed hero has to cover a 2560 display,
# so it gets 1920 as its top rung and relies on the texture being soft enough to upscale. A
# quote panel is never wider than the reading measure, so 1280 is already generous, and
# giving it a 1920 rung would ship bytes nothing requests.
TEXTURES: tuple[Texture, ...] = (
    Texture("Hero Background.png", "hero-light", "Homepage hero, light theme", "paper", (1920, 1280, 960)),
    Texture("Dark-Mode Manuscript Texture.png", "hero-dark", "Homepage hero, dark theme", "carbon", (1920, 1280, 960)),
    Texture("Knowledge Connection Field.png", "field-light", "Graph and Atlas headers, light theme", "paper", (1920, 1280, 960)),
    Texture("Footer Background.png", "footer-light", "Footer, light theme", "paper", (1920, 1280)),
    Texture("Quote Backdrop.png", "quote-light", "Featured verse panel", "paper", (1280, 960)),
    Texture("Thread of Inquiry.png", "inquiry-light", "Ask, pre-query state", "paper", (1600, 1120)),
    Texture("Archive Plates.png", "plates-light", "Four Vedas plates reference", "paper", (1536,)),
    Texture("OpenGraph Background Template.png", "og-light", "OpenGraph and social cards", "paper", (1200,)),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def base_tone(image: Image.Image) -> tuple[int, int, int]:
    """The plate's own paper colour: the modal pixel of a small resample.

    Resampling to 160x160 first is what makes the mode meaningful. At full size the modal
    pixel of a grainy scan is whichever single grain value happens to recur most, which
    wanders by a few levels between plates that look identical. Averaging into a small grid
    collapses the grain and leaves the paper.
    """
    from collections import Counter

    small = image.convert("RGB").resize((160, 160), Image.Resampling.BOX)
    counts = Counter(small.get_flattened_data())
    return counts.most_common(1)[0][0]


def rebalance(image: Image.Image, target: tuple[int, int, int]) -> Image.Image:
    """White-balance the plate so its paper reads as the brand's paper.

    Multiplicative per channel, which has the property we need: it moves the paper by the
    full correction and leaves ink almost untouched, because the correction is a ratio and
    ink is near zero. An additive shift would lift the blacks instead, greying every hairline
    on the plate, and the hairlines are the artwork.
    """
    base = base_tone(image)
    rgb = image.convert("RGB")
    channels = []
    for index, channel in enumerate(rgb.split()):
        ratio = target[index] / max(base[index], 1)
        channels.append(channel.point(lambda value, r=ratio: min(255, round(value * r))))
    merged = Image.merge("RGB", channels)
    if image.mode == "RGBA":
        merged.putalpha(image.getchannel("A"))
    return merged


def encode(image: Image.Image, stem: Path, width: int) -> list[dict[str, object]]:
    """Write one width in both formats and report what each cost."""
    height = round(image.height * width / image.width)
    resized = image.resize((width, height), Image.Resampling.LANCZOS)
    written: list[dict[str, object]] = []
    for suffix, params in (
        (".avif", {"quality": AVIF_QUALITY}),
        (".webp", {"quality": WEBP_QUALITY, "method": 6}),
    ):
        path = stem.with_name(f"{stem.name}-{width}{suffix}")
        resized.save(path, **params)
        written.append(
            {
                "file": path.relative_to(REPO_ROOT / "frontend" / "public").as_posix(),
                "width": width,
                "height": height,
                "bytes": path.stat().st_size,
            }
        )
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()

    if not args.source.is_dir():
        print(f"Source directory not found: {args.source}")
        return 1

    TEXTURE_OUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    source_total = 0
    output_total = 0

    for texture in TEXTURES:
        source_path = args.source / texture.source
        if not source_path.exists():
            print(f"  MISSING  {texture.source}")
            continue

        image = Image.open(source_path)
        measured = base_tone(image)
        if texture.target is not None:
            image = rebalance(image, texture.target)

        derivatives: list[dict[str, object]] = []
        for width in texture.widths:
            derivatives.extend(encode(image, TEXTURE_OUT / texture.slug, width))

        source_bytes = source_path.stat().st_size
        derived_bytes = sum(int(d["bytes"]) for d in derivatives)
        source_total += source_bytes
        output_total += derived_bytes

        manifest.append(
            {
                "slug": texture.slug,
                "role": texture.role,
                "source_name": texture.source,
                "source_sha256": sha256(source_path),
                "source_bytes": source_bytes,
                "measured_base_tone": "#%02X%02X%02X" % measured,
                "rebalanced_to": ("#%02X%02X%02X" % texture.target) if texture.target else None,
                "derivatives": derivatives,
            }
        )
        largest = max(int(d["bytes"]) for d in derivatives)
        print(
            f"  {texture.slug:16} base #{measured[0]:02X}{measured[1]:02X}{measured[2]:02X}"
            f" -> {source_bytes / 1024:7.0f} KB source,"
            f" {derived_bytes / 1024:6.0f} KB in {len(derivatives)} files,"
            f" largest {largest / 1024:5.0f} KB"
        )

    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "note": (
                    "Generated by scripts/build_brand_assets.py. Sources are the generated "
                    "brand artwork and are deliberately not committed; their SHA-256 is "
                    "recorded here so a later run can prove it started from the same files."
                ),
                "avif_quality": AVIF_QUALITY,
                "webp_quality": WEBP_QUALITY,
                "textures": manifest,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"\n  {len(manifest)} textures: {source_total / 1024 / 1024:.1f} MB of PNG"
        f" -> {output_total / 1024:.0f} KB of AVIF and WebP"
    )
    print(f"  manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
