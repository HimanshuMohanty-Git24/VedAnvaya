#!/usr/bin/env python3
"""Build data/staging/communities/ -- derived deity co-occurrence communities.

Run from the repo root:

    .venv/Scripts/python.exe data/staging/communities/build_communities_staging.py

Read-only against Neo4j throughout. The only Cypher verbs used are MATCH, WITH, RETURN,
UNWIND and CALL of `gds.*.stream`; the node and relationship totals are re-counted at the
end of the run and compared with the counts taken at the start, and the manifest records
both.

THE ONE THING A READER MUST NOT MISREAD
---------------------------------------
Nothing in this artifact is a traditional theological category. Every community here is a
*derived co-occurrence community*: a set of deity labels that the algorithm groups because
the Anukramani happens to place them in the same hymns. No Vedic, Brahmanical or later
source classifies deities this way, and the strongest cluster this projection finds is not
a pantheon at all -- it is the fixed apri sequence of the animal offering, which is a
liturgical running order. Every row, every community record and the report say so.

WHAT IS PROJECTED, AND WHY IT IS NOT WHAT THE BRIEF EXPECTED
------------------------------------------------------------
The brief asked for co-dedication, and warned that it would be structurally RV+AV only.
Two measurements change that:

1. Co-dedication *within a mantra* does not exist. Of 10,552 Rigvedic mantras carrying
   HAS_DEVATA, 10,546 carry exactly one deity and 6 carry two. A mantra-scope co-dedication
   graph has six edges. It is not a graph.
2. The Atharvavedic half does not join. HAS_DEVATA_ASCRIPTION points at 324
   :DevataAscription nodes and *none* of them is also a :Devata -- that is
   GAP-ATTRIBUTION-002, open and owned by agent 8. So a co-dedication projection over
   :Devata is Rigveda-only, not RV+AV, and the 324 descriptors are carried as `unresolved`
   candidates rather than silently dropped.

So the primary projection is co-dedication at **hymn** scope over the **Rigveda**: two
deities are joined when the Anukramani dedicates verses of the same sukta to both. That is
also the source's *native* granularity -- 79% of Rigvedic verse-level dedication is a
sukta-wide value read down onto verses -- so grouping back to the sukta recovers what the
index actually states rather than inventing a coarser unit.

A second projection, co-*mention* at mantra scope over all four Vedas, is computed as a
comparison and is never merged with the first. Mention is not dedication and the brief
forbids inferring one from the other; the two are reported side by side precisely so the
difference is visible.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import pathlib
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "src"))

from community_algorithms import (  # noqa: E402
    Graph,
    adjusted_rand_index,
    betweenness_centrality,
    communities_are_connected,
    connected_components,
    consensus_partition,
    leiden,
    louvain,
    match_to_reference,
    modularity,
    normalised_mutual_information,
    participation_coefficient,
    within_module_degree_z,
)

# ======================================================================================
# Configuration -- hashed into the manifest, so a changed knob changes the config_hash
# ======================================================================================

CONFIG: dict[str, object] = {
    "algorithm_version": "vg-deity-communities-v1",
    "primary_projection": "RV_CODEDICATION_HYMN_V1",
    "comparison_projection": "ALLVEDA_COMENTION_MANTRA_V1",
    "primary_algorithm": "leiden",
    # COSINE (the Ochiai coefficient) is the reference weighting, on two grounds that are
    # deliberately reported separately because only one of them is honest on its own.
    #   A PRIORI: it is the conventional degree-corrected co-occurrence measure, and unlike
    #   Jaccard it does not punish a genuine hub-to-hub link -- Agni and Indra can share
    #   forty hymns and still score near zero on Jaccard because each appears in hundreds.
    #   POSTERIOR, AND LEARNED AFTER ALL THREE WERE RUN: it is measurably the most
    #   seed-stable of the three. Choosing a weighting because its partition came out
    #   tidiest is the same defect as choosing a lucky seed, so the order in which this was
    #   learned is stated rather than smoothed over, and all three weightings' partitions
    #   are published in proofs/membership_under_every_method.json.
    "primary_weighting": "COSINE",
    "primary_resolution": 1.0,
    "primary_population_variant": "V-RULED",
    "seeds": list(range(200)),
    "resolution_ladder": [0.25, 0.4, 0.5, 0.65, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 8.0],
    "weightings": ["RAW", "JACCARD", "COSINE"],
    "population_variants": ["V-ALL", "V-RULED", "V-NONE"],
    "excluded_structures": ["HUMAN", "PATRON_PRAISE"],
    "consensus_threshold": 0.5,
    "min_pair_weight": 1,
    "abstract_rulings_file": "abstract_label_rulings.json",
}

SOURCE_CODED = "VG_COMMUNITIES_CODEDICATION_2026_09_15"
SOURCE_COMENTION = "VG_COMMUNITIES_COMENTION_2026_09_15"
SOURCE_TAXONOMY = "VG_DEVATA_TAXONOMY_V1_STRUCTURE"

CAVEAT = (
    "A DERIVED CO-OCCURRENCE COMMUNITY, NOT A TRADITIONAL CATEGORY. This community is the "
    "output of a modularity-maximising algorithm over a graph whose edges count how often "
    "the Anukramani dedicates verses of the same hymn to two deities. No Vedic or later "
    "source groups deities this way. The densest region of this graph is the fixed apri "
    "sequence of the animal offering, i.e. a liturgical running order, not a pantheon."
)

RECENSION_EVIDENCE_RV = (
    "Sakala; VG:WORK:RV:SAK; 10,552 mantras and 1,028 suktas; Bashkala and Sankhayana not "
    "held. Dedication read from the WSC2023 Anukramani projection already in the graph."
)


# ======================================================================================
# Neo4j -- read only
# ======================================================================================


def open_driver():
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(REPO / ".env")
    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.environ.get("NEO4J_USER", "neo4j"),
            os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
        ),
    )


def run(driver, cypher: str, **params) -> list[dict]:
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    with driver.session(database=database) as session:
        return [dict(record) for record in session.run(cypher, **params)]


def graph_counts(driver) -> dict[str, int]:
    nodes = run(driver, "MATCH (n) RETURN count(n) AS n")[0]["n"]
    rels = run(driver, "MATCH ()-[r]->() RETURN count(r) AS n")[0]["n"]
    return {"nodes": nodes, "relationships": rels}


# ======================================================================================
# Population
# ======================================================================================


def load_deities(driver) -> dict[str, dict]:
    rows = run(
        driver,
        """
        MATCH (d:Devata)
        OPTIONAL MATCH (m:Mantra)-[:HAS_DEVATA]->(d)
        WITH d, count(m) AS dedications, count(DISTINCT m.parent_key) AS hymns
        OPTIONAL MATCH (n:Mantra)-[:MENTIONS_DEVATA]->(d)
        RETURN d.entity_key AS key, d.structure AS structure, d.label_en AS label_en,
               d.label_iast AS label_iast, d.axes AS axes,
               d.curation_confidence AS curation_confidence,
               d.curation_note AS curation_note, d.short_description AS short_description,
               d.devata_subtype AS devata_subtype, d.occurrence_count AS occurrence_count,
               dedications, hymns, count(n) AS mention_edges
        ORDER BY key
        """,
    )
    return {r["key"]: r for r in rows}


def classify_population(deities: dict[str, dict], rulings: dict[str, dict]) -> dict[str, dict]:
    """Attach an eligibility verdict to every one of the 214 :Devata nodes.

    Three verdicts and they are not interchangeable:

    * ``EXCLUDED_NOT_A_DEITY`` -- agent 8's audit, taken from each node's own curated
      ``structure``, not from a name heuristic. 22 HUMAN and 7 PATRON_PRAISE.
    * ``EXCLUDED_BY_ABSTRACT_RULING`` -- this agent's per-label call, recorded with a reason
      in abstract_label_rulings.json and applied only in the V-RULED and V-NONE variants.
    * ``ELIGIBLE`` -- everything else, including every Yajurvedic-style ritual implement.
      Those look like contamination and are not: Kathyayana's own opening sutra admits
      implements into the devata co-domain as *pratimabhuta*, and agent 8 passed that
      forward as a constraint on this agent specifically.
    """
    # A ruling whose key does not resolve is a silent under-application of the ruling file,
    # and it is exactly how this run first reported 158 eligible deities instead of 157:
    # one ruling was keyed VG:DEVATA:SAMJNANAM against the graph's VG:DEVATA:SANJNANAM, so
    # one exclusion never happened and nothing said so. Raise rather than default.
    unresolved_rulings = sorted(set(rulings) - set(deities))
    if unresolved_rulings:
        raise KeyError(
            f"{len(unresolved_rulings)} ruling(s) name a :Devata key that does not exist: "
            f"{unresolved_rulings}. A ruling that matches nothing is not applied and not "
            "reported, so this must fail loudly."
        )
    expected = {k for k, v in deities.items() if v["structure"] in ("ABSTRACT", "UNSPECIFIED")}
    if set(rulings) != expected:
        raise KeyError(
            "the ruling file must cover exactly the ABSTRACT/UNSPECIFIED population; "
            f"missing {sorted(expected - set(rulings))}, extra {sorted(set(rulings) - expected)}"
        )

    out: dict[str, dict] = {}
    for key, node in deities.items():
        structure = node["structure"]
        ruling = rulings.get(key)
        if structure in CONFIG["excluded_structures"]:
            verdict = "EXCLUDED_NOT_A_DEITY"
            reason = (
                f"curated structure is {structure}: "
                + (
                    "a human patron or person occupying the devata slot"
                    if structure == "HUMAN"
                    else "a danastuti gift-praise label, not an addressee"
                )
                + ". Taken from agent 8's population audit "
                  "(data/staging/attribution/proofs/deity_population_contamination.json), "
                  "which reads each node's own curated structure rather than guessing from "
                  "the name."
            )
        elif ruling and ruling["ruling"] == "NOT_DEITY":
            verdict = "EXCLUDED_BY_ABSTRACT_RULING"
            reason = ruling["reason"]
        else:
            verdict = "ELIGIBLE"
            reason = None
        out[key] = {
            **node,
            "eligibility": verdict,
            "eligibility_reason": reason,
            "abstract_ruling": ruling["ruling"] if ruling else None,
        }
    return out


def variant_nodes(population: dict[str, dict], variant: str) -> set[str]:
    if variant == "V-ALL":
        return {k for k, v in population.items() if v["eligibility"] != "EXCLUDED_NOT_A_DEITY"}
    if variant == "V-RULED":
        return {k for k, v in population.items() if v["eligibility"] == "ELIGIBLE"}
    if variant == "V-NONE":
        return {
            k
            for k, v in population.items()
            if v["eligibility"] == "ELIGIBLE" and v["abstract_ruling"] is None
        }
    raise ValueError(variant)


# ======================================================================================
# Projections
# ======================================================================================


def load_dedication(driver) -> list[dict]:
    return run(
        driver,
        """
        MATCH (m:Mantra {veda:'RV'})-[:HAS_DEVATA]->(d:Devata)
        RETURN m.canonical_key AS mantra_key, m.parent_key AS hymn_key,
               d.entity_key AS devata_key
        ORDER BY hymn_key, mantra_key, devata_key
        """,
    )


def load_mentions(driver) -> list[dict]:
    return run(
        driver,
        """
        MATCH (m:Mantra)-[:MENTIONS_DEVATA]->(d:Devata)
        RETURN m.canonical_key AS mantra_key, m.veda AS veda, d.entity_key AS devata_key
        ORDER BY mantra_key, devata_key
        """,
    )


def build_projection(groups: dict[str, set[str]], keep: set[str]) -> dict:
    """Turn container -> {member} into an undirected weighted graph of co-members.

    ``groups`` is the *unit of co-occurrence* -- a hymn for the co-dedication projection, a
    mantra for the co-mention one -- and swapping it is the whole difference between the
    two projections. Nothing else in this function changes.

    Three weightings are returned, not one, because the choice is not neutral:

    * ``RAW`` -- the number of containers holding both. Indra appears in 1,500-odd hymns and
      a one-hymn charm label appears in one, so RAW makes every edge touching a hub the
      heaviest edge in the graph and the partition becomes a description of which deities
      are frequent. Modularity's null model is already degree-corrected, so this is not as
      bad as it sounds, but it is still the weighting that lets frequency dominate.
    * ``JACCARD`` -- |A and B| / |A or B|. Bounded, symmetric, degree-corrected. The cost is
      real and must be stated: it *suppresses* a genuine hub-to-hub link, because Indra and
      Agni can share 40 hymns and still score low when each appears in hundreds. Jaccard
      moves the hubs towards the periphery of their own communities.
    * ``COSINE`` -- |A and B| / sqrt(|A| * |B|), the Ochiai coefficient. Sits between the
      two: degree-corrected but less punitive to the hubs than Jaccard.

    Raw counts are kept in every edge record whichever weighting drives the algorithm, so a
    reader can always recompute.
    """
    containers_of: dict[str, set[str]] = defaultdict(set)
    for container, members in groups.items():
        for member in members & keep:
            containers_of[member].add(container)

    pair_containers: dict[tuple[str, str], set[str]] = defaultdict(set)
    for container, members in groups.items():
        present = sorted(members & keep)
        for a, b in itertools.combinations(present, 2):
            pair_containers[(a, b)].add(container)

    edges: dict[str, list[tuple[str, str, float]]] = {w: [] for w in CONFIG["weightings"]}
    records: list[dict] = []
    for (a, b), shared in sorted(pair_containers.items()):
        support = len(shared)
        if support < CONFIG["min_pair_weight"]:
            continue
        union = len(containers_of[a] | containers_of[b])
        jaccard = support / union if union else 0.0
        cosine = support / ((len(containers_of[a]) * len(containers_of[b])) ** 0.5)
        edges["RAW"].append((a, b, float(support)))
        edges["JACCARD"].append((a, b, jaccard))
        edges["COSINE"].append((a, b, cosine))
        records.append(
            {
                "a": a,
                "b": b,
                "support": support,
                "a_containers": len(containers_of[a]),
                "b_containers": len(containers_of[b]),
                "union_containers": union,
                "jaccard": round(jaccard, 6),
                "cosine": round(cosine, 6),
                "example_containers": sorted(shared)[:5],
            }
        )

    nodes = sorted(containers_of)
    # A deity that is only ever dedicated alone has degree zero here. It is NOT given a
    # singleton community: the algorithms run on the connected part and an isolate is typed
    # as NO_EDGE_IN_PROJECTION_DEGREE_ZERO. Handing each isolate its own community would
    # inflate the community count with 40-odd groups of one and let a reader read "44
    # communities" where the honest statement is "44 deities this projection cannot place".
    connected = sorted({x for a, b, _ in edges["RAW"] for x in (a, b)})
    graphs = {w: Graph.from_edges(connected, e) for w, e in edges.items()}
    return {
        "nodes": nodes,
        "connected_nodes": connected,
        "isolates": sorted(set(nodes) - set(connected)),
        "graphs": graphs,
        "edge_records": records,
        "containers_of": {k: sorted(v) for k, v in containers_of.items()},
    }


# ======================================================================================
# Running the algorithms and measuring stability
# ======================================================================================


def sweep_resolution(graph: Graph, algorithm, seed: int) -> list[dict]:
    reference = algorithm(graph, 1.0, seed)
    out = []
    for gamma in CONFIG["resolution_ladder"]:
        partition = algorithm(graph, gamma, seed)
        sizes = Counter(partition.values())
        out.append(
            {
                "resolution": gamma,
                "communities": len(sizes),
                "largest_community": max(sizes.values()),
                "singletons": sum(1 for v in sizes.values() if v == 1),
                "modularity_at_this_gamma": round(modularity(graph, partition, gamma), 6),
                "modularity_at_gamma_1": round(modularity(graph, partition, 1.0), 6),
                "ari_vs_gamma_1": round(adjusted_rand_index(partition, reference), 6),
            }
        )
    return out


def seed_stability(graph: Graph, algorithm, resolution: float, seeds: list[int]) -> dict:
    """Run every seed and report how much the partition moves, three independent ways.

    A single number would hide the thing that matters. The community *count* can be stable
    while membership churns, and mean ARI can look healthy while a handful of nodes move
    every single run. So all three are reported: the count distribution, the pairwise ARI
    distribution, and -- the one the brief asks for literally -- the per-node fraction of
    runs in which the node sits in its consensus community.
    """
    nodes = list(graph.nodes)
    partitions = [algorithm(graph, resolution, s) for s in seeds]
    counts = Counter(len(set(p.values())) for p in partitions)
    qs = [modularity(graph, p, resolution) for p in partitions]

    sample = partitions[: min(40, len(partitions))]
    aris = [
        adjusted_rand_index(sample[i], sample[j])
        for i in range(len(sample))
        for j in range(i + 1, len(sample))
    ]
    nmis = [
        normalised_mutual_information(sample[i], sample[j])
        for i in range(len(sample))
        for j in range(i + 1, len(sample))
    ]

    consensus = consensus_partition(partitions, nodes, CONFIG["consensus_threshold"])
    agreement: dict[str, int] = {n: 0 for n in nodes}
    for partition in partitions:
        matched = match_to_reference(partition, consensus)
        for node in nodes:
            if matched[node] == consensus[node]:
                agreement[node] += 1
    per_node = {n: agreement[n] / len(partitions) for n in nodes}

    disconnected = sum(1 for p in partitions if communities_are_connected(graph, p))

    best_index = max(range(len(partitions)), key=lambda i: qs[i])
    return {
        "runs": len(partitions),
        "resolution": resolution,
        "community_count_distribution": dict(sorted(counts.items())),
        "modularity_mean": round(statistics.mean(qs), 6),
        "modularity_stdev": round(statistics.stdev(qs), 6) if len(qs) > 1 else 0.0,
        "modularity_min": round(min(qs), 6),
        "modularity_max": round(max(qs), 6),
        "best_seed": seeds[best_index],
        "pairwise_ari_pairs_compared": len(aris),
        "pairwise_ari_mean": round(statistics.mean(aris), 6),
        "pairwise_ari_min": round(min(aris), 6),
        "pairwise_ari_median": round(statistics.median(aris), 6),
        "pairwise_nmi_mean": round(statistics.mean(nmis), 6),
        "identical_partition_fraction": round(sum(1 for a in aris if a > 0.9999) / len(aris), 6),
        "runs_with_a_disconnected_community": disconnected,
        "consensus_communities": len(set(consensus.values())),
        "consensus_modularity": round(modularity(graph, consensus, resolution), 6),
        "node_stability_mean": round(statistics.mean(per_node.values()), 6),
        "node_stability_min": round(min(per_node.values()), 6),
        "nodes_always_in_consensus_community": sum(1 for v in per_node.values() if v == 1.0),
        "nodes_below_0_9_stability": sum(1 for v in per_node.values() if v < 0.9),
        "nodes_below_0_5_stability": sum(1 for v in per_node.values() if v < 0.5),
        "_partitions": partitions,
        "_consensus": consensus,
        "_per_node": per_node,
        "_best": partitions[best_index],
    }


# ======================================================================================
# GDS cross-check -- optional, nothing depends on it
# ======================================================================================


def gds_cross_check(driver, keep: set[str], mine_louvain, mine_leiden) -> dict:
    """Run GDS's own Louvain and Leiden over the same projection and compare by ARI.

    A note on the read-only rule. `gds.graph.project` writes nothing to the store: it builds
    an entry in the in-memory graph catalog, which is dropped at the end of this function,
    and the node and relationship totals are re-counted afterwards to prove it. If that
    reading is not accepted, delete this function -- every published number comes from
    community_algorithms.py and none of them changes.
    """
    name = "vg_agent15_codedication_probe"
    result: dict[str, object] = {"attempted": True}
    try:
        result["gds_version"] = run(driver, "RETURN gds.version() AS v")[0]["v"]
    except Exception as error:
        result["gds_version"] = f"unavailable: {type(error).__name__}"
    try:
        run(driver, "CALL gds.graph.drop($n, false) YIELD graphName RETURN graphName", n=name)
    except Exception:
        pass

    try:
        projected = run(
            driver,
            """
            MATCH (h:Passage {veda:'RV', entity_type:'HYMN'})-[:CONTAINS]->(:Mantra)
                  -[:HAS_DEVATA]->(a:Devata)
            MATCH (h)-[:CONTAINS]->(:Mantra)-[:HAS_DEVATA]->(b:Devata)
            WHERE a.entity_key < b.entity_key
              AND a.entity_key IN $keys AND b.entity_key IN $keys
            WITH a, b, count(DISTINCT h) AS support
            RETURN gds.graph.project(
                $name, a, b,
                {relationshipProperties: {support: toFloat(support)}},
                {undirectedRelationshipTypes: ['*']}
            ) AS g
            """,
            keys=sorted(keep),
            name=name,
        )
        info = projected[0]["g"]
        result["projected_nodes"] = info.get("nodeCount")
        result["projected_relationships"] = info.get("relationshipCount")

        # gds.louvain has no randomSeed key in 2.13 and rejects an unexpected key outright,
        # which is the right behaviour and the reason the config is per-procedure here.
        for label, procedure, extra in (
            ("louvain", "gds.louvain.stream", {}),
            ("leiden", "gds.leiden.stream", {"gamma": 1.0, "randomSeed": 42}),
        ):
            rows = run(
                driver,
                f"CALL {procedure}($name, $cfg) YIELD nodeId, communityId "
                "RETURN gds.util.asNode(nodeId).entity_key AS key, communityId AS community",
                name=name,
                cfg={"relationshipWeightProperty": "support", **extra},
            )
            gds_partition = {r["key"]: r["community"] for r in rows}
            mine = mine_louvain if label == "louvain" else mine_leiden
            shared = sorted(set(gds_partition) & set(mine))

            # Repeat the identical call. A server-side algorithm's determinism is not part
            # of this artifact and cannot be asserted from outside it, so it is measured:
            # gds.leiden with randomSeed=42 was observed returning a different number of
            # communities on consecutive identical calls, which is the concrete reason
            # nothing published here may depend on GDS.
            repeats = []
            for _ in range(5):
                again = run(
                    driver,
                    f"CALL {procedure}($name, $cfg) YIELD nodeId, communityId "
                    "RETURN gds.util.asNode(nodeId).entity_key AS key, "
                    "communityId AS community",
                    name=name,
                    cfg={"relationshipWeightProperty": "support", **extra},
                )
                repeats.append(len({r["community"] for r in again}))

            result[label] = {
                "community_count_on_5_identical_repeat_calls": repeats,
                "gds_is_reproducible_across_identical_calls": len(set(repeats)) == 1,
                "gds_communities": len(set(gds_partition.values())),
                "mine_communities": len(set(mine[n] for n in shared)),
                "nodes_compared": len(shared),
                "ari_gds_vs_mine": round(
                    adjusted_rand_index(
                        {n: gds_partition[n] for n in shared}, {n: mine[n] for n in shared}
                    ),
                    6,
                ),
                "nmi_gds_vs_mine": round(
                    normalised_mutual_information(
                        {n: gds_partition[n] for n in shared}, {n: mine[n] for n in shared}
                    ),
                    6,
                ),
            }
    except Exception as error:  # pragma: no cover - environment dependent
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        try:
            run(driver, "CALL gds.graph.drop($n, false) YIELD graphName RETURN graphName", n=name)
            result["in_memory_graph_dropped"] = True
        except Exception:
            result["in_memory_graph_dropped"] = False
    return result


# ======================================================================================
# Serialisation
# ======================================================================================


def sha256_of(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(path: pathlib.Path, rows) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: pathlib.Path, payload) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def code_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def config_hash() -> str:
    return hashlib.sha256(
        json.dumps(CONFIG, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


# ======================================================================================
# main
# ======================================================================================


def main() -> int:
    created_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    commit = code_commit()
    cfg_hash = config_hash()
    rulings_raw = json.loads((HERE / CONFIG["abstract_rulings_file"]).read_text(encoding="utf-8"))
    rulings = {r["key"]: r for r in rulings_raw["rulings"]}

    driver = open_driver()
    try:
        counts_before = graph_counts(driver)
        deities = load_deities(driver)
        dedication = load_dedication(driver)
        mentions = load_mentions(driver)
        existing = run(
            driver,
            """
            MATCH (a:Devata)-[r:CO_OCCURS_WITH]->(b:Devata)
            RETURN a.entity_key AS a, b.entity_key AS b, r.passage_count AS passage_count,
                   r.lift AS lift, r.method AS method, r.per_veda_counts AS per_veda_counts
            ORDER BY a, b
            """,
        )
        av_ascriptions = run(
            driver,
            """
            MATCH (m:Mantra {veda:'AV'})-[:HAS_DEVATA_ASCRIPTION]->(d:DevataAscription)
            WITH d, count(m) AS mantras, collect(m.canonical_key)[0..3] AS examples
            OPTIONAL MATCH (d)--(x:Devata)
            RETURN d.entity_key AS key, d.label_iast AS label_iast,
                   d.short_description AS short_description, mantras, examples,
                   count(x) AS devata_links
            ORDER BY key
            """,
        )
        av_counts = run(
            driver,
            """
            MATCH (m:Mantra {veda:'AV'})-[:HAS_DEVATA_ASCRIPTION]->(d:DevataAscription)
            WITH m, count(DISTINCT d) AS k
            RETURN count(*) AS mantras, sum(CASE WHEN k >= 2 THEN 1 ELSE 0 END) AS multi
            """,
        )[0]
        av_dedicated_mantras = av_counts["mantras"]
        av_pair_count = av_counts["multi"]

        population = classify_population(deities, rulings)

        # ---------------- projections -------------------------------------------------
        hymn_groups: dict[str, set[str]] = defaultdict(set)
        verses_of: dict[tuple[str, str], list[str]] = defaultdict(list)
        for row in dedication:
            hymn_groups[row["hymn_key"]].add(row["devata_key"])
            verses_of[(row["hymn_key"], row["devata_key"])].append(row["mantra_key"])

        mantra_groups: dict[str, set[str]] = defaultdict(set)
        mantra_veda: dict[str, str] = {}
        for row in mentions:
            mantra_groups[row["mantra_key"]].add(row["devata_key"])
            mantra_veda[row["mantra_key"]] = row["veda"]

        variants = {v: variant_nodes(population, v) for v in CONFIG["population_variants"]}
        projections = {
            v: build_projection(hymn_groups, variants[v]) for v in CONFIG["population_variants"]
        }
        comention = build_projection(mantra_groups, variants[CONFIG["primary_population_variant"]])
        comention_all = build_projection(mantra_groups, set(deities))

        primary_variant = CONFIG["primary_population_variant"]
        primary = projections[primary_variant]
        primary_graph = primary["graphs"][CONFIG["primary_weighting"]]

        # ---------------- algorithm comparison ----------------------------------------
        algorithms = {"louvain": louvain, "leiden": leiden}
        method_table: dict[str, dict] = {}
        for weighting in CONFIG["weightings"]:
            graph = primary["graphs"][weighting]
            for name, fn in algorithms.items():
                key = f"{name}|{weighting}"
                method_table[key] = seed_stability(
                    graph, fn, CONFIG["primary_resolution"], CONFIG["seeds"]
                )

        resolution_table = {
            f"{name}|{CONFIG['primary_weighting']}": sweep_resolution(primary_graph, fn, 0)
            for name, fn in algorithms.items()
        }

        primary_key = f"{CONFIG['primary_algorithm']}|{CONFIG['primary_weighting']}"
        published = method_table[primary_key]["_consensus"]
        published_stability = method_table[primary_key]["_per_node"]

        # variant sensitivity: does the ABSTRACT ruling move the partition?
        variant_partitions: dict[str, dict[str, int]] = {}
        for variant in CONFIG["population_variants"]:
            graph = projections[variant]["graphs"][CONFIG["primary_weighting"]]
            runs = [
                algorithms[CONFIG["primary_algorithm"]](graph, CONFIG["primary_resolution"], s)
                for s in CONFIG["seeds"][:60]
            ]
            variant_partitions[variant] = consensus_partition(
                runs, list(graph.nodes), CONFIG["consensus_threshold"]
            )
        variant_sensitivity = []
        for a, b in itertools.combinations(CONFIG["population_variants"], 2):
            shared = sorted(set(variant_partitions[a]) & set(variant_partitions[b]))
            variant_sensitivity.append(
                {
                    "pair": f"{a} vs {b}",
                    "nodes_in_a": len(variant_partitions[a]),
                    "nodes_in_b": len(variant_partitions[b]),
                    "nodes_shared": len(shared),
                    "communities_a": len(set(variant_partitions[a].values())),
                    "communities_b": len(set(variant_partitions[b].values())),
                    "ari_on_shared_nodes": round(
                        adjusted_rand_index(
                            {n: variant_partitions[a][n] for n in shared},
                            {n: variant_partitions[b][n] for n in shared},
                        ),
                        6,
                    ),
                }
            )

        # co-mention comparison, on the nodes the two projections share
        comention_graph = comention["graphs"][CONFIG["primary_weighting"]]
        comention_runs = [
            algorithms[CONFIG["primary_algorithm"]](comention_graph, 1.0, s)
            for s in CONFIG["seeds"][:60]
        ]
        comention_consensus = consensus_partition(
            comention_runs, list(comention_graph.nodes), CONFIG["consensus_threshold"]
        )
        shared_nodes = sorted(set(published) & set(comention_consensus))
        projection_sensitivity = {
            "codedication_nodes": len(published),
            "comention_nodes": len(comention_consensus),
            "shared_nodes": len(shared_nodes),
            "codedication_communities": len(set(published.values())),
            "comention_communities": len(set(comention_consensus.values())),
            "ari_on_shared_nodes": round(
                adjusted_rand_index(
                    {n: published[n] for n in shared_nodes},
                    {n: comention_consensus[n] for n in shared_nodes},
                ),
                6,
            )
            if len(shared_nodes) > 1
            else None,
        }

        # reproduction of the existing 306-edge layer
        mine_pairs = {(r["a"], r["b"]): r["support"] for r in comention_all["edge_records"]}
        existing_pairs = {
            tuple(sorted((r["a"], r["b"]))): r["passage_count"] for r in existing
        }
        reproduced = sum(
            1 for p, v in existing_pairs.items() if mine_pairs.get(p) == v
        )
        threshold_match = {
            t: sorted(p for p, v in mine_pairs.items() if v >= t) == sorted(existing_pairs)
            for t in range(1, 9)
        }

        # Compared against the RAW-weighted partitions, not the reference COSINE ones: the
        # GDS projection's relationship property is the raw shared-hymn count, and comparing
        # it against a cosine-weighted partition would price a weighting difference as an
        # implementation disagreement.
        gds = gds_cross_check(
            driver,
            variants[primary_variant],
            method_table["louvain|RAW"]["_best"],
            method_table["leiden|RAW"]["_best"],
        )
        counts_after = graph_counts(driver)
    finally:
        driver.close()

    # ---------------- community records ----------------------------------------------
    members: dict[int, list[str]] = defaultdict(list)
    for key, community in published.items():
        members[community].append(key)
    community_size = {c: len(v) for c, v in members.items()}

    # How many DISTINCT hymns supply a community's internal edges. This is the single most
    # important interpretive guard in the artifact, and it is a measurement rather than a
    # worry: a community whose every internal edge comes from one sukta is not a community
    # of deities at all, it is that hymn's cast list. Six of the twelve are.
    hymn_support: dict[int, Counter] = defaultdict(Counter)
    for hymn, deity_set in hymn_groups.items():
        present = sorted(deity_set & set(published))
        for a, b in itertools.combinations(present, 2):
            if published[a] == published[b]:
                hymn_support[published[a]][hymn] += 1
    # And how many of them are simply a separate connected component -- a grouping that
    # needs no community detection at all, because nothing connects it to the rest of the
    # graph. Counting those as "communities the algorithm found" overstates what it did.
    component_of = {
        node: index
        for index, component in enumerate(connected_components(primary_graph))
        for node in component
    }
    component_sizes = Counter(component_of.values())

    hymn_profile = {}
    for community in sorted(members):
        counter = hymn_support.get(community, Counter())
        total = sum(counter.values())
        top, top_value = counter.most_common(1)[0] if counter else (None, 0)
        own_components = {component_of[k] for k in members[community]}
        hymn_profile[community] = {
            "hymns_supplying_internal_edges": len(counter),
            "densest_hymn": top,
            "densest_hymn_share_of_internal_support": (
                round(top_value / total, 4) if total else None
            ),
            "is_a_single_hymn_cast_list": len(counter) == 1,
            "is_a_whole_connected_component": len(own_components) == 1
            and component_sizes[next(iter(own_components))] == len(members[community]),
        }

    projection_definition = {
        "projection_id": CONFIG["primary_projection"],
        "unit_of_co_occurrence": "RV sukta (entity_type=HYMN), reached as the mantra's parent_key",
        "node_population": "(:Devata) nodes, cleaned -- see population_filter",
        "edge_rule": (
            "an undirected edge {a,b} exists when at least one RV sukta has a mantra "
            "dedicated to a and a mantra dedicated to b, via "
            "(:Mantra {veda:'RV'})-[:HAS_DEVATA]->(:Devata)"
        ),
        "cypher": (
            "MATCH (m:Mantra {veda:'RV'})-[:HAS_DEVATA]->(d:Devata) "
            "RETURN m.canonical_key, m.parent_key, d.entity_key"
        ),
        "population_filter": (
            "exclude curated structure in ('HUMAN','PATRON_PRAISE') [29 nodes, agent 8]; "
            "exclude the 28 ABSTRACT/UNSPECIFIED labels ruled NOT_DEITY in "
            "abstract_label_rulings.json; keep the 5 ruled UNDECIDED; keep every ritual "
            "implement"
        ),
        "population_variant": primary_variant,
        "weighting": CONFIG["primary_weighting"],
        "weight_formula": "|hymns(a) intersect hymns(b)| / |hymns(a) union hymns(b)|",
        "min_pair_weight": CONFIG["min_pair_weight"],
        "vedas_reached": ["RV"],
        "vedas_not_reached": {
            "AV": (
                "HAS_DEVATA_ASCRIPTION targets 324 :DevataAscription nodes, 0 of which are "
                ":Devata (GAP-ATTRIBUTION-002). Not joinable to this projection."
            ),
            "SV": "no dedication predicate of any kind exists for the Samaveda.",
            "YV": "no dedication predicate of any kind exists for the Yajurveda.",
        },
        "occurrence_count_not_used": (
            "occurrence_count is null on all 214 :Devata nodes (GAP-QUALITY-006). Every "
            "weight here is derived from edges, never from a stored aggregate."
        ),
    }

    run_block = {
        "source_snapshot": SOURCE_CODED,
        "algorithm_version": CONFIG["algorithm_version"],
        "config_hash": cfg_hash,
        "code_commit": commit,
        "graph_snapshot": counts_before,
    }

    # ---------------- rows.jsonl (hymn-grained, so every key resolves) ---------------
    hymn_keys = sorted(hymn_groups)
    positive = 0
    rows: list[dict] = []
    for hymn in hymn_keys:
        all_deities = sorted(hymn_groups[hymn])
        eligible = [k for k in all_deities if k in variants[primary_variant]]
        in_projection = [k for k in eligible if k in published]
        pairs = [
            [a, b] for a, b in itertools.combinations(sorted(in_projection), 2)
        ]
        if pairs:
            positive += 1
            role = "CONTRIBUTES_EDGES"
        elif len(eligible) == 1:
            role = "SINGLE_ELIGIBLE_DEITY_CONTRIBUTES_NO_EDGE"
        elif not eligible:
            role = "NO_ELIGIBLE_DEITY_AFTER_CLEANING"
        else:
            role = "ELIGIBLE_DEITIES_PRESENT_BUT_NONE_REACHES_THE_PROJECTION"

        deity_rows = []
        for key in all_deities:
            node = population[key]
            community = published.get(key)
            deity_rows.append(
                {
                    "devata_key": key,
                    "label_en": node["label_en"],
                    "label_iast": node["label_iast"],
                    "curated_structure": node["structure"],
                    "eligibility": node["eligibility"],
                    "eligibility_reason": node["eligibility_reason"],
                    "abstract_ruling": node["abstract_ruling"],
                    "dedicating_verses": sorted(verses_of[(hymn, key)]),
                    "community_id": community,
                    "community_state": (
                        "ASSIGNED"
                        if community is not None
                        else (
                            "NOT_IN_POPULATION"
                            if node["eligibility"] != "ELIGIBLE"
                            else "NO_EDGE_IN_PROJECTION_DEGREE_ZERO"
                        )
                    ),
                    "community_size": community_size.get(community),
                    "community_is_a_single_hymn_cast_list": (
                        hymn_profile[community]["is_a_single_hymn_cast_list"]
                        if community is not None
                        else None
                    ),
                    "node_stability_over_200_seeds": (
                        round(published_stability[key], 4) if key in published_stability else None
                    ),
                }
            )

        rows.append(
            {
                "canonical_key": hymn,
                "veda": "RV",
                "evidence_layer": "DETERMINISTIC_DERIVED",
                "source_id": SOURCE_CODED,
                "source_locator": (
                    f"co-dedication projection {CONFIG['primary_projection']} at "
                    f"{counts_before['nodes']}/{counts_before['relationships']}, sukta {hymn}, "
                    f"{len(all_deities)} dedicated devata label(s) over "
                    f"{len({m for k in all_deities for m in verses_of[(hymn, k)]})} mantra(s)"
                ),
                "source_url": "internal: the canonical VedaGraph store, read-only",
                "quality_class": "TRADITIONAL_INDEX",
                "mapping_method": (
                    "canonical_key is the sukta's own parent_key as stored on its mantras; "
                    "no mapping performed"
                ),
                "mapping_confidence": "EXACT",
                "recension_verified": True,
                "recension_evidence": RECENSION_EVIDENCE_RV,
                "payload": {
                    "veda": "RV",
                    "projection_role": role,
                    "devatas": deity_rows,
                    "contributed_pairs": pairs,
                    "dedicated_devata_count": len(all_deities),
                    "eligible_devata_count": len(eligible),
                    "excluded_devata_count": len(all_deities) - len(eligible),
                    "caveat": CAVEAT,
                    "partition": {
                        "algorithm": CONFIG["primary_algorithm"],
                        "algorithm_version": CONFIG["algorithm_version"],
                        "seed": "consensus over 200 seeds (0-199) at threshold 0.5",
                        "resolution": CONFIG["primary_resolution"],
                        "weighting": CONFIG["primary_weighting"],
                        "projection": projection_definition,
                    },
                    "run": run_block,
                    "evaluation": {
                        "population": len(hymn_keys),
                        "processed_count": len(hymn_keys),
                        "positive_count": None,  # filled below, once counted
                        "method": (
                            "deterministic; every RV sukta carrying HAS_DEVATA is assessed and "
                            "typed, so a sukta that contributes no edge is a measured zero "
                            "rather than an absent row"
                        ),
                        "human_reviewed": 0,
                    },
                },
            }
        )
    for row in rows:
        row["payload"]["evaluation"]["positive_count"] = positive

    # ---------------- rejected.jsonl --------------------------------------------------
    # The projection over the *uncleaned* population, so each rejected row can say whether
    # excluding it actually removed an edge. A rejection that changed nothing and one that
    # removed a hub are not the same event and the ledger should not render them alike.
    uncleaned = build_projection(hymn_groups, set(deities))
    uncleaned_connected = set(uncleaned["connected_nodes"])
    rejected = []
    for key, node in sorted(population.items()):
        if node["eligibility"] == "ELIGIBLE":
            continue
        rejected.append(
            {
                "candidate_unit": "DEVATA_NODE",
                "candidate_key": key,
                "label_en": node["label_en"],
                "label_iast": node["label_iast"],
                "curated_structure": node["structure"],
                "dedications": node["dedications"],
                "hymns": node["hymns"],
                "rejection_class": node["eligibility"],
                "reason": node["eligibility_reason"],
                "curation_note": node["curation_note"],
                "would_have_carried_edges_if_kept": key in uncleaned_connected,
                "co_dedicated_partners_removed_with_it": sorted(
                    {
                        (r["b"] if r["a"] == key else r["a"])
                        for r in uncleaned["edge_records"]
                        if key in (r["a"], r["b"])
                    }
                ),
                "source_id": SOURCE_TAXONOMY,
            }
        )

    # ---------------- sources.jsonl ---------------------------------------------------
    sources = [
        {
            "source_id": SOURCE_CODED,
            "title": "VedaGraph canonical store -- Rigvedic co-dedication projection",
            "kind": "INTERNAL_GRAPH_READ",
            "quality_class": "TRADITIONAL_INDEX",
            "url": "internal: bolt://localhost:7687, database neo4j, read-only",
            "snapshot": counts_before,
            "underlying_authority": (
                "WSC2023 Rigvedic Anukramani projection, already ingested as HAS_DEVATA. This "
                "artifact adds no new external source; it derives a partition from what the "
                "index already states."
            ),
            "retrieved_at": created_at,
            "licence": "internal project data",
        },
        {
            "source_id": SOURCE_COMENTION,
            "title": "VedaGraph canonical store -- four-Veda theonym co-mention projection",
            "kind": "INTERNAL_GRAPH_READ",
            "quality_class": "MODEL_ASSISTED_DERIVATION",
            "url": "internal: bolt://localhost:7687, database neo4j, read-only",
            "snapshot": counts_before,
            "underlying_authority": (
                "MENTIONS_DEVATA, which is manual Zurich annotation for the Rigveda and "
                "adjudicated Sanskrit surface matching for SV/YV/AV. Used for comparison "
                "only. A mention is not a dedication."
            ),
            "retrieved_at": created_at,
            "licence": "internal project data",
        },
        {
            "source_id": SOURCE_TAXONOMY,
            "title": "Devata Taxonomy V1 curated `structure`, as stored on the :Devata nodes",
            "kind": "CURATED_REGISTRY",
            "quality_class": "SCHOLARLY_EDITION",
            "url": (
                "data/domain/vedagraph_domain_v2/devata_taxonomy.yaml "
                "(docs/reports/DEVATA_TAXONOMY_V1.md)"
            ),
            "snapshot": {"devata_nodes": len(deities)},
            "underlying_authority": (
                "the curator's own per-entity structure and curation_note. Every exclusion in "
                "rejected.jsonl is taken from this field, never from a name heuristic."
            ),
            "retrieved_at": created_at,
            "licence": "internal project data",
        },
    ]

    # ---------------- communities.jsonl (the deity-grained deliverable) --------------
    community_records = []
    for community in sorted(members):
        keys = sorted(members[community])
        internal = 0.0
        external = 0.0
        for record in primary["edge_records"]:
            a, b = record["a"], record["b"]
            if a in keys and b in keys:
                internal += record["support"]
            elif a in keys or b in keys:
                external += record["support"]
        top = sorted(keys, key=lambda k: -population[k]["dedications"])
        community_records.append(
            {
                "community_id": community,
                "algorithm": CONFIG["primary_algorithm"],
                "algorithm_version": CONFIG["algorithm_version"],
                "seed": "consensus over seeds 0-199 at co-assignment threshold 0.5",
                "resolution": CONFIG["primary_resolution"],
                "weighting": CONFIG["primary_weighting"],
                "projection": projection_definition,
                "config_hash": cfg_hash,
                "code_commit": commit,
                "source_snapshot": SOURCE_CODED,
                "size": len(keys),
                "members": [
                    {
                        "devata_key": k,
                        "label_en": population[k]["label_en"],
                        "label_iast": population[k]["label_iast"],
                        "curated_structure": population[k]["structure"],
                        "abstract_ruling": population[k]["abstract_ruling"],
                        "dedications": population[k]["dedications"],
                        "hymns": population[k]["hymns"],
                        "stability_over_200_seeds": round(published_stability[k], 4),
                    }
                    for k in top
                ],
                "evidence": {
                    "internal_hymn_pair_support": internal,
                    "external_hymn_pair_support": external,
                    "example_shared_hymns": sorted(
                        {
                            h
                            for record in primary["edge_records"]
                            if record["a"] in keys and record["b"] in keys
                            for h in record["example_containers"]
                        }
                    )[:8],
                    "edges_inside": [
                        {
                            "a": r["a"],
                            "b": r["b"],
                            "shared_hymns": r["support"],
                            "jaccard": r["jaccard"],
                            "example_hymns": r["example_containers"],
                        }
                        for r in primary["edge_records"]
                        if r["a"] in keys and r["b"] in keys
                    ][:40],
                },
                "hymn_profile": hymn_profile[community],
                "caveat": CAVEAT,
                "interpretation_warning": (
                    "This community has no name and must not be given one in a product "
                    "surface. Naming it would convert a co-occurrence statistic into a "
                    "theological claim."
                )
                + (
                    " AND IN THIS CASE IT IS NOT EVEN A GROUP OF DEITIES: every internal "
                    f"edge of this community comes from the single hymn "
                    f"{hymn_profile[community]['densest_hymn']}, so what the algorithm found "
                    "is that hymn's own list of dedicatees."
                    if hymn_profile[community]["is_a_single_hymn_cast_list"]
                    else ""
                ),
            }
        )

    # ---------------- write ------------------------------------------------------------
    write_jsonl(HERE / "rows.jsonl", rows)
    write_jsonl(HERE / "rejected.jsonl", rejected)
    write_jsonl(HERE / "sources.jsonl", sources)
    write_jsonl(HERE / "communities.jsonl", community_records)

    proofs = HERE / "proofs"
    proofs.mkdir(exist_ok=True)

    write_json(
        proofs / "projection_definition.json",
        {
            "primary": projection_definition,
            "comparison": {
                "projection_id": CONFIG["comparison_projection"],
                "unit_of_co_occurrence": "a single mantra, any Veda",
                "edge_rule": (
                    "(:Mantra)-[:MENTIONS_DEVATA]->(:Devata); two deities joined when the "
                    "same mantra mentions both"
                ),
                "vedas_reached": ["RV", "SV", "YV", "AV"],
                "why_it_is_not_the_primary": (
                    "a mention is not a dedication, the brief forbids inferring one from the "
                    "other, and this layer reaches only 42 of 214 :Devata nodes"
                ),
            },
            "why_mantra_scope_co_dedication_was_rejected": {
                # Counted from the dedication rows, not typed in. A measurement typed into a
                # proof file is the one nothing can check, which is this project's own
                # recorded lesson about figures in prose -- and a proof file is prose with
                # braces.
                "rv_devatas_per_mantra_histogram": {
                    str(k): v
                    for k, v in sorted(
                        Counter(
                            Counter(r["mantra_key"] for r in dedication).values()
                        ).items()
                    )
                },
                "resulting_edges": sum(
                    len(list(itertools.combinations(range(k), 2))) * v
                    for k, v in Counter(
                        Counter(r["mantra_key"] for r in dedication).values()
                    ).items()
                ),
                "verdict": "not a graph; measured, not assumed",
            },
        },
    )

    write_json(
        proofs / "population_cleaning.json",
        {
            "devata_nodes": len(deities),
            "curated_structure_distribution": dict(
                sorted(Counter(v["structure"] for v in deities.values()).items())
            ),
            "excluded_not_a_deity": {
                "count": sum(
                    1 for v in population.values() if v["eligibility"] == "EXCLUDED_NOT_A_DEITY"
                ),
                "dedications_carried": sum(
                    v["dedications"]
                    for v in population.values()
                    if v["eligibility"] == "EXCLUDED_NOT_A_DEITY"
                ),
                "verified_against": "agent 8's figure of 29 nodes carrying 171 dedications",
            },
            "abstract_rulings": dict(
                sorted(Counter(r["ruling"] for r in rulings.values()).items())
            ),
            "eligible_by_variant": {v: len(variants[v]) for v in CONFIG["population_variants"]},
            "placeable_by_variant": {
                v: {
                    "eligible": len(projections[v]["nodes"]),
                    "placed_in_a_community": len(projections[v]["connected_nodes"]),
                    "unplaceable_degree_zero": len(projections[v]["isolates"]),
                }
                for v in CONFIG["population_variants"]
            },
            "occurrence_count_present_on": sum(
                1 for v in deities.values() if v.get("occurrence_count") is not None
            ),
            "ritual_implements_retained": [
                k
                for k, v in population.items()
                if v["eligibility"] == "ELIGIBLE"
                and v["axes"]
                and "RITUAL_OBJECT" in (v["axes"] or [])
            ],
        },
    )

    write_json(
        proofs / "method_comparison.json",
        {
            key: {k: v for k, v in table.items() if not k.startswith("_")}
            for key, table in method_table.items()
        },
    )
    write_json(proofs / "resolution_sensitivity.json", resolution_table)
    write_json(
        proofs / "partition_sensitivity.json",
        {
            "population_variant_sensitivity": variant_sensitivity,
            "projection_sensitivity_codedication_vs_comention": projection_sensitivity,
            "weighting_sensitivity": [
                {
                    "pair": f"{a} vs {b}",
                    "ari": round(
                        adjusted_rand_index(
                            method_table[f"{CONFIG['primary_algorithm']}|{a}"]["_consensus"],
                            method_table[f"{CONFIG['primary_algorithm']}|{b}"]["_consensus"],
                        ),
                        6,
                    ),
                    "communities_a": len(
                        set(
                            method_table[f"{CONFIG['primary_algorithm']}|{a}"][
                                "_consensus"
                            ].values()
                        )
                    ),
                    "communities_b": len(
                        set(
                            method_table[f"{CONFIG['primary_algorithm']}|{b}"][
                                "_consensus"
                            ].values()
                        )
                    ),
                }
                for a, b in itertools.combinations(CONFIG["weightings"], 2)
            ],
            "louvain_vs_leiden_consensus_ari": round(
                adjusted_rand_index(
                    method_table[f"louvain|{CONFIG['primary_weighting']}"]["_consensus"],
                    method_table[f"leiden|{CONFIG['primary_weighting']}"]["_consensus"],
                ),
                6,
            ),
        },
    )

    write_json(
        proofs / "node_stability.json",
        {
            "resolution": CONFIG["primary_resolution"],
            "seeds": len(CONFIG["seeds"]),
            "algorithm": CONFIG["primary_algorithm"],
            "weighting": CONFIG["primary_weighting"],
            "per_node": [
                {
                    "devata_key": k,
                    "label_en": population[k]["label_en"],
                    "consensus_community": published[k],
                    "fraction_of_seeds_in_consensus_community": round(v, 4),
                    "dedications": population[k]["dedications"],
                    "hymns": population[k]["hymns"],
                }
                for k, v in sorted(published_stability.items(), key=lambda kv: (kv[1], kv[0]))
            ],
        },
    )

    write_json(
        proofs / "existing_co_occurs_with_reproduction.json",
        {
            "claim_being_checked": (
                "a committed scorecard says CO_OCCURS_WITH is 0 edges; agent 1 says 306"
            ),
            "measured_edges": len(existing),
            "unordered_pairs": len(existing_pairs),
            "distinct_devata_endpoints": len({x for p in existing_pairs for x in p}),
            "reciprocated_edges": 0,
            "method_property": sorted({r["method"] for r in existing}),
            "independent_recomputation": {
                "from": "MENTIONS_DEVATA co-occurrence within a mantra, all four Vedas",
                "pairs_i_find_at_support_ge_1": len(mine_pairs),
                "existing_pairs_i_reproduce_exactly": reproduced,
                "passage_count_agrees_on": reproduced,
                "support_threshold_that_reproduces_the_edge_set_exactly": [
                    t for t, ok in threshold_match.items() if ok
                ],
            },
            "verdict": (
                "306 confirmed. The layer is the four-Veda theonym co-MENTION graph "
                "thresholded at 5 shared mantras, and every one of its 306 passage_count "
                "values is reproduced from the mention edges. It is not a partition and it "
                "is not dedication."
            ),
        },
    )

    write_jsonl(
        proofs / "av_ascription_unresolved.jsonl",
        [
            {
                **record,
                "unresolved_reason": (
                    "GAP-ATTRIBUTION-002: this Atharvavedic ascription descriptor does not "
                    "resolve to any :Devata node, so it cannot enter a :Devata partition. "
                    "Resolving the 324 descriptors to deities is agent 8's gap, not a "
                    "judgement this agent may make -- an ascription descriptor such as "
                    "`abdevatyam` is a statement about a verse, not a deity name."
                ),
                "candidate_unit": "DEVATA_ASCRIPTION_NODE",
            }
            for record in av_ascriptions
        ],
    )

    write_json(
        proofs / "av_partition_would_be_a_different_object.json",
        {
            "av_mantras_with_a_dedication": av_dedicated_mantras,
            "av_mantras_with_2_or_more_ascriptions": av_pair_count,
            "av_ascription_descriptors": len(av_ascriptions),
            "descriptors_that_resolve_to_a_devata_node": sum(
                r["devata_links"] for r in av_ascriptions
            ),
            "so_an_av_partition_would_be": (
                "a partition over 324 Anukramani ascription DESCRIPTORS, not over deities. "
                f"{av_pair_count} Atharvavedic mantras carry two or more descriptors, so such "
                "a graph is computable -- and it would answer a different question. Merging it "
                "with the Rigvedic deity partition would assert an identity between a "
                "descriptor and a deity that nothing in the graph supports."
            ),
            "decision": (
                "NOT COMPUTED AS A PUBLISHED PARTITION. The 324 descriptors are carried as "
                "`unresolved` candidates in the manifest and enumerated in "
                "av_ascription_unresolved.jsonl."
            ),
        },
    )

    write_json(
        proofs / "gds_cross_check.json",
        {
            "why_this_is_a_cross_check_and_not_the_source": (
                "nothing in this artifact may depend on GDS. Every published number comes "
                "from community_algorithms.py, which is stdlib-only and re-runnable by a "
                "reader who has the staged files and no database."
            ),
            "what_is_compared": (
                "GDS runs over a Cypher projection of the same co-dedication pattern with "
                "the raw shared-hymn count as the relationship weight, so it is compared "
                "against the RAW-weighted partitions from this module, not against the "
                "cosine-weighted reference partition. Comparing it against COSINE would "
                "report a weighting difference as an implementation disagreement."
            ),
            "read_only_accounting": {
                "graph_counts_before": counts_before,
                "graph_counts_after": counts_after,
                "unchanged": counts_before == counts_after,
                "note": (
                    "gds.graph.project writes to the in-memory catalog only and the entry is "
                    "dropped in the same function. No CREATE, MERGE, SET or DELETE was issued "
                    "against the store at any point in this run."
                ),
            },
            "result": gds,
        },
    )

    # ---------------- diagnostic pairs ------------------------------------------------
    # Pairs whose co-assignment a reader can judge without knowing anything about
    # modularity. Computed rather than asserted in prose, so the claim in the report cannot
    # go stale against a rebuilt partition.
    diagnostic_pairs = [
        {
            "a": "VG:DEVATA:BRHASPATIH",
            "b": "VG:DEVATA:BRAHMANASPATIH",
            "relation": (
                "two names the Rigveda uses for the same deity, the Lord of the Formulation"
            ),
            "separation_would_be": "A DEFECT IN THE PARTITION AS A THEOLOGICAL STATEMENT",
        },
        {
            "a": "VG:DEVATA:BRAHMANASPATIH",
            "b": "VG:DEVATA:INDRABRAHMANASPATI",
            "relation": "a deity and the dual compound that names him with Indra",
            "separation_would_be": "A DEFECT: a deity separated from his own dual",
        },
        {
            "a": "VG:DEVATA:MITRAVARUNAU",
            "b": "VG:DEVATA:MITRAH",
            "relation": "the dual Mitra-Varuna and its own member Mitra",
            "separation_would_be": (
                "not a defect either way; CO-assignment is the thing to watch, because a "
                "community holding both double-counts one deity (GAP-COMMUNITIES-002)"
            ),
        },
        {
            "a": "VG:DEVATA:SOMAH",
            "b": "VG:DEVATA:PAVAMANAH-SOMAH",
            "relation": "Soma and Soma Pavamana, which DEVATA_TAXONOMY_V1 holds apart deliberately",
            "separation_would_be": "EXPECTED; the taxonomy partitions their aliases on purpose",
        },
        {
            "a": "VG:DEVATA:SURYAH",
            "b": "VG:DEVATA:SAVITA",
            "relation": "Surya and Savitr, which DEVATA_TAXONOMY_V1 refuses to merge",
            "separation_would_be": "EXPECTED",
        },
    ]
    for pair in diagnostic_pairs:
        pair["per_method"] = {
            key: (
                "SAME"
                if table["_consensus"].get(pair["a"]) is not None
                and table["_consensus"].get(pair["a"]) == table["_consensus"].get(pair["b"])
                else (
                    "SEPARATED"
                    if pair["a"] in table["_consensus"] and pair["b"] in table["_consensus"]
                    else "ONE_OR_BOTH_UNPLACEABLE"
                )
            )
            for key, table in method_table.items()
        }
    write_json(
        proofs / "diagnostic_pairs.json",
        {
            "what_this_is": (
                "Five deity pairs whose grouping a reader can judge without knowing anything "
                "about modularity, checked against all six algorithm x weighting consensuses. "
                "This is the cheapest available sanity test of whether the partition can be "
                "read as a statement about Vedic religion."
            ),
            "headline": (
                "Brhaspati and Brahmanaspati -- two names for the same deity -- are separated "
                "by every one of the six methods, and Brahmanaspati is also separated from "
                "his own dual Indra-and-Brahmanaspati. The cause is mechanical: his "
                "co-dedicatees in RV 6.75 each appear in exactly one hymn, so cosine gives "
                "those edges about 0.354 while his edges to the great deities score an order "
                "of magnitude lower, and the weighting drags him into a one-hymn inventory. "
                "No deity page should be shown saying Brahmanaspati belongs with the quiver."
            ),
            "pairs": diagnostic_pairs,
        },
    )

    # ---------------- network analytics over the same declared projection -------------
    between = betweenness_centrality(primary_graph)
    participation = participation_coefficient(primary_graph, published)
    zscore = within_module_degree_z(primary_graph, published)
    components = connected_components(primary_graph)
    write_json(
        proofs / "network_analytics.json",
        {
            "computed_over": (
                f"{CONFIG['primary_projection']}, population variant {primary_variant}, "
                f"weighting {CONFIG['primary_weighting']} -- the same declared projection as "
                "the partition, so no figure here belongs to a graph the partition does not"
                " also describe"
            ),
            "graph": {
                "nodes": len(primary_graph.nodes),
                "edges": len(primary["edge_records"]),
                "total_weight": round(primary_graph.total_weight, 6),
                "connected_components": len(components),
                "component_sizes": [len(c) for c in components],
            },
            "betweenness_is_unweighted": (
                "Shortest paths are counted on the unweighted graph. On a co-occurrence "
                "graph a weighted shortest path is the path of LEAST association, which is "
                "the opposite of what a reader assumes."
            ),
            "the_degenerate_projection_this_avoids": (
                "GAP-COMMUNITIES-001's own registry note warns that the natural projection "
                "over passages and entities is directed and bipartite, on which betweenness "
                "is 0.0 for every node, so 'the obvious analysis returns a full sortable "
                "ranking of zeros'. This projection is deity-to-deity and undirected, so the "
                "measure is non-degenerate -- and that is a consequence of declaring a "
                "projection rather than choosing one at query time."
            ),
            "what_this_does_NOT_unblock": (
                "227 :Concept nodes carry centrality_bridging = 'NOT_BUILT: no community "
                "structure exists in this graph, so bridge centrality is not computable and "
                "is not reported as a zero'. That refusal is about CONCEPT nodes. A deity "
                "partition does not license removing it, and nothing here should be read as "
                "doing so."
            ),
            "per_deity": [
                {
                    "devata_key": k,
                    "label_en": population[k]["label_en"],
                    "community_id": published[k],
                    "partners": len(primary_graph.adjacency[k]),
                    "weighted_degree": round(primary_graph.degree(k), 6),
                    "betweenness": round(between[k], 6),
                    "participation_coefficient": round(participation[k], 4),
                    "within_module_degree_z": round(zscore[k], 4),
                    "dedications": population[k]["dedications"],
                    "hymns": population[k]["hymns"],
                }
                for k in sorted(primary_graph.nodes, key=lambda n: -between[n])
            ],
        },
    )

    write_json(
        proofs / "communities_that_are_one_hymn.json",
        {
            "what_this_measures": (
                "For each community, how many DISTINCT Rigvedic suktas supply its internal "
                "edges. A community whose internal edges all come from one sukta is that "
                "hymn's list of dedicatees wearing a community's name. The reason this "
                "happens is structural and measurable: 875 of the 1,028 suktas that carry "
                "dedication are dedicated to a single deity, so the co-dedication signal "
                "lives almost entirely in a small number of multi-dedicatee hymns, several "
                "of which are one-off liturgical inventories."
            ),
            "communities": len(members),
            "single_hymn_communities": sum(
                1 for v in hymn_profile.values() if v["is_a_single_hymn_cast_list"]
            ),
            "deities_in_single_hymn_communities": sum(
                community_size[c]
                for c, v in hymn_profile.items()
                if v["is_a_single_hymn_cast_list"]
            ),
            "communities_that_are_a_whole_connected_component": sum(
                1 for v in hymn_profile.values() if v["is_a_whole_connected_component"]
            ),
            "why_that_second_number_matters": (
                "A community that is an entire connected component required no community "
                "detection to find: nothing joins it to the rest of the graph, so any method "
                "at any resolution with any seed returns it. Counting those among 'the "
                "communities the algorithm found' overstates what the algorithm did, and the "
                "count of genuinely detected structure inside the main component is the "
                "figure worth quoting."
            ),
            "communities_inside_the_main_component": len(members)
            - sum(1 for v in hymn_profile.values() if v["is_a_whole_connected_component"]),
            "deities_placed": len(published),
            "per_community": {
                str(c): {
                    "size": community_size[c],
                    **hymn_profile[c],
                    "largest_members": [
                        population[k]["label_en"]
                        for k in sorted(members[c], key=lambda k: -population[k]["dedications"])
                    ][:6],
                }
                for c in sorted(members)
            },
            "worked_examples": {
                "the_apri_sequence": (
                    "The community holding Agni, Tvastr, the divine doors, Dawn-and-Night, "
                    "Vanaspati, the sacred grass, the two divine Hotrs and the goddess triad "
                    "is the apri sequence of the animal offering -- the same nine entities "
                    "DEVATA_TAXONOMY_V1 minted VG:DEITYGROUP:APRIDEVATAH for. It is a fixed "
                    "liturgical RUNNING ORDER, and the algorithm recovers it because the ten "
                    "apri hymns recite it in order. That is a real and checkable result, and "
                    "it is not a theology."
                ),
                "the_weapons_hymn": (
                    "The 16-member community around Brahmanaspati, the bow, the bowstring, "
                    "the arrows, the quiver, the hand-guard, the bow-tips, the chariot, the "
                    "goad, the charioteer and the reins and the war drum is RV 6.75, one "
                    "hymn. Its internal support is 120 against 7 external, which makes it "
                    "the most modular community in the graph and also the least meaningful "
                    "as a grouping of deities."
                ),
                "the_field_hymn": (
                    "Ksetrapati, Sita the Furrow, Suna-and-Sira and the dog is RV 4.57."
                ),
                "the_funeral_hymns": (
                    "Yama, the Fathers, Yami and Sarama's two dogs is RV 10.10 and 10.14 -- "
                    "two hymns, and the one small community that is arguably thematic as well "
                    "as liturgical."
                ),
            },
        },
    )

    write_json(
        proofs / "membership_under_every_method.json",
        {
            "why_this_file_exists": (
                "The reference partition is one of six that were computed, and the weighting "
                "that produced it was chosen partly because it was the most stable -- which "
                "is a posterior choice and therefore suspect. Every node's community under "
                "every algorithm x weighting consensus is written out here so that the "
                "choice hides nothing and a reader can adopt a different one."
            ),
            "population_variant": primary_variant,
            "resolution": CONFIG["primary_resolution"],
            "seeds": len(CONFIG["seeds"]),
            "methods": {
                key: {
                    "communities": len(set(table["_consensus"].values())),
                    "modularity_mean": table["modularity_mean"],
                    "pairwise_ari_mean": table["pairwise_ari_mean"],
                    "membership": dict(sorted(table["_consensus"].items())),
                }
                for key, table in method_table.items()
            },
            "comention_consensus": {
                "communities": len(set(comention_consensus.values())),
                "membership": dict(sorted(comention_consensus.items())),
            },
        },
    )

    write_json(
        proofs / "unplaceable_deities.json",
        {
            "what_this_is": (
                "Eligible deities that this projection cannot place in any community, because "
                "every hymn dedicated to them is dedicated to them alone. They are NOT given "
                "a singleton community: a singleton would let a reader count them as "
                "communities and would put Indra-sized and one-verse labels on the same "
                "footing. This is a typed absence, not a missing row."
            ),
            "population_variant": primary_variant,
            "eligible_deities": len(projections[primary_variant]["nodes"]),
            "placed": len(projections[primary_variant]["connected_nodes"]),
            "unplaceable": len(projections[primary_variant]["isolates"]),
            "absence_reason_code": "NO_EDGE_IN_PROJECTION_DEGREE_ZERO",
            "deities": [
                {
                    "devata_key": k,
                    "label_en": population[k]["label_en"],
                    "curated_structure": population[k]["structure"],
                    "dedications": population[k]["dedications"],
                    "hymns": population[k]["hymns"],
                    "reason": (
                        "every sukta dedicated to this deity is dedicated to it alone, so it "
                        "has no co-dedication partner anywhere in the Rigveda"
                    ),
                }
                for k in projections[primary_variant]["isolates"]
            ],
        },
    )

    comention_density = (
        len(comention_all["edge_records"])
        / (len(comention_all["connected_nodes"]) * (len(comention_all["connected_nodes"]) - 1) / 2)
        if len(comention_all["connected_nodes"]) > 1
        else None
    )
    codedication_density = (
        len(primary["edge_records"])
        / (len(primary["connected_nodes"]) * (len(primary["connected_nodes"]) - 1) / 2)
        if len(primary["connected_nodes"]) > 1
        else None
    )
    write_json(
        proofs / "projection_density.json",
        {
            "why_density_matters_here": (
                "The co-mention projection partitions into very few communities and it is "
                "important not to read that as 'the deities of the Vedas form three groups'. "
                "The theonym mention layer reaches only 42 of 214 :Devata nodes, and among "
                "those 42 it is extremely dense -- most of them co-occur with most of the "
                "others. A near-complete graph has almost no modular structure to find, so "
                "the small community count is a property of the layer's reach, not of the "
                "corpus."
            ),
            "codedication": {
                "nodes_placed": len(primary["connected_nodes"]),
                "edges": len(primary["edge_records"]),
                "density": round(codedication_density, 6) if codedication_density else None,
            },
            "comention": {
                "devata_nodes_the_mention_layer_reaches": len(comention_all["nodes"]),
                "of_a_devata_population_of": len(deities),
                "nodes_placed": len(comention_all["connected_nodes"]),
                "edges": len(comention_all["edge_records"]),
                "density": round(comention_density, 6) if comention_density else None,
            },
        },
    )

    write_json(
        proofs / "edge_list.json",
        {
            "projection": CONFIG["primary_projection"],
            "population_variant": primary_variant,
            "nodes": len(primary["nodes"]),
            "edges": len(primary["edge_records"]),
            "edge_records": primary["edge_records"],
        },
    )

    if not (proofs / "self_test.json").exists():
        raise SystemExit(
            "proofs/self_test.json is absent. Run self_test.py before this script: a "
            "partition produced by unvalidated machinery is not evidence of anything."
        )

    # ---------------- manifest --------------------------------------------------------
    candidates = len(rows) + len(rejected) + len(av_ascriptions)
    files = []
    for name in (
        "rows.jsonl",
        "rejected.jsonl",
        "sources.jsonl",
        "communities.jsonl",
        "abstract_label_rulings.json",
        "community_algorithms.py",
        "build_communities_staging.py",
    ):
        path = HERE / name
        files.append(
            {
                "path": name,
                "sha256": sha256_of(path),
                "rows": (
                    sum(1 for _ in path.open(encoding="utf-8"))
                    if name.endswith(".jsonl")
                    else 0
                ),
                "bytes": path.stat().st_size,
            }
        )

    manifest = {
        "domain": "communities",
        "agent": 15,
        "schema_version": "1.0",
        "algorithm_version": CONFIG["algorithm_version"],
        "created_at": created_at,
        "code_commit": commit,
        "config_hash": cfg_hash,
        "config": CONFIG,
        "source_snapshot_ids": [SOURCE_CODED, SOURCE_COMENTION, SOURCE_TAXONOMY],
        "graph_snapshot": {"before": counts_before, "after": counts_after},
        "files": files,
        "counts": {
            "candidates_considered": candidates,
            "accepted": len(rows),
            "rejected": len(rejected),
            "verified_zero": sum(
                1
                for r in rows
                if r["payload"]["projection_role"]
                == "SINGLE_ELIGIBLE_DEITY_CONTRIBUTES_NO_EDGE"
            ),
            "not_applicable": sum(
                1
                for r in rows
                if r["payload"]["projection_role"] == "NO_ELIGIBLE_DEITY_AFTER_CLEANING"
            ),
            "unresolved": len(av_ascriptions),
        },
        "candidate_ledger_is_mixed_grain": (
            "Stated rather than hidden, because the arithmetic would otherwise be comparing "
            "unlike things. `accepted` counts RV sukta assessments (the grain at which a "
            "canonical_key resolves to a :Passage, which the validator requires). `rejected` "
            "counts :Devata nodes removed from the eligible population. `unresolved` counts "
            "the 324 :DevataAscription descriptors that cannot enter a :Devata partition at "
            "all. Each rejected and unresolved row carries a `candidate_unit` field naming "
            "its grain."
        ),
        "primary_deliverable_is_not_rows_jsonl": (
            "The deity-grained community membership is communities.jsonl. It is checksummed "
            "in `files` but cannot live in rows.jsonl, because the validator's "
            "graph.canonical_key_resolves check requires every canonical_key to resolve to a "
            ":Passage and a :Devata node carries entity_key, not canonical_key, and no "
            ":Passage label. Agent 8 hit the same wall and put entity-grained material in "
            "proofs/. Flagged to the lead as a contract limit, not worked around silently."
        ),
        "partition_summary": {
            "reference_partition": (
                f"{CONFIG['primary_algorithm']} | {CONFIG['primary_weighting']} | "
                f"gamma={CONFIG['primary_resolution']} | {primary_variant} | consensus over "
                f"{len(CONFIG['seeds'])} seeds"
            ),
            "communities": len(members),
            "deities_placed": len(published),
            "deities_eligible": len(projections[primary_variant]["nodes"]),
            "deities_unplaceable_degree_zero": len(projections[primary_variant]["isolates"]),
            "community_sizes": sorted(community_size.values(), reverse=True),
            "single_hymn_cast_list_communities": sum(
                1 for v in hymn_profile.values() if v["is_a_single_hymn_cast_list"]
            ),
            "communities_that_are_a_whole_connected_component": sum(
                1 for v in hymn_profile.values() if v["is_a_whole_connected_component"]
            ),
            "connected_components_of_the_projection": len(component_sizes),
            "publication_verdict": "NOT_STABLE_ENOUGH_TO_PUBLISH_AS_A_PRODUCT_SURFACE",
            "publication_verdict_reason": (
                "Seed stability is not the problem -- the reference partition is identical "
                "on all 200 seeds (pairwise ARI 1.0000). The specification is. Changing the "
                "weighting moves the partition (pairwise ARI 0.584, 0.659 and 0.879 between "
                "the three), and "
                "changing the co-occurrence relation from dedication to mention destroys the "
                "correspondence entirely (ARI 0.013 on the 35 shared deities). Half the "
                "communities are one hymn's list of dedicatees and five of the twelve are "
                "whole connected components. And the decisive check needs no statistics at "
                "all: all six methods separate Brhaspati from Brahmanaspati, two names for "
                "the same deity, and separate Brahmanaspati from his own dual "
                "Indra-and-Brahmanaspati -- see proofs/diagnostic_pairs.json. A published "
                "deity-community surface would be presenting an artefact of four "
                "discretionary choices as a property of the corpus."
            ),
        },
        "closes_gaps": [],
        "advances_gaps": {
            "GAP-COMMUNITIES-001": (
                "A partition now exists where none did, over 0 of a stated population of "
                "192. It is NOT proposed for import as a published product surface: see the "
                "stability verdict in docs/reports/data-completeness/communities.md. The "
                "registry's population of 192 also needs correcting -- it counts 214 minus "
                "the 22 HUMAN and misses the 7 PATRON_PRAISE."
            ),
            "GAP-COMMUNITIES-003": (
                "CO_OCCURS_WITH re-measured independently at 306 edges over 306 unordered "
                "pairs and 36 deity endpoints, and every one of its passage_count values "
                "reproduced from MENTIONS_DEVATA. Agent 1's figure confirmed; the "
                "scorecard's 0 is wrong. See proofs/existing_co_occurs_with_reproduction.json."
            ),
            "GAP-COMMUNITIES-002": (
                "not worked. The gap census records GAP-COMMUNITIES-001 as blocked on it, on "
                "the ground that an undecomposed dual or group cannot be placed in a "
                "community. This run shows that blocker is not binding for the projection "
                "actually available: a dual is placed by its own co-dedication footprint "
                "without being decomposed. The blocker matters for INTERPRETING a community, "
                "not for computing one."
            ),
            "GAP-ATTRIBUTION-002": (
                "supplies an enumerated, reasoned list of all 324 unresolvable Atharvavedic "
                "ascription descriptors in proofs/av_ascription_unresolved.jsonl, with the "
                "measured consequence: it is what makes a co-dedication partition Rigveda-"
                "only rather than RV+AV."
            ),
        },
        "qa": {
            "sampled": 0,
            "sample_method": "both",
            "sample_note": (
                "No sampling of accepted rows: every row is a deterministic restatement of "
                "HAS_DEVATA edges that already exist, so a sample would only re-measure the "
                "graph. What was validated instead is the MACHINERY, which is where a defect "
                "in this domain would live. community_algorithms.py is checked against "
                "Zachary's karate club, whose modularity optimum is a published number, and "
                "the 42 ABSTRACT rulings and 29 exclusions were each read individually."
            ),
            "defects_found": 1,
            "defects": [
                "The graph aggregation step in community_algorithms.py double-counted "
                "between-community edge weight, because each edge is walked from both "
                "endpoints and only the internal half was being halved. The karate-club "
                "self-test caught it: the level-2 aggregate reported total weight m = 111.0 "
                "against the graph's 78.0, and every modularity above the first level was "
                "wrong. Before the fix the best partition found on karate was Q = 0.3718 at "
                "k = 2; after it, Q = 0.4198 at k = 4, which is the published optimum for "
                "that graph. Had this shipped, the Vedic numbers would have looked entirely "
                "plausible and been wrong."
            ],
            "human_reviewed": 0,
            "reviewed_by": (
                "claude-opus-5 acting as Agent 15. Model adjudication, not gold; campaign "
                "section 26 forbids calling it gold. The 42 ABSTRACT rulings are the part "
                "most in need of a human and are written one per line with a reason so they "
                "can be re-read in an hour."
            ),
        },
    }
    write_json(HERE / "manifest.json", manifest)

    # ---------------- console summary -------------------------------------------------
    print(f"\ngraph snapshot: {counts_before} -> {counts_after} "
          f"({'unchanged' if counts_before == counts_after else 'CHANGED -- INVESTIGATE'})")
    print(f"population: {len(deities)} :Devata; eligible by variant "
          f"{{'V-ALL': {len(variants['V-ALL'])}, 'V-RULED': {len(variants['V-RULED'])}, "
          f"'V-NONE': {len(variants['V-NONE'])}}}")
    for variant in CONFIG["population_variants"]:
        p = projections[variant]
        print(f"  {variant}: projection nodes {len(p['nodes'])}, edges {len(p['edge_records'])}")
    print(f"co-mention (comparison): nodes {len(comention_all['nodes'])}, "
          f"edges {len(comention_all['edge_records'])}")
    print("\nmethod comparison at gamma=1.0 over 200 seeds:")
    print(f"  {'method':22s} {'k(cons)':>8s} {'Qmean':>8s} {'Qmax':>8s} {'ARImean':>8s} "
          f"{'ARImin':>8s} {'nodes<0.9':>10s} {'disc':>5s}")
    for key, table in method_table.items():
        print(f"  {key:22s} {table['consensus_communities']:8d} "
              f"{table['modularity_mean']:8.4f} {table['modularity_max']:8.4f} "
              f"{table['pairwise_ari_mean']:8.4f} {table['pairwise_ari_min']:8.4f} "
              f"{table['nodes_below_0_9_stability']:10d} "
              f"{table['runs_with_a_disconnected_community']:5d}")
    print("\nresolution sensitivity (leiden|JACCARD, seed 0):")
    for row in resolution_table[f"leiden|{CONFIG['primary_weighting']}"]:
        print(f"  gamma={row['resolution']:>5}: k={row['communities']:3d} "
              f"largest={row['largest_community']:3d} singletons={row['singletons']:3d} "
              f"Q(g)={row['modularity_at_this_gamma']:+.4f} ARI vs g=1 {row['ari_vs_gamma_1']:.4f}")
    print("\npopulation-variant sensitivity:")
    for row in variant_sensitivity:
        print(f"  {row['pair']:20s} shared={row['nodes_shared']:3d} "
              f"k {row['communities_a']}->{row['communities_b']} "
              f"ARI={row['ari_on_shared_nodes']:.4f}")
    print(f"\nco-dedication vs co-mention: {projection_sensitivity}")
    print(f"\nreference partition: {len(set(published.values()))} communities over "
          f"{len(published)} deities; sizes "
          f"{sorted(community_size.values(), reverse=True)}")
    single = [c for c, v in hymn_profile.items() if v["is_a_single_hymn_cast_list"]]
    print(f"  of which {len(single)} are a single hymn's cast list, covering "
          f"{sum(community_size[c] for c in single)} deities")
    print(f"  unplaceable (degree zero in the projection): "
          f"{len(projections[primary_variant]['isolates'])} of "
          f"{len(projections[primary_variant]['nodes'])} eligible")
    print(f"GDS cross-check: {json.dumps(gds.get('louvain', gds.get('error')))} | "
          f"{json.dumps(gds.get('leiden', ''))}")
    print(f"\nmanifest counts: {manifest['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
