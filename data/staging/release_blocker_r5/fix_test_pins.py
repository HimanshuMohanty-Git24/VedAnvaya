"""Re-pin the four test constants R5's own changes invalidated.

None of these is a test weakened to pass. Each one asserted a premise this pass
deliberately changed, and each is re-pinned with the reconciliation that makes the new
figure checkable rather than merely green.

1.  The frozen census. 164,597 -> 164,601 and 509,486 -> 509,769, reconciling exactly
    against TWO receipted steps: the R5 migration (+2 DerivedMetric nodes, +283
    relationships = 158 ASSERTION_AGENT, 119 ASSERTION_TARGET, 6 MENTIONS_ENTITY) and the
    entity-coverage consumer rebuild that followed it (+2 DerivedMetric). The four corpora
    are unmoved, which is the guard that matters.

2.  ``test_the_pipeline_constant_predicates_are_still_constant``. Its premise is now VOID
    rather than false: it asserted that HAS_RISHI's confidence is a single constant, as the
    justification for the API returning null for it. GAP-QUALITY-003 removed the field --
    a constant 1.0 on every edge of seven predicates encoded a TIER and not a probability,
    and a thresholdable number with no curve behind it invites a filter nobody can honour.
    The test is REWRITTEN to assert the stronger property: no predicate carries a constant
    confidence, and the seven now carry ``source_explicit_tier_marker`` instead. Returning
    null is no longer hiding a value, because there is no value to hide.

3.  The DerivedMetric total in the G04 paging test, 1,481 -> 1,485.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]

CENSUS_OLD = """#: R4 moved the census by one receipted migration:
#: data/staging/release_blocker_r4/migration_receipt.json. +396 nodes (399 DerivedMetric
#: created for the widened deity-profile population, 3 deleted with the danastuti label's
#: deity metrics) and +1,444 relationships (1,035 MENTIONS_EPITHET, 399 MEASURES, 8
#: ASCRIBES_TO_DEVATA, 4 COMPOSED_OF, 1 ATTESTED_IN, less the 3 MEASURES that went with
#: the deleted metrics). The delta reconciles exactly against the 164,201/508,042
#: baseline, and tests/api/test_adversarial.py imports both constants from here so the
#: pin has one home.
FROZEN_NODES = 164_597
FROZEN_RELATIONSHIPS = 509_486"""

CENSUS_NEW = """#: R4 moved the census by one receipted migration:
#: data/staging/release_blocker_r4/migration_receipt.json. +396 nodes (399 DerivedMetric
#: created for the widened deity-profile population, 3 deleted with the danastuti label's
#: deity metrics) and +1,444 relationships (1,035 MENTIONS_EPITHET, 399 MEASURES, 8
#: ASCRIBES_TO_DEVATA, 4 COMPOSED_OF, 1 ATTESTED_IN, less the 3 MEASURES that went with
#: the deleted metrics). The delta reconciles exactly against the 164,201/508,042
#: baseline, and tests/api/test_adversarial.py imports both constants from here so the
#: pin has one home.
#:
#: R5 moved it again, by TWO steps rather than one, and both are receipted:
#:
#: *   the R5 migration, data/staging/release_blocker_r5/migration_receipt.json, with
#:     actual == promised on every counter: +2 nodes (the RITUAL_CONTEXT_PRECISION and
#:     MATERIAL_CULTURE_BY_RITUAL_CONTEXT DerivedMetric rows GAP-RITUAL-006 needed) and
#:     +283 relationships -- 158 ASSERTION_AGENT and 119 ASSERTION_TARGET projected from
#:     the RoleFiller resolution for GAP-SEMANTICS-003, plus 6 MENTIONS_ENTITY from the
#:     phrase pass for GAP-ENTITY_COVERAGE-007. Nothing was deleted.
#: *   the entity-coverage consumer rebuild that the dependency report required afterwards,
#:     which recomputed its metric families and added 2 more DerivedMetric rows.
#:
#: 164,597 + 2 + 2 = 164,601 and 509,486 + 283 = 509,769. The four corpora did not move,
#: which is the guard that actually matters and is asserted separately below.
FROZEN_NODES = 164_601
FROZEN_RELATIONSHIPS = 509_769"""

METRIC_OLD = """    assert sections[SectionKind.DERIVED_METRIC]["total_available"] == 1481"""
METRIC_NEW = """    # 1,481 -> 1,485. R5 added 2 (GAP-RITUAL-006's precision and material-culture rows)
    # and the entity-coverage rebuild the dependency report then required added 2 more.
    assert sections[SectionKind.DERIVED_METRIC]["total_available"] == 1485"""


def main() -> None:
    health = ROOT / "tests" / "api" / "test_app_health.py"
    raw = health.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("test_app_health.py contains CRLF; refusing")
    text = raw.decode("utf-8")
    if CENSUS_NEW in text:
        print("  census already re-pinned")
    else:
        if CENSUS_OLD not in text:
            raise SystemExit("census anchor not found")
        health.write_bytes(text.replace(CENSUS_OLD, CENSUS_NEW, 1).encode("utf-8"))
        print("  re-pinned FROZEN_NODES / FROZEN_RELATIONSHIPS")

    insights = ROOT / "tests" / "api" / "test_insights.py"
    raw = insights.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("test_insights.py contains CRLF; refusing")
    text = raw.decode("utf-8")
    if METRIC_NEW in text:
        print("  DerivedMetric total already re-pinned")
    else:
        if METRIC_OLD not in text:
            raise SystemExit("DerivedMetric anchor not found")
        insights.write_bytes(text.replace(METRIC_OLD, METRIC_NEW, 1).encode("utf-8"))
        print("  re-pinned the DerivedMetric total")


if __name__ == "__main__":
    main()
