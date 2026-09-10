"""Run the Product-V1 acceptance demos against the live graph and time every route.

**Why a script and not a test.** The 23 demos of the API spec are an acceptance narrative,
not assertions: "open Indra's profile", "explain why two nodes are connected", "show the
cross-Veda matrix". A test asks whether one payload is correct; this asks whether a
frontend developer can actually build a reading page, a deity page and a graph explorer out
of the routes that exist. Those are different questions, and the second one is answered by
walking the whole list and looking at what came back.

It doubles as the latency instrument for spec §39. The target is a median normal call under
150ms and most calls under 300ms, *excluding* endpoints explicitly labelled aggregate or
census -- so those are declared in :data:`AGGREGATE_PATH_MARKERS` and reported separately
rather than quietly averaged in to flatter the median.

A demo whose route does not exist is reported ``MISSING`` and does not stop the run. That
matters: this is executed while the route surface is still being assembled, and a harness
that aborts on the first 404 tells you about one gap instead of all of them.

Usage::

    PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/api_product_demos.py
    ... --json out.json      # machine-readable, for the final report
    ... --repeat 5           # more samples per route before taking the median
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi.testclient import TestClient

from vedagraph.api.app import create_app

#: Path fragments whose endpoints are censuses or aggregates. Excluded from the "normal
#: call" latency budget because §39 excludes them by name, and included in the report
#: anyway so that excluding them cannot hide a 4-second endpoint.
AGGREGATE_PATH_MARKERS: tuple[str, ...] = (
    "/stats",
    "/insights/",
    "/graph/path",
)

#: Known-good identifiers in the frozen graph, so a demo failure means a broken route
#: rather than a typo in a key. Every one was verified against the live graph.
RV_FIRST = "VG:RV:SAK:M01:S001:V001"
RV_SUKTA = "VG:RV:SAK:M01:S001"
RV_MANDALA = "VG:RV:SAK:M01"
YV_ADHYAYA = "VG:YV:VSM:A01"
AV_KANDA = "VG:AV:SAU:K20"
SV_COLLECTION = "VG:SV:KAU:ARANYA"
INDRA = "VG:DEVATA:INDRAH"
AGNI = "VG:DEVATA:AGNIH"
SOMA = "VG:DEVATA:SOMAH"


@dataclass
class Demo:
    """One line of the acceptance narrative."""

    number: int
    name: str
    path: str
    params: dict[str, Any] = field(default_factory=dict)
    #: Set where the demo's whole point is a refusal or a partial answer, so that a 200
    #: with an empty body is a failure rather than a pass.
    expect_keys: tuple[str, ...] = ()


DEMOS: tuple[Demo, ...] = (
    Demo(1, "list four Vedas", "/api/v1/works"),
    Demo(2, "open RV 1.1.1", f"/api/v1/passages/{RV_FIRST}"),
    Demo(3, "browse an RV Sukta", f"/api/v1/passages/{RV_SUKTA}/children"),
    Demo(4, "browse YV Adhyaya 1", f"/api/v1/passages/{YV_ADHYAYA}/children"),
    Demo(5, "browse AV Kanda 20", f"/api/v1/passages/{AV_KANDA}/children"),
    Demo(6, "open Indra profile", f"/api/v1/devatas/{INDRA}"),
    Demo(7, "open Agni profile", f"/api/v1/devatas/{AGNI}"),
    Demo(8, "open Soma profile", f"/api/v1/devatas/{SOMA}"),
    Demo(
        9,
        "certain/probable/ambiguous counts",
        f"/api/v1/devatas/{SOMA}",
        expect_keys=("certainty",),
    ),
    Demo(10, "search Sanskrit", "/api/v1/search", {"q": "agnim"}),
    Demo(11, "search English", "/api/v1/search", {"q": "fever"}),
    Demo(12, "search a Devata", "/api/v1/search", {"q": "indra"}),
    Demo(13, "open a Rishi family", "/api/v1/entities/rishi_family"),
    Demo(14, "open one ritual", "/api/v1/rituals"),
    Demo(15, "open fever/condition network", "/api/v1/entities/condition"),
    Demo(16, "open one FormulaFamily", "/api/v1/entities/formula_family"),
    Demo(17, "show one RV-SV relationship", f"/api/v1/passages/{RV_FIRST}/parallels"),
    Demo(18, "graph neighbourhood (Indra)", "/api/v1/graph/neighborhood/" + INDRA),
    Demo(19, "show cross-Veda matrix", "/api/v1/insights/cross-veda"),
    Demo(20, "meaningful graph path", "/api/v1/graph/path", {"from": INDRA, "to": AGNI}),
    Demo(21, "Q10 metals response", "/api/v1/insights/metals"),
    Demo(22, "Q23 capability refusal", "/api/v1/insights/capabilities"),
    Demo(23, "Q25 ritual-object partial", "/api/v1/insights/rituals"),
    Demo(24, "reader payload", f"/api/v1/passages/{RV_FIRST}/reader"),
    Demo(25, "product statistics", "/api/v1/stats"),
    Demo(26, "SV collection browse", f"/api/v1/passages/{SV_COLLECTION}/children"),
    Demo(27, "RV mandala browse", f"/api/v1/passages/{RV_MANDALA}/children"),
    Demo(28, "AV concerns insight", "/api/v1/insights/atharvaveda/concerns"),
    Demo(29, "formula diffusion", "/api/v1/insights/formula-diffusion"),
    Demo(30, "civilization insight", "/api/v1/insights/civilization"),
    Demo(31, "material culture", "/api/v1/insights/material-culture"),
    Demo(32, "devata network", f"/api/v1/devatas/{INDRA}/network"),
    Demo(33, "devata passages", f"/api/v1/devatas/{INDRA}/passages"),
    Demo(34, "work detail (Samaveda scope)", "/api/v1/works/VG:WORK:SV:KAU"),
)


def is_aggregate(path: str) -> bool:
    return any(marker in path for marker in AGGREGATE_PATH_MARKERS)


def excerpt(payload: Any, limit: int = 220) -> str:
    """A compact one-line view of a response, for eyeballing 34 of them in a terminal."""
    try:
        text = json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        text = str(payload)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit] + "..."


def run(client: TestClient, demo: Demo, repeat: int) -> dict[str, Any]:
    durations: list[float] = []
    response = None
    for _ in range(max(1, repeat)):
        started = time.perf_counter()
        response = client.get(demo.path, params=demo.params)
        durations.append((time.perf_counter() - started) * 1000)
    assert response is not None

    status = response.status_code
    try:
        payload = response.json()
    except ValueError:  # pragma: no cover - defensive
        payload = None

    if status == 404 and isinstance(payload, dict) and payload.get("error") is None:
        verdict = "MISSING"
    elif status == 200:
        verdict = "OK"
        for key in demo.expect_keys:
            if not isinstance(payload, dict) or key not in payload:
                verdict = f"OK_MISSING_KEY:{key}"
                break
    else:
        verdict = f"HTTP_{status}"

    return {
        "number": demo.number,
        "name": demo.name,
        "path": demo.path,
        "params": demo.params,
        "status": status,
        "verdict": verdict,
        "aggregate": is_aggregate(demo.path),
        "median_ms": round(statistics.median(durations), 1),
        "min_ms": round(min(durations), 1),
        "max_ms": round(max(durations), 1),
        "excerpt": excerpt(payload),
    }


def run_explain_chain(client: TestClient, repeat: int) -> dict[str, Any]:
    """Demo 21 of the spec: explain why two nodes are connected.

    Chained rather than declared, because a relationship id cannot be written into a demo
    table. The API deliberately refuses to expose Neo4j's ``element_id`` -- it is not stable
    across a rebuild, and this graph gets rebuilt -- so the only honest way to reach the
    explain endpoint is the way a frontend must: read a neighbourhood, follow an edge id it
    was handed. That the chain works end to end is the actual claim being tested.
    """
    neighbourhood = client.get(f"/api/v1/graph/neighborhood/{INDRA}")
    if neighbourhood.status_code != 200:
        return {
            "number": 21,
            "name": "explain a relationship (chained)",
            "path": "/api/v1/graph/relationships/{id}",
            "params": {},
            "status": neighbourhood.status_code,
            "verdict": "BLOCKED_ON_NEIGHBOURHOOD",
            "aggregate": False,
            "median_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "excerpt": excerpt(neighbourhood.json()),
        }

    edges = neighbourhood.json().get("edges") or []
    if not edges:
        return {
            "number": 21,
            "name": "explain a relationship (chained)",
            "path": "/api/v1/graph/relationships/{id}",
            "params": {},
            "status": 200,
            "verdict": "NO_EDGE_TO_EXPLAIN",
            "aggregate": False,
            "median_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "excerpt": "the neighbourhood returned no edges",
        }

    relationship_id = edges[0]["id"]
    demo = Demo(
        21, "explain a relationship (chained)", f"/api/v1/graph/relationships/{relationship_id}"
    )
    result = run(client, demo, repeat)
    result["chained_from"] = f"/api/v1/graph/neighborhood/{INDRA}"
    result["relationship_id_is_not_a_neo4j_id"] = (
        not relationship_id.isdigit() and ":" not in relationship_id.split("-")[0]
    )
    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Latency over normal calls only, with the aggregates reported beside them.

    p95 over a sample this small is the 95th-percentile *of these demos*, which is a
    coverage statement about the acceptance list and not a production SLO. Named
    ``p95_ms_over_demos`` so nobody quotes it as the latter.
    """
    ok = [r for r in results if r["verdict"].startswith("OK")]
    normal = [r["median_ms"] for r in ok if not r["aggregate"]]
    aggregate = [r["median_ms"] for r in ok if r["aggregate"]]

    slowest_normal = max(
        (r for r in ok if not r["aggregate"]), key=lambda r: r["median_ms"], default=None
    )
    return {
        "demos_total": len(results),
        "demos_ok": len(ok),
        "demos_missing": sum(1 for r in results if r["verdict"] == "MISSING"),
        "demos_failing": sum(
            1 for r in results if not r["verdict"].startswith("OK") and r["verdict"] != "MISSING"
        ),
        "normal_median_ms": round(statistics.median(normal), 1) if normal else None,
        "normal_p95_ms_over_demos": (
            round(sorted(normal)[min(len(normal) - 1, int(0.95 * len(normal)))], 1)
            if normal
            else None
        ),
        "normal_max_ms": round(max(normal), 1) if normal else None,
        "normal_over_300ms": sorted(
            r["path"] for r in ok if not r["aggregate"] and r["median_ms"] > 300
        ),
        "aggregate_median_ms": round(statistics.median(aggregate), 1) if aggregate else None,
        "aggregate_max_ms": round(max(aggregate), 1) if aggregate else None,
        "slowest_normal_endpoint": (
            {"path": slowest_normal["path"], "median_ms": slowest_normal["median_ms"]}
            if slowest_normal
            else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=3, help="Samples per route.")
    parser.add_argument("--json", type=Path, default=None, help="Write full results here.")
    parser.add_argument("--only", type=int, nargs="*", help="Run only these demo numbers.")
    args = parser.parse_args()

    demos = [d for d in DEMOS if not args.only or d.number in args.only]

    app = create_app()
    with TestClient(app) as client:
        ready = client.get("/ready")
        if ready.status_code != 200:
            print(f"NOT READY ({ready.status_code}): {excerpt(ready.json())}")
            return 2
        print(f"ready: {ready.json()['ready']}\n")
        results = [run(client, demo, args.repeat) for demo in demos]
        if not args.only:
            results.append(run_explain_chain(client, args.repeat))

    width = max(len(r["name"]) for r in results)
    for r in results:
        flag = "AGG" if r["aggregate"] else "   "
        print(
            f"{r['number']:>3}. {r['name']:<{width}}  {flag} "
            f"{r['median_ms']:>7.1f}ms  {r['verdict']}"
        )
        print(f"     {r['excerpt']}")

    summary = summarize(results)
    print("\n=== summary ===")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    if args.json:
        args.json.write_text(
            json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nwrote {args.json}")

    return 0 if summary["demos_failing"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
