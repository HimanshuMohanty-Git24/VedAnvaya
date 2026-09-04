"""The traditional-metadata range parser must fail closed, never guess."""

from pathlib import Path

from vedagraph.identity import uuid_for_urn
from vedagraph.metadata import (
    candidates_from_assertions,
    candidates_from_qa,
    parse_metadata_value,
    parse_range_value,
    render_review,
    write_review,
)
from vedagraph.models import QAIssue, SourceAssertion
from vedagraph.models.enums import (
    AssertionStatus,
    CandidateScopeType,
    MetadataPredicate,
    QASeverity,
    RangeParseStatus,
    ReviewStatus,
)

# The six strings that are currently deferred in the Mandala 1 sample.
RV_1_22_DEVATA = (
    "१-४ अश्विनौ, ५-८ सविता, ९-१० अग्निः, ११ देव्यः, "
    "१२ इन्द्राणी वरुणान्यग्नाय्यः, १३-१४ द्यावापृथिव्यौ, १५ पृथिवी, "
    "१६ विष्णुर्देवा वा, १७-२१ विष्णुः"
)
RV_1_50_DEVATA = "सूर्यः (११-१३ रोगघ्न्य उपनिषदः, १३ अन्त्योऽर्धर्चः द्विषद् घ्नश्च)"
RV_1_50_CHANDAS = "गायत्री, १०-१३ अनुष्टुप्"
RV_1_191_CHANDAS = "अनुष्टुप्, १०-१२ महा पंक्तिः, १३ महबृहती"
RV_1_164_CHANDAS = "त्रिष्टुप् १२, १५, २३, २९, ३६, ४१ जगती, ४२ प्रस्तार पंक्तिः, ५१ अनुष्टप्"
RV_1_164_DEVATA = (
    "१-४१ विश्वे देवाः, ४२ आद्यर्धर्चस्य वाक्, द्वितीयस्य आपः, "
    "४३ आद्यर्धर्चस्य शकधूमः, द्वितीयस्य सोमः, ४४ केशिनः (अग्निः सूर्यो वायुश्च,) "
    "४५ वाक्, ४६-४७ सूर्यः, ४८ संवत्सर कालचक्रम्,४९ सरस्वती, ५० साध्याः, "
    "५१ सूर्यः, पर्जन्याग्नयो वा, ५२ सरस्वान्, सूर्यो वा"
)


def test_unscoped_entity_is_a_whole_passage_claim() -> None:
    status, segments, unparsed, _ = parse_range_value("मधुच्छन्दा वैश्वामित्रः")
    assert status == RangeParseStatus.PARSED
    assert not unparsed
    assert segments[0].scope_type == CandidateScopeType.WHOLE_PASSAGE
    assert segments[0].raw_entity == "मधुच्छन्दा वैश्वामित्रः"
    assert not segments[0].needs_review


def test_devanagari_digit_ranges_are_read() -> None:
    status, segments, unparsed, _ = parse_range_value("१-४ अश्विनौ, ५-८ सविता")
    assert status == RangeParseStatus.PARSED
    assert not unparsed
    assert [(s.start_mantra, s.end_mantra, s.raw_entity) for s in segments] == [
        (1, 4, "अश्विनौ"),
        (5, 8, "सविता"),
    ]


def test_ascii_digit_ranges_are_read_the_same_way() -> None:
    status, segments, _, _ = parse_range_value("1-4 Ashvins, 5 Savitar")
    assert status == RangeParseStatus.PARSED
    assert [(s.start_mantra, s.end_mantra) for s in segments] == [(1, 4), (5, 5)]
    assert segments[1].scope_type == CandidateScopeType.MANTRA


def test_bare_numbers_accumulate_onto_the_following_entity() -> None:
    status, segments, _, _ = parse_range_value("१२, १५, २३ जगती")
    assert status == RangeParseStatus.PARSED
    assert segments[0].scope_type == CandidateScopeType.MANTRA_SET
    assert segments[0].mantras == [12, 15, 23]
    assert segments[0].start_mantra is None


