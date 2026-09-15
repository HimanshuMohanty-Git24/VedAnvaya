"""Stage 10: the morphological_roles vocabulary, and what it costs.

The mention layer writes a case onto every edge in ``morphological_roles``. Compared with
the treebank's hand-annotated ``Case`` feature, agreement looked like 89.1% -- until the
mismatches were read. They are not wrong cases. They are the *same* case under two
spellings: the Rigvedic branch writes ``NOM`` and the Atharvavedic and Yajurvedic branch
writes ``NOMINATIVE``, and an earlier pass of this agent nearly reported that as an
accuracy defect.

That is a real defect of a different kind, and it is the one this project has paid for
twice: a closed vocabulary that is not closed, and a value space nobody enumerated. A
consumer filtering ``morphological_roles CONTAINS 'NOM'`` gets the Rigveda and reads an
Atharvavedic zero, exactly as the AV deity caveat once read one.

So this stage reports both numbers: agreement as the strings stand, and agreement after
folding the two vocabularies together. The gap between them is the size of the vocabulary
problem, and what is left over after folding is the real accuracy.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib_align import deaccent  # noqa: E402

SCRATCH = pathlib.Path(sys.argv[1])
OUT = pathlib.Path("D:/VedaGraph/data/staging/quality/proofs")

#: The treebank's Case values, in this project's short form.
HUMAN_CASE = {
    "Nom": "NOM", "Acc": "ACC", "Ins": "INS", "Dat": "DAT",
    "Abl": "ABL", "Gen": "GEN", "Loc": "LOC", "Voc": "VOC",
}

#: The two spellings the graph actually uses, folded. Enumerated from the data rather
#: than assumed, which is the whole point.
GRAPH_CASE = {
    "NOM": "NOM", "NOMINATIVE": "NOM",
    "ACC": "ACC", "ACCUSATIVE": "ACC",
    "INS": "INS", "INSTRUMENTAL": "INS",
    "DAT": "DAT", "DATIVE": "DAT",
    "ABL": "ABL", "ABLATIVE": "ABL",
    "GEN": "GEN", "GENITIVE": "GEN",
    "LOC": "LOC", "LOCATIVE": "LOC",
    "VOC": "VOC", "VOCATIVE": "VOC",
}


def main() -> None:
    scores = json.loads((SCRATCH / "stage3_scores.json").read_text(encoding="utf-8"))
    graph = json.loads((SCRATCH / "stage2_graph.json").read_text(encoding="utf-8"))
    per_mantra = scores["per_mantra"]

    raw = collections.Counter()
    folded = collections.Counter()
    non_case_values = collections.Counter()
    vocabulary_by_veda: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    residual: list[dict] = []

    for row in graph["mentions_devata"]:
        for value in row["roles"] or []:
            vocabulary_by_veda[row["veda"]][value] += 1
        bucket = per_mantra.get(row["key"])
        if bucket is None:
            continue
        forms = {deaccent(form or "").lower() for form in (row["forms"] or [])}
        claimed_values = set(row["roles"] or [])
        if not forms or not claimed_values:
            continue
        tokens = [t for t in bucket["tokens"] if t["form"] in forms]
        if len(tokens) != 1:
            continue
        feats = dict(
            part.split("=", 1)
            for part in (tokens[0]["feats"] or "").split("|")
            if "=" in part
        )
        human = HUMAN_CASE.get(feats.get("Case", ""))
        if human is None:
            continue
        for claimed in claimed_values:
            raw[claimed == human] += 1
            mapped = GRAPH_CASE.get(claimed)
            if mapped is None:
                non_case_values[claimed] += 1
                folded["NOT_A_CASE_VALUE"] += 1
                continue
            folded[mapped == human] += 1
            if mapped != human:
                residual.append(
                    {
                        "canonical_key": row["key"],
                        "veda": row["veda"],
                        "devata": row["devata"],
                        "claimed": claimed,
                        "human_case": human,
                        "human_feats": tokens[0]["feats"],
                        "form": tokens[0]["form"],
                    }
                )

    raw_total = raw[True] + raw[False]
    fold_total = folded[True] + folded[False]
    report = {
        "finding": (
            "morphological_roles carries two disjoint spellings of the same case values, "
            "split by which branch wrote the edge."
        ),
        "the_two_vocabularies": {
            veda: dict(counter.most_common())
            for veda, counter in sorted(vocabulary_by_veda.items())
        },
        "agreement_against_human_case": {
            "as_the_strings_stand": {
                "pairs": raw_total,
                "agree": raw[True],
                "agreement": round(raw[True] / raw_total, 4) if raw_total else None,
            },
            "after_folding_the_two_vocabularies": {
                "pairs": fold_total,
                "agree": folded[True],
                "agreement": round(folded[True] / fold_total, 4) if fold_total else None,
            },
            "the_gap_is_the_vocabulary_problem": (
                "Everything between those two numbers is one case under two names. None "
                "of it is a wrong case, and all of it breaks a value filter."
            ),
        },
        "values_that_are_not_a_case_at_all": dict(non_case_values),
        "residual_real_disagreement": {
            "count": len(residual),
            "classes": dict(
                collections.Counter(
                    f"{row['claimed']} claimed, human says {row['human_case']}"
                    for row in residual
                )
            ),
            "examples": residual[:20],
        },
        "why_this_matters_beyond_tidiness": (
            "This is the third time in this project's recorded history that a value "
            "space nobody enumerated produced a false reading: the attribution axis "
            "written by three disagreeing mechanisms, the stale-claim audit that grepped "
            "for the value it expected, and now this. A query filtering on 'NOM' returns "
            "the Rigveda and reports an Atharvavedic zero."
        ),
        "measurement_limit": (
            "Only edges whose claimed surface form matches exactly one human-annotated "
            "token of that verse are counted, so no edge gets the benefit of the doubt "
            "from an ambiguous match. That is why the pair count is well below the edge "
            "count."
        ),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "morphological_role_vocabulary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(
        {
            k: v for k, v in report.items()
            if k in ("agreement_against_human_case", "values_that_are_not_a_case_at_all")
        },
        ensure_ascii=False, indent=1,
    ))
    print("residual classes:", report["residual_real_disagreement"]["classes"])
    for veda, counter in sorted(vocabulary_by_veda.items()):
        print(veda, dict(counter.most_common(6)))


if __name__ == "__main__":
    main()
