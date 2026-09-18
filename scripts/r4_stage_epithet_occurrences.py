#!/usr/bin/env python3
"""Stage GAP-ENTITY_COVERAGE-001: the epithet occurrence layer, from scholarly annotation.

The epithet layer was 13 ``:Epithet`` nodes, 13 ``HAS_EPITHET`` edges and nothing else --
**0** edges of any type between an ``:Epithet`` and a ``:Passage`` -- so no question about
where an epithet occurs could be answered. The Sanskrit is held for all four corpora and the
projection was simply never run.

Where the evidence comes from
=============================

The Rigvedic morphological annotation (``vedagraph.enrich.morphology``), which is scholarly
and per-token: 164,758 tokens, each carrying the annotator's own ``lemma_label`` and
``normalized_lemma`` beside the inflected ``surface_form``. Two routes are derived from it
and they are **not** the same claim, so each edge records which one produced it:

``STEM_LEMMA``
    The epithet's label folds onto an annotated ``normalized_lemma``. The epithet *is* the
    stem, so its occurrences are every mantra containing any inflection of that stem.

``ATTESTED_SURFACE_FORM``
    The epithet's label folds onto an annotated ``surface_form`` and no lemma. The epithet
    is itself an inflected form -- the three duals ``dasrā``, ``nāsatyā`` and
    ``rudravartanī`` -- and the annotator names its stem explicitly. Occurrences are the
    mantras attesting *that word form*. The stem's wider inflection is deliberately not
    claimed: ``dasrá-`` is an adjective meaning "wondrous" applied to many things, while
    the dual ``dasrā`` is the epithet of the Aśvins, and collapsing the two would inflate
    the epithet by 40 mantras of ordinary adjective.

That third route is what closes the three descriptors R3 left unresolved, and it closes
them on **explicit morphology the repository already holds** rather than by loosening a
fold. R3's instruction was not to force stem equivalence for them, and this does not: it
reads the annotator's stem attribution off the token.

What this does not do
=====================

*   **Normalization does not mint identity.** ``fold_alias``/``fold_annotation`` are used to
    *compare* the registry's IAST against the annotation's, never to create an ``:Epithet``
    or to merge two. The 13 ``:Epithet`` nodes and their ``epithet_key`` values are
    untouched and remain authoritative.
*   **No new epithet curation.** The inventory stays at 13. Expanding it is a curation
    question this pass is barred from answering, and the closure clause that asks for it is
    reported as needing an owner decision rather than quietly satisfied -- see
    ``owner_decision_required`` in the output.
*   **No write.** This stages; the migration applies.

The Rigveda-only bound is typed in every row rather than left to a caveat, because
``MENTIONS_LEMMA`` is 154,261 edges over the Rigveda's 10,552 mantras and **zero** over the
other three corpora. An epithet with no Samavedic occurrence is unannotated there, not
absent.

Usage:
    python scripts/r4_stage_epithet_occurrences.py
"""

from __future__ import annotations

import collections
import datetime
import json
import pathlib
import sys
from typing import Any, Final

from neo4j import GraphDatabase, Query

PROJECT_ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.enrich.concepts import fold_alias  # noqa: E402
from vedagraph.enrich.morphology import fold_annotation, load_annotation  # noqa: E402

OUT: Final = PROJECT_ROOT / "data" / "staging" / "release_blocker_r4" / "entity_001"
URI: Final = "bolt://localhost:7687"
AUTH: Final = ("neo4j", "vedagraph_dev")
DB: Final = "neo4j"
TIMEOUT: Final[float] = 300.0

CONTRACT: Final = "VG:EPITHET_OCCURRENCE:V1"

#: The corpus the annotation covers. Stated per edge; see the module docstring.
ANNOTATED_VEDAS: Final[tuple[str, ...]] = ("RV",)
UNANNOTATED_VEDAS: Final[tuple[str, ...]] = ("SV", "YV", "AV")