def test_multiple_ranges_across_a_whole_sukta_are_read() -> None:
    status, segments, unparsed, _ = parse_range_value(RV_1_22_DEVATA)
    assert status == RangeParseStatus.PARTIALLY_PARSED
    assert not unparsed
    assert len(segments) == 9
    assert segments[0].start_mantra == 1 and segments[-1].end_mantra == 21
    # The alternative marker is detected as a whole word, not as a syllable in a name.
    alternatives = [s for s in segments if s.qualifier_markers]
    assert [s.raw_entity for s in alternatives] == ["विष्णुर्देवा वा"]


def test_a_default_entity_with_exceptions_is_never_silently_broadened() -> None:
    status, segments, _, note = parse_range_value(RV_1_50_CHANDAS)
    assert status == RangeParseStatus.PARTIALLY_PARSED
    assert segments[0].scope_type == CandidateScopeType.WHOLE_PASSAGE
    assert segments[0].needs_review
    assert segments[1].start_mantra == 10 and segments[1].end_mantra == 13
    assert note is not None


def test_half_verse_scope_is_preserved_and_not_flattened_to_the_mantra() -> None:
    status, segments, _, _ = parse_range_value(RV_1_50_DEVATA)
    assert status == RangeParseStatus.PARTIALLY_PARSED
    half = [s for s in segments if s.scope_type == CandidateScopeType.HALF_VERSE]
    assert len(half) == 1
    assert half[0].start_mantra == 13
    assert "अन्त्योऽर्धर्चः" in half[0].qualifier_markers
    assert half[0].needs_review
    assert half[0].raw_scope_text


def test_an_entity_written_before_its_numbers_is_ambiguous() -> None:
    status, segments, unparsed, _ = parse_range_value(RV_1_164_CHANDAS)
    assert status == RangeParseStatus.AMBIGUOUS
    assert unparsed == ["त्रिष्टुप् १२"]
    assert segments  # the readable segments are still surfaced for the reviewer


def test_an_inline_gloss_containing_a_separator_is_unsupported_not_guessed() -> None:
    status, segments, unparsed, note = parse_range_value(RV_1_164_DEVATA)
    assert status == RangeParseStatus.UNSUPPORTED
    assert segments == []
    assert unparsed == [" ".join(RV_1_164_DEVATA.split())]
    assert note is not None and "not in a supported position" in note


def test_empty_value_is_invalid() -> None:
    status, segments, _, _ = parse_range_value("   ")
    assert status == RangeParseStatus.INVALID
    assert segments == []


def test_only_clean_parses_are_marked_safe_to_promote() -> None:
    clean = parse_metadata_value(
        subject_id="VG:RV:SAK:M01:S001",
        predicate=MetadataPredicate.HAS_RISHI,
        value="मधुच्छन्दा वैश्वामित्रः",
        source_id="VHP",
        source_locator="RV 1.1 VHP page",
    )
    assert clean.parse_status == RangeParseStatus.PARSED
    assert clean.safe_to_promote
    assert clean.review_status == ReviewStatus.NEEDS_REVIEW

    for value in (
        RV_1_22_DEVATA,
        RV_1_50_DEVATA,
        RV_1_50_CHANDAS,
        RV_1_191_CHANDAS,
        RV_1_164_CHANDAS,
        RV_1_164_DEVATA,
    ):
        candidate = parse_metadata_value(
            subject_id="VG:RV:SAK:M01:S164",
            predicate=MetadataPredicate.HAS_DEVATA,
            value=value,
            source_id="VHP",
            source_locator="RV 1.164 VHP page",
        )
        assert not candidate.safe_to_promote, value
        assert candidate.review_status == ReviewStatus.NEEDS_REVIEW


