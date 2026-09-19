"""Generate the provenance dataset the public sources page reads.

The graph stamps every text surface and every translation with a ``source_id``, but there is
no endpoint that lists the sources themselves -- the API answers questions about the corpus,
not about where the corpus came from. This script builds that list once, from the committed
registries, and writes it into ``frontend/public/data/provenance.json`` so the page can read
it off disk the way the homepage reads its world slice.

**Nothing here is written by hand.** Every title, editor, edition, date, licence and URL on
the sources page is copied out of ``data/registry/source_artifacts.yaml``. What this script
supplies is the one thing the registries do not record in a machine-readable field: which of
the 53 registered artifacts the shipped build actually loaded, and in what role. That is
declared in :data:`CONTRIBUTIONS` below, and every declaration names the repository record
that evidences it. The script refuses to write if a declared artifact, source or evidence
path does not exist, and it refuses to write if a shipped corpus carries an artifact no
declaration covers -- a sources page that silently drops a source it could not classify is
worse than no sources page, because the omission is invisible.

    uv run python scripts/build_frontend_provenance.py
    uv run python scripts/build_frontend_provenance.py --check

``--check`` writes nothing and exits non-zero if the committed JSON has drifted from the
registries, which is what CI and the frontend contract test run.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any, Final

import yaml

ROOT: Final = Path(__file__).resolve().parents[1]
REGISTRY: Final = ROOT / "data" / "registry"
CANONICAL: Final = ROOT / "data" / "canonical"
OUTPUT: Final = ROOT / "frontend" / "public" / "data" / "provenance.json"

#: Where a work's ``rights`` line points at the canonical build it was loaded from. The
#: registry states this in prose rather than in a field, so it is read out of the prose
#: rather than duplicated here: a second copy would be the one that goes stale.
CANONICAL_PATH_IN_RIGHTS: Final = re.compile(r"data/canonical/([A-Za-z0-9_]+)/manifest\.json")

VEDA_BY_WORK: Final = {
    "VG:WORK:RV:SAK": "RV",
    "VG:WORK:SV:KAU": "SV",
    "VG:WORK:YV:VSM": "YV",
    "VG:WORK:AV:SAU": "AV",
}


class ProvenanceError(RuntimeError):
    """A declaration does not match the repository. Never recovered from."""


# ---------------------------------------------------------------------------------------
# The layers a reader distinguishes.
#
# Not the pipeline's stages and not the graph's labels: these are the four different things
# a source can give you, and they carry different obligations. A primary text is the object
# of study. A translation is one scholar reading it, always datable and always attributable.
# The traditional apparatus is the tradition's own index, which is evidence about the
# tradition and not an independent observation of the text. A recitation is a performance.
#
# Comparison sits apart on purpose. A witness consulted to check another witness shaped what
# is displayed without supplying any of it, and a reader who sees it listed beside the text
# sources would reasonably conclude some of the verses came from it.
# ---------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _measured_figures() -> dict[str, str]:
    """Figures a contribution sentence may interpolate, counted rather than written down.

    One entry today and the mechanism matters more than the count: the recitation sentence
    carried "16,834" as a literal and went on carrying it after the catalogue grew to
    17,780, because a number inside prose is the one number no test reads. A missing
    catalogue raises rather than substituting a guess -- this script builds a provenance
    document, and a provenance document that quietly states a stale figure is worse than
    one that fails to build.
    """
    catalogue = ROOT / "data" / "product" / "audio_catalog.jsonl"
    if not catalogue.is_file():
        raise ProvenanceError(
            f"{catalogue} is missing, so the recitation count cannot be measured. "
            "Refusing to write a provenance document with an unverified figure."
        )
    with catalogue.open("r", encoding="utf-8") as handle:
        recitations = sum(1 for line in handle if line.strip())
    return {"recitation_count": f"{recitations:,}"}


LAYERS: Final[list[dict[str, str]]] = [
    {
        "id": "primary-text",
        "label": "The Sanskrit text",
        "note": (
            "The verses themselves. Each of the four collections is carried from one "
            "electronic edition, named here with its underlying print edition."
        ),
    },
    {
        "id": "translation",
        "label": "Translations",
        "note": (
            "Every translation held here is out of copyright, which means every one of them "
            "is also a century or more old. They are period readings, not current "
            "scholarship, and the reader sees the translator and the year on every verse."
        ),
    },
    {
        "id": "traditional-apparatus",
        "label": "The traditional apparatus",
        "note": (
            "The indices the tradition itself keeps: who is named as the seer of a hymn, "
            "which deity it is assigned to, which metre it is in. This is evidence about "
            "the tradition's own account of the text."
        ),
    },
    {
        "id": "recitation",
        "label": "Recitation",
        "note": (
            "Audio is linked and streamed, never republished. It is a layer over the text "
            "rather than part of it."
        ),
    },
    {
        "id": "comparison",
        "label": "Consulted for comparison",
        "note": (
            "Witnesses read against the text to check it. None of them supplies a verse "
            "displayed on this site."
        ),
    },
]

LAYER_IDS: Final = {layer["id"] for layer in LAYERS}


# ---------------------------------------------------------------------------------------
# What the shipped build actually loaded.
#
# `artifacts` are ids in data/registry/source_artifacts.yaml. `evidence` is the repository
# record that shows the build used them, and it is checked to exist. `contributes` is the one
# sentence the sources page prints; it says what this source gives the reader, in the
# reader's terms, not in the pipeline's.
# ---------------------------------------------------------------------------------------
CONTRIBUTIONS: Final[list[dict[str, Any]]] = [
    # --- primary text ------------------------------------------------------------------
    {
        "layer": "primary-text",
        "vedas": ["RV"],
        "artifacts": ["GRETIL.RV.AUFRECHT.TEI.2019"],
        "evidence": "data/canonical/rigveda_full_v1/source_artifacts.jsonl",
        "contributes": (
            "All 10,552 Rigvedic mantras, in romanised Sanskrit with the Vedic accents "
            "carried as combining marks."
        ),
    },
    {
        "layer": "primary-text",
        "vedas": ["AV"],
        "artifacts": [
            "GRETIL.AV.SAUNAKA.ACCENTED.HTML",
            "GRETIL.AV.SAUNAKA.UNACCENTED.HTML",
        ],
        "evidence": "data/canonical/atharvaveda_saunaka_digital_working_v1/source_artifacts.jsonl",
        "contributes": (
            "The 5,839 mantras of the Saunaka Atharvaveda, as an accented text with an "
            "unaccented second witness read beside it."
        ),
    },
    {
        "layer": "primary-text",
        "vedas": ["SV", "YV"],
        "artifacts": [
            "WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI",
            "WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI",
        ],
        "evidence": "data/canonical/samaveda_arcika_v1/source_artifacts.jsonl",
        "contributes": (
            "The Samavedic arcika and the whole Vajasaneyi Samhita, in Devanagari. These "
            "are the two collections this site sets in Devanagari rather than in "
            "transliteration, because that is the script they were carried in."
        ),
    },
    # --- translations ------------------------------------------------------------------
    {
        "layer": "translation",
        "vedas": ["RV"],
        "artifacts": ["GRIFFITH.RV.1896.WIKISOURCE"],
        "evidence": "data/canonical/rigveda_full_v1/source_artifacts.jsonl",
        "contributes": "The English of 10,502 of the 10,552 Rigvedic verses.",
    },
    {
        "layer": "translation",
        "vedas": ["YV"],
        "artifacts": ["GRIFFITH.YV.1899.SACREDTEXTS"],
        "evidence": "data/staged/yajurveda_translation_stage.json",
        "contributes": "The English of 1,903 of the 1,975 verses of the White Yajurveda.",
    },
    {
        "layer": "translation",
        "vedas": ["AV"],
        "artifacts": ["VEDAWEB.AVS.WHITNEY_LANMAN_1905.PLAINTEXT.L2"],
        "evidence": "data/staged/atharvaveda_translation_stage_full_v1.json",
        "contributes": (
            "The English of 4,878 of the 5,839 Atharvavedic verses, in Whitney's "
            "deliberately literal rendering."
        ),
    },
    # The four translation sources the bulk integration round added. Declared with
    # `source_ids` and no artifacts because they are pinned web captures and a disk
    # snapshot rather than the checksummed per-file artifacts source_artifacts.yaml
    # records; the per-page sha256 for each lives in the proofs file named as evidence.
    {
        "layer": "translation",
        "vedas": ["AV"],
        "artifacts": [],
        "source_ids": ["IA_WAYBACK_GRIFFITH_AV_1895"],
        "rights_status": "PUBLIC_DOMAIN",
        "evidence": "data/staging/translation/proofs/source_pages.json",
        "contributes": (
            "The English of 871 further Atharvavedic verses, almost all of kanda 20, which "
            "Whitney excluded from his translation because it is largely Rigvedic "
            "redaction. 34 of them are one rendering printed across a pair of verses. A "
            "further 18 verses from this source are in Latin, not English: Griffith put "
            "the passages he judged too explicit for an English readership into Latin, and "
            "those are his real published text rather than a translation into English."
        ),
    },
    {
        "layer": "translation",
        "vedas": ["RV"],
        "artifacts": [],
        "source_ids": ["IA_WAYBACK_GRIFFITH_RV_1896"],
        "rights_status": "PUBLIC_DOMAIN",
        "evidence": "data/staging/translation/integration/translation_bulk_import_receipt.json",
        "contributes": (
            "The English of 7 Rigvedic verses the Wikisource transcription of the same "
            "translation leaves out, and 6 more in Griffith's Latin rather than English."
        ),
    },
    {
        "layer": "translation",
        "vedas": ["YV"],
        "artifacts": [],
        "source_ids": ["SACRED_TEXTS_WYV_SNAPSHOT_2026_09_07"],
        "rights_status": "PUBLIC_DOMAIN",
        "evidence": "data/staging/translation/integration/translation_bulk_import_receipt.json",
        "contributes": (
            "The English of 36 Yajurvedic verses whose printed labels the shipped alignment "
            "had misread, each one re-located against the printed page and verified "
            "independently. Three further verses were located the same way and are withheld "
            "by owner decision rather than shown."
        ),
    },
    {
        "layer": "translation",
        "vedas": ["SV", "AV"],
        "artifacts": [],
        "source_ids": ["VEDAGRAPH_CANONICAL_RV_GRIFFITH"],
        "rights_status": "PUBLIC_DOMAIN",
        "evidence": "data/staging/translation/integration/translation_bulk_import_receipt.json",
        "contributes": (
            "Griffith's Rigvedic English shown beside 173 Samavedic and 21 Atharvavedic "
            "verses whose Sanskrit is verified character-identical to the Rigvedic verse he "
            "was translating. Each is disclosed as a reused rendering and names the verse it "
            "came from. None of them counts as a translation of its own corpus: the Samaveda "
            "still has no released translation of its own, and this is the only English that "
            "reaches it."
        ),
    },
    # --- traditional apparatus ----------------------------------------------------------
    {
        "layer": "traditional-apparatus",
        "vedas": ["RV"],
        "artifacts": [f"WSC2023.RV.ANUKRAMANI.M{index:02d}" for index in range(1, 11)],
        "evidence": "data/registry/rishis.yaml",
        "contributes": (
            "The Anukramani for all ten mandalas: the seer, the deity and the metre "
            "traditionally given for each hymn. This is the only Veda here for which that "
            "index is held, and it is the reason deity ascription figures are Rigvedic."
        ),
    },
    {
        "layer": "traditional-apparatus",
        "vedas": ["AV"],
        "artifacts": ["WIKISOURCE.AV.WHITNEY.ANUKRAMANI.HEADERS"],
        "evidence": "data/registry/rishis_av.yaml",
        "contributes": (
            "The Atharvavedic index, kept in its own namespace. Its seer names are not "
            "resolved against the Rigvedic register, because the two indices spell the "
            "same tradition differently and merging them would assert an identity nobody "
            "established."
        ),
    },
    {
        "layer": "traditional-apparatus",
        "vedas": ["YV"],
        "artifacts": ["WIKISOURCE_SA.YV.VSM.RISHISUCI"],
        "evidence": "data/registry/rishis_yv.yaml",
        "contributes": "The Rsisuci, the Yajurvedic index of seers, likewise kept apart.",
    },
    # --- recitation ---------------------------------------------------------------------
    {
        "layer": "recitation",
        "vedas": ["RV", "YV", "AV"],
        "artifacts": [],
        "source_ids": ["VEDSEARCH"],
        "rights_status": "UNKNOWN",
        "evidence": "data/product/audio_catalog.jsonl",
        # The count is read from the catalogue at build time, not written here. It was
        # "16,834" as a literal and stayed 16,834 through the admission of 946 further
        # recordings, because prose is the one place a figure has nothing checking it.
        "contributes": (
            "{recitation_count} verse recitations, one file per verse, streamed from the "
            "source rather than copied. No Samavedic recitation is catalogued, which is "
            "the gap this layer most obviously has."
        ),
    },
    # --- comparison ---------------------------------------------------------------------
    {
        "layer": "comparison",
        "vedas": ["RV", "AV"],
        "artifacts": [
            "VEDAWEB.RV.CORPUS.TEI.D3EB8AF",
            *[f"VEDAWEB.RV.BOOK{index:02d}.TEI.D3EB8AF" for index in range(1, 11)],
            "VEDAWEB.AVS.SANSKRIT.TITUS.PLAINTEXT",
        ],
        "evidence": "data/canonical/rigveda_full_v1/source_artifacts.jsonl",
        "contributes": (
            "A second electronic witness to the Rigveda, read against the first verse by "
            "verse. Where the two disagreed the difference was recorded rather than "
            "silently resolved."
        ),
    },
    {
        "layer": "comparison",
        "vedas": ["RV"],
        "artifacts": ["VHP.RV.SHAKALA.MANDALA1.WEB"],
        "evidence": "data/canonical/rigveda_full_v1/source_artifacts.jsonl",
        "contributes": (
            "The Government of India's portal, consulted to check the recension and the "
            "hymn structure of the first mandala. Its material is not reproduced here."
        ),
    },
]


def _load_yaml(name: str) -> dict[str, Any]:
    with (REGISTRY / name).open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = yaml.safe_load(handle)
    return loaded


def _jsonable(value: Any) -> Any:
    """Registry dates are ``datetime.date``; everything else is already JSON."""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _canonical_corpus_dirs(works: list[dict[str, Any]]) -> dict[str, str]:
    """Which canonical build each work was loaded from, per the registry's own rights line."""
    found: dict[str, str] = {}
    for work in works:
        match = CANONICAL_PATH_IN_RIGHTS.search(work.get("rights") or "")
        if not match:
            raise ProvenanceError(
                f"{work['work_id']} does not name a canonical manifest in its rights line, "
                "so which build shipped it cannot be established from the registry."
            )
        corpus = match.group(1)
        if not (CANONICAL / corpus / "manifest.json").exists():
            raise ProvenanceError(
                f"{work['work_id']} names data/canonical/{corpus}, which is absent."
            )
        found[work["work_id"]] = corpus
    return found


