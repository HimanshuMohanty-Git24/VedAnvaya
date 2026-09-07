"""Regenerate engineering audit reports from sealed candidates; never extracts semantics."""

# Markdown report templates intentionally preserve readable rendered lines.
# ruff: noqa: E501

from __future__ import annotations

import json
import platform
import re
from collections import Counter
from pathlib import Path
from typing import Any

from vedagraph.semantic.full_run import Freeze, digest, file_hash, make_plan
from vedagraph.semantic.readiness import GapAudit, ParallelAudit, ReviewAudit

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508")
REPORTS = Path("docs/reports")
MANIFESTS = Path("docs/manifests")
RUN_ID = "vedagraph-rigveda-semantic-luna-v3-full-1.0.0-rc1"
NOTICE = (
    "Engineering diagnostics, not Vedic expertise, HUMAN_GOLD, or canonical truth. "
    "All existing output stays CANDIDATE / NEEDS_REVIEW; unlocked_predicates = []. "
    "No extraction was performed in this audit."
)
BLOCKERS = {
    "B01": "Repeated predicate-target binding failure: verse-wide cue matching creates unsupported "
    "requests and invokes/praises the wrong mentioned entity (10.58.1, 10.170.1, 8.35.7-9, "
    "8.36.4-6). "
    "Correct the extraction execution path, preserve old artifacts, and verify these regressions "
    "before scaling. No semantic-schema expansion is needed.",
    "B02": "Evidence anchoring and validation are incomplete: gap spans match inside unrelated "
    "words; legacy validation does not validate gap anchors, other_evidence_ids or nested entity "
    "IDs. The new offline import guard closes ID-membership holes, but the frozen producer still "
    "creates misleading spans. Correct producer anchoring and version the execution contract.",
    "B03": "Provenance/readiness evidence mismatch: run_semantic_luna_v3_508.py calls the regex "
    "extract_packet implementation directly; model labels are constants and no independent model "
    "response receipt is consumed. Stable replay proves deterministic reproduction, not "
    "independent "
    "Luna replication. Establish an auditable actual Luna execution path and a bounded "
    "verification "
    "under its new execution version before authorizing the full model run. Do not relabel old "
    "data.",
}

# One authored observation for every gap, in sealed extraction order. No model repair.
GAP_NOTES = [
    "Oblation giver is a donor role, separate from the addressed Wood deity.",
    "All men is a human collective distinct from Savitar; the stored span instead hits manifested.",
    "Men and women are explicitly contrasted with livestock; one group occurrence need not "
    "identify persons.",
    "The pious man is the beneficiary, distinct from the mentioned Indra.",
    "Most bounteous Giver qualifies the addressed Lord, not an evidenced human patron.",
    "Mortal man is the beneficiary guarded by Indra, not Indra himself.",
    "Any man who hates us is an indefinite adversary; do not invent an identity.",
    "Men with hero children is a human group; wealthy chief is a separate donor context.",
    "Priest of men includes a human collective distinct from the invoked Priest.",
    "Not slaying men still mentions humans; negation must remain attached to any proposed event.",
    "The men pressed juice identifies human ritual participants, distinct from Soma and the "
    "addressees.",
    "That man, mightiest in heaven may be a figurative or divine referent; human typing is unsafe.",
    "Sisters and kindred Rivers relate to Three Goddesses; the human kinship gap code is "
    "misapplied.",
    "The man who worships is the beneficiary of help, distinct from Agni.",
    "This diligent man invokes the addressees; the worshipper is not the canonical Maruts or "
    "Earth.",
    "Mortal men explicitly contrast with immortal Agni.",
    "Wise man and man's advantage supply a human referent without establishing a named person.",
    "A mortal/man calls Agni; human actor and invoked deity remain separate.",
    "Liberal patron's rite supports a donor role; Free-givers elsewhere does not identify that "
    "patron.",
    "Like car-borne men is a comparison applied to Maruts; retain opaque comparison, not literal "
    "humans.",
    "Lowly man is the one helped by the addressed Friend; identity unresolved but human type "
    "supportable.",
    "Men whose worship is rejected are distinct from Indra.",
    "Our men are human beneficiaries; the canonical Pusan is not their identity.",
    "Men seize Agni and he shines for man; human collective contrasts with Agni.",
    "Men must seek the Lord of the house; humans and Agni are distinct.",
    "Active man gains spoil; the later named Indra is not that man's registry identity.",
    "Men wash and dress Soma; physical milk and human operators are separate occurrences.",
    "Other men than we identifies people without canonical identities.",
    "Cattle restored to men distinguishes human beneficiaries from livestock.",
    "Men with prepared grass invoke the unnamed addressee; no deity identity for the human group.",
    "Wealthy man and scorners are human referents; Father is a separate comparison.",
    "Lord of men refers to a human collective governed by Agni.",
    "King of men similarly distinguishes human collective from Agni.",
    "World of men denotes a human collective; do not mint a world/person canonical entity.",
    "Giver refers to the addressed Hurler of the Bolt; no human patron is evidenced by that "
    "epithet.",
    "Godless man and named recipients are human; names alone are not supplied canonical IDs.",
    "A man yet more devout is a recipient in gift context; do not resolve Nahup from memory.",
    "Wealth renowned with men supports human audience; stored span hits many instead.",
    "Works for man supports human beneficiary distinct from Surya and the Hero.",
    "Men have strengthened Pavamana supplies human worshippers; stored span hits Pavamana.",
    "Singing-men are human recipients of treasure, distinct from Pavamana.",
    "Food to man supplies human beneficiary; rain/heaven are separate referents.",
    "The man who worships Indu is human; no new Indu identity may be invented.",
    "Wealth-giver addresses Indu; a human patron cannot be inferred from giver.",
    "Sapient men prepare the flow; Indu remains distinct from human operators.",
    "Men seen by Soma are distinct from the addressed Soma/Pavamana.",
    "Free-giver continues the supplied Soma referent; an existing SOMAH mention is available, not "
    "a new patron.",
    "Prompt Giver continues the addressed Soma; supplied SOMAH exists, while Indra is the "
    "companion.",
    "Men generate/stablish Agni; human actors are not the AGNIH or MITRAH mention.",
    "Yama gathers men; Vivasvan's Son identifies the King, not requested offspring or the human "
    "group.",
    "Woman, wife and husband are evidenced humans; the stored man substring inside woman is not a "
    "full referent span.",
    "Furtherer of men distinguishes human beneficiaries from the described agent.",
    "Let men joy names a human group; stored men inside mental is a misleading span.",
    "The man eaten in this riddle is not safely resolvable as literal human; retain philological "
    "uncertainty.",
    "The man protected by the Asvins is a human beneficiary; no supplied named person identity.",
    "Many a man invokes the Car; Dawn metadata/mention does not make Dawn the invoked target.",
    "Question who are the men explicitly concerns humans; no named identity is established.",
    "Men abstain from pouring; preserve negation rather than infer actual offering from the action "
    "word.",
    "Men who injure law are distinct from Indra, Varuna and Mitra.",
    "This man may be whole again identifies a human beneficiary of herbs.",
    "Devapi Arstisena is called mortal man, but no person entity key is supplied in packet "
    "mentions.",
    "Woman and Mudgalani support a human occurrence; do not equate a name with a canonical key.",
    "Bounteous giver, maid and his home support a human donor role without a global patron "
    "registry.",
    "Men among whom Agni shines are human collective, distinct from Agni.",
    "Living men are governed by the named gods; stored man inside Aryaman is wrong anchoring.",
    "Man eats fruit contrasts with Goddess; do not type Aranyani as this person.",
    "Man who gives and liberal worshippers support humans with optional donor role.",
    "Gods and men explicitly distinguish humans from deities in sacrificial context.",
    "In person is an idiom about the Bright God, not an additional human referent.",
    "Youthful woman and her offspring support human occurrence; no canonical person registry is "
    "implied.",
]
GAP_EXCEPTIONS = {
    5: "EXTRACTION_OVERREACH",
    12: "EXPERT_PHILOLOGY_REQUIRED",
    13: "WRONG_GAP_CODE",
    20: "INTENTIONAL_OPAQUE_CASE",
    35: "EXTRACTION_OVERREACH",
    44: "EXTRACTION_OVERREACH",
    47: "CANONICAL_ENTITY_RESOLUTION_MISSED",
    48: "CANONICAL_ENTITY_RESOLUTION_MISSED",
    54: "EXPERT_PHILOLOGY_REQUIRED",
    69: "EXTRACTION_OVERREACH",
}

