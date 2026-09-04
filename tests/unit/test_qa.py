from uuid import uuid4

from vedagraph.models import Passage, QAIssue, SourceAssertion, SuktaDiscoveryRecord
from vedagraph.models.enums import DiscoveryAvailability, EntityType, QASeverity, QAStatus
from vedagraph.qa import CorpusRecords, qa_status, validate_corpus


def test_qa_detects_duplicate_keys_and_missing_sanskrit() -> None:
    key = "VG:RV:SAK:M01:S001:V001"
    passages = [
        Passage(
            entity_id=uuid4(),
            canonical_key=key,
            canonical_urn="urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:1",
            entity_type=EntityType.MANTRA,
            work_id="VG:WORK:RV:SAK",
            hierarchy={"mandala": 1, "sukta": 1, "mantra": 1},
            canonical_citation="RV 1.1.1",
            sequence_in_parent=1,
        ),
        Passage(
            entity_id=uuid4(),
            canonical_key=key,
            canonical_urn="urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:2",
            entity_type=EntityType.MANTRA,
            work_id="VG:WORK:RV:SAK",
            hierarchy={"mandala": 1, "sukta": 1, "mantra": 2},
            canonical_citation="RV 1.1.2",
            sequence_in_parent=2,
        ),
    ]
    issues = validate_corpus(
        CorpusRecords(
            passages=passages,
            texts=[],
            translations=[],
            metadata=[],
            sources=[],
            citations=[],
            audio_recordings=[],
            audio_segments=[],
            source_assertions=[],
        )
    )
    check_ids = {issue.check_id for issue in issues}
    assert "unique_canonical_keys" in check_ids
    assert "non_empty_sanskrit" in check_ids


def test_qa_detects_wrong_parent_duplicate_sequence_and_gap() -> None:
    mandala = Passage(
        entity_id=uuid4(),
        canonical_key="VG:RV:SAK:M01",
        canonical_urn="urn:vedagraph:section:rigveda:shakala:mandala:1",
        entity_type=EntityType.SECTION,
        work_id="VG:WORK:RV:SAK",
        hierarchy={"mandala": 1},
        canonical_citation="RV 1",
        sequence_in_parent=1,
    )
    mantras = [
        Passage(
            entity_id=uuid4(),
            canonical_key=f"VG:RV:SAK:M01:S001:V00{number}",
            canonical_urn=f"urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:{number}",
            entity_type=EntityType.MANTRA,
            work_id="VG:WORK:RV:SAK",
            hierarchy={"mandala": 1, "sukta": 1, "mantra": number},
            canonical_citation=f"RV 1.1.{number}",
            parent_key=mandala.canonical_key,
            sequence_in_parent=sequence,
        )
        for number, sequence in [(1, 1), (3, 1)]
    ]
    issues = validate_corpus(
        CorpusRecords(
            passages=[mandala, *mantras],
            texts=[],
            translations=[],
            metadata=[],
            sources=[],
            citations=[],
            audio_recordings=[],
            audio_segments=[],
            source_assertions=[],
        )
    )
    check_ids = {issue.check_id for issue in issues}
    assert {"valid_parents", "unique_sequences_in_parent"} <= check_ids


def test_info_only_qa_is_passed() -> None:
    issue = QAIssue(
        issue_id=uuid4(), check_id="coverage", severity=QASeverity.INFO, message="partial sample"
    )
    assert qa_status([issue]) == QAStatus.PASSED


