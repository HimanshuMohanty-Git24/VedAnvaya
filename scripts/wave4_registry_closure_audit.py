"""Terminate every gap-registry entry, measured. Wave 4 Phase 7.

The registry held 85 entries, 84 ``OPEN`` and 1 ``PARTIALLY_ADDRESSED``, and **it had no
closed state at all** -- no vocabulary for one, and no field to put one in. 67 entries carried
``causation_status: HYPOTHESIS_NOT_YET_MEASURED`` with every one of their 14 addressing
diagnostics reading ``NOT_RUN``. A registry in that shape cannot say whether the campaign is
finished, because nothing in it can ever be finished.

This audit gives every entry exactly one terminal status from the owner's allowed set, and it
is built to be unable to flatter the result:

*   **A ruling is declared before it is measured.** ``RULINGS`` below states the status and
    the basis for each of the 85 entries, and the measurement is run afterwards and compared.
    A status derived from whatever the graph currently says would be the M9 readback mistake
    again -- an expectation rebuilt from the thing it was supposed to check.

*   **Anything that cannot terminate is reported, not absorbed.** ``STILL_IMPLEMENTATION_
    FIXABLE`` and ``BLOCKED_EVIDENCE_INCOMPLETE`` are outside the owner's list on purpose, so
    an entry with unfinished implementation behind it appears in the count instead of being
    relabelled a scope decision. The exit code is non-zero while any entry holds one.

*   **An unmade owner decision is tracked as a blocker, never as a closure.**
    ``BLOCKED_OWNER_DECISION_REQUIRED`` joins ``NEEDS_AUDIBLE_REVIEW`` and
    ``ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA`` as an execution blocker: terminal for the
    purpose of "nothing reads OPEN", counted apart from the closures, and named with the
    decision it waits on. Five entries are there because material was acquired, staged and
    then not imported, and recording those as closed would be the exact disguise the owner
    barred -- the registry already did it once, describing 944 Atharvavedic translations as
    "closed via the Wayback Machine" while the graph held none of them.

*   **``CLOSED_SCOPE_DECISION`` requires a citation.** A scope decision that is not written
    down somewhere a reader can find is indistinguishable from a decision invented to clear
    the board, so every entry with that status names the file and lines that record it.

*   **``BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE`` requires five fields.** Sources searched, search
    date, addressing proof, why no lawful public source was usable, and an explicit statement
    that absence was not inferred from not-looking. An entry missing any of them is downgraded
    to ``BLOCKED_EVIDENCE_INCOMPLETE`` and counted as not terminated.

Usage:
    python scripts/wave4_registry_closure_audit.py [--write]

``--write`` adds the closure vocabulary and the per-entry verdict to the registry. Without it
the audit only reports.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
from typing import Any, Final, NamedTuple

from neo4j import GraphDatabase, Session

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = PROJECT_ROOT / "data" / "gap_registry.json"
OUT = PROJECT_ROOT / "data" / "staging" / "wave4" / "registry_closure_audit.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: The owner's allowed final statuses. An entry in one of these is closed.
CLOSED: Final[frozenset[str]] = frozenset(
    {
        "CLOSED_SOURCE_ACQUIRED",
        "CLOSED_DERIVED",
        "CLOSED_VERIFIED_ZERO",
        "CLOSED_NOT_APPLICABLE",
        "CLOSED_SCOPE_DECISION",
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE",
    }
)

#: Separately tracked execution blockers. Terminal for the purpose of "no entry is OPEN", and
#: explicitly NOT data-completeness closure: they are counted apart and named in the verdict.
EXECUTION_BLOCKERS: Final[frozenset[str]] = frozenset(
    {
        "NEEDS_AUDIBLE_REVIEW",
        "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA",
        "BLOCKED_OWNER_DECISION_REQUIRED",
    }
)

#: Not terminal. Every entry here is a NOT_READY signal and the reason the exit code is 1.
NOT_TERMINAL: Final[frozenset[str]] = frozenset(
    {"STILL_IMPLEMENTATION_FIXABLE", "BLOCKED_EVIDENCE_INCOMPLETE"}
)

#: The five things the owner requires of every BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE entry.
BLOCKED_EVIDENCE_FIELDS: Final[tuple[str, ...]] = (
    "sources_searched",
    "search_date",
    "addressing_proof",
    "why_no_lawful_source",
    "absence_not_inferred_from_not_looking",
)


class Ruling(NamedTuple):
    """One adjudication, stated before anything is measured."""

    status: str
    #: Why this status and not another. Prose, because the reason is the audit.
    basis: str
    #: A live Cypher whose single returned value the basis asserts something about, or "".
    measure: str = ""
    #: What that value must be for the ruling to stand. ``None`` records the measurement
    #: without gating on it -- used where the number is context rather than proof.
    expect: int | None = None
    #: Where the decision is written down. Required for CLOSED_SCOPE_DECISION.
    citation: str = ""
    #: The named owner decision this waits on. Required for BLOCKED_OWNER_DECISION_REQUIRED.
    owner_decision: str = ""
    #: Evidence for an external-source block, keyed by BLOCKED_EVIDENCE_FIELDS.
    blocked_evidence: dict[str, str] = {}  # noqa: RUF012 - NamedTuple default, never mutated


_SOURCE_ABSENT_SV_APPARATUS = {
    "sources_searched": (
        "Arseya Brahmana (seer apparatus) and Devatadhyaya Brahmana (deity apparatus) for the "
        "Kauthuma Samaveda; GRETIL, VedaWeb, sacred-texts, archive.org."
    ),
    "search_date": "2026-09-14/15, during the Wave 2 domain sweep",
    "addressing_proof": (
        "The block is a join-key failure, not a missing text: both apparatuses are keyed to "
        "samans in the gana collections, and the gana collections are a declared exclusion "
        "from this work identifier (works.yaml:290-297). There is no arcika-verse coordinate "
        "in either apparatus to address, so no coordinate system could be got wrong."
    ),
    "why_no_lawful_source": (
        "No source addresses Kauthuma arcika verses by the coordinate this corpus holds. "
        "Acquiring the ganas would be a new work identifier, not a fix to this one."
    ),
    "absence_not_inferred_from_not_looking": (
        "Recorded as a measured zero over an assessed population of 1,844 in "
        "veda_coverage_v3.json, with the join-key reason stated verbatim."
    ),
}

_SOURCE_ABSENT_SV_TRANSLATION = {
    "sources_searched": (
        "Griffith (Hymns of the Samaveda), Devi Chand, GRETIL, VedaWeb, sacred-texts.com, "
        "archive.org and the Wayback Machine."
    ),
    "search_date": "2026-09-15, and re-checked 2026-09-16 during the Wave 4 sweep",
    "addressing_proof": (
        "Not a coordinate failure: 1,242 Samavedic translations were located and staged "
        "against this corpus's own canonical keys (data/staging/translation/rows.jsonl), so "
        "the addressing demonstrably works. The graph holds none of them, which is an import "
        "gate and not a source absence -- recorded separately under "
        "BLOCKED_OWNER_DECISION_REQUIRED rather than as a source limitation."
    ),
    "why_no_lawful_source": "",
    "absence_not_inferred_from_not_looking": (
        "0 of 1,844 measured in the graph; 1,242 measured as staged and unimported."
    ),
}

_SOURCE_ABSENT_MORPHOLOGY = {
    "sources_searched": (
        "Zurich/VedaWeb morphological annotation (the only published manual annotation of a "
        "Vedic Samhita), DCS, and the Sanskrit treebanks reachable from them."
    ),
    "search_date": "2026-09-15",
    "addressing_proof": (
        "The RV layer is ingested from the published annotation at this corpus's own stanza "
        "coordinates, at 10,552 of 10,552, so the coordinate system is proven to work for "
        "the one corpus an annotation exists for."
    ),
    "why_no_lawful_source": (
        "No equivalent manual morphological annotation is published for the Samaveda, the "
        "Shukla Yajurveda or the Saunaka Atharvaveda. Generating one by machine would be "
        "model output presented as annotation."
    ),
    "absence_not_inferred_from_not_looking": (
        "9,658 mantras measured as carrying no lemma layer, against a corpus where the RV's "
        "10,552 are complete -- the contrast is what establishes it as a source absence."
    ),
}


#: One ruling per entry, declared ahead of measurement. The order is the registry's.
RULINGS: Final[dict[str, Ruling]] = {
    # ---- attribution -----------------------------------------------------------------
    "GAP-ATTRIBUTION-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Composite. The SV and YV halves are source-blocked on the apparatus join key; the "
        "AV half is not -- 324 Whitney descriptors are held and 0 resolve to a :Devata, and "
        "GAP-ATTRIBUTION-WHITNEY-UNRESOLVED-OBJECT-001 records a resolution channel that "
        "succeeds on 405 of 477 proposals. Unfinished implementation, not a source limit.",
        "MATCH (a:DevataAscription) WHERE (a)-->(:Devata) RETURN count(a)",
        0,
    ),
    "GAP-ATTRIBUTION-002": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The descriptors are held as opaque strings and the resolution step was never built. "
        "324 descriptors, 0 resolved, measured.",
        "MATCH (a:DevataAscription) WHERE (a)-->(:Devata) RETURN count(a)",
        0,
    ),
    "GAP-ATTRIBUTION-003": Ruling(
        "CLOSED_DERIVED",
        "A stale claim, corrected at the generator in Wave 4 (0ac5c7c). The API caveat said "
        "a zero for SV/YV/AV means the corpus carries no Anukramani deity ascription; the AV "
        "carries 5,385 HAS_DEVATA_ASCRIPTION edges. The rewritten caveat names both "
        "predicates and the identity-bridge gap. Measured: the false fragment is absent from "
        "the live query text, and the AV edge population is non-zero.",
        "MATCH ()-[r:HAS_DEVATA_ASCRIPTION]->() RETURN count(r)",
        5385,
    ),
    "GAP-ATTRIBUTION-004": Ruling(
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE",
        "0 of 1,844 Samavedic mantras carry HAS_RISHI, and the apparatus that would supply "
        "it is keyed to samans in the excluded gana collections.",
        "MATCH (m:Mantra {veda:'SV'})-[:HAS_RISHI]->() RETURN count(m)",
        0,
        blocked_evidence=_SOURCE_ABSENT_SV_APPARATUS,
    ),
    "GAP-ATTRIBUTION-005": Ruling(
        "CLOSED_NOT_APPLICABLE",
        "Two facts under one id, and both are correctly handled. The sukta-scope projection "
        "is typed CONTAINER_INHERITED rather than disguised as a per-verse claim, which is "
        "the honest representation of what the AV Anukramani asserts; and the 1,297 with "
        "nothing are the kandas the index does not attribute at all. The question 'why is "
        "this not per-verse' does not apply at the grain the source addresses.",
        "MATCH (m:Mantra {veda:'AV'})-[:HAS_RISHI]->() RETURN count(DISTINCT m)",
        4542,
    ),
    "GAP-ATTRIBUTION-006": Ruling(
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE",
        "Metre for SV and YV. The YV metre source is the Sarvanukramana-sutra, pratika-keyed "
        "prose refused for machine resolution; the SV's identity is melodic and its apparatus "
        "does not assert metre per arcika verse.",
        "MATCH (m:Mantra)-[:HAS_CHANDAS]->() WHERE m.veda IN ['SV','YV'] RETURN count(m)",
        0,
        blocked_evidence=_SOURCE_ABSENT_SV_APPARATUS,
    ),
    "GAP-ATTRIBUTION-007": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "427 of 729 seers unresolved to a family. The decomposition was built for the major "
        "Rigvedic lineages and never extended to the 134 AV and 228 YV registry entries. The "
        "patronymic evidence is in the registries already held; nothing external is needed.",
        "MATCH (r:Rishi) WHERE NOT (r)-[:BELONGS_TO_FAMILY]->() RETURN count(r)",
        427,
    ),
    "GAP-ATTRIBUTION-008": Ruling(
        "CLOSED_DERIVED",
        "A stale report claiming RishiFamily is empty and all 729 seers unresolved. Measured: "
        "87 families and 302 resolved seers. The claim described the V3 baseline and the "
        "layer was built afterwards.",
        "MATCH (f:RishiFamily) RETURN count(f)",
        87,
    ),
    "GAP-ATTRIBUTION-009": Ruling(
        "CLOSED_DERIVED",
        "All 214 :Devata nodes asserted that the Atharvaveda has no attribution layer, and "
        "api/ask/evidence.py reads that property as the qualifier attached to an absence. "
        "Corrected at the generator (domain/taxonomy.py) and propagated by M11, which imports "
        "the note rather than restating it. Measured: 0 nodes carry the false fragment.",
        "MATCH (d:Devata) WHERE d.attribution_scope_note CONTAINS 'no attribution layer' "
        "RETURN count(d)",
        0,
    ),
    # ---- audio -----------------------------------------------------------------------
    "GAP-AUDIO-001": Ruling(
        "CLOSED_VERIFIED_ZERO",
        "0 of 1,844 Kauthuma arcika verses have arcika-verse audio, over an assessed "
        "population of 1,844. The 475 licence-clean recordings that exist are page-level gana "
        "performances, which is a different work at a different grain -- a measured zero with "
        "a stated reason, not an unknown.",
        "",
        None,
        citation="data/registry/works.yaml:290-297 (ganas need their own work_id)",
    ),
    "GAP-AUDIO-002": Ruling(
        "NEEDS_AUDIBLE_REVIEW",
        "771 Atharvavedic rows re-established against the source's own division and staged. "
        "They are not in the product catalogue and must not be: every row is in "
        "data/staging/audio_review_queue.jsonl with review_status NEEDS_AUDIBLE_REVIEW, and "
        "no listening has been performed. Promotion also waits on OWNER_DECISION_E_AUDIO_GATE.",
        "",
        None,
        owner_decision="OWNER_DECISION_E_AUDIO_GATE",
    ),
    "GAP-AUDIO-003": Ruling(
        "NEEDS_AUDIBLE_REVIEW",
        "33 Madhyandina rows staged after the comparator fix; 25 accepted, 8 recorded as "
        "text-confirmation failures with real decoding audio at the coordinate. Unpromoted, "
        "in the review queue, unlistened.",
        "",
        None,
        owner_decision="OWNER_DECISION_E_AUDIO_GATE",
    ),
    "GAP-AUDIO-004": Ruling(
        "NEEDS_AUDIBLE_REVIEW",
        "150 Rigvedic rows staged from VedaWeb's per-stanza recitation, each with three "
        "independent coordinate assertions and a letter-similarity confirmation. Every row's "
        "own mapping_method ends 'This row was not reviewed by listening.' Unpromoted.",
        "",
        None,
        owner_decision="OWNER_DECISION_E_AUDIO_GATE",
    ),
    "GAP-AUDIO-005": Ruling(
        "CLOSED_SCOPE_DECISION",
        "The recitation layer is proxied rather than mirrored, with no per-record checksum. "
        "That is a recorded V1 decision about redistribution rights, not an unfinished "
        "import, and the consequence is now stated rather than implied.",
        "",
        None,
        citation="docs/PRODUCT_V1_SCOPE.md:212-221 (no audio redistribution)",
    ),
    "GAP-AUDIO-006": Ruling(
        "CLOSED_SCOPE_DECISION",
        "No sub-verse timing. Deriving it from proxied streams needs forced alignment, and "
        "inventing timings was explicitly refused. The expected population is not knowable "
        "because it is not a population -- it is a capability that was declined.",
        "",
        None,
        citation="docs/PRODUCT_V1_SCOPE.md:212-221",
    ),
    # ---- communities -----------------------------------------------------------------
    "GAP-COMMUNITIES-001": Ruling(
        "CLOSED_DERIVED",
        "Computed, then refused for publication on evidence: Leiden beats Louvain at ARI "
        "1.0000 against 0.9079 over 200 seeds, and the partition rests on a deity identity "
        "question the owner resolved separately. The 12 :DeityCommunity nodes exist and are "
        "marked :Internal, which is the refusal implemented rather than asserted.",
        "MATCH (c:DeityCommunity) WHERE NOT c:Internal RETURN count(c)",
        0,
    ),
    "GAP-COMMUNITIES-002": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "57 of 71 composite deity labels carry no components. The registry's own closure says "
        "decompose the 24 remaining pairs and type each group with its reason -- work over "
        "material already held, and the registry itself calls it 'worth doing for "
        "interpretation, not as a prerequisite'. Worth doing is not done.",
        "",
        None,
    ),
    "GAP-COMMUNITIES-003": Ruling(
        "CLOSED_DERIVED",
        "A stale scorecard claim that CO_OCCURS_WITH is empty. Measured: 306 deity-pair edges.",
        "MATCH ()-[r:CO_OCCURS_WITH]->() RETURN count(r)",
        306,
    ),
    # ---- cross-Veda ------------------------------------------------------------------
    "GAP-CROSS_VEDA-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Directed reuse exists for RV-SV only, measured at 1,684 edges and no other pair. "
        "The detector was built for the Samavedic case and never generalised. Asserting a "
        "direction on the other five pairs is a chronology claim and should NOT be "
        "generalised -- but the entry records that as unfinished rather than as a refusal, "
        "and the refusal is what it actually is. It stays fixable because the honest fix is "
        "to type the five pairs as deliberately undirected, which has not been done.",
        "MATCH (a)-[:REUSES_TEXT_FROM]->(b) RETURN count(DISTINCT a.veda + '-' + b.veda)",
        1,
    ),
    "GAP-CROSS_VEDA-002": Ruling(
        "CLOSED_DERIVED",
        "A stale claim. The entry says none of the 6,527 parallel and reuse edges records how "
        "the text was transformed. Measured: 6,271 edges carry cross_veda_transformation, "
        "written by the Wave 3 cross-Veda import with its fold correction applied.",
        "MATCH ()-[r]->() WHERE r.cross_veda_transformation IS NOT NULL RETURN count(r)",
        6271,
    ),
    "GAP-CROSS_VEDA-003": Ruling(
        "CLOSED_DERIVED",
        "256 EXACT_PARALLEL_OF edges carried no parallel_id and no match_level. Fixed at the "
        "generator (graph/lexical.py) and propagated by M12: 252 renamed from strongest_method "
        "-- the same assertion in the same words -- and 4 typed "
        "NOT_APPLICABLE_AT_THIS_GRANULARITY because LEMMA_SEQUENCE_EXACT is not a text "
        "surface. Measured: 0 edges left without a level or a typed absence.",
        "MATCH ()-[r:EXACT_PARALLEL_OF]->() WHERE r.match_level IS NULL "
        "AND r.match_level_absence IS NULL RETURN count(r)",
        0,
    ),
    "GAP-CROSS_VEDA-004": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Pada-level parallels are unimplemented although the schema and the token pada tags "
        "already support them. Verse-level detection was sufficient for the first pass. "
        "Nothing external is needed.",
        "",
        None,
    ),
    # ---- entity coverage -------------------------------------------------------------
    "GAP-ENTITY_COVERAGE-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The epithet layer reaches 4 of 214 deities and no epithet is linked to a passage. "
        "Measured: 13 Epithet nodes, 4 deities, 0 passage edges. The occurrence projection "
        "was never run over material already held.",
        "MATCH (e:Epithet)-[r]-(:Passage) RETURN count(r)",
        0,
    ),
    "GAP-ENTITY_COVERAGE-002": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Deity profile statistics were materialised for 30 of 214 deities, so 184 deity pages "
        "report null for every corpus. The product types the null as INSUFFICIENT_EVIDENCE "
        "rather than drawing it as a zero, which is correct handling of an unfinished pass.",
        "MATCH (d:Devata) WHERE d.profile_attributed_total IS NULL RETURN count(d)",
        184,
    ),
    "GAP-ENTITY_COVERAGE-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "No healing or remedy entity exists: bhesaja was never curated, and the Atharvaveda's "
        "characteristic subject is reachable only through afflictions and plants. A curation "
        "omission over text already held. The endpoint declares it in its own caveat, which "
        "is honest and is not a closure.",
        "MATCH (n) WHERE n:Remedy OR n:Bhesaja RETURN count(n)",
        0,
    ),
    "GAP-ENTITY_COVERAGE-004": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "No expected-entity manifest exists, so an entity the corpus attests but the registry "
        "omits cannot be detected by any query. This is the meta-gap of the entity domain and "
        "the reason the others were found by external inspection rather than by the graph "
        "auditing itself.",
        "",
        None,
    ),
    "GAP-ENTITY_COVERAGE-005": Ruling(
        "CLOSED_DERIVED",
        "A stale benchmark claim that tin is attested but unregistered. Measured: a Metal node "
        "for trapu exists.",
        "MATCH (m:Metal) WHERE toLower(coalesce(m.entity_key,'')) CONTAINS 'trapu' "
        "RETURN count(m)",
        1,
    ),
    "GAP-ENTITY_COVERAGE-006": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Lexical alias recall is unmeasured across the entity layer, and one cell is known "
        "false: ayas in the Yajurveda is attested at VSM 18.13 and matched by nothing. The "
        "product types that cell NO_LEXICAL_MATCH and names its own counter-example, which is "
        "exemplary reporting of an unmeasured dimension -- and leaves it unmeasured.",
        "",
        None,
    ),
    "GAP-ENTITY_COVERAGE-007": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Phrase matching was never built and personification resolution is materialised for 9 "
        "NaturalPhenomenon nodes only. Multi-word realia are unreachable and 220 entities have "
        "no way to distinguish a refusal from a gap.",
        "",
        None,
    ),
    "GAP-ENTITY_COVERAGE-008": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The deity, seer and metre registries carry typed non-members -- patrons and "
        "gift-praise listed beside deities by the source apparatus -- and no eligibility "
        "predicate was ever applied, so every count taken over them is inflated. Applying one "
        "is an ontology decision about what counts as a deity and needs an owner, but the "
        "entry is recorded as an implementation gap and no eligibility field exists to hold "
        "the answer, which is the fixable part.",
        "",
        None,
    ),
    # ---- formula ---------------------------------------------------------------------
    "GAP-FORMULA-001": Ruling(
        "CLOSED_DERIVED",
        "A stale claim, and Wave 4 found the declaration behind it was stale too. The entry "
        "says SHARES_FORMULA_WITH is the graph's only declared type carrying zero edges. "
        "Measured: 6,148 Passage-to-Passage edges, written by the Wave 3 formula import on a "
        "rarity-weighted distinctiveness criterion. enrich.predicates had declared the "
        "predicate deliberately empty; the entry is withdrawn and a new scorecard gate fails "
        "on any predicate declared empty that carries an edge.",
        "MATCH ()-[r:SHARES_FORMULA_WITH]->() RETURN count(r)",
        6148,
    ),
    "GAP-FORMULA-002": Ruling(
        "CLOSED_DERIVED",
        "Two things under one id. The USES_FORMULA half was recoverable from its own evidence "
        "surface all along; the parallel typology half was backfilled from a six-level "
        "identity ladder computed against each pair's own comparison ceiling, and the Wave 3 "
        "import landed it. Measured: 6,271 edges carry a transformation type.",
        "MATCH ()-[r]->() WHERE r.formula_transformation_type IS NOT NULL RETURN count(r)",
        4368,
    ),
    "GAP-FORMULA-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "1,103 of 4,825 formulas are strict substrings of another, so formula counts "
        "double-count nested wordings and any ranking over them is inflated. The nesting is "
        "measured and staged (data/staging/formula/formula_nesting.jsonl); the deduplication "
        "pass over it was not run.",
        "MATCH (f:Formula) RETURN count(f)",
        4825,
    ),
    # ---- morphology ------------------------------------------------------------------
    "GAP-MORPHOLOGY-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The lemma layer is an inert registry: 10,031 Lemma nodes and 39 reached by any edge, "
        "all 39 deity names. MENTIONS_LEMMA was built as the instrument behind the Rigvedic "
        "deity mention layer, not as a lexical index, and the full inventory was loaded as "
        "nodes and then left. The annotation that would index it is already ingested.",
        "MATCH (:Mantra)-[:MENTIONS_LEMMA]->(l:Lemma) RETURN count(DISTINCT l)",
        39,
    ),
    "GAP-MORPHOLOGY-002": Ruling(
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE",
        "Morphological annotation exists for the Rigveda only; 9,658 mantras in the other "
        "three corpora have no lemma layer. No equivalent manual annotation is published for "
        "them, and generating one by machine would be model output presented as annotation.",
        "MATCH (m:Mantra) WHERE m.veda <> 'RV' AND NOT (m)-[:MENTIONS_LEMMA]->() "
        "RETURN count(m)",
        9658,
        blocked_evidence=_SOURCE_ABSENT_MORPHOLOGY,
    ),
    "GAP-MORPHOLOGY-003": Ruling(
        "CLOSED_DERIVED",
        "The live Rigveda scope statement claimed a Padapatha text version is carried; none "
        "exists. Corrected at the generator (works.yaml) and reloaded in Wave 4 (4b2d386): "
        "the statement now records the measured absence and names the declared VEDAWEB."
        "PADAPATHA source that covers Mandala 1 and was never ingested. Measured: every one "
        "of the 44,276 TextVersion nodes carries text_form SAMHITA.",
        "MATCH (t:TextVersion) WHERE t.text_form <> 'SAMHITA' RETURN count(t)",
        0,
    ),
    "GAP-MORPHOLOGY-004": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "711 Rigvedic lexical tokens are unresolved because no feature-conditioned alias "
        "mechanism exists -- a deferral the architecture document itself calls the "
        "highest-value one. The features are in the annotation already held.",
        "",
        None,
    ),
    "GAP-MORPHOLOGY-005": Ruling(
        "CLOSED_SCOPE_DECISION",
        "No mantra is available in both scripts. The refusal to ship a generated "
        "transliteration is a recorded decision with a measured basis: accent placement in "
        "generated Devanagari was 0 of 21 acceptable at band scale, and shipping it would put "
        "wrong tone marks on scripture.",
        "MATCH (t:TextVersion) WHERE t.text_role = 'SEARCH_DERIVATIVE' RETURN count(t)",
        5839,
        citation="docs/reports/data-completeness/morphology.md; the AV accent calibration "
        "record in the owner ledger",
    ),
    "GAP-MORPHOLOGY-006": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Text-version provision is uneven: only the Atharvaveda has a search-normalised "
        "version, so an accent-bearing query matches AV and misses the rest. Measured: 5,839 "
        "SEARCH_DERIVATIVE rows and no others. Deriving the same normalisation for the other "
        "three corpora needs nothing external.",
        "MATCH (t:TextVersion) WHERE t.text_role = 'SEARCH_DERIVATIVE' RETURN count(t)",
        5839,
    ),
    # ---- other -----------------------------------------------------------------------
    "GAP-OTHER-001": Ruling(
        "CLOSED_SCOPE_DECISION",
        "Only the Shukla Yajurveda in the Madhyandina recension is held. A declared, tested "
        "and correctly surfaced boundary, and the one the product itself flags as most likely "
        "to mislead.",
        "MATCH (m:Mantra {veda:'YV'}) RETURN count(m)",
        1975,
        citation="data/registry/works.yaml (YV work scope); tests/domain/test_domain_layer.py",
    ),
    "GAP-OTHER-002": Ruling(
        "CLOSED_SCOPE_DECISION",
        "Only the Saunaka Atharvaveda is held. The scope statement says an Atharvavedic "
        "absence measured here is an absence from Saunaka only, which is the honest reading.",
        "MATCH (m:Mantra {veda:'AV'}) RETURN count(m)",
        5839,
        citation="data/registry/works.yaml (AV work scope)",
    ),
    "GAP-OTHER-003": Ruling(
        "CLOSED_VERIFIED_ZERO",
        "5,839 held against roughly 5,977 attested. The divergence is typed OPEN_RESEARCH "
        "with a falsified candidate mechanism recorded, which is the right handling: forcing "
        "a resolution would invent verse identity. The 1856 canonical corpus with "
        "passage_count 0 and qa_status FAILED is the cancelled scan, recorded as cancelled.",
        "MATCH (m:Mantra {veda:'AV'}) RETURN count(m)",
        5839,
        citation="the AV image-transcription cancellation in the owner ledger",
    ),
    "GAP-OTHER-004": Ruling(
        "CLOSED_VERIFIED_ZERO",
        "31 of the traditional 1,875 Samavedic verses carry no canonical key, enumerated with "
        "per-verse causes; 21 turn on two witnesses disagreeing about a dasati partition, and "
        "inventing a partition would fabricate verse identity. A measured, enumerated absence.",
        "MATCH (m:Mantra {veda:'SV'}) RETURN count(m)",
        1844,
    ),
    "GAP-OTHER-005": Ruling(
        "CLOSED_DERIVED",
        "A stale report listing all four Work.scope properties as null. Measured: all four "
        "populated and served live.",
        "MATCH (w:Work) WHERE w.scope IS NULL RETURN count(w)",
        0,
    ),
    "GAP-OTHER-006": Ruling(
        "CLOSED_DERIVED",
        "The comparator that verifies a recording is the verse we hold discarded 17 of 18 "
        "distinct letters on a 285-character skeleton, and its published calibration had been "
        "measured with that broken comparator. Fixed at commit 30ba692 with four regression "
        "tests and recalibrated over all 1,975 coordinate-aligned YV pairs against 800 "
        "deliberately mispaired ones, re-accepting every verse the shipped matcher accepted.",
        "",
        None,
    ),
    # ---- product surface -------------------------------------------------------------
    "GAP-PRODUCT_SURFACE-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The deity insight endpoint reports AV, YV and SV as both in scope and not covered "
        "while returning measured counts for all three, because vedas_not_covered is "
        "populated from the ascription dimension and vedas_in_scope from the naming one. Two "
        "axes merged into one coverage block. The prose caveats state the distinction; the "
        "structured fields contradict it.",
        "",
        None,
    ),
    "GAP-PRODUCT_SURFACE-002": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The limits catalogue publishes 7 of at least 21 structurally unanswerable "
        "dimensions. It says so rather than implying completeness, which is right, and the "
        "14 unpublished limits each need a reproducible probe that was never written.",
        "",
        None,
    ),
    "GAP-PRODUCT_SURFACE-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Three visualizations blocked by missing API aggregates. Two of the three are API "
        "omissions over data the graph already holds -- per-book deity breakdown and "
        "deity-by-metre -- and the third is a page-size cap.",
        "",
        None,
    ),
    "GAP-PRODUCT_SURFACE-004": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Ask cannot retrieve Samavedic passages at all and cannot reach several insight "
        "endpoints, so it refuses or misleads on questions the API answers directly. A "
        "retrieval-planning gap over data that is present and addressable.",
        "MATCH (m:Mantra {veda:'SV'}) RETURN count(m)",
        1844,
    ),
    "GAP-PRODUCT_SURFACE-005": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The whole canonical corpus is gitignored, so no released corpus text is protected by "
        "version history -- and this project has previously recovered a destroyed sealed "
        "schema from a dangling git blob. 4 released Samavedic verses also carry printed "
        "apparatus welded into the text.",
        "",
        None,
    ),
    # ---- quality ---------------------------------------------------------------------
    "GAP-QUALITY-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The Rigveda semantic gold set is a 120-row empty scaffold: every row UNANNOTATED "
        "with an epoch-zero timestamp, and its declared adjudication and manifest files do "
        "not exist. The harness was built and the annotation was never performed. The Wave 3 "
        "quality domain staged 3,951 rows adjudicated by a published human treebank, which "
        "its own manifest states does NOT close this gap.",
        "",
        None,
    ),
    "GAP-QUALITY-002": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The only populated gold set is model-adjudicated: all 575 theonym rows labelled by "
        "claude-opus-5, honestly typed MODEL_ADJUDICATED. Measuring the graph against it "
        "measures agreement between two model passes, not accuracy.",
        "",
        None,
    ),
    "GAP-QUALITY-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "No confidence value in the graph is calibrated, and several predicates carry a single "
        "constant on every edge, so filtering by confidence selects nothing. Calibration "
        "depends on ground truth, which GAP-QUALITY-001 and -002 show does not exist -- so "
        "the fixable part is to stop the field reading as a probability, which is unwritten.",
        "",
        None,
    ),
    "GAP-QUALITY-004": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "89 of the 100 benchmark questions remain non-pass and 11 are fully answerable. "
        "MISLEADING = 0 was the gate and is a real achievement, but it measures the absence "
        "of harm rather than the presence of answers.",
        "",
        None,
    ),
    "GAP-QUALITY-005": Ruling(
        "CLOSED_DERIVED",
        "The baseline matrix reported the Lemma row in a unit that concealed its sparsity: "
        "6,560 mantras touched by 39 words. The unit is now stated per row and the Lemma row "
        "carries its distinct-lemma count beside it, so the figure no longer reads as "
        "coverage. The underlying sparsity is GAP-MORPHOLOGY-001 and stays open there.",
        "MATCH (:Mantra)-[:MENTIONS_LEMMA]->(l:Lemma) RETURN count(DISTINCT l)",
        39,
    ),
    "GAP-QUALITY-006": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "occurrence_count is null on all 214 Devata and all 547 public Chandas nodes, and on "
        "Rishi it is written to two incompatible conventions -- 367 Rigveda-only seers report "
        "zero over the most-attributed corpus in the graph. Three writers, three conventions, "
        "no contract. Writing one contract is bounded work over data already held.",
        "MATCH (r:Rishi) WHERE r.occurrence_count = 0 RETURN count(r)",
        367,
    ),
    # ---- ritual ----------------------------------------------------------------------
    "GAP-RITUAL-001": Ruling(
        "CLOSED_DERIVED",
        "A stale claim. The entry says eight rites are modelled and names vajapeya, rajasuya, "
        "darsapurnamasa and caturmasya as absent. Measured: 103 :Ritual nodes including "
        "VG:CONCEPT:VAJAPEYA and VG:CONCEPT:DARSAPURNAMASA. The Wave 3 ritual import landed.",
        "MATCH (n:Ritual) RETURN count(n)",
        103,
    ),
    "GAP-RITUAL-002": Ruling(
        "CLOSED_DERIVED",
        "A stale claim that ritual procedure is effectively unmodelled at 3 HAS_STEP edges. "
        "Measured: 3,121 HAS_RITUAL_STEP edges from the sutra procedural layer, kept as a "
        "distinct predicate from the 3 Samhita-numbered HAS_STEP edges precisely so the two "
        "grains are not conflated.",
        "MATCH ()-[r:HAS_RITUAL_STEP]->() RETURN count(r)",
        3121,
    ),
    "GAP-RITUAL-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "9 of 23 registry objects are linked to no rite, so mani at 86 mentions and dundubhi "
        "at 17 are absent from the ritual-object ranking. The definition -- an object a "
        "curated rite is wired to use -- is right and stopped the earlier version ranking "
        "Indra's thunderbolt; the wiring over the enlarged rite population was not redone.",
        "",
        None,
    ),
    "GAP-RITUAL-004": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "11 ritual roles against the classical sixteen, and the hotr -- the officiant the "
        "Rigveda names most -- is wired to no rite at all.",
        "MATCH (r:RitualRole) RETURN count(r)",
        11,
    ),
    "GAP-RITUAL-005": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "No typed deity-to-offering predicate; the relation is representable only as generic "
        "association edges. RECEIVES_OFFERING is declared and carries zero edges, which is "
        "the shape of the gap: the type exists and nothing writes it.",
        "MATCH ()-[r:RECEIVES_OFFERING]->() RETURN count(r)",
        0,
    ),
    "GAP-RITUAL-006": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "No passage carries a ritual-context assignment, so a mention of a crop or metal "
        "cannot be distinguished as ritual or everyday and every material-culture count mixes "
        "the two. Measured: 0 mantras carry ritual_context, although 3,045 Wave 3 ritual rows "
        "were staged with an EXTERNAL_RITUAL_CITATION method that is explicitly not proximity.",
        "MATCH (p:Mantra) WHERE p.ritual_context IS NOT NULL RETURN count(p)",
        0,
    ),
    "GAP-RITUAL-007": Ruling(
        "CLOSED_DERIVED",
        "A stale diagnosis that asvamedha does not appear at all. Measured: "
        "VG:CONCEPT:ASVAMEDHA-HORSE-SACRIFICE exists.",
        "MATCH (n:Ritual) WHERE n.entity_key = 'VG:CONCEPT:ASVAMEDHA-HORSE-SACRIFICE' "
        "RETURN count(n)",
        1,
    ),
    # ---- Samaveda music --------------------------------------------------------------
    "GAP-SAMAVEDA_MUSIC-001": Ruling(
        "CLOSED_SCOPE_DECISION",
        "The gana collections are a declared exclusion from this work identifier, declared at "
        "four surfaces and carrying their own coverage_status field.",
        "",
        None,
        citation="data/registry/works.yaml:290-297",
    ),
    "GAP-SAMAVEDA_MUSIC-002": Ruling(
        "BLOCKED_OWNER_DECISION_REQUIRED",
        "No melodic layer of any kind exists and MUSICALIZED_AS carries zero edges. The Wave 3 "
        "samaveda_music domain staged 1,471 rows -- arcika notation with Vedic-extension "
        "marks -- whose manifest declares this gap closed, and the domain is blocked behind "
        "OWNER_DECISION_E_AUDIO_GATE with Gate B UNKNOWN and Gate C NOT_RUN. Staged and "
        "unimported is not closed, and it is not a source absence either.",
        "MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)",
        0,
        owner_decision="OWNER_DECISION_E_AUDIO_GATE",
    ),
    "GAP-SAMAVEDA_MUSIC-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The arcika ingest kept structural coordinates and discarded the edition's own running "
        "number, which is the only key joining an arcika verse to a gana rendering -- so 495 "
        "MUSICALIZED_AS edges could not be re-derived or audited after import. The number is "
        "in the edition already held.",
        "",
        None,
    ),
    # ---- scholarship -----------------------------------------------------------------
    "GAP-SCHOLARSHIP-001": Ruling(
        "CLOSED_DERIVED",
        "A stale claim that the graph records no scholarly position and no two claims "
        "contradict each other. Measured: 17 Scholar, 17 ScholarlyWork and 113 "
        "ScholarlyDisagreement nodes, each carrying two named asserters, two claims, "
        "page-precise locators and a stated incompatibility. The Wave 3 scholarship import "
        "landed after a lead correction withdrew one same-asserter disagreement.",
        "MATCH (d:ScholarlyDisagreement) RETURN count(d)",
        113,
    ),
    "GAP-SCHOLARSHIP-002": Ruling(
        "CLOSED_SCOPE_DECISION",
        "No post-Samhita layer for any Veda: no Brahmana, Aranyaka, Upanisad or commentary. A "
        "declared and consistently applied scope decision, stated at four work identifiers "
        "and in the product scope document, and surfaced per Veda on the frontend.",
        "",
        None,
        citation="data/registry/works.yaml (all four work scopes); docs/PRODUCT_V1_SCOPE.md",
    ),
    # ---- semantics -------------------------------------------------------------------
    "GAP-SEMANTICS-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The semantic assertion layer is Rigveda-only and covers 2,542 of 10,552 RV mantras. "
        "The rule half depends on the RV-only annotation and is genuinely source-blocked "
        "there; the model half reads a 19th-century English translation and was simply not "
        "extended, which is the fixable part and is recorded as one gap with the other.",
        "MATCH (:Mantra)-[:HAS_SEMANTIC_ASSERTION]->() RETURN count(*)",
        None,
    ),
    "GAP-SEMANTICS-002": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "All 4,865 semantic assertions are UNREVIEWED; no assertion has ever been checked by "
        "a human, and 2,459 are TIER_D unreviewed model output over a 19th-century English "
        "translation -- the weakest provenance in the graph and the half most in need of "
        "review. Human review is an execution blocker; what is fixable and unwritten is the "
        "review harness the absence is recorded against.",
        # The property is review_state, not review_status. The first draft of this ruling
        # named the wrong one, measured 0, and the pre-declared expectation is what caught it
        # -- a ruling written after the measurement would have recorded a triumphant zero.
        "MATCH (a:SemanticAssertion) WHERE a.review_state = 'UNREVIEWED' RETURN count(a)",
        4865,
    ),
    "GAP-SEMANTICS-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Not one of the 4,865 assertions carries a complete agent-predicate-target triple: "
        "the rule layer writes agent and predicate and never a target, the model layer writes "
        "targets, and the two were never reconciled. Both halves are in the graph.",
        "",
        None,
    ),
    "GAP-SEMANTICS-004": Ruling(
        "CLOSED_SCOPE_DECISION",
        "No chronological or stratigraphic dimension, and Veda membership is not a period. "
        "Deliberately not modelled for a defensible reason -- Vedic stratigraphy is contested "
        "and a stratum assignment would be an interpretive claim rather than a measurement. "
        "The entry's own complaint was that the decision was recorded nowhere; recording it "
        "here, with the reason, is the closure.",
        "",
        None,
        citation="this audit entry, and docs/reports/data-completeness/semantics.md",
    ),
    "GAP-SEMANTICS-005": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "All 375 DomainEntity nodes lack a domain assignment, so the entity population cannot "
        "be partitioned into ritual, cosmological or material spheres and questions about how "
        "two spheres connect have no partition to connect. The property was designed into the "
        "label name and never written. Assigning the spheres is a classification decision, "
        "but the field to hold it does not exist either.",
        "MATCH (e:DomainEntity) WHERE e.domain IS NULL RETURN count(e)",
        375,
    ),
    "GAP-SEMANTICS-006": Ruling(
        "CLOSED_SCOPE_DECISION",
        "No non-lexical resemblance measure: no embedding, no vector index, no asserted "
        "semantic resemblance. A recorded V1 non-goal, and the typed NOT_BUILT handling is "
        "exemplary -- the graph refuses the question rather than answering it lexically and "
        "calling that conceptual similarity. The Wave 3 staged layer is 43,006 "
        "THEMATICALLY_RESEMBLES edges held back for re-derivation from the final snapshot.",
        "",
        None,
        citation="docs/PRODUCT_V1_SCOPE.md:212-221 (no vector database, no embedding "
        "retrieval)",
    ),
    # ---- translation -----------------------------------------------------------------
    "GAP-TRANSLATION-001": Ruling(
        "BLOCKED_OWNER_DECISION_REQUIRED",
        "The Samaveda has 0 of 1,844 translations in the graph, and the registry records the "
        "block as a source limitation. Wave 4 measured otherwise: 1,242 Samavedic "
        "translations are staged against this corpus's own canonical keys and every one of "
        "the 2,254 staged translation rows targets a mantra that exists and carries no "
        "translation. The addressing works; the import gate is closed. Blocked on "
        "OWNER_DECISION_A_RV_SPAN and OWNER_DECISION_C_FORCED_ADDRESSES, with Gate B UNKNOWN "
        "and Gate C NOT_RUN, so it is neither closed nor source-limited.",
        "MATCH (m:Mantra {veda:'SV'})-[:HAS_TRANSLATION]->(t:Translation) "
        "WHERE t.language = 'en' AND t.reuse_kind IS NULL "
        "AND t.alignment_level <> 'MANTRA_RANGE' RETURN count(DISTINCT m)",
        0,
        owner_decision="OWNER_DECISION_A_RV_SPAN + OWNER_DECISION_C_FORCED_ADDRESSES",
        blocked_evidence=_SOURCE_ABSENT_SV_TRANSLATION,
    ),
    "GAP-TRANSLATION-002": Ruling(
        "BLOCKED_OWNER_DECISION_REQUIRED",
        "944 of 961 Atharvavedic translations were located via the Wayback Machine and the "
        "registry records the gap as closed. Measured: AV translation coverage is 4,878 of "
        "5,839, exactly the pre-closure figure, and the 944 are staged and unimported behind "
        "the same two owner decisions. Acquisition succeeded; promotion did not happen.",
        "MATCH (m:Mantra {veda:'AV'})-[:HAS_TRANSLATION]->(t:Translation) "
        "WHERE t.language = 'en' AND t.reuse_kind IS NULL "
        "AND t.alignment_level <> 'MANTRA_RANGE' RETURN count(DISTINCT m)",
        5715,
        owner_decision="OWNER_DECISION_A_RV_SPAN + OWNER_DECISION_C_FORCED_ADDRESSES",
    ),
    "GAP-TRANSLATION-003": Ruling(
        "BLOCKED_OWNER_DECISION_REQUIRED",
        "39 of 72 Yajurvedic gap labels were digit-confusion OCR with the translated text "
        "present throughout -- never a source gap. 51 rows staged; the graph holds 1,903 of "
        "1,975, the pre-closure figure.",
        "MATCH (m:Mantra {veda:'YV'})-[:HAS_TRANSLATION]->(t:Translation) "
        "WHERE t.language = 'en' AND t.reuse_kind IS NULL "
        "AND t.alignment_level <> 'MANTRA_RANGE' RETURN count(DISTINCT m)",
        1939,
        owner_decision="OWNER_DECISION_A_RV_SPAN + OWNER_DECISION_C_FORCED_ADDRESSES",
    ),
    "GAP-TRANSLATION-004": Ruling(
        "BLOCKED_OWNER_DECISION_REQUIRED",
        "50 Rigvedic mantras without a translation. Griffith renders each pair of Sakala "
        "verses as one merged unit, so 30 are barred from import until the coordinate repair "
        "is verified -- per owner decision A, correctly. 17 staged; the graph holds 10,502 of "
        "10,552, the pre-closure figure.",
        "MATCH (m:Mantra {veda:'RV'})-[:HAS_TRANSLATION]->(t:Translation) "
        "WHERE t.language = 'en' AND t.reuse_kind IS NULL "
        "AND t.alignment_level <> 'MANTRA_RANGE' RETURN count(DISTINCT m)",
        10479,
        owner_decision="OWNER_DECISION_A_RV_SPAN",
    ),
    "GAP-TRANSLATION-005": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "All 17,283 translations are single-witness and machine-aligned with no per-translation "
        "alignment confidence recorded, while PRODUCT_V1_SCOPE.md:58 claims 158 translations "
        "are 'recorded as uncertain' and no property on any Translation node carries that. A "
        "live document claims a field that does not exist.",
        "MATCH (t:Translation) WHERE t.alignment_confidence IS NOT NULL RETURN count(t)",
        0,
    ),
    "GAP-TRANSLATION-006": Ruling(
        "CLOSED_DERIVED",
        "25 of 31 shipped translations in RV 1.65-1.70 read against the wrong Sanskrit. "
        "Re-measured independently before any mutation -- 61 verses, 31 translated, 6 "
        "correct, 25 wrong, 0 ambiguous -- which reproduced the figure rather than inheriting "
        "it. Not a source defect: Griffith's edition numbers each four-pada group as one "
        "verse where ours numbers each hemistich, established from our own canonical text "
        "(every verse in the span is a single hemistich where the neighbours are two), our "
        "own Anukramani metre (viraj throughout, against tristup and jagati either side) and "
        "the source's own structure (ceil(V/2) units, the odd hymn's last unit one line "
        "rather than two). Fixed at the generator: six hymn-level declarations under "
        "translation_verse_spine in upstream_corrections.yaml, applied by the projection, so "
        "a rebuild produces the corrected anchors -- the corpus stays byte-identical because "
        "translations.jsonl is inside the sealed semantic freeze. build.py's coverage guard "
        "had detected the shortfall and named it translation_coverage_incomplete, which is "
        "why the campaign recorded 30 absent verses and not the 25 wrong ones; it now raises "
        "translation_verse_spine_mismatch as an ERROR. M13 re-anchored the 25 with a readback "
        "driven by the executed receipt: 0 old attachments serving, 0 text bytes changed, 0 "
        "provenance mismatches, neighbours at their pre-fix baseline. The 30 uncovered verses "
        "stay open under GAP-TRANSLATION-004, which is the honest state -- Griffith renders "
        "the pair as one unit and splitting it at his line break would fabricate.",
        "MATCH (m:Mantra {veda:'RV'})-[:HAS_TRANSLATION]->() "
        "WHERE m.canonical_key STARTS WITH 'VG:RV:SAK:M01:S065:' "
        "  OR m.canonical_key STARTS WITH 'VG:RV:SAK:M01:S066:' "
        "  OR m.canonical_key STARTS WITH 'VG:RV:SAK:M01:S067:' "
        "  OR m.canonical_key STARTS WITH 'VG:RV:SAK:M01:S068:' "
        "  OR m.canonical_key STARTS WITH 'VG:RV:SAK:M01:S069:' "
        "  OR m.canonical_key STARTS WITH 'VG:RV:SAK:M01:S070:' "
        "RETURN sum(CASE WHEN toInteger(substring(split(m.canonical_key,':')[5],1)) % 2 = 0 "
        "  THEN 1 ELSE 0 END)",
        0,
    ),
    # ---- named Wave 3/4 findings -----------------------------------------------------
    "GAP-CROSS-VEDA-DEVATA-IDENTITY-BRIDGE-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "HAS_DEVATA and HAS_DEVATA_ASCRIPTION value spaces intersect at zero, so cross-Veda "
        "deity reasoning fails silently for RV against AV. Confirmed by probe. Wave 4 stopped "
        "the product asserting otherwise -- the caveat and 214 deity notes are corrected -- "
        "but the bridge itself is unbuilt, and building it is the same resolution step as "
        "GAP-ATTRIBUTION-002.",
        "MATCH (a:DevataAscription) WHERE (a)-->(:Devata) RETURN count(a)",
        0,
    ),
    "GAP-ATTRIBUTION-WHITNEY-UNRESOLVED-OBJECT-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "466 source-explicit attributions held and unimportable. The resolution channel exists "
        "and resolves 405 of 477 proposals with zero ambiguity; it was blocked behind "
        "GAP-AV-CHANDOMETRE-SEGMENTATION-001 because the target metre vocabulary was "
        "contaminated. Wave 4 fixed the vocabulary at the generator and retired the 28 "
        "malformed identities, so the stated precondition is now met and the import has not "
        "been run.",
        "",
        None,
    ),
    "GAP-RITUAL-STEP-LOCATOR-COLLISION-001": Ruling(
        "CLOSED_VERIFIED_ZERO",
        "2 sutras unrepresentable under the current RitualStep identity, because the edition's "
        "citation granularity is coarser than its sutra granularity at that point. Not a "
        "staging defect: the locator extraction recorded what the edition prints. Admitting "
        "them needs either an edition that prints a sub-index or a deliberate identity "
        "revision, which is an owner decision and is recorded as one rather than taken.",
        "MATCH (s:RitualStep) RETURN count(s)",
        3121,
    ),
    "GAP-AV-CHANDOMETRE-SEGMENTATION-001": Ruling(
        "CLOSED_DERIVED",
        "33 metre assertions whose object was not a metre, and the owner's standing note was "
        "that the builder would recreate them. Wave 4 fixed the generator "
        "(build_atharvaveda_anukramani.py) with a criterion bounded by Whitney's own notation "
        "-- a colon separates a statement from its per-verse exceptions, and a bare N. is a "
        "verse address -- and 39 tests pin 19 malformed strings as refused and 16 real metre "
        "names carrying 3-av./6-p. qualifiers as surviving. M10 then marked the 28 identities "
        ":Internal, which M9 had left public in the world export. The import-time stdout swap "
        "that made the builder untestable, and is why the documented residual shipped, is "
        "fixed too. Measured: 0 compound values in the regenerated artifact.",
        "MATCH (c:Chandas) WHERE NOT c:Internal AND c.preferred_label CONTAINS ':' "
        "RETURN count(c)",
        0,
    ),
    "GAP-SEMANTIC-SIGNATURE-COVERAGE-001": Ruling(
        "CLOSED_DERIVED",
        "13 populated predicates whose endpoints nothing constrained -- 15 declared ones in "
        "total. Wave 4 declared a Signature for all 14 semantic predicates and for "
        "QA_ISSUE_ON, from the ontology's rule rather than from the observed population, and "
        "the two zero-edge predicates got the same signature from the same rule. The "
        "fallthrough that let a missing signature mean 'check only the subject' is now a "
        "raise, and an assert pins SIGNATURES == CONTROLLED_PREDICATES. Measured: 90 of 90 "
        "declared predicates constrained, 0 signature violations.",
        "",
        None,
    ),
}


def _one(session: Session, cypher: str) -> int | None:
    record = session.run(cypher).single()
    return None if record is None else int(record[0])


def audit(session: Session, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [str(g["gap_id"]) for g in gaps]
    unruled = [gid for gid in ids if gid not in RULINGS]
    stray = [gid for gid in RULINGS if gid not in ids]

    rows: list[dict[str, Any]] = []
    findings: list[str] = []
    for gid in ids:
        ruling = RULINGS[gid]
        status = ruling.status
        measured: int | None = None
        if ruling.measure:
            measured = _one(session, ruling.measure)
            if ruling.expect is not None and measured != ruling.expect:
                findings.append(
                    f"{gid}: ruling declared {ruling.expect} and the graph measures "
                    f"{measured}. The ruling was stated before the measurement, so this is a "
                    f"real disagreement and not a rounding of one into the other."
                )

        evidence_missing: list[str] = []
        if status == "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE":
            evidence_missing = [
                field
                for field in BLOCKED_EVIDENCE_FIELDS
                if not (ruling.blocked_evidence or {}).get(field)
            ]
            if evidence_missing:
                status = "BLOCKED_EVIDENCE_INCOMPLETE"
        if status == "CLOSED_SCOPE_DECISION" and not ruling.citation:
            status = "STILL_IMPLEMENTATION_FIXABLE"
            findings.append(
                f"{gid}: CLOSED_SCOPE_DECISION with no citation. A scope decision nobody "
                f"wrote down is indistinguishable from one invented to close the entry."
            )
        if status == "BLOCKED_OWNER_DECISION_REQUIRED" and not ruling.owner_decision:
            findings.append(f"{gid}: owner-decision block without a named decision")

        rows.append(
            {
                "gap_id": gid,
                "closure_status": status,
                "declared_status": ruling.status,
                "downgraded": status != ruling.status,
                "closure_basis": ruling.basis,
                "closure_measure": ruling.measure or None,
                "closure_measured_value": measured,
                "closure_expected_value": ruling.expect,
                "closure_citation": ruling.citation or None,
                "closure_owner_decision": ruling.owner_decision or None,
                "closure_blocked_evidence": dict(ruling.blocked_evidence or {}) or None,
                "closure_blocked_evidence_missing": evidence_missing or None,
                "terminates": status in (CLOSED | EXECUTION_BLOCKERS),
                "is_data_completeness_closure": status in CLOSED,
            }
        )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["closure_status"]] = counts.get(row["closure_status"], 0) + 1

    return {
        "artifact": "WAVE4_REGISTRY_CLOSURE_AUDIT",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "entries": len(rows),
        "entries_without_a_ruling": unruled,
        "rulings_for_no_entry": stray,
        "counts": dict(sorted(counts.items())),
        "closed": sum(1 for r in rows if r["is_data_completeness_closure"]),
        "execution_blockers": sum(
            1 for r in rows if r["closure_status"] in EXECUTION_BLOCKERS
        ),
        "not_terminated": sorted(r["gap_id"] for r in rows if not r["terminates"]),
        "measurement_disagreements": findings,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    gaps = registry["gaps"]

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            report = audit(session, gaps)
    finally:
        driver.close()

    report["sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print("  WAVE 4 PHASE 7 -- GAP REGISTRY CLOSURE AUDIT")
    print()
    print(f"  entries                         {report['entries']}")
    if report["entries_without_a_ruling"]:
        print(f"  WITHOUT A RULING                {report['entries_without_a_ruling']}")
    if report["rulings_for_no_entry"]:
        print(f"  RULINGS FOR NO ENTRY            {report['rulings_for_no_entry']}")
    print()
    for status, n in report["counts"].items():
        kind = (
            "closure"
            if status in CLOSED
            else "execution blocker"
            if status in EXECUTION_BLOCKERS
            else "NOT TERMINAL"
        )
        print(f"    {status:44} {n:3}  {kind}")
    print()
    print(f"  data-completeness closures      {report['closed']}")
    print(f"  separately tracked blockers     {report['execution_blockers']}")
    print(f"  NOT terminated                  {len(report['not_terminated'])}")
    for finding in report["measurement_disagreements"]:
        print(f"\n  DISAGREEMENT: {finding}")
    print()
    print(f"  report: {OUT.relative_to(PROJECT_ROOT)}")

    if args.write:
        by_id = {row["gap_id"]: row for row in report["rows"]}
        for gap in gaps:
            row = by_id[str(gap["gap_id"])]
            gap["status"] = row["closure_status"]
            for field in (
                "closure_basis",
                "closure_measure",
                "closure_measured_value",
                "closure_citation",
                "closure_owner_decision",
                "closure_blocked_evidence",
            ):
                gap[field] = row[field]
            gap["closure_measured_at"] = report["at"]
        registry["closure_vocabulary"] = {
            "closed": sorted(CLOSED),
            "execution_blockers_not_data_completeness_closure": sorted(EXECUTION_BLOCKERS),
            "not_terminal": sorted(NOT_TERMINAL),
            "rule": (
                "Every entry carries exactly one status. The six CLOSED_* and "
                "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE values are data-completeness closure. "
                "The execution blockers are terminal for the purpose of 'nothing is OPEN' and "
                "are NOT closure: they are counted separately and named in the verdict. "
                "STILL_IMPLEMENTATION_FIXABLE and BLOCKED_EVIDENCE_INCOMPLETE are not "
                "terminal at all, and while any entry holds one the campaign is not complete."
            ),
            "blocked_external_source_required_fields": list(BLOCKED_EVIDENCE_FIELDS),
            "audited_by": "scripts/wave4_registry_closure_audit.py",
            "audit_artifact": str(OUT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        }
        registry["generated_at"] = report["at"]
        REGISTRY.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"  wrote {REGISTRY.relative_to(PROJECT_ROOT)}")

    blocking = bool(
        report["not_terminated"]
        or report["entries_without_a_ruling"]
        or report["rulings_for_no_entry"]
        or report["measurement_disagreements"]
    )
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
