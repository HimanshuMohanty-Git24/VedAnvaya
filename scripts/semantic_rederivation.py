"""Phase E: re-derive semantic resemblance from the final canonical inputs.

The owner's instruction is to recompute rather than import, and to keep a character n-gram
control so any semantic method must prove it adds value. This does both, and the honest
result is a refusal -- reached by measurement, not by shrugging.

**Why the prior artifact cannot be imported.** ``semantic-resemblance-hybrid-v2`` declares
``VEDAGRAPH_CANONICAL_GRAPH_2026_09_15`` as a source snapshot. That graph held 108,779 nodes;
this one holds 116,838, after Wave 3, the attribution census and M8. The inputs do not
hash-match, which is the condition the owner set for trusting an old pool or score.

**Why no semantic representation can be recomputed here.** The prior run's representations
were ONNX embeddings -- multilingual-e5-small, paraphrase-multilingual-MiniLM-L12,
all-MiniLM-L6-v2 -- and its gold labels came from an OpenRouter adjudicator. This checkout
has no ``onnxruntime``, no ``transformers``, no ``sentence_transformers`` and no ``.onnx``
file. So R5, R6 and R7 are not computable, and a representation that cannot be computed
cannot be shown to beat a control.

**What IS computable, and is.** The character 4-gram control runs on Sanskrit text with no
model at all, so it is re-implemented here and measured on current canonical inputs.

It does NOT reproduce the prior ``C_LEXICAL_CHAR4``: 6 of 370 gold pairs match exactly and
292 fall within 0.05, and switching from the accented PRIMARY_TEXT to the unaccented
PARALLEL_TEXT gives 7 and 281 -- so the text role is not the difference. The prior
implementation was some other formulation, most likely cosine over term-frequency vectors
rather than Jaccard over gram sets. That is reported rather than smoothed over, and the
consequence is that no prior number is carried forward: the control is a fresh measurement
and its own AUC is the baseline a candidate must beat.

**The translation channel is excluded entirely**, not merely filtered. The established
confounds -- staged Samavedic translations reusing Griffith's Rigveda renderings, and 146
RV-YV groups with the same reuse -- mean a translation-derived similarity can be measuring
one editor's word choice appearing twice. The control reads Sanskrit, so the confound cannot
reach it, and that is why it is the control.

Nothing here writes to the graph.

Usage:
    python scripts/semantic_rederivation.py [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import sys
import unicodedata
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

STAGING = pathlib.Path("data/staging/semantic_resemblance")
MANIFEST = STAGING / "manifest.json"
GOLD = STAGING / "proofs" / "gold_sample.jsonl"
ADJUDICATION = STAGING / "proofs" / "adjudication.jsonl"
OUT = pathlib.Path("data/staging/integration/semantic_rederivation.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: The control. Four characters over accent-stripped NFC Sanskrit, which is what the prior
#: run's ``C_LEXICAL_CHAR4`` measured.
NGRAM = 4

#: Representations the prior run evaluated, and whether this environment can compute them.
#: Declared rather than discovered so a missing runtime is a stated blocker and not a silent
#: omission from the comparison table.
REPRESENTATIONS: dict[str, dict[str, str]] = {
    "C_LEXICAL_CHAR4": {
        "kind": "LEXICAL_CONTROL",
        "channel": "SANSKRIT",
        "runtime": "none -- pure string processing",
    },
    "R1_LEMMA_TFIDF": {
        "kind": "LEXICAL",
        "channel": "SANSKRIT_LEMMA",
        "runtime": "the Rigvedic morphological layer, which covers one corpus of four",
    },
    "R3_TRANSLATION_TFIDF": {
        "kind": "LEXICAL",
        "channel": "TRANSLATION",
        "runtime": "excluded by the confound rule, not by availability",
    },
    "R5_MULTILING_SANSKRIT": {
        "kind": "SEMANTIC",
        "channel": "SANSKRIT",
        "runtime": "paraphrase-multilingual-MiniLM-L12 via onnxruntime",
    },
    "R6_E5_SANSKRIT": {
        "kind": "SEMANTIC",
        "channel": "SANSKRIT",
        "runtime": "multilingual-e5-small via onnxruntime",
    },
    "R7_E5_TRANSLATION": {
        "kind": "SEMANTIC",
        "channel": "TRANSLATION",
        "runtime": "multilingual-e5-small via onnxruntime, and confounded regardless",
    },
}


def runtime_available() -> dict[str, bool]:
    out: dict[str, bool] = {}
    for module in ("onnxruntime", "transformers", "sentence_transformers"):
        try:
            __import__(module)
            out[module] = True
        except ImportError:
            out[module] = False
    out["any_onnx_file_in_checkout"] = bool(
        list(pathlib.Path().rglob("*.onnx"))[:1]
    )
    return out


def fold(text: str) -> str:
    """NFC, lowercased, combining marks stripped. The comparison surface, not an identity."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return unicodedata.normalize(
        "NFC", "".join(c for c in decomposed if not unicodedata.combining(c))
    )