def _refuse_undeclared_translation_sources(declared_source_ids: set[str]) -> None:
    """Refuse if the graph serves a translation from a source this page does not name.

    The check above covers the four canonical build manifests, and a translation written
    straight to the graph is not in any of them. That gap shipped once: the bulk
    integration round added 1,132 renderings under four new ``source_id`` values, the
    manifests knew nothing about them, this script wrote a clean page, and a reader could
    not resolve where a sixth of the Atharvavedic English had come from. The docstring
    already promised that an invisible omission is worse than no sources page; this makes
    the promise cover the surface the omission actually happened on.

    Skipped, loudly, when no graph is reachable -- this script is meant to run without one
    -- because a check that silently passes when it cannot look is the defect it guards
    against.
    """
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("provenance: neo4j driver absent; translation-source coverage NOT checked")
        return
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    auth = (
        os.environ.get("NEO4J_USER", "neo4j"),
        os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
    )
    try:
        driver = GraphDatabase.driver(uri, auth=auth)
        with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as session:
            live = {
                str(record["source_id"]): int(record["n"])
                for record in session.run(
                    "MATCH (:Mantra)-[:HAS_TRANSLATION]->(t:Translation) "
                    "WHERE t.source_id IS NOT NULL "
                    "RETURN t.source_id AS source_id, count(*) AS n"
                )
            }
        driver.close()
    except Exception as error:
        print(
            f"provenance: graph unreachable ({error.__class__.__name__}); "
            "translation-source coverage NOT checked"
        )
        return
    missing = {sid: n for sid, n in sorted(live.items()) if sid not in declared_source_ids}
    if missing:
        raise ProvenanceError(
            "The graph serves translations from sources this page does not name, so a "
            "reader could not resolve where they came from: "
            + ", ".join(f"{sid} ({n} translations)" for sid, n in missing.items())
        )
    print(
        f"provenance: all {len(live)} translation source_ids in the graph are declared "
        f"({sum(live.values()):,} translations)"
    )


