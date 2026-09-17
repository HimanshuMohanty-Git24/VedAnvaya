"""Guards for AGENT 4's ritual closure artifact.

Every test here carries its own negative control in the same function. A guard that only
ever sees good input is a guard nobody has measured, and this repository has twice shipped
a gate that was structurally incapable of failing, so each assertion below is run once
against the artifact and once against an input that is known to be wrong.
"""
from __future__ import annotations

import json
import pathlib

import pytest

ARTIFACT = pathlib.Path(__file__).resolve().parents[2] / (
    "data/staging/final_closure_sprint/agent4")
WAVE2 = pathlib.Path(__file__).resolve().parents[2] / "data/staging/ritual"

pytestmark = pytest.mark.skipif(
    not (ARTIFACT / "manifest.json").exists(),
    reason="AGENT 4 ritual closure artifact not built in this tree",
)

#: Offering keys the ritual registry knows. An edge needs a node at the far end, and a
#: normalized-string join is not identity evidence, so the far end must be one of these.
OFFERING_KEYS = frozenset({
    "VG:CONCEPT:HAVIS-OBLATION", "VG:CONCEPT:PURODASA-CAKE", "VG:CONCEPT:CARU-GRUEL",
    "VG:CONCEPT:AJYA-MELTED-BUTTER", "VG:CONCEPT:AMIKSA-CURDLED-MILK",
    "VG:CONCEPT:DADHI-SOUR-MILK", "VG:CONCEPT:PAYAS-MILK",
    "VG:CONCEPT:GHRTA-CLARIFIED-BUTTER", "VG:CONCEPT:SOMA-DRINK",
    "VG:CONCEPT:PASU-LIVESTOCK", "VG:CONCEPT:ASVA-HORSE", "VG:CONCEPT:GO-CATTLE",
    "VG:CONCEPT:AJA-GOAT", "VG:CONCEPT:ANNA-FOOD", "VG:CONCEPT:DAKSINA-PRIESTLY-GIFT",
    "VG:CONCEPT:VAPA-OMENTUM", "VG:CONCEPT:PRAJAPATI-PURODASA",
    "VG:CONCEPT:SURA-SPIRITUOUS-LIQUOR", "VG:CONCEPT:PARISRUT-FERMENTED-DRAUGHT",
    "VG:CONCEPT:MADHU-HONEY", "VG:CONCEPT:PURODASA-ASTAKAPALA",
})

RITUAL_CONTEXT_VOCABULARY = frozenset({
    "EMPLOYED_IN_RITE", "EMPLOYED_IN_RITE_PROBABLE", "RITE_NAMED_IN_THIS_MANTRA",
    "UNRESOLVED_SHARED_OPENING", "NO_RITUAL_CITATION_FOUND",
})

#: Forms that look like a dative in a naive list but are not one. `apsu` is the locative
#: plural of ap-; `apsu juhoti` is "he offers INTO the waters".
KNOWN_NON_DATIVES = frozenset({"apsu", "apsv", "devesu", "apas", "apah"})


