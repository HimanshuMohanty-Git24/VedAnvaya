# Rigveda Semantic V3 — Luna 508 Candidate Pilot

NO HUMAN GOLD EXISTS. CANDIDATE SEMANTIC OUTPUT IS NOT CANONICAL TRUTH. All assertions remain CANDIDATE / NEEDS_REVIEW; no predicates are unlocked.

## Starting health

The frozen V3 benchmark and independent replication were verified before this pilot.
No lower deterministic layer, frozen prompt, schema, ontology, policy, or human-gold file was modified.

## Frozen-input verification

PASS. The existing stratified selection contains 508 unique valid passage IDs, embeds the frozen 120 exactly, and all 120 overlapping EvidencePacket hashes match the frozen V3 seal. Prompt/schema/model/runtime hashes are pinned in `input_freeze.json` and the output seal.

## 508 configuration

- Selection: `data/builds/rigveda_semantic_pilot_v1.yaml`
- Batches: 22 deterministic batches of at most 24 packets
- Selection hash: `48add75cfb37cf6479ebf6e9454b2f2eab7151a8848e35ade160437fa8dd7919`
- Blind extraction: packet-local V3 only; previous semantic outputs were not read before sealing

## Blindness verification

The extraction phase read only the frozen V3 contract and the 508 EvidencePackets. `comparison_sources_opened = false` was pinned in the seal before this report phase.

## Output seal

`data/semantic/vedagraph-rigveda-semantic-luna-v3-508/v3_508_output_seal.json` is valid. `917 assertions` and `70 ontology-gap objects` are sealed; all remain candidate-only.

## Mantras processed

508

## Assertion count

917

## Assertions/mantra

1.8051

## No-claim count

143 (0.2815)

## Predicate distribution

| Predicate | Mantras | Assertions |
|---|---|---|
| INVOKES | 81 | 100 |
| PRAISES | 35 | 46 |
| REQUESTS | 83 | 113 |
| DESCRIBES | 91 | 110 |
| DESCRIBES_ACTION | 78 | 78 |
| INVOLVES_RITUAL | 78 | 78 |
| INVOLVES_OFFERING | 33 | 33 |
| INVOLVES_SUBSTANCE | 132 | 171 |
| REFERS_TO_NATURAL_PHENOMENON | 85 | 85 |
| REFERS_TO_PLACE | 56 | 56 |
| EXPRESSES | 47 | 47 |
| HAS_THEME | 0 | 0 |
| ASSOCIATED_WITH | 0 | 0 |
| CONTRASTS_WITH | 0 | 0 |

Observed predicates: **11/14**. Mandala distribution per predicate is pinned in the distribution report. `STRONG_INFERENCE` remains **0**, so there is no unexpected rise from the frozen benchmark distribution.

## Object-kind distribution

| Object kind | Occurrences |
|---|---|
| CANONICAL_ENTITY_REF | 256 |
| EVENT | 78 |
| NATURAL_PHENOMENON_REF | 85 |
| OFFERING_REF | 33 |
| ONTOLOGY_GAP_REF | 70 |
| PLACE_REF | 56 |
| REQUESTED_OUTCOME | 113 |
| RITUAL_EVENT | 78 |
| STATE_REF | 47 |
| SUBSTANCE_REF | 171 |

## Canonical entity reuse

Canonical references: **256**. Unknown canonical IDs: **0**. Canonical contradiction candidates: **0**. No auto-promotion occurred.

## Non-canonical semantic candidates

Non-canonical typed assertion objects: **661**; ontology-gap objects are reported separately and are not forced into semantic types.

## Explicitness distribution

{"EXPLICIT": 917}. `INTERPRETIVE` is forbidden by the frozen V3 schema.

## Validator/evidence results

Validator failures: **0**. Evidence failures: **0**. Average evidence anchors/assertion: **1.0**.

## Request QA

{
  "assertion_count": 113,
  "coordinated_assertion_ids": [],
  "coordinated_request_violations": 0,
  "one_outcome_per_assertion": true
}

## Event QA

{
  "actor_patient_inferred_count": 0,
  "assertion_count": 78,
  "event_object_violations": 0
}

## Ritual/offering/substance QA

{
  "boundary_violations": {
    "INVOLVES_OFFERING": 0,
    "INVOLVES_RITUAL": 0,
    "INVOLVES_SUBSTANCE": 0
  },
  "cross_kind_leakage": 0
}

## Natural phenomenon QA

{
  "canonical_entity_reuse_violations": 0
}

## Place/opaque spatial QA

{
  "opaque_spatial_referents": 0,
  "place_assertions": 56
}

## Embedded 120 stability

Exact assertion-set agreement: **120/120**; predicate presence: **120/120**; canonical objects: **120/120**; typed objects: **120/120**; evidence anchors: **120/120**; no-claim: **120/120**. High-severity differences: **0**. See the dedicated report.

## New 388 results

