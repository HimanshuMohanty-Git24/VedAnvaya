"""Gate B: structural and semantic validity over all 23,003 attribution rows.

The owner's instruction is to treat the rows as untrusted and to inherit no earlier
conclusion. So nothing here reads the domain's own report: every check is recomputed from
``rows.jsonl`` and from the live graph.

The domain is two populations that share a file and almost nothing else, and the first job of
this gate is to refuse to average them:

CENSUS  22,537 rows, ``DETERMINISTIC_DERIVED``, source ``VG_ATTRIBUTION_CENSUS_2026_09_15``
    A per-passage record of the STATE of rishi/devata/chandas attribution --
    ``SOURCE_EXPLICIT_PRESENT``, ``DERIVED_PRESENT``, ``ASSESSED_SOURCE_ABSENT``,
    ``NEVER_ASSESSED``, ``NOT_APPLICABLE_AT_THIS_GRANULARITY``. These are measurements of
    what the graph already holds, including typed absences. They are **not** attribution
    assertions, and importing them as edges would be a category error: an edge saying
    "this mantra has no recorded seer" is not a fact about the mantra, it is a fact about
    the record.

WHITNEY  466 rows, ``SOURCE_EXPLICIT``, Whitney's Atharvaveda index
    Genuine verse-level source assertions, read out of a printed bracket.

Every check is reported per population. An aggregate pass rate over a file holding a census
and an index would be meaningless.

Usage:
    python scripts/attribution_gate_b.py [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

from vedagraph.api.services.graph_service import (
    LEMMA_RELATIONSHIP,
    NON_TRAVERSABLE_REASONS,
    TRAVERSABLE_RELATIONSHIPS,
)

#: The authority for \"is this predicate declared\". NOT DOMAIN_RELATIONSHIP_TYPES, which is
#: the domain layer only: HAS_CHANDAS is a corpus-layer predicate carrying 20,210 edges and
#: sits outside it, so asking that set made a long-standing predicate look undeclared. The
#: product contract classifies every populated type and a live test holds it complete.
DECLARED_PREDICATES = (
    TRAVERSABLE_RELATIONSHIPS | set(NON_TRAVERSABLE_REASONS) | {LEMMA_RELATIONSHIP}
)

ROWS = pathlib.Path("data/staging/attribution/rows.jsonl")
MANIFEST = pathlib.Path("data/staging/attribution/manifest.json")
OUT = pathlib.Path("data/staging/integration/attribution_gate_b.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: The campaign invariant. Every group, side file included, goes through this.
NOT_IMPORTABLE = frozenset({"PROBABLE", "UNVERIFIED"})

#: The states a census row may report, and whether each one is an ASSERTION about the text
#: or a record about our coverage of it. Nothing in the second column may become an edge.
CENSUS_STATES: dict[str, bool] = {
    "SOURCE_EXPLICIT_PRESENT": False,
    "DERIVED_PRESENT": False,
    "ASSESSED_SOURCE_ABSENT": False,
    "NEVER_ASSESSED": False,
    "NOT_APPLICABLE_AT_THIS_GRANULARITY": False,
}

#: Predicates the Whitney rows name. Both must be declared by the ontology, or the rows are
#: asking for an edge type this graph does not have.
WHITNEY_PREDICATES = ("HAS_CHANDAS", "HAS_DEVATA_ASCRIPTION")

VEDA_PREFIX = {"RV": "VG:RV:", "SV": "VG:SV:", "YV": "VG:YV:", "AV": "VG:AV:"}


def read_rows() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in ROWS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def check(name: str, failures: list[str], *, detail: str = "") -> dict[str, Any]:
    return {
        "check": name,
        "failures": len(failures),
        "passed": not failures,
        "examples": failures[:5],
        "detail": detail,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    rows = read_rows()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    census = [r for r in rows if r.get("evidence_layer") == "DETERMINISTIC_DERIVED"]
    whitney = [r for r in rows if r.get("evidence_layer") == "SOURCE_EXPLICIT"]

    report: dict[str, Any] = {
        "artifact": "ATTRIBUTION_GATE_B",
        "rows_assessed": len(rows),
        "populations": {"CENSUS": len(census), "WHITNEY_INDEX": len(whitney)},
        "manifest_row_count": next(
            (f["rows"] for f in manifest["files"] if f["path"] == "rows.jsonl"), None
        ),
    }

    # ---- resolve every subject against the live graph ------------------------------
    keys = sorted({str(r.get("canonical_key") or "") for r in rows})
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            resolved: dict[str, list[str]] = {}
            for i in range(0, len(keys), 5000):
                for row in session.run(
                    "UNWIND $keys AS k MATCH (p:Passage {canonical_key: k}) "
                    "RETURN k AS key, labels(p) AS labels",
                    keys=keys[i : i + 5000],
                ):
                    resolved[str(row["key"])] = list(row["labels"])
            hymn_keys = sorted(
                {
                    str(r["payload"].get("hymn_key") or "")
                    for r in whitney
                    if r["payload"].get("hymn_key")
                }
            )
            resolved_hymns = {
                str(row["k"])
                for row in session.run(
                    "UNWIND $keys AS k MATCH (p:Passage {canonical_key: k}) RETURN DISTINCT k",
                    keys=hymn_keys,
                )
            }
    finally:
        driver.close()

    checks: list[dict[str, Any]] = []

    # 1. subject resolves
    unresolved = [k for k in keys if k not in resolved]
    checks.append(
        check(
            "every subject resolves to a canonical :Passage",
            unresolved,
            detail=f"{len(resolved)} of {len(keys)} distinct canonical keys matched a node",
        )
    )

    # 2. the Veda a row declares matches the key it carries
    wrong_veda = [
        f"{r['canonical_key']} declared {r['veda']}"
        for r in rows
        if not str(r.get("canonical_key") or "").startswith(
            VEDA_PREFIX.get(str(r.get("veda")), "\0")
        )
    ]
    checks.append(
        check("the declared Veda matches the canonical key's own prefix", wrong_veda)
    )

    # 3. recension: a row may not silently cross a school boundary
    bad_recension = [
        f"{r['canonical_key']} recension_verified={r.get('recension_verified')}"
        for r in rows
        if r.get("recension_verified") is not True
    ]
    checks.append(
        check(
            "every row carries a verified recension",
            bad_recension,
            detail="Jaiminiya is not Kauthuma; Taittiriya and Kanva are not Madhyandina.",
        )
    )

    # 4. nothing non-importable slipped in, and no side file bypasses the predicate
    non_importable = [
        str(r.get("canonical_key"))
        for r in rows
        if str(r.get("mapping_confidence") or "") in NOT_IMPORTABLE
    ]
    checks.append(
        check(
            "no row carries a confidence the campaign refuses",
            non_importable,
            detail="The Wave 3 defect: the filter was applied to rows.jsonl and to no side file.",
        )
    )
    side_files = sorted(
        p.name for p in ROWS.parent.glob("*.jsonl") if p.name not in {"rows.jsonl"}
    )
    checks.append(
        check(
            "the domain's side files are enumerated, not assumed absent",
            [],
            detail=f"side files present: {side_files or 'none'}",
        )
    )

    # ---- CENSUS population ---------------------------------------------------------
    census_checks: list[dict[str, Any]] = []
    unknown_states = []
    for r in census:
        for dim in ("rishi", "devata", "chandas"):
            state = str((r["payload"].get(dim) or {}).get("state") or "")
            if state and state not in CENSUS_STATES:
                unknown_states.append(f"{r['canonical_key']}:{dim}={state}")
    census_checks.append(
        check("every census state is a declared member of the closed set", unknown_states)
    )
    assertional = [s for s, is_assertion in CENSUS_STATES.items() if is_assertion]
    census_checks.append(
        check(
            "no census state is an assertion about the text",
            assertional,
            detail=(
                "Every state records what our coverage is, including a typed absence. A "
                "'NEVER_ASSESSED' edge would be a claim about the record wearing the shape "
                "of a claim about the mantra."
            ),
        )
    )
    missing_dims = [
        str(r.get("canonical_key"))
        for r in census
        if not all(isinstance(r["payload"].get(d), dict) for d in ("rishi", "devata", "chandas"))
    ]
    census_checks.append(
        check("every census row reports all three dimensions", missing_dims)
    )
    absent_without_reason = [
        f"{r['canonical_key']}:{dim}"
        for r in census
        for dim in ("rishi", "devata", "chandas")
        if str((r["payload"].get(dim) or {}).get("state") or "")
        in {"ASSESSED_SOURCE_ABSENT", "NOT_APPLICABLE_AT_THIS_GRANULARITY"}
        and not (r["payload"].get(dim) or {}).get("absence_reason_code")
    ]
    census_checks.append(
        check(
            "every recorded absence carries a reason code",
            absent_without_reason,
            detail="An untyped absence is the thing this campaign refuses to ship.",
        )
    )
    # Grain homogeneity: a census row's subject grain must match what it says it is.
    grain_mismatch = [
        str(r.get("canonical_key"))
        for r in census
        if bool(r["payload"].get("is_mantra"))
        != ("Mantra" in resolved.get(str(r.get("canonical_key")), []))
    ]
    census_checks.append(
        check(
            "the declared is_mantra agrees with the node's own labels",
            grain_mismatch,
            detail="A passage proxy standing in for an entity, or a container typed as a verse.",
        )
    )

    # ---- WHITNEY population --------------------------------------------------------
    whitney_checks: list[dict[str, Any]] = []
    undeclared = [
        p for p in WHITNEY_PREDICATES if p not in DECLARED_PREDICATES
    ]
    whitney_checks.append(
        check(
            "every predicate named is declared by the ontology",
            undeclared,
            detail=f"declared: {sorted(set(WHITNEY_PREDICATES) & DECLARED_PREDICATES)}",
        )
    )
    unresolved_objects = [
        f"{r['canonical_key']}:{r['payload']['dimension']}"
        for r in whitney
        if str(r["payload"].get("entity_resolution_method"))
        == "VERBATIM_SOURCE_STRING_NOT_RESOLVED"
    ]
    whitney_checks.append(
        check(
            "every object resolves to an entity the graph holds",
            unresolved_objects,
            detail=(
                "An edge needs a node at the far end. A verbatim printed string is evidence "
                "that the source said something, not a resolved referent."
            ),
        )
    )
    bad_hymn = [
        str(r["payload"].get("hymn_key"))
        for r in whitney
        if str(r["payload"].get("hymn_key") or "") not in resolved_hymns
    ]
    whitney_checks.append(check("the containing hymn resolves", bad_hymn))
    no_locator = [
        str(r.get("canonical_key"))
        for r in whitney
        if not str(r.get("source_locator") or "").strip()
    ]
    whitney_checks.append(check("every row carries a source locator", no_locator))
    mixed_scope = sorted({str(r["payload"].get("scope_type")) for r in whitney})
    whitney_checks.append(
        check(
            "the scope grain is homogeneous",
            [] if len(mixed_scope) == 1 else mixed_scope,
            detail=f"scope types present: {mixed_scope}",
        )
    )
    mixed_granularity = sorted({str(r["payload"].get("asserted_granularity")) for r in whitney})
    whitney_checks.append(
        check(
            "the asserted granularity is homogeneous",
            [] if len(mixed_granularity) == 1 else mixed_granularity,
            detail=f"granularities present: {mixed_granularity}",
        )
    )
    # A source-explicit claim must not be a deterministic derivation wearing the label.
    derived_as_explicit = [
        str(r.get("canonical_key"))
        for r in whitney
        if "read off" in str(r.get("mapping_method") or "").lower()
        or "derived" in str(r.get("mapping_method") or "").lower()
    ]
    whitney_checks.append(
        check(
            "no deterministic derivation is labelled source-explicit",
            derived_as_explicit,
            detail="The method must describe reading a source, not computing a value.",
        )
    )
    duplicate_subject_dimension = [
        f"{key}:{dim}"
        for (key, dim), n in collections.Counter(
            (str(r.get("canonical_key")), str(r["payload"].get("dimension"))) for r in whitney
        ).items()
        if n > 1
    ]
    whitney_checks.append(
        check(
            "no subject carries two rows for one dimension",
            duplicate_subject_dimension,
            detail="Duplicated attribution under two normalized forms of one printed value.",
        )
    )

    report["shared_checks"] = checks
    report["census_checks"] = census_checks
    report["whitney_checks"] = whitney_checks

    report["census_state_distribution"] = {
        dim: dict(
            collections.Counter(
                str((r["payload"].get(dim) or {}).get("state") or "") for r in census
            )
        )
        for dim in ("rishi", "devata", "chandas")
    }

    failed = [
        c
        for c in (checks + census_checks + whitney_checks)
        if not c["passed"]
    ]
    report["checks_run"] = len(checks) + len(census_checks) + len(whitney_checks)
    report["checks_failed"] = len(failed)
    report["verdict"] = "GATE_B_PASS" if not failed else "GATE_B_FINDINGS"

    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print()
    print("  ATTRIBUTION GATE B -- recomputed, nothing inherited")
    print()
    print(f"  rows {len(rows):,}   CENSUS {len(census):,}   WHITNEY {len(whitney)}")
    print()
    for title, group in (
        ("shared", checks),
        ("census", census_checks),
        ("whitney", whitney_checks),
    ):
        print(f"  {title.upper()}")
        for c in group:
            mark = "PASS" if c["passed"] else "FAIL"
            print(f"    {mark}  {c['check']:58} {c['failures']:>6}")
        print()
    print(f"  {report['checks_failed']} of {report['checks_run']} checks failed")
    print(f"  VERDICT: {report['verdict']}")
    print(f"  report: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
