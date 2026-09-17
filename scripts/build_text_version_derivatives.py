"""Stage the missing derived text versions for GAP-MORPHOLOGY-006.

Two populations, and they are different kinds of object, so they are emitted separately
and never summed:

1. ``SEARCH_DERIVATIVE`` for the three works that have none. The Atharvaveda already
   carries 5,839 of these and is not touched; the Rigveda, Samaveda and Yajurveda get one
   per mantra, built by :func:`vedagraph.enrich.text_derivatives.search_surface`, which is
   the Atharvavedic instrument plus one declared transliteration step for the two
   Devanagari-primary corpora.

2. ``NORMALIZED`` (accent-stripped) for the 139 Yajurvedic mantras whose source supplies no
   unaccented witness. These are our derivative, not a second edition, and they carry
   ``accent_source = DERIVED_ACCENT_STRIPPED`` so nothing downstream can read them as one.
   The other 1,836 Yajurvedic mantras keep the source's own unaccented text and get
   nothing new.

Neo4j is read **only**. Every mutation is staged for the lead to import.

Run::

    python scripts/build_text_version_derivatives.py
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Final

from dotenv import load_dotenv

from vedagraph.enrich.text_derivatives import (
    ACCENT_SOURCE_DERIVED,
    ACCENT_SOURCE_WITNESS,
    accent_stripped_surface,
    search_surface,
)
from vedagraph.identity import uuid_for_urn
from vedagraph.normalize.unicode import ComparisonForm, comparison_form

REPO: Final = Path(__file__).resolve().parents[1]
OUT_DIR: Final = REPO / "data" / "staging" / "final_closure_sprint" / "agent3"

#: The three works with no search derivative, with the role their searchable text sits in.
#: The Atharvaveda is absent deliberately: it already has one and re-deriving it would
#: rewrite 5,839 released rows to prove a point.
SOURCE_ROLE_BY_VEDA: Final[dict[str, str]] = {
    "RV": "PRIMARY_TEXT",
    "SV": "PRIMARY_TEXT",
    "YV": "EXTRACTED_FROM_CONTAINER",
}

SEARCH_VERSION_ID: Final[dict[str, str]] = {
    "RV": "VEDAGRAPH.RV.SEARCH_NORMALIZED",
    "SV": "VEDAGRAPH.SV.SEARCH_NORMALIZED",
    "YV": "VEDAGRAPH.YV.SEARCH_NORMALIZED",
}
YV_UNACCENTED_DERIVED_VERSION_ID: Final = "VEDAGRAPH.YV.VSM.UNACCENTED_DERIVED"

#: The probe that demonstrates the third clause of the closure test. Accent-bearing on
#: purpose: if the derivative did not strip the udatta, these return zero.
ACCENT_BEARING_PROBES: Final = ("agním", "sómam", "índra", "devásya")


def _session() -> Any:
    load_dotenv(str(REPO / ".env"))
    from neo4j import GraphDatabase

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "vedagraph_dev")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    return driver, driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j"))


def _read_sources(session: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for veda, role in SOURCE_ROLE_BY_VEDA.items():
        rows.extend(
            dict(record)
            for record in session.run(
                "MATCH (p:Mantra {veda:$veda})-[:HAS_TEXT_VERSION]->(t:TextVersion "
                "{text_role:$role}) "
                "RETURN p.canonical_key AS canonical_key, p.veda AS veda, "
                "t.script AS script, t.text_nfc AS text, t.source_id AS source_id, "
                "t.source_artifact_id AS source_artifact_id, "
                "t.rights_status AS rights_status, t.text_version_id AS derived_from",
                veda=veda,
                role=role,
            )
        )
    return rows


def _read_yv_missing_unaccented(session: Any) -> list[dict[str, Any]]:
    return [
        dict(record)
        for record in session.run(
            "MATCH (p:Mantra {veda:'YV'})-[:HAS_TEXT_VERSION]->"
            "(t:TextVersion {text_role:'EXTRACTED_FROM_CONTAINER'}) "
            "WHERE NOT (p)-[:HAS_TEXT_VERSION]->(:TextVersion {accented:false}) "
            "RETURN p.canonical_key AS canonical_key, t.script AS script, "
            "t.text_nfc AS text, t.source_id AS source_id, "
            "t.source_artifact_id AS source_artifact_id, "
            "t.rights_status AS rights_status, t.text_version_id AS derived_from"
        )
    ]


def build_search_rows(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for src in sources:
        derived = search_surface(src["text"], src["script"])
        version_id = SEARCH_VERSION_ID[src["veda"]]
        urn = f"urn:vedagraph:text:{src['canonical_key']}:{version_id}"
        rows.append(
            {
                "text_id": str(uuid_for_urn(urn)),
                "canonical_key": src["canonical_key"],
                "veda": src["veda"],
                "text_version_id": version_id,
                "text_role": "SEARCH_DERIVATIVE",
                "language": "sa",
                "script": derived.script,
                "text_form": "SAMHITA",
                "text_nfc": derived.text,
                "text_original": derived.text,
                "accented": False,
                "content_sha256": derived.content_sha256,
                "source_id": src["source_id"],
                "source_artifact_id": src["source_artifact_id"],
                "source_locator": f"derived:{'+'.join(derived.derivation_steps)}",
                # A derivative inherits its parent's rights. It is a transform of the
                # source text, not a new text, so it cannot be freer than what it came from.
                "rights_status": src["rights_status"],
                "derived_from_text_version_id": src["derived_from"],
                "derivation_steps": list(derived.derivation_steps),
                "provenance": "deterministic",
                "provenance_note": (
                    "Derived by a declared string transform over text already ingested. "
                    "No source was acquired and no human annotation is claimed."
                ),
            }
        )
    return rows


def build_yv_unaccented_rows(missing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for src in missing:
        derived = accent_stripped_surface(src["text"], src["script"])
        urn = f"urn:vedagraph:text:{src['canonical_key']}:{YV_UNACCENTED_DERIVED_VERSION_ID}"
        rows.append(
            {
                "text_id": str(uuid_for_urn(urn)),
                "canonical_key": src["canonical_key"],
                "veda": "YV",
                "text_version_id": YV_UNACCENTED_DERIVED_VERSION_ID,
                "text_role": "NORMALIZED",
                "language": "sa",
                "script": derived.script,
                "text_form": "SAMHITA",
                "text_nfc": derived.text,
                "text_original": derived.text,
                "accented": False,
                "content_sha256": derived.content_sha256,
                "source_id": src["source_id"],
                "source_artifact_id": src["source_artifact_id"],
                "source_locator": f"derived:{'+'.join(derived.derivation_steps)}",
                "rights_status": src["rights_status"],
                "derived_from_text_version_id": src["derived_from"],
                "derivation_steps": list(derived.derivation_steps),
                # The single most important field on this row.
                "accent_source": ACCENT_SOURCE_DERIVED,
                "accent_source_note": (
                    "Our accent-stripped derivative of our own accented text. The "
                    "Wikisource unaccented witness does not cover this mantra. This row "
                    f"is NOT a second edition; the 1,836 covered mantras carry "
                    f"{ACCENT_SOURCE_WITNESS}."
                ),
                "provenance": "deterministic",
            }
        )
    return rows


def probe_cross_corpus(
    session: Any, search_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Run the accent-bearing probes against staged RV/SV/YV plus live AV."""
    av_texts = [
        record["text"]
        for record in session.run(
            "MATCH (:Mantra {veda:'AV'})-[:HAS_TEXT_VERSION]->"
            "(t:TextVersion {text_role:'SEARCH_DERIVATIVE'}) RETURN t.text_nfc AS text"
        )
    ]
    by_veda: dict[str, list[str]] = {"AV": av_texts}
    for row in search_rows:
        by_veda.setdefault(row["veda"], []).append(row["text_nfc"])
    results: list[dict[str, Any]] = []
    for probe in ACCENT_BEARING_PROBES:
        folded = comparison_form(probe, ComparisonForm.SEARCH_NORMALIZED)
        hits = {
            veda: sum(1 for text in texts if folded in text)
            for veda, texts in sorted(by_veda.items())
        }
        results.append(
            {
                "query": probe,
                "query_is_accent_bearing": probe != folded,
                "folded_query": folded,
                "hits_per_veda": hits,
                "reaches_all_four": all(count > 0 for count in hits.values()),
            }
        )
    return results


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    driver, session = _session()
    try:
        sources = _read_sources(session)
        missing = _read_yv_missing_unaccented(session)
        search_rows = build_search_rows(sources)
        yv_rows = build_yv_unaccented_rows(missing)
        probes = probe_cross_corpus(session, search_rows)
        live_av = session.run(
            "MATCH (t:TextVersion) WHERE t.text_role='SEARCH_DERIVATIVE' "
            "RETURN count(t) AS n"
        ).single()["n"]
    finally:
        session.close()
        driver.close()

    search_path = OUT_DIR / "text_versions_search_derivative.jsonl"
    yv_path = OUT_DIR / "text_versions_yv_unaccented_derived.jsonl"
    for path, rows in ((search_path, search_rows), (yv_path, yv_rows)):
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    per_veda: dict[str, int] = {}
    for row in search_rows:
        per_veda[row["veda"]] = per_veda.get(row["veda"], 0) + 1
    manifest = {
        "artifact": "AGENT_3_TEXT_VERSION_DERIVATIVES",
        "gap": "GAP-MORPHOLOGY-006",
        "at": datetime.now(UTC).isoformat(),
        "neo4j_access": "READ_ONLY",
        "search_derivative": {
            "staged_rows": len(search_rows),
            "per_veda": per_veda,
            "already_live_AV": live_av,
            "post_import_total": len(search_rows) + live_av,
        },
        "yv_unaccented_derived": {
            "staged_rows": len(yv_rows),
            "accent_source": ACCENT_SOURCE_DERIVED,
        },
        "accent_bearing_probes": probes,
        "files": {
            path.name: sha256(path.read_bytes()).hexdigest()
            for path in (search_path, yv_path)
        },
    }
    manifest_path = OUT_DIR / "text_versions_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
