import pytest


@pytest.mark.live
def test_live_source_placeholder() -> None:
    pytest.skip("Run bounded live checks manually; CI never crawls external sources.")
