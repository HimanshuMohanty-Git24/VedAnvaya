#!/usr/bin/env python3
"""Owner decision D: inventory the LOAR Veda-recitationer deposit. Claim nothing.

The deposit was flagged by the Rigveda audio agent as a live lead for the Samavedic gap,
partly because Wave 0 had rested that gap on every candidate having an unnamed reciter and
this collection names its reciters. Decision D makes it a priority investigation and
forbids claiming any Samavedic coverage from it until each item is classified.

So this classifies. It does not attach anything to any canonical key, and the
`candidate_canonical_work` field is a *candidate*, never a mapping.

Classification is from what the source itself states -- item title, stated author/reciter,
and the collection's own catalogue item -- never from "Samaveda" appearing in a title and
never from a reciter's name alone, both of which decision D forbids.
"""

from __future__ import annotations

import json
import pathlib
import re
import urllib.request
from typing import Any

COLLECTION = "57bd2a3c-22c3-48ce-b9e5-ac536a89bc3d"
API = "https://loar.kb.dk/server/api"
OUT = pathlib.Path("data/staging/loar_samaveda")

GENRE = {
    "ARCIKA_RECITATION": "ARCIKA_RECITATION",
    "GRAMAGEYAGANA": "GRAMAGEYAGANA",
    "ARANYAKAGEYAGANA": "ARANYAKAGEYAGANA",
    "UHAGANA": "UHAGANA",
    "UHYAGANA": "UHYAGANA",
    "OTHER_SAMAVEDIC": "OTHER_SAMAVEDIC",
    "UNKNOWN": "UNKNOWN",
}


