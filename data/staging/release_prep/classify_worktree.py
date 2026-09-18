"""Classify every dirty and untracked path in the worktree, measured rather than guessed.

Release prep section C. The rule this is built around is that a file is only safe to delete
when something *tracked* still carries its identity, so "is its digest preserved elsewhere"
is computed and not asserted: every tracked JSON/TXT manifest in the repository is scanned
for each candidate's sha256 and for its repo-relative path, and the answer is recorded per
file with the manifest that holds it.

The six classes are the owner's:

``COMMIT_REQUIRED``
    Release-prep work that must enter git for the repository to be readable.
``GENERATED_TRACKED``
    A tracked artifact that a generator rewrote in this pass; the change is real output.
``LOCAL_EVIDENCE_KEEP_UNTRACKED``
    Evidence worth keeping on this machine, too large or too raw to version, whose identity
    a tracked manifest already pins.
``TEMPORARY_SAFE_TO_DELETE``
    Scratch whose evidence has a durable tracked replacement.
``SHOULD_BE_GITIGNORED``
    A reproducible local artifact that will keep reappearing until a rule names it.
``UNKNOWN_REQUIRES_OWNER``
    Anything this script cannot place. Never deleted, never staged.

Usage::

    python data/staging/release_prep/classify_worktree.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
from typing import Any, Final

ROOT: Final = pathlib.Path(__file__).resolve().parents[3]
OUT: Final = ROOT / "data" / "staging" / "release_prep" / "worktree_classification.json"

#: Files larger than this are not hashed for the digest search -- a 324 MB logical export is
#: never going to have its sha256 quoted in a manifest unless a .sha256 sidecar holds it, and
#: the sidecar is checked directly.
_HASH_CEILING_BYTES: Final = 64 * 1024 * 1024


def run(*args: str) -> str:
    return subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, check=True, encoding="utf-8"
    ).stdout


def dirty_paths() -> list[tuple[str, str]]:
    """``(porcelain status, repo-relative path)`` for everything git reports, files only."""
    out: list[tuple[str, str]] = []
    for line in run("git", "status", "--porcelain", "--untracked-files=all").splitlines():
        if not line.strip():
            continue
        status, path = line[:2], line[3:].strip().strip('"')
        if (ROOT / path).is_file():
            out.append((status, path))
    return out


def sha256_of(path: pathlib.Path) -> str | None:
    if path.stat().st_size > _HASH_CEILING_BYTES:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tracked_manifest_text() -> dict[str, str]:
    """Every tracked .json/.txt/.sha256 small enough to be a manifest, as text."""
    blobs: dict[str, str] = {}
    for rel in run("git", "ls-files").splitlines():
        if not rel.endswith((".json", ".txt", ".sha256", ".md", ".yaml")):
            continue
        candidate = ROOT / rel
        if not candidate.is_file() or candidate.stat().st_size > 8 * 1024 * 1024:
            continue
        try:
            blobs[rel] = candidate.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    return blobs


def preserved_by(
    rel: str, digest: str | None, blobs: dict[str, str]
) -> dict[str, Any]:
    """Which tracked artifacts carry this file's digest, or name its path."""
    by_digest = sorted(name for name, text in blobs.items() if digest and digest in text)
    # The full repo-relative path only, in both separator styles. A basename match was
    # tried first and had to be removed: "openapi.json" appears in a README, a frontend
    # audit and two source registries that have nothing to do with the dumped schema, and
    # it would have licensed deleting a file on the strength of an unrelated mention.
    # A durability claim that matches the wrong thing is worse than no claim.
    windows = rel.replace("/", "\\")
    by_path = sorted(
        name for name, text in blobs.items() if name != rel and (rel in text or windows in text)
    )
    sidecar = ROOT / (rel + ".sha256")
    sidecar_tracked = sidecar.is_file() and (rel + ".sha256") in blobs
    regenerator = REGENERATED_IDENTICALLY_BY.get(rel)
    return {
        "digest_recorded_in_tracked_artifacts": by_digest[:6],
        "path_named_in_tracked_artifacts": by_path[:6],
        "tracked_sha256_sidecar": (rel + ".sha256") if sidecar_tracked else None,
        "regenerated_identically_by": regenerator,
        "evidence_has_a_durable_tracked_replacement": bool(
            by_digest or sidecar_tracked or by_path or regenerator
        ),
    }


#: Paths whose durable replacement is a *generator* rather than a stored digest, recorded
#: only after the regeneration was actually run and compared. A claim that something is
#: reproducible is not evidence that it reproduces; these were checked.
REGENERATED_IDENTICALLY_BY: Final[dict[str, str]] = {
    "data/staging/release_blocker_r5/openapi.json": (
        "vedagraph.api.app.create_app().openapi() -- re-emitted 2026-09-18 and compared: "
        "386,344 bytes both sides, 46 paths both sides, sha256 5a464b183e940ab5 identical. "
        "The generator is tracked, so the dump carries no information the repository lacks."
    ),
}