{
  "assertions": 706,
  "assertions_per_mantra": 1.8196,
  "boundary_violations": 0,
  "canonical_refs": 199,
  "evidence_failures": 0,
  "explicitness": {
    "EXPLICIT": 706
  },
  "mantras": 388,
  "no_claims": 115,
  "object_kind_distribution": {
    "CANONICAL_ENTITY_REF": 199,
    "EVENT": 58,
    "NATURAL_PHENOMENON_REF": 69,
    "OFFERING_REF": 23,
    "ONTOLOGY_GAP_REF": 41,
    "PLACE_REF": 42,
    "REQUESTED_OUTCOME": 86,
    "RITUAL_EVENT": 59,
    "STATE_REF": 32,
    "SUBSTANCE_REF": 138
  },
  "ontology_gaps": {
    "KINSHIP_ROLE_UNMODELED": {
      "count": 1,
      "example_mantra_ids": [
        "VG:RV:SAK:M03:S004:V008"
      ],
      "object_families": [
        "ONTOLOGY_GAP_REF"
      ],
      "predicate_context": "not encoded by the V3 gap object"
    },
    "PATRON_ROLE_UNMODELED": {
      "count": 5,
      "example_mantra_ids": [
        "VG:RV:SAK:M01:S013:V011",
        "VG:RV:SAK:M08:S046:V002",
        "VG:RV:SAK:M09:S052:V005",
        "VG:RV:SAK:M09:S087:V004",
        "VG:RV:SAK:M10:S107:V010"
      ],
      "object_families": [
        "ONTOLOGY_GAP_REF"
      ],
      "predicate_context": "not encoded by the V3 gap object"
    },
    "PERSON_LIKE_REFERENT_UNMODELED": {
      "count": 35,
      "example_mantra_ids": [
        "VG:RV:SAK:M01:S083:V001",
        "VG:RV:SAK:M01:S120:V008",
        "VG:RV:SAK:M01:S133:V006",
        "VG:RV:SAK:M01:S137:V003",
        "VG:RV:SAK:M01:S150:V003",
        "VG:RV:SAK:M03:S017:V003",
        "VG:RV:SAK:M03:S062:V002",
        "VG:RV:SAK:M04:S001:V001",
        "VG:RV:SAK:M04:S019:V010",
        "VG:RV:SAK:M05:S087:V008"
      ],
      "object_families": [
        "ONTOLOGY_GAP_REF"
      ],
      "predicate_context": "not encoded by the V3 gap object"
    }
  },
  "predicate_distribution": {
    "ASSOCIATED_WITH": {
      "assertion_count": 0,
      "mantra_count": 0
    },
    "CONTRASTS_WITH": {
      "assertion_count": 0,
      "mantra_count": 0
    },
    "DESCRIBES": {
      "assertion_count": 82,
      "mantra_count": 69
    },
    "DESCRIBES_ACTION": {
      "assertion_count": 58,
      "mantra_count": 58
    },
    "EXPRESSES": {
      "assertion_count": 32,
      "mantra_count": 32
    },
    "HAS_THEME": {
      "assertion_count": 0,
      "mantra_count": 0
    },
    "INVOKES": {
      "assertion_count": 78,
      "mantra_count": 61
    },
    "INVOLVES_OFFERING": {
      "assertion_count": 23,
      "mantra_count": 23
    },
    "INVOLVES_RITUAL": {
      "assertion_count": 59,
      "mantra_count": 59
    },
    "INVOLVES_SUBSTANCE": {
      "assertion_count": 138,
      "mantra_count": 105
    },
    "PRAISES": {
      "assertion_count": 39,
      "mantra_count": 29
    },
    "REFERS_TO_NATURAL_PHENOMENON": {
      "assertion_count": 69,
      "mantra_count": 69
    },
    "REFERS_TO_PLACE": {
      "assertion_count": 42,
      "mantra_count": 42
    },
    "REQUESTS": {
      "assertion_count": 86,
      "mantra_count": 63
    }
  }
}. See the dedicated report.

## Distribution drift

The full drift tables, including relative differences and review flags, are in the dedicated distribution report. Flags are review signals, not automatic errors.

## Per-Mandala statistics

| Mandala | Mantras | Assertions | Assertions/mantra | No-claim rate | Gap rate |
|---|---|---|---|---|---|
| 1 | 89 | 138 | 1.5506 | 0.4831 | 0.1348 |
| 2 | 16 | 43 | 2.6875 | 0.1875 | 0.0 |
| 3 | 20 | 48 | 2.4 | 0.1 | 0.15 |
| 4 | 23 | 50 | 2.1739 | 0.1304 | 0.087 |
| 5 | 27 | 52 | 1.9259 | 0.2593 | 0.1111 |
| 6 | 28 | 46 | 1.6429 | 0.2857 | 0.1071 |
| 7 | 37 | 74 | 2.0 | 0.1892 | 0.0811 |
| 8 | 64 | 117 | 1.8281 | 0.2656 | 0.2031 |
| 9 | 78 | 155 | 1.9872 | 0.1282 | 0.1154 |
| 10 | 126 | 194 | 1.5397 | 0.3413 | 0.1746 |

## Devata diagnostic statistics

Deterministic `HAS_DEVATA` metadata was used only for aggregate diagnostics. No theological conclusion is drawn from these rates. Full data is in the distribution report.

