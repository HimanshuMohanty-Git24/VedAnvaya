"""Project every Knowledge Model V3 layer into Neo4j, and report what landed.

**This script exists because it did not.** The V3 layers -- the four-Veda theonym mention
layer, the agentive assertion layer, the sealed Rigvedic artifact, the Atharvavedic
ascription nodes and the formula families -- were first landed in the live database by an
ad-hoc session script that was not committed. The result was a graph carrying 107,935
nodes that **no artifact in the repository could reproduce**, which fails the two things
V3 is required to be: idempotent on rebuild and deterministic across independent builds.
Every layer below was already implemented and tested in :mod:`vedagraph.domain.v3_loader`;
what was missing was the thing that calls them in order.

Run order matters in exactly three places and nowhere else:

1. ``load_action_predicates`` before ``load_agentive`` -- an assertion links to a predicate
   node, so the vocabulary has to exist or 2,406 ``ASSERTION_PREDICATE`` edges silently
   find no endpoint and are never created. That is the quiet-failure shape this
   repository's loaders report ``sent`` and ``landed`` separately to catch.
2. ``load_theonym_mentions`` before ``retire_superseded_devata_mentions`` -- the retirement
   deletes the 9,000 Rigveda-only ``MENTIONS_ENTITY`` edges onto ``:Devata`` that the new
   four-Veda layer replaces. Retiring first would leave a window with no deity mention
   layer at all, and a crash inside it would leave the graph worse than before.
3. Formula families after the enrichment layer -- ``MEMBER_OF_FAMILY`` matches existing
   ``:Formula`` nodes and creates none, so running it against a graph without them lands
   720 orphan family nodes and no memberships.
4. ``load_formula_family_outward`` after ``load_formula_families`` -- the outward
   ``HAS_FORMULA`` mirror is copied from the membership edges *in the graph*, not
   re-derived from the artifact, so it can only be as complete as the pass before it.
5. ``load_sealed_predicate_edges`` after both ``load_action_predicates`` and ``sealed`` --
   it matches an existing vocabulary node and an existing assertion node and mints
   neither, which is what stops a projection quietly enlarging a closed vocabulary; run
   early, it lands nothing and reports the whole model layer as unmapped.

Everything else is independent and the order among them is alphabetical, not significant.

This script does **not** build artifacts. Each layer's artifact has its own builder
(``build_formula_families.py``, ``build_anukramani_knowledge_layer.py``,
``build_domain_v2.py``) and this one only projects what those wrote, so a projection can
be re-run without re-deriving -- and so a failure here is unambiguously a projection
failure.

Usage::

    python scripts/build_knowledge_model_v3.py
    python scripts/build_knowledge_model_v3.py --check       # measure, write nothing
    python scripts/build_knowledge_model_v3.py --only theonyms,formula_families
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
from typing import Any, Final

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import orjson  # noqa: E402
import yaml  # noqa: E402

from vedagraph.config.registry import load_works  # noqa: E402
from vedagraph.domain import (  # noqa: E402
    candidate_review,
    cooccurrence,
    entity_centrality,
    entity_overlap,
    profiles,
    v3_loader,
    work_scope,
)
from vedagraph.domain import loader as domain_loader  # noqa: E402
from vedagraph.domain.schema import all_domain_schema_cypher  # noqa: E402
from vedagraph.domain.sealed_semantics import prepare as prepare_sealed  # noqa: E402
from vedagraph.domain.theonyms import (  # noqa: E402
    extract_theonym_mentions,
    load_theonyms,
)
from vedagraph.enrich.agentive import extract_agentive, load_vocabulary  # noqa: E402
from vedagraph.enrich.corpus import load_corpus  # noqa: E402
from vedagraph.enrich.morphology import load_annotation  # noqa: E402

BOLT_URI: Final = "bolt://localhost:7687"
BOLT_AUTH: Final = ("neo4j", "vedagraph_dev")

ENRICHMENT_DIR: Final = PROJECT_ROOT / "data" / "enrichment" / "vedagraph_enrichment_v1"
RISHI_FAMILY_ARTIFACT: Final = (
    PROJECT_ROOT / "data" / "domain" / "vedagraph_domain_v2" / "rishi_families_v1.json"
)

#: Every layer this script can project, in dependency order. Named so ``--only`` can
#: select one without the caller having to know the order.
LAYERS: Final[tuple[str, ...]] = (
    # First and order-independent: it writes four Work properties and reads nothing this
    # script derives. Placed at the head so that a projection interrupted after any later
    # step still leaves the corpus scope statements in the graph -- they are the one layer
    # whose absence is actively misleading rather than merely missing.
    "work_scope",
    "action_predicates",
    "agentive",
    "theonyms",
    "retire_devata_mentions",
    # After `theonyms`, because it flags a deity's composition and the mention layer is
    # what a consumer reaches a composite deity through; before `devata_profiles`, which
    # reports the flag.
    # Before `devata_composition`, so that step's counts are taken after the variant edges
    # exist, and before `devata_profiles` for the same reason.
    "devata_variants",
    "devata_composition",
    "orphan_lemmas",
    "sealed",
    "devata_ascriptions",
    "formula_families",
    # Ritual-layer depth. After the domain layer exists (it types nodes the domain builder
    # created) and after formula families only for readability -- it shares no data with
    # them. It MATCHes every node it types and MERGEs none, so run against a graph without
    # the domain layer it lands nothing and reports every declaration as unwitnessed.
    "ritual_depth",
    # Immediately after, and never on its own against a stale membership layer: it copies
    # the MEMBER_OF_FAMILY edges that step landed rather than re-deriving them from the
    # artifact, so it mirrors whatever is there -- including a short load.
    "formula_family_outward",
    # Independent of every other layer: it MATCHes existing :Rishi nodes by pinned
    # entity_key, creates no Rishi and touches no HAS_RISHI edge. Placed after the formula
    # families only to keep the two membership layers adjacent for a reader.
    "rishi_families",
    # Must run after any pass that reloads the enrichment layer, because that layer writes
    # the full 47,976 aboutness edges including the translation-only ones this step
    # retires. Running the enrichment load without following it with this step silently
    # restores 21,539 edges that rest on Griffith's English alone.
    "about_concept",
    # After both assertion-producing layers, because it copies each assertion's grade
    # onto the edge that reaches it and can only be right once both have landed.
    "assertion_edge_grades",
    # Same requirement, one edge type over: it links the sealed layer to the predicate
    # vocabulary and then regrades every ASSERTION_PREDICATE edge from its assertion, so
    # both assertion layers and the vocabulary have to exist first.
    "sealed_predicate_edges",
    # After every layer that creates a passage-to-entity edge, since it measures scope
    # from those edges and would understate any layer landed after it.
    "layer_veda_scope",
    # After `theonyms`: it is counted over the mention layer, so it has to be rebuilt
    # whenever that layer moves or it silently describes the previous one.
    "devata_cooccurrence",
    # Must run after `theonyms` AND after `devata_cooccurrence`: a profile counts mentions
    # per referent-certainty tier and reads co-mention from CO_OCCURS_WITH, so running it
    # first would land a profile describing the previous mention layer while reporting
    # success. It is the last read-only-derived layer for that reason.
    "devata_profiles",
    # Last among the write layers: it deletes the candidate edges an independent reviewer
    # rejected. Running it before a layer that re-MERGEs the candidate set would put the
    # rejected assertions straight back.
    "candidate_review",
    # Strictly after everything that can touch MENTIONS_ENTITY, including the deletions
    # above: it reads that layer whole and recomputes every cross-Veda pair, so running it
    # earlier would materialise its edges against an input that a later step then changed,
    # and report success. It retires its own stale edges by pipeline_version rather than
    # relying on MERGE, because a pair that stops qualifying would otherwise survive every
    # future rebuild -- the shape this repository has been burned by before.
    "entity_overlap",
    # Same requirement as entity_overlap and for the same reason: it reads MENTIONS_ENTITY
    # and ABOUT_CONCEPT whole. It also writes the rank correlation between the two concept
    # layers, which is only meaningful once both have finished moving.
    "entity_centrality",
)


def _read_rishi_families() -> dict[str, list[dict[str, Any]]]:
    """The RishiFamily artifact, reshaped into the three row sets the loader takes.

    unassigned is folded into the decomposition rows rather than passed separately,
    because family_assignment_class belongs on the Rishi node: 426 of the 729 ṛṣis
    get no family, and a reader who cannot see *why* from the node will read the absence
    as a gap in the loader rather than as this layer's answer.
    """
    if not RISHI_FAMILY_ARTIFACT.exists():
        return {"families": [], "memberships": [], "decompositions": []}
    payload = orjson.loads(RISHI_FAMILY_ARTIFACT.read_bytes())
    classes = {
        str(row["entity_key"]): str(row["unassigned_class"])
        for row in payload.get("unassigned", [])
    }
    decompositions = [
        dict(row, unassigned_class=classes.get(str(row["entity_key"])))
        for row in payload.get("decompositions", [])
    ]
    return {
        "families": list(payload.get("families", [])),
        "memberships": list(payload.get("memberships", [])),
        "decompositions": decompositions,
    }


def _read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [orjson.loads(line) for line in path.read_bytes().split(b"\n") if line.strip()]


#: How many deity profiles the ``devata_profiles`` step completes. Twenty, because the
#: V3 close-out gate is stated over the top twenty and because a profile is only worth
#: landing if its holes have been read one deity at a time -- a run over all 214 would be a
#: number, not a reviewed set.
TOP_DEVATA_PROFILES: Final = 20


def _load_devata_profiles(session: Any) -> Any:
    """Complete the top-N deity profiles, selected by mentions and by attribution.

    **The selection is the union of two rankings, not one.** ``top_devatas`` orders by
    ``HAS_DEVATA`` and that layer is Rigveda-only, so on its own it builds a Rigvedic top
    twenty and calls it a four-Veda one. ``top_devatas_by_mention`` orders by the mention
    layer at the product's default certainty tiers, which spans four Vedas and matches what
    a default deity query returns. The two disagree -- Pṛthivī, Vāc, Mitra and Sarasvatī
    are heavily mentioned and lightly attributed, while Pavamāna-Soma is the reverse -- and
    taking the union rather than picking a side means no deity is excluded from the
    completed set by an artefact of which layer was consulted. The union is reported with
    the run so the disagreement is visible rather than averaged away.
    """
    by_mention = profiles.top_devatas_by_mention(session, limit=TOP_DEVATA_PROFILES)
    by_attribution = profiles.top_devatas(session, limit=TOP_DEVATA_PROFILES)
    selected = list(dict.fromkeys([key for key, _ in by_mention] + by_attribution))
    computed = [profiles.compute_profile(session, key) for key in selected]
    report = domain_loader.load_profiles(session, computed)
    report.detail["selection"] = {
        "by_mention_default_scope": [list(item) for item in by_mention],
        "by_attribution_rv_only": by_attribution,
        "in_mention_top_only": [key for key, _ in by_mention if key not in set(by_attribution)],
        "in_attribution_top_only": [
            key for key in by_attribution if key not in {k for k, _ in by_mention}
        ],
    }
    return report


def _read_yaml(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def _ascription_inputs() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The Atharvavedic ascription descriptors, and the assertions that point at them.

    The descriptors are registry entities and the assertions are in the Atharvavedic
    knowledge artifact, so this reads two files. They are filtered to the one predicate
    rather than passed wholesale: the same artifact carries ``HAS_RISHI`` and
    ``HAS_CHANDAS``, which the V1 projection owns, and handing them to this loader would
    write ascription edges onto rsis.
    """
    entities = list(
        _read_yaml(PROJECT_ROOT / "data" / "registry" / "devata_ascriptions_av.yaml").get(
            "entities"
        )
        or []
    )
    assertions = [
        row
        for row in _read_jsonl(
            PROJECT_ROOT
            / "data"
            / "knowledge"
            / "atharvaveda_deterministic_v1"
            / "knowledge_assertions.jsonl"
        )
        if row.get("predicate") == "HAS_DEVATA_ASCRIPTION"
    ]
    return entities, assertions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="derive every layer and report sizes without touching Neo4j",
    )
    parser.add_argument(
        "--only",
        default="",
        help=f"comma-separated subset of: {','.join(LAYERS)}",
    )
    args = parser.parse_args()

    selected = (
        tuple(name.strip() for name in args.only.split(",") if name.strip())
        if args.only
        else LAYERS
    )
    unknown = sorted(set(selected) - set(LAYERS))
    if unknown:
        print(f"unknown layer(s): {', '.join(unknown)}")
        print(f"known: {', '.join(LAYERS)}")
        return 2

    print("=" * 78)
    print("KNOWLEDGE MODEL V3 -- projection")
    print("=" * 78)

    print("\n[1/3] deriving the layers")
    corpus = load_corpus(PROJECT_ROOT)
    annotation = load_annotation(PROJECT_ROOT)
    index = load_theonyms(PROJECT_ROOT)
    vocabulary = load_vocabulary(PROJECT_ROOT)
    # The work registry, not the canonical works.jsonl: the scope statements live in
    # data/registry/works.yaml precisely because works.jsonl is hashed into its corpus
    # manifest and must not be edited to carry them.
    registry_works = load_works(PROJECT_ROOT / "data" / "registry" / "works.yaml")
    print(
        f"      corpus mantras={sum(len(corpus.of_veda(v)) for v in ('RV', 'SV', 'YV', 'AV'))}"
        f"  annotated tokens={len(annotation.tokens)}"
        f"  theonym deities={len(index.deities)}"
        f"  predicates={len(vocabulary.by_label)}"
    )

    theonym_rows, theonym_report = extract_theonym_mentions(corpus, annotation, index)
    agentive_rows, agentive_report = extract_agentive(annotation, vocabulary, index.rv_lemma)
    sealed = prepare_sealed(PROJECT_ROOT)
    ascription_entities, ascription_assertions = _ascription_inputs()
    families = _read_jsonl(ENRICHMENT_DIR / "formula_families.jsonl")
    members = _read_jsonl(ENRICHMENT_DIR / "formula_family_members.jsonl")
    ritual_depth = _read_yaml(
        PROJECT_ROOT / "data" / "domain" / "vedagraph_domain_v2" / "ritual_depth_v3_1.yaml"
    )
    rishi_families = _read_rishi_families()
    review_rows = candidate_review.load_review(PROJECT_ROOT)

    print(
        f"      rishi families={len(rishi_families['families'])}"
        f"  memberships={len(rishi_families['memberships'])}"
        f"  decompositions={len(rishi_families['decompositions'])}"
    )
    print(f"      theonym mentions={len(theonym_rows)}")
    print(f"      agentive assertions={len(agentive_rows)}")
    print(f"      sealed rows={len(sealed.rows)}")
    print(
        f"      ascription descriptors={len(ascription_entities)}"
        f"  assertions={len(ascription_assertions)}"
    )
    print(f"      formula families={len(families)}  memberships={len(members)}")
    print(
        f"      ritual depth: role retypes={len(ritual_depth.get('ritual_role_typing') or [])}"
        f"  offering types={len(ritual_depth.get('offering_typing') or [])}"
        f"  rite loci={len(ritual_depth.get('rite_loci') or [])}"
    )
    review_verdicts = {
        verdict: sum(1 for row in review_rows if row["verdict"] == verdict)
        for verdict in sorted({row["verdict"] for row in review_rows})
    }
    print(f"      candidate adjudications={len(review_rows)}  {review_verdicts}")

    summary: dict[str, Any] = {
        "derived": {
            "theonym_mentions": len(theonym_rows),
            "agentive_assertions": len(agentive_rows),
            "sealed_rows": len(sealed.rows),
            "ascription_descriptors": len(ascription_entities),
            "ascription_assertions": len(ascription_assertions),
            "formula_families": len(families),
            "formula_family_members": len(members),
            "rishi_families": len(rishi_families["families"]),
            "rishi_family_members": len(rishi_families["memberships"]),
        },
        "theonym_report": theonym_report.as_dict(),
        "agentive_report": agentive_report.as_dict(),
        "layers_selected": list(selected),
    }

    if args.check:
        print("\n[2/3] skipped (--check)")
        print("[3/3] summary")
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    from neo4j import GraphDatabase  # imported late: --check needs no driver

    print("\n[2/3] applying the schema and projecting")
    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    failures: list[str] = []
    try:
        with driver.session() as session:
            before = session.run(
                "MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() RETURN nodes, count(r) AS rels"
            ).single()
            summary["graph_before"] = {
                "nodes": before["nodes"],
                "relationships": before["rels"],
            }
            print(f"      before: {before['nodes']} nodes, {before['rels']} relationships")

            for cypher in all_domain_schema_cypher():
                session.run(cypher)

            steps: dict[str, Any] = {
                "work_scope": lambda: work_scope.load_work_scope(session, registry_works),
                "action_predicates": lambda: v3_loader.load_action_predicates(session, vocabulary),
                "agentive": lambda: v3_loader.load_agentive(session, agentive_rows),
                "theonyms": lambda: v3_loader.load_theonym_mentions(
                    session, [row.as_row() for row in theonym_rows]
                ),
                "retire_devata_mentions": (
                    lambda: v3_loader.retire_superseded_devata_mentions(session)
                ),
                "orphan_lemmas": lambda: v3_loader.mark_orphan_lemmas_internal(session),
                "sealed": lambda: v3_loader.load_sealed(session, sealed),
                "devata_ascriptions": lambda: v3_loader.load_devata_ascriptions(
                    session, ascription_entities, ascription_assertions
                ),
                "formula_families": lambda: v3_loader.load_formula_families(
                    session, families, members
                ),
                "ritual_depth": lambda: v3_loader.load_ritual_depth(session, ritual_depth),
                "formula_family_outward": (lambda: v3_loader.load_formula_family_outward(session)),
                "rishi_families": lambda: v3_loader.load_rishi_families(
                    session,
                    rishi_families["families"],
                    rishi_families["memberships"],
                    rishi_families["decompositions"],
                ),
                "about_concept": lambda: v3_loader.reconcile_about_concept(session),
                "assertion_edge_grades": (
                    lambda: v3_loader.reconcile_assertion_edge_grades(session)
                ),
                "sealed_predicate_edges": (lambda: v3_loader.load_sealed_predicate_edges(session)),
                "layer_veda_scope": lambda: v3_loader.stamp_layer_veda_scope(session),
                "devata_variants": lambda: v3_loader.load_devata_variants(session, PROJECT_ROOT),
                "devata_composition": (
                    lambda: v3_loader.reconcile_devata_composition(session, PROJECT_ROOT)
                ),
                "devata_cooccurrence": lambda: cooccurrence.rebuild(session),
                "devata_profiles": lambda: _load_devata_profiles(session),
                "entity_overlap": lambda: entity_overlap.load(
                    session, entity_overlap.derive(session)
                ),
                "entity_centrality": lambda: entity_centrality.load(
                    session, entity_centrality.derive(session)
                ),
                "candidate_review": lambda: candidate_review.apply_review(
                    session,
                    review_rows,
                    review_run="semantic-candidate-review-v3",
                ),
            }

            reports: list[Any] = []
            for name in LAYERS:
                if name not in selected:
                    continue
                report = steps[name]()
                reports.append(report)
                flag = "ok " if report.complete else "!! "
                if not report.complete:
                    failures.append(f"{report.step}: sent={report.sent} landed={report.landed}")
                print(f"      {flag}{report.step:<26} sent={report.sent:<8} landed={report.landed}")
            summary["load_reports"] = [r.as_dict() for r in reports]

            after = session.run(
                "MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() RETURN nodes, count(r) AS rels"
            ).single()
            summary["graph_after"] = {
                "nodes": after["nodes"],
                "relationships": after["rels"],
            }
            print(f"      after:  {after['nodes']} nodes, {after['rels']} relationships")
    finally:
        driver.close()

    print("\n[3/3] summary")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))

    if failures:
        print("\nINCOMPLETE LAYERS -- rows sent did not all land:")
        for line in failures:
            print(f"  !! {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
