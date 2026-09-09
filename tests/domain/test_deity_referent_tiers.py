"""The three-way referent-certainty split, and the default ambiguity policy it licenses.

Everything here runs offline. The rules are a pure function of properties already on a
``MENTIONS_DEVATA`` edge, and the measurement is a join against the committed gold set
``data/gold/theonym_mention_gold_v1.jsonl`` -- so the number this file asserts is
reproducible on a machine with no Neo4j, which is the only kind of precision claim this
project accepts. The gold snapshot carries ``morphological_role``,
``attribution_support`` and the pre-split ``referent_certainty`` for 378 of its 379
asserted rows, which is exactly the input the split consumes.

Two of these tests exist because of specific past failures rather than for coverage:

* :func:`test_the_probable_bucket_is_audited_per_alias_not_on_average` -- an audit of this
  graph once sampled rows and reported 97%+ correct while a single alias was 82.9% wrong.
  A bucket-level average is therefore not an acceptable assertion on its own.
* :func:`test_the_default_policy_excludes_the_vak_bucket` -- on the gold sample every
  asserted mention of ``VG:DEVATA:VAK`` is the common noun "speech". The default filter is
  the only thing between that deity and a confidently wrong answer, so it is pinned rather
  than left to a caller's discretion.
"""

from __future__ import annotations

import collections
import json
import math
import pathlib
from typing import Any

import pytest

from vedagraph.domain.theonyms import (
    AMBIGUOUS,
    BASIS_ADDRESS,
    BASIS_ANUKRAMANI,
    BASIS_CERTAIN,
    BASIS_COMPOUND_HOLD,
    BASIS_DEDICATION,
    BASIS_IDENTITY_ONLY,
    CERTAIN,
    DEFAULT_REFERENT_TIERS,
    EXPLORATORY_REFERENT_TIERS,
    PROBABLE,
    REFERENT_TIERS,
    STRICT_REFERENT_TIERS,
    TheonymRegistryError,
    referent_tiers_for_mode,
    refine_referent_certainty,
)

GOLD_PATH = (
    pathlib.Path(__file__).resolve().parents[2] / "data" / "gold" / "theonym_mention_gold_v1.jsonl"
)

#: The floor the ``PROBABLE`` tier has to clear for the default policy to be honest. Set
#: at the level of the ``CERTAIN`` tier's own measured precision rather than at a round
#: number, because the whole claim of the default policy is that adding ``PROBABLE`` to
#: ``CERTAIN`` does not dilute it.
PROBABLE_PRECISION_FLOOR = 0.90

#: What the split has to *achieve*: the bucket left behind must be measurably worse, or
#: the split has moved rows without separating anything.
AMBIGUOUS_PRECISION_CEILING = 0.75


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------


def test_certain_passes_through_untouched() -> None:
    """A row :func:`_grade` settled on observed morphology is never relitigated."""
    for roles in ((), ("NOM",), ("COMPOUND_INITIAL",), ("VOCATIVE",)):
        for support in (True, False):
            assert refine_referent_certainty(CERTAIN, roles, support) == (
                CERTAIN,
                BASIS_CERTAIN,
            )


def test_anukramani_corroboration_promotes_but_only_to_probable() -> None:
    """A second source agreeing about the passage is not a statement about the word."""
    assert refine_referent_certainty(AMBIGUOUS, ("NOM",), True) == (
        PROBABLE,
        BASIS_ANUKRAMANI,
    )


@pytest.mark.parametrize("role", ["VOCATIVE", "VOC"])
def test_address_morphology_promotes_on_either_role_spelling(role: str) -> None:
    """The two paths label roles differently and both spellings have to be honoured.

    The Rigvedic path carries the Zurich annotation's case abbreviations and the surface
    paths carry the registry's own words. A rule that knew only one spelling would silently
    apply to one corpus and not the other, which is the shape of defect this layer's
    per-path reporting exists to prevent.
    """
    assert refine_referent_certainty(AMBIGUOUS, (role,), False) == (
        PROBABLE,
        BASIS_ADDRESS,
    )


