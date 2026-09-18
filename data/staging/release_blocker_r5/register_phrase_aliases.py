"""Register the multi-word aliases in the concept registry, so the generator makes the edges.

Each phrase was confirmed to occur as a run of consecutive folded tokens, and audited PER
ALIAS rather than per row: every one reaches only its own form and none reaches a different
expression. The third pressing's four phrases reach exactly the SIX loci its own registry
definition names as read-but-unreachable -- RV 3.28.5, RV 4.34.4, RV 4.35.9, RV 8.57.1,
AVS 6.47.3, AVS 9.1.13 -- and no seventh, which is an independent confirmation rather than
a new claim.

The midday pressing's two phrases add NO passage: its single-token aliases already reach all
seven of its mentions. They are registered anyway, because the clause asks that phrase
matching REACH multi-word entities and a mechanism demonstrated on one of the two is a
mechanism demonstrated on a sample of one.

The registry's own stale sentence is corrected in the same pass. It reads "none of them is
reachable ... SANDHI_MATCH_VEDAS restricts the production substring pass to the Samaveda",
which was true and is now not: the phrase pass is not the substring pass and is not
restricted to the Samaveda.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "data" / "domain" / "vedagraph_domain_v2" / "domain_registry.yaml"
RITUAL_V3 = ROOT / "data" / "domain" / "vedagraph_domain_v2" / "domain_entities_ritual_v3.yaml"

TRTIYA_PHRASES = ["tṛtīye savane", "tṛtīye savana", "tṛtīyaṃ savanaṃ", "tṛtīyaṃ savanam"]
MADHYA_PHRASES = ["mādhyaṃdine savane", "mādhyandine savana"]


def _insert_after(text: str, anchor: str, addition: str) -> str:
    if anchor not in text:
        raise SystemExit(f"anchor not found:\n{anchor[:160]}")
    if addition.strip() in text:
        raise SystemExit("already registered")
    return text.replace(anchor, anchor + addition, 1)


def main() -> None:
    raw = REGISTRY.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("domain_registry.yaml contains CRLF; this writer assumes LF")
    text = raw.decode("utf-8")

    text = _insert_after(
        text,
        "  aliases_sa:\n  - tṛtīyamāptaṃṃ\n",
        "".join(f"  - {p}\n" for p in []) ,
    ) if False else text

    # third pressing
    anchor = "  aliases_sa:\n  - tṛtīyamāptaṃṃ\n"
    addition = "  aliases_sa_phrases:\n" + "".join(f"  - {p}\n" for p in TRTIYA_PHRASES)
    text = _insert_after(text, anchor, addition)

    # midday pressing
    anchor = (
        "  aliases_sa:\n  - mādhyaṃdine\n  - mādhyandine\n  - mādhyaṃndinam\n"
    )
    addition = "  aliases_sa_phrases:\n" + "".join(f"  - {p}\n" for p in MADHYA_PHRASES)
    text = _insert_after(text, anchor, addition)

    # correct the definition sentence that the phrase pass has just falsified
    stale = (
        "All six were\n    read and all six are this act -- and none of them is reachable, "
        "because the third pressing is the\n    only one of the three the corpus never "
        "writes as one word."
    )
    fixed = (
        "All six were\n    read, all six are this act, and all six are now REACHED by the "
        "mention layer's phrase pass,\n    which matches a run of consecutive whole tokens "
        "and is not the Samaveda-only substring pass.\n    The third pressing is still the "
        "only one of the three the corpus never writes as one word."
    )
    if stale in text:
        text = text.replace(stale, fixed, 1)
        corrected = True
    else:
        corrected = False

    REGISTRY.write_bytes(text.encode("utf-8"))
    print(f"domain_registry.yaml: phrases registered, stale sentence corrected={corrected}")

    # the ritual_v3 fragment carries the same two entries
    raw = RITUAL_V3.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("domain_entities_ritual_v3.yaml contains CRLF")
    text = raw.decode("utf-8")
    added = 0
    for label, phrases in (
        ("tṛtīya savana", TRTIYA_PHRASES),
        ("mādhyandina savana", MADHYA_PHRASES),
    ):
        marker = f"    preferred_label_sa: {label}\n"
        if marker not in text:
            continue
        block = "    aliases_sa_phrases:\n" + "".join(f"    - {p}\n" for p in phrases)
        if block.strip() in text:
            continue
        text = text.replace(marker, marker + block, 1)
        added += 1
    RITUAL_V3.write_bytes(text.encode("utf-8"))
    print(f"domain_entities_ritual_v3.yaml: {added} entries given phrase aliases")


if __name__ == "__main__":
    main()