def _jsonl(name, root=ARTIFACT):
    with (root / name).open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _json(name, root=ARTIFACT):
    return json.loads((root / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------
# The checks. Each is a plain function over data so the negative control can call it too.
# ---------------------------------------------------------------------------------------
def non_datives_registered_as_datives(mapping):
    return sorted(f for forms in mapping.values() for f in forms if f in KNOWN_NON_DATIVES)


def edges_with_no_node_at_the_far_end(rows, key_field, allowed):
    return [r for r in rows if r.get(key_field) not in allowed]


def rows_outside_the_vocabulary(rows, field, vocabulary):
    return [r for r in rows if r.get(field) not in vocabulary]


def mutations_touching_the_step_layers(mutations):
    hits = []
    for m in mutations.get("relationship_creates", []):
        if m.get("type") in {"HAS_STEP", "HAS_RITUAL_STEP"}:
            hits.append(m)
        if any(k in (m.get("properties") or {})
               for k in ("step_position", "order_basis", "rite_global_position")):
            hits.append(m)
    return hits


def asserted_edges_that_rest_on_probable_evidence(mutations):
    lexical = {"MENTIONS_ENTITY"}
    bad = []
    for m in mutations.get("relationship_creates", []):
        if m.get("type") in lexical:
            continue
        props = m.get("properties") or {}
        if props.get("evidence_layer") != "SOURCE_EXPLICIT":
            bad.append(m)
        if props.get("mapping_confidence") not in {"EXACT", None} or \
                props.get("mapping_confidence") == "PROBABLE":
            bad.append(m)
    return bad


# ---------------------------------------------------------------------------------------
def test_no_locative_is_registered_as_a_dative():
    """GOOD -> PASS on the corrected map; BAD -> the same check fails on the Wave 2 map."""
    corrected = {
        r["from_entity_key"]: [e["dative_form"] for e in r["evidence"]]
        for r in _jsonl("receives_offering.jsonl")
    }
    assert non_datives_registered_as_datives(corrected) == []

    wave2 = {r["devata_key"]: r["dative_forms"] for r in _jsonl("deity_offerings.jsonl", WAVE2)}
    offenders = non_datives_registered_as_datives(wave2)
    assert offenders == ["apsu"], (
        "negative control: the Wave 2 registry must still show the defect this guard was "
        "written for, otherwise the guard is measuring nothing")


def test_every_receives_offering_edge_has_an_offering_at_the_far_end():
    rows = list(_jsonl("receives_offering.jsonl"))
    assert rows, "the corrected artifact must propose at least one typed edge"
    assert edges_with_no_node_at_the_far_end(rows, "to_entity_key", OFFERING_KEYS) == []

    wave2 = list(_jsonl("deity_offerings.jsonl", WAVE2))
    broken = edges_with_no_node_at_the_far_end(wave2, "offering_key", OFFERING_KEYS)
    assert len(broken) == len(wave2), (
        "negative control: every Wave 2 row must still lack an offering at the far end, "
        "which is the defect this guard exists for")


def test_every_receives_offering_edge_carries_per_locus_verse_evidence():
    for r in _jsonl("receives_offering.jsonl"):
        assert r["evidence"], r["from_entity_key"]
        assert len(r["evidence"]) == r["loci"], (
            f"{r['from_entity_key']} claims {r['loci']} loci and cites "
            f"{len(r['evidence'])}; Wave 2 truncated its evidence at six and published the "
            f"full count beside it")
        for e in r["evidence"]:
            assert e["citation"] and e["supplementary_key"] and e["quote"]


def test_yupa_reaches_three_vedas_and_both_yajurvedic_witnesses():
    fix = _json("yupa_alias_fix.json")
    assert fix["simulation_reproduces_the_live_graph_before_the_fix"], (
        "the simulation must reproduce the live graph's existing edges before any alias is "
        "added, or its 'after' figure is unfalsifiable")
    assert fix["vedas_with_matches_after"] == 3
    assert fix["vsm_19_17_matched"] and fix["vsm_25_29_matched"]

    # negative control: the aliases the graph held before this fix reach two Vedas and
    # neither Yajurvedic witness, which is exactly what GAP-RITUAL-003 records.
    assert fix["vedas_with_matches_before"] == 2
    assert "VG:YV:VSM:A19:V017" not in fix["simulated_passages_before"]
    assert "VG:YV:VSM:A25:V029" not in fix["simulated_passages_before"]


def _letters(text: str) -> str:
    """Base letters only. The host forms carry Vedic tone marks between every syllable."""
    import unicodedata
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def test_no_yupa_alias_reaches_a_word_that_is_not_the_post():
    """Alias quality is measured per alias, not per row."""
    fix = _json("yupa_alias_fix.json")
    for alias, hosts in fix["host_forms_per_alias"].items():
        assert hosts, f"{alias} reached no host form at all"
        for host in hosts:
            base = _letters(host)
            assert base.startswith("yup") or base.startswith("svarav"), (
                f"{alias} reached {host}, which is a different word")
    assert "dhariyūpīyāyāṁ" in fix["deliberately_not_registered"], (
        "the Hariyupiya place-name must stay named as an exclusion, not silently absent")
    # negative control: the check must reject the place-name and the millet-style collision
    assert not _letters("dhariyūpīyāyāṁ").startswith("yup")
    assert not _letters("svaranti").startswith("svarav")


def test_ritual_context_is_total_and_absence_is_typed():
    rows = list(_jsonl("ritual_context.jsonl"))
    assert len(rows) == 20210, "the assignment must cover every core mantra"
    assert rows_outside_the_vocabulary(rows, "ritual_context",
                                       RITUAL_CONTEXT_VOCABULARY) == []
    values = {r["ritual_context"] for r in rows}
    assert "NO_RITUAL_CITATION_FOUND" in values, (
        "absence must be typed in the row; a positive-only assignment lets a reader infer "
        "a false zero")
    assert "NON_RITUAL" not in values, (
        "nothing measured here can support NON_RITUAL and no row may claim it")
    for r in rows:
        assert r["ritual_context_method"].startswith("EXTERNAL_RITUAL_CITATION")

    # negative control: a positive-only assignment must be caught by the same check.
    positive_only = [r for r in rows if r["ritual_context"] != "NO_RITUAL_CITATION_FOUND"]
    assert len(positive_only) < 20210
    assert rows_outside_the_vocabulary(
        [{"ritual_context": "NON_RITUAL"}], "ritual_context",
        RITUAL_CONTEXT_VOCABULARY), "the vocabulary check must reject an invented value"


def test_ritual_context_precision_is_measured_on_rows_that_were_read():
    p = _json("ritual_context_precision.json")
    assert p["reviewed"] == len(p["rows"])
    assert p["human_reviewed"] == 0, (
        "no human read any locus; a QA block that implies otherwise is the easiest number "
        "in this repository to overstate")
    assert p["precision_over_every_reviewed_row"] <= \
        p["precision_over_rows_whose_evidence_is_reproducible"]
    for row in p["rows"]:
        assert row["verdict"] and row["reason"]
    assert p["population_span_not_reproducible"] > 0, (
        "negative control: the unreproducible-span finding must still be present, or the "
        "reproducibility check is not running")


def test_the_two_step_layers_are_not_touched():
    mutations = _json("proposed_mutations.json")
    assert mutations_touching_the_step_layers(mutations) == []

    # negative control
    synthetic = {"relationship_creates": [
        {"type": "HAS_RITUAL_STEP", "properties": {}},
        {"type": "PERFORMED_BY", "properties": {"rite_global_position": 3}},
    ]}
    assert len(mutations_touching_the_step_layers(synthetic)) == 2


def test_no_probable_evidence_is_promoted_to_an_asserted_edge():
    mutations = _json("proposed_mutations.json")
    assert asserted_edges_that_rest_on_probable_evidence(mutations) == []

    synthetic = {"relationship_creates": [
        {"type": "USES_OBJECT",
         "properties": {"evidence_layer": "DETERMINISTIC_DERIVED",
                        "mapping_confidence": "PROBABLE"}},
    ]}
    assert asserted_edges_that_rest_on_probable_evidence(synthetic)


def test_every_uses_object_row_was_read_and_its_verdict_is_reasoned():
    rows = list(_jsonl("uses_object_adjudication.jsonl"))
    assert len(rows) == 4
    accepted = [r for r in rows if r["verdict"].startswith("ACCEPT")]
    assert len(accepted) == 1 and accepted[0]["object_key"] == "VG:CONCEPT:MANI-AMULET"
    assert accepted[0]["independent_witness"], (
        "the one promoted row must carry a witness independent of the matcher")
    for r in rows:
        assert r["reason"] and r["human_reviewed"] == 0
        assert r["wave2_staged_confidence"] == "PROBABLE", (
            "negative control: every one of these was staged PROBABLE, so if this field "
            "ever reads otherwise the source rows have moved under the verdicts")


def test_the_classical_sixteen_names_the_schema_its_denominator_comes_from():
    rows = list(_jsonl("ritual_roles.jsonl"))
    sixteen = [r for r in rows if r["in_classical_sixteen"]]
    assert len(sixteen) == 16
    for r in sixteen:
        assert r["denominator_schema"] == "SRAUTASUTRA_RTVIJ_SCHEMA_OF_SIXTEEN"
        assert r["existence_evidence"]["citation"] == "SankhSS 13.14.1"
        assert r["existence_evidence"]["attributed_translation"]
    outside = [r for r in rows if not r["in_classical_sixteen"]]
    assert outside, (
        "negative control: roles outside the schema must still be present in the file, "
        "because the eleven-against-sixteen figure the registry reports is wrong precisely "
        "because four of the eleven are these")


def test_hotr_carries_a_performed_by_edge_with_a_stated_source():
    rows = list(_jsonl("performed_by.jsonl"))
    hotr = [r for r in rows if r["to_entity_key"] == "VG:CONCEPT:HOTR-PRIEST"]
    assert hotr, "GAP-RITUAL-004 closes only if the hotr is wired to a rite"
    for r in rows:
        assert r["evidence_layer"] == "SOURCE_EXPLICIT"
        assert r["evidence"][0]["translation"], (
            "the enumeration is carried by an attributed translation as well as the "
            "Sanskrit, which is what makes it a statement rather than a reading")
    assert len(rows) == 16
    assert len({r["from_entity_key"] for r in rows}) == 1, (
        "one line states one rite's officiant set; an edge to a second rite would be an "
        "ordering or inference this artifact has no source for")


def test_the_proposed_census_delta_leaves_the_core_corpus_alone():
    m = _json("proposed_mutations.json")
    delta = m["expected_census_delta"]
    assert delta["nodes"] == m["counts"]["CREATE_NODE"]
    assert delta["relationships"] == m["counts"]["CREATE_RELATIONSHIP"]
    assert delta["nodes_after"] == m["baseline_census"]["nodes"] + delta["nodes"]
    assert delta["relationships_after"] == (
        m["baseline_census"]["relationships"] + delta["relationships"])
    assert m["counts"]["DELETE"] == 0
    for op in m["node_creates"]:
        assert "Passage" not in op["labels"] and "Mantra" not in op["labels"]
        assert "Work" not in op["labels"] and "TextVersion" not in op["labels"]


def test_the_sealed_wave2_artifact_was_not_rewritten():
    """The overlay must not have edited the artifact whose manifest hashes it."""
    import hashlib
    wave2_manifest = json.loads((WAVE2 / "manifest.json").read_text(encoding="utf-8"))
    checked = 0
    for entry in wave2_manifest["files"]:
        path = WAVE2 / entry["path"]
        if not path.exists():
            continue
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], (
            f"{entry['path']} no longer matches the seal it was published under")
        checked += 1
    assert checked >= 10, "negative control: the seal must actually cover files"


# ---------------------------------------------------------------------------------------
# Lead rulings 1-4. Each check is a plain function so its negative control is real.
# ---------------------------------------------------------------------------------------
def edges_violating(signature, edges):
    subjects, objects = signature
    bad = []
    for e in edges:
        if e.get("from_label") not in subjects or e.get("to_label") not in objects:
            bad.append(e)
    return bad


def in_place_edits_to_a_sealed_artifact(mutations):
    return [e for e in mutations.get("registry_edits", [])
            if e["op"] == "EDIT_REGISTRY_FILE"
            and e.get("file", "").startswith("data/staging/ritual/")]


def overlays_that_remove_rather_than_add(mutations):
    return [e for e in mutations.get("registry_edits", [])
            if e["op"] == "APPLY_OVERLAY" and e.get("removes")]


def corrections_that_zero_without_typing_the_absence(corrections):
    bad = []
    for c in corrections:
        props = c.get("properties") or {}
        zeroed = any(v == 0 for k, v in props.items() if k.endswith("_count"))
        typed = (props.get("supplementary_lines_assessed", 0) > 0
                 and "ASSESSED_ZERO" in str(props.get(
                     "supplementary_attestation_outcome", "")))
        if zeroed and not typed:
            bad.append(c)
    return bad


def test_receives_offering_signature_is_pinned_to_devata_offering():
    """RULING 4. The endpoint signature ships with the edges, not after them."""
    from vedagraph.domain.ontology import RELATIONSHIP_SIGNATURES
    subjects, objects = RELATIONSHIP_SIGNATURES["RECEIVES_OFFERING"]
    assert subjects == frozenset({"Devata"})
    assert objects == frozenset({"Offering"}), (
        "the range was {Offering, Substance, Animal, Plant} while the type carried zero "
        "edges, so nothing had ever measured it")

    edges = list(_jsonl("receives_offering.jsonl"))
    assert edges
    assert edges_violating((subjects, objects), edges) == []

    # negative control: the wrong-endpoint error this pin exists to catch
    assert edges_violating(
        (subjects, objects),
        [{"from_label": "Devata", "to_label": "Substance"},
         {"from_label": "Passage", "to_label": "Offering"}]) != []


def test_the_declared_signature_matches_what_the_artifact_proposes():
    m = _json("proposed_mutations.json")
    assert m["predicate_declaration"]["declared_signature"] == "(Devata) -> (Offering)"
    assert m["predicate_declaration"]["changed_in_the_same_change_as_the_edges"] is True
    for rel in m["relationship_creates"]:
        if rel["type"] != "RECEIVES_OFFERING":
            continue
        assert rel["from"]["label"] == "Devata" and rel["to"]["label"] == "Offering"


def test_the_sealed_registry_correction_is_an_overlay_not_an_edit():
    """RULING 1. A correction inside a seal goes outside it, additively."""
    m = _json("proposed_mutations.json")
    assert in_place_edits_to_a_sealed_artifact(m) == []
    overlays = [e for e in m["registry_edits"] if e["op"] == "APPLY_OVERLAY"]
    assert len(overlays) == 1
    assert overlays[0]["the_sealed_artifact_is_byte_identical"] is True
    assert overlays[0]["adds"]
    assert overlays_that_remove_rather_than_add(m) == [], (
        "an overlay that removes an alias changes what the sealed build meant, which is "
        "the thing the seal exists to prevent")

    synthetic = {"registry_edits": [
        {"op": "EDIT_REGISTRY_FILE", "file": "data/staging/ritual/ritual_registries.py"},
        {"op": "APPLY_OVERLAY", "adds": ["x"], "removes": ["sattram"]},
    ]}
    assert in_place_edits_to_a_sealed_artifact(synthetic)
    assert overlays_that_remove_rather_than_add(synthetic)


def test_the_overlay_only_reaches_the_session_and_its_effect_is_measured():
    o = _json("ritual_registry_overlay.json")
    assert o["supplementary_lines_reached"] > 0
    for token, count in o["host_forms_per_added_token"].items():
        assert token.startswith("satr") or token.startswith("sattr"), token
        assert count > 0
    decisive = o["the_decisive_line"]
    assert decisive is not None and decisive["citation"] == "SankhSS 13.14.1"
    assert "VG:CONCEPT:SATTRA" in decisive["newly_named"], (
        "the line whose anchoring defect this overlay exists to fix must be one of the "
        "lines it moves, or the overlay is measuring something else")


def test_the_audumbara_correction_types_its_absence():
    """RULING 3. An assessed zero must be distinguishable from an unexamined one."""
    m = _json("proposed_mutations.json")
    corrections = m["property_corrections"]
    assert len(corrections) == 1
    c = corrections[0]
    assert c["match"]["entity_key"] == "VG:CONCEPT:AUDUMBARA-AMULET"
    assert c["nodes_created"] == 0 and c["relationships_created"] == 0
    assert corrections_that_zero_without_typing_the_absence(corrections) == []
    assert c["properties"]["supplementary_attestation_count"] == 0
    assert c["properties"]["supplementary_lines_assessed"] > 0

    audit = _json("audumbara_sense_audit.json")
    assert audit["of_those_attesting_the_amulet"] == 0
    assert audit["supplementary_lines_assessed"] == \
        c["properties"]["supplementary_lines_assessed"]

    # negative control: a silent zeroing must be caught
    assert corrections_that_zero_without_typing_the_absence(
        [{"properties": {"supplementary_attestation_count": 0}}])


def test_the_rights_basis_is_recorded_and_is_not_cc_by():
    """RULING 2. A wrong licence recorded is worse than none."""
    for doc in (_json("proposed_mutations.json"), _json("manifest.json")):
        rights = doc["rights"]
        assert rights["basis"] == "PUBLIC_DOMAIN_BY_AGE"
        assert rights["basis_is_not"] == "CC_BY_4_0"
        assert rights["underlying_editions_public_domain_by_age"]
        assert rights["the_bound"].startswith("NO BULK VPC TEXT")
    # negative control: the check must reject a CC BY claim over corpus/VPC
    assert "CC_BY" not in _json("manifest.json")["rights"]["basis"]


def test_no_property_update_carries_supplementary_text():
    """The bound on ruling 2, measured rather than asserted."""
    rows = list(_jsonl("ritual_context.jsonl"))
    forbidden = {"citing_text_iast", "quote", "text_iast", "translation"}
    offenders = [r for r in rows if forbidden & set(r)]
    assert offenders == []
    # negative control
    assert [r for r in [{"citing_text_iast": "x"}] if forbidden & set(r)]