@pytest.mark.parametrize("role", ["DATIVE", "DAT"])
def test_dedication_morphology_promotes_on_either_role_spelling(role: str) -> None:
    assert refine_referent_certainty(AMBIGUOUS, (role,), False) == (
        PROBABLE,
        BASIS_DEDICATION,
    )


def test_lemma_or_string_identity_alone_never_promotes() -> None:
    """The evidence that created the ambiguity cannot be the evidence that resolves it."""
    for role in (
        "NOM",
        "ACC",
        "GEN",
        "INS",
        "LOC",
        "ABL",
        "NOMINATIVE",
        "ACCUSATIVE",
        "GENITIVE",
        "SANDHI_FUSED",
        "PLURAL_OBLIQUE",
        "UNKNOWN",
    ):
        assert refine_referent_certainty(AMBIGUOUS, (role,), False) == (
            AMBIGUOUS,
            BASIS_IDENTITY_ONLY,
        )


def test_the_compound_veto_outranks_every_promotion_rule() -> None:
    """A compound need not denote its members, so nothing inside one is promoted.

    ``soma-prsthaya ... agnaye`` (VSM 20.78) is an offering to Agni described as
    "soma-backed"; the Soma edge there is a compound member and the Anukramani ascription
    of that passage would otherwise promote it. Order matters, so it is pinned.
    """
    for role in ("COMPOUND_INITIAL", "COMPOUND_FINAL"):
        assert refine_referent_certainty(AMBIGUOUS, (role, "VOCATIVE"), True) == (
            AMBIGUOUS,
            BASIS_COMPOUND_HOLD,
        )


# ---------------------------------------------------------------------------
# The policy contract
# ---------------------------------------------------------------------------


def test_the_three_tiers_are_ordered_and_complete() -> None:
    assert REFERENT_TIERS == (CERTAIN, PROBABLE, AMBIGUOUS)
    assert STRICT_REFERENT_TIERS < DEFAULT_REFERENT_TIERS < EXPLORATORY_REFERENT_TIERS
    assert AMBIGUOUS not in DEFAULT_REFERENT_TIERS
    assert AMBIGUOUS in EXPLORATORY_REFERENT_TIERS


def test_an_unknown_mode_raises_rather_than_widening_the_filter() -> None:
    """A typo that silently widened the filter would put an ambiguous row in an answer."""
    assert referent_tiers_for_mode("default") == DEFAULT_REFERENT_TIERS
    assert referent_tiers_for_mode("strict") == STRICT_REFERENT_TIERS
    assert referent_tiers_for_mode("exploratory") == EXPLORATORY_REFERENT_TIERS
    with pytest.raises(TheonymRegistryError):
        referent_tiers_for_mode("Default")


# ---------------------------------------------------------------------------
# The measurement
# ---------------------------------------------------------------------------


def _gold_rows() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in GOLD_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _split_gold() -> dict[str, list[dict[str, Any]]]:
    """Every asserted, scorable gold row bucketed by the tier the split gives it.

    The gold snapshot stores one ``morphological_role`` per row rather than the edge's
    tuple, which is what the row's own evidence was; the split reads a role *set*, so a
    one-element tuple is the faithful reconstruction and not a simplification.
    """
    buckets: dict[str, list[dict[str, Any]]] = {tier: [] for tier in REFERENT_TIERS}
    for row in _gold_rows():
        if not row["graph_asserts"] or row["gold_label"] not in ("MENTION", "NO_MENTION"):
            continue
        if not row["referent_certainty"]:
            # The 13 rows the B1 fix moved carry no frozen edge properties. Excluded and
            # counted rather than defaulted, because defaulting them would let a guess
            # into a precision figure.
            continue
        tier, _ = refine_referent_certainty(
            row["referent_certainty"],
            (row["morphological_role"],) if row["morphological_role"] else (),
            bool(row["attribution_support"]),
        )
        buckets[tier].append(row)
    return buckets


def _precision(rows: list[dict[str, Any]]) -> tuple[int, int, float]:
    n = len(rows)
    hits = sum(1 for row in rows if row["gold_label"] == "MENTION")
    return hits, n, hits / n if n else float("nan")


