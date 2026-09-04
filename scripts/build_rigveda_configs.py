"""Generate version-controlled Mandala 2-10 and composed full-Rigveda configs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from vedagraph.config.registry import load_source_artifacts
from vedagraph.ingest.adapters.gretil import GRETILAdapter

BUILD_DIR = Path("data/builds")
GRETIL_PATH = Path(
    "data/raw/gretil/2026-09-04/"
    "14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd.xml"
)
GRETIL_SHA = "14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd"
BUILD_TIMESTAMP = "2026-09-04T00:00:00+05:30"


def _snapshot_path(checksum: str) -> Path:
    matches = [
        path
        for path in Path("data/raw").glob(f"**/{checksum}.*")
        if not path.name.endswith(".metadata.json")
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one snapshot for {checksum}, found {len(matches)}")
    return matches[0]


def _source(
    source_id: str,
    role: str,
    scope: str,
    artifact_id: str,
    snapshot_path: Path,
    checksum: str,
    parser_version: str,
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "role": role,
        "scope": scope,
        "source_artifact_id": artifact_id,
        "snapshot_path": snapshot_path.as_posix(),
        "snapshot_id": f"{source_id}:{checksum}",
        "snapshot_sha256": checksum,
        "parser_version": parser_version,
    }


def _config(mandala: int) -> dict[str, Any]:
    artifacts = {artifact.artifact_id: artifact for artifact in load_source_artifacts()}
    vedaweb_id = f"VEDAWEB.RV.BOOK{mandala:02d}.TEI.D3EB8AF"
    vedaweb = artifacts[vedaweb_id]
    if vedaweb.checksum_sha256 is None:
        raise ValueError(f"{vedaweb_id} has no checksum")
    discoveries = GRETILAdapter().discover_suktas(
        GRETIL_PATH, snapshot_id=f"GRETIL:{GRETIL_SHA}", mandala=mandala
    )
    selected_suktas = [item.sukta_number for item in discoveries]
    fragment_path = Path(f"data/derived/wikisource_mandala{mandala}_sources.yaml")
    fragment = yaml.safe_load(fragment_path.read_text(encoding="utf-8"))
    sources = [
        _source(
            "GRETIL",
            "sanskrit",
            f"RV.{mandala}",
            "GRETIL.RV.AUFRECHT.TEI.2019",
            GRETIL_PATH,
            GRETIL_SHA,
            "gretil-rigveda-tei-v2",
        ),
        _source(
            "VEDAWEB",
            "sanskrit_parallel",
            f"RV.{mandala}",
            vedaweb_id,
            _snapshot_path(vedaweb.checksum_sha256),
            vedaweb.checksum_sha256,
            "vedaweb-rigveda-tei-v1",
        ),
        *fragment["sources"],
    ]
    candidate_roles = {
        "EICHLER": "PARALLEL_TEXT",
        "VNH": "METRICALLY_RESTORED",
        "PADAPATHA": "PADAPATHA",
        "LUBOTSKY": "COMPARISON_ONLY",
        "ZURICH": "LINGUISTIC_ANNOTATION",
    }
    return {
        "config_version": "1.0.0",
        "dataset_id": f"rv_mandala_{mandala}_full_v1",
        "release_version": "1.0.0-rc1",
        "work_id": "VG:WORK:RV:SAK",
        "mandala": mandala,
        "selected_suktas": selected_suktas,
        "text_selection_policy": "ORIGINAL",
        "primary_sanskrit": {
            "artifact": "GRETIL.RV.AUFRECHT.TEI.2019",
            "text_version": "GRETIL.RV.AUFRECHT",
            "role": "PRIMARY_TEXT",
            "selection_policy": "ORIGINAL",
        },
        "parallel_sanskrit": [
            {
                "artifact": vedaweb_id,
                "text_version": "VEDAWEB.AUFRECHT",
                "role": "PARALLEL_TEXT",
            }
        ],
        "candidate_text_versions": [
            {
                "artifact": vedaweb_id,
                "text_version": f"VEDAWEB.{version}",
                "role": role,
            }
            for version, role in candidate_roles.items()
        ],
        "sources": sources,
        "translation_sources": ["WIKISOURCE_GRIFFITH_RV"],
        "metadata_sources": [],
        "media_discovery_sources": [],
        "reconciliation_policy_version": "rv-shakala-v1",
        "qa_policy_version": "rigveda-full-corpus-qa-v1",
        "rights_policy_version": "artifact-and-version-rights-v1",
        "media_policy_version": "external-reference-only-v1",
        "translation_alignment_policy_version": "conservative-source-numbered-v1",
        "output_location": f"data/canonical/rv_mandala_{mandala}_full_v1",
        "staging_location": f"data/staged/rv_mandala_{mandala}_full_v1",
        "build_timestamp": BUILD_TIMESTAMP,
    }


def _write_full_config() -> None:
    payload = {
        "config_version": "1.0.0",
        "dataset_id": "rigveda_full_v1",
        "release_version": "vedagraph-rigveda-shakala-1.0.0-rc1",
        "work_id": "VG:WORK:RV:SAK",
        "mandala_configs": [
            "data/builds/rv_mandala_1_full_v1.yaml",
            *(f"data/builds/rv_mandala_{mandala}_full_v1.yaml" for mandala in range(2, 11)),
        ],
        "expected_mandalas": 10,
        "expected_suktas": 1028,
        "expected_mantras": 10552,
        "reconciliation_policy_version": "rv-shakala-v1",
        "qa_policy_version": "rigveda-full-corpus-qa-v1",
        "output_location": "data/canonical/rigveda_full_v1",
        "build_timestamp": BUILD_TIMESTAMP,
    }
    path = BUILD_DIR / "rv_full_v1.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(f"Wrote {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mandala", type=int, choices=range(2, 11))
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not args.all and args.mandala is None:
        parser.error("choose --mandala N or --all")
    mandalas = range(2, 11) if args.all else [args.mandala]
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    for mandala in mandalas:
        if mandala is None:
            continue
        path = BUILD_DIR / f"rv_mandala_{mandala}_full_v1.yaml"
        path.write_text(yaml.safe_dump(_config(mandala), sort_keys=False), encoding="utf-8")
        print(f"Wrote {path}")
    if args.all:
        _write_full_config()


if __name__ == "__main__":
    main()
