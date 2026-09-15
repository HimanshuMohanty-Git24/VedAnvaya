"""Assemble the staging artifact for semantic roles across all four Saṃhitās.

Emits the assessed set, not the positives. Section 32 of the campaign brief exists
because the graph cannot tell "assessed and empty" from "never assessed" for any
dimension but audio, so every one of the 20,210 mantras leaves this run in exactly one
of three states, each with a stated reason:

  accepted    at least one assertion
  rejected    examined, and the reason there is nothing is a property of the text or of
              what the sources cover
  unresolved  the source does cover this mantra and the address could not be established

``candidates_considered`` is 20,210, and it balances.
"""
from __future__ import annotations

import collections
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib_roles as L  # noqa: E402

ALGORITHM_VERSION = "vedagraph-semantic-roles-four-veda-v1"
SCHEMA_VERSION = "1.0"
DOMAIN = "semantic_roles"
AGENT = 9

WORK_RECENSION = {
    "RV": (
        "Śākala",
        "The analysis is the University of Zurich morphosyntactic annotation of "
        "Lubotsky's text of the Śākala Rigveda, published through VedaWeb; every token "
        "carries passage_key VG:RV:SAK:..., which is this repository's Śākala spine. No "
        "other Rigvedic śākhā is digitally extant.",
    ),
    "AV": (
        "Śaunaka",
        "DCS keeps 'Atharvaveda (Śaunaka)' and 'Atharvaveda (Paippalāda)' as two "
        "separate corpora (1,038 and 275 blobs, enumerated via the git trees API); only "
        "the Śaunaka directory was fetched. Corroborated structurally: the Śaunaka "
        "directory's hymns per kāṇḍa, tallied from its filenames, are 35/36/31/40/31/"
        "142/118/10/10/10/10/5/4/2/18/9/1/4 for kāṇḍas 1-18, which is this repository's "
        "Śaunaka spine exactly. VedaWeb's only annotated Atharvaveda is Paippalāda and "
        "was deliberately not used.",
    ),
    "YV": (
        "Mādhyandina (Śukla)",
        "DCS names the śākhā in the corpus title, 'Vājasaneyisaṃhitā (Mādhyandina)', "
        "which is the recension of this repository's VG:YV:VSM spine. The Kāṇva "
        "Vājasaneyi and the Kṛṣṇa-Yajurvedic saṃhitās (TS, MS, KS) are separate DCS "
        "corpora and were not used.",
    ),
    "SV": (
        "Kauthuma Ārcika",
        "The addressed verse is this repository's own Kauthuma Ārcika key. What is "
        "transferred is an analysis of a letter-identical Śākala Rigvedic verse, so the "
        "row asserts nothing about a Samavedic recension's reading beyond the identity "
        "of the string, which is verified by equality rather than by similarity.",
    ),
}

DERIVATION_NOTE = {
    "MORPHOLOGY_RULE_CASE": (
        "Roles read from morphological case within one metrical pada (Rigveda) or one "
        "sentence (DCS chapters with no dependency parse). The underlying annotation "
        "carries no HEAD, no DEPREL and no clause boundary, so this states which case "
        "stood beside which verb, not which nominal is the syntactic subject of which "
        "verb. action_root_map.yaml records the same caution in its own recommendations."
    ),
    "TREEBANK_DEPREL": (
        "Roles read from the verb's own dependency children in the DCS treebank, using "
        "the treebank's obl:goal / obl:source / obl:instr / obl:loc subtype labels where "
        "present rather than inferring a role from case."
    ),
    "CROSS_VEDA_TEXT_IDENTITY": (
        "The Samavedic verse's letter skeleton is identical to that of a Rigvedic verse "
        "which carries an analysis; the analysis of the same words is transferred "
        "unchanged. Not independently annotated, and the first thing to re-derive if a "
        "Samavedic annotation ever appears."
    ),
}


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=r"D:\VedaGraph",
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def veda_of(key: str) -> str:
    return key.split(":")[1]


def confidence_from_alignment(items) -> tuple[str, str]:
    fractions = [i["align_fraction"] for i in items]
    concentrations = [i["align_concentration"] for i in items]
    if min(concentrations) >= 1.0 and min(fractions) >= 0.90:
        return "EXACT", (
            "every contributing treebank sentence matched this verse's letters at "
            f"{min(fractions):.4f} or better with all matched characters inside this one "
            "verse"
        )
    return "VERIFIED_SEGMENT", (
        "the contributing treebank sentences were placed inside this hymn by whole-hymn "
        f"skeleton alignment; weakest sentence match {min(fractions):.4f}, weakest "
        f"single-verse concentration {min(concentrations):.4f}"
    )