def _wilson_low(hits: int, n: int, z: float = 1.96) -> float:
    if not n:
        return float("nan")
    p = hits / n
    denominator = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denominator


def test_the_split_actually_separates() -> None:
    """PROBABLE clears the floor and AMBIGUOUS falls below the ceiling.

    Without both halves this assertion would pass on a split that moved rows around
    without telling a consumer anything, which is the failure a single headline number
    hides.
    """
    buckets = _split_gold()
    probable = _precision(buckets[PROBABLE])
    ambiguous = _precision(buckets[AMBIGUOUS])
    assert probable[1] >= 40, f"too few PROBABLE gold rows to make a claim: {probable}"
    assert probable[2] >= PROBABLE_PRECISION_FLOOR, probable
    assert ambiguous[2] <= AMBIGUOUS_PRECISION_CEILING, ambiguous
    # The default scope must not be diluted by the promotion.
    default = _precision(buckets[CERTAIN] + buckets[PROBABLE])
    assert default[2] >= 0.95, default


def test_probable_is_not_claimed_more_precisely_than_the_gold_set_supports() -> None:
    """The claim is the Wilson lower bound, not the point estimate.

    On roughly 50 rows the point estimate carries an interval about eight points wide, so
    a report quoting 0.98 as though it were 0.98 +/- nothing would be overclaiming. This
    test pins the honest form of the claim: the lower bound clears the floor.
    """
    hits, n, _ = _precision(_split_gold()[PROBABLE])
    assert _wilson_low(hits, n) >= 0.85, (hits, n, _wilson_low(hits, n))


def test_the_probable_bucket_is_audited_per_alias_not_on_average() -> None:
    """Every alias with enough rows to be scored has to hold up on its own.

    This graph has been embarrassed by an audit that sampled rows and reported 97%+ while
    one alias was 82.9% wrong, so the average is not the assertion. Aliases below the
    support threshold are unmeasured, not vindicated, and the report names them.
    """
    by_alias: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in _split_gold()[PROBABLE]:
        by_alias[f"{row['devata_id']}|{row['surface_form']}"].append(row)
    scorable = {alias: _precision(rows) for alias, rows in by_alias.items() if len(rows) >= 5}
    assert scorable, "no alias reached the support threshold"
    worst = min(scorable.items(), key=lambda item: item[1][2])
    assert worst[1][2] >= PROBABLE_PRECISION_FLOOR, f"worst alias {worst}"


def test_the_default_policy_excludes_the_vak_bucket() -> None:
    """Not one asserted Vac mention in the gold set is the goddess.

    ``VG:DEVATA:VAK`` is asserted on 302 passages and scores 0 true positives on 10 gold
    rows. The tier a row lands in is what decides whether a user sees that, so the
    property under test is that the default scope keeps essentially all of it out --
    stated as a bound on how many Vac rows the default admits, not as a hope.
    """
    buckets = _split_gold()
    admitted = [
        row
        for tier in DEFAULT_REFERENT_TIERS
        for row in buckets[tier]
        if row["devata_id"] == "VG:DEVATA:VAK"
    ]
    excluded = [row for row in buckets[AMBIGUOUS] if row["devata_id"] == "VG:DEVATA:VAK"]
    assert excluded, "the gold set no longer contains Vac rows; this test needs rewriting"
    assert not admitted, f"the default scope admits Vac rows: {admitted}"


def test_every_asserted_gold_row_lands_in_exactly_one_tier() -> None:
    """No row is dropped and none is double-counted, so the three figures add up.

    Every deity-profile answer has to be able to report certain, probable and ambiguous as
    three separate numbers whose sum is the total. A split that lost rows would make the
    three add to less than the mention count and hide ambiguity by omission.
    """
    buckets = _split_gold()
    sizes = {tier: len(rows) for tier, rows in buckets.items()}
    total = sum(sizes.values())
    scorable = [
        row
        for row in _gold_rows()
        if row["graph_asserts"]
        and row["gold_label"] in ("MENTION", "NO_MENTION")
        and row["referent_certainty"]
    ]
    assert total == len(scorable)
    ids = [row["row_id"] for rows in buckets.values() for row in rows]
    assert len(ids) == len(set(ids))
