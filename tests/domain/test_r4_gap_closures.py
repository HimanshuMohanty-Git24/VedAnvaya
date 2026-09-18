"""Regression tests for the gaps Release Blocker Closure R4 closed.

Each block names its gap and pins the thing that was wrong, not merely the thing that is
now right. Where a gap was closed by removing a false claim, the test refuses the claim's
asserting form by name -- a count that merely "looks healthy" would pass again the moment
someone reinstated the sentence.

Live tests are gated on ``VEDAGRAPH_LIVE_NEO4J`` and are reported by
``scripts/release_test_accounting.py`` under that gate, so a failure here cannot vanish
from a release report by being skipped.
"""

from __future__ import annotations

import os
import pathlib
import re
from typing import Any

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)


def _driver() -> Any:
    from neo4j import GraphDatabase

    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))


def _scalar(query: str) -> Any:
    driver = _driver()
    try:
        with driver.session() as session:
            record = session.run(query).single()
            return None if record is None else record[0]
    finally:
        driver.close()


# ---------------------------------------------------------------------------
# GAP-ENTITY_COVERAGE-003 -- bhesaja was curated all along
# ---------------------------------------------------------------------------

#: Every file that carried a form of "bhesaja was never curated". Two API surfaces and one
#: frontend plate published it; the registry entry quoted the API one as evidence that the
#: gap was open, so the false claim was also the gap's own warrant.
_BHESAJA_CLAIM_SURFACES = (
    "src/vedagraph/api/services/insight_service.py",
    "src/vedagraph/api/services/entity_service.py",
    "src/vedagraph/domain/queries.py",
    "src/vedagraph/api/models/insight.py",
    "frontend/src/components/lab/plates/human-concerns.tsx",
    # The corrected note sends the reader here, so an assertion landing on this page
    # would be the one place it does most damage.
    "frontend/src/app/limits/page.tsx",
)

#: The asserting form, rather than the substring "bhesaja" -- which now appears
#: legitimately in the corrective prose beside it.
_BHESAJA_FALSE_ASSERTIONS = (
    re.compile(r"bhe[sṣ]aja\s+was\s+(never|not)\s+curated", re.IGNORECASE),
    re.compile(r"no\s+healing\s+entity\s+in\s+the\s+registry", re.IGNORECASE),
    re.compile(r"registry\s+has\s+no\s+healing\s+entity", re.IGNORECASE),
)

#: A sentence carrying one of these is *reporting* the false claim in order to correct it,
#: which is the opposite of asserting it and must pass.
_BHESAJA_EXONERATIONS = (
    "was false",
    "which was false",
    "an earlier version of this",
    "this caveat stood",
    "stood here for two rounds",
)

#: Adjacent implicit-concatenation string literals, which is how a long caveat is written
#: in both Python and TSX. Collapsed before scanning; see
#: :func:`_logical_sentences`.
_LITERAL_JOIN = re.compile(r'"\s*\n\s*"')


def _logical_sentences(text: str) -> list[str]:
    """The file's prose as a reader meets it, not as the source wraps it.

    Scanning physical lines is what broke the first version of this check: a caveat quoting
    the old sentence in order to correct it had the assertion on one line and "which was
    false" three lines later, so a line-scoped needle flagged the correction as the defect.
    That is the recorded false-positive shape -- a corrective note quoting an old phrase --
    and the fix is to compare sentences rather than lines.
    """
    return _LITERAL_JOIN.sub("", text).splitlines()


def test_no_surface_asserts_that_bhesaja_was_never_curated() -> None:
    """BAD -> FAIL. The claim was false for two rounds and it was load-bearing.

    ``VG:CONCEPT:BHESAJA-HEALING`` has been in the registry with 7 registered Sanskrit
    aliases and 108 evidenced mention edges across all four corpora. Meanwhile
    ``/api/v1/insights/atharvaveda/concerns`` told readers a stated remedy was unreachable,
    and GAP-ENTITY_COVERAGE-003 cited that caveat as proof it was still open. The gap's
    evidence was the gap's own false claim.
    """
    offenders: list[str] = []
    for relative in _BHESAJA_CLAIM_SURFACES:
        text = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
        for number, sentence in enumerate(_logical_sentences(text), start=1):
            if any(marker in sentence.lower() for marker in _BHESAJA_EXONERATIONS):
                continue
            for pattern in _BHESAJA_FALSE_ASSERTIONS:
                if pattern.search(sentence):
                    offenders.append(f"{relative}~{number}: {sentence.strip()[:160]}")
    assert not offenders, "a surface still asserts the false absence:\n" + "\n".join(offenders)


