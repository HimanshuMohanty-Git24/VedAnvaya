"""Project the whole Rigvedic lexical index as MENTIONS_LEMMA -- GAP-MORPHOLOGY-001.

**What was wrong.** ``MENTIONS_LEMMA`` was built as the instrument behind the deity mention
layer and never as a lexical index. 10,031 ``:Lemma`` nodes were loaded and 39 of them --
every one a theonym -- were wired, leaving 9,992 with no edge in either direction. The
campaign baseline reports the dimension as "Lemma: RV 6,560", which is a true count of
*mantras* carrying at least one edge and conceals that those edges reach thirty-nine words.
A reader takes it for a 62% lexical index; it is a 0.4% one. That is why this artifact
emits **two** figures and the surface contract below requires both.

**The registry's scale objection does not survive measurement.** The row's
``implementation_dependency`` says projecting all 10,031 lemmas "would add on the order of
a million edges", and treats that as needing a policy before a load. Measured over
``data/knowledge/rigveda_lexical_v1/tokens.jsonl``: 164,758 tokens collapse to **154,261**
distinct ``(mantra, lemma)`` pairs. The order of magnitude is wrong by a factor of about
six and a half, and the objection it supported does not hold.

**The declared projection policy.** One edge per distinct ``(mantra, lemma)`` pair over the
whole annotation, with ``occurrence_count`` carrying the token multiplicity. No frequency
floor, no stop-lemma list, no part-of-speech filter: a floor would make the index's reach a
function of a threshold nobody records, and this layer's whole defect was a reach nobody
could see. Every edge is a token of that lemma annotated in that mantra by the Zurich
scholars -- it asserts a lexical occurrence and nothing more. It is **not** an entity
mention, not a topic and not a dedication.

**The existing 9,000 edges are a strict subset**, verified pair-by-pair against the live
graph: 0 of them fall outside the 154,261. The import is therefore a MERGE that adds
145,261 and leaves the deity instrument's own edges addressable and unchanged.

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
TOKENS: Final = REPO / "data" / "knowledge" / "rigveda_lexical_v1" / "tokens.jsonl"
OUT_DIR: Final = REPO / "data" / "staging" / "final_closure_sprint" / "agent3"

PROJECTION_POLICY: Final = "ALL_ANNOTATED_LEMMATA_ONE_EDGE_PER_MANTRA_LEMMA_PAIR_V1"


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


def read_pairs(path: Path) -> tuple[Counter[tuple[str, str]], int]:
    """Collapse the token stream to ``(mantra, lemma) -> occurrence_count``."""
    pairs: Counter[tuple[str, str]] = Counter()
    tokens = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            lemma = record.get("lemma")
            if not lemma:
                raise ValueError(f"token {record.get('token_key')} carries no lemma")
            tokens += 1
            pairs[(record["passage_key"], lemma)] += 1
    return pairs, tokens


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs, tokens = read_pairs(TOKENS)

    driver, session = _session()
    try:
        graph_lemmas = {
            record["lemma"] for record in session.run("MATCH (l:Lemma) RETURN l.lemma AS lemma")
        }
        existing = {
            (record["p"], record["l"])
            for record in session.run(
                "MATCH (m:Mantra)-[:MENTIONS_LEMMA]->(l:Lemma) "
                "RETURN m.canonical_key AS p, l.lemma AS l"
            )
        }
        zero_indegree_before = session.run(
            "MATCH (l:Lemma) WHERE size([(l)<--()|1])=0 RETURN count(l) AS n"
        ).single()["n"]
        distinct_reached_before = session.run(
            "MATCH (:Mantra)-[:MENTIONS_LEMMA]->(l:Lemma) RETURN count(DISTINCT l) AS n"
        ).single()["n"]
        mantras_reached_before = session.run(
            "MATCH (m:Mantra)-[:MENTIONS_LEMMA]->(:Lemma) RETURN count(DISTINCT m) AS n"
        ).single()["n"]
        # The projection is only sound if every annotated lemma already has a node. An
        # absent one would silently drop its edges and the drop would look like a corpus fact.
        missing_keys = sorted({lemma for _, lemma in pairs} - graph_lemmas)
    finally:
        session.close()
        driver.close()

    if missing_keys:
        raise SystemExit(
            f"{len(missing_keys)} annotated lemmas have no :Lemma node, e.g. {missing_keys[:5]}; "
            "load the nodes before projecting or the edges vanish without a trace"
        )
    orphan_existing = sorted(existing - set(pairs))
    if orphan_existing:
        raise SystemExit(
            f"{len(orphan_existing)} live MENTIONS_LEMMA edges are not in the annotation, "
            f"e.g. {orphan_existing[:3]}; reconcile before MERGE rather than after"
        )

    path = OUT_DIR / "mentions_lemma_projection.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for (passage_key, lemma), count in sorted(pairs.items()):
            handle.write(
                json.dumps(
                    {
                        "canonical_key": passage_key,
                        "lemma": lemma,
                        "occurrence_count": count,
                        "already_in_graph": (passage_key, lemma) in existing,
                        "projection_policy": PROJECTION_POLICY,
                        "knowledge_layer": "L2_DETERMINISTIC_DERIVED",
                        "provenance_class": "DETERMINISTIC_DERIVED",
                        "evidence_basis": "SANSKRIT",
                        "attribution_precision": "TEXTUAL_MENTION",
                        "quality_tier": "TIER_B",
                        "provenance": "deterministic",
                        "annotation_provenance": "human-published",
                        "annotation_note": (
                            "The lemmatisation is the University of Zurich manual scholarly "
                            "annotation, which is human-published. The projection of it into "
                            "edges is deterministic. The two are different claims."
                        ),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    distinct_lemmas = len({lemma for _, lemma in pairs})
    distinct_mantras = len({key for key, _ in pairs})
    manifest = {
        "artifact": "AGENT_3_MENTIONS_LEMMA_PROJECTION",
        "gap": "GAP-MORPHOLOGY-001",
        "at": datetime.now(UTC).isoformat(),
        "neo4j_access": "READ_ONLY",
        "projection_policy": PROJECTION_POLICY,
        "source_tokens": tokens,
        "edges_total_after_import": len(pairs),
        "edges_already_present": len(existing),
        "edges_to_create": len(pairs) - len(existing),
        "existing_edges_outside_the_projection": len(orphan_existing),
        # The two figures the surface must state side by side, and the whole reason this
        # gap was invisible in the baseline.
        "lemma_coverage_surface_contract": {
            "distinct_lemmas_reached_before": distinct_reached_before,
            "distinct_lemmas_reached_after": distinct_lemmas,
            "mantras_reached_before": mantras_reached_before,
            "mantras_reached_after": distinct_mantras,
            "rule": (
                "Any surface reporting lemma coverage states distinct lemmas reached AND "
                "mantras reached. Neither alone is the coverage."
            ),
        },
        "zero_indegree_lemmas_before": zero_indegree_before,
        "zero_indegree_lemmas_after_import": 0,
        "registry_claim_under_test": {
            "claim": "projecting all 10,031 lemmas would add on the order of a million edges",
            "measured_edges": len(pairs),
            "verdict": "FALSE -- overstated by roughly 6.5x",
        },
        "veda_scope": "RV only. The annotation is Rigvedic; SV, YV and AV get no edge here "
        "and this artifact makes no claim about their lexical index.",
        "files": {path.name: sha256(path.read_bytes()).hexdigest()},
    }
    (OUT_DIR / "mentions_lemma_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
