"""GAP-ENTITY_COVERAGE-007 clause 1, second pass: the attested INFLECTED phrases.

The first probe folded the registry's lemma-form labels (``tṛtīya savana``) and measured
zero. That zero was an artefact of my own query, not of the corpus: the registry registers
inflections for the token path and the corpus writes the phrase inflected. The registry
entry for ``VG:CONCEPT:TRTIYA-SAVANA-THIRD-PRESSING`` names the loci itself --

    "tṛtīye savane" at RV 3.28.5, "idaṃ tṛtīyaṃ savanaṃ kavīnām" at AVS 6.47.3,
    "tṛtīye savana ṛbhūṇām" at AVS 9.1.13, and the Rbhus' third libation at RV 4.34.4,
    RV 4.35.9 and RV 8.57.1 ... All six were read and all six are this act -- and none of
    them is reachable, because the third pressing is the only one of the three the corpus
    never writes as one word.

-- so the evidence was read and recorded by a previous pass and only the matcher is missing.

This probe does two things and writes nothing:

1.  For each candidate multi-word phrase, find every mantra where it occurs as a run of
    CONSECUTIVE folded tokens, and report the mantra key and the quote.
2.  Audit each phrase PER ALIAS rather than per row: print every distinct host run the
    phrase reaches, so a phrase that also lands inside a different expression is visible
    before anything is registered. This project has recorded twice that two random samples
    can read 97% while one alias is 82.9% wrong.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))

from vedagraph.enrich.concepts import fold_alias  # noqa: E402
from vedagraph.enrich.surfaces import render_for_display  # noqa: E402

import _q  # noqa: E402

#: Candidate phrase aliases, taken from the registry entries' own read evidence. Lemma
#: forms are included so the measurement shows which surface actually occurs.
CANDIDATES: dict[str, list[str]] = {
    "VG:CONCEPT:TRTIYA-SAVANA-THIRD-PRESSING": [
        "tṛtīya savana",
        "tṛtīye savane",
        "tṛtīye savana",
        "tṛtīyaṃ savanaṃ",
        "tṛtīyaṃ savanam",
        "tṛtīyam savanam",
    ],
    "VG:CONCEPT:MADHYANDINA-SAVANA-MIDDAY-PRESSING": [
        "mādhyandina savana",
        "mādhyandine savane",
        "mādhyaṃdine savane",
    ],
    # POSITIVE CONTROL. Not to be registered. A two-token run this corpus certainly
    # contains, so a zero on the real candidates can be told from a broken phrase pass.
    "__POSITIVE_CONTROL__": ["agnim īḷe", "indra soma"],
}


def go(session):
    out: dict[str, object] = {}
    rows = _q.rows(
        session,
        """
        MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(t:TextVersion)
        WHERE t.text_role = 'SEARCH_DERIVATIVE'
        RETURN m.canonical_key AS key, m.veda AS veda, t.text_nfc AS text
        """,
    )
    out["mantras_searched"] = len(rows)

    folded: dict[str, dict[str, str]] = {}
    for entity, phrases in CANDIDATES.items():
        folded[entity] = {}
        for phrase in phrases:
            parts = [fold_alias(p) for p in phrase.split()]
            if all(parts) and len(parts) > 1:
                folded[entity][phrase] = " ".join(parts)

    hits: dict[str, dict[str, list[dict[str, str]]]] = {
        e: {p: [] for p in folded[e]} for e in folded
    }
    host_runs: dict[str, collections.Counter] = {
        f"{e}|{p}": collections.Counter() for e in folded for p in folded[e]
    }

    for r in rows:
        tokens = (r["text"] or "").split()
        joined = " ".join(tokens)
        for entity, phrases in folded.items():
            for phrase, target in phrases.items():
                start = 0
                while True:
                    pos = joined.find(target, start)
                    if pos < 0:
                        break
                    # require the match to begin and end on a token boundary, so a phrase
                    # can never fire inside a longer word the way a substring pass would
                    before_ok = pos == 0 or joined[pos - 1] == " "
                    end = pos + len(target)
                    after_ok = end == len(joined) or joined[end] == " "
                    if before_ok and after_ok:
                        hits[entity][phrase].append(
                            {
                                "canonical_key": r["key"],
                                "veda": r["veda"],
                                "quote": render_for_display(
                                    joined[max(0, pos - 45) : end + 45]
                                ),
                            }
                        )
                        host_runs[f"{entity}|{phrase}"][
                            render_for_display(joined[pos:end])
                        ] += 1
                    start = pos + 1

    out["folded_phrases"] = {
        e: {p: render_for_display(t) for p, t in ps.items()} for e, ps in folded.items()
    }
    out["hits"] = {
        e: {p: {"count": len(v), "rows": v} for p, v in ps.items() if v} for e, ps in hits.items()
    }
    out["hit_counts"] = {
        e: {p: len(v) for p, v in ps.items()} for e, ps in hits.items()
    }
    out["host_run_audit_per_alias"] = {
        k: dict(v) for k, v in host_runs.items() if v
    }
    control = out["hit_counts"].get("__POSITIVE_CONTROL__", {})
    out["positive_control_fires"] = any(control.values())
    out["verdict"] = (
        "PHRASE_PASS_IS_SOUND_AND_THE_CANDIDATES_OCCUR"
        if out["positive_control_fires"]
        and any(
            n for e, ps in out["hit_counts"].items() if e != "__POSITIVE_CONTROL__" for n in ps.values()
        )
        else "SEE_CONTROL"
    )
    return out


if __name__ == "__main__":
    result = _q.run(go)
    pathlib.Path(__file__).with_name("probe_phrase_match2.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