def test_the_bhesaja_needle_can_still_fail() -> None:
    """A needle nobody proved can fail is a needle that certifies nothing.

    Both halves are checked: the asserting form must be caught, and each exonerating
    marker must actually exonerate. The second half is the one that matters -- an
    over-broad exoneration list would silence the check entirely.
    """
    asserting = 'note: "Including why there is no healing entity in the registry",'
    assert any(pattern.search(asserting) for pattern in _BHESAJA_FALSE_ASSERTIONS)
    assert not any(marker in asserting.lower() for marker in _BHESAJA_EXONERATIONS)

    correcting = (
        '"rounds saying otherwise -- the registry has no healing entity, bhesaja was '
        'never curated -- was false."'
    )
    assert any(pattern.search(correcting) for pattern in _BHESAJA_FALSE_ASSERTIONS)
    assert any(marker in correcting.lower() for marker in _BHESAJA_EXONERATIONS)

    # And the literal-join step must actually join, or the sentence view degrades back to
    # the line view that produced the false positive.
    wrapped = '        "the registry has no healing entity, "\n        "bhesaja was never curated -- was false."\n'
    joined = _logical_sentences(wrapped)
    assert len(joined) == 1, joined
    assert "was false" in joined[0]


@pytest.mark.live
@_LIVE
def test_live_the_remedy_entity_exists_with_registered_aliases_and_verse_evidence() -> None:
    """GOOD -> PASS, on the closure test's first two clauses.

    The registry's own closure *measure* asks ``n:Remedy OR n:Bhesaja``, which is 0 and
    should stay 0: adding a top-level label because a route name suggests one would give
    the product two answers to one question. The authoritative representation is the
    ``:Concept``, and that is what is asserted here.
    """
    assert _scalar("MATCH (n) WHERE n:Remedy OR n:Bhesaja RETURN count(n)") == 0, (
        "a :Remedy or :Bhesaja label was added; the concept is the authoritative "
        "representation and a second label is a second answer to one question"
    )
    driver = _driver()
    try:
        with driver.session() as session:
            node = session.run(
                "MATCH (n:Concept {entity_key: 'VG:CONCEPT:BHESAJA-HEALING'}) "
                "RETURN labels(n) AS labels, n.aliases_sa AS aliases_sa"
            ).single()
            assert node is not None, "the remedy concept is missing"
            assert "DomainEntity" in node["labels"]
            assert len(node["aliases_sa"]) >= 7, node["aliases_sa"]

            # Clause 2: the relation carries verse evidence, per edge, not per layer.
            rows = list(
                session.run(
                    """
                    MATCH (m:Mantra)-[r:MENTIONS_ENTITY]
                          ->(:Concept {entity_key: 'VG:CONCEPT:BHESAJA-HEALING'})
                    RETURN count(r) AS edges,
                           sum(CASE WHEN r.evidence IS NULL THEN 1 ELSE 0 END) AS no_evidence,
                           count(DISTINCT m.veda) AS vedas
                    """
                )
            )
            assert rows[0]["edges"] >= 108
            assert rows[0]["no_evidence"] == 0, (
                "a stated-remedy edge without verse evidence is the thing clause 2 forbids"
            )
            # All four corpora, so the AV figure is readable as specialisation rather than
            # as the only column anyone measured.
            assert rows[0]["vedas"] == 4
    finally:
        driver.close()


def test_the_stated_remedy_query_is_declared_and_serves_the_concerns_endpoint() -> None:
    from vedagraph.domain.queries import QUERIES_BY_NAME

    query = QUERIES_BY_NAME["stated_remedy_by_veda"]
    assert "VG:CONCEPT:BHESAJA-HEALING" in query.cypher
    # The caveat must say what a STATED remedy is and is not, because "remedy" invites the
    # reading that the verse prescribes something effective.
    assert "STATED remedy" in query.caveat
    assert "was false" in query.caveat


# ---------------------------------------------------------------------------
# GAP-ENTITY_COVERAGE-001 -- the epithet occurrence layer
# ---------------------------------------------------------------------------


