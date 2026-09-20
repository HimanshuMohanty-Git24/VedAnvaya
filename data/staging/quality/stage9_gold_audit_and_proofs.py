"""Stage 9: audit the three existing gold files, and write the proofs.

The 575-row theonym set was adjudicated by claude-opus-5. This agent is claude-opus-5, so
it may not re-adjudicate those rows -- but it can do something better: check them against
the human treebank wherever the treebank covers the same verse. That is an independent
test of a model adjudication, and it is per alias rather than per row, because two random
per-row samples in this project once reported 97%+ while a single alias was 82.9% wrong.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib_align import deaccent  # noqa: E402

SCRATCH = pathlib.Path(sys.argv[1])
OUT = pathlib.Path("D:/VedaGraph/data/staging/quality")
GOLD = pathlib.Path("D:/VedaGraph/data/gold")


def norm(text: str) -> str:
    return deaccent(text or "").lower().strip()


def read_jsonl(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    scores = json.loads((SCRATCH / "stage3_scores.json").read_text(encoding="utf-8"))
    population = json.loads((SCRATCH / "stage5_population.json").read_text(encoding="utf-8"))
    pua_metre = json.loads((SCRATCH / "stage6_pua_metre.json").read_text(encoding="utf-8"))
    calibration = json.loads((SCRATCH / "stage4_calibration.json").read_text(encoding="utf-8"))
    alignment = json.loads((SCRATCH / "stage1_alignment.json").read_text(encoding="utf-8"))
    stage7_path = SCRATCH / "stage7_pua_llm.json"
    stage7 = json.loads(stage7_path.read_text(encoding="utf-8")) if stage7_path.exists() else {}
    per_mantra = scores["per_mantra"]
    lemma_sets = scores["entity_lemma_sets"]
    proofs = OUT / "proofs"
    proofs.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------- the existing gold files
    semantic = read_jsonl(GOLD / "rigveda_semantic_gold_v1.jsonl")
    theonym = read_jsonl(GOLD / "theonym_mention_gold_v1.jsonl")
    ask = read_jsonl(GOLD / "ask_benchmark_v1.jsonl")

    theonym_checked = []
    for row in theonym:
        key = row.get("passage_key")
        bucket = per_mantra.get(key)
        entity = row.get("devata_id")
        if bucket is None or not entity:
            continue
        lemmas = set(lemma_sets.get(entity, {}))
        human_says_present = bool(lemmas & set(bucket["lemmas"]))
        model_said = row.get("gold_label") or row.get("deity_verdict")
        theonym_checked.append(
            {
                "row_id": row.get("row_id"),
                "passage_key": key,
                "devata_id": entity,
                "alias_or_forms": row.get("matched_forms") or [],
                "stratum": row.get("stratum"),
                "ambiguity_class": row.get("ambiguity_class"),
                "model_gold_label": model_said,
                "model_deity_verdict": row.get("deity_verdict"),
                "model_annotator": row.get("annotator"),
                "model_annotator_model": row.get("annotator_model"),
                "human_lemma_present": human_says_present,
                "bridged": bool(lemmas),
                "verse_annotation_coverage": bucket["verse_coverage"],
                "agreement": (
                    None if not lemmas
                    else (
                        (model_said == "MENTION") == human_says_present
                    )
                ),
            }
        )
    decidable = [r for r in theonym_checked if r["agreement"] is not None]
    agree = sum(1 for r in decidable if r["agreement"])
    per_alias: dict[str, list[dict]] = collections.defaultdict(list)
    for row in decidable:
        for form in row["alias_or_forms"] or ["<no form recorded>"]:
            per_alias[norm(form)].append(row)
    alias_agreement = sorted(
        (
            {
                "alias": alias,
                "rows": len(group),
                "agree": sum(1 for r in group if r["agreement"]),
                "agreement": round(sum(1 for r in group if r["agreement"]) / len(group), 4),
            }
            for alias, group in per_alias.items()
            if len(group) >= 3
        ),
        key=lambda row: (row["agreement"], -row["rows"]),
    )

    gold_audit = {
        "what_was_claimed_at_the_start": (
            "695 gold rows, zero human annotations, and the only populated set "
            "adjudicated by claude-opus-5 -- the same model family that produced much of "
            "what it would score. Verified by the lead before this agent began."
        ),
        "rigveda_semantic_gold_v1": {
            "rows": len(semantic),
            "annotators": dict(collections.Counter(r.get("annotator") for r in semantic)),
            "rows_with_any_entity": sum(1 for r in semantic if r.get("entities")),
            "rows_with_any_relation": sum(1 for r in semantic if r.get("relations")),
            "distinct_annotated_at": sorted(
                {r.get("annotated_at") for r in semantic}
            ),
            "verdict": "EMPTY_SCAFFOLD. Every row is UNANNOTATED, every entity and "
                       "relation list is empty, and every timestamp is epoch zero. It is "
                       "a sampling frame, and it is the right 120 verses to annotate, but "
                       "it holds no annotation and must not be called a gold set.",
            "companion_files_it_declares": {
                "present": [],
                "absent": ["the two declared companion files do not exist on disk"],
            },
        },
        "theonym_mention_gold_v1": {
            "rows": len(theonym),
            "annotators": dict(collections.Counter(r.get("annotator") for r in theonym)),
            "annotator_models": dict(
                collections.Counter(r.get("annotator_model") for r in theonym)
            ),
            "verdict": "MODEL_ADJUDICATED, by claude-opus-5. Section 26 forbids scoring "
                       "claude-opus-5 output with claude-opus-5, so this agent did not "
                       "re-adjudicate it. It tested it against human annotation instead.",
            "independent_check_against_human_annotation": {
                "rows_whose_verse_the_treebank_covers": len(theonym_checked),
                "rows_decidable_after_bridging": len(decidable),
                "model_agrees_with_human_annotation": agree,
                "agreement_rate": round(agree / len(decidable), 4) if decidable else None,
                "method": (
                    "for each row, does the human treebank annotate this verse with a "
                    "lemma in the claimed deity's lemma set, and does that match the "
                    "row's own MENTION / NOT_MENTION label"
                ),
                "limit": (
                    "this tests the mention decision, not the ambiguity class or the "
                    "referent choice, and a row the treebank cannot reach is not counted "
                    "either way"
                ),
                "per_alias_agreement_worst_first": alias_agreement[:25],
                "why_per_alias": (
                    "an earlier audit in this project found two random samples reporting "
                    "97%+ while a single alias was 82.9% wrong. A per-row rate cannot see "
                    "that and a per-alias table can."
                ),
            },
        },
        "ask_benchmark_v1": {
            "rows": len(ask),
            "has_annotator_field": any("annotator" in r for r in ask),
            "fields": sorted({key for r in ask for key in r}),
            "verdict": "NOT AN ANNOTATED SET AT ALL. 60 questions with no expected "
                       "answer, no annotator field and no reference. It is a question "
                       "list; whatever graded it was not this file.",
        },
        "conclusion": (
            "Nothing in data/gold/ is human gold, and this agent did not create human "
            "gold either. What it created is a reference set adjudicated by published "
            "human annotation of the Vedic text -- which is one step removed from human "
            "review of our claims, and the row type says so."
        ),
    }
    (proofs / "existing_gold_audit.json").write_text(
        json.dumps(gold_audit, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # ------------------------------------------------------- the calibration proof
    metre_buckets = {
        key: {
            "nominal_confidence": 1.0,
            "adjudicated": value["decided"],
            "observed_accuracy": value["observed_accuracy"],
        }
        for key, value in pua_metre["metre_by_tier"].items()
    }
    (proofs / "calibration.json").write_text(
        json.dumps(
            {
                "the_question": (
                    "The graph carries a property named confidence on 76,050 edges and "
                    "the API exposes min_confidence as a filter. Does the number behave "
                    "like a probability?"
                ),
                "the_answer": "No, on three independent grounds, each measured below.",
                "ground_1_the_value_is_mostly_a_constant": {
                    "confidence_bearing_edges": 76050,
                    "value_distribution": population["confidence_values"],
                    "predicates_with_a_single_constant": [
                        row["predicate"] for row in population["confidence_by_predicate"]
                        if row["guard"] == "SINGLE_CONSTANT"
                    ],
                    "edges_at_a_single_constant": sum(
                        row["total"] for row in population["confidence_by_predicate"]
                        if row["guard"] == "SINGLE_CONSTANT"
                    ),
                    "reading": (
                        "50,468 of 76,050 edges carry exactly 1.0, and for five "
                        "predicates the value never varies at all, so a threshold either "
                        "keeps every edge of that predicate or none."
                    ),
                },
                "ground_2_one_constant_spans_a_26_point_accuracy_range": {
                    "layer": "HAS_CHANDAS, every edge at confidence 1.0",
                    "buckets": metre_buckets,
                    "reading": (
                        "All of these edges say 1.0. Measured against the syllable count "
                        "of their own verses, the Atharvavedic inherited bucket is right "
                        "71.4% of the time and the Rigvedic inherited bucket 97.6%. One "
                        "nominal value, a 26-point spread in observed accuracy."
                    ),
                },
                "ground_3_where_the_value_varies_it_does_not_order_accuracy": {
                    "layer": "ABOUT_CONCEPT, the only high-volume predicate whose "
                             "confidence varies",
                    "buckets": [
                        row for row in calibration["calibration"]
                        if row["layer"] == "about_concept" and row["adjudicated"] >= 30
                    ],
                    "reading": (
                        "0.80 and 0.85 differ by five points of nominal confidence and "
                        "two points of measured lexical precision, in the same "
                        "direction but not the same size; and the 0.89 bucket, nominally "
                        "the most confident, measures below the 0.85 bucket on the strict "
                        "reading. The value is a per-branch constant -- 0.80 for a "
                        "Sanskrit token match, 0.85 when an English gloss agrees, 0.55 "
                        "for a sandhi-insensitive match -- and what it records is which "
                        "code path fired."
                    ),
                },
                "what_should_be_used_instead": (
                    "quality_tier and attribution_precision do carry signal: TIER_A / "
                    "PER_PASSAGE outperforms TIER_B / CONTAINER_INHERITED on metre in "
                    "the Atharvaveda by 21 points. They are the honest axis and they are "
                    "already on every edge."
                ),
                "what_is_still_not_measured": (
                    "No layer has a reliability curve, because a reliability curve needs "
                    "a confidence that varies continuously and this one takes 16 values "
                    "of which three cover 98%. Calibration in the proper sense is not "
                    "merely unmeasured here; the field's shape forbids it."
                ),
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    # ------------------------------------------------------- remaining proofs
    (proofs / "alias_soundness.json").write_text(
        json.dumps(
            {
                "what_this_is": (
                    "Every alias in the deity and concept registries, checked against "
                    "206,440 human-annotated words. For each: how often that exact "
                    "surface form occurs as a whole word in the human corpus, and which "
                    "lemma the annotators gave it."
                ),
                "why_per_alias": (
                    "A layer-level precision of 98% can contain an alias that is wrong "
                    "every time. Two random per-row samples in this project once "
                    "reported 97%+ while one alias was 82.9% wrong."
                ),
                "summary": {
                    "alias_rows": len(scores["alias_rows"]),
                    "by_surface_class": dict(
                        collections.Counter(
                            r["h2_verdict"] for r in scores["alias_rows"]
                        )
                    ),
                    "by_soundness_class": dict(
                        collections.Counter(
                            r["h3_verdict"] for r in scores["alias_rows"]
                        )
                    ),
                },
                "worst_aliases_by_measured_precision": calibration["per_alias_precision"][:60],
                "rows": scores["alias_rows"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    (proofs / "pua_encoding_defect.json").write_text(
        json.dumps(
            {
                "finding": (
                    "Private Use Area codepoints stand where Unicode letters belong, in "
                    "the canonical text of two Vedas and in the morphology layer's roots."
                ),
                "corrects_a_committed_audit": {
                    "the_committed_reading": (
                        "corpus-audit.md CORPUS_D01 and agent-2-verification.md read this "
                        "as a normaliser stripping the base letter along with its "
                        "combining mark, storing kr-with-ring as kdhi. Confirmed by the "
                        "lead."
                    ),
                    "what_is_actually_stored": (
                        "VG:AV:SAU:K01:S002:V002 SEARCH_DERIVATIVE holds U+006B U+E000 "
                        "U+0064 U+0068 U+0069. Nothing was stripped. The two codepoints "
                        "r + U+0325 were replaced by the single Private Use Area "
                        "codepoint U+E000, which has no glyph, so every terminal and "
                        "every report renders it as nothing -- which is why two "
                        "independent readers saw kdhi and inferred deletion."
                    ),
                    "why_it_matters": (
                        "The committed reading implies the information is gone and the "
                        "layer must be rebuilt from source. It is not gone. One letter "
                        "became one codepoint and the substitution table below restores "
                        "it exactly, derived from 5,123 verse pairs rather than guessed."
                    ),
                    "and_it_explains_the_disproven_symptom": (
                        "Agent 2 reported a search outage that the lead disproved. A "
                        "symmetric substitution is exactly why: query and index pass "
                        "through the same mapping, so they still match."
                    ),
                },
                "surfaces_affected": pua_metre["pua_scan"]["surfaces"],
                "mapping_derived_from_the_data": (stage7.get("pua_mapping") or {}),
                "root_inventory": pua_metre["pua_root_inventory"],
                "root_totals": pua_metre["pua_root_totals"],
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    (proofs / "reference_set_integrity.json").write_text(
        json.dumps(
            {
                "how_the_address_was_established": (
                    "The treebank cites a hymn, never a verse. Each sentence was aligned "
                    "to the verse of that hymn whose de-accented de-spaced skeleton best "
                    "contains it, accepted only above 0.62 containment and only when the "
                    "winner beat the runner-up by 0.06."
                ),
                "alignment_outcomes": alignment["status_counts"],
                "monotonicity_check": alignment["monotonicity"],
                "why_monotonicity": (
                    "Treebank sentences are ordered within a hymn, so the verse numbers "
                    "they align to must not go backwards. A backwards jump means one of "
                    "the two sentences is misaddressed. Both sides of every jump were "
                    "quarantined and are not used, because the evidence does not say "
                    "which of the two is wrong."
                ),
                "second_independent_witness": (
                    "For the Rigveda the graph already cites the Zurich/VedaWeb lemma "
                    "verse by verse. A row where the treebank annotation and the Zurich "
                    "citation name the same lemma for the same canonical key has been "
                    "addressed identically by two unrelated annotation projects, and only "
                    "those rows are typed EXACT."
                ),
                "verse_annotation_coverage": scores["coverage"],
                "treebank_size": scores["treebank"],
                "bridges": {
                    "zurich_lemma_bridge": scores["zurich_bridge"],
                    "curated_allomorph_bridge": scores.get("allomorph_bridge_applied"),
                    "entity_lemma_sets": len(scores["entity_lemma_sets"]),
                },
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    (proofs / "negative_results.json").write_text(
        json.dumps(
            {
                "what_could_not_be_scored_and_why": [
                    {
                        "layer": "Samavedic anything",
                        "status": "NO_REFERENCE_EXISTS",
                        "detail": (
                            "The treebank's 57 texts include no Samavedic text. With DCS "
                            "(271 corpora) and VedaWeb (7 texts) already recorded as "
                            "negative in Wave 0, that is three independent negatives. "
                            "1,844 Samavedic mantras carry 2,027 ABOUT_CONCEPT edges, "
                            "1,335 MENTIONS_DEVATA edges and 1,311 USES_FORMULA edges, "
                            "and not one of them can be adjudicated against any published "
                            "annotation."
                        ),
                    },
                    {
                        "layer": "morphology",
                        "status": "THERE_IS_NO_LAYER_TO_SCORE",
                        "detail": (
                            "The graph holds 10,031 :Lemma nodes carrying the Zurich "
                            "lemma inventory, whose own mantra_count properties imply "
                            "154,261 mantra-lemma pairs. 9,000 edges exist, over 39 "
                            "lemmas, all theonyms. Scoring that as morphology would be a "
                            "category error; it is a theonym mention index. Its recall "
                            "against the inventory the graph itself holds is 5.8%, and "
                            "within the 39 lemmas it attempted it is 99.9%."
                        ),
                    },
                    {
                        "layer": "formula membership and parallel detection",
                        "status": "SCORED_STRUCTURALLY_ONLY_AND_PREDATES_WAVE_2",
                        "detail": (
                            "Agents 10 and 12 are rebuilding these in this wave, so every "
                            "figure here predates their work and must not be quoted "
                            "against it. As it stands: 22,686 USES_FORMULA edges, all "
                            "TIER_B, 2,109 of them from a sandhi-substring method of the "
                            "same class as the concept layer's 0.55 tier; "
                            "SHARES_FORMULA_WITH still has zero edges; and 5,808 parallel "
                            "edges across four predicates carry no transformation type at "
                            "all, confirming CROSS_VEDA-002. The parallel layer does "
                            "carry the graph's only genuinely continuous quality measures "
                            "-- similarity, edit_ratio, lcs_ratio, token_jaccard, "
                            "ngram_jaccard -- which is what confidence should have looked "
                            "like."
                        ),
                    },
                    {
                        "layer": "aboutness, as distinct from lexical occurrence",
                        "status": "PARTLY_UNSCORABLE_BY_THIS_REFERENCE",
                        "detail": (
                            "A human lemma annotation can settle whether a word is in a "
                            "verse and which word it is. It cannot settle whether a verse "
                            "is *about* a concept. So ABOUT_CONCEPT is reported on its "
                            "lexical claim, which its own method field says is all it "
                            "makes, and the aboutness question is left open rather than "
                            "answered by this agent's opinion."
                        ),
                    },
                    {
                        "layer": "the three-role semantic assertion",
                        "status": "TWO_EARLIER_FIGURES_RECONCILED_NEITHER_WAS_WRONG",
                        "detail": (
                            "Benchmark Q67 said 17 assertions carry three role slots; "
                            "agent-1-verification.md measured 0. Both are right. 17 "
                            "assertions carry three role EDGES; 0 carry one edge of each "
                            "of the three TYPES. The disagreement was in the predicate, "
                            "not the count. 1,522 carry none, which both agree on."
                        ),
                    },
                ],
                "role_slot_histogram": population["semantic_assertions"][
                    "role_slot_histogram"
                ],
                "lemma_layer": population["lemma_layer"],
                "formula_layer": population["formula_layer"],
                "parallel_layer": population["parallel_layer"],
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    (proofs / "attribution_tier_conflict.json").write_text(
        json.dumps(
            {
                "finding": (
                    "1,176 mantras carry a source-explicit metre AND a "
                    "container-inherited metre that name different Chandas nodes, and "
                    "every one of those edges says confidence 1.0."
                ),
                "counts": population["multi_valued_attribution"],
                "chandas_conflicts": population["chandas_tier_conflict_total"],
                "examples": population["chandas_tier_conflict_examples"],
                "why_this_is_not_merely_untidy": (
                    "An Anukramani names a per-verse metre precisely when it differs from "
                    "the hymn's. So the disagreement is the index working, and the defect "
                    "is that the inherited edge was not withdrawn when the explicit one "
                    "arrived. A consumer reading HAS_CHANDAS on AVS 6.73.1 is handed both "
                    "bhurij and traistubham at identical confidence, with quality_tier as "
                    "the only thing that could break the tie -- and nothing in the API "
                    "contract says a reader must."
                ),
                "not_the_same_for_dedication": (
                    "HAS_DEVATA has only 6 multi-valued mantras and none spanning tiers, "
                    "and HAS_RISHI has 307 multi-valued and none spanning tiers. So this "
                    "is specific to metre, and the fix is scoped."
                ),
                "attribution_split": population["attribution_split"],
                "dedication_named_in_verse_by_tier": calibration["dedication_by_tier"],
                "how_to_read_the_dedication_table": (
                    "Dedication is not mention: a hymn dedicated to Indra need not name "
                    "him. So a low named_share is not an error rate. It is reported "
                    "because the gap between the tiers is the informative part -- 54.5% "
                    "of verses carrying a sukta-wide inherited dedication name that "
                    "deity, against 75% of the small per-verse single-mantra set."
                ),
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    (proofs / "precision_recall.json").write_text(
        json.dumps(
            {
                "precision": {
                    layer: {
                        "edges_on_annotated_verses": len(rows_),
                        "verdicts": dict(
                            collections.Counter(r["verdict"] for r in rows_)
                        ),
                        "false_positive_classes": dict(
                            collections.Counter(
                                r["fp_class"] for r in rows_ if r.get("fp_class")
                            )
                        ),
                    }
                    for layer, rows_ in scores["scored"].items()
                },
                "recall": {
                    layer: {k: v for k, v in value.items() if k != "miss_sample"}
                    for layer, value in scores["recall"].items()
                },
                "false_negative_classes_explained": {
                    "INFLECTION_ABSENT_FROM_ALIAS_LIST": (
                        "the human annotation shows the word is in the verse under an "
                        "inflected form the registry's closed alias list does not carry. "
                        "The pipeline cannot match it, and the entity is genuinely "
                        "present. This is the dominant class and the actionable one: the "
                        "alias lists are partial inflection tables, not paradigms."
                    ),
                    "ALIAS_LISTED_BUT_NOT_MATCHED": (
                        "the form IS in the alias list, the human annotation shows it in "
                        "the verse, and no edge exists. A genuine pipeline miss. Note one "
                        "alternative cause that this measurement cannot exclude: the "
                        "alias may have been claimed by a competing entity in the merged "
                        "alias namespace, in which case the edge exists and points "
                        "elsewhere."
                    ),
                },
                "morphology_rule_layer": calibration["morphology_summary"],
                "llm_layer": {
                    key: value
                    for key, value in (stage7.get("llm_adjudication") or {}).items()
                    if key != "rows"
                },
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    print("proofs written:", sorted(p.name for p in proofs.iterdir()))
    print("theonym gold rows the treebank could reach:", len(theonym_checked))
    print("decidable:", len(decidable), "agreement:",
          round(agree / len(decidable), 4) if decidable else None)
    print("worst aliases:", alias_agreement[:6])


if __name__ == "__main__":
    main()
