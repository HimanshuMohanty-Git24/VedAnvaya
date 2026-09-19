"""The two-tier audio publication contract, stated as tests.

``OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION`` (2026-09-19) lets a recording be published
without anyone having heard it. Everything that makes that safe rather than reckless is
one of two things: a refusal in
:meth:`~vedagraph.product.audio.models.AudioRecord._check_internal_consistency`, or the
single sentence :func:`~vedagraph.product.audio.catalog.tier_note` writes. So most tests
here assert that a construction *fails*, and the ones that do not assert that a sentence
does not contain a claim.

Two of them read the live artifacts rather than a fixture. A tier contract that held only
over hand-built records would say nothing about the catalogue that actually ships, and this
project has twice certified an absence against the wrong surface.

The guard tests are paired with mutations. A refusal test that would also pass against the
deleted guard is not a test, and this repository has found two of those; each
``test_..._guard_is_what_refuses_it`` below deletes the clause it depends on and asserts
the construction then succeeds.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pydantic import ValidationError

from vedagraph.product.audio.catalog import (
    AudioCatalog,
    tier_label,
    tier_note,
    write_catalog,
)
from vedagraph.product.audio.models import (
    AudioRecord,
    AudioScope,
    AudioType,
    MappingConfidence,
    PlaybackMode,
    PublicationTier,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_CATALOG = REPO_ROOT / "data" / "product" / "audio_catalog.jsonl"
DECISIONS_LOG = REPO_ROOT / "data" / "manual" / "audio_review" / "sample_decisions.jsonl"

#: Phrases that assert a human heard the recording. None may appear in anything the product
#: renders for an unreviewed row. The bare word "verified" is deliberately *not* on this
#: list: the unreviewed note has to be able to say "it is not described as verified".
HUMAN_REVIEW_CLAIMS = (
    "human verified",
    "human-verified",
    "humanly verified",
    "audibly verified",
    "audibly-verified",
    "verified by ear",
    "listened to and confirmed",
    "confirmed by a listener",
    "reviewed by a listener",
)

EVIDENCE = "data/manual/audio_review/sample_decisions.jsonl: reviewer X played Y on Z."

#: One Rigvedic key from the staged set. Its five *rival* sources are all in
#: ``rejected.jsonl``; the source actually admitted is not. Named here because the
#: distinction between those two facts is what the exclusion rule turns on.
RV_ADMITTED_KEY = "VG:RV:SAK:M01:S117:V006"
RV_ADMITTED_SOURCE = "VEDAWEB.RV.SAK.KIRCHHEINER.2026-09-15"
RV_DECLINED_SOURCE = "VEDSEARCH.RV.SAK.RECITATION.2026-09-12"


def _admission_module() -> ModuleType:
    """Load the admission script by path; ``scripts/audio`` is not an importable package."""
    path = REPO_ROOT / "scripts" / "audio" / "admit_source_mapped_rows.py"
    spec = importlib.util.spec_from_file_location("admit_source_mapped_rows", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def admission() -> ModuleType:
    return _admission_module()


def record(**overrides: Any) -> AudioRecord:
    base: dict[str, Any] = {
        "audio_id": "TEST:RV:one.mp3",
        "veda": "RV",
        "recension": "SAK",
        "scope_type": AudioScope.SUKTA,
        "scope_key": "VG:RV:SAK:M01:S001",
        "audio_type": AudioType.RECITATION,
        "title": "A recitation",
        "source_name": "A source",
        "source_page": "https://example.invalid/page",
        "media_url": "https://example.invalid/one.mp3",
        "mapping_method": "derived from the publisher's own one-file-per-sukta layout",
        "mapping_confidence": MappingConfidence.STRUCTURAL,
        "playback_mode": PlaybackMode.REMOTE_DIRECT,
    }
    base.update(overrides)
    return AudioRecord(**base)


def effective_decisions() -> dict[tuple[str, str], dict[str, Any]]:
    """The last line per ``review_id`` in the append-only log, keyed by key and media URL."""
    by_review: dict[str, dict[str, Any]] = {}
    if DECISIONS_LOG.exists():
        with DECISIONS_LOG.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    by_review[row["review_id"]] = row
    return {(r["canonical_key"], r["media_url"]): r for r in by_review.values()}


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def test_a_record_that_says_nothing_about_review_is_unreviewed() -> None:
    """The default decides 16,834 incumbent rows, so it is a contract and not a detail."""
    assert record().publication_tier is PublicationTier.SOURCE_MAPPED_UNREVIEWED


def test_a_catalogue_line_without_the_field_loads_as_unreviewed(tmp_path: Path) -> None:
    line = json.loads(record().model_dump_json())
    del line["publication_tier"]
    del line["audible_review_evidence"]
    path = tmp_path / "audio_catalog.jsonl"
    path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    loaded = AudioCatalog.load(path)
    assert loaded.records[0].publication_tier is PublicationTier.SOURCE_MAPPED_UNREVIEWED


def test_the_reviewed_tier_is_reachable_when_the_hearing_is_cited() -> None:
    reviewed = record(
        publication_tier=PublicationTier.RELEASED_VERIFIED, audible_review_evidence=EVIDENCE
    )
    assert reviewed.publication_tier is PublicationTier.RELEASED_VERIFIED


@pytest.mark.parametrize("evidence", [None, "", "   "])
def test_the_reviewed_tier_is_refused_without_evidence_of_a_hearing(evidence: str | None) -> None:
    with pytest.raises(ValidationError, match="audible_review_evidence"):
        record(
            publication_tier=PublicationTier.RELEASED_VERIFIED,
            audible_review_evidence=evidence,
        )


def test_an_unreviewed_row_may_not_carry_evidence_of_a_hearing() -> None:
    """The mirror clause. Two fields describing one fact must not be able to disagree."""
    with pytest.raises(ValidationError, match="audible_review_evidence is set"):
        record(
            publication_tier=PublicationTier.SOURCE_MAPPED_UNREVIEWED,
            audible_review_evidence=EVIDENCE,
        )


MODELS_SOURCE = REPO_ROOT / "src" / "vedagraph" / "product" / "audio" / "models.py"

#: The two guard conditions, quoted from the source, and what each becomes when disarmed.
#: Quoted rather than described so that editing the guard breaks these tests loudly instead
#: of leaving them asserting a clause that no longer exists.
GUARDS = {
    "released_verified_needs_evidence": (
        'if not (self.audible_review_evidence or "").strip():',
        "if False:",
    ),
    "unreviewed_must_not_carry_evidence": (
        "elif self.audible_review_evidence is not None:",
        "elif False:",
    ),
}


def _models_with_guard_disarmed(guard: str) -> ModuleType:
    """A copy of ``models.py`` with one guard condition replaced by ``False``."""
    original, replacement = GUARDS[guard]
    source = MODELS_SOURCE.read_text(encoding="utf-8")
    assert source.count(original) == 1, f"guard {guard!r} is no longer where the test expects it"
    module = ModuleType(f"audio_models_without_{guard}")
    # Registered before exec and rebuilt after, because ``models.py`` carries
    # ``from __future__ import annotations``: pydantic resolves the string annotations out
    # of the module's own namespace and needs to be able to find it by name.
    sys.modules[module.__name__] = module
    exec(
        compile(source.replace(original, replacement), f"<{module.__name__}>", "exec"),
        module.__dict__,
    )
    module.AudioRecord.model_rebuild(_types_namespace=module.__dict__)
    return module


def _as_dict(**overrides: Any) -> dict[str, Any]:
    payload = json.loads(record().model_dump_json())
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("guard", "fields"),
    [
        (
            "released_verified_needs_evidence",
            {"publication_tier": "RELEASED_VERIFIED", "audible_review_evidence": None},
        ),
        (
            "unreviewed_must_not_carry_evidence",
            {
                "publication_tier": "SOURCE_MAPPED_UNREVIEWED",
                "audible_review_evidence": EVIDENCE,
            },
        ),
    ],
)
def test_each_refusal_stops_happening_when_its_guard_is_disarmed(
    guard: str, fields: dict[str, Any]
) -> None:
    """Mutate, then trust.

    Each construction above is refused by the shipped model. Here the same construction is
    fed to a copy of the model with exactly one guard condition replaced by ``False``, and
    it succeeds -- which is what proves the refusal came from that clause rather than from
    a field type, a coincidence, or another validator entirely. Two of this repository's
    rejection tests once passed against the guard deleted.
    """
    with pytest.raises(ValidationError):
        AudioRecord(**_as_dict(**fields))
    mutated = _models_with_guard_disarmed(guard)
    permitted = mutated.AudioRecord(**_as_dict(**fields))
    assert permitted.publication_tier.value == fields["publication_tier"]


def test_the_tiers_partition_the_catalogue(tmp_path: Path) -> None:
    records = [
        record(audio_id="TEST:RV:a.mp3", scope_key="VG:RV:SAK:M01:S001"),
        record(audio_id="TEST:RV:b.mp3", scope_key="VG:RV:SAK:M01:S002"),
        record(
            audio_id="TEST:RV:c.mp3",
            scope_key="VG:RV:SAK:M01:S003",
            publication_tier=PublicationTier.RELEASED_VERIFIED,
            audible_review_evidence=EVIDENCE,
        ),
    ]
    path = tmp_path / "audio_catalog.jsonl"
    write_catalog(path, records)
    catalog = AudioCatalog.load(path)
    per_tier = {tier: len(catalog.for_tier(tier)) for tier in PublicationTier}
    assert sum(per_tier.values()) == len(catalog) == 3
    assert per_tier[PublicationTier.RELEASED_VERIFIED] == 1


def test_every_veda_carries_every_tier_even_at_zero(tmp_path: Path) -> None:
    """A missing key renders as nothing; a zero renders as "0 reviewed"."""
    path = tmp_path / "audio_catalog.jsonl"
    write_catalog(path, [record()])
    counts = AudioCatalog.load(path).counts_by_veda_and_tier()
    assert set(counts) >= {"RV", "SV", "YV", "AV"}
    for veda, tiers in counts.items():
        assert set(tiers) == {tier.value for tier in PublicationTier}, veda
    assert counts["SV"]["SOURCE_MAPPED_UNREVIEWED"] == 0


# ---------------------------------------------------------------------------
# What a reader is told
# ---------------------------------------------------------------------------


def test_the_unreviewed_note_never_claims_a_person_heard_it() -> None:
    note = tier_note(PublicationTier.SOURCE_MAPPED_UNREVIEWED).lower()
    for claim in HUMAN_REVIEW_CLAIMS:
        assert claim not in note, claim
    assert "no person has listened" in note


def test_the_unreviewed_label_never_reads_as_verified() -> None:
    label = tier_label(PublicationTier.SOURCE_MAPPED_UNREVIEWED).lower()
    for claim in HUMAN_REVIEW_CLAIMS:
        assert claim not in label, claim
    assert "not yet reviewed" in label


def test_the_reviewed_note_says_who_did_what() -> None:
    note = tier_note(PublicationTier.RELEASED_VERIFIED).lower()
    assert "played this recording" in note
    assert "named reviewer" in note


def test_every_tier_has_a_note_and_a_label() -> None:
    for tier in PublicationTier:
        assert tier_note(tier).strip()
        assert tier_label(tier).strip()


# ---------------------------------------------------------------------------
# The shipped catalogue
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def live_catalog() -> AudioCatalog:
    if not LIVE_CATALOG.exists():
        pytest.skip("no shipped catalogue on this checkout")
    return AudioCatalog.load(LIVE_CATALOG)


def test_the_shipped_catalogue_tiers_sum_to_the_catalogue(live_catalog: AudioCatalog) -> None:
    per_tier = {tier: len(live_catalog.for_tier(tier)) for tier in PublicationTier}
    assert sum(per_tier.values()) == len(live_catalog)
    by_veda = live_catalog.counts_by_veda_and_tier()
    assert sum(sum(t.values()) for t in by_veda.values()) == len(live_catalog)


def test_no_shipped_unreviewed_row_carries_review_evidence(live_catalog: AudioCatalog) -> None:
    offenders = [
        r.audio_id
        for r in live_catalog.for_tier(PublicationTier.SOURCE_MAPPED_UNREVIEWED)
        if r.audible_review_evidence
    ]
    assert offenders == []


def test_every_shipped_reviewed_row_is_backed_by_a_real_decision_row(
    live_catalog: AudioCatalog,
) -> None:
    """The claim on the record must be findable in the log, by key *and* by media URL.

    By media URL because a verdict about one recording of a passage says nothing about a
    different recording of the same passage, and because the owner sample and the staged
    Atharvavedic set draw on two different publishers for overlapping keys.
    """
    decisions = effective_decisions()
    for row in live_catalog.for_tier(PublicationTier.RELEASED_VERIFIED):
        assert row.audible_review_evidence, row.audio_id
        decision = decisions.get((row.scope_key or "", row.media_url or ""))
        assert decision is not None, f"{row.audio_id}: no decision row for this key and URL"
        assert decision["verdict"] == "AUDIBLY_VERIFIED", row.audio_id
        assert decision["recording_opened"] is True, row.audio_id
        assert decision["reviewer"], row.audio_id


def test_the_shipped_catalogue_does_not_claim_more_hearings_than_the_log_holds(
    live_catalog: AudioCatalog,
) -> None:
    """The population check the sample acceptance forbids collapsing."""
    heard = sum(
        1 for row in effective_decisions().values() if row.get("verdict") == "AUDIBLY_VERIFIED"
    )
    assert len(live_catalog.for_tier(PublicationTier.RELEASED_VERIFIED)) <= heard


# ---------------------------------------------------------------------------
# "No known rejection", which is the condition most easily got wrong
# ---------------------------------------------------------------------------


def test_a_rejection_naming_a_rival_source_bars_that_source_only(admission: ModuleType) -> None:
    """The whole Rigvedic set hangs on this.

    All 150 admitted Rigvedic keys appear in ``rejected.jsonl`` -- five times each, once
    per declined rival source. An exclusion keyed on ``canonical_key`` alone would refuse
    every one of them and look rigorous doing it.
    """
    per_candidate, whole_key = admission.rejection_index("audio_rv")
    assert (RV_ADMITTED_KEY, RV_DECLINED_SOURCE) in per_candidate
    assert (RV_ADMITTED_KEY, RV_ADMITTED_SOURCE) not in per_candidate
    assert RV_ADMITTED_KEY not in whole_key


def test_the_rigvedic_rejections_really_do_name_every_admitted_key(
    admission: ModuleType,
) -> None:
    """Proves the test above is not passing on a file that happens to be empty of them."""
    per_candidate, _ = admission.rejection_index("audio_rv")
    rejected_keys = {key for key, _ in per_candidate}
    staged = [
        json.loads(line)
        for line in (REPO_ROOT / "data" / "staging" / "audio_rv" / "rows.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert staged, "no staged Rigvedic rows to reason about"
    assert all(row["canonical_key"] in rejected_keys for row in staged)


def test_a_rejection_naming_no_candidate_bars_the_whole_key(
    admission: ModuleType, tmp_path: Path
) -> None:
    staging = tmp_path / "data" / "staging" / "synthetic"
    staging.mkdir(parents=True)
    (staging / "rejected.jsonl").write_text(
        json.dumps({"canonical_key": "VG:RV:SAK:M01:S001:V001", "reason_code": "NO_AUDIO"}) + "\n",
        encoding="utf-8",
    )
    admission.REPO_ROOT = tmp_path
    try:
        per_candidate, whole_key = admission.rejection_index("synthetic")
    finally:
        admission.REPO_ROOT = REPO_ROOT
    assert whole_key == {"VG:RV:SAK:M01:S001:V001"}
    assert per_candidate == set()


def test_the_admission_run_refused_what_its_report_says_it_refused() -> None:
    """The refusals are the interesting output; a run that refused nothing proves nothing."""
    report_path = REPO_ROOT / "docs" / "reports" / "audio" / "admission_report.json"
    if not report_path.exists():
        pytest.skip("no admission report on this checkout")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["admitted"] + report["refused"] == report["candidates_evaluated"]
    assert report["refused"] > 0, "every condition passing is a reason to distrust them"
    assert sum(report["admitted_by_tier"].values()) == report["admitted"]
    assert report["catalogue_after"] - report["catalogue_before"] == report["admitted"]


def test_no_text_unverified_row_reached_the_catalogue(live_catalog: AudioCatalog) -> None:
    """Condition 3 of the decision, checked on the shipped file rather than in the report.

    The eight Yajurvedic residue rows have a dittographic or truncated source text field;
    what their recording says is unknown. The new policy widens what may be published
    *unheard*, not what may be published *unmapped*.
    """
    assert [r.audio_id for r in live_catalog if not r.text_verified] == []