# Queue order is frozen by the 508 report. Entries reflect evidence inspection, not score mapping.
REVIEW_NOTES = [
    (
        "PREDICATE_BOUNDARY",
        "B01 B02",
        "May the God drink does not request offspring; guards our offspring is descriptive. In "
        "person is not human.",
    ),
    (
        "ONTOLOGY_GAP",
        "B02",
        "Human worshippers are evidenced, but gap span points into Pavamana; no-claim itself may "
        "remain cautious.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "Come nigh addresses Mitra and Varuna, while extractor invokes the Soma to be drunk; milk "
        "verbs also become substance.",
    ),
    (
        "ONTOLOGY_GAP",
        "B02",
        "Human collective is valid, but gap span points inside Pavamana; wealth and strength "
        "requests are directly phrased.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "O Asvins is the address; Soma sought for drinking and accompanying Surya become INVOKES "
        "targets.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "Same Asvin address is misbound to Soma/Surya; added oblation supports an independent "
        "offering difference.",
    ),
    (
        "PREDICATE_BOUNDARY",
        "",
        "Commands to slay and drive away disease raise request/event boundary; retained event is "
        "review-sensitive.",
    ),
    (
        "PREDICATE_BOUNDARY",
        "",
        "Give strength is a real wording addition; shared commands need event/request review, not "
        "enforced equality.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "O Satakratu, drink Soma addresses the drinker; INVOKES SOMAH confuses drink with "
        "addressee.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "Glorify the Atris' hymn and drink Soma does not praise/invoke Soma; verse-wide cue scope "
        "fails.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Human operators, milk and waters are explicit; ritual/substance detail is reviewable.",
    ),
    (
        "ONTOLOGY_GAP",
        "B02",
        "Singing-men are human recipients but span points inside Pavamana; send action is directly "
        "supported.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "O Indra receives address; Soma is thine own drink, not a second invoked target; "
        "Free-giver is not human patron.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "Indra is a companion, not necessarily praised; Giver is addressed Soma, not an unmodeled "
        "human patron.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Human patient is explicit; rich in Soma substance identity may need domain review without "
        "structural leakage.",
    ),
    (
        "ONTOLOGY_GAP",
        "B02",
        "Donor/men are clear, but span man comes from many; no-claim does not justify "
        "canonicalizing a chief.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Priest of men includes humans; unnamed divine identity and archaic address can remain "
        "unclaimed.",
    ),
    (
        "PHILOLOGY_REQUIRED",
        "",
        "Elliptical grammar and wise-man addressee need reading; no structural failure in "
        "withholding assertions.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Active man is human; Much-invoked is descriptive epithet, not necessarily a fresh "
        "invocation.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Human invokers are clear; unnamed Best slayer identity remains unresolved.",
    ),
    (
        "TRANSLATION_AMBIGUITY",
        "",
        "Wealthy man, scorners and Father simile leave target scope open; no invented identity.",
    ),
    (
        "PHILOLOGY_REQUIRED",
        "",
        "Glorious one, Nahup and more devout man need referent resolution; retain opaque "
        "uncertainty.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Worshipping human is explicit; Flow and heroic strength are not automatically a strength "
        "request.",
    ),
    (
        "ONTOLOGY_GAP",
        "B02",
        "Woman and husband are clear, but stored span is only man inside woman; funeral "
        "interpretation is not needed for this diagnostic.",
    ),
    (
        "PHILOLOGY_REQUIRED",
        "",
        "Riddle participant and pronouns are obscure; withholding a canonical interpretation is "
        "appropriate.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Man is beneficiary; corrupted come u on translation deserves source review, not invented "
        "correction.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Human donor is supported; lake/palaces are similes and need no forced place assertions.",
    ),
    (
        "EXPECTED_MODEL_UNCERTAINTY",
        "",
        "No-claim omits slayest wording; isolated omission remains review, and cannot validate "
        "checklist completeness.",
    ),
    (
        "OBJECT_GRANULARITY",
        "",
        "Extra sentence Waters hold all medicines explains medicine detail; Soma speaker versus "
        "substance remains review-sensitive.",
    ),
    (
        "PREDICATE_BOUNDARY",
        "",
        "Thunder-armed epithet becomes storm; distinguish figurative description from actual "
        "phenomenon without ontology rewrite.",
    ),
    (
        "TYPE_BOUNDARY_RISK",
        "",
        "Sacrifice may denote act rather than offered object; permitted OFFERING_REF shape alone "
        "does not settle semantic role.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "O Asvins address again produces Soma and Surya invocations: repeated target-scope "
        "failure.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "Satakratu is addressed; Soma is drunk, not invoked. Same failure as neighboring verses.",
    ),
    (
        "OBJECT_GRANULARITY",
        "",
        "Soma juice normalized as meath is a granularity/translation diagnostic; recipient list "
        "differs from next pair member.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Food for man, rain and heaven are supplied; send normalizes bringing and is reviewable.",
    ),
    (
        "PREDICATE_BOUNDARY",
        "",
        "Water-winner epithet drives water/phenomenon claims; preserve candidate review for "
        "figurative scope.",
    ),
    (
        "OBJECT_GRANULARITY",
        "",
        "Shorter Waters passage lacks explicit medicines sentence; broad comparison is partial for "
        "explainable reason.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "The invoked/described Car is not the lexical Dawn entity; verse-wide descriptive cue "
        "attaches DESCRIBES to Dawn.",
    ),
    (
        "TYPE_BOUNDARY_RISK",
        "",
        "Gods and men who sacrifice states an act, not automatically a thing offered; keep role "
        "boundary review.",
    ),
    (
        "SAFE_REVIEW_ONLY",
        "",
        "Four quarters differs from Yama's Son; its no-claim does not share the false offspring "
        "assertion.",
    ),
    (
        "SAFE_REVIEW_ONLY",
        "",
        "Sea wording differs from waters/plants; absence of an ontology head is not evidence "
        "fabrication.",
    ),
    (
        "SAFE_REVIEW_ONLY",
        "",
        "Beams of light differ from waters/plants; withheld claim is not itself a systemic error.",
    ),
    (
        "SAFE_REVIEW_ONLY",
        "",
        "Mountain heights differ from waters/plants; local no-claim does not justify global "
        "semantic equality.",
    ),
    ("SAFE_REVIEW_ONLY", "", "Distant realms remain vague; opaque spatial handling is acceptable."),
    (
        "TRANSLATION_AMBIGUITY",
        "",
        "Sarya/Surya and Come/Conie source variants explain lexical sensitivity; no silent text "
        "repair.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "O Asvins still receives the address; Surya becomes INVOKES because its name and O "
        "co-occur.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Giver of the oblation is a donor role; existing gap is safer than forced identity.",
    ),
    (
        "ONTOLOGY_GAP",
        "B02",
        "All men is supported but span hits manifested; ID-valid evidence is not enough.",
    ),
    (
        "ONTOLOGY_GAP",
        "",
        "Human and livestock beneficiaries explicitly receive health; person typing can be "
        "deferred safely.",
    ),
    (
        "CANONICAL_ENTITY_RISK",
        "B01",
        "Vamra when glorified drives PRAISES Indra elsewhere in the verse; laudatory target is "
        "misbound.",
    ),
]


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def report(name: str, text: str) -> None:
    (REPORTS / name).write_text(text.rstrip() + "\n", encoding="utf-8")


