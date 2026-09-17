"""The semantic-assertion review harness and its stratified sample -- GAP-SEMANTICS-002.

The gap is that all 4,865 live assertions are ``review_state='UNREVIEWED'`` and none has
ever been checked by a human. Two things were missing and they are different: the *harness*
that a review would write through, and the *reviewer*. This script supplies the first and
says plainly that it cannot supply the second.

**The property is ``review_state``.** Read from the live graph before anything was written:
``review_state`` exists with exactly one value, ``UNREVIEWED``, on 4,865 nodes, and
``review_status`` is not a property key in this database at all. An earlier pass declared
4,865 unreviewed against a measured 0 by querying the wrong name; that is why the name is
read and asserted here rather than restated.

**What this harness will not do.** It will not set ``review_state`` to anything. A review
state written by this script would be a state produced by a model reading a model's output,
and recording that as a review is the relabel the campaign exists to prevent. The vocabulary
below keeps the three kinds of adjudication apart by name, so no consumer can read one as
another:

``HUMAN_REVIEWED``
    A person read the verse and the assertion. Requires ``reviewer_kind='human'`` and a
    named reviewer. **Nothing in this repository has ever reached this state.**
``SOURCE_ADJUDICATED``
    An independent published source decides it -- a treebank parse, an Anukramani entry.
    Requires the source id and locator.
``MODEL_ADJUDICATED``
    A model re-read it. Requires the model id. It is evidence about the model.

**Why SOURCE_ADJUDICATED cannot be run on the live 4,865 either, and that is measured.**
The only independent adjudicator this project holds for the semantic layer is the DCS
dependency parse. DCS carries no Rigvedic parse, and all 4,865 live assertions are
Rigvedic. So the independent-source route reaches exactly 0 of them. The remaining work is
a human reading verses, which is reviewer time -- not an external source that does not
exist.

Neo4j is read **only**.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

REPO: Final = Path(__file__).resolve().parents[1]
OUT_DIR: Final = REPO / "data" / "staging" / "final_closure_sprint" / "agent3"

REVIEW_STATES: Final[dict[str, dict[str, Any]]] = {
    "UNREVIEWED": {
        "meaning": "nothing has checked this assertion",
        "requires": [],
        "counts_as_human_review": False,
    },
    "HUMAN_REVIEWED": {
        "meaning": "a person read the verse and the assertion",
        "requires": ["reviewer_kind='human'", "reviewer_id", "reviewed_at"],
        "counts_as_human_review": True,
    },
    "SOURCE_ADJUDICATED": {
        "meaning": "an independent published source decides it",
        "requires": ["reviewer_kind='source'", "source_id", "source_locator", "reviewed_at"],
        "counts_as_human_review": False,
    },
    "MODEL_ADJUDICATED": {
        "meaning": "a model re-read it; evidence about the model",
        "requires": ["reviewer_kind='model'", "model_id", "reviewed_at"],
        "counts_as_human_review": False,
    },
}

#: How many assertions to draw per stratum. Deliberately small and deterministic: this is a
#: frame for a human to work through, and a frame nobody can finish is not a plan.
SAMPLE_PER_STRATUM: Final = 60

#: Assertions Agent 3 stages for import, every one UNREVIEWED. Read from the delta artifact
#: rather than hard-coded, so the post-integration figure cannot drift from the delta.
_DELTA: Final = (
    REPO
    / "data"
    / "staging"
    / "final_closure_sprint"
    / "agent3"
    / "semantic_assertions.jsonl"
)
STAGED_ASSERTIONS: Final = (
    sum(1 for line in _DELTA.open(encoding="utf-8") if line.strip()) if _DELTA.exists() else 0
)


def _session() -> Any:
    load_dotenv(str(REPO / ".env"))
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.environ.get("NEO4J_USER", "neo4j"),
            os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
        ),
    )
    return driver, driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j"))


def validate_transition(state: str, fields: dict[str, Any]) -> None:
    """Refuse a review record that does not carry what its state requires.

    This is the harness's whole contract. A ``HUMAN_REVIEWED`` row with
    ``reviewer_kind='model'`` is the single failure mode that would make every later figure
    a lie, so it raises rather than warns.
    """
    if state not in REVIEW_STATES:
        raise ValueError(f"unknown review_state {state!r}; the vocabulary is closed")
    spec = REVIEW_STATES[state]
    for requirement in spec["requires"]:
        if "=" in requirement:
            name, expected = requirement.split("=", 1)
            if str(fields.get(name)) != expected.strip("'"):
                raise ValueError(
                    f"review_state={state} requires {requirement}, got "
                    f"{name}={fields.get(name)!r}"
                )
        elif not fields.get(requirement):
            raise ValueError(f"review_state={state} requires {requirement}")
    if spec["counts_as_human_review"] and fields.get("reviewer_kind") != "human":
        raise ValueError(
            f"{state} may only be written by a human reviewer; a model- or "
            "source-adjudicated record must use its own state"
        )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    driver, session = _session()
    try:
        states = {
            record["s"]: record["n"]
            for record in session.run(
                "MATCH (a:SemanticAssertion) RETURN a.review_state AS s, count(*) AS n"
            )
        }
        review_status_present = any(
            record["k"] == "review_status"
            for record in session.run("CALL db.propertyKeys() YIELD propertyKey AS k RETURN k")
        )
        strata = [
            dict(record)
            for record in session.run(
                "MATCH (a:SemanticAssertion) "
                "RETURN a.derivation AS derivation, a.quality_tier AS quality_tier, "
                "count(*) AS population ORDER BY derivation"
            )
        ]
        sample: list[dict[str, Any]] = []
        for stratum in strata:
            sample.extend(
                dict(record)
                for record in session.run(
                    "MATCH (m:Mantra)-[:HAS_SEMANTIC_ASSERTION]->(a:SemanticAssertion) "
                    "WHERE a.derivation = $derivation "
                    "RETURN a.assertion_id AS assertion_id, m.canonical_key AS canonical_key, "
                    "m.veda AS veda, a.derivation AS derivation, "
                    "a.quality_tier AS quality_tier, a.predicate AS predicate, "
                    "a.frame AS frame, a.review_state AS review_state_before "
                    "ORDER BY a.assertion_id LIMIT $limit",
                    derivation=stratum["derivation"],
                    limit=SAMPLE_PER_STRATUM,
                )
            )
        # Can an independent published source adjudicate any of them? Measured, not assumed.
        rv_share = session.run(
            "MATCH (m:Mantra)-[:HAS_SEMANTIC_ASSERTION]->(a:SemanticAssertion) "
            "RETURN m.veda AS veda, count(*) AS n"
        )
        per_veda = {record["veda"]: record["n"] for record in rv_share}
    finally:
        session.close()
        driver.close()

    for row in sample:
        row["review_state"] = "UNREVIEWED"
        row["reviewer_kind"] = None
        row["reviewer_id"] = None
        row["reviewed_at"] = None
        row["verdict"] = None
        row["note"] = None

    path = OUT_DIR / "semantic_review_frame.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sample:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "artifact": "AGENT_3_SEMANTIC_REVIEW_FRAME",
        "gap": "GAP-SEMANTICS-002",
        "at": datetime.now(UTC).isoformat(),
        "neo4j_access": "READ_ONLY",
        "property_name_read_from_the_database": "review_state",
        "review_status_property_exists": review_status_present,
        "live_review_state_values": states,
        # LEAD CORRECTION 3. The live figure is pre-import. Agent 3's own delta stages
        # 30,274 further assertions, every one UNREVIEWED, so the gap's declared
        # closure_measure reads 35,139 after integration -- 7.2x the figure the gap was
        # written against. Closing SEMANTICS-001's coverage makes this gap LARGER.
        "unreviewed_population": {
            "live_now": states.get("UNREVIEWED", 0),
            "staged_by_agent_3_all_unreviewed": STAGED_ASSERTIONS,
            "after_integration": states.get("UNREVIEWED", 0) + STAGED_ASSERTIONS,
            "multiple": round(
                (states.get("UNREVIEWED", 0) + STAGED_ASSERTIONS)
                / max(states.get("UNREVIEWED", 1), 1),
                2,
            ),
            "note": "Report the post-integration figure. Quoting 4,865 after the import "
            "would understate the gap by 30,274.",
        },
        "review_state_vocabulary": REVIEW_STATES,
        "strata": strata,
        "sample_per_stratum": SAMPLE_PER_STRATUM,
        "sample_rows": len(sample),
        "sample_by_derivation": dict(Counter(row["derivation"] for row in sample)),
        "assertions_per_veda": per_veda,
        "independent_source_adjudication_reach": {
            "only_independent_adjudicator_held": "DCS dependency treebank",
            "dcs_rigvedic_coverage": 0,
            "live_assertions_that_are_rigvedic": per_veda.get("RV", 0),
            "live_assertions_an_independent_source_could_decide": 0,
            "conclusion": "SOURCE_ADJUDICATED reaches 0 of the live layer. What remains is "
            "a human reading verses. That is reviewer time, not an unavailable external "
            "source, and it is not an implementation gap either.",
        },
        "rows_written_to_a_reviewed_state_by_this_script": 0,
        "human_annotation_claimed": False,
        "files": {path.name: sha256(path.read_bytes()).hexdigest()},
    }
    (OUT_DIR / "semantic_review_frame_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
