"""Stage 8: emit the staging artifact.

Each row is one item of the reference set: what the graph claims, what an independent
reference says, and who said it. The row carries its own provenance, so a row separated
from this manifest is still auditable.

Two things this stage is careful about.

*The address.* A treebank sentence cites a hymn, never a verse, so every aligned verse
address was established by text similarity. That is not good enough to call EXACT on its
own. But for the Rigveda a second, independent annotation is already in the graph: the
Zurich/VedaWeb lemmatisation, cited verse by verse in the mention layer's own evidence. A
row whose treebank annotation and whose Zurich citation name the same lemma for the same
canonical key has been addressed the same way by two unrelated annotation projects, and
that row is typed EXACT. Rows without that second witness are typed PROBABLE and are, by
the contract, staged and not importable.

*The word GOLD.* It does not appear in any row. The reference is published human
annotation of the Vedic text, which is the strongest thing available, and it is still not
a human annotation of *our* claims. Nobody reviewed a single VedaGraph assertion by hand.
The row type says so.
"""

from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

OUT = pathlib.Path("D:/VedaGraph/data/staging/quality")
SCRATCH = pathlib.Path(sys.argv[1])

ALGORITHM_VERSION = "vg-quality-reference-set-v1"
REFERENCE_SET = "vedanvaya-reference-set-v1"

SOURCES = [
    {
        "source_id": "UD_SANSKRIT_VEDIC_V2",
        "title": "UD_Sanskrit-Vedic (the Treebank of Vedic Sanskrit)",
        "url": "https://github.com/UniversalDependencies/UD_Sanskrit-Vedic",
        "licence": "CC BY-SA 4.0",
        "quality_class": "SCHOLARLY_EDITION",
        "annotation_class": "PUBLISHED_HUMAN_ANNOTATION",
        "annotators": [
            "Salvatore Scarlata", "Elia Ackermann", "Oliver Hellwig",
            "Erica Biagetti", "Sven Sellmer",
        ],
        "annotator_codes_in_the_data": ["Ol", "Er", "Au", "Sv", "Sa"],
        "annotation_status_as_declared_by_the_treebank": {
            "Lemmas": "converted from manual",
            "UPOS": "automatic with corrections",
            "XPOS": "converted from manual",
            "Features": "converted from manual",
            "Relations": "manual native",
        },
        "what_it_covers": (
            "27,182 sentences / 206,440 words over 57 Vedic texts. In scope for this "
            "corpus: RV 4,352 sentences, AVS 2,175, VSM 622. The Samaveda is absent, "
            "which is the third independent negative on Samavedic morphology after DCS "
            "and VedaWeb."
        ),
        "reference_scope_limit": (
            "It annotates the Vedic text. It does not annotate VedaGraph's claims, so it "
            "can decide whether a word is in a verse and which word it is, and it cannot "
            "decide whether a verse is *about* a concept."
        ),
        "citation": (
            "Hellwig, Scarlata, Ackermann and Widmer, 'The Treebank of Vedic Sanskrit', "
            "LREC 2020; Hellwig, Nehrdich and Sellmer, 'Data-driven Dependency Parsing "
            "of Vedic Sanskrit', LRE 57:1173-1206, 2023."
        ),
        "retrieved_at": "2026-09-15",
        "files": [
            "sa_vedic-ud-train.conllu", "sa_vedic-ud-dev.conllu", "sa_vedic-ud-test.conllu",
        ],
    },
    {
        "source_id": "VEDAWEB_ZURICH_VIA_GRAPH",
        "title": "VedaWeb / Zurich Rigveda lemmatisation, as already cited in the graph",
        "url": "https://vedaweb.uni-koeln.de/rigveda",
        "licence": "cited, not redistributed here",
        "quality_class": "SCHOLARLY_EDITION",
        "annotation_class": "PUBLISHED_HUMAN_ANNOTATION",
        "what_it_covers": (
            "Per-token lemma and morphology for the Rigveda. Not fetched: it is read out "
            "of the graph's own MENTIONS_DEVATA evidence quotes, which carry the Zurich "
            "lemma and case verbatim, and out of the 10,031 :Lemma nodes."
        ),
        "used_for": (
            "the deity-to-lemma bridge, and as the second independent witness that a "
            "treebank sentence was addressed to the right verse."
        ),
    },
    {
        "source_id": "VG_CANONICAL_STORE_2026_09_15",
        "title": "The canonical VedaGraph Neo4j store, read-only",
        "url": "internal: bolt://localhost:7687, database neo4j",
        "licence": "internal",
        "quality_class": "PRIMARY_DIGITAL_EDITION",
        "annotation_class": "NOT_AN_ANNOTATION_THE_SUBJECT_UNDER_TEST",
        "what_it_covers": "108,779 nodes / 265,295 relationships at measurement time.",
    },
    {
        "source_id": "INDEPENDENT_MODEL_ADJUDICATOR",
        "title": "The provider configured in .env, used only where a judgement is needed",
        "url": "https://openrouter.ai",
        "licence": "API terms",
        "quality_class": "MODEL_ASSISTED_DERIVATION",
        "annotation_class": "INDEPENDENT_MODEL_ADJUDICATION",
        "what_it_covers": (
            "The semantic assertions extracted by claude-opus-5, which this agent may "
            "not score because this agent IS claude-opus-5. Different vendor and "
            "different model family."
        ),
    },
]


