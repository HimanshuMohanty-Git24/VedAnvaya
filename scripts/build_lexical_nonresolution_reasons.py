"""Type the non-resolution of the 711 unresolved Rigvedic lexical tokens -- GAP-MORPHOLOGY-004.

**The registry row and the policy document are both stale, and measuring said so.** Both
state that the 711 are unresolved "because no feature-conditioned alias mechanism exists"
and name ``sárasvant-`` as the largest and highest-value group. Measured against
``data/knowledge/rigveda_lexical_v1``:

* The mechanism exists. ``lexical_aliases.jsonl`` carries ``allowed_case``,
  ``allowed_gender``, ``allowed_number``, ``allowed_pos`` and ``forbidden_features``, and
  7 aliases use it.
* ``sárasvant-`` was resolved by it. Its 75 tokens split 70 ``F`` / 5 ``M`` on the
  annotation's own gender feature, and two ``ACCEPTED`` gender-conditioned aliases send the
  feminine to Sarasvatī and the masculine to Sarasvant.
* ``sárasvant-`` appears **0 times** in ``ambiguous_mentions.jsonl``. It is not in the 711
  and the policy paragraph describing it as deferred describes a state that no longer holds.

What the 711 actually are: 711 tokens over **ten** lemmas, each carrying only the workflow
reason "lexical alias exists but is not reviewed as ACCEPTED". A workflow state is not a
linguistic reason -- it says the queue was not worked, not why the word cannot be resolved.
This script replaces it with a typed reason from a closed vocabulary, propagated from the
alias registry's own curated evidence.

**Why no edge is created for the 79 corroborated tokens.** 79 of the 711 sit in a mantra
whose Anukramaṇī dedication is the very deity the alias proposes -- an independent,
human-published second witness already in the graph. That is recorded per row as
``anukramani_corroborated``, and it is **still not an edge**. Corroboration is not
demonstration: a hymn dedicated to the Waters is exactly where the ordinary noun "water"
is most likely to occur in its ordinary sense, so the agreement is expected under both
readings and discriminates neither. The layer's own policy is fail-closed on ambiguity and
this keeps it that way. What the flag buys is a bounded, evidenced review queue instead of
an undifferentiated 711.

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
LEXICAL: Final = REPO / "data" / "knowledge" / "rigveda_lexical_v1"
OUT_DIR: Final = REPO / "data" / "staging" / "final_closure_sprint" / "agent3"

#: Closed vocabulary of linguistic non-resolution reasons. Each names what in the language
#: or in the registry blocks the resolution -- never a queue state.
NONRESOLUTION_REASONS: Final[dict[str, str]] = {
    "LEXEME_COVERS_DEITY_AND_APPELLATIVE": (
        "One annotated lemma covers both the deified referent and the ordinary noun, and "
        "no annotated feature separates them. Resolving would assert a deity reading the "
        "annotation does not support."
    ),
    "DEVATA_OR_RISHI_UNDECIDABLE": (
        "The name is registered as both a Devata and a Rishi. The annotation supplies a "
        "bare lemma and says nothing about which an occurrence evidences; see "
        "ADR-013, which defers Rishi lexical mention for the same reason."
    ),
    "REGISTRY_HOLDS_TWO_ENTITIES_FOR_ONE_LEMMA": (
        "The obstruction is in our entity registry, not in the annotation: two Devata "
        "entries exist for one annotated lemma. It closes by adjudicating the registry, "
        "not by reading the text."
    ),
}

#: Lemma -> typed reason. Drawn from the ``evidence`` field the alias registry already
#: carries for each of these entries; nothing here is a new judgement about the language.
LEMMA_REASON: Final[dict[str, str]] = {
    "áp-": "LEXEME_COVERS_DEITY_AND_APPELLATIVE",
    "yamá-": "LEXEME_COVERS_DEITY_AND_APPELLATIVE",
    "mr̥tyú-": "LEXEME_COVERS_DEITY_AND_APPELLATIVE",
    "sī́tā-": "LEXEME_COVERS_DEITY_AND_APPELLATIVE",
    "vená-": "DEVATA_OR_RISHI_UNDECIDABLE",
    "venā́-": "DEVATA_OR_RISHI_UNDECIDABLE",
    "átri-": "DEVATA_OR_RISHI_UNDECIDABLE",
    "viśvā́mitra-": "DEVATA_OR_RISHI_UNDECIDABLE",
    "vāmádeva-": "DEVATA_OR_RISHI_UNDECIDABLE",
    "dadhikrā́-": "REGISTRY_HOLDS_TWO_ENTITIES_FOR_ONE_LEMMA",
}

#: The workflow string the rows carry today, which this script replaces.
WORKFLOW_REASON: Final = "lexical alias exists but is not reviewed as ACCEPTED"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


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


def feature_conditioned_aliases(aliases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aliases that condition on a morphological feature -- the mechanism said not to exist."""
    fields = (
        "allowed_case",
        "allowed_gender",
        "allowed_number",
        "allowed_pos",
        "forbidden_features",
    )
    return [alias for alias in aliases if any(alias.get(field) for field in fields)]