## Semantic candidate-head inventory

Exact `object_kind + normalized_head` inventories and deterministic duplicate review groups are in the ontology-gaps report. No fuzzy grouping or global canonicalization was performed.

## Semantic predicate co-occurrence

{"INVOKES + REQUESTS": 17, "PRAISES + DESCRIBES": 4, "RITUAL + OFFERING + SUBSTANCE": 8}. These are descriptive within-mantra counts, not graph relations.

## Exact/near parallel semantic consistency

{"EXACT: partial overlap": 2, "EXACT: same semantic assertion set": 4, "NEAR: different semantic candidates": 11, "NEAR: partial overlap": 10, "NEAR: same semantic assertion set": 11}. Candidates were compared, never copied; exact textual disagreements are review signals.

## Ontology-gap inventory

{
  "KINSHIP_ROLE_UNMODELED": {
    "count": 1,
    "example_mantra_ids": [
      "VG:RV:SAK:M03:S004:V008"
    ],
    "object_families": [
      "ONTOLOGY_GAP_REF"
    ],
    "predicate_context": "not encoded by the V3 gap object"
  },
  "PATRON_ROLE_UNMODELED": {
    "count": 8,
    "example_mantra_ids": [
      "VG:RV:SAK:M01:S013:V011",
      "VG:RV:SAK:M01:S061:V003",
      "VG:RV:SAK:M05:S053:V016",
      "VG:RV:SAK:M08:S046:V002",
      "VG:RV:SAK:M09:S052:V005",
      "VG:RV:SAK:M09:S087:V004",
      "VG:RV:SAK:M09:S087:V009",
      "VG:RV:SAK:M10:S107:V010"
    ],
    "object_families": [
      "ONTOLOGY_GAP_REF"
    ],
    "predicate_context": "not encoded by the V3 gap object"
  },
  "PERSON_LIKE_REFERENT_UNMODELED": {
    "count": 61,
    "example_mantra_ids": [
      "VG:RV:SAK:M01:S035:V005",
      "VG:RV:SAK:M01:S043:V006",
      "VG:RV:SAK:M01:S051:V009",
      "VG:RV:SAK:M01:S083:V001",
      "VG:RV:SAK:M01:S120:V008",
      "VG:RV:SAK:M01:S122:V008",
      "VG:RV:SAK:M01:S127:V002",
      "VG:RV:SAK:M01:S133:V006",
      "VG:RV:SAK:M01:S137:V003",
      "VG:RV:SAK:M01:S150:V003"
    ],
    "object_families": [
      "ONTOLOGY_GAP_REF"
    ],
    "predicate_context": "not encoded by the V3 gap object"
  }
}

## High-risk review queue

50 deterministic cases were selected from the requested risk strata. This is not human gold.

## Existing expert-case status

| Mantra | In 508 | V3 stable | Unresolved status |
|---|---|---|---|
| VG:RV:SAK:M09:S068:V010 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M08:S005:V014 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M04:S022:V006 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M10:S030:V003 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M08:S022:V014 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M08:S001:V017 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M10:S108:V001 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M02:S008:V006 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M06:S068:V006 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M09:S087:V009 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M09:S074:V001 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M09:S104:V005 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M04:S035:V009 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M02:S017:V005 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M01:S094:V013 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M06:S013:V001 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M10:S089:V008 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M04:S034:V006 | True | True | STABLE_MODEL_DISAGREEMENT |
| VG:RV:SAK:M08:S060:V011 | True | True | EXPERT_PHILOLOGY_REQUIRED |
| VG:RV:SAK:M10:S027:V013 | True | True | EXPERT_PHILOLOGY_REQUIRED |

## Performance

{
  "aggregation_comparison_reporting_seconds": 1.371862,
  "evidence_packet_preparation_seconds": 5.923966,
  "extraction_batch_handling_seconds": 0.555125,
  "total_wall_seconds_recorded_from_script_start": 1.371867,
  "validation_seconds": null
}. No API billing or token cost was invented.

## Tests

See the final handoff for the executed test commands and any incomplete checks.

## Ruff/mypy

Recorded in the final handoff after the quality suite.

## Git safety

Frozen semantic runs and human gold were not overwritten. Bulk 508 semantic output remains under the ignored `data/semantic` policy; only code, tests, reports, and the manifest are intended for tracking.

## Manifest

`docs/manifests/vedagraph-rigveda-semantic-luna-v3-508.json` pins corpus, knowledge, lexical, frozen V3 original/replication metadata, contract hashes, selection and packet hashes, output hashes, model/runtime/reasoning, `human_gold = UNANNOTATED`, `unlocked_predicates = []`, and `canonical_promotion = false`.

## Final state

`V3_508_CANDIDATE_PILOT_READY`

## Recommendation about whether a full 10,552-mantra candidate extraction should be the next session

The 508 pilot is a candidate-only diagnostic and does not authorize a full-corpus run. The recommendation is **do not start the 10,552-mantra extraction until the high-risk queue and any flagged drift/parallel cases receive review**.
