"""Stage the ``domain`` assignment for every :DomainEntity node -- GAP-SEMANTICS-005.

The property was designed into the label name and never written, so the entity population
cannot be partitioned at all. This stages it.

**The vocabulary is declared before assignment and it is closed.** :data:`DOMAINS` is the
whole of it; an entity that resolves to nothing in it raises rather than silently receiving
an empty list, because an empty list and "we never looked" are indistinguishable once
written.

**The property is list-valued, and that is the point.** Soma is ritual, botanical and
material at once; a single-valued domain would force a false choice and then the false
choice would be the thing every later count was taken over. A one-domain entity carries a
one-element list, so no reader has to branch on type.

**Two provenances, typed apart on the node, never merged.**

``deterministic``
    The domain follows by a declared rule from a label the registry already carries. The
    rule is in :data:`LABEL_DOMAINS` and a reader can re-run it.

``model-assisted``
    There is no label that decides it, so the domain was read off the entity's own English
    gloss by a model. It is recorded as ``model-assisted`` on the node. **It is not human
    annotation and must never be reported as one.** The 22 bare ``:Concept`` entities and
    a handful of label-ambiguous ones are the whole of this class.

Neo4j is read **only**. Every mutation is staged for the lead to import.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

REPO: Final = Path(__file__).resolve().parents[1]
OUT_DIR: Final = REPO / "data" / "staging" / "final_closure_sprint" / "agent3"

#: The closed domain vocabulary. Declared before any assignment was made.
DOMAINS: Final[dict[str, str]] = {
    "RITUAL": "the sacrifice and its performance: rites, officiants, oblations, "
    "implements and the acts that make up a rite",
    "COSMOLOGICAL": "the ordered world and its powers: the three worlds, the waters, "
    "dawn, the seasons, the phenomena a hymn addresses as agents",
    "MATERIAL": "worked and unworked physical stuff: metals, substances, made objects, "
    "weapons, grain as a commodity",
    "BIOTIC": "living kinds as living kinds: plants and animals",
    "SOCIAL": "human collectivities and the relations inside them: tribes, kingship, "
    "kinship, alliance, rivalry, the ancestors",
    "CORPOREAL": "the body and what happens to it: parts, breath, lifespan, affliction, "
    "healing, death",
    "SPECULATIVE": "the abstract vocabulary the hymns reason with: order, truth, being, "
    "mind, formulation, and the qualities predicated of gods and men",
    "GEOGRAPHIC": "located things: rivers as places, mountains, fields, dwellings",
}

#: Deterministic rules. Every label a node carries contributes its domains, and the node's
#: domain list is the union. A node whose labels fire several rules is genuinely
#: multi-domain and keeps all of them.
LABEL_DOMAINS: Final[dict[str, tuple[str, ...]]] = {
    "Ritual": ("RITUAL",),
    "SocialRite": ("RITUAL", "SOCIAL"),
    "RitualRole": ("RITUAL", "SOCIAL"),
    "Offering": ("RITUAL", "MATERIAL"),
    "Object": ("MATERIAL",),
    "Weapon": ("MATERIAL",),
    "Substance": ("MATERIAL",),
    "Metal": ("MATERIAL",),
    "Crop": ("MATERIAL", "BIOTIC"),
    "Plant": ("BIOTIC",),
    "Animal": ("BIOTIC",),
    "NaturalPhenomenon": ("COSMOLOGICAL",),
    "CosmicEntity": ("COSMOLOGICAL",),
    "River": ("COSMOLOGICAL", "GEOGRAPHIC"),
    "Place": ("GEOGRAPHIC",),
    "Tribe": ("SOCIAL",),
    "Condition": ("CORPOREAL",),
    "State": ("CORPOREAL",),
    "PhilosophicalConcept": ("SPECULATIVE",),
    "Quality": ("SPECULATIVE",),
    "HumanConcern": ("SOCIAL", "CORPOREAL"),
}

#: ``:Action`` alone does not decide a domain -- 23 of the 26 are acts of the sacrifice and
#: 3 are not -- so the rule is conditioned on the registry's own ``wave3_domain`` flag,
#: which records which curation wave created the node. That is still deterministic: it
#: reads a property the registry carries rather than the entity's meaning.
ACTION_RITUAL_FLAG: Final = "ritual"

#: Entities no label decides. Read off the entity's own English gloss BY A MODEL. Typed
#: ``model-assisted`` on the node and never reported as human annotation.
CURATED_DOMAINS: Final[dict[str, tuple[str, ...]]] = {
    # The 22 bare :Concept entities.
    "VG:CONCEPT:ADHVAN-PATH": ("COSMOLOGICAL", "GEOGRAPHIC"),
    "VG:CONCEPT:AVAS-HELP": ("SOCIAL",),
    "VG:CONCEPT:AYUS-LIFE": ("CORPOREAL",),
    "VG:CONCEPT:BHESAJA-HEALING": ("CORPOREAL", "RITUAL"),
    "VG:CONCEPT:ENAS-SIN": ("SPECULATIVE", "SOCIAL"),
    "VG:CONCEPT:HRD-HEART": ("CORPOREAL",),
    "VG:CONCEPT:JANA-PEOPLE": ("SOCIAL",),
    "VG:CONCEPT:KAMA-DESIRE": ("SPECULATIVE",),
    "VG:CONCEPT:MRTYU-DEATH": ("CORPOREAL", "COSMOLOGICAL"),
    "VG:CONCEPT:PITARAH-ANCESTORS": ("SOCIAL", "RITUAL"),
    "VG:CONCEPT:PRAJA-OFFSPRING": ("SOCIAL", "CORPOREAL"),
    "VG:CONCEPT:PRANA-BREATH": ("CORPOREAL",),
    "VG:CONCEPT:RAJAN-KINGSHIP": ("SOCIAL",),
    "VG:CONCEPT:SAKHYA-FRIENDSHIP": ("SOCIAL",),
    "VG:CONCEPT:SAMAN-CHANT": ("RITUAL",),
    "VG:CONCEPT:SARMAN-PROTECTION": ("SOCIAL", "RITUAL"),
    "VG:CONCEPT:SATRU-ENEMY": ("SOCIAL",),
    "VG:CONCEPT:TANU-BODY": ("CORPOREAL",),
    "VG:CONCEPT:VAJA-PRIZE": ("SOCIAL", "MATERIAL"),
    "VG:CONCEPT:VASU-WEALTH": ("MATERIAL", "SOCIAL"),
    "VG:CONCEPT:VIRA-HERO": ("SOCIAL",),
    "VG:CONCEPT:VRATA-ORDINANCE": ("SPECULATIVE", "RITUAL"),
    # The three :Action entities the registry's ritual flag does not claim. Two of them
    # genuinely are not ritual acts; the third is one and the flag simply missed it, which
    # is why the flag alone could not be trusted to decide the class.
    "VG:CONCEPT:JANMAN-BIRTH": ("CORPOREAL", "SOCIAL"),
    "VG:CONCEPT:YUDH-BATTLE": ("SOCIAL",),
    "VG:CONCEPT:AVABHRTHA-CONCLUDING-BATH": ("RITUAL",),
}


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


def assign(entity_key: str, labels: list[str], wave3_domain: str | None) -> dict[str, Any]:
    """Resolve one entity's domains, with the provenance that produced them.

    :raises ValueError: if nothing resolves. An entity with no domain would reintroduce
        the exact null this gap is about, one node at a time.
    """
    derived: set[str] = set()
    fired: list[str] = []
    for label in labels:
        domains = LABEL_DOMAINS.get(label)
        if domains:
            derived.update(domains)
            fired.append(f"label:{label}")
    if "Action" in labels and wave3_domain == ACTION_RITUAL_FLAG:
        derived.add("RITUAL")
        fired.append("label:Action+wave3_domain:ritual")

    curated = CURATED_DOMAINS.get(entity_key, ())
    if derived and not curated:
        provenance, basis = "deterministic", fired
    elif curated and not derived:
        provenance, basis = "model-assisted", ["gloss_read_by_model"]
    elif curated and derived:
        provenance, basis = "deterministic+model-assisted", [*fired, "gloss_read_by_model"]
    else:
        raise ValueError(
            f"{entity_key} resolves to no domain from labels {labels!r} and has no curated "
            "entry; add a rule or a curated assignment rather than writing an empty list"
        )

    domains = sorted(derived | set(curated))
    unknown = [d for d in domains if d not in DOMAINS]
    if unknown:
        raise ValueError(f"{entity_key} produced domains outside the closed vocabulary: {unknown}")
    return {
        "entity_key": entity_key,
        "domain": domains,
        "domain_count": len(domains),
        "domain_provenance": provenance,
        "domain_basis": basis,
        "domain_vocabulary_version": "VG_DOMAIN_SPHERES_V1",
        "domain_is_human_annotation": False,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    driver, session = _session()
    try:
        entities = [
            dict(record)
            for record in session.run(
                "MATCH (e:DomainEntity) RETURN e.entity_key AS entity_key, "
                "[l IN labels(e) WHERE NOT l IN ['DomainEntity','Concept']] AS labels, "
                "e.wave3_domain AS wave3_domain, e.domain AS existing_domain "
                "ORDER BY e.entity_key"
            )
        ]
        null_before = session.run(
            "MATCH (e:DomainEntity) WHERE e.domain IS NULL RETURN count(e) AS n"
        ).single()["n"]
    finally:
        session.close()
        driver.close()

    rows = [assign(e["entity_key"], e["labels"], e["wave3_domain"]) for e in entities]
    path = OUT_DIR / "domain_entity_domains.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    by_provenance: dict[str, int] = {}
    by_domain: dict[str, int] = {}
    multi = 0
    for row in rows:
        by_provenance[row["domain_provenance"]] = by_provenance.get(row["domain_provenance"], 0) + 1
        multi += row["domain_count"] > 1
        for domain in row["domain"]:
            by_domain[domain] = by_domain.get(domain, 0) + 1
    manifest = {
        "artifact": "AGENT_3_DOMAIN_ENTITY_DOMAINS",
        "gap": "GAP-SEMANTICS-005",
        "at": datetime.now(UTC).isoformat(),
        "neo4j_access": "READ_ONLY",
        "vocabulary": DOMAINS,
        "vocabulary_declared_before_assignment": True,
        "entities": len(rows),
        "domain_is_null_before": null_before,
        "domain_is_null_after_import": 0,
        "multi_domain_entities": multi,
        "by_provenance": by_provenance,
        "by_domain": dict(sorted(by_domain.items())),
        "human_annotation_claimed": False,
        "files": {path.name: sha256(path.read_bytes()).hexdigest()},
    }
    (OUT_DIR / "domain_entity_domains_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