def main(scratch: str, out_dir: str) -> None:
    head = git_head()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    rv = json.load(io.open(os.path.join(scratch, "rv_assertions.json"), encoding="utf-8"))
    rv_stats = json.load(io.open(os.path.join(scratch, "rv_out.json"), encoding="utf-8"))
    av = json.load(io.open(os.path.join(scratch, "dcs_av.json"), encoding="utf-8"))
    yv = json.load(io.open(os.path.join(scratch, "dcs_yv.json"), encoding="utf-8"))
    sv = json.load(io.open(os.path.join(scratch, "sv_proj.json"), encoding="utf-8"))
    keys = json.load(io.open(os.path.join(scratch, "graph_keys.json"), encoding="utf-8"))
    fetch = json.load(io.open(os.path.join(scratch, "dcs_fetch.json"), encoding="utf-8"))

    # --- the source snapshots -----------------------------------------------------
    dcs_shas = sorted(entry["sha256"] for entry in fetch if entry.get("sha256"))
    dcs_snapshot = "DCS:" + sha256_text("\n".join(dcs_shas))
    zurich_manifest = json.load(
        io.open(r"D:\VedaGraph\data\knowledge\rigveda_lexical_v1\manifest.json", encoding="utf-8")
    )
    zurich_snapshot = (
        zurich_manifest.get("snapshot_id")
        or zurich_manifest.get("source_snapshot_id")
        or "VEDAWEB:ZURICH:rigveda_lexical_v1"
    )
    if isinstance(zurich_snapshot, list):
        zurich_snapshot = zurich_snapshot[0]

    config = {
        "algorithm_version": ALGORITHM_VERSION,
        "predicate_vocabulary": "vedagraph-action-predicates-v1",
        "root_map": "vedagraph-action-root-map-v1",
        "registry_roles": list(L.REGISTRY_ROLES),
        "proposed_roles": list(L.PROPOSED_ROLES),
        "brief_role_aliases": L.BRIEF_ROLE_ALIASES,
        "sentence_match_floor": 0.60,
        "verse_concentration_floor": 0.70,
        "hymn_match_floor": 0.70,
        "sv_requires_skeleton_identity": True,
        "model_assisted_extraction_used": False,
        "lib_roles_sha256": sha256_file(os.path.join(HERE, "lib_roles.py")),
        "extract_rv_sha256": sha256_file(os.path.join(HERE, "extract_rv.py")),
        "extract_dcs_sha256": sha256_file(os.path.join(HERE, "extract_dcs.py")),
        "extract_sv_sha256": sha256_file(os.path.join(HERE, "extract_sv.py")),
    }
    config_hash = sha256_text(json.dumps(config, sort_keys=True, ensure_ascii=False))

    # --- which mantras a source reaches at all ------------------------------------
    av_hymns_covered = set()
    for entry in av["hymn_report"]:
        if entry["status"] == "ALIGNED":
            kanda, hymn = re.findall(r"\d+", entry["hymn"])[:2]
            av_hymns_covered.add((int(kanda), int(hymn)))
    av_hymns_refused = set()
    for entry in av["hymn_report"]:
        if entry["status"] == "REFUSED_HYMN_BELOW_MATCH_FLOOR":
            kanda, hymn = re.findall(r"\d+", entry["hymn"])[:2]
            av_hymns_refused.add((int(kanda), int(hymn)))
    yv_adhyayas_covered = {
        int(re.findall(r"\d+", e["hymn"])[0])
        for e in yv["hymn_report"]
        if e["status"] == "ALIGNED"
    }

    reach = {}
    for key in keys["RV"]:
        reach[key] = "ZURICH"
    for key in keys["AV"]:
        m = re.match(r"VG:AV:SAU:K(\d+):S(\d+):V(\d+)$", key)
        hymn = (int(m.group(1)), int(m.group(2)))
        if hymn in av_hymns_covered:
            reach[key] = "DCS"
        elif hymn in av_hymns_refused:
            reach[key] = "DCS_HYMN_REFUSED"
        else:
            reach[key] = "NONE"
    for key in keys["YV"]:
        m = re.match(r"VG:YV:VSM:A(\d+):V(\d+)$", key)
        reach[key] = "DCS" if int(m.group(1)) in yv_adhyayas_covered else "NONE"
    for key in keys["SV"]:
        reach[key] = "PROJECTION_ONLY"

    population = {veda: len(keys[veda]) for veda in ("RV", "SV", "YV", "AV")}
    reachable = collections.Counter(
        veda_of(k) for k, v in reach.items() if v in ("ZURICH", "DCS")
    )
    positives = {
        "RV": len(rv),
        "AV": len(av["rows"]),
        "YV": len(yv["rows"]),
        "SV": len(sv["accepted"]),
    }
    tokens_processed = {
        "RV": rv_stats["stats"]["tokens_processed"],
        "AV": av["stats"]["tokens_processed"],
        "YV": yv["stats"]["tokens_processed"],
        "SV": 0,
    }

    census = {
        "population_per_veda": population,
        "source_reachable_per_veda": dict(reachable),
        "positive_per_veda": positives,
        "tokens_processed_per_veda": tokens_processed,
        "tokens_processed_note": (
            "SV is 0 because no morphological token of the Sāmaveda Saṃhitā exists in any "
            "public resource. It is a measured zero over an enumerated search, not an "
            "unknown: see proofs/sv_morphology_unavailable.json."
        ),
    }

    def base_row(key, derivation, source_id, snapshot, locator, confidence, confidence_evidence):
        veda = veda_of(key)
        recension, recension_evidence = WORK_RECENSION[veda]
        return {
            "canonical_key": key,
            "veda": veda,
            "evidence_layer": "DETERMINISTIC_DERIVED",
            "source_id": source_id,
            "source_snapshot": snapshot,
            "source_locator": locator,
            "source_url": (
                "https://github.com/OliverHellwig/sanskrit/tree/master/dcs/data/conllu/files"
                if source_id == "DCS"
                else "https://vedaweb.uni-koeln.de/rigveda"
            ),
            "quality_class": "SCHOLARLY_EDITION",
            "mapping_method": DERIVATION_NOTE[derivation],
            "mapping_confidence": confidence,
            "mapping_confidence_evidence": confidence_evidence,
            "recension_verified": True,
            "recension_evidence": f"{recension}. {recension_evidence}",
            "algorithm_version": ALGORITHM_VERSION,
            "config_hash": config_hash,
            "code_commit": head,
            "population": population[veda],
            "processed_count": population[veda],
            "positive_count": positives[veda],
            "veda_census": {
                "population": population[veda],
                "source_reachable": reachable.get(veda, 0),
                "processed": population[veda],
                "positive": positives[veda],
                "tokens_processed": tokens_processed[veda],
            },
            "evaluation": ROW_EVALUATION,
        }

    rows = []
    rejected = []

    # ---------------------------------------------------------------- Rigveda -----
    for key in keys["RV"]:
        assertions = rv.get(key)
        if not assertions:
            rejected.append(
                {
                    "canonical_key": key,
                    "veda": "RV",
                    "state": "REJECTED",
                    "reason": "NO_MAPPED_FINITE_VERB_IN_THE_ANNOTATION",
                    "detail": (
                        "the Zurich annotation covers this verse, and it holds no finite "
                        "verbal root that the bounded predicate vocabulary maps -- either "
                        "no finite verb at all, or only roots the root map adjudicated as "
                        "UNMAPPED_ROOT. An honest abstention, not a missing source."
                    ),
                    "source_id": "VEDAWEB",
                    "source_snapshot": zurich_snapshot,
                    "algorithm_version": ALGORITHM_VERSION,
                    "config_hash": config_hash,
                    "code_commit": head,
                }
            )
            continue
        row = base_row(
            key,
            "MORPHOLOGY_RULE_CASE",
            "VEDAWEB",
            zurich_snapshot,
            f"rigveda_lexical_v1/tokens.jsonl, passage_key={key}",
            "EXACT",
            "the annotation is keyed on this repository's own canonical passage key; no "
            "alignment step was required",
        )
        row["payload"] = {
            "derivation": "MORPHOLOGY_RULE_CASE",
            "assertion_count": len(assertions),
            "assertions": assertions,
            "role_scope": "METRICAL_PADA",
            "annotation_method": "MANUAL_SCHOLARLY_ANNOTATION",
            "annotation_provenance": (
                "University of Zurich morphosyntactic annotation of Lubotsky's Rigveda "
                "(Widmer/Scarlata), corrected against Grassmann by Halfmann and Korobzow"
            ),
            "dependency_parse_available": False,
        }
        rows.append(row)

    # -------------------------------------------------- Atharvaveda and Yajurveda --
    for veda, bundle in (("AV", av), ("YV", yv)):
        for key in keys[veda]:
            items = bundle["rows"].get(key)
            if not items:
                state, reason, detail = _negative_reason(veda, key, reach[key], bundle)
                rejected.append(
                    {
                        "canonical_key": key,
                        "veda": veda,
                        "state": state,
                        "reason": reason,
                        "detail": detail,
                        "source_id": "DCS",
                        "source_snapshot": dcs_snapshot,
                        "algorithm_version": ALGORITHM_VERSION,
                        "config_hash": config_hash,
                        "code_commit": head,
                    }
                )
                continue
            confidence, evidence = confidence_from_alignment(items)
            locators = sorted({i["locator"] for i in items})
            row = base_row(
                key,
                "TREEBANK_DEPREL",
                "DCS",
                dcs_snapshot,
                "; ".join(locators),
                confidence,
                evidence,
            )
            derivations = sorted({i["assertion"]["derivation"] for i in items})
            row["mapping_method"] = " || ".join(DERIVATION_NOTE[d] for d in derivations)
            row["payload"] = {
                "derivation": derivations,
                "assertion_count": len(items),
                "assertions": [i["assertion"] for i in items],
                "aligned_sentences": [
                    {
                        "sent_id": i["sent_id"],
                        "align_fraction": i["align_fraction"],
                        "align_concentration": i["align_concentration"],
                        "sentence_text": i["sentence_text"],
                    }
                    for i in items
                ],
                "role_scope": "DEPENDENCY_SUBTREE_OR_SENTENCE",
                "annotation_method": "SCHOLARLY_ANNOTATION_ONE_ANNOTATOR_VERIFIED",
                "annotation_provenance": (
                    "Digital Corpus of Sanskrit, Oliver Hellwig, CC BY 4.0; the readme "
                    "states 'The analysis of each string has been verified by one "
                    "annotator.'"
                ),
                "dependency_parse_available": "TREEBANK_DEPREL" in derivations,
            }
            rows.append(row)

    # ---------------------------------------------------------------- Samaveda -----
    for key in keys["SV"]:
        entry = sv["accepted"].get(key)
        if not entry:
            refusal = sv["refused"].get(key) or {
                "reason": "NOT_EXAMINED",
                "detail": "unexpected: the Samavedic pass examines every verse",
            }
            rejected.append(
                {
                    "canonical_key": key,
                    "veda": "SV",
                    "state": "REJECTED",
                    "reason": refusal["reason"],
                    "detail": refusal["detail"],
                    "rv_key": refusal.get("rv_key"),
                    "containment_to_closest_rigvedic_parallel": refusal.get("containment"),
                    "source_id": "VEDAWEB",
                    "source_snapshot": zurich_snapshot,
                    "morphology_source_for_the_samaveda": "NONE_EXISTS",
                    "algorithm_version": ALGORITHM_VERSION,
                    "config_hash": config_hash,
                    "code_commit": head,
                }
            )
            continue
        row = base_row(
            key,
            "CROSS_VEDA_TEXT_IDENTITY",
            "VEDAWEB",
            zurich_snapshot,
            f"rigveda_lexical_v1/tokens.jsonl, passage_key={entry['rv_key']} "
            f"(letter-identical to {key})",
            "EXACT",
            "the two verses' de-accented, de-spaced letter skeletons are equal as "
            "strings; the transfer rests on string equality, not on similarity",
        )
        # The inner assertions arrive carrying the Rigvedic derivation they were produced
        # with. Left alone, a Samavedic assertion would read derivation=MORPHOLOGY_RULE_CASE
        # and imply a Samavedic morphological annotation, which does not exist. Retyped,
        # with the underlying derivation and the analysed passage both kept on the record.
        projected = []
        for assertion in entry["assertions"]:
            retyped = dict(assertion)
            retyped["underlying_derivation"] = assertion["derivation"]
            retyped["derivation"] = "CROSS_VEDA_TEXT_IDENTITY"
            retyped["analysed_passage"] = entry["rv_key"]
            retyped["cautions"] = list(assertion.get("cautions") or []) + [
                "ANALYSIS_IS_OF_A_LETTER_IDENTICAL_RIGVEDIC_VERSE_NOT_OF_A_SAMAVEDIC_ANNOTATION"
            ]
            projected.append(retyped)
        row["payload"] = {
            "derivation": "CROSS_VEDA_TEXT_IDENTITY",
            "assertion_count": len(projected),
            "assertions": projected,
            "projected_from": entry["rv_key"],
            "projection_relationship_in_graph": entry["relationship"],
            "projection_graph_score": entry["graph_score"],
            "independently_annotated": False,
            "role_scope": "METRICAL_PADA_OF_THE_RIGVEDIC_SOURCE",
            "gana_scope_note": (
                "This concerns the Ārcika text only. The sung sāman, its stobhas and its "
                "melodic text are a different object and this row says nothing about them."
            ),
            "dependency_parse_available": False,
        }
        rows.append(row)

    os.makedirs(out_dir, exist_ok=True)
    _write_jsonl(os.path.join(out_dir, "rows.jsonl"), rows)
    _write_jsonl(os.path.join(out_dir, "rejected.jsonl"), rejected)
    _write_jsonl(os.path.join(out_dir, "sources.jsonl"), sources_records(dcs_snapshot, zurich_snapshot, fetch))

    counted = collections.Counter(r["state"] for r in rejected)
    manifest = {
        "domain": DOMAIN,
        "agent": AGENT,
        "schema_version": SCHEMA_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "created_at": now,
        "code_commit": head,
        "config_hash": config_hash,
        "config": config,
        "source_snapshot_ids": ["DCS_CONLLU_2026_09", "VEDAWEB_ZURICH_RIGVEDA_LEXICAL_V1"],
        "source_snapshot": {"DCS": dcs_snapshot, "VEDAWEB": zurich_snapshot},
        "files": [],
        "counts": {
            "candidates_considered": sum(population.values()),
            "accepted": len(rows),
            "rejected": counted["REJECTED"],
            "verified_zero": counted["REJECTED"],
            "not_applicable": 0,
            "unresolved": counted["UNRESOLVED"],
        },
        "counts_note": (
            "candidates_considered is every mantra in the graph, 20,210, because section "
            "32 requires the assessed set rather than the positives. verified_zero repeats "
            "the rejected figure deliberately: every rejected row is a measured zero over "
            "an examined mantra with a named reason, not a mantra that was skipped. "
            "unresolved counts only mantras a source does cover and whose address could "
            "not be established."
        ),
        "population": population,
        "processed_count": sum(population.values()),
        "positive_count": len(rows),
        "census": census,
        "per_veda": per_veda_block(population, reachable, positives, tokens_processed, rv_stats, av, yv, sv, rows, rejected),
        "closes_gaps": [
            "GAP-SEMANTICS-001",
            "GAP-SEMANTICS-003",
            "GAP-MORPHOLOGY-002",
        ],
        "gap_closure_notes": {
            "GAP-SEMANTICS-001": (
                "HAS_SEMANTIC_ASSERTION would reach all four corpora and Rigvedic coverage "
                "would rise from 2,542 to 10,150 of 10,552. The two existing derivations "
                "and the three new ones stay separately typed; nothing here may be summed "
                "with the 2,459 TIER_D model-extraction assertions."
            ),
            "GAP-SEMANTICS-003": (
                "Assertions carrying agent, predicate and patient together go from 0 to a "
                "measured non-zero. The :Devata-only endpoint range is NOT closed by this "
                "artifact and cannot be: see the additive schema proposal in the report."
            ),
            "GAP-MORPHOLOGY-002": (
                "Partially. A morphological layer reaches AV and YV for the first time, "
                "typed distinctly from the Rigveda's manual annotation. It does not reach "
                "the Samaveda, and the negative is evidenced rather than deferred."
            ),
        },
        "qa": {
            "sampled": 1158,
            "sample_method": "both",
            "defects_found": 5,
            "sampled_note": (
                "44 assertions adjudicated by reading, plus 1,114 scored mechanically "
                "against the dependency parse in the Wave-3 adversarial preflight."
            ),
            "human_reviewed": 0,
            "adjudicator": "MODEL_ADJUDICATED",
            "adjudicator_model": "claude-opus-5",
            "adjudication_is_not_human_annotation": True,
            "note": (
                "51 assertions were drawn -- 31 adversarially across eight strata that each "
                "exercise a rule which could force a wrong answer, and 20 at random -- and "
                "44 were adjudicated against the verse text and the source sentence. This "
                "is a model reading its own output and is recorded as such; it is not a "
                "gold set and it is not a human review. The defect rate it produces, 4 in "
                "44, is a floor on the true rate, not an estimate of it."
            ),
            "defects": [
                {
                    "id": "QA-1",
                    "example": "AVŚ 14.2.22, upastṛ",
                    "found": "the ritual spreading of the hide came out as DESTROYS",
                    "cause": (
                        "DCS never writes a long vocalic r -- measured: 0 of 1,651 verb "
                        "lemmas -- so its stṛ is both Zurich's str̥- (DESTROYS, 8 tokens) "
                        "and str̥̄- (ESTABLISHES, the strewing of the barhis, 30 tokens)"
                    ),
                    "status": "CLOSED IN CODE",
                    "fix": (
                        "DCS lemmas now resolve over a length-neutral bucket; a bucket with "
                        "two mapped predicates resolves only when one holds 95% or more of "
                        "the key's Rigvedic tokens, and names the loser on the assertion"
                    ),
                },
                {
                    "id": "QA-2",
                    "example": "RV 8.48.10, 'ayaṁ yaḥ somo ny adhāyy asme'",
                    "found": "a passive verb's nominative was labelled AGENT, making the deposited Soma the depositor",
                    "cause": "the case rule read any agreeing nominative as the agent",
                    "status": "CLOSED IN CODE",
                    "fix": "under voice=PASS a nominative is PATIENT; 467 Rigvedic, 116 Atharvavedic and 9 Yajurvedic case-scoped fillers moved, plus 25 Atharvavedic and 3 Yajurvedic nsubj fillers under a parsed passive",
                },
                {
                    "id": "QA-3",
                    "example": "VSM 6.22, 'mā apaḥ mā oṣadhīḥ hiṃsīḥ'",
                    "found": "a prohibition came out as a requested SLAYS with the plants as PATIENT -- the opposite of the verse",
                    "cause": "the predicate vocabulary has no polarity field and only two frames",
                    "status": "MITIGATED, NOT CLOSED",
                    "fix": (
                        "every assertion in the scope of a negation or prohibition particle "
                        "now carries POLARITY_NOT_MODELLED_NEGATION_PARTICLE_IN_SCOPE with "
                        "the particle named. A polarity field is proposed in the report; it "
                        "is an ontology change and not this agent's to make."
                    ),
                },
                {
                    "id": "QA-4",
                    "example": "AVŚ 6.114.2, upaśak",
                    "found": "'we could not accomplish the sacrifice' came out as BLESSES",
                    "cause": (
                        "inherited: action_root_map.yaml maps √śak- to BLESSES on the "
                        "lexicalised desiderative 'helps, teaches', which is defensible for "
                        "the simplex and wrong for upa-śak 'be able to'"
                    ),
                    "status": "OPEN, INHERITED FROM THE ROOT MAP",
                    "fix": "none applied. Overriding a hand-adjudicated root map from a string operation would be worse than the defect.",
                },
                {
                    "id": "QA-5",
                    "example": "AVS 1.1.4 asmanam tanvam kridhi; AVS 1.4.4 amuh yah upa surye ... tah nah hinvantu",
                    "found": (
                        "the case-scoped rule attaches roles across a clause boundary. "
                        "Scored against the dependency parse on 1,114 sentences: 623 of "
                        "2,715 emitted fillers (23.0%) belong to another clause and 50 more "
                        "carry the wrong role, 24.8% wrong in total."
                    ),
                    "cause": (
                        "the deployed gate counts FINITE verbs, and the leakage comes from "
                        "non-finite clauses (acl, xcomp, advcl) and from subjects internal "
                        "to a nominal, none of which the gate can see"
                    ),
                    "status": "MEASURED, NOT FIXABLE WITHOUT A PARSE",
                    "fix": (
                        "none. It is a property of reading roles from case with no "
                        "dependency annotation, which is the situation for all of the "
                        "Rigveda and three quarters of the rest. The measured rate is "
                        "carried on every row instead. No count was restaged: predicates, "
                        "frames, assertions and abstentions do not depend on role scope, "
                        "and the agent-predicate-patient triple figure survives at 92.2%."
                    ),
                },
            ],
            "limitations_the_sample_exposed_that_are_not_defects": [
                "A dative of purpose is read as BENEFICIARY, because the registry defines BENEFICIARY as a dative. 'for lasting might' becomes a beneficiary.",
                "A first-person optative wish is filed ASSERTED, because the registry's two frames are ASSERTED and REQUESTED only.",
                "Pronoun referents are not resolved: 2,250 AGENT and 2,412 PATIENT fillers are pronouns, many of them deities addressed as 'thee'.",
                "Directional and causative nuance carried by a preverb or a secondary stem is lost, which action_root_map.yaml explicitly instructs ('record the particle as a qualifier; do not derive a new predicate').",
            ],
        },
        "evaluation": EVALUATION,
    }
    manifest["files"] = [
        {
            "path": name,
            "sha256": sha256_file(os.path.join(out_dir, name)),
            "rows": rowcount,
            "bytes": os.path.getsize(os.path.join(out_dir, name)),
        }
        for name, rowcount in (
            ("rows.jsonl", len(rows)),
            ("rejected.jsonl", len(rejected)),
            ("sources.jsonl", len(sources_records(dcs_snapshot, zurich_snapshot, fetch))),
        )
    ]
    with io.open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(manifest["counts"], indent=1))
    print(json.dumps(manifest["per_veda"], indent=1, ensure_ascii=False))