def test_qa_flags_deferred_metadata_range_but_not_plain_values() -> None:
    sukta_id = uuid4()
    sukta = Passage(
        entity_id=sukta_id,
        canonical_key="VG:RV:SAK:M01:S022",
        canonical_urn="urn:vedagraph:sukta:rigveda:shakala:mandala:1:sukta:22",
        entity_type=EntityType.HYMN,
        work_id="VG:WORK:RV:SAK",
        hierarchy={"mandala": 1, "sukta": 22},
        canonical_citation="RV 1.22",
        sequence_in_parent=22,
    )

    def assertion(predicate: str, value: str) -> SourceAssertion:
        return SourceAssertion(
            assertion_id=uuid4(),
            subject_id="VG:RV:SAK:M01:S022",
            predicate=predicate,
            value=value,
            source_id="VHP",
            source_locator="RV 1.22 VHP page",
        )

    issues = validate_corpus(
        CorpusRecords(
            passages=[sukta],
            texts=[],
            translations=[],
            metadata=[],
            sources=[],
            citations=[],
            audio_recordings=[],
            audio_segments=[],
            source_assertions=[
                assertion("HAS_DEVATA", "१-४ अश्विनौ, ५-८ सविता"),
                assertion("HAS_CHANDAS", "गायत्री"),
                assertion("HAS_TEXT", "RV 1.22.1 body 1"),
            ],
        )
    )
    deferred = [issue for issue in issues if issue.check_id == "deferred_metadata_range"]
    assert len(deferred) == 1
    assert deferred[0].severity == QASeverity.WARNING
    assert deferred[0].details["predicate"] == "HAS_DEVATA"


def _mantra(sukta: int, mantra: int) -> Passage:
    return Passage(
        entity_id=uuid4(),
        canonical_key=f"VG:RV:SAK:M01:S{sukta:03d}:V{mantra:03d}",
        canonical_urn=f"urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:{sukta}:mantra:{mantra}",
        entity_type=EntityType.MANTRA,
        work_id="VG:WORK:RV:SAK",
        hierarchy={"mandala": 1, "sukta": sukta, "mantra": mantra},
        canonical_citation=f"RV 1.{sukta}.{mantra}",
        parent_key=f"VG:RV:SAK:M01:S{sukta:03d}",
        sequence_in_parent=mantra,
    )


def _discovery(sukta: int, known_mantra_count: int) -> SuktaDiscoveryRecord:
    return SuktaDiscoveryRecord(
        canonical_sukta_key=f"VG:RV:SAK:M01:S{sukta:03d}",
        sukta_number=sukta,
        mandala_number=1,
        parent_mandala_key="VG:RV:SAK:M01",
        source_id="GRETIL",
        source_locator=f"RV 1.{sukta}",
        availability=DiscoveryAvailability.AVAILABLE,
        discovery_source="TEI div/lg hierarchy",
        known_mantra_count=known_mantra_count,
        snapshot_id="GRETIL:fixture",
    )


def test_qa_flags_mantra_count_mismatch_against_gretil_discovery() -> None:
    # GRETIL discovery says Sukta 1 has 3 mantras, but only 2 were canonically ingested:
    # a silent drop this check exists to catch.
    passages = [_mantra(1, 1), _mantra(1, 2)]
    issues = validate_corpus(
        CorpusRecords(
            passages=passages,
            texts=[],
            translations=[],
            metadata=[],
            sources=[],
            citations=[],
            audio_recordings=[],
            audio_segments=[],
            source_assertions=[],
            discoveries=[_discovery(1, 3)],
        )
    )
    mismatches = [
        issue for issue in issues if issue.check_id == "expected_vs_canonical_mantra_count"
    ]
    assert len(mismatches) == 1
    assert mismatches[0].severity == QASeverity.ERROR
    assert mismatches[0].details == {"expected": 3, "actual": 2}


def test_qa_does_not_flag_a_sukta_deliberately_left_out_of_the_build() -> None:
    # A partial-sample build never ingests Sukta 2 at all; that is not the same failure
    # as silently dropping a mantra from a Sukta the build did select.
    passages = [_mantra(1, 1)]
    issues = validate_corpus(
        CorpusRecords(
            passages=passages,
            texts=[],
            translations=[],
            metadata=[],
            sources=[],
            citations=[],
            audio_recordings=[],
            audio_segments=[],
            source_assertions=[],
            discoveries=[_discovery(1, 1), _discovery(2, 5)],
        )
    )
    assert not [issue for issue in issues if issue.check_id == "expected_vs_canonical_mantra_count"]