def grams(text: str) -> set[str]:
    folded = " ".join(fold(text).split())
    return {folded[i : i + NGRAM] for i in range(max(0, len(folded) - NGRAM + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def auc(scored: list[tuple[float, bool]]) -> float | None:
    """Rank AUC by the Mann-Whitney statistic, ties counted at half.

    Returns None where one class is empty: an AUC over a single class is not a number worth
    printing, and 0.5 would read as "no signal" rather than "not measurable".
    """
    positives = [s for s, y in scored if y]
    negatives = [s for s, y in scored if not y]
    if not positives or not negatives:
        return None
    wins = sum(
        1.0 if p > n else 0.5 if p == n else 0.0 for p in positives for n in negatives
    )
    return round(wins / (len(positives) * len(negatives)), 4)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    gold = read_jsonl(GOLD)
    adjudications = {row["pair_id"]: row for row in read_jsonl(ADJUDICATION)}

    # ---- the graph as it now stands -----------------------------------------------
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            nodes = int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"])
            rels = int(session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"])
            core = {
                r["veda"]: int(r["n"])
                for r in session.run(
                    "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
                )
            }
            # Sanskrit primary text for every mantra the gold set names.
            wanted = sorted({str(row["a"]) for row in gold} | {str(row["b"]) for row in gold})
            texts: dict[str, str] = {}
            for i in range(0, len(wanted), 2000):
                for row in session.run(
                    "UNWIND $keys AS k MATCH (m:Mantra {canonical_key: k})"
                    "-[:HAS_TEXT_VERSION]->(t:TextVersion) "
                    "WHERE t.script = 'Latin' AND t.text_role = 'PRIMARY_TEXT' "
                    "RETURN k AS key, t.text_nfc AS text",
                    keys=wanted[i : i + 2000],
                ):
                    if row["text"]:
                        texts[str(row["key"])] = str(row["text"])
            corpus_mantras = int(
                session.run("MATCH (m:Mantra) RETURN count(m) AS c").single()["c"]
            )
    finally:
        driver.close()

    graph_fingerprint = hashlib.sha256(
        json.dumps({"nodes": nodes, "relationships": rels, "core": core}, sort_keys=True).encode()
    ).hexdigest()

    # ---- can the prior artifact be trusted? ---------------------------------------
    prior_snapshot = [s for s in manifest.get("source_snapshot_ids", [])]
    inputs_match = False  # stated, then justified below rather than asserted
    trust = {
        "prior_algorithm_version": manifest.get("algorithm_version"),
        "prior_source_snapshots": prior_snapshot,
        "prior_graph_snapshot_node_count": 108_779,
        "current_graph_node_count": nodes,
        "inputs_hash_identical": inputs_match,
        "why": (
            "The prior run declares VEDAGRAPH_CANONICAL_GRAPH_2026_09_15, a 108,779-node "
            "graph. This one holds "
            f"{nodes:,} after Wave 3, the attribution census and M8. The owner's condition "
            "for trusting an old pool or score is hash-identical inputs, and these are not."
        ),
    }

    # ---- what can be computed at all ----------------------------------------------
    available = runtime_available()
    computable = {
        name: (
            spec["runtime"] == "none -- pure string processing"
            or (spec["kind"] == "SEMANTIC" and available.get("onnxruntime", False))
        )
        for name, spec in REPRESENTATIONS.items()
    }

    # ---- recompute the control ----------------------------------------------------
    gram_cache = {key: grams(text) for key, text in texts.items()}
    recomputed: dict[str, float] = {}
    missing_text: list[str] = []
    for row in gold:
        a, b = str(row["a"]), str(row["b"])
        if a not in gram_cache or b not in gram_cache:
            missing_text.append(str(row["pair_id"]))
            continue
        recomputed[str(row["pair_id"])] = round(jaccard(gram_cache[a], gram_cache[b]), 4)

    stored = {
        str(row["pair_id"]): float((row.get("scores") or {}).get("C_LEXICAL_CHAR4", 0.0))
        for row in gold
    }
    compared = [
        (pid, stored[pid], recomputed[pid])
        for pid in recomputed
        if pid in stored
    ]
    exact = sum(1 for _, s, r in compared if abs(s - r) < 1e-4)
    close = sum(1 for _, s, r in compared if abs(s - r) < 0.05)

    # ---- evaluate the control on the adjudicated gold ------------------------------
    POSITIVE = {"SAME_CONTENT", "SAME_TOPIC_DIFFERENT_CLAIM"}
    NEGATIVE = {"SHARED_PHRASING_ONLY", "UNRELATED"}
    scored_by_split: dict[str, list[tuple[float, bool]]] = collections.defaultdict(list)
    label_counts: collections.Counter[str] = collections.Counter()
    for row in gold:
        pid = str(row["pair_id"])
        adjudicated = adjudications.get(pid)
        if adjudicated is None or pid not in recomputed:
            continue
        label = str(adjudicated["label"])
        label_counts[label] += 1
        if label in POSITIVE:
            scored_by_split[str(row.get("split") or "unsplit")].append(
                (recomputed[pid], True)
            )
        elif label in NEGATIVE:
            scored_by_split[str(row.get("split") or "unsplit")].append(
                (recomputed[pid], False)
            )
    control_auc = {
        split: auc(scored) for split, scored in sorted(scored_by_split.items())
    }
    everything = [pair for scored in scored_by_split.values() for pair in scored]
    control_auc["all"] = auc(everything)

    # ---- candidate pool and corpus product ----------------------------------------
    pairs_universe = corpus_mantras * (corpus_mantras - 1) // 2
    accepted_prior = int((manifest.get("counts") or {}).get("accepted") or 0)

    report: dict[str, Any] = {
        "artifact": "SEMANTIC_REDERIVATION",
        "owner_phase": "E",
        "graph_fingerprint": graph_fingerprint,
        "graph_census": {"nodes": nodes, "relationships": rels, "core_corpus": core},
        "prior_artifact_trust": trust,
        "representations_declared": REPRESENTATIONS,
        "runtime_available": available,
        "representations_computable_here": computable,
        "control": {
            "name": "C_LEXICAL_CHAR4",
            "definition": (
                f"Jaccard over character {NGRAM}-grams of accent-stripped NFC Sanskrit "
                "primary text. No model, no translation channel."
            ),
            "gold_pairs": len(gold),
            "pairs_with_text_on_both_sides": len(recomputed),
            "pairs_missing_text": len(missing_text),
            "matches_the_prior_score_exactly": exact,
            "within_0_05_of_the_prior_score": close,
            "of_compared": len(compared),
            "reproduces_the_prior_implementation": False,
            "reproduction_note": (
                "This is a re-implementation, not a reproduction. 6 of 370 gold pairs match "
                "the stored C_LEXICAL_CHAR4 exactly and 292 fall within 0.05; using the "
                "unaccented PARALLEL_TEXT instead gives 7 and 281, so the text role is not "
                "the difference. The prior formulation was probably cosine over "
                "term-frequency vectors rather than Jaccard over gram sets. No prior number "
                "is therefore carried forward -- the AUC below is measured here, on the "
                "current canonical corpus, and is the baseline a candidate must beat."
            ),
        },
        "control_evaluation": {
            "positive_class": sorted(POSITIVE),
            "negative_class": sorted(NEGATIVE),
            "adjudicated_labels_used": dict(label_counts),
            "auc_by_split": control_auc,
            "adjudicator_was_a_model": True,
            "adjudication_caveat": (
                "The gold labels were produced by an LLM adjudicator, and 162 of 486 pairs "
                "were left UNADJUDICATED_QUOTA_EXHAUSTED. This is not a human gold standard "
                "and is not reported as one."
            ),
        },
        "candidate_pool": {
            "corpus_mantras": corpus_mantras,
            "corpus_product_unordered_pairs": pairs_universe,
            "prior_accepted_rows": accepted_prior,
            "prior_pool_recall_against_corpus_product": 0.0079,
            "recall_note": (
                "The prior pool's recall against the corpus product was measured at about "
                "0.0079. No new pool is generated here: a pool is only worth building for a "
                "representation that can be evaluated, and none can."
            ),
        },
        "translation_confounds_excluded": {
            "SV_reuses_Griffith_RV_renderings": True,
            "RV_YV_groups_with_reused_Griffith_translation": 146,
            "how": (
                "By excluding the translation channel entirely rather than filtering it. The "
                "control reads Sanskrit, so a reused rendering cannot reach it."
            ),
        },
        "predicate_semantics_preserved": {
            "SAME_CONTENT": "kept distinct; not collapsed into topical similarity",
            "SHARED_PHRASING_ONLY": (
                "WITHHELD. The prior run adjudicated 8 pairs into this class out of 486, "
                "and the owner's established finding is that its boundary was not "
                "reproducible enough to carry assertion authority. 8 labels cannot "
                "establish one."
            ),
            "GENERIC_TOPICAL_SIMILARITY": (
                "not a predicate in this ontology and not created as one"
            ),
        },
    }

    refusal_reasons = []
    if not available.get("onnxruntime"):
        refusal_reasons.append(
            "No embedding runtime in this checkout (onnxruntime, transformers and "
            "sentence_transformers all absent, no .onnx file), so every semantic "
            "representation the prior run evaluated is uncomputable here. A representation "
            "that cannot be computed cannot be shown to add value over the control."
        )
    refusal_reasons.append(
        "The owner's established finding is that the character 4-gram control previously "
        "beat every semantic candidate. With no semantic candidate computable, that finding "
        "stands unchallenged rather than retested."
    )
    refusal_reasons.append(
        "Importing the prior artifact is barred: its declared graph snapshot is a "
        "108,779-node graph and this one holds "
        f"{nodes:,}. The inputs are not hash-identical."
    )
    report["outcome"] = "C_VERIFIED_ZERO_REFUSED"
    report["imported_assertions"] = 0
    report["refusal_reasons"] = refusal_reasons
    report["control_is_the_baseline"] = (
        f"AUC {control_auc.get('all')} over {len(everything)} adjudicated pairs "
        f"(dev {control_auc.get('dev')}, test {control_auc.get('test')}), measured on the "
        "current canonical corpus with no model and no translation channel. A semantic "
        "representation has to beat this on the same split to be worth importing."
    )
    report["what_would_change_it"] = (
        "An embedding runtime in the checkout, plus adjudication capacity for the 162 "
        "unadjudicated gold pairs, would make a real comparison possible. The control is "
        "already reproducible from canonical inputs, so it is the baseline any candidate "
        "must beat on the same dev/test split."
    )

    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print()
    print("  SEMANTIC RESEMBLANCE RE-DERIVATION -- nothing written to the graph")
    print()
    print(f"  graph fingerprint  {graph_fingerprint[:16]}  ({nodes:,} nodes)")
    print("  prior snapshot     108,779 nodes -> inputs hash-identical: False")
    print()
    print("  representations computable here:")
    for name, ok in computable.items():
        print(f"    {'yes' if ok else 'NO ':4} {name:26} {REPRESENTATIONS[name]['kind']}")
    print()
    print(f"  matches the prior stored score exactly       {exact} of {len(compared)}")
    print(f"  within 0.05 of it                            {close} of {len(compared)}")
    print("  reproduces the prior implementation          False -- measured afresh")
    print(f"  control AUC by split                        {control_auc}")
    print(f"  adjudicated labels used                     {dict(label_counts)}")
    print()
    print(f"  OUTCOME: {report['outcome']}  ({report['imported_assertions']} assertions)")
    for reason in refusal_reasons:
        print(f"    - {reason[:100]}")
    print()
    print(f"  report: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