#: The compact per-row form. The prose lives on the manifest; a row separated from its
#: manifest must still know that nothing here was human-checked and that no precision
#: figure is claimed, which is what these four fields say.
ROW_EVALUATION = {
    "human_annotated": 0,
    "human_gold_available": False,
    "precision_claimed": None,
    "precision_claimed_note": "no human gold set for Vedic semantic roles exists in this "
    "repository; see manifest.evaluation for what was measured instead",
    # The Wave-3 adversarial preflight, carried on the row because a row separated from its
    # manifest must still know the measured error rate of the instrument that made it.
    "case_scoped_rule_measured_against_the_treebank": {
        "measured_on": "1,114 DCS sentences that carry a dependency parse, with the "
        "deployed single-finite-verb gate applied",
        "role_fillers_scored": 2715,
        "wrong_share": 0.2479,
        "wrong_share_note": "623 fillers attached across a clause boundary plus 50 given "
        "the wrong role. A property of reading roles from case with no parse.",
        "same_argument_duplicate_share": 0.2136,
        "same_argument_duplicate_note": "a modifier, determiner or conjunct inside an "
        "argument the verb does have, carrying the same role in 406 of 423 checkable "
        "cases. Inflates the filler count; does not change the role.",
        "agent_predicate_patient_triple_survival": 0.922,
        "triple_survival_note": "and the error is conservative: the parse finds 42 "
        "complete triples the case rule missed, against 17 it manufactured",
        "applies_to_derivations": ["MORPHOLOGY_RULE_CASE", "CROSS_VEDA_TEXT_IDENTITY"],
        "does_not_apply_to": "TREEBANK_DEPREL, which is the parse itself",
    },
}

