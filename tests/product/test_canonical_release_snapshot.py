"""The released corpus is gitignored, so the manifest is the only thing that can notice.

``.gitignore`` line 17 excludes ``data/canonical/**``. Nothing about the shipped corpus is in
git history, which means a truncation, a partial rebuild or a stray export leaves no trace and
trips no diff. ``SV-UNTRACKED-RELEASE-01`` records the hazard;
:mod:`scripts.snapshot_canonical_release` answers it with a tracked per-file digest.

A manifest that cannot fail is not protection, so the decisive test here is the negative one:
:func:`test_perturbed_file_is_detected` builds a small tree, records it, changes one byte, and
requires the verifier to name that file. Without it, every other assertion in this file would
pass just as happily against a verifier that returned ``ok`` unconditionally -- which is how a
validator in this project once reported a clean run over rows it had silently skipped.

The clean-tree cases assert on the *real* release. They never write to ``data/canonical``:
the perturbation is always performed on a copy under ``tmp_path``.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "snapshot_canonical_release.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("snapshot_canonical_release", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


snapshot_canonical_release = _load_module()


@pytest.fixture(scope="module")
def manifest() -> dict:
    path = snapshot_canonical_release.MANIFEST_PATH
    assert path.is_file(), (
        f"{path.relative_to(PROJECT_ROOT).as_posix()} is missing. "
        "Regenerate with: python scripts/snapshot_canonical_release.py"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_is_tracked_not_gitignored() -> None:
    """The point of the manifest is that it survives a clone of an ignored corpus."""
    import subprocess

    rel = snapshot_canonical_release.MANIFEST_PATH.relative_to(PROJECT_ROOT).as_posix()
    result = subprocess.run(
        ["git", "check-ignore", "-q", rel], cwd=PROJECT_ROOT, capture_output=True
    )
    assert result.returncode != 0, f"{rel} is gitignored; it would not survive a clone"


def _is_ignored(rel: str) -> bool:
    import subprocess

    return (
        subprocess.run(
            ["git", "check-ignore", "-q", rel], cwd=PROJECT_ROOT, capture_output=True
        ).returncode
        == 0
    )


@pytest.mark.parametrize(
    "dataset", sorted(set(snapshot_canonical_release.released_dirs().values()))
)
def test_release_build_manifest_is_tracked_eligible(dataset: str) -> None:
    """Each build's own digest record must survive a clone of a corpus that does not.

    It used to sit under ``data/canonical/**`` and be ignored with everything else, which
    meant the record of what shipped died in exactly the event it existed to detect.
    """
    rel = f"data/canonical/{dataset}/manifest.json"
    assert (PROJECT_ROOT / rel).is_file(), f"{rel} is missing"
    assert not _is_ignored(rel), f"{rel} is gitignored; the release has no tracked digest"


@pytest.mark.parametrize(
    "rel",
    [
        "data/canonical/rigveda_full_v1/text_versions.jsonl",
        "data/canonical/samaveda_arcika_v1/text_versions.jsonl",
        "data/canonical/yajurveda_vsm_v1/passages.jsonl",
        "data/canonical/atharvaveda_saunaka_digital_working_v1/passages.jsonl",
    ],
)
def test_corpus_text_is_still_ignored(rel: str) -> None:
    """The exemption is for digests only.

    ``data/builds/four_veda_corpus_candidate_manifest.json`` states that the four datasets are
    separately licensed and that the CC BY-NC-SA Rigvedic layer must not be republished inside
    a single merged adapted work. Un-ignoring the corpus to get version history would do
    exactly that, so the manifest is the protection and the text stays out.
    """
    assert _is_ignored(rel), f"{rel} is no longer ignored; the corpus must not be committed"


def test_manifest_covers_every_projected_release_dataset(manifest: dict) -> None:
    """Every directory the graph projects must appear, or the gap is only partly closed.

    The two tracked semantic freezes in ``docs/manifests/`` hash 15 canonical files each, all
    of them ``rigveda_full_v1``. That left the Samaveda, Yajurveda and Atharvaveda releases
    with no tracked digest at all, which is the hole this asserts is now filled.
    """
    released = set(snapshot_canonical_release.released_dirs().values())
    covered = {
        row["dataset"]
        for row in manifest["entries"]
        if row["tier"] == snapshot_canonical_release.TIER_RELEASE
    }
    assert released <= covered, f"no tracked digest for: {sorted(released - covered)}"


def test_fingerprint_is_internally_consistent(manifest: dict) -> None:
    """The recorded fingerprint must be reproducible from the rows it claims to summarise."""
    assert (
        snapshot_canonical_release.fingerprint(manifest["entries"])
        == manifest["fingerprint_sha256"]
    )


def test_fingerprint_ignores_mtime(manifest: dict) -> None:
    """A copy does not carry mtime; an external snapshot must still prove identical bytes."""
    rows = [dict(row) for row in manifest["entries"]]
    for row in rows:
        row["mtime"] = "1970-01-01T00:00:00Z"
    assert snapshot_canonical_release.fingerprint(rows) == manifest["fingerprint_sha256"]


def test_release_tier_totals_match_the_rows(manifest: dict) -> None:
    rows = [r for r in manifest["entries"] if r["tier"] == snapshot_canonical_release.TIER_RELEASE]
    assert manifest["release_file_count"] == len(rows)
    assert manifest["release_total_bytes"] == sum(r["size"] for r in rows)


def test_live_release_still_matches_the_manifest(manifest: dict) -> None:
    """The real, untracked corpus on disk, re-hashed against its recorded identity."""
    result = snapshot_canonical_release.verify(
        manifest, tiers=frozenset({snapshot_canonical_release.TIER_RELEASE})
    )
    assert result["missing"] == [], f"released files are gone: {result['missing']}"
    assert result["mismatched"] == [], (
        "released file contents no longer match the recorded sha256: "
        f"{[m['path'] for m in result['mismatched']]}"
    )
    assert result["checked"] == manifest["release_file_count"]


# ---------------------------------------------------------------------------
# The negative case. Everything above is worthless if this does not hold.
# ---------------------------------------------------------------------------


def _tiny_tree(root: pathlib.Path) -> dict:
    """A three-file stand-in with the manifest's own row shape, built under tmp_path."""
    corpus = root / "data" / "canonical" / "toy_v1"
    corpus.mkdir(parents=True)
    for name, body in (
        ("passages.jsonl", '{"canonical_key":"VG:TOY:1"}\n'),
        ("text_versions.jsonl", '{"text_original":"agnim ile"}\n'),
        ("manifest.json", '{"passage_count": 1}\n'),
    ):
        (corpus / name).write_text(body, encoding="utf-8")

    rows = []
    for path in sorted(corpus.rglob("*")):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "tier": snapshot_canonical_release.TIER_RELEASE,
                "dataset": "toy_v1",
                "size": path.stat().st_size,
                "sha256": snapshot_canonical_release.sha256_file(path),
                "mtime": "2026-09-16T00:00:00Z",
            }
        )
    return {
        "entries": rows,
        "fingerprint_sha256": snapshot_canonical_release.fingerprint(rows),
        "release_file_count": len(rows),
    }


def test_clean_copy_passes(tmp_path: pathlib.Path) -> None:
    toy = _tiny_tree(tmp_path)
    result = snapshot_canonical_release.verify(toy, root=tmp_path)
    assert result["ok"] is True
    assert result["internally_consistent"] is True
    assert result["checked"] == 3


def test_perturbed_file_is_detected(tmp_path: pathlib.Path) -> None:
    """One byte changed in a copy must be named, with both digests, and fail the run."""
    toy = _tiny_tree(tmp_path)
    victim = tmp_path / "data" / "canonical" / "toy_v1" / "text_versions.jsonl"
    original = victim.read_text(encoding="utf-8")
    victim.write_text(original.replace("agnim", "agniM"), encoding="utf-8")

    result = snapshot_canonical_release.verify(toy, root=tmp_path)

    assert result["ok"] is False
    assert [m["path"] for m in result["mismatched"]] == [victim.relative_to(tmp_path).as_posix()]
    bad = result["mismatched"][0]
    assert bad["actual_sha256"] != bad["expected_sha256"]
    assert result["missing"] == []


def test_truncated_file_is_detected(tmp_path: pathlib.Path) -> None:
    """The failure mode this exists for: a partial rebuild that leaves a shorter file."""
    toy = _tiny_tree(tmp_path)
    victim = tmp_path / "data" / "canonical" / "toy_v1" / "passages.jsonl"
    victim.write_bytes(b"")

    result = snapshot_canonical_release.verify(toy, root=tmp_path)

    assert result["ok"] is False
    assert result["mismatched"][0]["path"] == victim.relative_to(tmp_path).as_posix()
    assert result["mismatched"][0]["actual_size"] == 0


def test_deleted_file_is_detected(tmp_path: pathlib.Path) -> None:
    """A stray export that removes a file must not read as 'nothing changed'."""
    toy = _tiny_tree(tmp_path)
    victim = tmp_path / "data" / "canonical" / "toy_v1" / "manifest.json"
    victim.unlink()

    result = snapshot_canonical_release.verify(toy, root=tmp_path)

    assert result["ok"] is False
    assert result["missing"] == [victim.relative_to(tmp_path).as_posix()]


def test_staged_sv_apparatus_proposal_was_applied_and_stays_applied() -> None:
    """The correction has LANDED, so this guard now asserts the post-application state.

    It used to assert the pre-application state -- that the stored text still matched the
    proposal's recorded "current" -- so that a staged correction would go stale loudly
    rather than silently. It did exactly that: applying the correction in R5
    (GAP-PRODUCT_SURFACE-005) turned this test red, which is the guard working and not the
    guard breaking.

    Inverted rather than deleted, because the same file still has something to check and
    the direction is the only thing that changed. What must hold now:

    *   the stored text equals the proposal's PROPOSED text, exactly;
    *   the apparatus prefix is gone from the head of the stored text;
    *   the correction was a pure prefix deletion, so ``current`` is still
        ``apparatus + proposed`` and no other codepoint ever moved; and
    *   the stored ``content_sha256`` is the proposed digest.

    A rebuild that reintroduced the apparatus, or an edit that changed any other codepoint
    while removing it, fails here.
    """
    proposal_path = (
        PROJECT_ROOT
        / "data"
        / "staging"
        / "final_closure_sprint"
        / "agent6"
        / "gap005_sv_apparatus_corrections.json"
    )
    if not proposal_path.is_file():
        pytest.skip("SV apparatus proposal not present")
    proposal = json.loads(proposal_path.read_text(encoding="utf-8"))

    corpus = PROJECT_ROOT / "data" / "canonical" / "samaveda_arcika_v1" / "text_versions.jsonl"
    by_locator = {}
    for line in corpus.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            by_locator[row["source_locator"]] = row

    import hashlib

    for correction in proposal["corrections"]:
        row = by_locator[correction["source_locator"]]
        apparatus = correction["apparatus_removed"]["substring"]
        proposed = correction["proposed"]["text_original"]
        current = correction["current"]["text_original"]

        # The proposal's own internal claim, still checked: a pure prefix deletion.
        assert current == apparatus + proposed, (
            "the correction must be a pure prefix deletion: no other codepoint may change"
        )
        # And the stored text is now the corrected one.
        assert row["text_original"] == proposed, (
            f"{correction['canonical_key']}: the stored text is not the corrected reading. "
            "If the corpus was rebuilt from the uncorrected parser, the apparatus is back."
        )
        assert not row["text_original"].startswith(apparatus), (
            f"{correction['canonical_key']}: the apparatus prefix is present again"
        )
        assert (
            hashlib.sha256(proposed.encode("utf-8")).hexdigest()
            == correction["proposed"]["content_sha256"]
        )
        assert row["content_sha256"] == correction["proposed"]["content_sha256"], (
            f"{correction['canonical_key']}: stored digest is not the corrected digest"
        )
        assert correction["source_evidence"][
            "corrected_reading_occurs_verbatim_in_pinned_page_line_form"
        ], f"{correction['canonical_key']}: corrected reading is not in the pinned page"


def test_snapshot_roundtrip_reproduces_the_fingerprint(tmp_path: pathlib.Path) -> None:
    """An external snapshot is only a recovery target if it can prove it holds the bytes."""
    source = tmp_path / "src"
    toy = _tiny_tree(source)
    destination = tmp_path / "snap"
    destination.mkdir()
    for row in toy["entries"]:
        target = destination / row["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / row["path"], target)

    result = snapshot_canonical_release.verify(toy, root=destination)
    assert result["ok"] is True
    assert snapshot_canonical_release.fingerprint(toy["entries"]) == toy["fingerprint_sha256"]
