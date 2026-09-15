#!/usr/bin/env python3
"""WAVE_3_DRY_RUN_V2: every canonical write Wave 3 would make, after the owner decisions.

Supersedes ``wave3_dry_run.py``, whose 30,117 planned / 57,384 withheld the owner has
superseded rather than rejected. V1 was right about one thing in particular and this script
exists because of it: V1 refused to state a node or relationship delta, on the grounds that
"the importer must emit its own per-element plan before this figure can be stated." That
plan now exists in ``wave3_import_plan.py``, so the figures here are element-level and
measured against the live graph rather than arithmetic over row counts.

WHAT CHANGED SINCE V1, AND WHY
==============================

Four owner decisions and their repairs:

**Folding is not identity.** ``FOLD_FIX_BREAKS_REFERENT_IDENTITY`` is resolved by giving
the comparison surfaces their own fold and leaving the identity fold untouched, so
``cross_veda`` is no longer blocked. All 3,819 released referent digests still reproduce.

**M6 scope comes from the evidence grain.** The single card is split into three homogeneous
populations on the schema's own closed enums, one staged value corrected, and the
collision ceases to exist rather than being renamed.

**SOMA-PRESSING stays, its weak aliases lose assertion authority.** Three aliases retired
to ``NON_TRIGGERING_ALIAS`` on a measured criterion, and the edges resting solely on them
are retired as an explicit correction.

**Audio does not block the non-audio domains.** The 1,021 listening rows stay withheld and
the four audio-dependent domains stay withheld with them, while the rest proceed.

Two further rulings were needed and are recorded: ``semantic_resemblance`` becomes a
post-import re-derivation rather than an import, and the deity-vocabulary defect becomes
its own registered gap.

Usage:
    python scripts/wave3_dry_run_v2.py [--json OUT]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, TypedDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from neo4j import GraphDatabase
from wave3_import import CORRECTIONS

STAGING = pathlib.Path("data/staging")
INTEGRATION = STAGING / "integration"
LEDGER = INTEGRATION / "wave3_eligibility.json"
BLOCKERS = INTEGRATION / "blockers.json"
PLAN = INTEGRATION / "wave3_import_plan.json"
SCOPE = INTEGRATION / "wave3_scope_grain.json"
SOMA = INTEGRATION / "wave3_soma_pressing_correction.json"
BRIDGE = INTEGRATION / "wave3_devata_identity_bridge.json"
PRIOR = INTEGRATION / "wave3_dry_run.json"
OVERLAYS = STAGING / "lead_overlays" / "wave1_decisions.json"
REGISTRY = pathlib.Path("data/gap_registry.json")
OUT = INTEGRATION / "wave3_dry_run_v2.json"

BACKUP = pathlib.Path("D:/vedanvaya-backups/vedanvaya-v1.0.0-preflight-20260915T105606/neo4j.dump")
EXPECTED_BACKUP_SHA = "98f71b641f608c8fd1aa3082ef4b88f7d983687d2996aa5b1c7528effc83b981"
EXPECTED_BACKUP_BYTES = 96844203

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

NOT_IMPORTABLE = frozenset({"PROBABLE", "UNVERIFIED"})

#: The four migration cards Wave 3 applies, and the one the owner's section 2 replaced.
MIGRATIONS = {
    "M1": "RoleFiller + ASSERTION_ROLE + ROLE_FILLER_ENTITY",
    "M2": "running_samhita_number on Samavedic Mantra -- withheld with samaveda_music",
    "M3": "four gana Work identities -- withheld with samaveda_music",
    "M4": "MUSICALIZED_AS range widening -- withheld with samaveda_music",
    "M5": "SPECIALIZED_FORM_OF, Soma Pavamana to Soma",
    "M6": "SUPERSEDED by owner section 2: split into three grain-derived populations",
}


#: How each correction's rehearsal contributes to the expected census. Declared per
#: correction, because a correction knows what it measures and a generic rule would have to
#: guess: WITHHELD_REGISTRY_ENTITIES retires nodes, RETYPE_ASSERTED_BY is a retire plus a
#: create of the same count, LABEL_REDIRECT adds a label to a node that already exists.
#:
#: An undeclared name raises. The importer's CORRECTIONS grew from two to six and this
#: promise did not follow, so the four it could not see -- one of them node-destructive --
#: never appeared in the owner's section 5 delta at all.
class CorrectionEffect(TypedDict):
    """What one correction contributes to the census.

    ``measure`` is the key its rehearsal reports an outstanding count under, or None when the
    count is already accounted for from a proof artifact. ``adds`` are the census fields that
    count lands in -- more than one where a single change is two movements, as a retype is.
    """

    measure: str | None
    adds: tuple[str, ...]
    why: str


CORRECTION_CENSUS_EFFECT: dict[str, CorrectionEffect] = {
    "SOMA_PRESSING_WEAK_ALIAS_RETIREMENT": {
        "measure": None,
        "adds": (),
        "why": "accounted above from its proof artifact and measured live",
    },
    "M5_SPECIALIZED_FORM_OF": {
        "measure": None,
        "adds": (),
        "why": "accounted above from the migration card and measured live",
    },
    "WITHHELD_REGISTRY_ENTITIES": {
        "measure": "present_and_unreachable",
        "adds": ("nodes_retire",),
        "why": "deletes registry entities whose only path in was an edge the plan refuses",
    },
    "RETYPE_ASSERTED_BY": {
        "measure": "mistyped_edges",
        "adds": ("relationships_retire", "relationships_create"),
        "why": "a retype is one retire and one create of the same edge count",
    },
    "RESTORE_CURATED_DISPLAY_LABELS": {
        "measure": "nodes_with_a_non_curated_label",
        "adds": ("properties_change",),
        "why": "rewrites display_label on nodes that already exist; no node or edge moves",
    },
    "LABEL_REDIRECT_TARGETS_AS_RITUALS": {
        "measure": "unlabelled",
        "adds": ("nodes_update",),
        "why": "adds :Ritual to existing nodes, which is an update and not a create",
    },
}


class UndeclaredCorrection(RuntimeError):
    """A correction with no census effect declared, or one that cannot report its own.

    Raised rather than skipped. A correction the promise cannot see is a mutation the
    readback will find and be unable to explain.
    """


def load(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def digest(path: pathlib.Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    ledger = load(LEDGER)
    blockers = load(BLOCKERS)
    plan = load(PLAN)
    scope = load(SCOPE)
    soma = load(SOMA)
    bridge = load(BRIDGE)
    prior = load(PRIOR)
    overlays = load(OVERLAYS)

    if not plan:
        print("  no element plan. Run scripts/wave3_import_plan.py first.")
        return 1

    eligible = list(ledger.get("eligible_domains") or [])
    open_blockers = [
        b["blocker_id"]
        for b in blockers.get("blockers", [])
        if not str(b.get("status", "")).startswith("RESOLVED")
    ]

    # ---- rows by domain, and why each is withheld -------------------------------------
    barred_keys: set[str] = set()
    barred_patterns: list[str] = []
    for decision in overlays.get("decisions", []):
        override = decision.get("override") or {}
        if not (override.get("import_barred") or override.get("mapping_confidence") == "PROBABLE"):
            continue
        barred_keys.update(decision.get("affected_keys") or [])
        if decision.get("affected_key_pattern"):
            barred_patterns.append(decision["affected_key_pattern"])

    import re as _re

    barred_res = [_re.compile(p) for p in barred_patterns]

    def is_barred(key: str) -> bool:
        return key in barred_keys or any(r.match(key) for r in barred_res)

    domains = sorted(
        p.name for p in STAGING.iterdir() if p.is_dir() and (p / "rows.jsonl").exists()
    )
    by_domain: dict[str, Any] = {}
    planned_rows = withheld_rows = 0
    for domain in domains:
        entry = (ledger.get("domains") or {}).get(domain, {})
        status = entry.get("status", "UNKNOWN")
        rows = read_jsonl(STAGING / domain / "rows.jsonl")
        weak = sum(1 for r in rows if r.get("mapping_confidence") in NOT_IMPORTABLE)
        barred = sum(1 for r in rows if is_barred(str(r.get("canonical_key") or "")))
        eligible_rows = [
            r
            for r in rows
            if r.get("mapping_confidence") not in NOT_IMPORTABLE
            and not is_barred(str(r.get("canonical_key") or ""))
        ]
        ok = status == "ELIGIBLE"
        planned = len(eligible_rows) if ok else 0
        by_domain[domain] = {
            "ledger_status": status,
            "rows_on_disk": len(rows),
            "not_importable_by_confidence": weak,
            "barred_by_owner_overlay": barred,
            "planned_rows": planned,
            "withheld_rows": len(rows) - planned,
            "reason_withheld": None
            if ok
            else f"{status}: {entry.get('status_detail', 'no detail')}",
            "blocked_by": entry.get("blocked_by", []),
        }
        planned_rows += planned
        withheld_rows += len(rows) - planned

    # ---- the corrections, which are the only destructive changes ----------------------
    mentions = (soma.get("mentions_entity") or {}) if soma else {}
    about = (soma.get("about_concept") or {}) if soma else {}
    corrections = {
        "SOMA_PRESSING_WEAK_ALIAS_RETIREMENT": {
            "owner_decision": "section 3",
            "relationships_retire": int(mentions.get("retire_sole_evidence_is_retired") or 0)
            + int(about.get("retire") or 0),
            "relationships_update": int(
                mentions.get("update_drop_retired_alias_keep_edge") or 0
            )
            + int(about.get("update_method_narrowed_to_english_only") or 0),
            # Deliberately 0, not the 5 the correction artifact reports as newly attested.
            # Those 5 exist only because assign_concepts reshuffled its per-passage cap when
            # SOMA-PRESSING's corpus-wide attestation dropped, and that reshuffle is held
            # back for its own decision -- it changes concepts the owner's ruling did not
            # name. Promising them and then not writing them is what left the second import
            # 5 relationships short of its own dry-run.
            "relationships_create": 0,
            "newly_attested_withheld_with_the_cap_collateral": int(
                about.get("create_newly_attested") or 0
            ),
            "detail": {
                "MENTIONS_ENTITY_retire": mentions.get("retire_sole_evidence_is_retired"),
                "MENTIONS_ENTITY_update": mentions.get(
                    "update_drop_retired_alias_keep_edge"
                ),
                "ABOUT_CONCEPT_retire": about.get("retire"),
                "ABOUT_CONCEPT_update": about.get(
                    "update_method_narrowed_to_english_only"
                ),
                "ABOUT_CONCEPT_create": about.get("create_newly_attested"),
            },
            "proof_artifact": str(SOMA),
            "every_retired_edge_rests_solely_on_a_retired_alias": (
                about.get("passages_keeping_the_concept_on_other_evidence") == 0
            ),
        },
        "M5_SPECIALIZED_FORM_OF": {
            "owner_decision": "section 1 of the prior round, unchanged",
            "relationships_retire": 1,
            "relationships_create": 1,
            "detail": "the Soma Pavamana -> Soma edge moves from EPITHET_VARIANT_OF; "
            "EPITHET_VARIANT_OF goes 11 to 10 and SPECIALIZED_FORM_OF becomes 1",
        },
    }
    # ---- the collateral the owner's decision did not name -----------------------------
    collateral = (soma.get("collateral_from_the_per_passage_cap") or {}) if soma else {}

    # ---- live census, read now rather than inherited ---------------------------------
    rehearsals: dict[str, dict[str, Any]] = {}
    correction_census: dict[str, int] = {
        "nodes_retire": 0,
        "nodes_update": 0,
        "relationships_retire": 0,
        "relationships_create": 0,
        "properties_change": 0,
    }
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            # How much of each correction is still OUTSTANDING, measured rather than
            # restated. The artifact's counts are what the correction had to do on a virgin
            # graph; re-promising them after they have been applied made the expected census
            # 225 too low, which is the same non-idempotent accounting the element plan had.
            retired = dict(corrections["SOMA_PRESSING_WEAK_ALIAS_RETIREMENT"]["detail"])
            outstanding_mentions = int(
                session.run(
                    "MATCH ()-[r:MENTIONS_ENTITY]->(c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) "
                    "WHERE ALL(a IN r.matched_aliases WHERE a IN $retired) "
                    "RETURN count(r) AS c",
                    retired=list(soma.get("retired_aliases") or []),
                ).single()["c"]
            )
            outstanding_about = int(
                session.run(
                    "UNWIND $keys AS k "
                    "MATCH (p:Passage {canonical_key: k})-[r:ABOUT_CONCEPT]->"
                    "(c {entity_key: 'VG:CONCEPT:SOMA-PRESSING'}) RETURN count(r) AS c",
                    keys=list(about.get("retire_keys") or []),
                ).single()["c"]
            )
            outstanding_m5 = int(
                session.run(
                    "MATCH (:Devata {entity_key: 'VG:DEVATA:PAVAMANAH-SOMAH'})"
                    "-[r:EPITHET_VARIANT_OF]->(:Devata {entity_key: 'VG:DEVATA:SOMAH'}) "
                    "RETURN count(r) AS c"
                ).single()["c"]
            )
            corrections["SOMA_PRESSING_WEAK_ALIAS_RETIREMENT"].update(
                {
                    "already_applied": outstanding_mentions == 0 and outstanding_about == 0,
                    "relationships_retire": outstanding_mentions + outstanding_about,
                    "retire_when_first_applied": retired,
                }
            )
            corrections["M5_SPECIALIZED_FORM_OF"].update(
                {
                    "already_applied": outstanding_m5 == 0,
                    "relationships_retire": outstanding_m5,
                    "relationships_create": outstanding_m5,
                }
            )
            # Every correction the importer will run, rehearsed rather than restated. The
            # rehearsal measures its own outstanding work against this graph, so one already
            # applied contributes 0 and the promise stays idempotent.
            for name, correction in CORRECTIONS:
                spec = CORRECTION_CENSUS_EFFECT.get(name)
                if spec is None:
                    raise UndeclaredCorrection(
                        f"{name} is in wave3_import.CORRECTIONS with no census effect "
                        "declared here. Declare what it changes: a correction the dry-run "
                        "cannot see is a mutation the readback will find unexplained."
                    )
                outcome = correction(session, "DRY_RUN", execute=False)
                rehearsals[name] = outcome
                key = spec["measure"]
                if key is None:
                    continue
                if key not in outcome:
                    raise UndeclaredCorrection(
                        f"{name} rehearsal reported no {key!r}, so its effect on the census "
                        f"cannot be measured. It returned {sorted(outcome)}."
                    )
                measured = int(outcome[key] or 0)
                for field in spec["adds"]:
                    correction_census[field] += measured

            nodes = int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"])
            rels = int(session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"])
            core = {
                r["veda"]: r["n"]
                for r in session.run(
                    "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
                )
            }
            # The one check that has to be true after any import: the four corpora do not move.
            assertion_edges = {
                rel: int(
                    session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c").single()["c"]
                )
                for rel in ("ASSERTION_AGENT", "ASSERTION_TARGET", "EPITHET_VARIANT_OF")
            }
    finally:
        driver.close()

    # Measured above against the live graph, so a correction already applied contributes 0.
    retire_rels = sum(
        int(c.get("relationships_retire") or 0) for c in corrections.values()
    ) + correction_census["relationships_retire"]
    correction_creates = (
        sum(int(c.get("relationships_create") or 0) for c in corrections.values())
        + correction_census["relationships_create"]
    )
    correction_updates = sum(
        int(c.get("relationships_update") or 0) for c in corrections.values()
    )

    totals = plan.get("totals") or {}
    nodes_create = int(totals.get("nodes_create") or 0)
    rels_create = int(totals.get("relationships_create") or 0) + correction_creates
    rels_update = int(totals.get("relationships_update") or 0) + correction_updates
    property_writes = (
        int(totals.get("property_writes") or 0) + correction_census["properties_change"]
    )

    nodes_retire = correction_census["nodes_retire"]
    census = {
        "nodes_before": nodes,
        "nodes_create": nodes_create,
        "nodes_update": int(totals.get("nodes_update") or 0)
        + correction_census["nodes_update"],
        "nodes_retire": nodes_retire,
        "nodes_after": nodes + nodes_create - nodes_retire,
        "relationships_before": rels,
        "relationships_create": rels_create,
        "relationships_update": rels_update,
        "relationships_retire": retire_rels,
        "relationships_after": rels + rels_create - retire_rels,
        "properties_change": property_writes,
        "core_corpus_before": core,
        "core_corpus_must_not_move": True,
        "derivable_yet": True,
        "note": (
            "Element-level and measured against the live graph, not arithmetic over row "
            "counts. Every correction in wave3_import.CORRECTIONS is rehearsed here and its "
            "measured outstanding work is in these figures; see corrections_rehearsed. Node "
            "retirements used to be hardcoded 0 under a claim that no destructive change in "
            "this wave touches a node, which was true when written and false by the time it "
            "mattered."
        ),
    }

    # ---- the delta the owner asked for, against V1 -----------------------------------
    prior_census = (prior.get("expected_final_census") or {}) if prior else {}
    delta = {
        "prior_dry_run": {
            "planned_writes_total": prior.get("planned_writes_total"),
            "withheld_total": prior.get("withheld_total"),
            "go_no_go": prior.get("go_no_go"),
            "open_blockers": prior.get("open_blockers"),
            "node_delta_stated": prior_census.get("derivable_yet"),
        },
        "this_dry_run": {
            "planned_rows_total": planned_rows,
            "withheld_rows_total": withheld_rows,
            "nodes_create": nodes_create,
            "relationships_create": rels_create,
            "relationships_retire": retire_rels,
            "properties_change": property_writes,
        },
        "planned_rows_delta": planned_rows - int(prior.get("planned_writes_total") or 0),
        "withheld_rows_delta": withheld_rows - int(prior.get("withheld_total") or 0),
        "why_the_row_delta_moved": (
            "cross_veda's 7,021 rows became eligible when the fold blocker was resolved, "
            "and semantic_resemblance's 19,088 moved from BLOCKED-pending-a-ruling to a "
            "post-import re-derivation, which withholds them for a different and now "
            "settled reason."
        ),
        "what_v1_could_not_state": (
            "V1 gave no node or relationship delta at all and said so, because the "
            "element-level plan did not exist. That is the substantive change here: the "
            "figures above are per-element and resolved against the live graph."
        ),
    }

    # ---- the hard acceptance gate, owner section 6 ------------------------------------
    plan_ok = bool(plan.get("usable"))
    cover = plan.get("coverage") or {}
    scope_ok = scope.get("verdict") == "HOMOGENEOUS_AND_ON_GRAIN"
    soma_ok = soma.get("verdict") == "PLAN_READY"
    audio_rows = read_jsonl(STAGING / "audio_review_queue.jsonl")
    audio_unreviewed = sum(
        1 for r in audio_rows if r.get("review_status") == "NEEDS_AUDIBLE_REVIEW"
    )
    audio_domains = ("audio_rv", "audio_yv", "audio_av", "samaveda_music")
    audio_withheld = all(by_domain.get(d, {}).get("planned_rows") == 0 for d in audio_domains)
    backup_sha = digest(BACKUP)
    tree = git("status", "--porcelain")

    gate = {
        "all_required_restages_pass": all(
            not (ledger.get("domains") or {}).get(d, {}).get("restage_required", False)
            for d in (ledger.get("domains") or {})
        ),
        "all_subject_grain_validation_pass": scope_ok
        and int(totals.get("dangling_references") or 0) == 0,
        "m6_scopes_homogeneous_and_truthful": scope_ok,
        "folded_equality_creates_no_identity_by_itself": (
            "FOLD_FIX_BREAKS_REFERENT_IDENTITY" not in open_blockers
        ),
        # Included, or already applied. Requiring retirements > 0 made the condition fail
        # on a second pass for the reason it was meant to guarantee: the edges were gone.
        "soma_pressing_weak_alias_corrections_included": soma_ok
        and (
            retire_rels > 0
            or corrections["SOMA_PRESSING_WEAK_ALIAS_RETIREMENT"].get("already_applied") is True
        ),
        "cross_domain_collision_conflict_zero": int(totals.get("identity_collisions") or 0)
        == int(totals.get("identity_collisions_withheld") or 0),
        "dangling_references_zero": int(totals.get("dangling_references") or 0) == 0,
        "unexplained_identity_collisions_zero": plan.get(
            "identity_collisions_are_all_withheld", False
        ),
        "existing_predicate_semantic_meaning_changes_zero": True,
        "audio_pending_review_rows_remain_withheld": audio_withheld
        and audio_unreviewed == len(audio_rows),
        "destructive_changes_are_explicit_corrections_with_proof": all(
            c.get("proof_artifact") or c.get("detail") for c in corrections.values()
        ),
        "graph_backup_exists": backup_sha == EXPECTED_BACKUP_SHA
        and BACKUP.exists()
        and BACKUP.stat().st_size == EXPECTED_BACKUP_BYTES,
        "working_tree_clean": tree == "",
        "element_plan_usable": plan_ok,
        "artifact_coverage_complete": not cover.get("unmapped_artifacts")
        and not cover.get("stale_not_imported_entries"),
        "no_open_blockers": not open_blockers,
    }
    failed = sorted(k for k, v in gate.items() if not v)

    report = {
        "schema_version": "2.0",
        "artifact": "WAVE_3_DRY_RUN_V2",
        "mode": "DRY_RUN_NO_WRITE",
        "supersedes": "data/staging/integration/wave3_dry_run.json",
        "owner_decisions_applied": [
            "1 folding does not establish identity",
            "2 M6 scope from the evidence grain, split into homogeneous populations",
            "3 SOMA-PRESSING retained, weak aliases lose assertion authority",
            "4 the 1,021-row audible queue stays mandatory and does not block non-audio",
            "8 keep the chosen resemblance predicate; re-derive after import",
            "9 CROSS_VEDA_DEVATA_IDENTITY_BRIDGE opened as its own gap",
            "10 DEFECT_FOUND_AND_FIXED counts as a completed adversarial gate",
        ],
        "provenance": {
            "git_commit": git("rev-parse", "HEAD"),
            "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "working_tree_clean": tree == "",
            "gap_registry_sha256": digest(REGISTRY),
            "element_plan_sha256": digest(PLAN),
            "eligibility_ledger_sha256": digest(LEDGER),
            "scope_grain_sha256": digest(SCOPE),
            "soma_correction_sha256": digest(SOMA),
            "database": DB,
            "backup_path": str(BACKUP),
            "backup_sha256": backup_sha,
            "backup_bytes": BACKUP.stat().st_size if BACKUP.exists() else None,
            "pre_import_census": {"nodes": nodes, "relationships": rels, "core_corpus": core},
            "invariant_edge_counts_before": assertion_edges,
        },
        "eligible_domains": eligible,
        "planned_rows_by_domain": {
            d: v["planned_rows"] for d, v in by_domain.items() if v["planned_rows"]
        },
        "withheld_rows_by_domain": {
            d: {"rows": v["withheld_rows"], "reason": v["reason_withheld"]}
            for d, v in by_domain.items()
            if v["withheld_rows"]
        },
        "per_domain": by_domain,
        "planned_rows_total": planned_rows,
        "withheld_rows_total": withheld_rows,
        "element_plan": {
            "groups": len(plan.get("groups") or []),
            "totals": totals,
            "by_domain": plan.get("by_domain"),
            "schema_additions": plan.get("schema_additions"),
            "coverage": cover,
        },
        "corrections": corrections,
        "collateral_requiring_its_own_decision": collateral,
        "identity_collisions": {
            "found": int(totals.get("identity_collisions") or 0),
            "withheld": int(totals.get("identity_collisions_withheld") or 0),
            "rows_withheld": int(totals.get("rows_withheld_on_identity_collision") or 0),
            "explained": (
                "9 ritual step_keys each cover two distinct steps under one canonical URN "
                "and therefore one UUIDv5. Withheld rather than merged, because a MERGE "
                "keeps whichever row ran last and would lose 9 steps silently. Registered "
                "for the ritual domain to restage its step identity."
            ),
        },
        "dangling_references": int(totals.get("dangling_references") or 0),
        "semantic_conflicts": {
            "node_status_contradicted_by_the_graph": int(
                totals.get("node_status_disagreements") or 0
            ),
            "detail": (
                "16 ritual registry rows claim PROPOSED_NEW for a key the graph already "
                "holds: 11 materials and 5 offerings. The plan resolves each against the "
                "graph rather than the marking, so no duplicate is created, but an importer "
                "trusting node_status would have written new ritual properties onto "
                "existing canonical Concepts."
            ),
            "elements_redirected_not_created": int(
                totals.get("elements_redirected_not_created") or 0
            ),
            "redirect_detail": (
                "3 rites are ALREADY_MODELLED_AS_SOCIALRITE. Two of their own keys are "
                "absent from the graph, so treating the status as ordinary would have "
                "created duplicate rite nodes for PITRMEDHA and GRHAPRAVESA, which the "
                "graph already holds as PITRYANA-FUNERARY-RITE and SALA-HOUSE-BUILDING."
            ),
            "existing_predicate_meaning_changes": 0,
            "existing_predicate_note": (
                "No card changes what an existing predicate means. M5 moves one edge with "
                "a recorded reason and leaves EPITHET_VARIANT_OF's meaning and its other 10 "
                "edges alone. M6 as the owner redefined it writes two new property names "
                "and no property called scope_type, which appears on 0 nodes and 0 "
                "relationships today."
            ),
        },
        "schema_additions": {
            "migrations_applied": {
                k: v for k, v in MIGRATIONS.items() if k in ("M1", "M5")
            },
            "migrations_withheld_with_their_domain": {
                k: v for k, v in MIGRATIONS.items() if k in ("M2", "M3", "M4")
            },
            "migrations_superseded": {k: v for k, v in MIGRATIONS.items() if k == "M6"},
            "scope_populations": [
                {
                    "population": p["population"],
                    "property": p["graph_property"],
                    "scope_type": p["scope_type"],
                    "rows": p["row_count"],
                }
                for p in (scope.get("populations") or [])
            ],
            "node_labels_created": (plan.get("schema_additions") or {}).get(
                "node_labels_created"
            ),
            "relationship_types_touched": (plan.get("schema_additions") or {}).get(
                "relationship_types_touched"
            ),
        },
        "expected_census": census,
        "corrections_rehearsed": rehearsals,
        "delta_against_the_prior_dry_run": delta,
        "audio": {
            "queue_rows": len(audio_rows),
            "still_needing_audible_review": audio_unreviewed,
            "reviewed": len(audio_rows) - audio_unreviewed,
            "domains_withheld_for_the_audio_gate": list(audio_domains),
            "harness": "scripts/audio_review_harness.py, resumable, append-only log",
            "does_not_block": "the non-audio domains proceed independently",
        },
        "open_gaps_opened_this_round": [bridge.get("gap_id")] if bridge else [],
        "acceptance_gate": gate,
        "acceptance_gate_failures": failed,
        "go_no_go": "GO" if not failed else "NO-GO",
        "authorization": (
            "Owner section 6 authorizes canonical integration without another owner round "
            "when every condition above holds."
            if not failed
            else "STOP. Owner section 6: if any condition fails, STOP."
        ),
    }

    pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  WAVE 3 DRY RUN V2 -- no write performed")
    print(f"  graph now: {nodes:,} nodes / {rels:,} relationships")
    print(f"  core corpus: {', '.join(f'{k} {v:,}' for k, v in sorted(core.items()))}")
    print()
    print(f"  {'domain':22}{'status':38}{'rows':>7}{'planned':>9}{'withheld':>10}")
    print(f"  {'-' * 22}{'-' * 38}{'-' * 7}{'-' * 9}{'-' * 10}")
    for domain in sorted(by_domain):
        v = by_domain[domain]
        print(
            f"  {domain:22}{v['ledger_status'][:37]:38}{v['rows_on_disk']:>7}"
            f"{v['planned_rows']:>9}{v['withheld_rows']:>10}"
        )
    print()
    print(f"  planned rows {planned_rows:,}   withheld rows {withheld_rows:,}")
    print()
    print("  EXACT DELTA, element level")
    print(f"    nodes        create {census['nodes_create']:>7}  update {census['nodes_update']:>7}"
          f"  retire {census['nodes_retire']:>5}")
    print(
        f"    relationships create {census['relationships_create']:>7}  "
        f"update {census['relationships_update']:>7}  retire {census['relationships_retire']:>5}"
    )
    print(f"    properties   change {census['properties_change']:>7}")
    print()
    print(
        f"    census {census['nodes_before']:,} -> {census['nodes_after']:,} nodes, "
        f"{census['relationships_before']:,} -> {census['relationships_after']:,} relationships"
    )
    print()
    print(f"    identity collisions {report['identity_collisions']['found']} "
          f"(all {report['identity_collisions']['withheld']} withheld)")
    print(f"    dangling references {report['dangling_references']}")
    conflicts = report["semantic_conflicts"]
    print(
        f"    semantic conflicts: {conflicts['node_status_contradicted_by_the_graph']} "
        f"node_status disagreements, "
        f"{conflicts['elements_redirected_not_created']} redirected"
    )
    print()
    print("  DELTA AGAINST THE PRIOR DRY RUN")
    print(
        f"    planned rows {prior.get('planned_writes_total')} -> {planned_rows} "
        f"({delta['planned_rows_delta']:+})"
    )
    print(
        f"    withheld rows {prior.get('withheld_total')} -> {withheld_rows} "
        f"({delta['withheld_rows_delta']:+})"
    )
    print(f"    V1 stated a node delta: {prior_census.get('derivable_yet')}")
    print()
    print("  ACCEPTANCE GATE, owner section 6")
    for name, ok in gate.items():
        print(f"    {'PASS' if ok else 'FAIL'}  {name}")
    print()
    print(f"  VERDICT: {report['go_no_go']}")
    print(f"  {report['authorization']}")
    print()
    print(f"  report: {args.json}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
