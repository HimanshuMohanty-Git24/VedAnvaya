"""Cross-source comparison: GRETIL IAST vs Sanskrit Wikisource Devanagari.

The two sources are in different scripts, and ``compare.text.classify`` deliberately
refuses to compare across scripts. So the Devanagari side is transliterated to IAST with
the repository's existing deterministic transliterator first, and the resulting reading
is declared COMPARISON_ONLY: it is a derived surface used to classify a difference, and
it never becomes stored text for either source.

Neither source is modified. Output is a TextComparison record per aligned verse plus a
category distribution.

    ./.venv/Scripts/python.exe scripts/compare_samaveda_sources.py
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from vedagraph.compare.text import (
    COMPARATOR_VERSION,
    VersionReading,
    compare_missing,
    compare_readings,
)
from vedagraph.identity import sv_mantra_identity
from vedagraph.ingest.adapters.samaveda_gretil import SamavedaGRETILAdapter
from vedagraph.ingest.adapters.samaveda_wikisource import SamavedaWikisourceAdapter
from vedagraph.models.enums import TextRole
from vedagraph.storage.jsonl import write_jsonl
from vedagraph.transliteration import DevanagariToIAST

GRETIL_SNAPSHOT = Path(
    "data/raw/gretil/2026-09-07/"
    "91c28c0394e94dccc9bad12a08224fbcde0a1194402b610df26647621ed92456.xml"
)
WIKISOURCE_ROOT = Path("data/raw/wikisource_sa/2026-09-07")

# How the two sources are joined, and why it is not by sequence position.
#
# The two sources index verses on DIFFERENT systems, which a first attempt at this
# comparison exposed rather than papered over:
#
#   GRETIL      numbers a verse locally inside its dasati:  1 1 1 0501a -> verse 1
#   Wikisource  labels the same verse with the running whole-Samhita number: 45
#
# Aligning by printed verse number therefore produced 19 spurious MISSING rows out of
# 29 for every dasati except the first, where the two systems coincide. Rather than
# invent a per-unit offset (which would silently assume 10 verses per dasati, a thing
# this edition does not guarantee), the join is on the RUNNING VERSE NUMBER, which both
# sources supply independently: GRETIL prints it in its verse apparatus and Wikisource
# uses it as its verse label. That is a source-provided alignment, not a derived one.
#
# Where the two disagree about which running number a given text carries, that is a real
# cross-source divergence and is reported, not reconciled.
ALIGNMENT: tuple[tuple[str, tuple[int, int, int, int], str], ...] = (
    (
        "1b3005b62194531bb233fbaddfd9fe2da8f46114d69ed19cc043663cc4c87c76.php",
        (1, 1, 1, 1),
        "Purvarcika chanda arcika, prapathaka 1, dasati 1 -> GRETIL ardha 1",
    ),
    (
        "3ffa60f176d76e6b59c87bdbaa32d0a260f9aeb1674b0ddfb9566cc3e4535ed4.php",
        (1, 1, 1, 5),
        "Purvarcika chanda arcika, prapathaka 1, dasati 5 -> GRETIL ardha 1",
    ),
    (
        "eeffe2eeff9ab43463b4d942fe1040eb013a7e975dbb12f8c7b9db55be72d80d.php",
        (2, 0, 0, 1),
        "Wikisource nests Aranya arcika under Purvarcika as 1.2.1; GRETIL makes it arcika 2",
    ),
)

LEFT_VERSION = "GRETIL.SV.KAUTHUMA"
RIGHT_VERSION = "WIKISOURCE.SA.SV.KAUTHUMA.IAST"
OUTPUT = Path("data/canonical/samaveda_pilot_v1/text_comparisons.jsonl")


def main() -> None:
    gretil = SamavedaGRETILAdapter()
    wikisource = SamavedaWikisourceAdapter()
    transliterator = DevanagariToIAST()

    # Join key: the running verse number the source itself prints.
    parsed = gretil.parse_structure(GRETIL_SNAPSHOT)
    gretil_by_running: dict[int, tuple[tuple[int, ...], str]] = {}
    ambiguous_running: set[int] = set()
    for verse in parsed.verses:
        text = gretil.verse_text(verse)
        for running in set(verse.running_numbers):
            if running in gretil_by_running:
                ambiguous_running.add(running)
                continue
            gretil_by_running[running] = (verse.coordinates, text)

    comparisons = []
    notes: list[str] = []
    numbering_divergences: list[str] = []
    for filename, (arcika, prapathaka, ardha, dasati), rationale in ALIGNMENT:
        snapshot = WIKISOURCE_ROOT / filename
        page = wikisource.parse_dasati(snapshot)
        records = wikisource.parse(
            snapshot,
            snapshot_id=f"WIKISOURCE_SA:{filename.split('.')[0]}",
            arcika=arcika,
            prapathaka=prapathaka,
            ardha=ardha,
            dasati=dasati,
        )
        notes.append(
            f"{page.page_title} rev {page.revision_id}: {len(records)} verses parsed; "
            f"{len(page.unparsed_remainder)} unparsed fragment(s). {rationale}"
        )
        for record in records:
            # The Wikisource verse label IS the running whole-Samhita number.
            running = int(record.hierarchy["verse"])
            matched = gretil_by_running.get(running)
            if matched is None:
                passage_key = f"SV-UNJOINED:running:{running}"
                comparisons.append(
                    compare_missing(
                        passage_key=passage_key,
                        citation=f"SV running {running}",
                        left_version_id=LEFT_VERSION,
                        right_version_id=RIGHT_VERSION,
                    )
                )
                continue
            coordinates, left_text = matched
            passage_key = sv_mantra_identity(*coordinates)[0]
            citation = (
                f"SV {'.'.join(str(v) for v in coordinates)} (running {running})"
            )
            if coordinates[:4] != (arcika, prapathaka, ardha, dasati):
                numbering_divergences.append(
                    f"running {running}: Wikisource places it in unit "
                    f"{(arcika, prapathaka, ardha, dasati)} but GRETIL's running number "
                    f"puts the same verse at {coordinates}"
                )
            if running in ambiguous_running:
                numbering_divergences.append(
                    f"running {running}: GRETIL prints this number on more than one verse"
                )
            right_iast = transliterator.transliterate(record.text_original)
            comparisons.append(
                compare_readings(
                    passage_key=passage_key,
                    citation=citation,
                    left=VersionReading(LEFT_VERSION, left_text, TextRole.PRIMARY_TEXT),
                    right=VersionReading(RIGHT_VERSION, right_iast, TextRole.COMPARISON_ONLY),
                )
            )

    comparisons.sort(key=lambda item: item.passage_key)
    written = write_jsonl(OUTPUT, comparisons)

    print(f"comparator: {COMPARATOR_VERSION}")
    for note in notes:
        print(f"  {note}")
    print(f"\nnumbering divergences detected: {len(numbering_divergences)}")
    for line in numbering_divergences[:12]:
        print(f"  {line}")
    print(f"\naligned verse comparisons: {written} -> {OUTPUT}")
    print("\ncategory distribution:")
    for category, count in sorted(Counter(c.category.value for c in comparisons).items()):
        print(f"  {category}: {count}")
    print("\nsimilarity: "
          f"min={min(c.similarity for c in comparisons):.4f} "
          f"mean={sum(c.similarity for c in comparisons) / len(comparisons):.4f} "
          f"max={max(c.similarity for c in comparisons):.4f}")
    print("\nlowest-similarity examples:")
    for c in sorted(comparisons, key=lambda item: item.similarity)[:6]:
        print(f"  {c.citation} {c.category.value} sim={c.similarity:.4f} "
              f"tokens {c.left_token_count}/{c.right_token_count}: {c.classification_basis}")


if __name__ == "__main__":
    main()
