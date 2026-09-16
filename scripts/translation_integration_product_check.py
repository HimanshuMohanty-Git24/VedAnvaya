#!/usr/bin/env python3
"""Phase K: what a visitor is actually told, sampled across every class this round created.

A readback proves the data landed. It cannot prove the product says something true about
it, and the two have come apart in this repository before: a dependency system read the
current artifact while the browser downloaded 28 wrong labels. So this walks the live HTTP
API -- not the service objects -- for one verse of each class, and asserts on the payload a
client receives.

Two sentences must never be produced and both are checked as prohibitions rather than as
the absence of a positive:

* a verse a range translation covers must not be told that no translation covers it;
* a Samavedic verse showing Griffith's Rigvedic English must not be presented as having an
  independent Samaveda translation.

Run with the API served on 127.0.0.1:8000:
    python scripts/translation_integration_product_check.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Final

import translation_integration_common as T

BASE: Final = "http://127.0.0.1:8000/api/v1"

#: One verse per public class, named rather than sampled at random, so a re-run inspects
#: the same rows and a regression is attributable.
CASES: Final[tuple[dict[str, Any], ...]] = (
    {
        "label": "1. ordinary source-explicit translation",
        "key": "VG:AV:SAU:K03:S009:V004",
        "expect": {
            "coverage_kind": "DEDICATED_TRANSLATION",
            "language": "en",
            "is_this_passages_own": True,
            "independent_translation": True,
            "disclosure": None,
        },
    },
    {
        "label": "2. AV Wayback-recovered translation",
        "key": "VG:AV:SAU:K20:S001:V001",
        "expect": {"coverage_kind": "DEDICATED_TRANSLATION", "language": "en"},
        "expect_source_contains": "WAYBACK",
    },
    {
        "label": "3. YV verified forced address",
        "key": "VG:YV:VSM:A06:V023",
        "expect": {
            "coverage_kind": "DEDICATED_TRANSLATION",
            "language": "en",
            "independent_translation": True,
        },
    },
    {
        "label": "4. RV MANTRA_RANGE anchor",
        "key": "VG:RV:SAK:M01:S065:V001",
        "expect": {
            "coverage_kind": "RANGE_TRANSLATION",
            "is_this_passages_own": True,
            "language": "en",
        },
        "expect_span_at_least": 2,
    },
    {
        "label": "5. RV MANTRA_RANGE secondary verse",
        "key": "VG:RV:SAK:M01:S065:V002",
        "expect": {
            "coverage_kind": "RANGE_TRANSLATION",
            "is_this_passages_own": False,
            "language": "en",
        },
        "expect_anchor": "VG:RV:SAK:M01:S065:V001",
        "expect_span_at_least": 2,
    },
    {
        "label": "6. Samaveda reused rendering",
        "key": None,  # resolved from the plan: the first Samavedic reuse node
        "resolve": "first_sv_reuse",
        "expect": {
            "coverage_kind": "REUSED_RENDERING",
            "language": "en",
            "independent_translation": False,
            "reused_from_veda": "RV",
        },
        "expect_disclosure_contains": "reused",
    },
    {
        "label": "7. Latin / non-English row",
        "key": "VG:AV:SAU:K20:S136:V001",
        "expect": {"language": "la", "independent_translation": True},
        "expect_disclosure_contains": "Latin",
    },
    {
        "label": "8. withheld forced address",
        "key": "VG:YV:VSM:A20:V085",
        "expect_no_translation": True,
    },
    {
        "label": "9. uncovered verse",
        "key": "VG:RV:SAK:M01:S179:V001",
        "expect_no_translation": True,
    },
    {
        "label": "10. existing pre-import translation",
        "key": "VG:RV:SAK:M01:S001:V001",
        "expect": {
            "coverage_kind": "DEDICATED_TRANSLATION",
            "language": "en",
            "independent_translation": True,
            "disclosure": None,
        },
        "expect_source_contains": "WIKISOURCE",
    },
)

#: Sentences the product must not produce about a verse that is in fact covered.
FORBIDDEN_WHEN_COVERED: Final[tuple[str, ...]] = (
    "No released translation covers this passage",
    "No translation of any kind reaches this",
    "No translation is aligned to this verse",
)


def get(path: str) -> dict[str, Any]:
    url = f"{BASE}{path}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return {"_http_error": error.code, "_url": url}


def encoded(key: str) -> str:
    return urllib.parse.quote(key, safe="")


def _first_sv_reuse(plan: dict[str, Any]) -> str:
    for node in sorted(plan["nodes_detail"], key=lambda n: n["attach_to_canonical_key"]):
        if node["veda"] == "SV" and node["properties"].get("reuse_kind"):
            return str(node["attach_to_canonical_key"])
    raise SystemExit("no Samavedic reuse node in the plan")


def check_case(case: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    key = case["key"] or _first_sv_reuse(plan)
    reader = get(f"/passages/{encoded(key)}/reader")
    if "_http_error" in reader:
        return {"label": case["label"], "key": key, "failures": [f"HTTP {reader['_http_error']}"]}

    block = reader["translations"]
    items = block.get("items") or []
    caveats = " ".join(c["text"] for c in block.get("caveats") or [])
    failures: list[str] = []

    if case.get("expect_no_translation"):
        if items:
            failures.append(f"expected no translation, got {len(items)}")
        if block["data_status"] == "SUPPORTED":
            failures.append("an empty translation set must not claim SUPPORTED")
        if not caveats:
            failures.append("an empty translation set must carry a caveat")
        return {
            "label": case["label"],
            "key": key,
            "translations": 0,
            "data_status": block["data_status"],
            "caveat": caveats[:200],
            "failures": failures,
        }

    if not items:
        return {
            "label": case["label"],
            "key": key,
            "failures": ["expected a translation, got none"],
            "caveat": caveats[:200],
        }

    row = items[0]
    for field, want in (case.get("expect") or {}).items():
        got = row.get(field)
        if got != want:
            failures.append(f"{field}: expected {want!r}, got {got!r}")

    if case.get("expect_anchor") and row.get("anchor_canonical_key") != case["expect_anchor"]:
        failures.append(
            f"anchor: expected {case['expect_anchor']}, got {row.get('anchor_canonical_key')}"
        )
    span = len(row.get("covers_canonical_keys") or [])
    if case.get("expect_span_at_least") and span < case["expect_span_at_least"]:
        failures.append(f"span: expected at least {case['expect_span_at_least']}, got {span}")
    if case.get("expect_disclosure_contains"):
        text = (row.get("disclosure") or "").lower()
        if case["expect_disclosure_contains"].lower() not in text:
            failures.append(
                f"disclosure must mention {case['expect_disclosure_contains']!r}: "
                f"{row.get('disclosure')!r}"
            )
    if case.get("expect_source_contains"):
        source = str(row.get("source_id") or "")
        if case["expect_source_contains"] not in source:
            failures.append(
                f"source_id must contain {case['expect_source_contains']!r}, got {source!r}"
            )

    # The two prohibitions, checked on any covered verse.
    for sentence in FORBIDDEN_WHEN_COVERED:
        if sentence.lower() in caveats.lower():
            failures.append(f"a covered verse is told {sentence!r}")

    if row.get("coverage_kind") == "REUSED_RENDERING":
        if row.get("independent_translation"):
            failures.append("a reused rendering claims independent_translation")
        if not row.get("reused_from_passage_key"):
            failures.append("a reused rendering does not name its source passage")
        if not row.get("reused_from_translation_id"):
            failures.append("a reused rendering does not name the translation it reuses")
    if row.get("language") != "en" and not row.get("disclosure"):
        failures.append("a non-English rendering carries no disclosure")

    return {
        "label": case["label"],
        "key": key,
        "translations": len(items),
        "coverage_kind": row.get("coverage_kind"),
        "language": row.get("language"),
        "language_name": row.get("language_name"),
        "is_this_passages_own": row.get("is_this_passages_own"),
        "independent_translation": row.get("independent_translation"),
        "anchor": row.get("anchor_canonical_key"),
        "span": span,
        "source_id": row.get("source_id"),
        "reused_from": row.get("reused_from_citation"),
        "disclosure": (row.get("disclosure") or "")[:160] or None,
        "caveat": caveats[:200] or None,
        "failures": failures,
    }


def ask_evidence_check() -> dict[str, Any]:
    """Whether Ask's evidence packet discloses the reuse and the span.

    Built in-process from the real retriever and the real packet builder, not by asking
    ``/ask``. The disclosure is a property of the evidence, and asserting it on the packet
    is deterministic and free; asserting it in generated prose would be testing the model
    rather than the product, and would burn a daily quota to do it.
    """
    import os

    from dotenv import load_dotenv

    load_dotenv(str(T.REPO / ".env"))
    sys.path.insert(0, str(T.REPO / "src"))
    from vedagraph.api.ask.evidence import build_evidence_packet
    from vedagraph.api.ask.planner import QueryPlan
    from vedagraph.api.ask.retriever import retrieve
    from vedagraph.api.config import ApiSettings
    from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

    os.environ.setdefault("VEDAGRAPH_LLM_PROVIDER", "none")
    plan = json.loads((T.INTEGRATION / "translation_import_plan.json").read_text("utf-8"))
    repository = Neo4jRepository(ApiSettings())

    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    for label, key, must_contain in (
        ("samavedic reused rendering", _first_sv_reuse(plan), "reused"),
        ("rigvedic range secondary verse", "VG:RV:SAK:M01:S065:V002", "span"),
    ):
        result = retrieve(
            QueryPlan(retrieval_channels=["passage_by_key"], passage_key=key),
            [],
            repository,
        )
        packet = build_evidence_packet(result)
        items = [i for i in packet.items if i.passage_key == key]
        rendered = packet.prompt_block if hasattr(packet, "prompt_block") else ""
        disclosures = [i.translation_disclosure for i in items if i.translation_disclosure]
        quoted = [i for i in items if i.translation]
        row = {
            "label": label,
            "key": key,
            "evidence_items": len(items),
            "items_quoting_a_translation": len(quoted),
            "disclosures": disclosures,
            "qualifiers": [i.qualifier for i in items if i.qualifier],
        }
        if quoted and not disclosures:
            failures.append(
                f"{label}: Ask quotes the English for {key} with no disclosure, so an answer "
                "would present it as that verse's own translation"
            )
        elif disclosures and must_contain not in " ".join(disclosures).lower():
            failures.append(
                f"{label}: the disclosure does not mention {must_contain!r}: {disclosures}"
            )
        if not quoted:
            failures.append(f"{label}: Ask retrieved no English for {key}, so nothing to disclose")
        row["rendered_mentions_translation_is"] = "translation_is:" in rendered
        checks.append(row)

    return {"surface": "retriever + build_evidence_packet", "checks": checks, "failures": failures}


def coverage_check() -> dict[str, Any]:
    """The four populations per work, and that they partition the corpus."""
    out = {}
    failures = []
    for work in ("VG:WORK:RV:SAK", "VG:WORK:SV:KAU", "VG:WORK:YV:VSM", "VG:WORK:AV:SAU"):
        body = get(f"/works/{encoded(work)}")
        coverage = body["translation_coverage"]
        total = (
            coverage["dedicated"]
            + coverage["range_covered"]
            + coverage["reused_rendering"]
            + coverage["other_language"]
            + coverage["uncovered"]
        )
        out[work] = {
            "mantras": coverage["mantras"],
            "dedicated": coverage["dedicated"],
            "range_covered": coverage["range_covered"],
            "reused_rendering": coverage["reused_rendering"],
            "other_language": coverage["other_language"],
            "uncovered": coverage["uncovered"],
            "percent_dedicated": coverage["percent"],
            "populations_sum_to_the_corpus": total == coverage["mantras"],
        }
        if total != coverage["mantras"]:
            failures.append(f"{work}: populations sum to {total}, corpus is {coverage['mantras']}")
        if work == "VG:WORK:SV:KAU" and coverage["dedicated"] != 0:
            failures.append(
                "the Samaveda reports a dedicated translation; every English string that "
                "reaches it is a reused Rigvedic rendering and must not be counted as its own"
            )
    return {"per_work": out, "failures": failures}


def main() -> int:
    plan = json.loads((T.INTEGRATION / "translation_import_plan.json").read_text("utf-8"))
    results = [check_case(case, plan) for case in CASES]
    coverage = coverage_check()
    ask = ask_evidence_check()

    failures = (
        [f"{r['label']}: {f}" for r in results for f in r["failures"]]
        + [f"coverage: {f}" for f in coverage["failures"]]
        + [f"ask: {f}" for f in ask["failures"]]
    )
    report = {
        "phase": "K",
        "base_url": BASE,
        "cases": results,
        "coverage": coverage,
        "ask_evidence": ask,
        "failures": failures,
        "verdict": "PRODUCT_TRUTHFUL" if not failures else "PRODUCT_CHECK_FAILED",
    }
    T.write_json(T.INTEGRATION / "translation_product_check.json", report)

    for r in results:
        status = "OK  " if not r["failures"] else "FAIL"
        print(f"{status} {r['label']}")
        print(f"       {r['key']}")
        if "coverage_kind" in r:
            print(
                f"       kind={r['coverage_kind']} lang={r['language']}"
                f" own={r['is_this_passages_own']}"
                f" independent={r['independent_translation']} span={r['span']}"
                f" src={r['source_id']}"
            )
        if r.get("reused_from"):
            print(f"       reused from: {r['reused_from']}")
        if r.get("disclosure"):
            print(f"       disclosure: {r['disclosure']}")
        if r.get("caveat"):
            print(f"       caveat: {r['caveat'][:150]}")
        for f in r["failures"]:
            print(f"       ! {f}")
    print()
    print("coverage per work:")
    for work, row in coverage["per_work"].items():
        print(
            f"  {work:<18} dedicated={row['dedicated']:>6} range={row['range_covered']:>4}"
            f" reused={row['reused_rendering']:>4} other={row['other_language']:>3}"
            f" uncovered={row['uncovered']:>5} partitions={row['populations_sum_to_the_corpus']}"
        )
    print()
    print("ask evidence:", json.dumps(ask))
    print("VERDICT:", report["verdict"])
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
