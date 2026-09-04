"""Assemble the full Rigveda Mandala 1 build configuration.

Combines the fixed sanskrit/discovery/metadata/parallel-sanskrit source pins (reused
verbatim from the reviewed 5-Sukta sample) with the 191-Sukta Wikisource translation
pins written by ``scripts/fetch_wikisource_mandala1.py``. Writes
``data/builds/rv_mandala_1_full_v1.yaml``. Contains no corpus text, only source pins.
"""

from __future__ import annotations

from pathlib import Path

import yaml

WIKISOURCE_FRAGMENT = Path("data/derived/wikisource_mandala1_sources.yaml")
OUTPUT = Path("data/builds/rv_mandala_1_full_v1.yaml")

FIXED_SOURCES: list[dict[str, object]] = [
    {
        "source_id": "GRETIL",
        "role": "sanskrit",
        "scope": "RV.1",
        "source_artifact_id": "GRETIL.RV.AUFRECHT.TEI.2019",
        "snapshot_path": (
            "data/raw/gretil/2026-09-04/"
            "14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd.xml"
        ),
        "snapshot_id": "GRETIL:14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd",
        "snapshot_sha256": "14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd",
        "parser_version": "gretil-rigveda-tei-v2",
    },
    {
        "source_id": "VEDAWEB",
        "role": "sanskrit_parallel",
        "scope": "RV.1",
        "source_artifact_id": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
        "snapshot_path": (
            "data/raw/vedaweb/2026-09-04/"
            "c5c18d89a415ea16917f0f63616ee9fff7e32c4828b67f1e7647d2d023bc984c.tei"
        ),
        "snapshot_id": "VEDAWEB:c5c18d89a415ea16917f0f63616ee9fff7e32c4828b67f1e7647d2d023bc984c",
        "snapshot_sha256": "c5c18d89a415ea16917f0f63616ee9fff7e32c4828b67f1e7647d2d023bc984c",
        "parser_version": "vedaweb-rigveda-tei-v1",
    },
    {
        "source_id": "VHP",
        "role": "discovery",
        "scope": "RV.1",
        "source_artifact_id": "VHP.RV.SHAKALA.MANDALA1.WEB",
        "snapshot_path": (
            "data/raw/vhp/2026-09-04/"
            "3a4c8eae800f90e8dd86a48b46bbdbe1b6b2995eeaed67575dd21941a202c633.html"
        ),
        "snapshot_id": "VHP:3a4c8eae800f90e8dd86a48b46bbdbe1b6b2995eeaed67575dd21941a202c633",
        "snapshot_sha256": "3a4c8eae800f90e8dd86a48b46bbdbe1b6b2995eeaed67575dd21941a202c633",
        "parser_version": "vhp-rigveda-v2",
    },
]

