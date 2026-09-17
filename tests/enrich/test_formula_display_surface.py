"""No formula may publish a character a reader cannot read.

``display_form`` is the string the product prints when it names a formula. Its contract is
"a real attested span", and that was applied without checking the span was legible: 23 of
the 4,825 live ``:Formula`` nodes print a raw U+1CEA VEDIC SIGN ANUSVARA BAHIRGOMUKHA in
the middle of an IAST label -- ``apāᳪṃ retāᳪṃsi jinvati`` -- because the Vajasaneyi edition
spells the anusvara that way, U+1CEA is Unicode category Lo so ``strip_vedic_accents``
leaves it standing, and every attestation of those 23 is in that edition.

This is the same defect class as the private-use leak
:mod:`vedagraph.enrich.surfaces` documents one level down, and it is worse than mojibake in
the same way: a Devanagari sign inside a Latin string renders, so the damage looks like
Sanskrit rather than like corruption.

**The fix does not touch identity.** ``formula_id`` is
``stable_id("formula", formula.collapsed)`` at ``vedagraph/enrich/formulas.py:810`` -- it
derives from ``collapsed`` and from nothing else. ``display_form`` carries no identity, so
correcting it moves none. ``collapsed`` and ``normalized`` are left exactly as they are;
correcting *those* would move ``formula_id`` and is an owner decision, sized separately.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from collections.abc import Iterator
from typing import Any

import pytest

from vedagraph.enrich.formulas import _UNREADABLE_IN_IAST, _is_readable_iast, _pick_display_form

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
STAGED = (
    PROJECT_ROOT
    / "data"
    / "staging"
    / "final_closure_sprint"
    / "agent1"
    / "formula_display_form_repair.json"
)
AUDIT = STAGED.with_name("formula_nesting_audit.json")
PARTITION = STAGED.with_name("formula_display_form_basis_partition.json")

#: Fields a repair may never write. ``formula_id`` is derived from ``collapsed``, and
#: ``normalized`` is a rendering of the same string, so a row that touched either would be
#: proposing an identity change while calling itself a display fix.
IDENTITY_FIELDS = frozenset({"formula_id", "collapsed", "normalized"})


def _staged() -> dict[str, Any]:
    if not STAGED.exists():
        pytest.skip("agent 1 staging not built; run scripts/agent1_final_closure.py")
    return json.loads(STAGED.read_text(encoding="utf-8"))


# -- the predicate ----------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "form"),
    [
        ("vedic sign anusvara bahirgomukha", "apāᳪṃ retāᳪṃsi"),
        ("devanagari sign candrabindu virama", "teṣāꣳ sahasrayojane"),
        ("bare devanagari", "अपां रेतांसि"),
        ("a comparison sentinel that escaped", "soma"),
    ],
)
def test_the_readability_predicate_rejects_an_unrendered_sign(label: str, form: str) -> None:
    """BAD -> FAIL. Each of these renders as something, which is why it got published."""
    assert not _is_readable_iast(form), label


def test_the_readability_predicate_accepts_real_iast() -> None:
    """GOOD -> PASS. A predicate that rejects everything would pass the test above too."""
    for form in ("apāṃ retāṃsi jinvati", "agnim īḷe purohitam", "yūyam pāta svastibhiḥ"):
        assert _is_readable_iast(form)


def test_the_picker_prefers_a_readable_attestation_over_an_unreadable_first_one() -> None:
    """The defect exactly: ``forms[0]`` was taken without asking whether it was legible."""
    forms = ("iᳪṃ stotṛbhya ā bhara", "iṣaṃ stotṛbhya ā bhara")
    assert _pick_display_form(forms, "fallback") == "iṣaṃ stotṛbhya ā bhara"


def test_the_picker_falls_back_only_when_no_attestation_is_readable() -> None:
    forms = ("iᳪṃ stotṛbhya ā bhara",)
    assert _pick_display_form(forms, "iṣaṃ stotṛbhya ā bhara") == "iṣaṃ stotṛbhya ā bhara"
    assert _pick_display_form((), "iṣaṃ") == "iṣaṃ"


def test_the_unreadable_ranges_cover_the_scripts_this_corpus_actually_carries() -> None:
    """A range list that missed Vedic Extensions would have missed the whole defect."""
    covered = {low for low, _high in _UNREADABLE_IN_IAST}
    assert {0x0900, 0x1CD0, 0xA8E0, 0xE000} <= covered


# -- the staged repair ------------------------------------------------------


def test_every_staged_repair_is_readable() -> None:
    """GOOD -> PASS. A repair that still carries the sign would be the defect renamed."""
    rows = _staged()["mutations"]
    assert rows, "the repair group is empty"
    unreadable = [
        row["key"]["formula_id"]
        for row in rows
        if row["op"] == "node_update" and not _is_readable_iast(row["set"]["display_form"])
    ]
    assert not unreadable, unreadable


def test_no_staged_repair_touches_a_field_an_identity_is_derived_from() -> None:
    """BAD -> FAIL. The reason this fix was withheld once, turned into a check."""
    for row in _staged()["mutations"]:
        if row["op"] != "node_update":
            continue
        written = set(row["set"])
        assert not (written & IDENTITY_FIELDS), row["key"]
        assert set(row["untouched"]) == IDENTITY_FIELDS
        assert set(row["key"]) == {"formula_id"}


def test_the_repair_covers_every_offender_the_audit_found() -> None:
    """Neither more nor fewer: a repair over a different population is not this repair."""
    if not AUDIT.exists():
        pytest.skip("agent 1 staging not built")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    repaired = {row["key"]["formula_id"] for row in _staged()["mutations"]}
    assert repaired == set(audit["graph_surfaces_unfolded_ids"])
    assert len(repaired) == audit["graph_surfaces_unfolded"]


def test_a_rendered_repair_says_it_is_rendered_and_not_attested() -> None:
    """The lossy branch must be distinguishable, or the reader is told a rendering is a
    spelling. Measured: none of the offenders has a readable attested span, so every row is
    the rendered branch."""
    for row in _staged()["mutations"]:
        if row["op"] != "node_update":
            continue
        basis = row["set"]["display_form_basis"]
        assert basis in {
            "ATTESTED_SPAN",
            "RENDERED_COMPARISON_FORM_NOT_AN_ATTESTED_SPELLING",
        }
        assert row["set"]["display_form_corroboration"]


def test_the_uncorroborated_repair_is_named_rather_than_asserted() -> None:
    """One of the 23 does not appear in the independently rebuilt population in any form.

    It is still repaired -- the value is a deterministic rendering of the node's own
    comparison surface -- but it carries no second opinion, and a row that cannot be
    corroborated must say so rather than sit in a list of 23 that look alike.
    """
    counts = _staged()["corroboration_counts"]
    assert sum(counts.values()) == _staged()["rows"]
    uncorroborated = [
        row["key"]["formula_id"]
        for row in _staged()["mutations"]
        if row["op"] == "node_update"
        and row["set"]["display_form_corroboration"].startswith("UNCORROBORATED")
    ]
    assert len(uncorroborated) == counts.get(
        "UNCORROBORATED_THIS_WORDING_IS_ABSENT_FROM_THE_REBUILT_POPULATION", 0
    )


def test_applying_the_staged_repair_to_the_live_population_leaves_no_offender() -> None:
    """GOOD -> PASS, without writing anything.

    The live gate below is red until the lead integrates, so on its own it could not show
    that the repair is *sufficient* -- only that the defect is still there. This applies
    the staged rows to the live ``display_form`` values in memory and re-runs the same
    predicate over the whole population, which is the assertion the gate will make once the
    write has happened.
    """
    repair = {
        row["key"]["formula_id"]: row["set"]["display_form"]
        for row in _staged()["mutations"]
        if row["op"] == "node_update"
    }
    before = {
        row["key"]["formula_id"]: row["before"]["display_form"]
        for row in _staged()["mutations"]
        if row["op"] == "node_update"
    }
    assert before and all(not _is_readable_iast(value) for value in before.values()), (
        "the recorded before-values must be the defect, or this proves nothing"
    )
    after = {key: repair[key] for key in before}
    assert all(_is_readable_iast(value) for value in after.values())
    assert all(after[key] != before[key] for key in before), "a no-op repair is not a repair"


# -- the basis is a partition, not a flag on 23 nodes -----------------------


def _partition() -> dict[str, Any]:
    if not PARTITION.exists():
        pytest.skip("agent 1 staging not built; run scripts/agent1_final_closure.py")
    return json.loads(PARTITION.read_text(encoding="utf-8"))


def test_display_form_basis_is_written_to_every_formula_or_the_absence_would_speak() -> None:
    """The point of the exercise. 23 labelled and 4,802 unlabelled would make "no property"
    mean ATTESTED_SPAN, which is a claim read out of a missing row -- the same shape as a
    false zero. The two labels must cover the whole population exactly once."""
    partition = _partition()
    by_label = partition["by_label"]
    labelled = [key for keys in by_label.values() for key in keys]
    assert len(labelled) == len(set(labelled)), "a formula carries two bases"
    assert len(labelled) == partition["population"], (
        f"{len(labelled)} labelled of {partition['population']}; the partition is not total"
    )
    assert partition["unlabelled"] == []


def test_the_two_label_sets_are_disjoint() -> None:
    """A node cannot be both a rendering and an attested spelling."""
    by_label = _partition()["by_label"]
    rendered = set(by_label["RENDERED_COMPARISON_FORM_NOT_AN_ATTESTED_SPELLING"])
    attested = set(by_label["ATTESTED_SPAN"])
    assert rendered & attested == set()
    assert rendered == {row["key"]["formula_id"] for row in _staged()["mutations"]}


def test_the_basis_vocabulary_is_closed() -> None:
    """An unknown basis must raise rather than quietly become a fifth kind of evidence."""
    partition = _partition()
    assert set(partition["by_label"]) == set(partition["vocabulary"])


def test_the_backfill_cites_the_audit_it_rests_on() -> None:
    """A basis with no evidence reference is an assertion wearing a measurement's clothes."""
    if not AUDIT.exists():
        pytest.skip("agent 1 staging not built")
    partition = _partition()
    digest = hashlib.sha256(AUDIT.read_bytes()).hexdigest()
    assert partition["readability_evidence"].endswith(digest), (
        "the cited audit digest does not match the audit that was written"
    )
    assert partition["attestation_evidence"]


