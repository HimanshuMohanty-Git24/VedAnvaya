"""Stage 6: the Private Use Area scan, and metre scored against its own median.

Two corrections to earlier passes in this agent's own work, both worth keeping visible.

The vowelless roots are not stripped letters
--------------------------------------------
A first reading of ``SemanticAssertion.root`` saw *karisyasi* with root ``k`` and took it
for the below-mark stripping defect Agent 2 found in the Atharvavedic SEARCH_DERIVATIVE
layer. It is not. The stored value is ``k`` followed by U+E000, a Private Use Area
codepoint standing in for vocalic *r*. That is the same class as the ``Samved.xlsx`` trap
Wave 0 recorded -- a font hack where a Unicode letter belongs -- and it is a different
defect with a different fix. So the whole graph is scanned for it rather than one field.

Metre is scored against its own median, not its nominal count
-------------------------------------------------------------
Counting syllables in the transmitted samhita spelling under-counts systematically,
because Vedic metre is counted on the restored text where hiatus and disyllabic readings
recover syllables that sandhi has contracted away. A fixed nominal target therefore
reports a whole metre as divergent when the bias is in the counter. Each metre is scored
against the median count of the verses that carry it: that cancels the counter's bias and
leaves only verses that diverge from their own metre-mates.
"""

from __future__ import annotations

import collections
import json
import os
import pathlib
import re
import statistics
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib_align import deaccent, to_iast  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv("D:/VedaGraph/.env")
from neo4j import GraphDatabase  # noqa: E402

SCRATCH = pathlib.Path(sys.argv[1])
PUA = re.compile(r"[\ue000-\uf8ff\U000f0000-\U000ffffd\U00100000-\U0010fffd]")
_VOWELS = re.compile(r"ai|au|[a\u0101i\u012bu\u016b\u1e5b\u1e5d\u1e37\u1e39eo]")

#: A metre must be carried by at least this many verses before a median is trustworthy.
MEDIAN_FLOOR = 12
#: Divergence from a metre's own median beyond this is called a defect.
DIVERGENCE_BAND = 4


def syllables(text: str) -> int:
    folded = deaccent(to_iast(text or "")).lower()
    return len(_VOWELS.findall(re.sub(r"[|\u0964\u0965\d]", " ", folded)))