def _shipped_artifact_ids(corpus_dirs: Iterable[str]) -> set[str]:
    """Every artifact id the four shipped canonical builds recorded."""
    ids: set[str] = set()
    for corpus in corpus_dirs:
        path = CANONICAL / corpus / "source_artifacts.jsonl"
        if not path.exists():
            raise ProvenanceError(f"data/canonical/{corpus} has no source_artifacts.jsonl.")
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    ids.add(json.loads(line)["artifact_id"])
    return ids


ARTIFACT_FIELDS: Final = (
    "artifact_id",
    "title",
    "edition_title",
    "source_edition",
    "editors",
    "electronic_editors",
    "contributors",
    "publication_date",
    "retrieval_date",
    "format",
    "language",
    "recension",
    "rights_status",
    "license_url",
    "url",
    "work_id",
)


def _rights_of(artifacts: list[dict[str, Any]], contribution: dict[str, Any]) -> list[str]:
    """The rights under which *these files* are held, not the rights of the site they sit on.

    The two differ and the difference matters. ``sources.yaml`` records GRETIL as UNKNOWN and
    says why in as many words: do not infer a corpus-wide licence from a site being reachable.
    The Rigvedic file GRETIL serves carries CC BY-NC-SA 4.0 in its own TEI header and the
    Atharvavedic ones carry no grant at all, so a page that printed the site's UNKNOWN beside
    both would be strictly less true than the registry it was built from.
    """
    if artifacts:
        return sorted(
            {artifact["rights_status"] for artifact in artifacts if artifact["rights_status"]}
        )
    declared = contribution.get("rights_status")
    if not declared:
        raise ProvenanceError(
            f"{contribution['layer']} contribution has no artifacts and declares no "
            "rights_status, so its terms would be blank rather than unknown."
        )
    return [declared]