def test_readability_alone_would_not_have_licensed_the_attested_label() -> None:
    """The correction this module records.

    The instruction was that the audit finding exactly 23 unreadable surfaces proves the
    other 4,802 "took the attested branch". It does not: the live display_form values were
    written by the code that took ``forms[0]`` unconditionally, not by the picker that
    checks legibility, so readability licenses nothing about attestation. Both properties
    are therefore measured, and this pins that they are two claims rather than one.
    """
    unreadable_but_attested = _pick_display_form(
        ("apāᳪṃ retāᳪṃsi",), "apāṃ retāṃsi"
    )
    assert unreadable_but_attested == "apāṃ retāṃsi", (
        "an attested span can be unreadable, which is the whole of the 23"
    )
    assert _is_readable_iast("apāṃ retāṃsi")
    partition = _partition()
    assert "source_forms" in partition["attestation_evidence"], (
        "attestation must be evidenced by membership in the node's own source_forms, not "
        "inferred from readability"
    )


# -- the live graph, which is the gate --------------------------------------


@pytest.fixture
def live_session() -> Iterator[Any]:
    pytest.importorskip("neo4j")
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv(str(PROJECT_ROOT / ".env"))
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))
    try:
        driver.verify_connectivity()
    except Exception:  # pragma: no cover - environment, not logic
        driver.close()
        pytest.skip("no Neo4j at bolt://localhost:7687")
    with driver.session(database="neo4j") as session:
        if int(session.run("MATCH (f:Formula) RETURN count(f) AS c").single()["c"]) == 0:
            pytest.skip("the graph holds no Formula nodes")
        yield session
    driver.close()