def main() -> None:
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    out: dict[str, object] = {}
    with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as session:

        # ------------------------------------------------------------ the PUA scan
        hits: dict[str, dict] = {}
        codepoints: collections.Counter = collections.Counter()

        def scan(label: str, query: str) -> None:
            found = 0
            examples = []
            for record in session.run(query):
                blob = json.dumps(dict(record), ensure_ascii=False, default=str)
                marks = PUA.findall(blob)
                if not marks:
                    continue
                found += 1
                codepoints.update(f"U+{ord(ch):04X}" for ch in marks)
                if len(examples) < 4:
                    examples.append(
                        {
                            key: (ascii(value) if isinstance(value, str) else value)
                            for key, value in dict(record).items()
                        }
                    )
            hits[label] = {"records_with_pua": found, "examples": examples}

        scan(
            "SemanticAssertion.root",
            "MATCH (a:SemanticAssertion) WHERE a.root IS NOT NULL "
            "RETURN a.root AS root, count(*) AS n",
        )
        scan(
            "SemanticAssertion.all_string_properties",
            "MATCH (a:SemanticAssertion) RETURN a.assertion_id AS id, a.root AS root, "
            "a.root_label AS root_label, a.verb_surface AS verb_surface, "
            "a.agent_surface AS agent_surface, a.patient AS patient, "
            "a.instrument AS instrument, a.beneficiary AS beneficiary, "
            "a.roles_json AS roles_json, a.display_label AS display_label, "
            "a.preverbs AS preverbs, a.pada AS pada",
        )
        scan(
            "TextVersion.text_nfc",
            "MATCH (t:TextVersion) RETURN t.text_nfc AS text LIMIT 50000",
        )
        scan(
            "Translation.text",
            "MATCH (t:Translation) RETURN t.text AS text LIMIT 50000",
        )
        scan(
            "Devata.aliases_iast",
            "MATCH (d:Devata) RETURN d.entity_key AS key, d.label_iast AS label, "
            "d.aliases_iast AS aliases",
        )
        scan(
            "Concept.aliases_sa",
            "MATCH (c:Concept) RETURN c.entity_key AS key, c.preferred_label_sa AS label, "
            "c.aliases_sa AS aliases",
        )
        scan(
            "Lemma.lemma",
            "MATCH (l:Lemma) RETURN l.lemma AS lemma, l.normalized_lemma AS normalized",
        )
        scan(
            "Formula.surface",
            "MATCH (f:Formula) RETURN f.entity_key AS key, properties(f) AS props",
        )
        scan(
            "MENTIONS_DEVATA.matched_forms",
            "MATCH ()-[r:MENTIONS_DEVATA]->() RETURN r.matched_forms AS forms, "
            "r.evidence AS evidence LIMIT 30000",
        )
        scan(
            "ABOUT_CONCEPT.evidence",
            "MATCH ()-[r:ABOUT_CONCEPT]->() RETURN r.evidence AS evidence LIMIT 30000",
        )
        out["pua_scan"] = {
            "surfaces": hits,
            "codepoints_seen": dict(codepoints),
            "note": (
                "A Private Use Area codepoint has no meaning outside the font that "
                "defined it. A value carrying one cannot be searched, sorted, joined to a "
                "lexicon or rendered by any consumer that does not ship that font."
            ),
        }
        # exactly which roots, and the verb they were derived from, so the mapping is
        # recoverable rather than guessed
        out["pua_root_inventory"] = [
            {
                "root_repr": ascii(record["root"]),
                "codepoints": [f"U+{ord(ch):04X}" for ch in record["root"]],
                "assertions": record["n"],
                "verb_examples": record["verbs"][:3],
            }
            for record in (
                dict(r)
                for r in session.run(
                    "MATCH (a:SemanticAssertion) WHERE a.root IS NOT NULL "
                    "RETURN a.root AS root, count(*) AS n, "
                    "collect(a.verb_surface)[0..3] AS verbs ORDER BY n DESC"
                )
            )
            if PUA.search(record["root"] or "")
        ]
        out["pua_root_totals"] = {
            "distinct_roots_with_pua": len(out["pua_root_inventory"]),
            "assertions_affected": sum(
                row["assertions"] for row in out["pua_root_inventory"]
            ),
            "assertions_with_a_root": dict(
                session.run(
                    "MATCH (a:SemanticAssertion) WHERE a.root IS NOT NULL "
                    "RETURN count(*) AS n"
                ).single()
            )["n"],
        }

        # ------------------------------------------------------------ metre, self-relative
        metre = [
            dict(record)
            for record in session.run(
                "MATCH (m:Mantra)-[r:HAS_CHANDAS]->(c:Chandas) "
                "MATCH (m)-[:HAS_TEXT_VERSION]->(t:TextVersion) "
                "RETURN m.canonical_key AS key, m.veda AS veda, "
                "c.display_label AS label, r.quality_tier AS tier, "
                "r.attribution_precision AS precision, r.confidence AS confidence, "
                "collect(t.text_nfc) AS texts"
            )
        ]
        for row in metre:
            row["counted"] = max(syllables(text) for text in row["texts"]) if row["texts"] else 0
            del row["texts"]
        by_metre: dict[str, list[int]] = collections.defaultdict(list)
        for row in metre:
            by_metre[row["label"]].append(row["counted"])
        medians = {
            label: statistics.median(counts)
            for label, counts in by_metre.items()
            if len(counts) >= MEDIAN_FLOOR
        }
        for row in metre:
            median = medians.get(row["label"])
            if median is None:
                row["verdict"] = "TOO_FEW_VERSES_FOR_A_MEDIAN"
                row["deviation"] = None
            else:
                row["deviation"] = row["counted"] - median
                row["verdict"] = (
                    "CONSISTENT_WITH_ITS_METRE"
                    if abs(row["deviation"]) <= DIVERGENCE_BAND
                    else "DIVERGES_FROM_ITS_OWN_METRE"
                )
        out["metre_medians"] = {
            label: {"median_syllables": median, "verses": len(by_metre[label])}
            for label, median in sorted(medians.items())
        }
        summary: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter
        )
        for row in metre:
            summary[f"{row['veda']}|{row['tier']}|{row['precision']}"][row["verdict"]] += 1
        out["metre_by_tier"] = {}
        for key, counter in sorted(summary.items()):
            decided = (
                counter["CONSISTENT_WITH_ITS_METRE"]
                + counter["DIVERGES_FROM_ITS_OWN_METRE"]
            )
            out["metre_by_tier"][key] = {
                **dict(counter),
                "decided": decided,
                "observed_accuracy": (
                    round(counter["CONSISTENT_WITH_ITS_METRE"] / decided, 4)
                    if decided
                    else None
                ),
            }
        out["metre_rows"] = [
            row for row in metre if row["verdict"] == "DIVERGES_FROM_ITS_OWN_METRE"
        ]

    driver.close()
    (SCRATCH / "stage6_pua_metre.json").write_text(
        json.dumps(out, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print("== PUA codepoints seen:", out["pua_scan"]["codepoints_seen"])
    for label, value in out["pua_scan"]["surfaces"].items():
        print("  {:42s} records_with_pua={}".format(label, value["records_with_pua"]))
    print("== PUA root totals:", out["pua_root_totals"])
    for row in out["pua_root_inventory"][:10]:
        print("   ", row["root_repr"], row["codepoints"], row["assertions"],
              [ascii(v) for v in row["verb_examples"]])
    print("== metre by tier")
    for key, value in out["metre_by_tier"].items():
        print("  {:36s} {}".format(key, value))


if __name__ == "__main__":
    main()