def test_the_epithet_occurrence_predicate_is_declared_with_a_signature() -> None:
    """An undeclared predicate is invisible to /api/v1/graph, which is safe and silent."""
    from vedagraph.domain import ontology

    assert ontology.REL_MENTIONS_EPITHET == "MENTIONS_EPITHET"
    assert ontology.REL_MENTIONS_EPITHET in ontology.CAMPAIGN_RELATIONSHIP_TYPES
    assert ontology.CORPUS_AND_CAMPAIGN_SIGNATURES[ontology.REL_MENTIONS_EPITHET] == (
        frozenset({ontology.LABEL_PASSAGE, ontology.LABEL_MANTRA}),
        frozenset({ontology.LABEL_EPITHET}),
    )
    # Not HAS_EPITHET: that is Devata -> Epithet and says "this deity is called this",
    # which is true whether or not any particular verse says so.
    assert ontology.RELATIONSHIP_SIGNATURES[ontology.REL_HAS_EPITHET] == (
        frozenset({ontology.LABEL_DEVATA}),
        frozenset({ontology.LABEL_EPITHET}),
    )

    from vedagraph.api.services.graph_service import PREDICATE_SEMANTICS

    semantics = PREDICATE_SEMANTICS["MENTIONS_EPITHET"]
    # The Rigveda-only bound belongs in the predicate's own limit, because a reader who
    # takes a count from a row is the reader who did not read the caveat.
    assert "RIGVEDA ONLY" in semantics.limit
    assert "UNANNOTATED" in semantics.limit


@pytest.mark.live
@_LIVE
def test_live_every_epithet_occurrence_edge_states_its_tier_and_its_bound() -> None:
    driver = _driver()
    try:
        with driver.session() as session:
            total = session.run(
                "MATCH (:Mantra)-[r:MENTIONS_EPITHET]->(:Epithet) RETURN count(r) AS c"
            ).single()["c"]
            assert total > 0, "the occurrence layer did not land"

            # Endpoint discipline, and the property contract on every edge.
            assert (
                session.run(
                    "MATCH (a)-[r:MENTIONS_EPITHET]->(b) "
                    "WHERE NOT (a:Passage OR a:Mantra) OR NOT b:Epithet RETURN count(r) AS c"
                ).single()["c"]
                == 0
            )
            missing = session.run(
                """
                MATCH (:Mantra)-[r:MENTIONS_EPITHET]->(:Epithet)
                RETURN sum(CASE WHEN r.epithet_match_tier IS NULL THEN 1 ELSE 0 END) AS tier,
                       sum(CASE WHEN r.annotator_lemma IS NULL THEN 1 ELSE 0 END) AS lemma,
                       sum(CASE WHEN r.absence_outside_annotated_vedas IS NULL
                                THEN 1 ELSE 0 END) AS bound
                """
            ).single()
            assert missing["tier"] == 0
            assert missing["lemma"] == 0, (
                "provenance must point at the scholarly annotation layer on every edge"
            )
            assert missing["bound"] == 0, (
                "the Rigveda-only bound is typed in the row, not left to a caveat"
            )

            tiers = {
                record["t"]
                for record in session.run(
                    "MATCH ()-[r:MENTIONS_EPITHET]->() RETURN DISTINCT r.epithet_match_tier AS t"
                )
            }
            assert tiers == {"STEM_LEMMA", "ATTESTED_SURFACE_FORM"}, tiers

            # The layer is derived from Rigvedic annotation, so it must be Rigveda-only.
            # A Samavedic edge here would be a claim the evidence cannot support.
            vedas = {
                record["v"]
                for record in session.run(
                    "MATCH (m:Mantra)-[:MENTIONS_EPITHET]->(:Epithet) RETURN DISTINCT m.veda AS v"
                )
            }
            assert vedas == {"RV"}, vedas

            # Normalisation did not mint identity: the inventory is still the curated 13.
            assert session.run("MATCH (e:Epithet) RETURN count(e) AS c").single()["c"] == 13
            # And every one of them now answers "where does this occur".
            reached = session.run(
                "MATCH (e:Epithet) WHERE EXISTS { MATCH (:Mantra)-[:MENTIONS_EPITHET]->(e) } "
                "RETURN count(e) AS c"
            ).single()["c"]
            assert reached == 13, f"{13 - reached} epithets still answer nothing"
    finally:
        driver.close()


# ---------------------------------------------------------------------------
# GAP-ATTRIBUTION-002 clause 1 -- the vrddhi-spelled suffix, landed
# ---------------------------------------------------------------------------


