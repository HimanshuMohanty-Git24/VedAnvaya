"""Build and load Knowledge Model V2: the Vedic domain layer.

Runs the whole pass in order and reports what landed at each step:

1. merge the V2 entity fragments into one registry, in one alias namespace
2. extract Sanskrit-grounded mentions over all four Vedas
3. load the Devata overlay and the interpretive claims
4. upgrade the live graph (internal marking, type labels, display, grade stamping)
5. project entities, mentions, taxonomy, profiles, metrics and claims
6. write artifacts and a manifest

Idempotent: everything is MERGE-based on deterministic keys, so running it twice is the
same as running it once, and running it over a V1 graph converges to the same result as a
rebuild.

Usage::

    python scripts/build_domain_v2.py
    python scripts/build_domain_v2.py --artifacts-only   # no database needed
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
import warnings
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import yaml  # noqa: E402

from vedagraph.domain import loader as domain_loader  # noqa: E402
from vedagraph.domain import upgrade as domain_upgrade  # noqa: E402
from vedagraph.domain.claims import claim_summary, load_claims  # noqa: E402
from vedagraph.domain.mentions import extract_mentions  # noqa: E402
from vedagraph.domain.ontology import DOMAIN_MODEL_VERSION  # noqa: E402
from vedagraph.domain.profiles import (  # noqa: E402
    attribution_metrics,
    compute_profile,
    corpus_metrics,
    top_devatas,
)
from vedagraph.domain.registry import (  # noqa: E402
    DOMAIN_DIR,
    entities_by_node_type,
    load_domain_entities,
    merge_registry,
)
from vedagraph.domain.taxonomy import (  # noqa: E402
    devata_name_forms,
    load_taxonomy,
    registry_label_forms,
)
from vedagraph.enrich.corpus import load_corpus  # noqa: E402

BOLT_URI = "bolt://localhost:7687"
BOLT_AUTH = ("neo4j", "vedagraph_dev")

#: How many deities get a full profile. The long tail is mostly one-off abstract labels
#: whose profile would be a row of ones.
PROFILE_COUNT = 25


def _read_yaml(path: pathlib.Path) -> dict[str, Any]:
    """Parse an overlay file, or return empty if it has not been authored yet."""
    if not path.exists():
        return {}
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def _write_jsonl(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts-only",
        action="store_true",
        help="build artifacts without touching Neo4j",
    )
    args = parser.parse_args()

    out = PROJECT_ROOT / DOMAIN_DIR
    manifest: dict[str, Any] = {"domain_model_version": DOMAIN_MODEL_VERSION}

    print("=" * 78)
    print("KNOWLEDGE MODEL V2 -- domain layer build")
    print("=" * 78)

    print("\n[1/6] merging the entity registry")
    merge = merge_registry(PROJECT_ROOT)
    entities = load_domain_entities(PROJECT_ROOT)
    manifest["registry"] = merge.as_dict()
    manifest["entities_by_node_type"] = entities_by_node_type(entities)
    print(f"      base={merge.base_entities}  merged={merge.merged_entities}")
    for name, count in sorted(merge.fragment_entities.items()):
        print(f"      fragment {pathlib.Path(name).name}: {count}")
    for name in sorted(merge.missing_fragments):
        print(f"      MISSING fragment {pathlib.Path(name).name}")

    print("\n[2/6] loading the Devata overlay and interpretive claims")
    taxonomy, taxonomy_summary = load_taxonomy(PROJECT_ROOT)
    claims = load_claims(PROJECT_ROOT)
    rituals = list(_read_yaml(PROJECT_ROOT / DOMAIN_DIR / "rituals.yaml").get("rituals") or [])
    concern_lists = {
        key: list(value)
        for key, value in _read_yaml(
            PROJECT_ROOT / DOMAIN_DIR / "concern_predicates.yaml"
        ).items()
        if isinstance(value, list)
    }
    manifest["devata_taxonomy"] = taxonomy_summary.as_dict()
    manifest["claims"] = claim_summary(claims)
    print(
        f"      overlay entries={taxonomy_summary.entries}"
        f"  classified={taxonomy_summary.classified}"
        f"  unknown_taxonomy_rate={taxonomy_summary.unknown_taxonomy_rate:.4f}"
    )
    print(
        f"      claims={len(claims)}  rituals={len(rituals)}  "
        f"concern_predicates={sum(len(v) for v in concern_lists.values())}"
    )

    print("\n[3/6] extracting Sanskrit-grounded mentions over four Vedas")
    corpus = load_corpus(PROJECT_ROOT)
    # Every form that is a deity's name, not just the stem. Passing stems alone disabled
    # the theonym check on the vocative -- see devata_name_forms for the measurement.
    devata_labels = devata_name_forms(PROJECT_ROOT, taxonomy) or registry_label_forms(
        PROJECT_ROOT
    )
    mention_rows, mention_report = extract_mentions(corpus, entities, devata_labels)
    manifest["mentions"] = mention_report.as_dict()
    print(f"      mentions={len(mention_rows)}")
    for veda, info in sorted(
        mention_report.notes.get("coverage_by_veda", {}).items()
    ):
        print(
            f"      {veda}: {info['with_mention']}/{info['mantras']} "
            f"mantras ({info['coverage']:.1%})"
        )

    print("\n[4/6] writing artifacts")
    rows = [row.as_row() for row in mention_rows]
    _write_jsonl(out / "domain_mentions.jsonl", rows)
    _write_jsonl(out / "devata_taxonomy_resolved.jsonl", [e.as_row() for e in taxonomy])
    print(f"      {out.name}/domain_mentions.jsonl  ({len(rows)} rows)")

    if args.artifacts_only:
        (out / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("\n[5/6] skipped (--artifacts-only)")
        print("[6/6] manifest written")
        return 0

    from neo4j import GraphDatabase  # imported late: artifacts-only needs no driver

    print("\n[5/6] upgrading the live graph")
    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    try:
        with driver.session() as session:
            before = session.run(
                "MATCH (n) WITH count(n) AS nodes "
                "MATCH ()-[r]->() RETURN nodes, count(r) AS rels"
            ).single()
            manifest["graph_before"] = {
                "nodes": before["nodes"],
                "relationships": before["rels"],
            }

            upgrade_reports = domain_upgrade.upgrade(session)
            for report in upgrade_reports:
                flag = "ok " if report.complete else "!! "
                print(f"      {flag}{report.step:<26} sent={report.sent:<8} landed={report.landed}")

            print("\n[6/6] projecting the domain layer")
            load_reports = [
                domain_loader.load_entities(session, entities),
                domain_loader.load_mentions(session, rows),
                domain_loader.load_devata_taxonomy(session, taxonomy),
                domain_loader.load_rituals(session, rituals),
                domain_loader.load_concern_predicates(session, concern_lists),
            ]

            keys = top_devatas(session, PROFILE_COUNT)
            profiles = [compute_profile(session, key) for key in keys]
            metrics = [m for p in profiles for m in attribution_metrics(p)]
            metrics.extend(corpus_metrics(session))

            load_reports.extend(
                [
                    domain_loader.load_profiles(session, profiles),
                    domain_loader.load_metrics(session, metrics),
                    domain_loader.load_claims(session, claims),
                ]
            )
            for report in load_reports:
                flag = "ok " if report.complete else "!! "
                print(f"      {flag}{report.step:<26} sent={report.sent:<8} landed={report.landed}")

            _write_jsonl(out / "devata_profiles.jsonl", [p.as_row() for p in profiles])
            _write_jsonl(out / "derived_metrics.jsonl", [m.as_row() for m in metrics])

            after = session.run(
                "MATCH (n) WITH count(n) AS nodes "
                "MATCH ()-[r]->() RETURN nodes, count(r) AS rels"
            ).single()
            manifest["graph_after"] = {
                "nodes": after["nodes"],
                "relationships": after["rels"],
            }
            manifest["upgrade"] = domain_upgrade.summarise(upgrade_reports)
            manifest["load"] = domain_loader.summarise(load_reports)
            manifest["label_readability"] = domain_upgrade.unknown_label_rate(session)

            print(
                f"\n      nodes {before['nodes']} -> {after['nodes']}"
                f"   relationships {before['rels']} -> {after['rels']}"
            )
            print(
                "      unknown_label_rate="
                f"{manifest['label_readability']['unknown_label_rate']:.4f}"
            )
    finally:
        driver.close()

    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    complete = manifest["upgrade"]["all_complete"] and manifest["load"]["all_complete"]
    print(f"\n{'=' * 78}\nall steps complete: {complete}\n{'=' * 78}")
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