def sha256_of(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd="D:/VedaGraph",
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def main() -> None:
    scores = json.loads((SCRATCH / "stage3_scores.json").read_text(encoding="utf-8"))
    population = json.loads((SCRATCH / "stage5_population.json").read_text(encoding="utf-8"))
    pua_metre = json.loads((SCRATCH / "stage6_pua_metre.json").read_text(encoding="utf-8"))
    alignment = json.loads((SCRATCH / "stage1_alignment.json").read_text(encoding="utf-8"))
    stage7_path = SCRATCH / "stage7_pua_llm.json"
    stage7 = (
        json.loads(stage7_path.read_text(encoding="utf-8")) if stage7_path.exists() else {}
    )
    per_mantra = scores["per_mantra"]

    # ---- the second witness: does the graph's Zurich citation agree on this address?
    graph = json.loads((SCRATCH / "stage2_graph.json").read_text(encoding="utf-8"))
    import re

    zurich_by_key: dict[str, set[str]] = collections.defaultdict(set)
    lemma_pattern = re.compile(r"\(([^;()]+)-;")
    for row in graph["mentions_devata"]:
        for item in json.loads(row["evidence"] or "[]"):
            for match in lemma_pattern.finditer(item.get("quote", "")):
                from lib_align import deaccent

                zurich_by_key[row["key"]].add(deaccent(match.group(1)).lower())
    address_confirmed: dict[str, bool] = {}
    for key, bucket in per_mantra.items():
        cited = zurich_by_key.get(key)
        address_confirmed[key] = bool(cited and cited & set(bucket["lemmas"]))
    confirmed_count = sum(1 for value in address_confirmed.values() if value)

    rows: list[dict] = []
    rejected: list[dict] = []

    def base(key: str, layer: str, source_id: str, evidence_layer: str,
             quality_class: str, mapping_method: str, mapping_confidence: str) -> dict:
        return {
            "canonical_key": key,
            "veda": key.split(":")[1],
            "evidence_layer": evidence_layer,
            "source_id": source_id,
            "source_locator": layer,
            "source_url": next(
                s.get("url", "") for s in SOURCES if s["source_id"] == source_id
            ),
            "quality_class": quality_class,
            "mapping_method": mapping_method,
            "mapping_confidence": mapping_confidence,
            "recension_verified": True,
            "recension_evidence": {
                "RV": "Sakala; the treebank cites RV by mandala and hymn and its text "
                      "matches our Sakala verse letter for letter after de-accenting",
                "AV": "Saunaka; the treebank's citation_text is AVS, explicitly the "
                      "Saunaka recension, and Paippalada (AVP) is a separate citation "
                      "code in the same file",
                "YV": "Madhyandina; the treebank's citation_text is VSM, the "
                      "Vajasaneyi-Samhita Madhyandina, matching our VG:WORK:YV:VSM",
                "SV": "not reached: the treebank has no Samavedic text",
            }[key.split(":")[1]],
            "algorithm_version": ALGORITHM_VERSION,
            "code_commit": CODE_COMMIT,
            "config_hash": CONFIG_HASH,
            "source_snapshot": source_id,
        }

    # ---------------------------------------------------- the adjudicated claim rows
    layer_populations = {
        "MENTIONS_DEVATA": 17165,
        "MENTIONS_ENTITY": 28227,
        "ABOUT_CONCEPT": 24969,
    }
    for layer_name, layer_key in (
        ("MENTIONS_DEVATA", "mentions_devata"),
        ("MENTIONS_ENTITY", "mentions_entity"),
        ("ABOUT_CONCEPT", "about_concept"),
    ):
        scored_rows = scores["scored"][layer_key]
        decided = [
            r for r in scored_rows
            if r["verdict"] in {"CONFIRMED", "CONFIRMED_VIA_UNSOUND_ALIAS", "REFUTED"}
        ]
        positives = sum(1 for r in decided if r["verdict"] != "REFUTED")
        for row in scored_rows:
            if row["verdict"] not in {
                "CONFIRMED", "CONFIRMED_VIA_UNSOUND_ALIAS", "REFUTED"
            }:
                rejected.append(
                    {
                        "canonical_key": row["canonical_key"],
                        "layer": layer_name,
                        "entity_key": row["entity_key"],
                        "reason_code": row["verdict"],
                        "reason": {
                            "UNDECIDED_PARTIAL_ANNOTATION":
                                "the annotators analysed only part of this verse, so an "
                                "absence here would be an artefact of coverage",
                            "UNDECIDED_REFERENCE_CANNOT_SEE_THIS_FORM":
                                "the claimed form is a word of our sandhied text but the "
                                "treebank is unsandhied, so the reference cannot carry "
                                "that surface at all",
                            "NOT_ADJUDICABLE":
                                "no human annotation for this verse, or no registry entry",
                        }.get(row["verdict"], row["verdict"]),
                        "verse_coverage": row.get("verse_coverage"),
                    }
                )
                continue
            key = row["canonical_key"]
            bucket = per_mantra[key]
            rows.append(
                {
                    **base(
                        key, layer_name, "UD_SANSKRIT_VEDIC_V2", "SOURCE_EXPLICIT",
                        "SCHOLARLY_EDITION",
                        "treebank sentence aligned to a verse by de-accented de-spaced "
                        "skeleton containment within the cited hymn, then confirmed "
                        "against the Zurich lemma the graph cites for the same key",
                        "EXACT" if address_confirmed.get(key) else "PROBABLE",
                    ),
                    "payload": {
                        "reference_set": REFERENCE_SET,
                        "reference_set_type": "INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET",
                        "not_human_gold_because":
                            "no human annotated any VedaGraph claim. The human annotation "
                            "is of the Vedic text, and this agent derived the verdict from "
                            "it mechanically.",
                        "layer": layer_name,
                        "graph_claim": {
                            "entity_key": row["entity_key"],
                            "claimed_forms": row["claimed_forms"],
                        },
                        "reference_verdict": row["verdict"],
                        "reference_detail": {
                            "h1_occurrence": row.get("h1"),
                            "h2_resolution": row.get("h2"),
                            "human_lemma": row.get("human_lemma"),
                            "human_upos": row.get("human_upos"),
                            "expected_lemma": row.get("expected_lemma"),
                            "false_positive_class": row.get("fp_class"),
                        },
                        "adjudicated_by": "PUBLISHED_HUMAN_TREEBANK",
                        "adjudicator_detail": {
                            "treebank_annotator_codes": bucket["annotators"],
                            "treebank_sentence_ids": bucket["sent_ids"],
                            "verse_annotation_coverage": bucket["verse_coverage"],
                            "address_confirmed_by_second_annotation":
                                address_confirmed.get(key, False),
                        },
                        "stratum": {
                            "veda": row["veda"],
                            **{k: v for k, v in row["strata"].items() if v is not None},
                            "alias_surface_class": row["alias_h2"],
                            "alias_soundness_class": row["alias_h3"],
                        },
                        "population": layer_populations[layer_name],
                        "processed_count": len(scored_rows),
                        "adjudicated_count": len(decided),
                        "positive_count": positives,
                        "evaluation": {
                            "independence": "the adjudicator is a published human "
                                            "annotation; no model of this project "
                                            "contributed to the verdict",
                            "producer_of_the_claim": row["strata"].get("method"),
                        },
                    },
                }
            )

    # ---------------------------------------------------- metre rows, text-derived
    metre_divergent = pua_metre["metre_rows"]
    for row in metre_divergent:
        rows.append(
            {
                **base(
                    row["key"], "HAS_CHANDAS", "VG_CANONICAL_STORE_2026_09_15",
                    "DETERMINISTIC_DERIVED", "PRIMARY_DIGITAL_EDITION",
                    "syllable nuclei counted in the verse's own text and compared with "
                    "the median count of every verse carrying the same metre name",
                    "EXACT",
                ),
                "payload": {
                    "reference_set": REFERENCE_SET,
                    "reference_set_type": "DETERMINISTIC_TEXT_DERIVED_REFERENCE",
                    "layer": "HAS_CHANDAS",
                    "graph_claim": {
                        "chandas_label": row["label"],
                        "quality_tier": row["tier"],
                        "attribution_precision": row["precision"],
                        "confidence": row["confidence"],
                    },
                    "reference_verdict": row["verdict"],
                    "reference_detail": {
                        "counted_syllables": row["counted"],
                        "median_for_this_metre": pua_metre["metre_medians"]
                        .get(row["label"], {})
                        .get("median_syllables"),
                        "deviation": row["deviation"],
                        "band": "a deviation of more than 4 syllables from the metre's "
                                "own median, which cancels the syllable counter's "
                                "systematic under-count on sandhied text",
                    },
                    "adjudicated_by": "DETERMINISTIC_TEXT_DERIVATION",
                    "stratum": {
                        "veda": row["veda"],
                        "tier": row["tier"],
                        "attribution_precision": row["precision"],
                        "nominal_confidence": row["confidence"],
                    },
                    "population": 16331,
                    "processed_count": sum(
                        v["decided"] + v.get("TOO_FEW_VERSES_FOR_A_MEDIAN", 0)
                        for v in pua_metre["metre_by_tier"].values()
                    ),
                    "adjudicated_count": sum(
                        v["decided"] for v in pua_metre["metre_by_tier"].values()
                    ),
                    "positive_count": sum(
                        v.get("CONSISTENT_WITH_ITS_METRE", 0)
                        for v in pua_metre["metre_by_tier"].values()
                    ),
                    "evaluation": {
                        "independence": "no model and no annotation; the claim is a "
                                        "syllable count and the text settles it",
                    },
                },
            }
        )

    # ---------------------------------------------------- the encoding defect rows
    for entry in pua_metre["pua_root_inventory"]:
        rejected.append(
            {
                "canonical_key": None,
                "layer": "SEMANTIC_ASSERTION_MORPHOLOGY",
                "reason_code": "PRIVATE_USE_AREA_CODEPOINT_IN_A_ROOT",
                "reason": "the stored root carries a Private Use Area codepoint, so it "
                          "cannot be joined to any lexicon or rendered by any consumer",
                "root_repr": entry["root_repr"],
                "codepoints": entry["codepoints"],
                "assertions_affected": entry["assertions"],
            }
        )

    # ---------------------------------------------------- the LLM-adjudicated rows
    llm = stage7.get("llm_adjudication") or {}
    for row in llm.get("rows", []):
        rows.append(
            {
                **base(
                    row["canonical_key"], "SEMANTIC_ASSERTION_LLM",
                    "INDEPENDENT_MODEL_ADJUDICATOR", "SEMANTIC_MODEL_EXTRACTION",
                    "MODEL_ASSISTED_DERIVATION",
                    "assertion read off the graph by assertion_id; no mapping performed",
                    "PROBABLE",
                ),
                "payload": {
                    "reference_set": REFERENCE_SET,
                    "reference_set_type": "INDEPENDENT_MODEL_ADJUDICATED",
                    "layer": "SEMANTIC_ASSERTION_LLM",
                    "graph_claim": {
                        "assertion_id": row["assertion_id"],
                        "semantic_predicate": row["claimed_predicate"],
                        "explicitness": row["explicitness"],
                        "role_slots_filled": row["slots"],
                        "produced_by": row["produced_by"],
                    },
                    "reference_verdict": row["verdict"],
                    "reference_detail": {"reason": row["reason"]},
                    "adjudicated_by": "INDEPENDENT_MODEL",
                    "adjudicator_detail": {
                        "model": row["adjudicated_by"],
                        "provider": llm.get("provider"),
                        "calls_made": llm.get("calls_made"),
                    },
                    "stratum": {
                        "veda": row["canonical_key"].split(":")[1],
                        "predicate": row["claimed_predicate"],
                        "slots": row["slots"],
                        "sample_stratum": row["stratum"],
                    },
                    "population": 2459,
                    "processed_count": llm.get("tasks_sent"),
                    "adjudicated_count": llm.get("verdicts_returned"),
                    "positive_count": llm.get("summary", {}).get("SUPPORTED", 0),
                    "evaluation": {
                        "independence": llm.get("independence"),
                        "why_not_this_agent": "these assertions were written by "
                                              "claude-opus-5 and this agent is "
                                              "claude-opus-5; campaign section 26",
                    },
                },
            }
        )

    # ---------------------------------------------------- rejected alignment candidates
    align_status = collections.Counter(
        f"{r['citation_text']}:{r['align_status']}" for r in alignment["records"]
    )
    for label, count in sorted(align_status.items()):
        citation, status = label.split(":", 1)
        if status == "ALIGNED":
            continue
        rejected.append(
            {
                "canonical_key": None,
                "layer": "REFERENCE_SET_ALIGNMENT",
                "reason_code": status,
                "reason": {
                    "AMBIGUOUS_MARGIN": "two verses of the cited hymn fit this sentence "
                                        "within 6 points of containment, so the address "
                                        "is not decided and was not forced",
                    "BELOW_FLOOR": "no verse of the cited hymn contains 62% of this "
                                   "sentence's skeleton",
                    "QUARANTINED_NON_MONOTONIC": "this sentence sits on one side of a "
                                                 "backwards jump in verse order within "
                                                 "its hymn; one of the pair is "
                                                 "misaddressed and the evidence does not "
                                                 "say which, so neither is used",
                    "HYMN_NOT_IN_CORPUS": "the cited hymn is not in this corpus",
                    "BAD_CITATION": "the citation is not a hymn address this corpus can "
                                    "resolve",
                }.get(status, status),
                "citation_text": citation,
                "sentences": count,
            }
        )
    for row in scores["alias_rows"]:
        if row["h2_verdict"] == "UNATTESTED_AS_A_TOKEN":
            rejected.append(
                {
                    "canonical_key": None,
                    "layer": "ALIAS_REGISTRY",
                    "reason_code": "UNATTESTED_AS_A_TOKEN_IN_206440_ANNOTATED_WORDS",
                    "reason": "this registry alias never occurs as a whole word in the "
                              "human-annotated corpus, so no edge it produced can be "
                              "adjudicated and its soundness is undecidable",
                    "entity_key": row["entity_key"],
                    "alias": row["alias"],
                }
            )

    # The contract admits one row per (canonical_key, source_id): rows get filtered and
    # re-exported, and a second row for the same pair is indistinguishable from a
    # duplicate that lost its context. So the per-claim verdicts are folded into one row
    # per verse per reference, and the claim count is carried inside the payload rather
    # than expressed as row multiplicity.
    grouped: dict[tuple, dict] = {}
    for row in rows:
        pair = (row["canonical_key"], row["source_id"])
        existing = grouped.get(pair)
        if existing is None:
            claim = {
                "layer": row["payload"]["layer"],
                "graph_claim": row["payload"]["graph_claim"],
                "reference_verdict": row["payload"]["reference_verdict"],
                "reference_detail": row["payload"].get("reference_detail"),
                "stratum": row["payload"]["stratum"],
            }
            payload = dict(row["payload"])
            for dropped in ("layer", "graph_claim", "reference_verdict",
                            "reference_detail", "stratum"):
                payload.pop(dropped, None)
            payload["layers_present"] = [claim["layer"]]
            payload["adjudicated_claims"] = [claim]
            payload["adjudicated_claim_count"] = 1
            payload["verdict_counts"] = {claim["reference_verdict"]: 1}
            grouped[pair] = {**row, "payload": payload}
            continue
        payload = existing["payload"]
        claim = {
            "layer": row["payload"]["layer"],
            "graph_claim": row["payload"]["graph_claim"],
            "reference_verdict": row["payload"]["reference_verdict"],
            "reference_detail": row["payload"].get("reference_detail"),
            "stratum": row["payload"]["stratum"],
        }
        payload["adjudicated_claims"].append(claim)
        payload["adjudicated_claim_count"] += 1
        payload["verdict_counts"][claim["reference_verdict"]] = (
            payload["verdict_counts"].get(claim["reference_verdict"], 0) + 1
        )
        if claim["layer"] not in payload["layers_present"]:
            payload["layers_present"].append(claim["layer"])
        # a verse whose address only one of its claims could confirm is the weaker of the
        # two, so the row keeps the weaker confidence
        if existing["mapping_confidence"] == "EXACT" and row["mapping_confidence"] != "EXACT":
            existing["mapping_confidence"] = row["mapping_confidence"]
    claim_total = len(rows)
    rows = sorted(grouped.values(), key=lambda r: (r["canonical_key"], r["source_id"]))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rows.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (OUT / "rejected.jsonl").write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rejected
        ),
        encoding="utf-8",
    )
    (OUT / "sources.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in SOURCES),
        encoding="utf-8",
    )
    print("rows:", len(rows), "folded from", claim_total, "adjudicated claims")
    print("rejected:", len(rejected), "sources:", len(SOURCES))
    print("claims by layer:", dict(collections.Counter(
        claim["layer"] for r in rows for claim in r["payload"]["adjudicated_claims"])))
    print("rows by mapping_confidence:", dict(
        collections.Counter(r["mapping_confidence"] for r in rows)))
    print("address confirmed by a second annotation:",
          confirmed_count, "of", len(address_confirmed))
    (SCRATCH / "stage8_meta.json").write_text(
        json.dumps(
            {
                "rows": len(rows),
                "adjudicated_claims": claim_total,
                "rejected": len(rejected),
                "address_confirmed": confirmed_count,
                "address_total": len(address_confirmed),
            }
        ),
        encoding="utf-8",
    )


CODE_COMMIT = commit()
CONFIG_HASH = hashlib.sha256(
    json.dumps(
        {
            "algorithm_version": ALGORITHM_VERSION,
            "align_floor": 0.62,
            "align_margin": 0.06,
            "verse_coverage_floor": 0.80,
            "alias_purity_floor": 0.80,
            "metre_median_floor": 12,
            "metre_divergence_band": 4,
            "llm_call_cap": 22,
            "sample_seed": 20260915,
        },
        sort_keys=True,
    ).encode()
).hexdigest()

if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    main()