#: (path predicate, class, phase, reason). First match wins, so order is the ruling.
RULES: Final[tuple[tuple[str, str, str, str], ...]] = (
    (
        "data/staging/final_stabilization/neo4j_backup_20260917/",
        "SHOULD_BE_GITIGNORED",
        "final stabilization (2026-09-17)",
        "A Neo4j dump taken before a canonical mutation. .gitignore already carries exactly "
        "this rule for data/backup/*.dump, with the reason written out: the bytes are "
        "reproducible from the graph they came from and what a later reader needs is the "
        "IDENTITY of the backup a migration was gated on, not the payload. This copy sits "
        "outside the directory the existing rule covers, so it is still offered to git on "
        "every status.",
    ),
    (
        "data/staging/release_blocker_r3/backup/MANIFEST.json",
        "COMMIT_REQUIRED",
        "release blocker closure R3",
        "1 KB, and the only versioned identity the 472 MB R3 backup would have. R4 and R5 "
        "each track their backup's MANIFEST.json and two .sha256 sidecars; R3 tracks "
        "nothing and has no sidecars at all, so ignoring the directory wholesale would "
        "destroy the digest in exactly the event it exists to detect. This manifest already "
        "carries both payload sha256 values inline, so tracking it alone completes the "
        "arrangement without needing sidecars.",
    ),
    (
        "data/staging/release_blocker_r3/backup/",
        "SHOULD_BE_GITIGNORED",
        "release blocker closure R3",
        "A logical export -- nodes.jsonl + relationships.jsonl -- of the same kind .gitignore "
        "already excludes for release_blocker_r4, and for the same stated reason. Neo4j runs "
        "in a container on 5.26-community where `neo4j-admin database dump` needs the "
        "database stopped, so the pre-migration backup is taken logically instead.",
    ),
    (
        "data/staging/release_blocker_r5/backup/",
        "SHOULD_BE_GITIGNORED",
        "release blocker closure R5",
        "The R5 half of the same pair. Its MANIFEST.json and both .sha256 sidecars are "
        "already tracked and were committed with R5, so the backup's identity is versioned "
        "and only the 486 MB payload is not -- which is precisely the arrangement the R4 "
        "rule describes.",
    ),
    (
        "data/staging/release_blocker_r5/openapi.json",
        "TEMPORARY_SAFE_TO_DELETE",
        "release blocker closure R5",
        "A dump of the live FastAPI schema, taken to check a surface during R5. The brief "
        "names temporary OpenAPI dumps as a do-not-commit class, and it is regenerated in "
        "one command from the running app.",
    ),
    (
        "data/staging/final_closure_sprint/",
        "LOCAL_EVIDENCE_KEEP_UNTRACKED",
        "final closure sprint (agents 1-8)",
        "Per-agent intermediate output and the ad-hoc probe scripts that produced it. The "
        "sprint's durable artifacts -- 111 of them, including every agent's manifest.json "
        "with per-file sha256, the closure reports and the registry outcomes -- are already "
        "tracked and committed. Committing the intermediates as well would add them to the "
        "repository only because they exist.",
    ),
    (
        "data/staging/release_prep/",
        "COMMIT_REQUIRED",
        "release prep",
        "This pass's own generators and receipts. Small, durable, and cited by the release-"
        "prep report and by OWNER_DECISIONS.md section 40/41.",
    ),
    (
        "data/staging/wave4/registry_closure_audit.json",
        "GENERATED_TRACKED",
        "wave 4 phase 7, regenerated at release prep",
        "The registry audit's own report, rewritten by this pass's --write run. Tracked "
        "already; the change is the two Samaveda-music rulings and the new content digest.",
    ),
    (
        "data/gap_registry.json",
        "GENERATED_TRACKED",
        "release prep",
        "The gap registry, rewritten by scripts/wave4_registry_closure_audit.py --write to "
        "record the two owner decisions. This is the registry consequence the brief asks be "
        "committed.",
    ),
    (
        "scripts/wave4_registry_closure_audit.py",
        "COMMIT_REQUIRED",
        "release prep",
        "The ruling table is the audit. Both Samaveda-music rulings were restated here "
        "before being measured, which is the order this script is built to enforce.",
    ),
    (
        "docs/reports/data-completeness/OWNER_DECISIONS.md",
        "COMMIT_REQUIRED",
        "release prep",
        "Owner round eight, sections 40 and 41. A CLOSED_SCOPE_DECISION requires a citation "
        "naming where the decision is written down, and this is that file.",
    ),
    (
        "scripts/review_audio_sample.py",
        "COMMIT_REQUIRED",
        "release prep",
        "The owner's audio sample reviewer.",
    ),
    (
        "scripts/audio_review_harness.py",
        "COMMIT_REQUIRED",
        "release prep",
        "The 1,021-row browser harness, fixed. review_id is not unique in the queue -- one "
        "id covers four Commons recordings -- and the harness keyed verdicts on it, so one "
        "keystroke would have marked three recordings AUDIBLY_VERIFIED that nobody played. "
        "The recording is now half of the row identity.",
    ),
    (
        "src/vedagraph/llm/",
        "COMMIT_REQUIRED",
        "release prep",
        "Credential slots, quota failover and secret redaction for the Ask benchmark.",
    ),
    (
        "tests/",
        "COMMIT_REQUIRED",
        "release prep",
        "Tests for this pass's additions.",
    ),
    (
        "scripts/run_ask_benchmark.py",
        "COMMIT_REQUIRED",
        "release prep",
        "The benchmark runner gains the credential-slot report and the failover wiring.",
    ),
    (
        ".gitignore",
        "COMMIT_REQUIRED",
        "release prep",
        "The three backup rules proposed by this classification.",
    ),
    (
        "data/manual/audio_review/",
        "LOCAL_EVIDENCE_KEEP_UNTRACKED",
        "release prep",
        "Human review decisions. The owner is the only author, no agent may write here, and "
        "the repository's precedent for a human audio verdict is a tracked prose record "
        "(docs/reports/PRODUCT_V1_AUDIO_LISTENING_CHECK.md) written from the log rather than "
        "the raw log itself.",
    ),
)


