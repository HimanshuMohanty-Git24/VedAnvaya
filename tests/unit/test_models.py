from uuid import uuid4

import pytest
from pydantic import ValidationError

from vedagraph.models import AudioSegment, MetadataScope, SourceAssertion
from vedagraph.models.enums import (
    AlignmentMethod,
    AssertionStatus,
    RightsStatus,
    ScopeType,
)


def test_rights_enum_is_complete() -> None:
    assert {item.value for item in RightsStatus} == {
        "PUBLIC_DOMAIN",
        "CC_BY",
        "CC_BY_SA",
        "CC_BY_NC",
        "CC_BY_NC_SA",
        "APACHE_2_0",
        "PERMISSION_GRANTED",
        "PERMISSION_REQUIRED",
        "RESEARCH_ONLY",
        "REFERENCE_ONLY",
        "EXTERNAL_REFERENCE_ONLY",
        "UNKNOWN",
    }


def test_metadata_range_scope() -> None:
    scope = MetadataScope(
        scope_type=ScopeType.MANTRA_RANGE,
        passage_id=uuid4(),
        start_sequence=1,
        end_sequence=4,
    )
    assert scope.start_sequence == 1
    with pytest.raises(ValidationError):
        MetadataScope(scope_type=ScopeType.MANTRA_RANGE, passage_id=uuid4())


def test_audio_segment_requires_forward_time() -> None:
    with pytest.raises(ValidationError):
        AudioSegment(
            segment_id=uuid4(),
            audio_id=uuid4(),
            passage_id=uuid4(),
            start_ms=2000,
            end_ms=1000,
            alignment_method=AlignmentMethod.ALGORITHMIC,
        )


def test_source_assertion_retains_arbitrary_typed_value() -> None:
    assertion = SourceAssertion(
        assertion_id=uuid4(),
        subject_id="VG:WORK:AV:SAU",
        predicate="REPORTED_UNIT_COUNT",
        value=5987,
        source_id="VEDSEARCH",
        source_locator="homepage",
        status=AssertionStatus.UNREVIEWED,
    )
    assert assertion.value == 5987
