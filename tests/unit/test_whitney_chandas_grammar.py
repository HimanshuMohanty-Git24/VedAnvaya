"""The Whitney metre-name grammar, and proof the builder cannot re-emit the 33.

Wave 4 Phase 3. The generator -- ``scripts/build_atharvaveda_anukramani.py`` -- named this as
a known residual in its own docstring and shipped it: *"17 HAS_CHANDAS values are whole
un-parsed bracket fragments rather than metre names: they still contain a colon."* Measured
at the source, the population was 33 rows, matching the 33 canonical edges M9 withdrew, scope
for scope.

**Root cause, one bracket.** AVS 5.3 prints a per-verse *devatā* list after the first colon,
and its final segment carries the per-verse devatā, then the hymn's metre, then that metre's
own exception, with no semicolon between them:

    8, 11. āindrī. trāiṣṭubham: 2. bhurij

The tail loop splits on ``;`` alone, so ``[^;]+`` takes all three, ``METRE_STEM`` matches the
middle one, and the compound is emitted as the metre of verses 8 and 11.

**The fixture is the point of this file.** A parser fix is only worth anything if the cases it
was written against are pinned, and — more importantly — if the cases it must NOT reject are
pinned too. Every valid negative here is a real metre name from the registry carrying
numeric-looking structural qualifiers (``3-av.``, ``6-p.``, ``2-p.``), which a generic
digit-detection rule would destroy. Those are the assertions that stop this fix from being
broadened into the 17/28/39 heuristics the owner barred.
"""

from __future__ import annotations

import importlib
import json
import pathlib
import re

import pytest

builder = importlib.import_module("scripts.build_atharvaveda_anukramani")

CANONICAL = pathlib.Path(
    "data/canonical/atharvaveda_saunaka_digital_working_v1/traditional_metadata.jsonl"
)
REGISTRY = pathlib.Path("data/registry/chandas_av.yaml")

#: The 33 malformed values the builder used to emit, taken verbatim from the pre-fix
#: artifact. Deduplicated to distinct strings -- several covered more than one verse address.
MALFORMED_VALUES: tuple[str, ...] = (
    "āindrī. trāiṣṭubham: 2. bhurij",
    "rāudryāu: 2. triṣṭubh",
    "3-p. pipīlikamadhyā purauṣṇih: 1-11. ekāvasāna",
    "brāhmaṇaspatyā. ānuṣṭubham: 4. virāṭprastārapan̄kti",
    "bhāumī. ānuṣṭubham: 1, 3. pathyāpan̄kti",
    "sarvātmakaṁ rudram. trāiṣṭubham: 2. anuṣṭubh",
    "āindryas. ānuṣṭubham: 2. 3-av. 6-p. jagatī",
    "3-av. 6-p. virāḍ atijagatī: 24. 5-p. virāḍ atijagatī",
    "varuṇastuti. trāiṣṭubham: 1. gāyatrī",
    "mantroktabahudevatyam. 1. pathyābṛhatī",
    "mantroktadevatye. jagatyāu. 3. āindrī. anuṣṭubh",
    "5. 2-p. āsurī gāyatrī",
    "2. bhurij",
    "sāvitrī. 1. 1-p. brāhmy anuṣṭubh",
    "sāurye. 1. ārcy anuṣṭubh",
    "mantroktadevatyam. 1, 2. anuṣṭubh",
    "6. anuṣṭubh",
    "5. jagatī",
    "7. 5-p. pathyāpan̄kti",
)

#: Real metre names that MUST survive. Every one carries something a naive numeric or
#: punctuation rule would trip on: a hyphenated avasāna or pāda count, a comma, or a
#: multi-word qualifier chain. Drawn from the live registry, not invented.
VALID_METRE_NAMES: tuple[str, ...] = (
    "anuṣṭubh",
    "triṣṭubh",
    "jagatī",
    "pathyāpan̄kti",
    "upariṣṭādbṛhatī",
    "bhurij",
    "3-av. 6-p. dvyuṣṇiggarbhā jagatī",
    "1-av. 2-p. nicṛd ārcy anuṣṭubh",
    "1-av. 2-p. prājāpatyā bhurig anuṣṭubh",
    "2-p. virāḍgāyatrī",
    "4-p. atiçakvarī",
    "6-p. jagatī",
    "3-p. bhurin̄ mahābṛhatī",
    "5-p. kakummatīgarbhā ’ṣṭi",  # noqa: RUF001 - the edition's own apostrophe
    "ārṣī gāyatrī",
    "prastārapan̄kti",
)


