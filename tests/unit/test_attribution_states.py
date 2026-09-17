"""The attribution census's state vocabulary, and the one inversion that must be impossible.

``SOURCE_ASSERTS_UNRESOLVED_OBJECT`` was added so the graph can say *the source was read,
it states a value at this granularity, and we could not resolve that value to an identity*.
Before it existed, 150 verse-dimension pairs said ``ASSESSED_SOURCE_ABSENT`` -- "a source
was consulted and it states nothing" -- while Whitney's printed bracket stated a verse-level
value this repository holds in staging and withheld under OWNER_DECISIONS.md sections 20
and 25.

The danger is a one-line edit. ``ABSENCE_STATES`` sits directly beneath ``DECLARED_STATES``
in the same module, and adding the new name to both looks like thoroughness. It would demand
a reason code explaining why the source is silent about a verse it demonstrably speaks
about, and the importer would then raise on every corrected row -- or worse, be fed a
manufactured reason code to make it pass. That is the exact inversion the state exists to
correct, so it is tested rather than left to the comment beside it.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
MODULE_PATH = PROJECT_ROOT / "scripts" / "attribution_import.py"

UNRESOLVED = "SOURCE_ASSERTS_UNRESOLVED_OBJECT"


@pytest.fixture(scope="module")
def attribution_import():
    spec = importlib.util.spec_from_file_location("attribution_import", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_unresolved_object_state_is_declared(attribution_import) -> None:
    """Without this the importer raises UndeclaredState on all 150 corrected rows."""
    assert UNRESOLVED in attribution_import.DECLARED_STATES


def test_the_unresolved_object_state_is_not_an_absence(attribution_import) -> None:
    """BAD -> FAIL. The one-line edit that would invert the correction's meaning.

    A source that states a value is not a source that is silent. If this name ever appears
    in ABSENCE_STATES, every row carrying it is required to explain an absence it does not
    claim.
    """
    assert UNRESOLVED not in attribution_import.ABSENCE_STATES, (
        "SOURCE_ASSERTS_UNRESOLVED_OBJECT means the source SPOKE and we could not resolve "
        "what it said. Putting it in ABSENCE_STATES asserts the opposite and demands a "
        "reason code for a silence that is not there."
    )


def test_every_absence_state_is_declared(attribution_import) -> None:
    """ABSENCE_STATES must be a subset, or the importer can require a reason for a state
    it would also reject as undeclared."""
    assert attribution_import.ABSENCE_STATES <= attribution_import.DECLARED_STATES


def test_the_absence_states_are_exactly_the_two_that_mean_absence(attribution_import) -> None:
    """Pinned as a set, not a membership check.

    A membership check passes while a sixth state is quietly added; this fails, which is the
    point -- a new absence state is a decision about what a silence means and should not be
    able to arrive as a diff nobody reads.
    """
    assert attribution_import.ABSENCE_STATES == frozenset(
        {"ASSESSED_SOURCE_ABSENT", "NOT_APPLICABLE_AT_THIS_GRANULARITY"}
    )


def test_a_present_state_is_never_an_absence_state(attribution_import) -> None:
    """The three states that assert the source gave us something, kept out of the absences."""
    present = {"SOURCE_EXPLICIT_PRESENT", "DERIVED_PRESENT", UNRESOLVED}
    assert present <= attribution_import.DECLARED_STATES
    assert not (present & attribution_import.ABSENCE_STATES)


def test_an_undeclared_state_still_raises(attribution_import) -> None:
    """GOOD -> PASS on the guard the new entry had to pass through.

    Adding a name to DECLARED_STATES must not soften the check for the next one.
    """
    assert "SOURCE_SHRUGGED" not in attribution_import.DECLARED_STATES
    assert issubclass(attribution_import.UndeclaredState, RuntimeError)