def classify(rel: str) -> tuple[str, str, str]:
    for prefix, klass, phase, reason in RULES:
        if rel == prefix or rel.startswith(prefix):
            return klass, phase, reason
    return (
        "UNKNOWN_REQUIRES_OWNER",
        "unknown",
        "No rule in this table places it. Left on disk untouched and reported.",
    )


def main() -> int:
    blobs = tracked_manifest_text()
    tracked = set(run("git", "ls-files").splitlines())

    records: list[dict[str, Any]] = []
    for status, rel in dirty_paths():
        path = ROOT / rel
        size = path.stat().st_size
        digest = sha256_of(path)
        klass, phase, reason = classify(rel)
        records.append(
            {
                "path": rel,
                "size_bytes": size,
                "git_status": status,
                "tracked": rel in tracked,
                "originating_phase": phase,
                "classification": klass,
                "why": reason,
                "sha256": digest,
                **preserved_by(rel, digest, blobs),
            }
        )

    records.sort(key=lambda r: (r["classification"], r["path"]))
    counts: dict[str, int] = {}
    bytes_by_class: dict[str, int] = {}
    for record in records:
        counts[record["classification"]] = counts.get(record["classification"], 0) + 1
        bytes_by_class[record["classification"]] = (
            bytes_by_class.get(record["classification"], 0) + record["size_bytes"]
        )

    unpreserved_deletions = [
        r["path"]
        for r in records
        if r["classification"] == "TEMPORARY_SAFE_TO_DELETE"
        and not r["evidence_has_a_durable_tracked_replacement"]
    ]

    payload = {
        "artifact": "RELEASE_PREP_WORKTREE_CLASSIFICATION",
        "head": run("git", "rev-parse", "HEAD").strip(),
        "branch": run("git", "rev-parse", "--abbrev-ref", "HEAD").strip(),
        "total_paths": len(records),
        "counts": counts,
        "bytes_by_class": bytes_by_class,
        "policy": {
            "commit": ["COMMIT_REQUIRED", "GENERATED_TRACKED"],
            "delete": [
                "TEMPORARY_SAFE_TO_DELETE, and only where "
                "evidence_has_a_durable_tracked_replacement is true"
            ],
            "ignore": ["SHOULD_BE_GITIGNORED"],
            "preserve_on_disk": ["LOCAL_EVIDENCE_KEEP_UNTRACKED", "UNKNOWN_REQUIRES_OWNER"],
            "never": ["git add -A", "git clean -fd", "git reset --hard"],
        },
        "proposed_gitignore_rules": [
            {
                "rule": "data/staging/final_stabilization/neo4j_backup_20260917/*.dump",
                "covers": 1,
                "bytes": 169799495,
                "precedent": ".gitignore data/backup/*.dump",
            },
            {
                "rule": "data/staging/release_blocker_r3/backup/*.jsonl",
                "covers": 2,
                "bytes": 494314964,
                "precedent": ".gitignore data/staging/release_blocker_r4/backup/*.jsonl",
            },
            {
                "rule": "data/staging/release_blocker_r5/backup/*.jsonl",
                "covers": 2,
                "bytes": 508649517,
                "precedent": ".gitignore data/staging/release_blocker_r4/backup/*.jsonl",
            },
        ],
        "deletions_without_a_durable_replacement": unpreserved_deletions,
        "paths": records,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print(f"  {len(records)} paths classified -> {OUT.relative_to(ROOT)}")
    for klass in sorted(counts):
        print(f"    {klass:32}{counts[klass]:>5}  {bytes_by_class[klass] / 1e6:>10.1f} MB")
    if unpreserved_deletions:
        print("\n  REFUSING to mark these deletable -- no tracked artifact preserves them:")
        for path in unpreserved_deletions:
            print(f"    {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