# VHP traditional-metadata coverage stays exactly the sample's 5 already-snapshotted
# Suktas (task: no new bulk VHP ingestion this session). Reused verbatim from
# data/builds/rv_mandala_1.yaml.
VHP_METADATA_SOURCES: list[dict[str, object]] = [
    {
        "source_id": "VHP",
        "role": "metadata",
        "scope": "RV.1.1",
        "source_artifact_id": "VHP.RV.SHAKALA.MANDALA1.WEB",
        "snapshot_path": (
            "data/raw/vhp/2026-09-04/"
            "3a4c8eae800f90e8dd86a48b46bbdbe1b6b2995eeaed67575dd21941a202c633.html"
        ),
        "snapshot_id": "VHP:3a4c8eae800f90e8dd86a48b46bbdbe1b6b2995eeaed67575dd21941a202c633",
        "snapshot_sha256": "3a4c8eae800f90e8dd86a48b46bbdbe1b6b2995eeaed67575dd21941a202c633",
        "parser_version": "vhp-rigveda-v2",
    },
    {
        "source_id": "VHP",
        "role": "metadata",
        "scope": "RV.1.22",
        "source_artifact_id": "VHP.RV.SHAKALA.MANDALA1.WEB",
        "snapshot_path": (
            "data/raw/vhp/2026-09-04/"
            "943d5a5b3cdf87319f1b634cc49925e119c6ea5334fb6b1a73a1975cd0837937.html"
        ),
        "snapshot_id": "VHP:943d5a5b3cdf87319f1b634cc49925e119c6ea5334fb6b1a73a1975cd0837937",
        "snapshot_sha256": "943d5a5b3cdf87319f1b634cc49925e119c6ea5334fb6b1a73a1975cd0837937",
        "parser_version": "vhp-rigveda-v2",
    },
    {
        "source_id": "VHP",
        "role": "metadata",
        "scope": "RV.1.50",
        "source_artifact_id": "VHP.RV.SHAKALA.MANDALA1.WEB",
        "snapshot_path": (
            "data/raw/vhp/2026-09-04/"
            "fb49e07090c27445149d9e915adef719c0f8a9e2d22c44fdf6d69cb7752567e2.html"
        ),
        "snapshot_id": "VHP:fb49e07090c27445149d9e915adef719c0f8a9e2d22c44fdf6d69cb7752567e2",
        "snapshot_sha256": "fb49e07090c27445149d9e915adef719c0f8a9e2d22c44fdf6d69cb7752567e2",
        "parser_version": "vhp-rigveda-v2",
    },
    {
        "source_id": "VHP",
        "role": "metadata",
        "scope": "RV.1.164",
        "source_artifact_id": "VHP.RV.SHAKALA.MANDALA1.WEB",
        "snapshot_path": (
            "data/raw/vhp/2026-09-04/"
            "5eee5aa6c4a162425e6afda8b6952ddc68a762a9245dc2cdf7d05b5382aaa8c2.html"
        ),
        "snapshot_id": "VHP:5eee5aa6c4a162425e6afda8b6952ddc68a762a9245dc2cdf7d05b5382aaa8c2",
        "snapshot_sha256": "5eee5aa6c4a162425e6afda8b6952ddc68a762a9245dc2cdf7d05b5382aaa8c2",
        "parser_version": "vhp-rigveda-v2",
    },
    {
        "source_id": "VHP",
        "role": "metadata",
        "scope": "RV.1.191",
        "source_artifact_id": "VHP.RV.SHAKALA.MANDALA1.WEB",
        "snapshot_path": (
            "data/raw/vhp/2026-09-04/"
            "ea578e56195ea1b1acb7635338185ab089b474d4597b9a272d602c11459dbee9.html"
        ),
        "snapshot_id": "VHP:ea578e56195ea1b1acb7635338185ab089b474d4597b9a272d602c11459dbee9",
        "snapshot_sha256": "ea578e56195ea1b1acb7635338185ab089b474d4597b9a272d602c11459dbee9",
        "parser_version": "vhp-rigveda-v2",
    },
]


def main() -> None:
    fragment = yaml.safe_load(WIKISOURCE_FRAGMENT.read_text(encoding="utf-8"))
    wikisource_sources = fragment["sources"]
    all_sources = [*FIXED_SOURCES, *VHP_METADATA_SOURCES, *wikisource_sources]

    config = {
        "config_version": "1.0.0",
        "dataset_id": "rv_mandala_1_full_v1",
        "release_version": "1.0.0-rc1",
        "work_id": "VG:WORK:RV:SAK",
        "mandala": 1,
        "selected_suktas": list(range(1, 192)),
        "text_selection_policy": "ORIGINAL",
        "primary_sanskrit": {
            "artifact": "GRETIL.RV.AUFRECHT.TEI.2019",
            "text_version": "GRETIL.RV.AUFRECHT",
            "role": "PRIMARY_TEXT",
            "selection_policy": "ORIGINAL",
        },
        "parallel_sanskrit": [
            {
                "artifact": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
                "text_version": "VEDAWEB.AUFRECHT",
                "role": "PARALLEL_TEXT",
            },
        ],
        # Documented but not built into canonical output this session (see
        # RIGVEDA_BASE_EDITION.md): the remaining VedaWeb layers keep their roles on
        # record without adding staging/parsing cost to the full-Mandala build.
        "candidate_text_versions": [
            {
                "artifact": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
                "text_version": "VEDAWEB.EICHLER",
                "role": "PARALLEL_TEXT",
            },
            {
                "artifact": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
                "text_version": "VEDAWEB.VNH",
                "role": "METRICALLY_RESTORED",
            },
            {
                "artifact": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
                "text_version": "VEDAWEB.PADAPATHA",
                "role": "PADAPATHA",
            },
            {
                "artifact": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
                "text_version": "VEDAWEB.LUBOTSKY",
                "role": "COMPARISON_ONLY",
            },
            {
                "artifact": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
                "text_version": "VEDAWEB.ZURICH",
                "role": "LINGUISTIC_ANNOTATION",
            },
        ],
        "sources": all_sources,
        "translation_sources": ["WIKISOURCE_GRIFFITH_RV"],
        "metadata_sources": ["VHP"],
        "media_discovery_sources": ["VHP"],
        "reconciliation_policy_version": "rv-mandala-1-v1",
        "output_location": "data/canonical/rv_mandala_1_full_v1",
        "staging_location": "data/staged/rv_mandala_1_full_v1",
        "build_timestamp": "2026-09-04T00:00:00+05:30",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(f"Wrote {len(all_sources)} source entries to {OUTPUT}")


if __name__ == "__main__":
    main()
