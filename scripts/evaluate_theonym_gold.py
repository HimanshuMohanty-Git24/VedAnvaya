"""Measure the precision and recall of the four-Veda theonym mention layer.

The layer under test is ``MENTIONS_DEVATA``, built by
:mod:`vedagraph.domain.theonyms` and projected by
:func:`vedagraph.domain.v3_loader.load_theonym_mentions`. This script scores it against
``data/gold/theonym_mention_gold_v1.jsonl`` and reports the result.

**Nothing here is reported blended across extraction paths.** The Rigveda has the
University of Zurich manual morphosyntactic annotation, so a Rigvedic mention is a
statement by a scholarly source that this token's lemma is ``indra-``. The Samaveda,
Yajurveda and Atharvaveda have no annotation, so a mention there is an adjudicated
surface match. Those are different claims with different error profiles, and a single
combined figure would let the annotated corpus's accuracy stand in for the unannotated
ones'. Every headline number below is therefore emitted three times: overall, for
``rv-lemma-annotation``, and for the two surface paths.

**Two targets, not one.** The gold set carries two labels per row:

``gold_label``
    The strict claim: does this verse name this **god**? A verse that uses ``soma`` for
    the pressed juice offered to Indra scores ``NO_MENTION`` even though the string is
    there. This is the target that matters for a graph whose nodes are deities.

``name_lemma_present``
    The weaker claim: does a word of this deity's name-lemma occur in the verse at all,
    in whichever sense? Scoring against this isolates *attachment* errors -- host
    intrusion, sandhi mis-segmentation, a wrong lemma -- from *sense* errors. The gap
    between the two is the size of the homonym problem.

Rows labelled ``AMBIGUOUS`` are excluded from every precision and recall denominator and
counted separately, because a large exclusion bucket is itself a finding.

The sample is **stratified and deliberately over-samples the cells most likely to fail**,
so the pooled figures are diagnostic rather than corpus-representative. The
``uniform_*`` strata are plain uniform draws from the live edge set and are the only
unbiased precision estimates here; they are reported separately under that name.

Usage::

    python scripts/evaluate_theonym_gold.py
    python scripts/evaluate_theonym_gold.py --json out.json
    python scripts/evaluate_theonym_gold.py --no-graph   # score the frozen snapshot only
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import json
import math
import pathlib
import sys
from collections.abc import Iterable, Sequence
from typing import Any, Final

GOLD_PATH: Final = pathlib.Path("data") / "gold" / "theonym_mention_gold_v1.jsonl"

BOLT_URI: Final = "bolt://localhost:7687"
BOLT_AUTH: Final = ("neo4j", "vedagraph_dev")

LABEL_MENTION: Final = "MENTION"
LABEL_NO_MENTION: Final = "NO_MENTION"
LABEL_AMBIGUOUS: Final = "AMBIGUOUS"
VALID_LABELS: Final[frozenset[str]] = frozenset(
    {LABEL_MENTION, LABEL_NO_MENTION, LABEL_AMBIGUOUS}
)

PATH_ANNOTATION: Final = "rv-lemma-annotation"
SURFACE_PATHS: Final[frozenset[str]] = frozenset(
    {"sanskrit-surface-token", "sanskrit-surface-sandhi"}
)

#: Below this many scorable rows a per-deity or per-cell rate is not printed. A figure
#: built on two rows moves by 0.50 on one disagreement and is worse than silence.
MIN_SUPPORT: Final = 8

#: The one field a reader is entitled to check before believing anything else.
REQUIRED_ANNOTATOR: Final = "MODEL_ADJUDICATED"

_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "annotator",
    "citation",
    "devata_id",
    "extraction_path",
    "gold_label",
    "graph_asserts",
    "name_lemma_present",
    "passage_key",
    "reasoning",
    "referent_certainty",
    "row_id",
    "sanskrit",
    "sample_seed",
    "schema_version",
    "stratum",
    "surface_form",
    "veda",
)


class GoldSetError(ValueError):
    """The gold file is unusable. Raised rather than scored around."""


@dataclasses.dataclass(frozen=True)
class GoldRow:
    """One adjudicated (passage, deity) pair."""

    row_id: str
    stratum: str
    passage_key: str
    citation: str
    veda: str
    devata_id: str
    surface_form: str
    graph_asserts: bool
    extraction_path: str
    referent_certainty: str
    morphological_role: str
    gold_label: str
    name_lemma_present: bool
    ambiguity_class: str
    borderline: bool
    is_ambiguous_common_noun: bool
    reasoning: str

    @property
    def scorable(self) -> bool:
        """False for a row the Sanskrit does not settle."""
        return self.gold_label != LABEL_AMBIGUOUS

    @property
    def gold_positive(self) -> bool:
        return self.gold_label == LABEL_MENTION

    @property
    def path_group(self) -> str:
        """Which extraction path this row tests.

        A row with no edge is grouped by its Veda rather than by an edge property it
        does not have: a missed Rigvedic mention is a failure of the annotation path and
        a missed Atharvavedic one is a failure of the surface path, and pooling them
        would hide which.
        """
        if self.extraction_path == PATH_ANNOTATION:
            return PATH_ANNOTATION
        if self.extraction_path in SURFACE_PATHS:
            return "surface"
        return PATH_ANNOTATION if self.veda == "RV" else "surface"


@dataclasses.dataclass(frozen=True)
class Score:
    """Confusion counts and the rates derived from them."""

    tp: int
    fp: int
    fn: int
    tn: int

    @property
    def support(self) -> int:
        return self.tp + self.fp + self.fn + self.tn

    @property
    def predicted_positive(self) -> int:
        return self.tp + self.fp

    @property
    def gold_positive(self) -> int:
        return self.tp + self.fn

    @property
    def precision(self) -> float | None:
        return None if self.predicted_positive == 0 else self.tp / self.predicted_positive

    @property
    def recall(self) -> float | None:
        return None if self.gold_positive == 0 else self.tp / self.gold_positive

    @property
    def f1(self) -> float | None:
        precision, recall = self.precision, self.recall
        if precision is None or recall is None or precision + recall == 0.0:
            return None
        return 2 * precision * recall / (precision + recall)

    @property
    def specificity(self) -> float | None:
        negatives = self.tn + self.fp
        return None if negatives == 0 else self.tn / negatives

    def as_dict(self) -> dict[str, Any]:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "support": self.support,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "specificity": self.specificity,
        }


def score_rows(rows: Iterable[GoldRow], *, target: str = "gold_label") -> Score:
    """Confusion counts for one group of rows.

    ``target`` selects which claim is being scored: ``gold_label`` is the strict
    deity-reference reading, ``name_lemma_present`` the weaker "the name-word is in this
    verse at all" reading. Non-scorable rows are dropped by the caller, not here, so
    that the count of dropped rows stays visible.
    """
    tp = fp = fn = tn = 0
    for row in rows:
        predicted = row.graph_asserts
        actual = row.gold_positive if target == "gold_label" else row.name_lemma_present
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1
    return Score(tp=tp, fp=fp, fn=fn, tn=tn)


def wilson_interval(successes: int, trials: int, *, z: float = 1.96) -> tuple[float, float]:
    """A 95% Wilson score interval, which behaves at 0 and at 1 where normal-approximation
    intervals do not. Reported beside every headline rate so a reader can see how much of
    the number is the sample size.
    """
    if trials == 0:
        return (0.0, 1.0)
    proportion = successes / trials
    denominator = 1.0 + z * z / trials
    centre = proportion + z * z / (2 * trials)
    spread = z * math.sqrt(proportion * (1 - proportion) / trials + z * z / (4 * trials * trials))
    return (max(0.0, (centre - spread) / denominator), min(1.0, (centre + spread) / denominator))


def _require(record: dict[str, Any], row_id: str) -> None:
    missing = [field for field in _REQUIRED_FIELDS if field not in record]
    if missing:
        raise GoldSetError(f"{row_id}: missing fields {missing}")
    label = record["gold_label"]
    if label not in VALID_LABELS:
        raise GoldSetError(f"{row_id}: gold_label {label!r} not in {sorted(VALID_LABELS)}")
    annotator = record["annotator"]
    if annotator != REQUIRED_ANNOTATOR:
        raise GoldSetError(
            f"{row_id}: annotator is {annotator!r}. This set was adjudicated by a model; "
            f"only {REQUIRED_ANNOTATOR!r} is truthful here."
        )
    if not str(record["reasoning"]).strip():
        raise GoldSetError(f"{row_id}: empty reasoning")
    if not str(record["sanskrit"]).strip():
        raise GoldSetError(f"{row_id}: empty sanskrit; every row is adjudicated against the text")


def load_gold(path: pathlib.Path) -> list[GoldRow]:
    """Read and validate the frozen gold set."""
    if not path.exists():
        raise GoldSetError(f"gold set not found: {path}")
    rows: list[GoldRow] = []
    seen: set[str] = set()
    seeds: set[int] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GoldSetError(f"{path}:{number}: not JSON: {exc}") from exc
        row_id = str(record.get("row_id", f"line {number}"))
        _require(record, row_id)
        if row_id in seen:
            raise GoldSetError(f"{row_id}: listed twice")
        seen.add(row_id)
        seeds.add(int(record["sample_seed"]))
        rows.append(
            GoldRow(
                row_id=row_id,
                stratum=str(record["stratum"]),
                passage_key=str(record["passage_key"]),
                citation=str(record["citation"]),
                veda=str(record["veda"]),
                devata_id=str(record["devata_id"]),
                surface_form=str(record["surface_form"]),
                graph_asserts=bool(record["graph_asserts"]),
                extraction_path=str(record["extraction_path"]),
                referent_certainty=str(record["referent_certainty"]),
                morphological_role=str(record.get("morphological_role", "")),
                gold_label=str(record["gold_label"]),
                name_lemma_present=bool(record["name_lemma_present"]),
                ambiguity_class=str(record.get("ambiguity_class", "UNAMBIGUOUS")),
                borderline=bool(record.get("borderline", False)),
                is_ambiguous_common_noun=bool(record.get("is_ambiguous_common_noun", False)),
                reasoning=str(record["reasoning"]),
            )
        )
    if not rows:
        raise GoldSetError(f"{path}: no rows")
    if len(seeds) != 1:
        raise GoldSetError(f"{path}: rows carry {len(seeds)} different sample seeds: {seeds}")
    return rows


def fetch_live_edges() -> set[tuple[str, str]]:
    """Every ``(passage_key, devata_id)`` the live graph asserts. Read-only."""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    try:
        with driver.session() as session:
            return {
                (str(record["pk"]), str(record["did"]))
                for record in session.run(
                    "MATCH (p:Passage)-[:MENTIONS_DEVATA]->(d:Devata) "
                    "RETURN p.canonical_key AS pk, d.entity_key AS did"
                )
            }
    finally:
        driver.close()


def reconcile(rows: Sequence[GoldRow], live: set[tuple[str, str]]) -> list[str]:
    """Rows whose frozen ``graph_asserts`` disagrees with the live graph.

    The gold set records the layer's claim at the moment it was frozen. If the graph has
    since been rebuilt, the metrics below describe a state that no longer exists, and
    saying so is more useful than silently scoring a stale snapshot.
    """
    return [
        row.row_id
        for row in rows
        if ((row.passage_key, row.devata_id) in live) != row.graph_asserts
    ]


def refresh_from_live(
    rows: Sequence[GoldRow], live: set[tuple[str, str]]
) -> list[GoldRow]:
    """Re-point every row's ``graph_asserts`` at the live graph, keeping its gold label.

    **Which half of a gold row is frozen, and which is not.** The ``gold_label`` is a
    judgement about the *text* -- whether this verse refers to this deity -- and it stays
    true however often the graph is rebuilt. ``graph_asserts`` is a snapshot of what the
    layer claimed at freeze time, and it goes stale the moment the layer changes.

    Scoring the frozen column measures a graph that no longer exists. That was not
    hypothetical: a one-condition recall fix landed 904 new edges, and because the scorer
    read the frozen column the headline precision and recall did not move at all, while
    the drift count quietly reported 13 disagreeing rows. Recomputed live, the same gold
    labels showed recall rising from 0.8514 to 0.8857 on 12 recovered true positives
    against 1 new false positive.

    So the default is live and ``--frozen`` is the opt-out, which keeps the reproducible
    historical figure available without making it the one a reader sees by accident.
    """
    return [
        dataclasses.replace(
            row, graph_asserts=(row.passage_key, row.devata_id) in live
        )
        for row in rows
    ]


def _fmt(value: float | None) -> str:
    return "  n/a " if value is None else f"{value:.4f}"


def _line(name: str, score: Score, *, width: int = 34) -> str:
    """One scored group.

    A slice containing no gold negatives cannot yield a recall figure -- its recall is
    1.0 by construction, not by merit -- so recall and F1 are printed as ``n/a`` there
    rather than as a number a reader could quote.
    """
    interval = wilson_interval(score.tp, score.predicted_positive)
    positives_only = score.fn + score.tn == 0
    recall = "  n/a " if positives_only else _fmt(score.recall)
    f1 = "  n/a " if positives_only else _fmt(score.f1)
    return (
        f"  {name:<{width}} P {_fmt(score.precision)} "
        f"[{interval[0]:.2f}-{interval[1]:.2f}]  "
        f"R {recall}  F1 {f1}   "
        f"tp={score.tp:4d} fp={score.fp:3d} fn={score.fn:3d} tn={score.tn:3d}"
    )


def _grouped(
    rows: Sequence[GoldRow], key: str, *, min_support: int = MIN_SUPPORT
) -> tuple[list[tuple[str, Score]], list[tuple[str, int]]]:
    """Scores per group, split into those with enough rows and those without."""
    buckets: dict[str, list[GoldRow]] = collections.defaultdict(list)
    for row in rows:
        buckets[str(getattr(row, key))].append(row)
    reported: list[tuple[str, Score]] = []
    withheld: list[tuple[str, int]] = []
    for name, group in sorted(buckets.items()):
        if len(group) >= min_support:
            reported.append((name, score_rows(group)))
        else:
            withheld.append((name, len(group)))
    return reported, withheld


def build_report(rows: Sequence[GoldRow], live: set[tuple[str, str]] | None) -> dict[str, Any]:
    """Every metric this measurement exists to produce."""
    ambiguous = [row for row in rows if not row.scorable]
    scorable = [row for row in rows if row.scorable]

    by_path: dict[str, list[GoldRow]] = collections.defaultdict(list)
    for row in scorable:
        by_path[row.path_group].append(row)

    report: dict[str, Any] = {
        "gold_rows": len(rows),
        "scorable_rows": len(scorable),
        "excluded_ambiguous": [
            {"row_id": row.row_id, "citation": row.citation, "reasoning": row.reasoning}
            for row in ambiguous
        ],
        "borderline_rows": sum(1 for row in scorable if row.borderline),
        "stratification": {
            name: {
                "rows": len(group),
                "graph_asserts": sum(1 for row in group if row.graph_asserts),
                "gold_mention": sum(1 for row in group if row.gold_positive),
            }
            for name, group in sorted(
                
                    (name, [row for row in rows if row.stratum == name])
                    for name in {row.stratum for row in rows}
                
            )
        },
        "overall": score_rows(scorable).as_dict(),
        "overall_name_lemma_target": score_rows(
            scorable, target="name_lemma_present"
        ).as_dict(),
        "by_path": {
            name: score_rows(group).as_dict() for name, group in sorted(by_path.items())
        },
        "by_path_name_lemma_target": {
            name: score_rows(group, target="name_lemma_present").as_dict()
            for name, group in sorted(by_path.items())
        },
        "by_extraction_path_positives_only": {
            name: score_rows(group).as_dict()
            for name, group in sorted(
                
                    (name, [row for row in scorable if row.extraction_path == name])
                    for name in {row.extraction_path for row in scorable if row.graph_asserts}
                
            )
        },
    }

    veda_reported, veda_withheld = _grouped(scorable, "veda")
    report["by_veda"] = {name: score.as_dict() for name, score in veda_reported}
    report["by_veda_withheld"] = dict(veda_withheld)

    deity_reported, deity_withheld = _grouped(scorable, "devata_id")
    report["by_deity"] = {name: score.as_dict() for name, score in deity_reported}
    report["by_deity_withheld"] = dict(deity_withheld)

    certainty = [row for row in scorable if row.graph_asserts]
    report["by_referent_certainty"] = {
        name: score.as_dict()
        for name, score in _grouped(certainty, "referent_certainty", min_support=1)[0]
    }

    ambiguous_nouns = [row for row in scorable if row.is_ambiguous_common_noun]
    asserted_ambiguous = [row for row in ambiguous_nouns if row.graph_asserts]
    wrong_sense = [
        row
        for row in asserted_ambiguous
        if not row.gold_positive and row.name_lemma_present
    ]
    report["ambiguity_failure"] = {
        "rows_on_ambiguous_common_nouns": len(ambiguous_nouns),
        "asserted": len(asserted_ambiguous),
        "wrong_sense": len(wrong_sense),
        "wrong_sense_rate": (
            None if not asserted_ambiguous else len(wrong_sense) / len(asserted_ambiguous)
        ),
        "score": score_rows(ambiguous_nouns).as_dict(),
        "examples": [
            {
                "row_id": row.row_id,
                "citation": row.citation,
                "devata_id": row.devata_id,
                "surface_form": row.surface_form,
                "reasoning": row.reasoning,
            }
            for row in wrong_sense[:12]
        ],
    }

    report["by_ambiguity_class"] = {
        name: score.as_dict()
        for name, score in _grouped(scorable, "ambiguity_class", min_support=1)[0]
    }

    report["errors"] = {
        "false_positives": [
            {
                "row_id": row.row_id,
                "citation": row.citation,
                "veda": row.veda,
                "devata_id": row.devata_id,
                "extraction_path": row.extraction_path,
                "referent_certainty": row.referent_certainty,
                "surface_form": row.surface_form,
                "name_lemma_present": row.name_lemma_present,
                "reasoning": row.reasoning,
            }
            for row in scorable
            if row.graph_asserts and not row.gold_positive
        ],
        "false_negatives": [
            {
                "row_id": row.row_id,
                "citation": row.citation,
                "veda": row.veda,
                "devata_id": row.devata_id,
                "surface_form": row.surface_form,
                "ambiguity_class": row.ambiguity_class,
                "borderline": row.borderline,
                "reasoning": row.reasoning,
            }
            for row in scorable
            if not row.graph_asserts and row.gold_positive
        ],
    }

    strict = [row for row in scorable if not row.borderline]
    report["excluding_borderline"] = {
        "rows": len(strict),
        "overall": score_rows(strict).as_dict(),
        "by_path": {
            name: score_rows([row for row in strict if row.path_group == name]).as_dict()
            for name in sorted({row.path_group for row in strict})
        },
    }

    uniform = [row for row in scorable if row.stratum.endswith("_uniform")]
    report["uniform_strata"] = {
        "rows": len(uniform),
        "overall": score_rows(uniform).as_dict(),
        "by_path": {
            name: score_rows([row for row in uniform if row.path_group == name]).as_dict()
            for name in sorted({row.path_group for row in uniform})
        },
    }

    if live is not None:
        drifted = reconcile(rows, live)
        report["live_graph"] = {
            "edges": len(live),
            "rows_disagreeing_with_frozen_snapshot": len(drifted),
            "drifted_row_ids": drifted[:20],
        }
    return report


def print_report(report: dict[str, Any]) -> None:
    """The report as a person reads it."""
    print("=" * 100)
    print("THEONYM MENTION LAYER -- MEASURED AGAINST theonym_mention_gold_v1")
    print("=" * 100)
    print(
        f"gold rows {report['gold_rows']}   scorable {report['scorable_rows']}   "
        f"excluded AMBIGUOUS {len(report['excluded_ambiguous'])}   "
        f"borderline (kept, flagged) {report['borderline_rows']}"
    )
    if "live_graph" in report:
        live = report["live_graph"]
        print(
            f"live graph: {live['edges']} MENTIONS_DEVATA edges; "
            f"{live['rows_disagreeing_with_frozen_snapshot']} gold rows disagree with the "
            "frozen snapshot"
        )

    def show(title: str, blob: dict[str, Any]) -> None:
        score = Score(tp=blob["tp"], fp=blob["fp"], fn=blob["fn"], tn=blob["tn"])
        print(_line(title, score))

    print("\n--- HEADLINE: strict deity-reference target (gold_label) ---")
    show("OVERALL (stratified, diagnostic)", report["overall"])
    for name, blob in report["by_path"].items():
        show(f"path: {name}", blob)

    print("\n--- Same rows, weaker target: is the name-lemma in the verse at all? ---")
    show("OVERALL", report["overall_name_lemma_target"])
    for name, blob in report["by_path_name_lemma_target"].items():
        show(f"path: {name}", blob)

    print(
        "\n--- Uniform strata only: a plain uniform draw from the live edge set. "
        "Precision here is\n    the unbiased corpus estimate; these strata contain no "
        "negatives, so recall is not estimable. ---"
    )
    show(f"OVERALL ({report['uniform_strata']['rows']} rows)", report["uniform_strata"]["overall"])
    for name, blob in report["uniform_strata"]["by_path"].items():
        show(f"path: {name}", blob)

    print("\n--- Per Veda ---")
    for name, blob in report["by_veda"].items():
        show(name, blob)
    if report["by_veda_withheld"]:
        print(f"  withheld for n < {MIN_SUPPORT}: {report['by_veda_withheld']}")

    print("\n--- Per extraction path, edges only (precision of what the layer asserts) ---")
    for name, blob in report["by_extraction_path_positives_only"].items():
        show(name, blob)

    print(f"\n--- Per deity (only where n >= {MIN_SUPPORT}) ---")
    for name, blob in report["by_deity"].items():
        show(name.replace("VG:DEVATA:", ""), blob)
    withheld = report["by_deity_withheld"]
    if withheld:
        print(f"  too few rows for a per-deity figure ({len(withheld)} deities):")
        print(
            "    "
            + ", ".join(
                f"{key.replace('VG:DEVATA:', '')}={value}"
                for key, value in sorted(withheld.items())
            )
        )

    print("\n--- Errors by the layer's own confidence signal (referent_certainty) ---")
    for name, blob in report["by_referent_certainty"].items():
        score = Score(tp=blob["tp"], fp=blob["fp"], fn=blob["fn"], tn=blob["tn"])
        rate = None if score.predicted_positive == 0 else score.fp / score.predicted_positive
        print(
            f"  {name or '(none)':<22} asserted={score.predicted_positive:4d} "
            f"wrong={score.fp:3d}  error rate {_fmt(rate)}"
        )

    failure = report["ambiguity_failure"]
    print("\n--- Ambiguity failure rate (ambiguous common nouns) ---")
    print(
        f"  rows {failure['rows_on_ambiguous_common_nouns']}   asserted {failure['asserted']}   "
        f"wrong sense {failure['wrong_sense']}   rate {_fmt(failure['wrong_sense_rate'])}"
    )
    for example in failure["examples"][:6]:
        print(
            f"    {example['row_id']} {example['citation']} "
            f"{example['devata_id'].replace('VG:DEVATA:', '')} "
            f"[{example['surface_form']}]"
        )

    print("\n--- Excluding every row flagged borderline ---")
    show(f"OVERALL ({report['excluding_borderline']['rows']} rows)",
         report["excluding_borderline"]["overall"])
    for name, blob in report["excluding_borderline"]["by_path"].items():
        show(f"path: {name}", blob)

    errors = report["errors"]
    print(
        f"\n--- {len(errors['false_positives'])} false positives, "
        f"{len(errors['false_negatives'])} false negatives ---"
    )
    for row in errors["false_positives"][:15]:
        print(f"  FP {row['row_id']} {row['citation']:<18} "
              f"{row['devata_id'].replace('VG:DEVATA:', ''):<20} "
              f"{row['referent_certainty'].replace('DEITY_', ''):<10} {row['surface_form']}")
    for row in errors["false_negatives"][:15]:
        print(f"  FN {row['row_id']} {row['citation']:<18} "
              f"{row['devata_id'].replace('VG:DEVATA:', ''):<20} "
              f"{row['ambiguity_class']:<20} {row['surface_form']}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gold", type=pathlib.Path, default=GOLD_PATH, help="path to the gold JSONL"
    )
    parser.add_argument("--json", type=pathlib.Path, help="also write the report as JSON")
    parser.add_argument(
        "--no-graph",
        action="store_true",
        help="skip the live-graph reconciliation and score the frozen snapshot only",
    )
    parser.add_argument(
        "--frozen",
        action="store_true",
        help=(
            "score the graph_asserts column as frozen in the gold set, instead of the "
            "live graph. Reproduces the figure published at freeze time; use it to "
            "compare against history, not to describe the current layer."
        ),
    )
    arguments = parser.parse_args(argv)

    try:
        rows = load_gold(arguments.gold)
    except GoldSetError as error:
        print(f"gold set unusable: {error}", file=sys.stderr)
        return 2

    live: set[tuple[str, str]] | None = None
    if not arguments.no_graph:
        try:
            live = fetch_live_edges()
        except Exception as error:
            print(f"live graph unavailable ({error}); scoring the frozen snapshot", file=sys.stderr)

    # Live by default. See `refresh_from_live` for why the frozen column is the wrong
    # thing to score once the layer has moved.
    if live is not None and not arguments.frozen:
        rows = refresh_from_live(rows, live)
        print(
            "scoring the LIVE graph (pass --frozen for the freeze-time figure)",
            file=sys.stderr,
        )

    report = build_report(rows, live)
    print_report(report)
    if arguments.json:
        arguments.json.write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"\nwrote {arguments.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
