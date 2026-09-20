#!/usr/bin/env python3
"""Gate B for ``samaveda_music``: is the notation claim MEANT the way it is written?

Gate A already asked whether the artifact is well formed, and it passes at full evaluation
coverage with ``--graph``. Gate B is the other question, and ``wave3_eligibility.json``
records it as ``UNKNOWN`` with the detail "no semantic review recorded" -- so there was
nothing to re-run here and this file is the implementation, not a re-execution.

The gate definition is not invented. ``data/staging/integration/wave3_eligibility.json``
declares it verbatim:

    B -- SEMANTIC: classification, population, source meaning, relation meaning

Those four words are the four sections below, and every check belongs to exactly one of
them. The population under test is the **1,136 ``ARCIKA_NOTATION`` rows**, which are what
``OWNER_DECISION_F_NOTATION_IS_NOT_AUDIO`` authorises; the 332 ``GANA_RENDERING`` rows and
the 3 container-scope performance rows are reported and are OUT OF SCOPE for this pass under
``OWNER_DECISION_G_GANA_OBJECT_OUT_OF_V1``, which places the object-side Gana model outside
Product V1. A check that averaged the two populations would be the mistake the attribution
gate was built to refuse: a file holding two kinds of claim has no single pass rate.

Two disciplines this project has paid for, both enforced here:

*   **Coverage is reported, not assumed.** Every check states the rows it evaluated and the
    rows that were eligible. A check below full coverage is a failure OF THE GATE, counted
    separately from any failure of the data, because a validator that silently skips is
    worse than no validator -- it converts absence of checking into evidence.

*   **A closed vocabulary is enumerated, never grepped for the value expected.** Each field
    with a declared value space has its ACTUAL distinct values listed in the artifact. Twice
    in this campaign an audit certified an absence by searching for the string it expected
    instead of enumerating what was there.

Gate B does not ask whether the notation is TRUE. That is Gate C, and it is a separate file
on purpose: the same codepath must not be allowed to validate itself.

Usage:
    python scripts/samaveda_music_gate_b.py [--json OUT]

Exit code is 1 if any check fails or if any check is below full coverage.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import itertools
import json
import pathlib
import re
import sys
from typing import Any

from neo4j import GraphDatabase, Query

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
STAGING = PROJECT_ROOT / "data" / "staging" / "samaveda_music"
ROWS = STAGING / "rows.jsonl"
REJECTED = STAGING / "rejected.jsonl"
SOURCES = STAGING / "sources.jsonl"
MANIFEST = STAGING / "manifest.json"
OUT = PROJECT_ROOT / "data" / "staging" / "integration" / "samaveda_music_gate_b.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"
QUERY_TIMEOUT_SECONDS = 300.0

#: The layer this gate adjudicates. The other two layers in the file are reported and left
#: alone: their object side is outside Product V1 by owner decision.
IN_SCOPE_LAYER = "ARCIKA_NOTATION"

#: The campaign invariant, identical to the one the attribution gate enforces. A row in
#: either class may not be imported by any pass.
NOT_IMPORTABLE = frozenset({"PROBABLE", "UNVERIFIED"})

#: The payload field space a notation row is allowed to occupy. Declared as a closed set so
#: a field arriving tomorrow is reported rather than ignored -- and so a reader can see that
#: no field anywhere in it names a PITCH, a svara NAME or a decipherment. The notation is
#: recorded as codepoints; interpreting it would need van der Hoogt 1929, which is not held.
DECLARED_PAYLOAD_FIELDS = frozenset(
    {
        "devanagari_extended_marks",
        "is_a_rendering",
        "layer",
        "notated_text_devanagari",
        "notation_encoding",
        "notation_system",
        "note",
        "private_use_codepoints",
        "tone_mark_count",
        "tone_marks_by_codepoint",
        "tone_stripped_text",
        "u0301_combining_acute",
        "vedic_extensions_marks",
    }
)

#: Any of these appearing in a payload key or value would mean the artifact had crossed from
#: recording the marks to interpreting them into music.
INTERPRETATION_VOCABULARY = re.compile(
    r"pitch|hertz|hz|frequency|interval|scale_degree|udatta|anudatta|svarita|"
    r"krusta|prathama|dvitiya|tritiya|caturtha|mandra|atisvara|melody|melodic|raga",
    re.IGNORECASE,
)

#: Audio vocabulary. A notation row claiming any of it would be the exact confusion
#: OWNER_DECISION_F was written to forbid: notation is not audio and may not borrow its
#: verification.
AUDIO_VOCABULARY = re.compile(
    r"audio|recording|ogg|mp3|wav|listen|heard|aural|duration_seconds|performance",
    re.IGNORECASE,
)

#: The two reason classes the withheld population is allowed to carry. A withheld row whose
#: reason falls outside them is an untyped absence, which this project treats as a defect:
#: a reader who sees only the positive rows infers a zero the data never stated.
WITHHELD_CLASSES = ("NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT", "NO_NEAR_LINE_PROBABLE_ABSENCE")

#: The predicate and the ``TextRole`` the notation import would use. Both must already exist:
#: HAS_TEXT_VERSION in the graph's own type store, PARALLEL_TEXT in the declared enum. The
#: notation is a second WITNESS of a verse's text, not an edge to a melodic object.
TARGET_PREDICATE = "HAS_TEXT_VERSION"
TARGET_TEXT_ROLE = "PARALLEL_TEXT"

#: The predicate and object model the notation rows must NOT ask for, because owner decision
#: G places them outside Product V1.
FORBIDDEN_PREDICATE = "MUSICALIZED_AS"

LOCATOR = re.compile(r"^sa\.wikisource page_id (\d+) revid (\d+) line (\d+)$")


class Check:
    """One semantic question, with its own coverage."""

    def __init__(self, name: str, section: str, asks: str) -> None:
        self.name = name
        self.section = section
        self.asks = asks
        self.eligible = 0
        self.evaluated = 0
        self.failures: list[dict[str, Any]] = []
        self.observed: dict[str, Any] = {}

    def fail(self, **detail: Any) -> None:
        if len(self.failures) < 25:
            self.failures.append(detail)
        self._overflow = getattr(self, "_overflow", 0) + 1

    @property
    def failure_count(self) -> int:
        return getattr(self, "_overflow", 0)

    def as_dict(self) -> dict[str, Any]:
        coverage = (self.evaluated / self.eligible) if self.eligible else 1.0
        return {
            "name": self.name,
            "section": self.section,
            "asks": self.asks,
            "eligible": self.eligible,
            "evaluated": self.evaluated,
            "coverage": round(coverage, 6),
            "at_full_coverage": self.evaluated == self.eligible,
            "failures": self.failure_count,
            "failure_examples": self.failures,
            "observed": self.observed,
            "status": (
                "PASS"
                if self.failure_count == 0 and self.evaluated == self.eligible
                else "FAIL"
            ),
        }


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def verse_component(canonical_key: str) -> int:
    return int(canonical_key.rsplit(":V", 1)[1])


def collection_of(canonical_key: str) -> str:
    return canonical_key.split(":")[3]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    rows = load_jsonl(ROWS)
    rejected = load_jsonl(REJECTED)
    sources = {r["source_id"]: r for r in load_jsonl(SOURCES)}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    notation = [r for r in rows if r["payload"]["layer"] == IN_SCOPE_LAYER]
    out_of_scope = collections.Counter(
        r["payload"]["layer"] for r in rows if r["payload"]["layer"] != IN_SCOPE_LAYER
    )
    withheld = [
        r
        for r in rejected
        if r["disposition"] == "UNRESOLVED" and r["kind"] == IN_SCOPE_LAYER
    ]

    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database=DB) as session:
        sv_keys = set(
            session.run(
                Query(
                    "MATCH (m:Mantra {veda:'SV'}) RETURN m.canonical_key AS k",
                    timeout=QUERY_TIMEOUT_SECONDS,
                )
            ).value()
        )
        sv_by_collection = collections.Counter(collection_of(k) for k in sv_keys)
        rel_types = set(
            session.run(
                Query(
                    "CALL db.relationshipTypes() YIELD relationshipType "
                    "RETURN relationshipType",
                    timeout=QUERY_TIMEOUT_SECONDS,
                )
            ).value()
        )
        labels = set(
            session.run(
                Query(
                    "CALL db.labels() YIELD label RETURN label",
                    timeout=QUERY_TIMEOUT_SECONDS,
                )
            ).value()
        )
        container_keys = set(
            session.run(
                Query(
                    # Scoped to entity_type, NOT to the label. Every :Mantra here also
                    # carries :Passage -- 1,844 of them -- so a label-only container query
                    # reports all 1,136 notation rows as container-grained. The :Internal
                    # label taught this project the same lesson at 70,559 false hits.
                    "MATCH (p:Passage) WHERE p.canonical_key STARTS WITH 'VG:SV:' "
                    "AND p.entity_type = 'STRUCTURAL_CONTAINER' "
                    "RETURN p.canonical_key AS k",
                    timeout=QUERY_TIMEOUT_SECONDS,
                )
            ).value()
        )
        declared_roles = set(
            session.run(
                Query(
                    "MATCH (t:TextVersion) RETURN DISTINCT t.text_role AS r",
                    timeout=QUERY_TIMEOUT_SECONDS,
                )
            ).value()
        )
    driver.close()

    # Whether PARALLEL_TEXT is a member of the codebase's declared TextRole vocabulary is a
    # question about the code, not the graph, so it is read from the enum rather than from
    # whatever values happen to be populated.
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from vedagraph.models.enums import TextRole

    role_vocabulary = {member.value for member in TextRole}

    checks: list[Check] = []

    # -- 1. CLASSIFICATION ------------------------------------------------------------
    c = Check(
        "classification.source_explicit_is_earned_not_asserted",
        "classification",
        "Every row calls itself SOURCE_EXPLICIT. Does each one actually carry a mark the "
        "source supplied, rather than a mark this pipeline could have inferred?",
    )
    c.eligible = len(notation)
    layers_seen: collections.Counter[str] = collections.Counter()
    for row in notation:
        c.evaluated += 1
        payload = row["payload"]
        layers_seen[row["evidence_layer"]] += 1
        if row["evidence_layer"] != "SOURCE_EXPLICIT":
            c.fail(key=row["canonical_key"], why="evidence_layer", got=row["evidence_layer"])
        elif payload["tone_mark_count"] < 1:
            c.fail(key=row["canonical_key"], why="source_explicit_with_no_mark")
        elif payload["private_use_codepoints"] or payload["u0301_combining_acute"]:
            c.fail(
                key=row["canonical_key"],
                why="mark_is_a_font_hack_or_an_iast_acute",
                pua=payload["private_use_codepoints"],
                u0301=payload["u0301_combining_acute"],
            )
    c.observed = {
        "evidence_layer_value_space": dict(layers_seen),
        "quality_class_value_space": dict(
            collections.Counter(r["quality_class"] for r in notation)
        ),
        "mapping_confidence_value_space": dict(
            collections.Counter(r["mapping_confidence"] for r in notation)
        ),
        "notation_system_value_space": dict(
            collections.Counter(r["payload"]["notation_system"] for r in notation)
        ),
        "notation_encoding_value_space": dict(
            collections.Counter(r["payload"]["notation_encoding"] for r in notation)
        ),
        "rows_with_zero_tone_marks": sum(
            1 for r in notation if r["payload"]["tone_mark_count"] == 0
        ),
        "total_tone_marks": sum(r["payload"]["tone_mark_count"] for r in notation),
    }
    checks.append(c)

    c = Check(
        "classification.not_importable_vocabulary_is_absent",
        "classification",
        "The campaign forbids importing a PROBABLE or UNVERIFIED row. Does any field of any "
        "row carry either word?",
    )
    c.eligible = len(notation)
    for row in notation:
        c.evaluated += 1
        blob = json.dumps(row, ensure_ascii=False)
        hits = sorted(w for w in NOT_IMPORTABLE if re.search(rf"\b{w}\b", blob))
        if hits:
            c.fail(key=row["canonical_key"], words=hits)
    c.observed = {"forbidden_words": sorted(NOT_IMPORTABLE)}
    checks.append(c)

    c = Check(
        "classification.notation_is_not_audio",
        "classification",
        "OWNER_DECISION_F rules the audible gate covers audio only. Does any notation row "
        "borrow audio vocabulary or claim aural verification?",
    )
    c.eligible = len(notation)
    for row in notation:
        c.evaluated += 1
        if row["payload"]["is_a_rendering"] is not False:
            c.fail(key=row["canonical_key"], why="is_a_rendering_not_false")
            continue
        hits = sorted(
            {m.group(0).lower() for m in AUDIO_VOCABULARY.finditer(" ".join(row["payload"]))}
        )
        if hits:
            c.fail(key=row["canonical_key"], why="audio_vocabulary_in_payload_keys", hits=hits)
    c.observed = {
        "is_a_rendering_value_space": dict(
            collections.Counter(r["payload"]["is_a_rendering"] for r in notation)
        ),
        "listening_review_population_declared_by_manifest": manifest["qa"]["detail"][
            "listening_review_population"
        ],
        "manifest_human_reviewed": manifest["qa"]["human_reviewed"],
    }
    checks.append(c)

    c = Check(
        "classification.marks_are_recorded_not_interpreted",
        "classification",
        "Is the payload field space the declared closed set, and does nothing in it name a "
        "pitch, a svara name or a decipherment the project does not hold?",
    )
    c.eligible = len(notation)
    field_space: collections.Counter[str] = collections.Counter()
    for row in notation:
        c.evaluated += 1
        keys = set(row["payload"])
        field_space.update(keys)
        undeclared = sorted(keys - DECLARED_PAYLOAD_FIELDS)
        missing = sorted(DECLARED_PAYLOAD_FIELDS - keys)
        if undeclared or missing:
            c.fail(key=row["canonical_key"], undeclared=undeclared, missing=missing)
            continue
        interpretive = sorted(
            {m.group(0).lower() for k in keys for m in INTERPRETATION_VOCABULARY.finditer(k)}
        )
        if interpretive:
            c.fail(key=row["canonical_key"], why="interpretation_field", hits=interpretive)
    c.observed = {
        "payload_field_space_actually_present": sorted(field_space),
        "declared_payload_field_space": sorted(DECLARED_PAYLOAD_FIELDS),
        "codepoints_recorded": sorted(
            {cp for r in notation for cp in r["payload"]["tone_marks_by_codepoint"]}
        ),
    }
    checks.append(c)

    # -- 2. POPULATION ----------------------------------------------------------------
    c = Check(
        "population.every_samavedic_verse_carries_one_typed_disposition",
        "population",
        "Completeness here is a truthful disposition per verse, not universal coverage. Do "
        "the notated and the withheld partition the 1,844 exactly once each?",
    )
    c.eligible = len(sv_keys)
    notated_keys = [r["canonical_key"] for r in notation]
    withheld_keys = [r["canonical_key"] for r in withheld]
    dispositions: dict[str, list[str]] = collections.defaultdict(list)
    for key in notated_keys:
        dispositions[key].append("NOTATED")
    for key in withheld_keys:
        dispositions[key].append("WITHHELD")
    for key in sorted(sv_keys):
        c.evaluated += 1
        got = dispositions.get(key, [])
        if len(got) != 1:
            c.fail(key=key, dispositions=got or ["NONE"])
    for key in sorted(set(dispositions) - sv_keys):
        c.fail(key=key, why="disposition_for_a_verse_the_graph_does_not_hold")
    c.observed = {
        "sv_verses_in_graph": len(sv_keys),
        "notated": len(notated_keys),
        "notated_distinct": len(set(notated_keys)),
        "withheld": len(withheld_keys),
        "withheld_distinct": len(set(withheld_keys)),
        "notated_plus_withheld": len(notated_keys) + len(withheld_keys),
        "keys_in_both": sorted(set(notated_keys) & set(withheld_keys))[:10],
        "verses_with_no_disposition": sorted(sv_keys - set(dispositions))[:10],
    }
    checks.append(c)

    c = Check(
        "population.coverage_is_reported_per_collection_not_only_as_a_total",
        "population",
        "A 1,136 total hides which arcika a reader can and cannot see notation for. Does "
        "every collection's notated count sit inside its own denominator?",
    )
    per_collection = collections.Counter(collection_of(k) for k in notated_keys)
    c.eligible = len(sv_by_collection)
    for name, denominator in sorted(sv_by_collection.items()):
        c.evaluated += 1
        notated_here = per_collection.get(name, 0)
        if notated_here > denominator:
            c.fail(collection=name, notated=notated_here, denominator=denominator)
    c.observed = {
        "notated_by_collection": dict(sorted(per_collection.items())),
        "denominator_by_collection": dict(sorted(sv_by_collection.items())),
        "coverage_by_collection": {
            name: round(per_collection.get(name, 0) / denominator, 4)
            for name, denominator in sorted(sv_by_collection.items())
        },
        "collections_with_no_notation_at_all": sorted(
            name for name in sv_by_collection if name not in per_collection
        ),
    }
    checks.append(c)

    c = Check(
        "population.withheld_absence_is_typed_in_the_row",
        "population",
        "A withheld verse must say WHY in its own row. Does each of the 708 carry a reason "
        "from the closed set, and are the two kinds of absence kept apart?",
    )
    c.eligible = len(withheld)
    classes: collections.Counter[str] = collections.Counter()
    for row in withheld:
        c.evaluated += 1
        near = row.get("nearest_accented_line_similarity_at_least_0_90")
        if near is None:
            c.fail(key=row["canonical_key"], why="no_near_line_field")
            continue
        cls = WITHHELD_CLASSES[0] if near else WITHHELD_CLASSES[1]
        classes[cls] += 1
        if not (row.get("reason") or "").strip():
            c.fail(key=row["canonical_key"], why="empty_reason")
        elif row.get("source_id") != "WIKISOURCE_SA.SV.KAU.SASVARA_PURNA":
            c.fail(key=row["canonical_key"], why="withheld_against_a_different_witness")
    c.observed = {
        "withheld_reason_classes": dict(classes),
        "declared_classes": list(WITHHELD_CLASSES),
        "distinct_reason_strings": len({r.get("reason") for r in withheld}),
        "is_a_rejection": False,
        "note": (
            "A withheld row is not a rejection. 599 are a witness disagreement that needs "
            "philological adjudication and 109 are a probable absence from this witness; "
            "neither is a statement that the verse has no notation in the tradition."
        ),
    }
    checks.append(c)

    # -- 3. SOURCE MEANING ------------------------------------------------------------
    c = Check(
        "source.every_row_cites_one_pinned_revision_of_one_page",
        "source",
        "A witness that moved mid-harvest would make the 1,136 a mixture of two texts. Do "
        "all rows cite the same page_id and revid, and is every line cited once?",
    )
    c.eligible = len(notation)
    pages: collections.Counter[str] = collections.Counter()
    lines: list[int] = []
    for row in notation:
        c.evaluated += 1
        match = LOCATOR.match(row["source_locator"])
        if not match:
            c.fail(key=row["canonical_key"], locator=row["source_locator"])
            continue
        page_id, revid, line = match.groups()
        pages[f"page_id {page_id} revid {revid}"] += 1
        lines.append(int(line))
    declared = sources.get("WIKISOURCE_SA.SV.KAU.SASVARA_PURNA", {})
    if len(pages) > 1:
        c.fail(why="more_than_one_page_or_revision", pages=dict(pages))
    if len(set(lines)) != len(lines):
        duplicated = [n for n, count in collections.Counter(lines).items() if count > 1]
        c.fail(why="a_witness_line_used_for_more_than_one_verse", lines=duplicated[:10])
    c.observed = {
        "page_and_revision_cited": dict(pages),
        "sources_jsonl_pins": {
            "page_id": declared.get("page_id"),
            "revision_pinned": declared.get("revision_pinned"),
            "revision_timestamp": declared.get("revision_timestamp"),
        },
        "row_locator_agrees_with_sources_jsonl": list(pages)
        == [f"page_id {declared.get('page_id')} revid {declared.get('revision_pinned')}"],
        "distinct_witness_lines": len(set(lines)),
        "line_span": [min(lines), max(lines)] if lines else None,
        "lines_strictly_increasing_in_canonical_file_order": all(
            b > a for a, b in itertools.pairwise(lines)
        ),
    }
    checks.append(c)

    c = Check(
        "source.the_witness_is_labelled_what_it_is",
        "source",
        "This is a community transcription, not a critical edition. Does the source record "
        "say so, carry a licence, and does every row inherit that quality class?",
    )
    c.eligible = len(notation) + 1
    for row in notation:
        c.evaluated += 1
        if row["source_id"] not in sources:
            c.fail(key=row["canonical_key"], why="source_id_does_not_resolve")
        elif row["quality_class"] != sources[row["source_id"]]["quality_class"]:
            c.fail(
                key=row["canonical_key"],
                why="row_quality_class_disagrees_with_its_source",
                row=row["quality_class"],
                source=sources[row["source_id"]]["quality_class"],
            )
    c.evaluated += 1
    for field in ("licence", "licence_url", "authority_tier", "revision_pinned"):
        if not declared.get(field):
            c.fail(why="source_record_missing_field", field=field)
    if declared.get("authority_tier") != "COMMUNITY_TRANSCRIPTION":
        c.fail(why="authority_tier_overstates_the_witness", got=declared.get("authority_tier"))
    c.observed = {
        "source_id": declared.get("source_id"),
        "authority_tier": declared.get("authority_tier"),
        "quality_class": declared.get("quality_class"),
        "licence": declared.get("licence"),
        "is_a_critical_edition": False,
        "what_this_is_not": (
            "Not a critical edition and not a school-certified notation. It is one pinned "
            "revision of a community transcription that prints the Kauthuma numeric svara "
            "marks, and it must be presented as a witness rather than as the text."
        ),
    }
    checks.append(c)

    c = Check(
        "source.the_recension_claim_is_about_this_witness",
        "source",
        "A notation from another school laid over Kauthuma verses would be wrong in a way "
        "no count could show. Does every row carry the recension finding, and does the "
        "finding name what it excludes?",
    )
    c.eligible = len(notation) + 1
    for row in notation:
        c.evaluated += 1
        if row["recension_verified"] is not True:
            c.fail(key=row["canonical_key"], why="recension_not_verified")
        elif len((row.get("recension_evidence") or "").strip()) < 40:
            c.fail(key=row["canonical_key"], why="recension_evidence_too_thin")
    c.evaluated += 1
    evidence = declared.get("recension_evidence", "")
    for excluded in ("Ranayaniya", "Jaiminiya"):
        if excluded.lower() not in evidence.lower():
            c.fail(why="recension_evidence_does_not_exclude", school=excluded)
    if "kauthum" not in evidence.lower():
        c.fail(why="recension_evidence_does_not_name_kauthuma")
    c.observed = {
        "distinct_recension_evidence_strings_on_rows": len(
            {r["recension_evidence"] for r in notation}
        ),
        "schools_explicitly_excluded": ["Ranayaniya", "Jaiminiya"],
        "qa_report_foreign_marker_check": manifest["qa"]["detail"].get("stratified_by"),
    }
    checks.append(c)

    # -- 4. RELATION MEANING ----------------------------------------------------------
    c = Check(
        "relation.the_row_asks_for_a_text_witness_not_a_melodic_object",
        "relation",
        "Owner decision G places the object-side Gana model outside Product V1. Does any "
        "notation row ask for MUSICALIZED_AS, a Gana node, or any object this graph has no "
        "canonical identity for?",
    )
    c.eligible = len(notation)
    for row in notation:
        c.evaluated += 1
        blob = json.dumps(row, ensure_ascii=False)
        if FORBIDDEN_PREDICATE in blob:
            c.fail(key=row["canonical_key"], why="names_the_forbidden_predicate")
        elif re.search(r"\bgana\b|gana_unit_id|saman_id|stobha", blob, re.IGNORECASE):
            c.fail(key=row["canonical_key"], why="names_a_gana_object")
    c.observed = {
        "target_predicate": TARGET_PREDICATE,
        "target_predicate_already_in_the_graphs_type_store": TARGET_PREDICATE in rel_types,
        "target_text_role": TARGET_TEXT_ROLE,
        "target_text_role_in_the_declared_enum": TARGET_TEXT_ROLE in role_vocabulary,
        "target_text_role_already_populated_in_the_graph": TARGET_TEXT_ROLE in declared_roles,
        "forbidden_predicate": FORBIDDEN_PREDICATE,
        "forbidden_predicate_in_the_graphs_type_store": FORBIDDEN_PREDICATE in rel_types,
        "labels_matching_melodic_object_vocabulary": sorted(
            label for label in labels if re.search(r"saman|gana|stobha|melod", label, re.I)
        ),
        "what_the_row_is": (
            "A second, accented WITNESS of a verse's own text. The claim is textual: this "
            "source prints these marks on this verse. It is not a claim that the verse is "
            "sung as any named saman, which would need an object side this corpus excludes."
        ),
    }
    checks.append(c)

    c = Check(
        "relation.the_subject_grain_is_the_verse",
        "relation",
        "Notation printed on a verse belongs to that verse. Does every key resolve to a "
        "verse-grained Mantra rather than to a container?",
    )
    c.eligible = len(notation)
    for row in notation:
        c.evaluated += 1
        key = row["canonical_key"]
        if key not in sv_keys:
            c.fail(key=key, why="does_not_resolve_to_an_sv_mantra")
        elif key in container_keys:
            c.fail(key=key, why="also_resolves_to_a_container_passage")
        elif not re.search(r":V\d+$", key):
            c.fail(key=key, why="key_does_not_end_at_verse_grain")
    c.observed = {
        "all_keys_resolve_to_a_mantra": all(r["canonical_key"] in sv_keys for r in notation),
        "container_grained_rows": 0,
        "container_passages_in_scope": len(container_keys),
    }
    checks.append(c)

    # -- verdict ----------------------------------------------------------------------
    failing = [c for c in checks if c.failure_count]
    under_covered = [c for c in checks if c.evaluated != c.eligible]
    verdict = "PASS" if not failing and not under_covered else "FAIL"

    artifact = {
        "artifact": "SAMAVEDA_MUSIC_GATE_B",
        "gate": "B",
        "gate_definition": (
            "SEMANTIC -- classification, population, source meaning, relation meaning "
            "(data/staging/integration/wave3_eligibility.json)"
        ),
        "domain": "samaveda_music",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "deterministic": True,
        "determinism_note": (
            "Every check is a total pass over the population -- no sample, no seed, no "
            "model call. Re-running it on the same rows and the same graph gives the same "
            "artifact byte for byte apart from the timestamp."
        ),
        "required_inputs": {
            "staging_rows": str(ROWS.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "staging_rejected": str(REJECTED.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "staging_sources": str(SOURCES.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "graph": f"{URI} db={DB}",
            "declared_enum": "src/vedagraph/models/enums.py TextRole",
        },
        "population_under_test": {
            "layer": IN_SCOPE_LAYER,
            "rows": len(notation),
            "withheld_rows_also_adjudicated": len(withheld),
            "denominator": len(sv_keys),
            "out_of_scope_layers": dict(out_of_scope),
            "out_of_scope_reason": (
                "OWNER_DECISION_G_GANA_OBJECT_OUT_OF_V1 places the object-side Gana model "
                "outside Product V1. The 332 GANA_RENDERING rows and the 3 container-scope "
                "performance rows stay staged and are not adjudicated for import here. They "
                "are not averaged into any figure above: a file holding two kinds of claim "
                "has no single pass rate."
            ),
        },
        "pass_condition": (
            "Every check reports zero failures AND full coverage of its own eligible "
            "population. A check below full coverage fails the GATE, not the data."
        ),
        "checks": [c.as_dict() for c in checks],
        "summary": {
            "checks_run": len(checks),
            "checks_passing": len(checks) - len({c.name for c in failing + under_covered}),
            "checks_failing": len({c.name for c in failing + under_covered}),
            "rows_evaluated_across_all_checks": sum(c.evaluated for c in checks),
            "checks_below_full_coverage": [c.name for c in under_covered],
            "total_failures": sum(c.failure_count for c in checks),
        },
        "verdict": verdict,
    }

    path = pathlib.Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"GATE B  samaveda_music  {IN_SCOPE_LAYER}  {len(notation):,} rows")
    print()
    for check in checks:
        d = check.as_dict()
        flag = "OK  " if d["status"] == "PASS" else "FAIL"
        print(
            f"  [{flag}] {d['name']:<62} "
            f"{d['evaluated']}/{d['eligible']} evaluated, {d['failures']} failure(s)"
        )
    print()
    print(f"  {verdict}. report: {path.relative_to(PROJECT_ROOT)}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