@pytest.mark.live
@_LIVE
def test_live_the_vrddhi_spelled_descriptors_reach_their_deities_in_the_graph() -> None:
    """The resolver fix is tested in ``test_ascription_bridge``; this pins the landing."""
    driver = _driver()
    try:
        with driver.session() as session:
            resolved = session.run(
                "MATCH (a:DevataAscription)-[:ASCRIBES_TO_DEVATA]->(:Devata) "
                "RETURN count(DISTINCT a) AS c"
            ).single()["c"]
            assert resolved == 47, f"39 before the fix, 47 after; measured {resolved}"

            # The looser suffix tier is countable apart from the exact one, which is the
            # whole reason it has its own path value.
            paths = {
                record["p"]: record["n"]
                for record in session.run(
                    "MATCH ()-[r:ASCRIBES_TO_DEVATA]->() "
                    "RETURN r.ascription_resolution_path AS p, count(*) AS n"
                )
            }
            assert paths["DEITY_ADJECTIVE_SUFFIX_LENGTH_FOLDED"] == 8
            assert paths["DEITY_ADJECTIVE_SUFFIX"] == 12
            assert paths["VRDDHI_TADDHITA"] == 27

            for label, devata in (
                ("agnidāivatam", "VG:DEVATA:AGNIH"),
                ("indradāivatam", "VG:DEVATA:INDRAH"),
            ):
                landed = session.run(
                    "MATCH (a:DevataAscription {label_iast: $label})"
                    "-[:ASCRIBES_TO_DEVATA]->(d:Devata) RETURN d.entity_key AS k",
                    label=label,
                ).single()
                assert landed is not None and landed["k"] == devata, label

            # Every unresolved descriptor still carries an explicit reason: clause 3, which
            # R3 closed and which this fix must not undo.
            assert (
                session.run(
                    "MATCH (a:DevataAscription) "
                    "WHERE a.ascription_resolution_status STARTS WITH 'UNRESOLVED' "
                    "AND a.ascription_unresolved_reason IS NULL RETURN count(a) AS c"
                ).single()["c"]
                == 0
            )
    finally:
        driver.close()


# ---------------------------------------------------------------------------
# Agent B's criticals, pinned so each one can only happen once
# ---------------------------------------------------------------------------


@pytest.mark.live
@_LIVE
def test_live_the_stored_attribution_scope_note_matches_its_generator() -> None:
    """Agent B's C3: the corrected note existed in code and never reached the graph.

    ``attribution_scope_note`` is written onto all 214 ``:Devata`` nodes by the taxonomy
    overlay, and it is SERVED -- ``vedagraph.api.ask.retriever`` selects it and
    ``vedagraph.api.ask.evidence`` uses it as the qualifier on an absence. So a stale copy
    is not a cosmetic drift: Ask publishes it to a model as the justification for an answer.

    R4 corrected the note in ``taxonomy.py`` (285 -> 277, plus the residual disclosure) and
    did not re-land it, so the graph kept publishing 285 while the source said 277.
    ``tests/domain/test_attribution_scope_note.py`` names the missing step in its own
    failure message -- "re-land attribution_scope_note onto the 214 :Devata nodes" -- and
    then nothing compared the two. This is that comparison.
    """
    source = (PROJECT_ROOT / "src" / "vedagraph" / "domain" / "taxonomy.py").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r'"attribution_scope_note": \(\n(.*?)\n            \),', source, re.DOTALL
    )
    assert match is not None, "the overlay no longer writes attribution_scope_note"
    expected = "".join(re.findall(r'^\s*"(.*)"$', match.group(1), re.M))
    assert expected, "the note reconstructed empty, so this test would pass vacuously"

    driver = _driver()
    try:
        with driver.session() as session:
            stored = [
                (record["note"], record["n"])
                for record in session.run(
                    "MATCH (d:Devata) RETURN DISTINCT d.attribution_scope_note AS note, "
                    "count(*) AS n"
                )
            ]
    finally:
        driver.close()

    assert len(stored) == 1, f"the note is not uniform across :Devata: {len(stored)} variants"
    note, count = stored[0]
    assert count == 214
    assert note == expected, (
        "the stored attribution_scope_note has drifted from the overlay that writes it. "
        "Re-land it onto the 214 :Devata nodes; Ask serves this string."
    )
    # And the figures the correction was about, asserted directly rather than by length.
    assert "277" in note
    assert "285" not in note
    assert "R4-RESIDUAL-ATTRIBUTION-002" in note