def build() -> dict[str, Any]:
    sources_registry = _load_yaml("sources.yaml")["sources"]
    artifacts_registry = _load_yaml("source_artifacts.yaml")["source_artifacts"]
    works_registry = _load_yaml("works.yaml")["works"]

    sources_by_id = {source["source_id"]: source for source in sources_registry}
    artifacts_by_id = {artifact["artifact_id"]: artifact for artifact in artifacts_registry}

    corpus_by_work = _canonical_corpus_dirs(works_registry)
    shipped = _shipped_artifact_ids(corpus_by_work.values())

    declared: set[str] = set()
    entries: list[dict[str, Any]] = []

    for contribution in CONTRIBUTIONS:
        if contribution["layer"] not in LAYER_IDS:
            raise ProvenanceError(f"Unknown layer {contribution['layer']!r}.")

        evidence = ROOT / contribution["evidence"]
        if not evidence.exists():
            raise ProvenanceError(
                f"{contribution['evidence']} is declared as evidence and does not exist."
            )

        artifacts: list[dict[str, Any]] = []
        source_ids: set[str] = set(contribution.get("source_ids", []))
        for artifact_id in contribution["artifacts"]:
            artifact = artifacts_by_id.get(artifact_id)
            if artifact is None:
                raise ProvenanceError(
                    f"{artifact_id} is declared as shipped and is not in source_artifacts.yaml."
                )
            declared.add(artifact_id)
            source_ids.add(artifact["source_id"])
            artifacts.append(_jsonable({field: artifact.get(field) for field in ARTIFACT_FIELDS}))

        for source_id in sorted(source_ids):
            source = sources_by_id.get(source_id)
            if source is None:
                raise ProvenanceError(f"{source_id} is not in sources.yaml.")
            rights = source.get("rights") or {}
            mine = [
                artifact
                for artifact in artifacts
                if artifacts_by_id[artifact["artifact_id"]]["source_id"] == source_id
            ]
            entries.append(
                {
                    "layer": contribution["layer"],
                    "source_id": source_id,
                    "name": source["name"],
                    "organization": source.get("organization"),
                    "url": source.get("url"),
                    "authority_tier": source.get("authority_tier"),
                    "rights_status": _rights_of(mine, contribution),
                    "site_rights_status": rights.get("status"),
                    "rights_url": rights.get("license_url"),
                    "vedas": contribution["vedas"],
                    "contributes": contribution["contributes"].format(
                        **_measured_figures()
                    ),
                    "evidence": contribution["evidence"],
                    "artifacts": mine,
                }
            )

    unclassified = sorted(shipped - declared)
    if unclassified:
        raise ProvenanceError(
            "These artifacts are recorded in a shipped canonical build and no contribution "
            "declares them, so the sources page would omit them silently: "
            + ", ".join(unclassified)
        )

    _refuse_undeclared_translation_sources({entry["source_id"] for entry in entries})

    works = [
        {
            "work_id": work["work_id"],
            "veda": VEDA_BY_WORK[work["work_id"]],
            "work_name": work["work_name"],
            "abbreviation": work["abbreviation"],
            "recension": work["recension"],
            "hierarchy": work["hierarchy"],
            "scope": work["scope"],
            "completeness": work["completeness"],
            "excluded_corpora": work["excluded_corpora"],
            "canonical_build": corpus_by_work[work["work_id"]],
        }
        for work in sorted(works_registry, key=lambda row: row["work_id"])
    ]

    return {
        "generator": "scripts/build_frontend_provenance.py",
        "inputs": [
            "data/registry/sources.yaml",
            "data/registry/source_artifacts.yaml",
            "data/registry/works.yaml",
        ],
        "layers": LAYERS,
        "works": works,
        "entries": entries,
        "totals": {
            "sources": len({entry["source_id"] for entry in entries}),
            "artifacts": len(declared),
            "registered_sources": len(sources_registry),
            "registered_artifacts": len(artifacts_registry),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed JSON matches the registries. Writes nothing.",
    )
    args = parser.parse_args(argv)

    try:
        payload = build()
    except ProvenanceError as error:
        print(f"provenance: {error}", file=sys.stderr)
        return 2

    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n"

    if args.check:
        if not OUTPUT.exists():
            print(f"provenance: {OUTPUT} has not been generated.", file=sys.stderr)
            return 1
        if OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"provenance: {OUTPUT} is stale. Run scripts/build_frontend_provenance.py.",
                file=sys.stderr,
            )
            return 1
        print(f"provenance: up to date ({payload['totals']['sources']} sources).")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        f"provenance: wrote {OUTPUT.relative_to(ROOT)} "
        f"({payload['totals']['sources']} sources, {payload['totals']['artifacts']} artifacts)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