EVALUATION = {
    "human_annotated": 0,
    "human_gold_available": False,
    "gold_set_note": (
        "There is no human gold set for Vedic semantic roles in this repository. "
        "rigveda_semantic_gold_v1.jsonl holds 120 rows, every one UNANNOTATED, and "
        "theonym_mention_gold_v1.jsonl is MODEL_ADJUDICATED by the same model family it "
        "would score. So no precision figure is claimed here, for any corpus."
    ),
    "what_is_measured_instead": [
        "Predicate resolution rate per corpus, with every abstention typed by cause.",
        "Alignment strength per addressed verse: the fraction of the treebank sentence's "
        "letters matched and the fraction of those falling inside one verse, both carried "
        "on the row.",
        "Refusal counts for each rule that could have forced a wrong answer: number "
        "disagreement on a nominative, a homonym fold, a particle-sensitive root, a "
        "conjugation-sensitive root, a sentence spanning a verse boundary.",
    ],
    "adversarial_preflight_before_wave_3": {
        "assumption_tested": (
            "A role read from morphological case standing beside a finite verb, scoped to "
            "one pada (Rigveda) or one sentence (unparsed DCS), is the role a dependency "
            "parse would assign. 28,370 of 30,274 assertions rest on it, which is why it "
            "was chosen over the Samavedic projection (372 assertions) or the "
            "dominant-sense rule (1,139)."
        ),
        "why_a_test_was_possible_at_all": (
            "This report said no agreement figure could be computed because no independent "
            "source exists. That is true of the SOURCE and false of the RULE: 2,823 DCS "
            "sentences carry a human-validated dependency parse, so the case rule can be "
            "run on exactly those and scored against it. The instrument has a ground truth "
            "even where the corpus does not, and not noticing that was the gap in the "
            "original evaluation design."
        ),
        "verdict": "FAILS AT FILLER LEVEL, HOLDS AT ASSERTION LEVEL",
        "filler_level": {
            "fillers_emitted": 2715,
            "exact_agreement_with_the_parse": 1318,
            "raw_precision": 0.4855,
            "cross_clause_leakage": 623,
            "role_disagreements": 50,
            "wrong_share": 0.2479,
            "same_argument_expansion": 580,
            "treebank_unassigned": 127,
            "other": 17,
            "reading": (
                "The raw 0.4855 is an average of unlike quantities and must not be quoted. "
                "Decomposed: 21.4% of emitted fillers are a second token inside one "
                "argument and carry the right role, 24.8% are wrong, and the remainder the "
                "parse assigns to no verb either."
            ),
        },
        "the_defect_the_single_finite_verb_gate_does_not_catch": (
            "Leakage comes from NON-finite clauses -- acl 75, xcomp:result 56, xcomp 34, "
            "advcl 42 -- and from subjects internal to a nominal, nsubj 106. The deployed "
            "gate counts finite verbs, so it sees none of them. Two measured examples: "
            "asmanam tanvam kridhi gives the predicative complement as a second PATIENT, "
            "and amuh yah upa surye ... tah nah hinvantu gives the subject of a relative "
            "clause as the AGENT of the main verb."
        ),
        "assertion_level": {
            "unchanged_by_scope": (
                "passages processed, assertions, predicates, frames and every abstention "
                "count. All derive from the verb's own morphology, not from role scope."
            ),
            "triples_case_rule_calls_complete": 218,
            "triples_the_parse_also_calls_complete": 201,
            "survival_rate": 0.922,
            "triples_the_case_rule_missed": 42,
            "triples_the_case_rule_manufactured": 17,
            "reading": (
                "Completeness needs an AGENT and a PATIENT anywhere in the role set, and "
                "leakage adds fillers to a set that usually already held both. So the "
                "0 to 5,219 three-slot figure survives at 92.2%, and the rule "
                "under-reports completeness rather than over-reporting it."
            ),
        },
        "headline_cost_figure_survives": {
            "deity_share_among_parse_confirmed_fillers": 0.0774,
            "deity_share_among_parse_rejected_fillers": 0.0372,
            "reading": (
                "Leakage is LESS deity-heavy than confirmed attachment, so discarding it "
                "would raise the deity share from 8.08% to at most about 8.6%. The "
                "Devata-only-leaves-91.9%-unrepresentable conclusion stands, and if "
                "anything it understates the case."
            ),
        },
        "what_was_not_changed_and_why": (
            "No row was restaged and no count renumbered. The leakage cannot be fixed "
            "without a parse, which is the finding rather than a bug to patch: all of the "
            "Rigveda and three quarters of the non-Rigvedic material have none. The "
            "measured rate is attached to every row's evaluation block instead so it "
            "travels with the data, and each filler already carries its own case, surface "
            "and evidence string for a consumer that wants to re-judge it."
        ),
        "what_the_lead_should_do_with_it": (
            "Treat a case-scoped role filler as a candidate and a TREEBANK_DEPREL filler as "
            "a reading. A product surface that counts role fillers should report the two "
            "derivations separately, or apply the 0.2479 discount and say so. Counting "
            "agent-predicate-patient triples is safe at 92.2%."
        ),
    },
    "why_no_cross_source_agreement_figure": (
        "UD_Sanskrit-Vedic looked like an independent second witness and is not. Measured "
        "here: 2,160 of 9,105 DCS Atharvavedic sentences and 619 of 2,516 Vājasaneyi "
        "sentences carry a dependency parse, against UD's own 2,175 AVŚ and 622 VSM "
        "sentences. UD is the treebanked slice of DCS re-released, not a second opinion, "
        "so agreement between them would measure nothing."
    ),
}


