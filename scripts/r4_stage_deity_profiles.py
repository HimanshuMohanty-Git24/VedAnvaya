#!/usr/bin/env python3
"""Stage GAP-ENTITY_COVERAGE-002: deity profiles and metrics over the eligible population.

Profiles were selected as the union of the top twenty deities by mention and the top twenty
by attribution, which reached 25 subjects. So 189 deity pages reported ``null`` for every
corpus, and the closure test asks the materialisation to reach *the resolved-deity
population* rather than a top-N. ``VG:DEVATA:SARASVATI`` is the entry's named example and
returns ``null`` for ``profile_attributed_total``.

Two things this fixes at once
=============================

**The denominator.** :func:`vedagraph.domain.profiles.eligible_devatas` selects by
``VG:DEITY_ELIGIBILITY:V1``'s own predicate, so 157 of 214. Not 214: that would put 22
human patrons and 7 danastuti gift-praise labels on deity profile pages, which the entry
names as the hazard.

**A live instance of that hazard.** ``top_devatas`` ranked by ``HAS_DEVATA`` with no
eligibility filter, and ``VG:DEVATA:DANASTUTIH`` -- "praise of a patron's gift", ruled
``NOT_DEITY`` with ``non_deity_kind: DANASTUTI_GIFT_PRAISE`` -- is one of the 25 that
already carries all three deity metrics. Selecting by the predicate removes it. Its three
metrics are staged for **deletion**, named individually, rather than left behind where a
count of 157 would hide them.

Every row is written out in full so the migration applies exactly what was staged here and
``actual == promised`` is a real comparison rather than the same computation run twice.

Measured when written: all 157 eligible deities carry at least one ``HAS_DEVATA`` edge, so
every materialised figure is a real count and none is a zero standing in for an absent
layer.

Usage:
    python scripts/r4_stage_deity_profiles.py
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import pathlib
import sys
from typing import Any, Final

from neo4j import GraphDatabase

PROJECT_ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.domain import profiles as profiles_module  # noqa: E402

OUT: Final = PROJECT_ROOT / "data" / "staging" / "release_blocker_r4" / "entity_002"
URI: Final = "bolt://localhost:7687"
AUTH: Final = ("neo4j", "vedagraph_dev")
DB: Final = "neo4j"


def main() -> int:
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            eligible = profiles_module.eligible_devatas(session)
            # Measured once and passed in, per compute_profile's own instruction: a caller
            # that lets it default gets the scope declared rather than measured.
            scope = profiles_module.measure_attribution_scope(session)

            before_subjects = sorted(
                {
                    record["k"]
                    for record in session.run(
                        "MATCH (m:DerivedMetric) WHERE m.subject_key STARTS WITH 'VG:DEVATA:' "
                        "RETURN DISTINCT m.subject_key AS k"
                    )
                }
            )
            ineligible_now_carrying_metrics = sorted(
                {
                    record["k"]
                    for record in session.run(
                        "MATCH (m:DerivedMetric) WHERE m.subject_key STARTS WITH 'VG:DEVATA:' "
                        "WITH DISTINCT m.subject_key AS k "
                        "MATCH (d:Devata {entity_key: k}) WHERE d.is_deity <> true "
                        "RETURN k"
                    )
                }
            )
            metrics_to_delete = sorted(
                record["id"]
                for record in session.run(
                    "MATCH (m:DerivedMetric) WHERE m.subject_key IN $keys "
                    "RETURN m.metric_id AS id",
                    keys=ineligible_now_carrying_metrics,
                )
            )
            attributed = {
                record["k"]: record["n"]
                for record in session.run(
                    "MATCH (d:Devata)<-[r:HAS_DEVATA]-(:Passage) "
                    "WHERE d.entity_key IN $keys "
                    "RETURN d.entity_key AS k, count(r) AS n",
                    keys=eligible,
                )
            }

            computed = [
                profiles_module.compute_profile(session, key, attribution_scope=scope)
                for key in eligible
            ]
    finally:
        driver.close()

    metrics = [
        dataclasses.asdict(metric)
        for profile in computed
        for metric in profiles_module.attribution_metrics(profile)
    ]

    without_attribution = sorted(key for key in eligible if not attributed.get(key))

    report = {
        "artifact": "R4_ENTITY_002_DEITY_PROFILE_STAGING",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gap_id": "GAP-ENTITY_COVERAGE-002",
        "selection": {
            "predicate": "VG:DEITY_ELIGIBILITY:V1 -- d.is_deity = true",
            "eligible": len(eligible),
            "registry_total": 214,
            "why_not_the_registry_total": (
                "22 human patrons and 7 danastuti gift-praise labels would land on deity "
                "profile pages."
            ),
        },
        "before": {
            "distinct_metric_subjects": len(before_subjects),
            "subjects": before_subjects,
            "ineligible_subjects_carrying_deity_metrics": ineligible_now_carrying_metrics,
        },
        "promised": {
            "profiles_written": len(computed),
            "metrics_written": len(metrics),
            "metric_names": sorted({metric["metric_name"] for metric in metrics}),
            "distinct_metric_subjects_after": len(
                {metric["subject_key"] for metric in metrics}
            ),
            "metrics_deleted": len(metrics_to_delete),
            "metric_ids_deleted": metrics_to_delete,
        },
        "eligible_without_any_attribution_edge": without_attribution,
        "sarasvati_is_in_scope": "VG:DEVATA:SARASVATI" in eligible,
        "profiles": [dataclasses.asdict(profile) for profile in computed],
        "metrics": metrics,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "staging.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  GAP-ENTITY_COVERAGE-002 -- DEITY PROFILES STAGED")
    print()
    print(f"  eligible population          {len(eligible)} of 214")
    print(f"  metric subjects before       {len(before_subjects)}")
    print(f"  ineligible carrying metrics  {ineligible_now_carrying_metrics}")
    print(f"  profiles computed            {len(computed)}")
    print(f"  metrics staged               {len(metrics)} over "
          f"{len({m['subject_key'] for m in metrics})} subjects")
    print(f"  metrics staged for deletion  {len(metrics_to_delete)}")
    print(f"  eligible with no attribution {len(without_attribution)}")
    print(f"  SARASVATI in scope           {report['sarasvati_is_in_scope']}")
    print()
    print(f"  staged: {(OUT / 'staging.json').relative_to(PROJECT_ROOT)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