def table(headers: list[str], values: list[list[object]]) -> str:
    def line(values: list[object]) -> str:
        return "| " + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in values) + " |"

    return "\n".join([line(headers), line(["---"] * len(headers)), *[line(v) for v in values]])


def main() -> None:
    stats = read(ROOT / "v3_508_statistics.json")
    packets = {
        p["passage_key"]: p
        for f in sorted((ROOT / "batches").glob("*/evidence.jsonl"))
        for p in rows(f)
    }
    payloads = {p["mantra_id"]: p for p in rows(ROOT / "v3_extractions.jsonl")}
    gaps = [g for p in payloads.values() for g in p["ontology_gaps"]]
    assert len(gaps) == len(GAP_NOTES) == 70
    audited_gaps = []
    gap_table = []
    anchor_defects = []
    for index, (gap, note) in enumerate(zip(gaps, GAP_NOTES, strict=True), 1):
        packet = packets[gap["source_passage_id"]]
        text = packet["translation"]["text"]
        span = gap["evidence"][0]["translation_span"]
        start, end = span["start"], span["end"]
        partial = (start > 0 and text[start - 1].isalnum()) or (
            end < len(text) and text[end].isalnum()
        )
        blockers = ["B02"] if partial else []
        classification = GAP_EXCEPTIONS.get(index, "TRUE_SCHEMA_GAP")
        if index in {5, 13, 35, 44, 47, 48, 69}:
            blockers.append("B01")
        person = (
            "USEFUL"
            if classification == "TRUE_SCHEMA_GAP"
            else ("EXPERT_REQUIRED" if classification == "EXPERT_PHILOLOGY_REQUIRED" else "UNSAFE")
        )
        audit = GapAudit(
            case_id=gap["candidate_id"],
            passage_ids=[packet["passage_key"]],
            classification=classification,
            person_ref=person,
            rationale=note,
            blocker_ids=blockers,
            decision="BLOCKS_FULL_RUN" if blockers else "DOES_NOT_BLOCK_FULL_RUN",
        )
        audited_gaps.append(audit.model_dump(mode="json"))
        if partial:
            anchor_defects.append(
                {
                    "case_id": gap["candidate_id"],
                    "passage_id": packet["passage_key"],
                    "span": span,
                    "matched": text[start:end],
                    "context": text[max(0, start - 16) : end + 16],
                }
            )
        gap_table.append(
            [
                index,
                packet["citation"],
                gap["candidate_id"],
                gap["ontology_gap_code"],
                classification,
                person,
                f"{start}:{end} {text[start:end]!r}",
                note,
                audit.decision,
                ", ".join(blockers),
            ]
        )

    selected_pairs = [
        c
        for c in stats["parallel"]["cases"]
        if c["category"] == "different semantic candidates"
        or (c["relation"] == "EXACT" and c["category"] == "partial overlap")
    ]
    metrics = {
        tuple(sorted((r["subject_key"], r["object_key"]))): r
        for r in rows(Path("data/knowledge/rigveda_lexical_v1/mantra_parallels.jsonl"))
    }
    parallel_audits = []
    parallel_table = []
    dossier_pairs = []
    for i, pair in enumerate(selected_pairs, 1):
        left, right = packets[pair["left"]], packets[pair["right"]]
        metric = metrics[tuple(sorted((pair["left"], pair["right"])))]
        bad = pair["left"].endswith("M10:S058:V001")
        if pair["relation"] == "EXACT":
            classification = "TRANSLATION_VARIANT_EFFECT"
            note = "Identical Sanskrit and lexical sequence; same rishi/devata/metre. 4.22.11 translates isam as wealth, others as power. Wealth is recognized as REQUESTS, power is absent from the regex outcome list. Neighbors differ but the implementation never reads them. Translation effect exposes coverage asymmetry; do not force equality or choose a Sanskrit gloss."
        elif bad:
            classification = "EXTRACTION_INCONSISTENCY"
            note = "10.58.1 emits REQUESTS offspring from Vivasvan's Son plus come in the shared return-of-spirit refrain. Son identifies Yama, not a requested child. Shared metadata and neighbors do not license that relation. The other destination wording does not request offspring either. Repeated whole-verse cue binding is an extraction bug."
        else:
            classification = "TEXT_VARIANT_JUSTIFIED_DIFFERENCE"
            note = "10.58.7 specifically names waters and plants (apah/osadhih); the other verse names a different destination. Water substance/phenomenon candidates reflect changed words. Shared return-of-spirit refrain does not require identical object sets. Missing other place/event candidates is separate recall uncertainty."
        audit = ParallelAudit(
            case_id=f"PAR-{i:02d}",
            passage_ids=[pair["left"], pair["right"]],
            classification=classification,
            rationale=note,
            blocker_ids=["B01"] if bad else [],
            decision="BLOCKS_FULL_RUN" if bad else "DOES_NOT_BLOCK_FULL_RUN",
        )
        parallel_audits.append(audit.model_dump(mode="json"))
        m = metric["metrics"]
        parallel_table.append(
            [
                audit.case_id,
                left["citation"],
                right["citation"],
                pair["relation"],
                m["token_jaccard"],
                m["ordered_token_similarity"],
                m["normalized_edit_similarity"],
                classification,
                note,
                audit.decision,
            ]
        )
        dossier_pairs.append(
            {
                "audit": audit.model_dump(mode="json"),
                "metrics": metric,
                "left_packet": left,
                "right_packet": right,
                "left_payload": payloads[left["citation"]],
                "right_payload": payloads[right["citation"]],
            }
        )

    assert len(stats["review_queue"]) == len(REVIEW_NOTES) == 50
    triage = []
    triage_table = []
    for index, (case, observation) in enumerate(
        zip(stats["review_queue"], REVIEW_NOTES, strict=True), 1
    ):
        category, blocker_text, note = observation
        tags = []
        if category != "ONTOLOGY_GAP" and "new ontology gap" in case["reasons"]:
            tags.append("ONTOLOGY_GAP")
        if blocker_text:
            tags.append("ARCHITECTURE_BUG")
        audit = ReviewAudit(
            case_id=f"REV-{index:02d}",
            passage_ids=[case["mantra_id"]],
            classification=category,
            secondary_tags=tags,
            rationale=note,
            blocker_ids=blocker_text.split(),
            decision="BLOCKS_FULL_RUN" if blocker_text else "DOES_NOT_BLOCK_FULL_RUN",
        )
        triage.append(audit.model_dump(mode="json"))
        triage_table.append(
            [
                audit.case_id,
                packets[case["mantra_id"]]["citation"],
                category,
                ", ".join(tags),
                audit.decision,
                blocker_text,
                note,
            ]
        )

    # Only enumerate IDs and hash files. Never build full-corpus packets or call extract_packet.
    corpus = Path("data/canonical/rigveda_full_v1")
    ids = sorted(
        p["canonical_key"]
        for p in rows(corpus / "passages.jsonl")
        if re.fullmatch(r"VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}", p["canonical_key"])
    )
    roles = {
        "corpus_manifest": str(corpus / "manifest.json"),
        "traditional_manifest": "data/knowledge/rigveda_deterministic_v1/manifest.json",
        "lexical_manifest": "data/knowledge/rigveda_lexical_v1/manifest.json",
        "morphology": "data/knowledge/rigveda_lexical_v1/tokens.jsonl",
        "prompt": "prompts/semantic_extraction_v3.md",
        "schema": "schemas/semantic_extraction_v3.schema.json",
        "object_ontology": "src/vedagraph/semantic/object_ontology.py",
        "semantic_ontology": "src/vedagraph/semantic/ontology.py",
        "explicitness_policy": "src/vedagraph/semantic/object_ontology.py",
        "normalization_policy": "src/vedagraph/semantic/normalization.py",
        "packet_schema": "schemas/semantic_evidence_packet.schema.json",
        "packet_builder": "src/vedagraph/semantic/packet.py",
        "packet_model": "src/vedagraph/models/semantic.py",
        "object_model": "src/vedagraph/models/normalization.py",
        "validator": "src/vedagraph/semantic/v3.py",
        "runtime_lock": "pyproject.toml",
        "operations": "src/vedagraph/semantic/full_run.py",
    }
    roles = {k: Path(v).as_posix() for k, v in roles.items()}
    files = {
        p.as_posix(): file_hash(p)
        for directory in [
            corpus,
            Path("data/knowledge/rigveda_deterministic_v1"),
            Path("data/knowledge/rigveda_lexical_v1"),
        ]
        for p in directory.glob("*.json*")
    }
    files.update({v: file_hash(Path(v)) for v in roles.values()})
    for directory in [Path("src/vedagraph/semantic"), Path("data/registries")]:
        for p in directory.rglob("*"):
            if p.is_file() and p.suffix in {".py", ".yaml"}:
                files[p.as_posix()] = file_hash(p)
    freeze = Freeze(
        run_id=RUN_ID,
        files=files,
        roles=roles,
        passage_ids=ids,
        runtime_version=f"Python {platform.python_version()}; Codex host build UNVERIFIED; BLOCKED draft",
    )
    freeze.verify(Path.cwd(), ids)
    plan = make_plan(RUN_ID, ids, digest(freeze.model_dump(mode="json")))
    write(MANIFESTS / "rigveda_semantic_full_run_freeze.draft.json", freeze.model_dump(mode="json"))
    write(
        MANIFESTS / "rigveda_semantic_full_run_batch_plan.draft.json", plan.model_dump(mode="json")
    )
    summary = {
        "ontology_decision": "KEEP_GAPS_FOR_FULL_RUN",
        "parallel_decision": "PARALLEL_EXTRACTION_BUG_FOUND",
        "final_state": "FULL_RIGVEDA_V3_CANDIDATE_RUN_BLOCKED",
        "blockers": BLOCKERS,
        "gap_counts": dict(Counter(a["classification"] for a in audited_gaps)),
        "anchor_defect_count": len(anchor_defects),
        "parallel_counts": dict(Counter(a["classification"] for a in parallel_audits)),
        "triage_counts": dict(Counter(a["classification"] for a in triage)),
        "triage_blocking": sum(bool(a["blocker_ids"]) for a in triage),
        "plan_hash": digest(plan.model_dump(mode="json")),
        "freeze_hash": plan.freeze_hash,
        "full_id_hash": digest(ids),
        "batch_count": len(plan.batches),
    }
    write(
        MANIFESTS / "rigveda_semantic_readiness_audit.json",
        {
            "summary": summary,
            "gaps": audited_gaps,
            "parallels": parallel_audits,
            "review_queue": triage,
            "anchor_defects": anchor_defects,
        },
    )
    # Evidence remains in ignored local data, not copied into tracked reports.
    write(
        Path("data/semantic/readiness-audit/evidence_dossier.json"),
        {
            "gaps": [
                {
                    "audit": a,
                    "packet": packets[a["passage_ids"][0]],
                    "payload": payloads[packets[a["passage_ids"][0]]["citation"]],
                }
                for a in audited_gaps
            ],
            "parallels": dossier_pairs,
            "review": [
                {
                    "audit": a,
                    "packet": packets[a["passage_ids"][0]],
                    "payload": payloads[packets[a["passage_ids"][0]]["citation"]],
                }
                for a in triage
            ],
            "expert_cases": stats["expert_cases"],
        },
    )

    report(
        "RIGVEDA_SEMANTIC_508_ONTOLOGY_AUDIT.md",
        f"""# V3 508 ontology audit

{NOTICE}

## Decision

`KEEP_GAPS_FOR_FULL_RUN`. No object ontology V2 is required. This is not full-run authorization.
The existing gap object safely preserves unresolved occurrences; bad gap emission/anchoring is
an extractor defect, not proof that a new type is needed. No result was repaired.

All 70 gap objects were inspected (61 person-like, 8 patron, 1 kinship), not sampled.
One gap can summarize several mentions; these are 70 objects, not a count of distinct humans.
Classifications: {json.dumps(summary["gap_counts"], sort_keys=True)}.
Substring anchor defects: **{len(anchor_defects)}**. Offsets are zero-based, end-exclusive.
A TRUE_SCHEMA_GAP can also have defective evidence anchoring; primary ontology classification
and engineering blocker are independent. These are engineering readings of supplied translation,
checked against packet mentions; not Sanskrit adjudications.

## Person-like conclusion and options

57 of 61 person-like records support a useful generic human occurrence on supplied English evidence;
2 require philological resolution, 1 is a simile kept opaque, and 1 is an idiom overreach.
Do not convert stored gaps automatically: evidence spans and literal-human status must first pass.
PERSON_REF would improve querying but is optional, not a canonical person registry. Preserve number,
indefiniteness, negation and comparison scope; never infer a human from a divine epithet or name alone.
Packet-provided canonical identity takes precedence only when the referent itself is resolved;
traditional rishi/devata assignment is not identity proof for an occurrence.

| Option | Benefit | Risk / decision |
| --- | --- | --- |
| Keep evidenced gaps | No extraction-schema migration, auditable uncertainty | Recommended now; repair execution bugs separately |
| PERSON_REF plus evidenced role qualifiers | Human occurrence without canonical person registry; patron/kinship/ancestor avoid kind proliferation | Optional later version; roles need evidence, kinship needs relata and must allow unknown relata |
| Separate PATRON/KINSHIP/ANCESTOR kinds | Explicit role indexing | Confuses role with ontological type; divine/nonhuman kinship does not imply PERSON_REF |
| Canonical person registry | Cross-occurrence identity | Out of scope; unsupported names must never create canonical identity |

Only 3 of 8 patron records support human donor typing. The 1 kinship record concerns goddesses/rivers,
so PERSON_REF + KINSHIP is unsafe there. No ancestor occurrence was observed; its future role design
is conceptual only. A role can relate deities or natural referents and need not imply a human.

## Complete occurrence ledger

{table(["#", "Mantra", "Object ID", "Original code", "Classification", "PERSON_REF", "Stored span", "Diagnostic", "Gate", "Blockers"], gap_table)}
""",
    )
    report(
        "RIGVEDA_SEMANTIC_508_PARALLEL_AUDIT.md",
        f"""# V3 508 parallel audit

{NOTICE}

`PARALLEL_EXTRACTION_BUG_FOUND`. The issue is relation-scope failure, not an instruction to
force textual parallels to share semantic outputs. All 11 near-different and 2 exact-partial
pairs were inspected, including both complete packets, translations, tokens/lemmas, mentions,
traditional metadata, immediate previous/next context, assertions and stored parallel metrics.
The local evidence dossier preserves those exact inputs for every pair.

The 38 original cases remain: exact same 4, exact partial 2, near same 11, near partial 10,
near different 11. The 11 near-different pairs all belong to hymn 10.58, so they are correlated
pair observations, not 11 independent model failures. Six include 10.58.1 and expose the same
false offspring request. Five compare 10.58.7 waters/plants with other destinations and have
text-justified differences. Missing claims in other verses are not forced into equality.

The exact pairs have identical Sanskrit, identical 19-token lexical sequences and matching
rishi/devata/metre. The supplied English switches power/wealth; only wealth is recognized by
the regex outcome inventory. This explains partial outputs but provides no evidence of model
stochasticity. Surrounding verses differ; the producer does not read those context fields.
The two exact cases are primary TRANSLATION_VARIANT_EFFECT, with extraction coverage asymmetry
as a secondary observation. A scholar need not settle the gloss before candidate creation.

{table(["Case", "Left", "Right", "Relation", "Token Jaccard", "Ordered tokens", "Edit similarity", "Primary class", "Diagnostic", "Gate"], parallel_table)}

Metrics are read from mantra_parallels.jsonl under rigveda-mantra-parallel-policy-v1. They measure
text overlap, not semantic equivalence. Pair IDs and complete metric records are retained locally.
""",
    )
    report(
        "RIGVEDA_SEMANTIC_508_REVIEW_TRIAGE.md",
        f"""# V3 508 review queue triage

{NOTICE}

All 50 cases were inspected. **{summary["triage_blocking"]}** exhibit a concrete systemic blocker;
**{50 - summary["triage_blocking"]}** do not block individually. Blocking labels point to existing
engineering failures, not expert approval requirements. A nonblocking label is not semantic acceptance.
No EVIDENCE_PACKET_BUG was established: bad spans are generated evidence anchors, not corrupted
packet IDs. Canonical ID membership is intact, but valid IDs can still be attached to the wrong relation.

Primary category counts: {json.dumps(summary["triage_counts"], sort_keys=True)}.

{table(["Case", "Mantra", "Primary category", "Secondary tags", "Gate", "Blockers", "Evidence-based diagnostic"], triage_table)}

## Existing 20 expert cases

The prior 20-case V3 queue was inspected alongside its 508 stability records. All remain unresolved
expert diagnostics; none is human gold. The two canonical-scope examples 9.87.9 and 10.89.8 must
also be tracked as engineering target-binding risks; 10.27.13 remains a riddle/philology issue.
The expert queue is not an exhaustive engineering risk inventory. No expert answer was invented.

{table(["Mantra", "In 508", "V3 stable", "Existing status"], [[v["mantra_id"], v["in_508_pilot"], v["v3_result_stable"], v["status"]] for v in stats["expert_cases"]])}
""",
    )
    projection = [
        [name, count, round(count * 10552 / 508)]
        for name, count in [
            ("Candidate assertions", 917),
            ("No-claim mantras", 143),
            ("Ontology-gap objects", 70),
            ("Canonical-reference assertion objects (not unique entities)", 256),
            ("Top-50 queue capacity analogue", 50),
        ]
    ]
    report(
        "RIGVEDA_SEMANTIC_FULL_RUN_OPERATIONS.md",
        f"""# Full Rigveda V3 operations — blocked draft

{NOTICE}

## ROUGH ENGINEERING PROJECTIONS

{table(["Measure", "Observed / 508", "Linear capacity analogue / 10,552"], projection)}

Multiplier 10,552/508 = {10552 / 508:.6f}. These are capacity scenarios, not statistical predictions.
The pilot is selected, includes correlated parallels and uses a deterministic heuristic producer;
an actual model run may differ substantially. No confidence interval or corpus semantic truth is claimed.
The top-50 queue is capped by construction, so about 1,039 is a review-capacity analogue, not a predicted
flag prevalence. Keep the complete uncapped risk ledger; deduplicate overlapping flags. A conservative
storage/workflow upper bound is 10,552 mantra-level review entries, with potentially multiple reasons.

## Review policy

1. Tier 1: validate every packet and payload, including gap anchors and all nested canonical IDs;
   reject schema/ID/evidence failures, duplicate IDs, canonical contradictions and structural type
   leakage. All rejected batches remain FAILED; final seal requires zero unresolved failures.
   Deterministic validation cannot establish semantic entailment.
2. Tier 2: retain all risk flags: gaps, opaque referents, exact/near disagreements, predicates with
   fewer than 10 full-run occurrences, heads occurring once, more than 6 assertions per mantra,
   four or more predicate families, and rare family combinations (fewer than 5 occurrences).
   Compute rarity after aggregation; do not bias extraction from previous semantic results.
   Deduplicate by mantra then reason, preserve every underlying assertion/pair ID, and stratify
   by mandala, predicate, object kind and gap code. Never silently drop overflow beyond top 50.
3. Tier 3: optional independent Sol/high review of at most 200 deterministic targeted cases plus
   50 hash-selected ordinary cases as an initial diagnostic budget. Never all 10,552. Sample by
   ascending SHA256(run_id + passage_id) within strata; persist IDs and selection-policy hash.
   Escalate repeated shared failure mechanisms, not isolated interpretive disagreements.
4. Tier 4: domain experts receive high-value unresolved identity/philology disputes only (initial
   budget 20). Review budgets are operational choices, not acceptance thresholds or a prerequisite
   for producing candidates. Gold requires actual human annotation, outside this audit.

## Freeze before any future extraction

Draft file: docs/manifests/rigveda_semantic_full_run_freeze.draft.json.
It pins corpus/traditional/lexical manifests AND their materialized JSON/JSONL files, morphology
tokens plus lexical manifest source snapshot hashes, prompt, schema, both ontologies, explicitness
policy (object ontology and prompt), normalization, EvidencePacket schema/model/builder, typed models,
semantic implementation and validation, operations code, project dependencies and exact full ID set.
The source snapshot hashes are the ten VEDAWEB snapshot IDs in the pinned lexical manifest.
Before launch, add the verified Codex build/model execution receipt format and exact installed
dependency lock; current draft explicitly records host build UNVERIFIED. Model alias behavior cannot
be cryptographically pinned: preserve returned model/build metadata and each raw response receipt.

Any changed frozen file, model, reasoning, runtime, source or passage-ID hash requires a NEW extraction
version/run ID and plan. Do not resume across drift; a draft is not an executable authorization.
Full ID set: 10,552 unique mantra IDs enumerated directly from canonical passages, not fabricated
range arithmetic. No full-corpus EvidencePackets were built and no candidates were extracted.

Freeze hash: `{summary["freeze_hash"]}`.
ID-list hash: `{summary["full_id_hash"]}`.
Plan hash: `{summary["plan_hash"]}`.

## Batch plan and checkpoint custody

Recommend **24 mantras**, **440 batches**: 439 x 24 + 16. Lexicographically ordered fixed-width
canonical IDs, consecutive slices; the entire plan includes freeze hash and has a canonical JSON hash.
One EvidencePacket per model context is preferred, with 24 as persistence/scheduling unit. Never
hundreds of packets per context. Keep semantic extraction packet-local even if a batch dispatches
several independent calls. Do not carry previous semantic outputs into the next packet's context.

src/vedagraph/semantic/full_run.py provides offline custody with PENDING, EXTRACTED, VALIDATED,
FAILED and SEALED checkpoints. Each has run_id, batch_id, mantra_ids, packet_hashes, plan_hash,
output_hash, validator_result and completed_timestamp. Packet hashes are recomputed before staging
and resume. Full packet hashes are accumulated per staged batch and included in the final seal;
the preparation sources are frozen first. Output files are atomically replaced only within a
single-writer transaction; flush/fsync precedes replace. The 508 runner lacked verified skipping,
atomic writes and a resumable state machine, and has deliberately not been modified or reused.

Workflow for a future separately authorized execution adapter:

1. Verify the Freeze against on-disk inputs and canonical full IDs before dispatch and each resume.
2. Construct BatchStore from the exact hashed Plan. prepare(batch_id, packets) freezes packet
   hashes and rejects reordered, missing, duplicate or mutated input. Verify all completed outputs
   with recover before deciding what needs work. A live single-writer lock prevents overlap.
3. Only PENDING with no output is eligible for model dispatch. Persist actual response receipts
   in the future execution adapter; the store accepts already-authored payloads, never invokes Luna.
4. commit writes output, then EXTRACTED checkpoint, then validates. It refuses duplicate commits.
   An output/checkpoint interruption is recovered by re-reading and validating the existing output,
   without re-extraction. FAILED attempts require explicit retry_failed; prior output is archived by
   content hash. Failed attempts must never be silently overwritten.
5. Completed batches are rehashed and revalidated. Mismatch fails closed. A stale writer lock requires
   operator confirmation that the process is dead before manual removal; no time-based automatic theft.
6. regenerate rebuilds aggregate data from validated batch files without extraction. Reports can read
   that aggregate independently. seal verifies the full freeze/IDs, every batch, all hashes and duplicate
   IDs, then writes a full-run output seal and marks checkpoints SEALED. Candidate-only fields are fixed.

Local fsync/atomic replace protects process interruption; network-filesystem durability and power-loss
recovery are not certified. A process killed after a model response but before local receipt persistence
cannot promise exactly-once remote execution: the future adapter needs provider request IDs/idempotency
where available. Do not claim the offline store solves remote execution. The live adapter/provenance
remains blocked under B03; existing regex producer must not be connected as a substitute.

## Validation and reporting cadence

Per packet: strict V3 shape and complete evidence/identity membership checks. Per batch: coverage,
candidate-only status, no unlocking, raw response receipt, hashes and fourteen-family trace verification.
Every 10 validated batches: regenerate counts, failures and risk metrics without showing prior semantic
outputs to the extractor. Pause on any repeated relation-binding failure or evidence corruption.
At completion: 10,552 exact unique IDs, no unresolved failed batches, matching freeze, sealed aggregate,
distributions, no-claim/gap inventories, all deterministic parallel comparisons and uncapped risk ledger.
No full candidate enters canonical knowledge, HUMAN_GOLD or SOURCE_EXPLICIT automatically.

## Next session

Do not execute the full run. Resolve B01/B02/B03, wire and verify the actual model adapter and complete
runtime/receipt pinning in a new execution contract. Retain frozen V3 prompt/schema unless a separate
architecture finding requires change. Re-run readiness after bounded regression verification.
The deferred target is Luna gpt-5.6-luna, high reasoning, CODEX_DIRECT, packet-local contexts,
24-mantra checkpoints, 440 batches, candidate-only. `{RUN_ID}` is a proposed unused ID; execution
changes before sealing the draft require a freshly named version, never reuse pilot identity.
""",
    )
    report(
        "RIGVEDA_SEMANTIC_FULL_RUN_READINESS.md",
        f"""# Full Rigveda V3 candidate readiness

{NOTICE}

## Final state

`FULL_RIGVEDA_V3_CANDIDATE_RUN_BLOCKED`

## Starting health

508 mantras, 917 assertions, 143 no-claim mantras, 70 gaps, 256 canonical-reference objects.
917 EXPLICIT, 0 STRONG_INFERENCE, 0 INTERPRETIVE. Legacy validator/evidence/type checks report zero
failures. Embedded 120 agrees exactly; all prior expert cases remain unannotated. These structural
and replay checks were reproduced by the relevant tests. They do not establish semantic entailment,
correct relation-to-entity binding, complete span validation or independent model replication.

## Ontology decision

`KEEP_GAPS_FOR_FULL_RUN`. Existing occurrence gaps are representable and reviewable. PERSON_REF is
optional later improvement, not a prerequisite. See RIGVEDA_SEMANTIC_508_ONTOLOGY_AUDIT.md for all 70.
Counts: {json.dumps(summary["gap_counts"], sort_keys=True)}. {len(anchor_defects)} misleading substring spans.

## Parallel decision

`PARALLEL_EXTRACTION_BUG_FOUND`. Six near pairs share a false offspring request in RV 10.58.1;
five have legitimate waters/plants text differences. Both exact-partial cases are translation effects.
The relation-binding mechanism repeats in the review queue, so this is a systemic engineering blocker.
See RIGVEDA_SEMANTIC_508_PARALLEL_AUDIT.md for all 13 pair audits with deterministic metrics.

## Exact blockers and closure requirements

{chr(10).join(f"- **{key}**: {value}" for key, value in BLOCKERS.items())}

No blocker is an exhaustive-human-review requirement. No ontology or prompt/schema change is proven
necessary. This session adds only audit/custody infrastructure, not semantic extraction repairs.
The supplemental importer now checks nested identity and gap evidence membership but cannot certify
the meaning of an anchor. Old zero-failure reports remain unchanged and must be read with that limit.

## Queue and expert review

All 50 triaged: {summary["triage_blocking"]} blocking manifestations, {50 - summary["triage_blocking"]} nonblocking.
Categories, reasons and secondary tags appear in RIGVEDA_SEMANTIC_508_REVIEW_TRIAGE.md. None is gold.
The three engineering blocker mechanisms, not the number of affected pairs/cases, determine the gate.

## Operations and immutability

Offline batch persistence, hash verification, duplicate prevention, failure recovery, atomic writes,
aggregate regeneration and seal prerequisites are implemented in semantic/full_run.py. Actual model
dispatch and response provenance are intentionally absent and remain a B03 requirement. See
RIGVEDA_SEMANTIC_FULL_RUN_OPERATIONS.md for four-tier review, projections and runtime limitations.

Proposed plan: 24 mantras, 440 batches (last 16). ID-only draft hash `{summary["plan_hash"]}`.
Frozen-current-files draft hash `{summary["freeze_hash"]}`. Draft is blocked, not authorization.
Prompt and V3 schema remain byte-identical. No lower deterministic layer was changed.

## Quality and Git safety

Preflight: ruff format --check (267 files), ruff check, mypy --strict (86 source files) passed;
146 semantic tests passed and one optional OpenAI SDK test skipped. The initial shell wildcard pytest
invocation did not expand on PowerShell and was corrected to a collected semantic test selection.
Final checks and audit-specific regression outcomes are recorded in readiness_quality.json after execution.
The starting workspace was extensively dirty. All pre-existing src/prompt/schema/semantic artifacts
are protected by readiness_starting_files.json; no commit, reset, stash or cleanup was performed.

## Next-session configuration

Next session is corrective engineering and bounded regression verification, not full extraction.
Deferred extraction target: `{RUN_ID}`, model gpt-5.6-luna, reasoning high, runtime CODEX_DIRECT,
24-mantra checkpoints, one packet per semantic context, 440 batches. Complete runtime/receipt freeze,
resolve the exact blockers, issue a new execution version and rerun the gate before any model dispatch.
All outputs remain LLM_EXTRACTED / MODEL_CANDIDATE, CANDIDATE / NEEDS_REVIEW, unlocked_predicates [].
""",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