def _negative_reason(veda, key, reachability, bundle):
    if reachability == "NONE":
        if veda == "AV":
            detail = (
                "DCS's Atharvaveda (Śaunaka) corpus holds kāṇḍas 1-18 complete plus 3 of "
                "the 72 hymns of kāṇḍa 19, and no kāṇḍa 20 at all. This verse is outside "
                "that. Measured from the corpus's own file list, not assumed."
            )
        else:
            detail = (
                "DCS's Vājasaneyisaṃhitā (Mādhyandina) corpus holds adhyāyas 1-15 of 40. "
                "This verse is in adhyāya 16 or later. Measured from the file list."
            )
        return "REJECTED", "SOURCE_COVERAGE_ENDS_BEFORE_THIS_VERSE", detail
    if reachability == "DCS_HYMN_REFUSED":
        return (
            "UNRESOLVED",
            "HYMN_REFUSED_BELOW_SKELETON_MATCH_FLOOR",
            "the source covers this hymn, but its sentence sequence did not match this "
            "hymn's verse sequence well enough to place any sentence safely, so no verse "
            "inside it was addressed. Resolvable by hand; not resolved here.",
        )
    return (
        "REJECTED",
        "NO_MAPPED_FINITE_VERB_IN_THE_ADDRESSED_SENTENCES",
        "sentences from the source were addressed to this verse and none of them holds a "
        "finite verbal root that the bounded predicate vocabulary maps. An honest "
        "abstention over examined text.",
    )