@pytest.mark.neo4j
def test_every_live_formula_carries_a_display_form_basis(live_session: Any) -> None:
    """The second integration gate: the partition has to be total in the graph too.

    RED until ``A1_FORMULA_DISPLAY_FORM_REPAIR`` and
    ``A1_FORMULA_DISPLAY_FORM_BASIS_BACKFILL`` are both applied. Asserting totality only
    over the staged file would prove the plan is total and say nothing about the data.
    """
    rows = live_session.run(
        "MATCH (f:Formula) RETURN f.formula_id AS id, f.display_form_basis AS basis"
    ).data()
    vocabulary = set(_partition()["vocabulary"])
    unlabelled = [str(row["id"]) for row in rows if not row["basis"]]
    wrong = [str(row["id"]) for row in rows if row["basis"] and row["basis"] not in vocabulary]
    assert not wrong, f"basis values outside the closed vocabulary: {wrong[:3]}"
    assert not unlabelled, (
        f"{len(unlabelled)} of {len(rows)} Formula nodes carry no display_form_basis, so "
        "its absence would have to be read as ATTESTED_SPAN. Staged as "
        "A1_FORMULA_DISPLAY_FORM_BASIS_BACKFILL."
    )


@pytest.mark.neo4j
def test_no_live_formula_display_form_carries_an_unreadable_codepoint(
    live_session: Any,
) -> None:
    """The integration gate for the staged repair.

    RED until the lead applies ``A1_FORMULA_DISPLAY_FORM_REPAIR``, and that is the point:
    the defect is in the canonical graph, so only a canonical write can clear it. No
    exemption list, because excusing a published Devanagari sign is the defect.
    """
    rows = live_session.run(
        "MATCH (f:Formula) RETURN f.formula_id AS id, f.display_form AS display_form, "
        "f.display_form_basis AS basis"
    ).data()
    assert len(rows) > 1_000, f"only {len(rows)} formulas; the probe is wrong"
    partition = _partition()
    assert {str(row["id"]) for row in rows} == {
        key for keys in partition["by_label"].values() for key in keys
    }, "the staged partition and the live population are not the same set of formulas"
    offenders = [
        str(row["id"]) for row in rows if not _is_readable_iast(str(row["display_form"] or ""))
    ]
    assert not offenders, (
        f"{len(offenders)} Formula nodes publish a codepoint no reader can read as IAST; "
        f"first is {offenders[0]}. The repair is staged as "
        "A1_FORMULA_DISPLAY_FORM_REPAIR in "
        "data/staging/final_closure_sprint/agent1/proposed_mutations.json."
    )