def get(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        return payload


def first(md: dict[str, Any], field: str) -> str | None:
    entries = md.get(field) or []
    return entries[0].get("value") if entries else None


def classify(title: str, author: str | None) -> tuple[str, str, str, str]:
    """Return (stated_veda, stated_recension, genre, evidence).

    Deliberately conservative. A title naming a gana class is strong evidence of genre; a
    title naming only "Samaveda" is not evidence of arcika, and is classified UNKNOWN or
    OTHER_SAMAVEDIC rather than guessed upward.
    """
    t = title.lower()

    # Checked before the gana-class branches below because "Aranyakagana" names its class
    # without the word "gramageya" or "samaveda" -- the first pass missed it entirely and
    # filed a genuine Samavedic gana item as UNKNOWN.
    if "aranyakagana" in t or "aranyageya" in t or "aranyakageya" in t:
        return (
            "SV",
            "JAIMINIYA_PROBABLE",
            GENRE["ARANYAKAGEYAGANA"],
            "Title states Aranyakagana, the Aranyakageyagana class by name. Same Nambudiri "
            "reciters as the item titled 'Samaveda - Nambudiri Jaiminiya'. Probable, not "
            "verified.",
        )
    if "madhyandina" in t:
        return (
            "YV",
            "MADHYANDINA_STATED",
            "NOT_SAMAVEDIC",
            "Title states Sukla Yajurveda - Madhyandina Samhita. That is the recension this "
            "product holds, and it is a live lead for the 190 Yajurvedic verses Wave 1 left "
            "blocked on rights and granularity -- this deposit's rights are open, so the "
            "rights half of that blocker does not apply here. Granularity does: the item "
            "carries far fewer files than the Samhita has adhyayas.",
        )
    if "kanva" in t:
        return (
            "YV",
            "KANVA_STATED",
            "NOT_SAMAVEDIC",
            "Title states Kanva Samhita. Kanva is a different Sukla Yajurveda recension from "
            "the Madhyandina this product holds, and must not be substituted for it.",
        )
    if "aitareya" in t:
        return (
            "RV",
            "AITAREYA_STATED",
            "NOT_SAMAVEDIC",
            "An Aitareya Brahmana or Aranyaka recitation -- Rigvedic ritual prose rather "
            "than Samhita. Supplementary evidence corpus, not core.",
        )
    if "introdu" in t:
        return (
            "N/A",
            "N/A",
            "NOT_SAMAVEDIC",
            "The collection's own introduction, not a recitation.",
        )
    if "gramageya" in t:
        return (
            "SV",
            "JAIMINIYA_PROBABLE",
            GENRE["GRAMAGEYAGANA"],
            "Title states Gramageya, which is the Gramageyagana class by name. Recension "
            "not stated at item level; the reciters are Nambudiri, the Kerala community "
            "that preserves the Jaiminiya Samaveda, and a sibling item in this same "
            "collection is titled 'Samaveda - Nambudiri Jaiminiya'. Probable, not verified.",
        )
    if "uhaganam" in t or "uhyaganam" in t or "uhagana" in t:
        genres = []
        if "uhaganam" in t or re.search(r"\buhagana", t):
            genres.append("UHAGANA")
        if "uhyaganam" in t or re.search(r"\buhyagana", t):
            genres.append("UHYAGANA")
        return (
            "SV",
            "JAIMINIYA_PROBABLE",
            "+".join(genres) if genres else GENRE["OTHER_SAMAVEDIC"],
            "Title names Uhaganam and/or Uhyaganam explicitly. Same Nambudiri reciters and "
            "same collection as the item titled Nambudiri Jaiminiya. Probable, not verified.",
        )
    if "jaiminiya" in t:
        return (
            "SV",
            "JAIMINIYA_STATED",
            GENRE["OTHER_SAMAVEDIC"],
            "Title states Jaiminiya. This is a different Samavedic recension from the "
            "Kauthuma arcika this product holds, and the campaign forbids merging them.",
        )
    if "samaveda" in t or "samagana" in t:
        return (
            "SV",
            "NOT_STATED",
            GENRE["UNKNOWN"],
            "Title names the Samaveda without stating a recension or a genre. Decision D "
            "forbids inferring arcika from 'Samaveda' alone, so this stays UNKNOWN pending "
            "the collection catalogue or an audible check.",
        )
    if "rgveda" in t or "rigveda" in t:
        return (
            "RV",
            "SAKALA_PROBABLE",
            "NOT_SAMAVEDIC",
            "Title states Rgveda Samhita. Recension not stated at item level; the "
            "segmented delivery of this master is already the accepted Rigvedic source.",
        )
    if "atharvaveda" in t:
        recension = "SAUNAKA_STATED" if "saunaka" in t else "NOT_STATED"
        return (
            "AV",
            recension,
            "NOT_SAMAVEDIC",
            "Title states Atharvaveda"
            + (
                " - Saunaka Samhita, which is the recension this product holds."
                if "saunaka" in t
                else ", recension not stated."
            ),
        )
    # "Tattiriya" as the deposit spells it slipped a tittiriya/taittiriya test and left a
    # Krsna-Yajurveda item unclassified. Transliteration variance is the rule here, not the
    # exception, so match on the stem.
    if re.search(r"t[ai]tt?[ai]riya", t):
        return (
            "YV",
            "TAITTIRIYA_STATED",
            "NOT_SAMAVEDIC",
            "Title states Tittiriya. That is Krsna-Yajurveda, not the Madhyandina this "
            "product holds, and it is explicitly forbidden as a Madhyandina substitute.",
        )
    if "catalogue" in t:
        return (
            "ALL",
            "N/A",
            "NOT_SAMAVEDIC",
            "A catalogue of the collection rather than a recitation. This is the document "
            "that would settle every recension and genre question below.",
        )
    return ("UNKNOWN", "NOT_STATED", GENRE["UNKNOWN"], "Title does not state a Veda.")


def main() -> int:
    data = get(f"{API}/discover/search/objects?dsoType=item&scope={COLLECTION}&size=100")
    objects = data["_embedded"]["searchResult"]["_embedded"]["objects"]
    total = data["_embedded"]["searchResult"]["page"]["totalElements"]

    rows = []
    for obj in objects:
        item = obj["_embedded"]["indexableObject"]
        md = item.get("metadata", {})
        title = item.get("name") or ""
        author = first(md, "dc.contributor.author")
        uuid = item["uuid"]

        bitstreams = []
        try:
            bundles = get(f"{API}/core/items/{uuid}/bundles")
            for bundle in bundles["_embedded"]["bundles"]:
                if bundle["name"] != "ORIGINAL":
                    continue
                streams = get(f"{API}/core/bundles/{bundle['uuid']}/bitstreams?size=200")
                for bitstream in streams["_embedded"]["bitstreams"]:
                    bitstreams.append(
                        {
                            "name": bitstream.get("name"),
                            "size_bytes": bitstream.get("sizeBytes"),
                            "checksum": (bitstream.get("checkSum") or {}).get("value"),
                            "checksum_algorithm": (bitstream.get("checkSum") or {}).get(
                                "checkSumAlgorithm"
                            ),
                            "download_url": f"{API}/core/bitstreams/{bitstream['uuid']}/content",
                        }
                    )
        except Exception as error:
            bitstreams = [{"error": f"bitstream enumeration failed: {error}"}]

        veda, recension, genre, evidence = classify(title, author)

        rows.append(
            {
                "loar_item_id": uuid,
                "loar_handle": item.get("handle"),
                "item_url": f"https://loar.kb.dk/items/{uuid}",
                "cassette_identifier": first(md, "dc.identifier.other") or item.get("handle"),
                "title": title,
                "reciter": author,
                "all_contributors": [
                    e.get("value") for e in (md.get("dc.contributor.author") or [])
                ],
                "stated_veda": veda,
                "stated_sakha_or_recension": recension,
                "stated_genre": genre,
                "date_issued": first(md, "dc.date.issued"),
                "description": first(md, "dc.description"),
                "rights": first(md, "dc.rights"),
                "rights_uri": first(md, "dc.rights.uri"),
                "language": first(md, "dc.language.iso"),
                "file_count": len(bitstreams),
                "total_bytes": sum(b.get("size_bytes") or 0 for b in bitstreams),
                "files": bitstreams[:60],
                "duration": None,
                "duration_note": (
                    "Not stated in item metadata and not measured: no byte was fetched. "
                    "Duration requires downloading or range-reading each file."
                ),
                "audible_opening": None,
                "audible_opening_note": "NOT HEARD. This environment cannot audition audio.",
                "matched_sanskrit": None,
                "candidate_canonical_work": (
                    "VG:WORK:SV:KAU:GANA (candidate only, NOT a mapping)"
                    if veda == "SV" and genre not in ("UNKNOWN", "NOT_SAMAVEDIC")
                    else None
                ),
                "classification": genre,
                "confidence": (
                    "STATED_BY_SOURCE_TITLE"
                    if genre not in ("UNKNOWN", "NOT_SAMAVEDIC")
                    else "INSUFFICIENT"
                ),
                "evidence": evidence,
                "review_status": "NEEDS_AUDIBLE_REVIEW",
                "coverage_claimed": False,
                "coverage_claim_note": (
                    "No coverage is claimed from this item. Owner decision D forbids it "
                    "until classification is complete."
                ),
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "inventory.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
        newline="\n",
    )

    import collections

    print(f"collection totalElements: {total}; enumerated: {len(rows)}")
    print("\nby stated_veda / genre:")
    for (veda, genre), count in sorted(
        collections.Counter((r["stated_veda"], r["stated_genre"]) for r in rows).items()
    ):
        print(f"  {veda:8} {genre:28} {count:>3}")
    print("\nSamavedic items:")
    for r in rows:
        if r["stated_veda"] == "SV":
            print(
                f"  {r['title'][:44]:46} | {r['stated_sakha_or_recension']:22} "
                f"| {r['stated_genre']:18} | {r['file_count']:>3} file(s)"
            )
    arcika = [r for r in rows if r["stated_genre"] == "ARCIKA_RECITATION"]
    print(f"\nitems classified ARCIKA_RECITATION: {len(arcika)}")
    print("\nnon-Samavedic items relevant to other gaps:")
    for r in rows:
        if r["stated_veda"] in ("AV", "YV") or "catalogue" in r["title"].lower():
            print(
                f"  {r['title'][:44]:46} | {r['stated_veda']:4} "
                f"| {r['stated_sakha_or_recension']:20} | {r['file_count']:>3} file(s)"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