def test_candidate_records_serialize_and_keep_the_raw_source_string() -> None:
    candidate = parse_metadata_value(
        subject_id="VG:RV:SAK:M01:S050",
        predicate=MetadataPredicate.HAS_DEVATA,
        value=RV_1_50_DEVATA,
        source_id="VHP",
        source_locator="RV 1.50 VHP page",
    )
    payload = candidate.model_dump(mode="json")
    assert payload["raw_value"] == " ".join(RV_1_50_DEVATA.split())
    assert payload["parser_version"] == candidate.parser_version
    assert payload["segments"][0]["raw_scope_text"]
    assert candidate.candidate_id == uuid_for_urn(
        f"urn:vedagraph:metadata-candidate:VG:RV:SAK:M01:S050:HAS_DEVATA:VHP:"
        f"{candidate.parser_version}"
    )


def test_candidates_are_read_from_deferred_qa_warnings() -> None:
    issue = QAIssue(
        issue_id=uuid_for_urn("urn:vedagraph:test:issue"),
        check_id="deferred_metadata_range",
        severity=QASeverity.WARNING,
        message="deferred",
        entity_id="VG:RV:SAK:M01:S022",
        details={"predicate": "HAS_DEVATA", "value": RV_1_22_DEVATA, "source_id": "VHP"},
    )
    other = issue.model_copy(update={"check_id": "sequence_gaps"})
    candidates = candidates_from_qa([issue, other])
    assert len(candidates) == 1
    assert candidates[0].subject_id == "VG:RV:SAK:M01:S022"


def test_candidates_are_read_from_source_assertions_and_ignore_other_predicates() -> None:
    def assertion(predicate: str, value: str) -> SourceAssertion:
        return SourceAssertion(
            assertion_id=uuid_for_urn(f"urn:vedagraph:test:{predicate}:{value}"),
            subject_id="VG:RV:SAK:M01:S050",
            predicate=predicate,
            value=value,
            source_id="VHP",
            source_locator="RV 1.50 VHP page",
            status=AssertionStatus.UNREVIEWED,
        )

    candidates = candidates_from_assertions(
        [
            assertion("HAS_CHANDAS", RV_1_50_CHANDAS),
            assertion("REPORTED_MANTRA_COUNT", "13"),
            assertion("SANSKRIT_TEXT", "agnim"),
        ]
    )
    assert [item.predicate for item in candidates] == [MetadataPredicate.HAS_CHANDAS]


def test_review_report_states_that_nothing_was_promoted(tmp_path: Path) -> None:
    candidates = [
        parse_metadata_value(
            subject_id="VG:RV:SAK:M01:S164",
            predicate=MetadataPredicate.HAS_CHANDAS,
            value=RV_1_164_CHANDAS,
            source_id="VHP",
            source_locator="RV 1.164 VHP page",
        ),
        parse_metadata_value(
            subject_id="VG:RV:SAK:M01:S050",
            predicate=MetadataPredicate.HAS_DEVATA,
            value=RV_1_50_DEVATA,
            source_id="VHP",
            source_locator="RV 1.50 VHP page",
        ),
    ]
    report = render_review(candidates)
    assert "AMBIGUOUS" in report
    assert "HALF_VERSE" in report
    assert "nothing has been promoted to" in report
    assert RV_1_164_CHANDAS in report
    path = write_review(candidates, tmp_path / "review.md")
    assert path.read_text(encoding="utf-8") == report


def test_the_committable_review_withholds_permission_required_source_text(
    tmp_path: Path,
) -> None:
    candidates = [
        parse_metadata_value(
            subject_id="VG:RV:SAK:M01:S050",
            predicate=MetadataPredicate.HAS_DEVATA,
            value=RV_1_50_DEVATA,
            source_id="VHP",
            source_locator="RV 1.50 VHP page",
        )
    ]
    redacted = render_review(candidates, redact_source_text=True)
    assert RV_1_50_DEVATA not in redacted
    assert "सूर्यः" not in redacted
    # Everything the parser produced still has to be reviewable.
    assert "HALF_VERSE" in redacted
    assert "PARTIALLY_PARSED" in redacted
    assert "VG:RV:SAK:M01:S050" in redacted
    assert "withheld" in redacted
    path = write_review(candidates, tmp_path / "redacted.md", redact_source_text=True)
    assert path.read_text(encoding="utf-8") == redacted