@pytest.mark.live
@_LIVE
def test_live_no_personification_refusal_is_contradicted_by_the_registry() -> None:
    """Agent B's C1: two refusals asserted an absence the registry disproved.

    The V1 mapping was hand-written and stored the reason "No :Devata in this registry
    carries this phenomenon's Sanskrit stem" on ``VG:CONCEPT:USAS-DAWN`` and
    ``VG:CONCEPT:CANDRAMAS-MOON`` while ``VG:DEVATA:USAH`` carries ``label_iast: uṣas`` and
    ``VG:DEVATA:CANDRAMAH`` carries ``label_iast: candramas`` -- exact matches on the same
    field that matched AGNI-FIRE. The same R4 migration landed a ``COMPOSED_OF`` edge to
    ``VG:DEVATA:USAH``, so one arm of the pass used the deity while another denied it
    existed.

    This rebuilds the index from the graph and refuses any REFUSED_NO_REGISTERED_DEITY_
    COUNTERPART row whose stem or alias actually reaches a registered deity. It is the
    check that would have caught the hand-written map.
    """
    driver = _driver()
    try:
        with driver.session() as session:
            deities = [
                dict(record)
                for record in session.run(
                    "MATCH (d:Devata) WHERE d.is_deity = true "
                    "RETURN d.entity_key AS k, d.label_iast AS iast, "
                    "d.preferred_label AS pref, d.aliases_iast AS al"
                )
            ]
            phenomena = [
                dict(record)
                for record in session.run(
                    "MATCH (n:NaturalPhenomenon) RETURN n.entity_key AS k, "
                    "n.preferred_label_sa AS sa, n.aliases_sa AS al, "
                    "n.personification_status AS status, n.personified_as AS target"
                )
            ]
    finally:
        driver.close()

    index: dict[str, set[str]] = {}
    for deity in deities:
        surfaces = [deity["iast"], deity["pref"], *(deity["al"] or [])]
        for surface in surfaces:
            if surface:
                index.setdefault(str(surface).strip().lower(), set()).add(deity["k"])

    contradicted: list[str] = []
    for phenomenon in phenomena:
        if phenomenon["status"] != "REFUSED_NO_REGISTERED_DEITY_COUNTERPART":
            continue
        reachable = set(index.get(str(phenomenon["sa"] or "").strip().lower(), ()))
        for alias in phenomenon["al"] or []:
            reachable |= index.get(str(alias).strip().lower(), set())
        if reachable:
            contradicted.append(f"{phenomenon['k']} reaches {sorted(reachable)}")
    assert not contradicted, (
        "a personification refusal says no registered deity carries the stem, and one "
        "does:\n" + "\n".join(contradicted)
    )

    # A phenomenon that IS personified must name a live, eligible deity.
    live_keys = {deity["k"] for deity in deities}
    for phenomenon in phenomena:
        if phenomenon["status"] == "PERSONIFIED_AS_A_REGISTERED_DEVATA":
            assert phenomenon["target"] in live_keys, phenomenon["k"]
    # And the two Agent B named, by name.
    named = {p["k"]: p for p in phenomena}
    assert named["VG:CONCEPT:USAS-DAWN"]["target"] == "VG:DEVATA:USAH"
    assert named["VG:CONCEPT:CANDRAMAS-MOON"]["target"] == "VG:DEVATA:CANDRAMAH"


def test_no_surface_publishes_the_superseded_285_descriptor_split() -> None:
    """Agent B's C2: 39/285 was updated in seven places and missed in two.

    ``entity_service.py:1424`` served "one of the 285 descriptors refused resolution"
    in the SAME response as ``ATTRIBUTION_SCOPE_STATEMENT`` saying "The other 277 are
    refused", both marked ``source="measured"`` -- a payload contradicting itself.
    ``insight_service.py`` carried a third copy that Agent B's own sweep missed.

    The needle is the descriptor split specifically, not the digits 285, because 27,285 and
    a 285-character skeleton appear legitimately elsewhere in the source.
    """
    pattern = re.compile(r"285 (?:of (?:the )?324|descriptors|of those 324)", re.IGNORECASE)
    offenders: list[str] = []
    for path in sorted((PROJECT_ROOT / "src" / "vedagraph").rglob("*.py")):
        for number, sentence in enumerate(_logical_sentences(path.read_text(encoding="utf-8")), 1):
            if pattern.search(sentence):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)}~{number}: {sentence.strip()[:120]}")
    assert not offenders, (
        "the superseded 39/285 descriptor split is still published:\n" + "\n".join(offenders)
    )
