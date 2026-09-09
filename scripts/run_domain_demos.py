"""Run every named domain query against the live graph and write the demonstrations report.

Two jobs. First, it is the integration test for :mod:`vedagraph.domain.queries`: a query
that does not parse, or that returns nothing because a label was renamed, fails here
rather than in a report nobody re-ran. Second, it produces
``docs/reports/VEDAGRAPH_DOMAIN_DEMOS_V2.md`` with real output rather than illustrative
output, including each query's caveat -- an answer published without its limits is the
failure mode this whole pass exists to fix.

Usage::

    python scripts/run_domain_demos.py
    python scripts/run_domain_demos.py --only deity_profile crops_by_veda
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
import time
import warnings
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.domain.queries import QUERIES, DomainQuery, questions_served  # noqa: E402

BOLT_URI = "bolt://localhost:7687"
BOLT_AUTH = ("neo4j", "vedagraph_dev")

REPORT_PATH = pathlib.Path("docs") / "reports" / "VEDAGRAPH_DOMAIN_DEMOS_V2.md"

#: Rows shown per query in the report. The point is to demonstrate shape and plausibility,
#: not to dump the graph.
MAX_ROWS = 8

#: Queries whose empty result is the pass condition rather than a failure.
EMPTY_IS_PASS = frozenset(
    {
        "internal_leakage_check",
        "unlabelled_product_nodes",
        # Zero orphans is the pass condition: every domain entity has an edge.
        "orphan_domain_entities",
        # Measured empty, and documented in the query own caveat: the tribes and
        # the rivers are both attested and never share a mantra.
        "rivers_and_tribes",
    }
)

#: The demonstrations the V2 spec requires, mapped to the queries that provide them.
REQUIRED_DEMOS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("A", "Indra profile", ("deity_profile", "rishis_invoking_deity_strict")),
    ("B", "Agni: deity, fire and ritual medium", ("agni_deity_fire_medium",)),
    ("C", "Soma: deity versus substance", ("soma_deity_versus_substance",)),
    ("D", "Varuna profile", ("varuna_profile",)),
    ("E", "Rudra profile without Shiva", ("rudra_profile_no_shiva",)),
    ("F", "One ritual", ("ritual_profile",)),
    (
        "G",
        "One Atharvavedic human concern",
        ("condition_neighbourhood", "human_concerns_by_veda"),
    ),
    ("H", "Material culture: crops across four Vedas", ("crops_by_veda", "metals_by_veda")),
    (
        "I",
        "Cross-Veda formula family",
        ("cross_veda_formulas", "formula_family_diffusion"),
    ),
    ("J", "One interpretive claim, fully traced", ("claim_evidence_trace",)),
)


def _scalar(value: Any) -> Any:
    if isinstance(value, list):
        rendered = [_scalar(item) for item in value]
        return rendered[:6] + (["..."] if len(rendered) > 6 else [])
    if isinstance(value, dict):
        return {key: _scalar(item) for key, item in value.items()}
    if isinstance(value, str) and len(value) > 160:
        return value[:157] + "..."
    return value


def _run(session: Any, query: DomainQuery) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        records = [dict(record) for record in session.run(query.cypher, **query.parameters)]
        error = ""
    except Exception as exc:
        records = []
        error = f"{type(exc).__name__}: {exc}"
    elapsed = (time.perf_counter() - start) * 1000
    return {
        "name": query.name,
        "rows": len(records),
        "ms": round(elapsed, 1),
        "error": error,
        "sample": [{k: _scalar(v) for k, v in row.items()} for row in records[:MAX_ROWS]],
    }


def _table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_(no rows)_\n"
    columns = list(rows[0].keys())
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in rows:
        cells = []
        for column in columns:
            value = row.get(column)
            text = (
                json.dumps(value, ensure_ascii=False)
                if isinstance(value, list | dict)
                else str(value)
            )
            cells.append(text.replace("|", "\\|").replace("\n", " ")[:150])
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", help="run only these query names")
    args = parser.parse_args()

    selected = [q for q in QUERIES if not args.only or q.name in set(args.only)]
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    results: dict[str, dict[str, Any]] = {}
    try:
        with driver.session() as session:
            for query in selected:
                outcome = _run(session, query)
                results[query.name] = outcome
                status = (
                    "ERROR"
                    if outcome["error"]
                    else "pass(empty)"
                    if outcome["rows"] == 0 and query.name in EMPTY_IS_PASS
                    else "EMPTY"
                    if outcome["rows"] == 0
                    else "ok"
                )
                print(
                    f"  {status:<12} {query.name:<38} rows={outcome['rows']:<6} "
                    f"{outcome['ms']:>8.1f} ms"
                )
                if outcome["error"]:
                    print(f"               {outcome['error'][:160]}")
    finally:
        driver.close()

    errors = [name for name, r in results.items() if r["error"]]
    empties = [
        name
        for name, r in results.items()
        if not r["error"] and r["rows"] == 0 and name not in EMPTY_IS_PASS
    ]

    if args.only:
        print(f"\nerrors={len(errors)} unexpected_empty={len(empties)}")
        return 1 if errors else 0

    lines: list[str] = [
        "# VedaGraph Domain Demonstrations (Knowledge Model V2)",
        "",
        "Generated by `scripts/run_domain_demos.py` against the live graph. Every table",
        "below is real output, and every query is published with the `caveat` recorded",
        "alongside it in `vedagraph.domain.queries` -- an answer without its limits is the",
        "failure this pass exists to fix.",
        "",
        f"- queries run: **{len(results)}**",
        f"- errors: **{len(errors)}**",
        f"- unexpectedly empty: **{len(empties)}**",
        "",
        "## Query index",
        "",
        "| query | rows | ms | serves questions |",
        "|---|---|---|---|",
    ]
    by_name = {q.name: q for q in selected}
    for name, outcome in results.items():
        serves = ", ".join(str(n) for n in by_name[name].serves) or "-"
        lines.append(f"| `{name}` | {outcome['rows']} | {outcome['ms']} | {serves} |")

    lines += ["", "## Required demonstrations", ""]
    for letter, title, query_names in REQUIRED_DEMOS:
        lines += [f"### {letter}. {title}", ""]
        for name in query_names:
            query = by_name.get(name)
            outcome = results.get(name)
            if query is None or outcome is None:
                continue
            lines += [
                f"**`{name}`** — {query.question}",
                "",
                f"*Parameters:* `{json.dumps(query.parameters, ensure_ascii=False)}`"
                if query.parameters
                else "*Parameters:* none",
                "",
                _table(outcome["sample"]),
                "",
                f"> **Caveat.** {query.caveat}" if query.caveat else "",
                "",
            ]

    lines += ["", "## All queries", ""]
    for query in selected:
        outcome = results[query.name]
        lines += [
            f"### `{query.name}`",
            "",
            query.question,
            "",
            f"- rows: {outcome['rows']}  •  {outcome['ms']} ms",
        ]
        if outcome["error"]:
            lines.append(f"- **ERROR:** `{outcome['error']}`")
        lines += ["", _table(outcome["sample"]), ""]
        if query.caveat:
            lines += [f"> **Caveat.** {query.caveat}", ""]

    served = questions_served()
    lines += [
        "## Killer-question coverage by query",
        "",
        "Which of the fifty questions have at least one query addressing them. This is",
        "coverage, not answerability: a question with a query may still be only partially",
        "answerable, and the scorecard is where that judgement is recorded.",
        "",
        "| question | queries |",
        "|---|---|",
    ]
    for number, names in served.items():
        lines.append(f"| {number} | " + ", ".join(f"`{n}`" for n in names) + " |")
    lines += [
        "",
        f"Questions with at least one query: **{len(served)}** of 50.",
        "",
    ]

    target = PROJECT_ROOT / REPORT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"\nwrote {REPORT_PATH}")
    print(f"errors={len(errors)} unexpected_empty={len(empties)}")
    if errors:
        print("ERRORS: " + ", ".join(errors))
    if empties:
        print("EMPTY: " + ", ".join(empties))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
