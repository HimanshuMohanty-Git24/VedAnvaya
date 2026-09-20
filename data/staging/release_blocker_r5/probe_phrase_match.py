"""GAP-ENTITY_COVERAGE-007 clause 1: can a phrase pass reach the multi-word entities?

The mention layer's token pass is ``index.token.get(token)`` over one folded token at a
time, so a registered label containing a space can never equal a key and the phrase never
fires. Two `:DomainEntity` rows carry a multi-word Sanskrit label.

FALSIFIER STATED BEFORE THE TEST: if neither multi-word label occurs as a run of
consecutive folded tokens anywhere in the four Samhitas, then phrase matching is
implementable but has nothing to match, and clause 1 must close on a measured zero with the
phrase pass built and tested rather than on an edge.

This probe reads the live store only. It writes nothing.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "src"))

from vedagraph.enrich.concepts import fold_alias  # noqa: E402

import _q  # noqa: E402

MULTIWORD = {
    "VG:CONCEPT:MADHYANDINA-SAVANA-MIDDAY-PRESSING": "mādhyandina savana",
    "VG:CONCEPT:TRTIYA-SAVANA-THIRD-PRESSING": "tṛtīya savana",
}


def go(session):
    out: dict[str, object] = {}
    folded = {k: fold_alias(v) for k, v in MULTIWORD.items()}
    out["folded_labels"] = {k: {"raw": MULTIWORD[k], "folded": v, "has_space": " " in v} for k, v in folded.items()}

    # Pull every mantra's searchable text once. SEARCH_NORMALIZED TextVersions carry the
    # folded surface the mention layer actually searches.
    rows = _q.rows(
        session,
        """
        MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(t:TextVersion)
        WHERE t.text_role = 'SEARCH_DERIVATIVE'
        RETURN m.canonical_key AS key, m.veda AS veda, t.text_nfc AS text
        """,
    )
    out["search_normalized_text_versions"] = len(rows)
    if not rows:
        forms = _q.rows(
            session,
            "MATCH (t:TextVersion) RETURN t.text_form AS form, t.text_role AS role, count(*) AS c ORDER BY c DESC",
        )
        out["text_form_distribution"] = forms
        return out

    hits: dict[str, list[dict[str, str]]] = {k: [] for k in MULTIWORD}
    # unigram frequency of each phrase's parts, so a zero can be told from a fold defect
    part_counts: dict[str, int] = collections.Counter()
    parts = {p for f in folded.values() for p in f.split()}

    for r in rows:
        text = r["text"] or ""
        tokens = text.split()
        joined = " ".join(tokens)
        for part in parts:
            part_counts[part] += tokens.count(part)
        for key, phrase in folded.items():
            if phrase and phrase in joined:
                position = joined.find(phrase)
                hits[key].append(
                    {
                        "canonical_key": r["key"],
                        "veda": r["veda"],
                        "quote": joined[max(0, position - 60) : position + len(phrase) + 60],
                    }
                )

    out["phrase_hits"] = {k: {"count": len(v), "rows": v[:10]} for k, v in hits.items()}
    out["component_token_frequency"] = dict(part_counts)
    out["falsifier_result"] = (
        "PHRASE_OCCURS" if any(hits.values()) else "NO_PHRASE_OCCURS_IN_ANY_SAMHITA"
    )
    return out


if __name__ == "__main__":
    result = _q.run(go)
    pathlib.Path(__file__).with_name("probe_phrase_match.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