def per_veda_block(population, reachable, positives, tokens, rv_stats, av, yv, sv, rows, rejected):
    by_veda_rows = collections.Counter(r["veda"] for r in rows)
    predicates = collections.Counter()
    role_counts = collections.Counter()
    proposed = collections.Counter()
    assertion_counts = collections.Counter()
    derivations = collections.Counter()
    triples = collections.Counter()
    filler_types = collections.Counter()
    nondeity = collections.Counter()
    for row in rows:
        veda = row["veda"]
        for assertion in row["payload"]["assertions"]:
            assertion_counts[veda] += 1
            derivations[(veda, assertion["derivation"])] += 1
            predicates[(veda, assertion["predicate"])] += 1
            roles = {f["role"] for f in assertion["roles"]}
            if {"AGENT", "PATIENT"} <= roles:
                triples[veda] += 1
            for filler in assertion["roles"]:
                role_counts[(veda, filler["role"])] += 1
                filler_types[(veda, filler["filler_type"])] += 1
                if filler["proposed_role"]:
                    proposed[(veda, filler["role"])] += 1
                if filler["filler_type"] != "DEITY":
                    nondeity[veda] += 1
    rej = collections.Counter((r["veda"], r["reason"]) for r in rejected)
    out = {}
    for veda in ("RV", "SV", "YV", "AV"):
        out[veda] = {
            "population": population[veda],
            "source_reachable": reachable.get(veda, 0),
            "passages_processed": population[veda],
            "tokens_processed": tokens[veda],
            "passages_with_at_least_one_assertion": by_veda_rows[veda],
            "assertions": assertion_counts[veda],
            "distinct_predicates": sum(1 for (v, _) in predicates if v == veda),
            "assertions_with_agent_predicate_and_patient": triples[veda],
            "role_fillers": {r: c for (v, r), c in role_counts.items() if v == veda},
            "proposed_role_fillers": {r: c for (v, r), c in proposed.items() if v == veda},
            "role_fillers_that_are_not_a_deity": nondeity[veda],
            "derivations": {d: c for (v, d), c in derivations.items() if v == veda},
            "abstentions": {r: c for (v, r), c in rej.items() if v == veda},
            "filler_types": {t: c for (v, t), c in filler_types.items() if v == veda},
        }
    return out


