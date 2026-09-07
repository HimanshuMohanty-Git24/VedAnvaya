"""Issue the execution-version v3.1 full-run freeze draft and its batch plan.

The v3 draft is left exactly where it is. A freeze pins file bytes, and the corrective
engineering session changed the extraction contract, so the v3 draft is now correctly
stale — that is what ``require new extraction version`` means. This writes a new draft
under a new run identity rather than editing the old one.

A draft is not authorization. The full run stays blocked until the bounded regression
under CODEX_DIRECT has been run and reviewed.
"""

from __future__ import annotations

import json
import platform
import re
from pathlib import Path

from vedagraph.semantic.full_run import Freeze, digest, file_hash, make_plan

RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-full-1.0.0-rc1"
MANIFESTS = Path("docs/manifests")
CORPUS = Path("data/canonical/rigveda_full_v1")

ROLES = {
    "corpus_manifest": "data/canonical/rigveda_full_v1/manifest.json",
    "traditional_manifest": "data/knowledge/rigveda_deterministic_v1/manifest.json",
    "lexical_manifest": "data/knowledge/rigveda_lexical_v1/manifest.json",
    "morphology": "data/knowledge/rigveda_lexical_v1/tokens.jsonl",
    "prompt": "prompts/semantic_extraction_v3.md",
    "schema": "schemas/semantic_extraction_v3.schema.json",
    "object_ontology": "src/vedagraph/semantic/object_ontology.py",
    "semantic_ontology": "src/vedagraph/semantic/ontology.py",
    "explicitness_policy": "src/vedagraph/semantic/object_ontology.py",
    "normalization_policy": "src/vedagraph/semantic/normalization.py",
    "packet_schema": "schemas/semantic_evidence_packet.schema.json",
    "packet_builder": "src/vedagraph/semantic/packet.py",
    "packet_model": "src/vedagraph/models/semantic.py",
    "object_model": "src/vedagraph/models/normalization.py",
    "validator": "src/vedagraph/semantic/v3.py",
    "runtime_lock": "pyproject.toml",
    "operations": "src/vedagraph/semantic/full_run.py",
    "execution_contract": "src/vedagraph/semantic/codex_direct.py",
    "evidence_validator": "src/vedagraph/semantic/evidence.py",
    "span_validator": "src/vedagraph/semantic/spans.py",
}


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    ids = sorted(
        key
        for line in (CORPUS / "passages.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
        for key in [json.loads(line)["canonical_key"]]
        if re.fullmatch(r"VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}", key)
    )
    roles = {name: Path(value).as_posix() for name, value in ROLES.items()}
    files = {
        path.as_posix(): file_hash(path)
        for directory in [
            CORPUS,
            Path("data/knowledge/rigveda_deterministic_v1"),
            Path("data/knowledge/rigveda_lexical_v1"),
        ]
        for path in directory.glob("*.json*")
    }
    files.update({value: file_hash(Path(value)) for value in roles.values()})
    for directory in [Path("src/vedagraph/semantic"), Path("data/registries")]:
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".yaml"}:
                files[path.as_posix()] = file_hash(path)
    freeze = Freeze(
        run_id=RUN_ID,
        files=files,
        roles=roles,
        passage_ids=ids,
        runtime_version=(
            f"Python {platform.python_version()}; Codex host build UNVERIFIED; BLOCKED draft"
        ),
    )
    freeze.verify(Path.cwd(), ids)
    plan = make_plan(RUN_ID, ids, digest(freeze.model_dump(mode="json")))
    write(
        MANIFESTS / "rigveda_semantic_execution_v3_1_freeze.draft.json",
        freeze.model_dump(mode="json"),
    )
    write(
        MANIFESTS / "rigveda_semantic_execution_v3_1_batch_plan.draft.json",
        plan.model_dump(mode="json"),
    )
    print(f"freeze hash {plan.freeze_hash}")
    print(f"plan hash {digest(plan.model_dump(mode='json'))}")
    print(f"batches {len(plan.batches)} of {plan.batch_size}; ids {len(ids)}")


if __name__ == "__main__":
    main()