@pytest.mark.parametrize("value", MALFORMED_VALUES)
def test_every_known_malformed_value_is_refused(value: str) -> None:
    """The 33-case regression. Each returns a reason naming which token fired."""
    reason = builder.compound_metre_statement(value)
    assert reason, f"{value!r} must be refused as a compound statement"
    assert reason in {
        "colon_separates_statement_from_per_verse_exceptions",
        "embedded_verse_address",
    }


@pytest.mark.parametrize("value", VALID_METRE_NAMES)
def test_every_valid_metre_name_survives(value: str) -> None:
    """The valid-negative regression, and the reason the rule stays narrow.

    ``3-av. 6-p. dvyuṣṇiggarbhā jagatī`` is one metre name with two structural qualifiers.
    Generic digit detection would refuse it, and refusing 500 good metres to catch 33 bad
    ones is the failure mode the owner explicitly barred.
    """
    assert builder.compound_metre_statement(value) == "", (
        f"{value!r} is a metre name and must not be refused"
    )


def test_the_criterion_uses_only_the_two_justified_tokens() -> None:
    """Boundary cases around the colon and the verse address, stated explicitly.

    A digit alone is not enough; a digit followed by a hyphen is a qualifier; a digit
    followed by a period and a space is a verse address. That last distinction is the whole
    rule, and it is asserted here rather than left to the parametrised lists.
    """
    assert builder.compound_metre_statement("2-p. gāyatrī") == ""
    assert builder.compound_metre_statement("gāyatrī 2") == ""
    assert builder.compound_metre_statement("virāṭ 3-av.") == ""
    assert builder.compound_metre_statement("2. gāyatrī") == "embedded_verse_address"
    assert (
        builder.compound_metre_statement("gāyatrī: 2. bhurij")
        == "colon_separates_statement_from_per_verse_exceptions"
    )
    # The colon is checked first, so a value carrying both reports the colon. Asserted so
    # the precedence is a decision rather than an accident of ordering.
    assert (
        builder.compound_metre_statement("a: 2. b")
        == "colon_separates_statement_from_per_verse_exceptions"
    )


def test_the_regenerated_artifact_carries_no_compound_metre_value() -> None:
    """The end-to-end proof: the corrected builder's own output, read from disk.

    A unit test on the predicate could pass while the builder called it in the wrong place,
    or not at all. This reads the artifact the builder actually wrote.
    """
    if not CANONICAL.exists():
        pytest.skip("canonical AV artifact not present in this checkout")
    rows = [
        json.loads(line)
        for line in CANONICAL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    chandas = [r for r in rows if r.get("predicate") == "HAS_CHANDAS"]
    assert chandas, "no HAS_CHANDAS rows found, so this test proves nothing"
    offenders = [
        str(r["value"]) for r in chandas if builder.compound_metre_statement(str(r["value"]))
    ]
    assert not offenders, (
        f"{len(offenders)} compound metre value(s) still emitted: {offenders[:3]}"
    )


def test_the_registry_no_longer_mints_an_identity_from_a_compound() -> None:
    """The registry is downstream of the artifact, so it is checked separately.

    541 entities before the fix, 513 after. The 28 that went are the retired identities M10
    marked internal -- they remain in the graph holding their literal, and are absent from
    the registry the corrected builder produces.
    """
    if not REGISTRY.exists():
        pytest.skip("AV chandas registry not present in this checkout")
    import yaml

    entities = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["entities"]
    offenders = [
        str(e["preferred_label"])
        for e in entities
        if builder.compound_metre_statement(str(e["preferred_label"]))
    ]
    assert not offenders, (
        f"{len(offenders)} compound label(s) still in the registry: {offenders[:3]}"
    )


def test_the_malformed_fixture_is_not_silently_empty() -> None:
    """A fixture that drifts to empty turns this whole file into a no-op.

    The count is pinned, and the strings are checked against the criterion's own two tokens
    so a typo that made one of them innocuous would fail here rather than quietly reduce
    coverage.
    """
    assert len(MALFORMED_VALUES) == 19, "distinct malformed strings behind the 33 rows"
    assert len(VALID_METRE_NAMES) >= 16
    verse_address = re.compile(r"(?<![0-9a-zA-Z-])\d{1,2}\.\s")
    for value in MALFORMED_VALUES:
        assert ":" in value or verse_address.search(value), (
            f"{value!r} is in the malformed fixture but carries neither justified token"
        )
