"""Grade a delta run independently, then compose it with the frozen 60-question result.

**The synthesis model does not grade itself.** Every check here is either deterministic
code or a query against the live graph: the packet is replayed from Neo4j, each citation
is resolved against it, each integer in the prose is matched to an evidence row, and each
Sanskrit run is checked for provenance. The verdicts are recorded below as data, with the
measurement that justifies each one, so a reader can disagree with the judgement while
checking the arithmetic.

**The composite is 57 + 3, and says so per question.** Fifty-seven verdicts come from the
frozen run and are copied unchanged; three come from delta runs, in two artifacts made at
two commits. Nothing here re-grades an *untouched* answer: a frozen verdict is replaced
only for a question that was actually re-asked and re-measured.

Q02 is the third. Its frozen answer said Indra's attributed verses were "distributed
across all ten mandalas" over a row enumerating nine, and it had been graded
SUPPORTED_CORRECT because every *figure* in it checked out -- the unsupported word was
"ten". That is the class this guardrail was built for, so the question was re-asked rather
than left in the backlog with a verdict its own product now contradicts.

The remaining fifty-seven are still not re-graded against rules that postdate them: that
would produce a number describing neither run.

Usage::

    python scripts/grade_ask_delta.py <delta-artifact.jsonl> [<more-artifacts.jsonl> ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from vedagraph.api.ask import evidence as evidence_stage
from vedagraph.api.ask import planner as planner_stage
from vedagraph.api.ask import resolver as resolver_stage
from vedagraph.api.ask import retriever as retriever_stage
from vedagraph.api.ask.citation import audit as citation_audit
from vedagraph.api.ask.citation import extract_cited_ids
from vedagraph.api.ask.models import AskMode
from vedagraph.api.ask.quantitative import _DIGIT_GROUPING, numeric_facts, validate
from vedagraph.api.config import get_api_settings
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

FROZEN_EVALUATION: Final = Path(
    "data/gold/ask_benchmark_runs/"
    "openrouter-nvidia_nemotron-3-ultra-550b-a55b_free-bfdba0b998f1f6cd-evaluation.jsonl"
)
FROZEN_RUN: Final = Path(
    "data/gold/ask_benchmark_runs/"
    "openrouter-nvidia_nemotron-3-ultra-550b-a55b_free-bfdba0b998f1f6cd.jsonl"
)
FROZEN_SHA: Final = "b20f8c34802b56c23a1811ee99544814ae855ad97e4cb6af2315ca79a091a625"

COMPOSITE_LABEL: Final = "ASK_PRODUCT_V1_FINAL_COMPOSITE"

ORIGINAL_FROZEN_RUN: Final = "ORIGINAL_FROZEN_RUN"
POST_FIX_DELTA_RUN: Final = "POST_FIX_DELTA_RUN"


@dataclass(frozen=True)
class Verdict:
    """One graded question, with the reasoning kept beside the label."""

    question_id: str
    original_verdict: str
    root_cause: str
    fix: str
    final_verdict: str
    reason: str


#: The two verdicts, and why. Written here rather than derived, because a verdict is a
#: judgement about truthfulness and the mechanical checks below are its evidence, not its
#: replacement. Each reason names a measurement the script prints.
VERDICTS: Final[tuple[Verdict, ...]] = (
    Verdict(
        question_id="Q34",
        original_verdict="MISLEADING",
        root_cause=(
            "Two causes, both product defects. The planner's passage-key pattern could "
            "not parse a sectioned Samavedic citation, so passage lookup never ran for "
            "any of the 1,844 Samavedic mantras and the packet came back empty; and the "
            "scope line's 'contains NO Aranyaka' collided with ARANYA, one of the four "
            "sections of the Kauthuma arcika, which the product itself cites as "
            "'SV ARANYA 1.1'. Told only the genre statement, the model correctly obeyed "
            "it and denied that a verse this graph stores exists at all. Absence was "
            "asserted from an empty retrieval."
        ),
        fix=(
            "The pattern admits the four arcika section tokens, needs only one numeric "
            "part when a section is named (the Mahanamnya is flat -- eleven verses cited "
            "'SV MAHANAMNYA 1' to '10' -- and a two-part minimum had kept that whole "
            "section unreachable even after the first fix), and tolerates the same "
            "separators the reader endpoint always has, so 'sv_aranya_1.1' resolves in "
            "both surfaces. The scope line now states the collision in both directions: "
            "an SV ARANYA locus IS present as arcika verse text, and its presence is not "
            "a claim to hold a separate or complete Aranyaka corpus."
        ),
        final_verdict="PARTIAL_CORRECT",
        reason=(
            "The passage now resolves and the answer returns its Sanskrit, byte-identical "
            "to the PRIMARY_TEXT the graph holds at VG:SV:KAU:ARANYA:D01:V01, cited [E1] "
            "with no invented id and no unverified Sanskrit run. It makes no claim of "
            "absence and no claim to hold an Aranyaka corpus. PARTIAL rather than "
            "SUPPORTED because the packet holds one item: the Samavedic corpus carries no "
            "translation for any of its verses, so the verse text is all there is to give, "
            "and the runtime grades one substantive citation as LIMITED. Correct and "
            "complete for what the graph holds, and thin for the same reason."
        ),
    ),
    Verdict(
        question_id="Q02",
        original_verdict="SUPPORTED_CORRECT",
        root_cause=(
            "SYNTHESIS_QUANTITATIVE_OVERSTATEMENT over a row that prints only its "
            "positive keys. E13 gives DEVATA_STRUCTURAL_SPREAD as nine mandala keys -- "
            "1-8 and 10 -- because Indra holds no HAS_DEVATA attribution in mandala 9 at "
            "all, that mandala being the Soma Pavamana collection, 1,087 of whose verses "
            "are dedicated to Soma instead. The answer rounded nine keys up to 'all ten "
            "mandalas'. Nothing caught it: every figure in the sentence was real and "
            "correctly cited, so the citation audit passed and the figure check passed; "
            "the unsupported token was the word 'ten'. It was graded SUPPORTED_CORRECT "
            "on exactly that reasoning, and the grading note recorded that every figure "
            "matched -- which was true, and not the question."
        ),
        fix=(
            "None specific to this question, and that is the point: the UNIVERSAL rule "
            "shipped for Q60 already covers a counted universal asserted over an "
            "enumeration of fewer groups, and it found this one offline by being run "
            "across all sixty frozen answers. The re-ask verifies the guardrail on the "
            "answer that motivated no part of it."
        ),
        final_verdict="PARTIAL_CORRECT",
        reason=(
            "The overstatement is gone and nothing was substituted for it: the answer "
            "now recites E13's nine pairs exactly as the packet gives them -- 1: 493, "
            "2: 141, 3: 229, 4: 197, 5: 103, 6: 279, 7: 163, 8: 862, 10: 402 -- with no "
            "universal over them and no mandala the row does not carry. Critically it "
            "does NOT convert the gap into an absence: the words absent, never, nowhere "
            "and zero do not occur, and mandala 9 is named in neither direction. That "
            "restraint is correct rather than merely cautious, because 214 mandala-9 "
            "verses do mention Indra under MENTIONS_DEVATA, so 'Indra is absent from "
            "mandala 9' would have been a second, worse defect -- and the packet carries "
            "no per-mandala mention row from which the answer could have said so either "
            "way. Every figure is verified against the replayed packet and the live "
            "graph, the quantitative validator returns no finding, nine citations all "
            "resolve, none is invented, and the generation was not truncated. "
            "PARTIAL rather than SUPPORTED for a defect the mechanical checks cannot "
            "see, found by reading the answer: the second paragraph says the entity "
            "description 'derives from the Rigvedic Anukramani attribution layer'. It "
            "does not. E5 is an ENTITY_FACT, a characterisation this project authored, "
            "and E5's qualifier -- about the Anukramani layer covering the Rigveda only "
            "-- is a scope note travelling with the item, not the description's source. "
            "The answer's own preceding sentence calls it 'an entity-level "
            "characterisation' and then contradicts itself. The frozen answer had this "
            "right ('from the project's entity layer, not from a quoted verse'), so it "
            "is a regression in the re-ask, not a standing product defect. It "
            "misdescribes the provenance of one curated sentence rather than the content "
            "of the corpus -- no data is manufactured, denied or miscounted -- which is "
            "why it is PARTIAL and not MISLEADING. Recorded as ASK_BL_13. The answer "
            "also drops the frozen version's non-additivity note, though it commits no "
            "additivity error, labelling each figure with the relation type that "
            "produced it."
        ),
    ),
    Verdict(
        question_id="Q60",
        original_verdict="MISLEADING",
        root_cause=(
            "SYNTHESIS_QUANTITATIVE_OVERSTATEMENT, and a missing contract rather than a "
            "retrieval fault. Retrieval, the evidence packet and every citation were "
            "correct; the prose said 'the hotr appears in hundreds of verses in each "
            "corpus, and the sacrifice in hundreds as well [E7, E8]' over rows reading 18 "
            "AV, 195 RV, 38 SV and 49 YV, overstating three of four corpora by five to "
            "ten times while citing the two items that refute it. No stage could see it: "
            "every check before synthesis tested provenance and none tested arithmetic."
        ),
        fix=(
            "A deterministic post-synthesis validator over integers the packet already "
            "printed -- magnitude, counted universal, exact count, comparison, majority "
            "and absence -- scoped per sentence to the rows that sentence itself cites. A "
            "flagged draft is returned to the provider once with a generic instruction "
            "naming neither the question nor the figure; if it still fails the answer is "
            "graded PARTIAL and carries a caveat rather than being returned as fully "
            "supported. No question-specific branch exists anywhere in it."
        ),
        final_verdict="SUPPORTED_CORRECT",
        reason=(
            "The overstatement is gone and its opposite is present: the answer now states "
            "all sixteen per-corpus figures exactly as E7 and E8 give them, every one "
            "verified against the replayed packet and the live graph. Six citations, all "
            "resolving, none invented. The quantitative validator returns no finding, the "
            "Sanskrit quoted is in the cited evidence, the generation was not truncated, "
            "and the answer closes by naming what the evidence does not establish."
        ),
    ),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def _replay(
    repo: Neo4jRepository, question: str, context: dict[str, Any]
) -> evidence_stage.EvidencePacket:
    plan = planner_stage.plan(
        question, explicit_veda=context.get("veda"), mode=AskMode(context.get("mode", "AUTO"))
    )
    if context.get("passage_context") and not plan.passage_key:
        plan.passage_key = context["passage_context"]
    if context.get("entity_context"):
        plan.entities_mentioned.insert(0, context["entity_context"])
        if "entities" not in plan.retrieval_channels:
            plan.retrieval_channels.insert(0, "entities")
    resolved = resolver_stage.resolve_entities(plan.entities_mentioned, repo)
    return evidence_stage.build_evidence_packet(retriever_stage.retrieve(plan, resolved, repo))


#: Digits that are never a count: an evidence id, and a passage locus.
_NOT_A_COUNT: Final = re.compile(
    r"\[[^\]]{0,120}\]|\b[A-Z]{2,4}(?:\s+[A-Z]{4,12})?\s*\d+(?:\.\d+)+"
)
#: A count in the prose. Digits inside a dotted locus are excluded by requiring
#: that no digit follow the dot -- which keeps a *sentence-final* figure, where the
#: dot is a full stop: "ABOUT_CONCEPT 50." is the figure 50, and a pattern refusing
#: any adjacent dot skipped it, under-reporting what the answer actually stated.
_INTEGER: Final = re.compile(r"(?<!\d)(?<!\d\.)(\d{1,9})(?!\d)(?!\.\d)")


def _figure_check(answer: str, packet: evidence_stage.EvidencePacket) -> dict[str, Any]:
    """Every integer in the prose, matched against the figures the packet printed.

    Stricter than the shipped validator on purpose: this is the audit, so it reports
    *every* unmatched figure rather than only the ones a named rule fires on.

    One thing it must not do is report an *identifier* as an unmatched figure. A metric
    row labels its values with numbers -- ``DEVATA_STRUCTURAL_SPREAD: {"1": 493, "8":
    862}`` means mandala 1 and mandala 8 -- so an answer that recites the row states 1
    and 8 as labels and 493 and 862 as counts. Pooling all four into one set and
    subtracting made this report read ``figures_not_in_packet: [1, 2, 3, ...]`` over an
    answer that had quoted the row exactly, which is the audit itself manufacturing a
    fabrication claim. Labels are matched against the packet's own group strings and
    reported under their own name, so the two kinds stay distinguishable and neither is
    hidden. Verse loci are already dropped upstream by ``_NOT_A_COUNT`` for the same
    reason.
    """
    values: set[int] = set()
    labels: set[int] = set()
    for item in packet.items:
        for fact in numeric_facts(item):
            values.add(fact.value)
            if fact.group:
                labels.update(int(m.group(1)) for m in _INTEGER.finditer(fact.group))
    masked = _NOT_A_COUNT.sub(" ", answer)
    masked = _DIGIT_GROUPING.sub("", masked)
    stated = {int(m.group(1)) for m in _INTEGER.finditer(masked)}
    return {
        "figures_in_answer": sorted(stated),
        "figures_in_packet": sorted(values),
        "figures_not_in_packet": sorted(stated - values - labels),
        "group_labels_in_packet": sorted(labels),
        "stated_as_a_packet_group_label": sorted((stated - values) & labels),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "artifacts",
        type=Path,
        nargs="+",
        help="Delta artifacts, in any order. A question re-asked twice is an error "
        "rather than a last-one-wins, because the composite must name one measurement.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/gold/ask_benchmark_runs/ask_product_v1_final_composite.json"),
    )
    args = parser.parse_args()

    # Which artifact supplied which question is recorded, not inferred: the composite
    # names three delta verdicts made at two commits, and a reader must be able to
    # check each one against the file it actually came from.
    delta: dict[str, dict[str, Any]] = {}
    delta_source: dict[str, Path] = {}
    for artifact in args.artifacts:
        for row in _rows(artifact):
            if row["id"] in delta:
                raise SystemExit(
                    f"{row['id']} appears in both {delta_source[row['id']]} and "
                    f"{artifact}; the composite would have to pick one silently"
                )
            delta[row["id"]] = row
            delta_source[row["id"]] = artifact
    frozen_eval = {row["question_id"]: row for row in _rows(FROZEN_EVALUATION)}
    frozen_run = {row["id"]: row for row in _rows(FROZEN_RUN)}

    frozen_sha = _sha(FROZEN_RUN)
    print(f"frozen artifact sha256 : {frozen_sha}")
    print(f"matches the graded run : {frozen_sha == FROZEN_SHA}")
    for artifact in args.artifacts:
        print(f"delta artifact sha256  : {_sha(artifact)}  {artifact}")
    print()

    repo = Neo4jRepository(get_api_settings())
    graded: list[dict[str, Any]] = []
    try:
        for verdict in VERDICTS:
            row = delta[verdict.question_id]
            packet = _replay(repo, row["question"], row.get("context") or {})
            audited = citation_audit(row["answer"], packet)
            quantitative = validate(row["answer"], packet)
            packet_ids = set(packet.by_id())
            cited = extract_cited_ids(row["answer"])
            figures = _figure_check(row["answer"], packet)

            checks = {
                "packet_items_replayed": len(packet.items),
                "packet_items_recorded": row["evidence_count"],
                "citations_in_answer": cited,
                "citations_not_in_packet": [c for c in cited if c not in packet_ids],
                "invented_citations_surviving": row["invented_citations_surviving"],
                "sanskrit_absent_from_packet": audited.unverified_quotes,
                "sanskrit_in_packet_but_uncited": audited.uncited_quotes,
                "quantitative_findings": [
                    {"rule": f.rule.value, "detail": f.detail} for f in quantitative.findings
                ],
                "generation_truncated": row["generation_truncated"],
                "runtime_status": row["status"],
                "runtime_support_level": row["support_level"],
                **figures,
            }
            graded.append(
                {
                    "question_id": verdict.question_id,
                    "question": row["question"],
                    "provenance": POST_FIX_DELTA_RUN,
                    "code_commit": row["code_commit"],
                    "original_verdict": verdict.original_verdict,
                    "root_cause": verdict.root_cause,
                    "fix": verdict.fix,
                    "new_runtime_status": row["status"],
                    "final_verdict": verdict.final_verdict,
                    "citation_validation": (
                        "PASS"
                        if not checks["citations_not_in_packet"]
                        and not row["invented_citations_surviving"]
                        else "FAIL"
                    ),
                    "quantitative_validation": ("PASS" if not quantitative.findings else "FAIL"),
                    "truncation_status": (
                        "TRUNCATED" if row["generation_truncated"] else "COMPLETE"
                    ),
                    "reason": verdict.reason,
                    "checks": checks,
                    "answer": row["answer"],
                }
            )

            print("=" * 78)
            print(f"{verdict.question_id}  {verdict.original_verdict} -> {verdict.final_verdict}")
            for key, value in checks.items():
                print(f"  {key:34} {value}")
    finally:
        repo.close()

    # -- composite: 57 untouched + 3 delta -----------------------------------
    replaced = {v.question_id for v in VERDICTS}
    composite: list[dict[str, Any]] = []
    for qid, row in frozen_eval.items():
        if qid in replaced:
            continue
        composite.append(
            {
                "question_id": qid,
                "question": row["question"],
                "provenance": ORIGINAL_FROZEN_RUN,
                "code_commit": frozen_run[qid]["code_commit"],
                "final_verdict": row["final_verdict"],
                "runtime_status": row["runtime_status"],
                "citation_validation": (
                    "PASS" if not row["invented_citations_surviving"] else "FAIL"
                ),
            }
        )
    composite.extend(
        {
            "question_id": entry["question_id"],
            "question": entry["question"],
            "provenance": entry["provenance"],
            "code_commit": entry["code_commit"],
            "final_verdict": entry["final_verdict"],
            "runtime_status": entry["new_runtime_status"],
            "citation_validation": entry["citation_validation"],
        }
        for entry in graded
    )

    #: The frozen grading spells a refusal in full; the report totals it under the short
    #: name. Mapped rather than renamed, because the frozen file is not edited.
    buckets = {
        "SUPPORTED_CORRECT": 0,
        "PARTIAL_CORRECT": 0,
        "CORRECTLY_REFUSED": 0,
        "MISLEADING": 0,
        "HALLUCINATED": 0,
    }
    for entry in composite:
        key = entry["final_verdict"].replace(
            "INSUFFICIENT_EVIDENCE_CORRECTLY_REFUSED", "CORRECTLY_REFUSED"
        )
        buckets[key] += 1

    total_citations = sum(
        len(frozen_run[e["question_id"]]["citation_ids"])
        if e["provenance"] == ORIGINAL_FROZEN_RUN
        else len(delta[e["question_id"]]["citation_ids"])
        for e in composite
    )
    surviving = sum(
        len(
            frozen_run[e["question_id"]]["invented_citations_surviving"]
            if e["provenance"] == ORIGINAL_FROZEN_RUN
            else delta[e["question_id"]]["invented_citations_surviving"]
        )
        for e in composite
    )

    print("\n" + "=" * 78)
    print(COMPOSITE_LABEL)
    print("=" * 78)
    print(f"  questions                        {len(composite)}")
    for name, count in buckets.items():
        print(f"  {name:32} {count}")
    print(f"  total citations                  {total_citations}")
    print(f"  invented citations surviving     {surviving}")
    print(
        f"  from {ORIGINAL_FROZEN_RUN:24} "
        f"{sum(1 for e in composite if e['provenance'] == ORIGINAL_FROZEN_RUN)}"
    )
    print(
        f"  from {POST_FIX_DELTA_RUN:24} "
        f"{sum(1 for e in composite if e['provenance'] == POST_FIX_DELTA_RUN)}"
    )

    args.out.write_text(
        json.dumps(
            {
                "label": COMPOSITE_LABEL,
                "frozen_run_artifact": str(FROZEN_RUN),
                "frozen_run_sha256": frozen_sha,
                "frozen_run_sha256_matches_graded": frozen_sha == FROZEN_SHA,
                "delta_run_artifacts": [
                    {
                        "artifact": str(artifact),
                        "sha256": _sha(artifact),
                        "question_ids": sorted(
                            (q for q, a in delta_source.items() if a == artifact),
                            key=lambda q: int(q[1:]),
                        ),
                    }
                    for artifact in args.artifacts
                ],
                "totals": buckets,
                "total_questions": len(composite),
                "total_citations": total_citations,
                "invented_citations_surviving": surviving,
                "delta_grading": graded,
                "per_question": sorted(composite, key=lambda e: int(e["question_id"][1:])),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwritten to {args.out}")


if __name__ == "__main__":
    main()