def main() -> int:
    annotation = load_annotation(PROJECT_ROOT)
    tokens = list(annotation.tokens)

    by_lemma: dict[str, list[Any]] = collections.defaultdict(list)
    by_surface: dict[str, list[Any]] = collections.defaultdict(list)
    for token in tokens:
        by_lemma[fold_annotation(token.normalized_lemma)].append(token)
        by_surface[fold_annotation(token.surface_form)].append(token)

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            epithets = [
                dict(record)
                for record in session.run(
                    Query(
                        """
                        MATCH (d:Devata)-[:HAS_EPITHET]->(e:Epithet)
                        RETURN e.epithet_key AS epithet_key, e.label_iast AS label_iast,
                               e.label_en AS label_en, d.entity_key AS devata_key
                        ORDER BY e.epithet_key
                        """,
                        timeout=TIMEOUT,
                    )
                )
            ]
            # Which mantra keys actually exist, so a staged edge cannot point at nothing.
            live_mantras = {
                record["k"]
                for record in session.run(
                    Query(
                        "MATCH (m:Mantra {veda:'RV'}) RETURN m.canonical_key AS k",
                        timeout=TIMEOUT,
                    )
                )
            }
            existing = session.run(
                Query(
                    "MATCH (:Epithet)<-[r]-(p) WHERE p:Passage OR p:Mantra RETURN count(r)",
                    timeout=TIMEOUT,
                )
            ).single()[0]
    finally:
        driver.close()

    rows: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    missing_mantras: list[str] = []

    for epithet in epithets:
        folded = fold_alias(epithet["label_iast"] or "")
        lemma_tokens = by_lemma.get(folded, [])
        surface_tokens = by_surface.get(folded, [])

        if lemma_tokens:
            tier = "STEM_LEMMA"
            chosen = lemma_tokens
            basis = (
                "The epithet's label folds onto the annotator's own normalized_lemma, so "
                "the epithet is the stem and every inflection of it counts."
            )
        elif surface_tokens:
            tier = "ATTESTED_SURFACE_FORM"
            chosen = surface_tokens
            basis = (
                "The epithet's label folds onto an attested inflected surface_form and "
                "onto no lemma, so the epithet is itself an inflected form. The "
                "annotator's stem attribution is recorded and the stem's wider inflection "
                "is deliberately NOT claimed."
            )
        else:
            unresolved.append(
                {
                    "epithet_key": epithet["epithet_key"],
                    "label_iast": epithet["label_iast"],
                    "folded": folded,
                    "reason": (
                        "The folded label matches neither an annotated normalized_lemma nor "
                        "an annotated surface_form anywhere in the 164,758-token Rigvedic "
                        "annotation. Not forced onto a near neighbour."
                    ),
                }
            )
            rows.append(
                {
                    "epithet_key": epithet["epithet_key"],
                    "label_iast": epithet["label_iast"],
                    "devata_key": epithet["devata_key"],
                    "match_tier": "UNRESOLVED_NO_ANNOTATION_EVIDENCE",
                    "mantras": 0,
                    "tokens": 0,
                    "lemma_labels": [],
                }
            )
            continue

        lemma_labels = sorted({token.lemma_label for token in chosen})
        mantra_keys = sorted({token.passage_key for token in chosen})
        present = [key for key in mantra_keys if key in live_mantras]
        missing_mantras.extend(key for key in mantra_keys if key not in live_mantras)

        # Per-epithet recall, measured rather than assumed. The alias-recall discipline
        # says a single aggregate over all epithets would hide an epithet at 0.
        rows.append(
            {
                "epithet_key": epithet["epithet_key"],
                "label_iast": epithet["label_iast"],
                "devata_key": epithet["devata_key"],
                "match_tier": tier,
                "mantras": len(present),
                "tokens": len(chosen),
                "lemma_labels": lemma_labels,
                "stem_lemma_mantras": len({t.passage_key for t in lemma_tokens}),
                "surface_form_mantras": len({t.passage_key for t in surface_tokens}),
                "basis": basis,
            }
        )
        for key in present:
            tokens_here = [token for token in chosen if token.passage_key == key]
            edges.append(
                {
                    "mantra_key": key,
                    "epithet_key": epithet["epithet_key"],
                    "properties": {
                        "epithet_occurrence_contract": CONTRACT,
                        "epithet_match_tier": tier,
                        "knowledge_layer": "L2_DETERMINISTIC_DERIVED",
                        # evidence_basis is the evidence SURFACE and its vocabulary is
                        # closed. The surface here is the Sanskrit text. The derivation --
                        # that this layer infers an epithet occurrence from a per-token
                        # lemma -- is a DIFFERENT axis and travels on knowledge_layer and
                        # provenance_layer. A first version put
                        # "DERIVED_FROM_SCHOLARLY_ANNOTATION" here and invented a value
                        # outside the vocabulary, which is the recorded two-axes defect.
                        "evidence_basis": "SANSKRIT",
                        "quality_tier": "TIER_B",
                        "provenance_layer": "vedaweb-zurich-rigveda-morphological-annotation",
                        "annotator_lemma": lemma_labels[0] if lemma_labels else None,
                        "token_count": len(tokens_here),
                        "surface_forms": sorted({t.surface_form for t in tokens_here})[:8],
                        # The bound, in the row.
                        "annotated_vedas": list(ANNOTATED_VEDAS),
                        "unannotated_vedas": list(UNANNOTATED_VEDAS),
                        "absence_outside_annotated_vedas": "UNANNOTATED_NOT_ABSENT",
                    },
                }
            )

    resolved_rows = [row for row in rows if row["match_tier"] != "UNRESOLVED_NO_ANNOTATION_EVIDENCE"]
    deities = sorted({row["devata_key"] for row in resolved_rows})

    report = {
        "artifact": "R4_ENTITY_001_EPITHET_OCCURRENCE_STAGING",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gap_id": "GAP-ENTITY_COVERAGE-001",
        "contract": CONTRACT,
        "annotation_tokens_read": len(tokens),
        "epithets": len(epithets),
        "epithets_with_occurrence_evidence": len(resolved_rows),
        "epithets_unresolved": len(unresolved),
        "edges_staged": len(edges),
        "existing_epithet_passage_edges_before": existing,
        "staged_edges_point_at_a_missing_mantra": sorted(set(missing_mantras)),
        "match_tier_distribution": dict(
            collections.Counter(row["match_tier"] for row in rows)
        ),
        "deities_reached_by_the_occurrence_layer": deities,
        "per_epithet_recall": rows,
        "unresolved_detail": unresolved,
        "clause_status": {
            "epithets_carry_passage_edges": (
                f"MET once applied: {len(edges)} edges over "
                f"{len(resolved_rows)} of {len(epithets)} epithets."
            ),
            "per_epithet_recall_is_measured": (
                "MET. per_epithet_recall carries a mantra count and a token count per "
                "epithet, not one aggregate, and an epithet with no evidence is a typed "
                "row rather than a silent absence."
            ),
            "the_inventory_reaches_well_beyond_4_deities": (
                "NOT MET, AND NOT IMPLEMENTATION-FIXABLE. See owner_decision_required."
            ),
        },
        "owner_decision_required": {
            "decision_id": "OWNER_DECISION_ENTITY_001_EPITHET_INVENTORY_DENOMINATOR",
            "clause": "the inventory reaches well beyond 4 deities",
            "why_it_is_not_implementation_fixable": (
                "The clause asks the epithet INVENTORY to grow, and the inventory is "
                "curation, not projection. All 13 curated epithets belong to 4 deities; "
                "the occurrence layer can only reach the deities the inventory already "
                "names, so no amount of projection moves this number. Reaching more "
                "deities requires curating new :Epithet nodes, which means choosing which "
                "Sanskrit words are epithets of which gods -- an interpretive editorial "
                "act with no source in this repository that states it. R4's instruction is "
                "explicit: do not invent new epithet curation."
            ),
            "why_the_denominator_is_unsupported": (
                "'well beyond 4' names no number and no source. 4 is not a shortfall "
                "against a declared expectation; it is simply how many deities the 13 "
                "curated epithets happen to belong to. There is no published epithet index "
                "in this repository against which 4 could be measured as incomplete, so "
                "the clause cannot be passed or failed -- which is the defect, not the "
                "count."
            ),
            "the_choice": (
                "Either (a) name a scholarly epithet index as the declared expectation, "
                "at which point this becomes a real coverage gap with a real denominator "
                "and an external-source dependency; or (b) re-scope the clause to what the "
                "repository can support -- every curated epithet carries measured "
                "occurrence evidence or a typed reason for having none -- and record that "
                "the inventory's size is a curation decision outside this campaign."
            ),
            "consequences": {
                "option_a": (
                    "GAP-ENTITY_COVERAGE-001 becomes partly external-source dependent and "
                    "cannot close in this release. The other two clauses stay closed."
                ),
                "option_b": (
                    "GAP-ENTITY_COVERAGE-001 closes CLOSED_DERIVED on the two clauses the "
                    "repository's own evidence supports, with the inventory question "
                    "recorded as a named scope decision rather than absorbed."
                ),
            },
        },
        "edges": edges,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "staging.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  GAP-ENTITY_COVERAGE-001 -- EPITHET OCCURRENCE LAYER STAGED")
    print()
    print(f"  annotation tokens read      {report['annotation_tokens_read']}")
    print(f"  epithets                    {report['epithets']}")
    print(f"  with occurrence evidence    {report['epithets_with_occurrence_evidence']}")
    print(f"  unresolved                  {report['epithets_unresolved']}")
    print(f"  edges staged                {report['edges_staged']}  "
          f"(existing: {report['existing_epithet_passage_edges_before']})")
    print(f"  tiers                       {report['match_tier_distribution']}")
    print(f"  deities reached             {len(report['deities_reached_by_the_occurrence_layer'])}")
    print(f"  edges at a missing mantra   {len(report['staged_edges_point_at_a_missing_mantra'])}")
    print()
    for row in rows:
        print(f"    {row['label_iast']:<15} {row['match_tier']:<22} mantras={row['mantras']:<5} "
              f"lemma={row['lemma_labels']}")
    print()
    print(f"  staged: {(OUT / 'staging.json').relative_to(PROJECT_ROOT)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