def sources_records(dcs_snapshot, zurich_snapshot, fetch):
    return [
        {
            "source_id": "DCS",
            "source_snapshot": dcs_snapshot,
            "title": "Digital Corpus of Sanskrit — CoNLL-U release",
            "publisher": "Oliver Hellwig",
            "url": "https://github.com/OliverHellwig/sanskrit/tree/master/dcs/data/conllu",
            "licence": "CC BY 4.0",
            "licence_evidence": "stated verbatim in dcs/data/conllu/readme.md",
            "quality_class": "SCHOLARLY_EDITION",
            "retrieved_at": "2026-09-15",
            "files_fetched": len([f for f in fetch if f.get("sha256")]),
            "snapshot_method": (
                "each blob fetched from raw.githubusercontent.com at ref master and "
                "SHA-256'd individually; source_snapshot is the SHA-256 of the sorted "
                "list of those digests, so the whole snapshot is one verifiable value"
            ),
            "coverage_as_measured_here": {
                "corpora_in_release": 271,
                "atharvaveda_saunaka_hymn_files": 519,
                "atharvaveda_saunaka_hymns_per_kanda": {
                    "1": 35, "2": 36, "3": 31, "4": 40, "5": 31, "6": 142, "7": 118,
                    "8": 10, "9": 10, "10": 10, "11": 10, "12": 5, "13": 4, "14": 2,
                    "15": 18, "16": 9, "17": 1, "18": 4, "19": 3, "20": 0,
                },
                "vajasaneyi_madhyandina_adhyaya_files": 15,
                "samaveda_samhita_present": False,
                "enumeration_method": (
                    "git trees API on the dcs subtree, recursive, truncated=false, 23,576 "
                    "entries. The contents API caps at 1,000 and the Atharvavedic "
                    "directory holds 1,038 blobs, so the contents API would have hidden "
                    "kāṇḍas 16 to 19."
                ),
            },
        },
        {
            "source_id": "VEDAWEB",
            "source_snapshot": zurich_snapshot,
            "title": (
                "University of Zurich morphosyntactic annotation of the Rigveda, via "
                "VedaWeb TEI (already held at data/knowledge/rigveda_lexical_v1)"
            ),
            "publisher": "Cologne Center for eHumanities / University of Zurich",
            "url": "https://vedaweb.uni-koeln.de/rigveda",
            "licence": "see data/registry/rights.yaml for the held snapshot",
            "quality_class": "SCHOLARLY_EDITION",
            "retrieved_at": "already in repository; not re-fetched",
            "coverage_as_measured_here": {
                "passages": 10552,
                "tokens": 164758,
                "finite_verb_tokens": 23622,
                "root_tokens": 32029,
                "dependency_parse_present": False,
            },
        },
        {
            "source_id": "UD_SANSKRIT_VEDIC",
            "source_snapshot": "UD_Sanskrit-Vedic:train+dev+test, 27,182 sentences",
            "title": "UD_Sanskrit-Vedic treebank",
            "publisher": "Hellwig, Scarlata, Ackermann, Widmer",
            "url": "https://github.com/UniversalDependencies/UD_Sanskrit-Vedic",
            "licence": "CC BY-SA 4.0",
            "quality_class": "SCHOLARLY_EDITION",
            "retrieved_at": "2026-09-15",
            "used_for_extraction": False,
            "why_not_used": (
                "enumerated and then set aside as non-additive. It holds 57 texts, 27,182 "
                "sentences and 206,440 tokens, of which AVŚ 2,175 sentences and VSM 622 — "
                "which are the same sentences as the 2,160 Atharvavedic and 619 "
                "Vājasaneyi DCS sentences that carry a dependency parse. It is the "
                "treebanked slice of DCS re-released under a different licence, so using "
                "it would add no coverage and agreement between them would measure "
                "nothing. It contains no Sāmaveda Saṃhitā: the only Sāmavedic text is "
                "SVidhB, the Sāmavidhāna Brāhmaṇa, 202 sentences."
            ),
        },
        {
            "source_id": "VEDAWEB_RESOURCE_INDEX",
            "source_snapshot": "vedaweb.uni-koeln.de/api/texts + /api/resources, 2026-09-15",
            "title": "VedaWeb 2.0 text and resource index",
            "publisher": "Cologne Center for eHumanities",
            "url": "https://vedaweb.uni-koeln.de/api/texts",
            "licence": "index metadata; per-resource licences vary",
            "quality_class": "SCHOLARLY_EDITION",
            "retrieved_at": "2026-09-15",
            "used_for_extraction": False,
            "why_not_used": (
                "probed to establish two negatives and one positive by measurement rather "
                "than by inheritance. Negative one: 7 texts, none of them the Sāmaveda. "
                "Negative two: the avs (Śaunaka) text carries no textAnnotation resource "
                "at all, while avp (Paippalāda) does — so the most inviting annotated "
                "Atharvaveda on VedaWeb is the wrong śākhā, and it was not used. "
                "Incidental positive: the rv text carries a plainText resource 'Lubotsky "
                "Padapatha (1997)', which is the padapatha GAP-MORPHOLOGY-003 says our "
                "scope statement claims and the graph does not hold."
            ),
        },
    ]


def _write_jsonl(path, records):
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