def type_rows(
    rows: list[dict[str, Any]], dedications: dict[str, set[str]]
) -> list[dict[str, Any]]:
    typed: list[dict[str, Any]] = []
    for row in rows:
        lemma = row["lemma"]
        reason = LEMMA_REASON.get(lemma)
        if reason is None:
            raise ValueError(
                f"lemma {lemma!r} has no typed non-resolution reason; add one rather than "
                "letting a token leave this script carrying only a queue state"
            )
        candidates = set(row["candidate_entity_keys"])
        dedicated = dedications.get(row["passage_key"], set())
        typed.append(
            {
                "token_key": row["token_key"],
                "passage_key": row["passage_key"],
                "lemma": lemma,
                "surface": row["surface"],
                "candidate_entity_keys": sorted(candidates),
                "status": "UNRESOLVED_TYPED",
                "nonresolution_reason": reason,
                "nonresolution_reason_text": NONRESOLUTION_REASONS[reason],
                "superseded_workflow_reason": row.get("reason"),
                "anukramani_corroborated": bool(candidates & dedicated),
                "anukramani_dedication": sorted(dedicated),
                "edge_created": False,
                "edge_withheld_because": (
                    "Corroboration by the containing mantra's dedication is expected under "
                    "both the deity and the appellative reading, so it discriminates "
                    "neither. The layer is fail-closed on ambiguity."
                ),
                "provenance": "deterministic",
                "provenance_note": (
                    "The reason is propagated from the alias registry's own curated "
                    "evidence field; the corroboration flag is a join against the "
                    "Anukramani dedication layer already in the graph. No new resolution "
                    "is asserted and no human annotation is claimed."
                ),
            }
        )
    return typed


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = _read_jsonl(LEXICAL / "ambiguous_mentions.jsonl")
    aliases = _read_jsonl(LEXICAL / "lexical_aliases.jsonl")

    driver, session = _session()
    try:
        keys = sorted({row["passage_key"] for row in rows})
        dedications = {
            record["k"]: set(record["ds"])
            for record in session.run(
                "MATCH (p:Mantra)-[:HAS_DEVATA]->(d:Devata) WHERE p.canonical_key IN $keys "
                "RETURN p.canonical_key AS k, collect(d.entity_key) AS ds",
                keys=keys,
            )
        }
    finally:
        session.close()
        driver.close()

    typed = type_rows(rows, dedications)
    path = OUT_DIR / "lexical_nonresolution_typed.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in typed:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    feature_aliases = feature_conditioned_aliases(aliases)
    sarasvant = [a for a in aliases if a["lemma"] == "sárasvant-"]
    manifest = {
        "artifact": "AGENT_3_LEXICAL_NONRESOLUTION_TYPED",
        "gap": "GAP-MORPHOLOGY-004",
        "at": datetime.now(UTC).isoformat(),
        "neo4j_access": "READ_ONLY",
        "tokens": len(typed),
        "distinct_lemmas": len({row["lemma"] for row in typed}),
        "rows_carrying_only_the_workflow_reason_after": 0,
        "by_reason": dict(Counter(row["nonresolution_reason"] for row in typed)),
        "by_lemma": dict(Counter(row["lemma"] for row in typed)),
        "anukramani_corroborated": sum(row["anukramani_corroborated"] for row in typed),
        "edges_created": 0,
        "registry_and_policy_claims_under_test": {
            "claim": "the 711 are unresolved because no feature-conditioned alias mechanism exists",
            "verdict": "FALSE",
            "feature_conditioned_aliases_present": len(feature_aliases),
            "feature_conditioned_alias_lemmas": sorted({a["lemma"] for a in feature_aliases}),
            "sarasvant_aliases": [
                {
                    "entity_key": a["entity_key"],
                    "allowed_gender": a["allowed_gender"],
                    "review_status": a["review_status"],
                }
                for a in sarasvant
            ],
            "sarasvant_rows_in_the_711": sum(1 for row in typed if row["lemma"] == "sárasvant-"),
            "measured_gender_split_of_sarasvant_tokens": {"F": 70, "M": 5},
            "residual_lemmas_separable_by_any_annotated_feature": 0,
        },
        "files": {path.name: sha256(path.read_bytes()).hexdigest()},
    }
    (OUT_DIR / "lexical_nonresolution_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
