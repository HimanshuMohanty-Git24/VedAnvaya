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

from neo4j import GraphDatabase, Query, Session

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = PROJECT_ROOT / "data" / "gap_registry.json"
OUT = PROJECT_ROOT / "data" / "staging" / "wave4" / "registry_closure_audit.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: Every measure here is a single aggregate. Anything slower than this is a defect.
QUERY_TIMEOUT_SECONDS: Final[float] = 300.0

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
    #: The value ``expect`` held before the RELEASE BLOCKER CLOSURE R1 re-adjudication,
    #: where the graph moved past a pre-integration declaration. Kept rather than
    #: overwritten: a re-declaration that erases what it replaced is indistinguishable
    #: from editing the measurement to make it green, and the disagreements are the
    #: campaign's own record of the gate working. ``None`` means never revised.
    prior_expect: int | None = None
    #: What the re-measurement established. Required whenever ``prior_expect`` is set.
    reaudit: str = ''


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
    "why_no_lawful_source": (
        "No Kauthuma-aligned public-domain Samaveda translation exists. "
        "data/domain/vedagraph_domain_v2/veda_coverage_v3.json:285 records it verbatim: 'No "
        "complete translation of the Kauthuma arcika is ingested; the only one located is "
        "Ranayaniya and does not align.' Campaign rule 3 forbids mapping another recension "
        "onto the one held, so the located candidate may not be force-aligned. Measured "
        "2026-09-17: the only renderings any Samavedic verse carries are 173 "
        "REUSED_SURFACE_IDENTICAL rows of Griffith's Rigvedic English on verified-identical "
        "text, and 0 Translation nodes carry a Kauthuma-aligned source_id."
    ),
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


# --- RELEASE BLOCKER CLOSURE R1 -------------------------------------------------------
# Three further external-source blocks, each carrying all five fields the owner requires.
# Every figure in them was measured read-only against the live graph, or read out of the
# named artifact, on 2026-09-17. None is copied from another agent's report.

_SOURCE_ABSENT_SV_YV_DEDICATION = {
    "sources_searched": (
        "Kauthuma Devatadhyaya Brahmana (Samavedic deity apparatus) and the Madhyandina "
        "Sarvanukramana-sutra (Yajurvedic apparatus); GRETIL, VedaWeb, sacred-texts, "
        "archive.org. Re-checked 2026-09-17 against the two records that refuse them."
    ),
    "search_date": (
        "2026-09-14/15, re-checked 2026-09-17"
    ),
    "addressing_proof": (
        "Dedication addressing is proven to work for the two corpora an apparatus exists for: "
        "measured 2026-09-17, HAS_DEVATA reaches 10,552 of 10,552 RV mantras and the AV half "
        "now reaches 4,160 mantras through HAS_DEVATA_ASCRIPTION (4,816 edges) plus 882 "
        "HAS_DEVATA_DERIVED and 39 ASCRIBES_TO_DEVATA bridge edges. The SV and YV zeros are "
        "therefore not a coordinate failure on this side."
    ),
    "why_no_lawful_source": (
        "For the SV the apparatus is keyed to samans in the gana collections, a declared "
        "exclusion from this work identifier (data/registry/works.yaml:290-297), so no arcika-"
        "verse coordinate exists to address. For the YV "
        "data/knowledge/yajurveda_deterministic_v1/manifest.json records the Madhyandina "
        "Sarvanukramana-sutra as pratika-keyed sutra prose refused for machine resolution, "
        "with descriptor_predicates an empty list. The same block is already accepted under "
        "GAP-ATTRIBUTION-004 and GAP-ATTRIBUTION-006."
    ),
    "absence_not_inferred_from_not_looking": (
        "Measured 2026-09-17 by enumerating every relationship type between a Mantra and a "
        ":Devata or :DevataAscription, per Veda, rather than by querying the predicate "
        "expected to be absent: DESCRIBES, HAS_DEVATA, HAS_DEVATA_ASCRIPTION, "
        "HAS_DEVATA_DERIVED, INVOKES, MENTIONS_DEVATA, PRAISES. SV and YV are reached only by "
        "the naming predicates (MENTIONS_DEVATA 1,335 SV / 1,964 YV), which are not "
        "dedication, and by 0 dedication edges of any type."
    ),
}

_SOURCE_ABSENT_RISHI_LINEAGE = {
    "sources_searched": (
        "WSC2023, the only pinned Rigvedic Anukramani source (commit "
        "05b5987d6d8d6ec7228926eb68d6a21117c9b1f2); the Vedic Heritage Portal; published "
        "structured scholarly genealogy datasets; encyclopaedic and community sources. Each is "
        "named and refused with its own reason in "
        "docs/architecture/RIGVEDA_RISHI_STRUCTURE_FINDINGS.md."
    ),
    "search_date": (
        "Recorded in docs/architecture/RIGVEDA_RISHI_STRUCTURE_FINDINGS.md, whose finding is "
        "NO SUFFICIENT DETERMINISTIC SOURCE FOUND; re-read and re-measured 2026-09-17."
    ),
    "addressing_proof": (
        "Not an addressing failure. Measured 2026-09-17: 302 of 729 seers DO carry "
        "BELONGS_TO_FAMILY over 87 :RishiFamily nodes, and "
        "data/domain/vedagraph_domain_v2/rishi_families_v1.json is built (538 KB), so the "
        "entry's second closure clause -- that tests/domain/test_rishi_families.py runs rather "
        "than skipping -- is now met: the module collects and passes, with one test skipped "
        "only for want of VEDAGRAPH_LIVE_NEO4J."
    ),
    "why_no_lawful_source": (
        "The pinned Anukramani stores patronymic-plus-name phrases and no lineage field. The "
        "findings document records that a suffix rule 'applied blindly would manufacture "
        "relationships', that 'an inference that is right most of the time is still an "
        "inference, and this repository does not record inferences as source-explicit edges', "
        "that the rights policy forbids bulk use of the Vedic Heritage Portal, that no rights-"
        "compatible structured dataset with per-claim provenance was found, and that an LLM "
        "genealogy is explicitly excluded."
    ),
    "absence_not_inferred_from_not_looking": (
        "Measured, not assumed: 427 of 729 with no BELONGS_TO_FAMILY on 2026-09-17, against "
        "302 resolved and 87 families that prove the layer works where an explicit source "
        "exists. The alternatives were enumerated and each refused by name with its reason, "
        "rather than one query being run and read as absence."
    ),
}

_SOURCE_ABSENT_AV_KANDA20_RESIDUAL = {
    "sources_searched": (
        "Whitney/Lanman via VEDAWEB (the ingested AV translation, which omits kanda 20); "
        "Griffith's Hymns of the Atharvaveda via the Internet Archive Wayback Machine, sacred-"
        "texts.com being 403 behind a Cloudflare bot challenge; and, for each residual verse, "
        "every Rigvedic text version in the store as a reuse route."
    ),
    "search_date": (
        "2026-09-16, per-key; re-measured against the graph 2026-09-17"
    ),
    "addressing_proof": (
        "Addressing demonstrably works: 944 of 961 kanda-20 renderings were located and "
        "b4b1b0b imported them. Measured 2026-09-17, AV translation coverage is 5,788 mantras "
        "carrying HAS_TRANSLATION plus 34 covered by a DECLARED_RANGE rendering attached to "
        "their anchor, so the 51 the closure predicate counts decomposes exactly as 34 range-"
        "covered plus 17 uncovered."
    ),
    "why_no_lawful_source": (
        "Griffith's kanda-20 print does not carry these 17 verses. The cross-corpus reuse "
        "route was then tested per verse against every one of the 21,104 Rigvedic text "
        "versions in the store rather than only the asserted parallel, and refused on "
        "measurement; for AVS 20.57.13 two of six pairings reach exactly 1.0 and Gate B still "
        "refuses it. Every per-key verdict is in "
        "data/staging/final_closure_sprint/agent7/residual_disposition.json."
    ),
    "absence_not_inferred_from_not_looking": (
        "All 17 keys are named individually with their own addressing verdict and their own "
        "refused reuse measurement. The population was reconciled arithmetically against the "
        "graph (5,788 + 34 + 17 = 5,839) rather than inferred from a single count returning a "
        "number that looked small."
    ),
}


#: One ruling per entry, declared ahead of measurement. The order is the registry's.
RULINGS: Final[dict[str, Ruling]] = {
    # ---- attribution -----------------------------------------------------------------
    "GAP-ATTRIBUTION-001": Ruling(
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE",
        "The AV half the ruling called unfinished implementation is now built, and what "
        "remains is the apparatus block this registry already accepts twice. Measured "
        "2026-09-17 by enumerating every Mantra-to-Devata relationship type per Veda: a "
        "dedication predicate reaches RV (HAS_DEVATA, 10,552 mantras) and AV "
        "(HAS_DEVATA_ASCRIPTION 4,816 edges over 4,160 mantras, plus 882 HAS_DEVATA_DERIVED "
        "and 39 ASCRIBES_TO_DEVATA), and reaches SV and YV with zero edges of any dedication "
        "type -- they carry only the naming predicate MENTIONS_DEVATA, 1,335 and 1,964, which "
        "is a different axis. The SV block is the gana join key and the YV block is "
        "pratika-keyed sutra prose refused for machine resolution; both are recorded, and "
        "GAP-ATTRIBUTION-004 and -006 are already BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE on the "
        "same two apparatuses. The residual AV resolution work is GAP-ATTRIBUTION-002 and "
        "stays open there rather than being counted twice here.",
        "MATCH (a:DevataAscription) WHERE (a)-->(:Devata) RETURN count(a)",
        39,
        blocked_evidence=_SOURCE_ABSENT_SV_YV_DEDICATION,
        prior_expect=0,
        reaudit=(
            "0 resolved ascriptions became 39, so the AV half is no longer unbuilt and the "
            "entry's remaining reach is the SV and YV apparatus absence alone."
        ),
    ),
    "GAP-ATTRIBUTION-002": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Two of three clauses now pass; the entry stays open on clause 1, and on a defect R3 "
        "found while closing the other two. CLAUSE 3 CLOSED: all 324 :DevataAscription nodes "
        "carry ascription_resolution_status from the closed seven-value vocabulary in "
        "vedagraph.domain.ascription_bridge, and all 285 unresolved carry "
        "ascription_unresolved_reason -- 0 unresolved without a reason, against 285 before, so "
        "a reader can now tell a refused descriptor from one nobody processed. The statuses "
        "were computed by the repository's own resolver, not adjudicated here: 210 "
        "UNRESOLVED_STEM_MATCHES_NO_CANONICAL_DEVATA, 67 UNRESOLVED_COMPOUND_TWO_ASCRIPTIONS, "
        "4 UNRESOLVED_SUBJECT_DESCRIPTOR_NOT_A_DEITY, 3 UNRESOLVED_NAMES_A_PLURALITY, 1 "
        "UNRESOLVED_SOURCE_DEFERS_TO_THE_MANTRA. CLAUSE 2 CLOSED: the deity insight read "
        "ascribed_scope off HAS_DEVATA alone, which is Rigveda-only, and so published AV in "
        "the ascription dimension's vedas_not_covered while 851 Atharvavedic passages carried "
        "a resolved dedication -- a false absence on the field whose whole job is to tell a "
        "missing layer from a real zero. Both dedication routes now travel in ONE pattern so "
        "the figure and its scope label cannot disagree, the layer scope is MEASURED rather "
        "than read from profiles.ATTRIBUTION_VEDAS (which is ('RV',) and correct about "
        "HAS_DEVATA -- the last reader of the constant profiles.py's own docstring says "
        "nothing should read), and a new ascription_routes block states each route's method: "
        "SOURCE_STATED_ANUKRAMANI_DEDICATION and TADDHITA_SASYA_DEVATA_DERIVATION. The node "
        "twin was corrected with it: attribution_scope was the literal ['RV'] on all 214 "
        ":Devata and is now measured per node, 179 ['RV'] and 35 ['RV','AV'], with 0 nodes "
        "claiming a corpus they have no edge in and 0 omitting one they do. CLAUSE 2 WAS FIRST "
        "CLOSED INCOMPLETELY, and the hostile pass caught it: the insight route was widened "
        "and /api/v1/devatas/{id} was left on HAS_DEVATA alone, so the same product answered "
        "the same question two ways -- Indra 2,869 scope ['RV'] on one surface and 2,945 scope "
        "['RV','AV'] on the other -- while entity_service still shipped two caveats reading "
        "'ATTRIBUTION ... IS RIGVEDIC' and 'basis=ascription with veda=AV is empty by "
        "construction', the second of which the same graph falsifies for 35 deities. That is "
        "the type-level attribution failure this project has recorded once already, "
        "reproduced by the fix for it. Both deity surfaces, the ascription passages route and "
        "its count now read one pattern over both predicates and agree exactly on every "
        "sampled deity; the AV caveat states which predicate serves it; and the stored literal "
        "in taxonomy.py that would have flattened the 35 on the next rebuild is gone, the "
        "value now derived in loader.apply_overlay per GAP-ATTRIBUTION-009's own "
        "implementation_dependency, with the per-node distribution pinned by a live test. "
        "CLAUSE 1 OPEN, and "
        "this is the R3 finding: 'greater than 0 for every resolvable descriptor' is unmet "
        "because the resolver UNDER-MATCHES the source's own spelling. "
        "DEITY_ADJECTIVE_SUFFIXES lists the deity-adjective suffix in short-a forms "
        "('daivatam', 'devatyam'), Whitney prints the vrddhi form '-daivatam' with a long a, "
        "and suffix stripping runs BEFORE any length folding -- so no candidate is generated "
        "at all and the LENGTH_INSENSITIVE tier, which is applied to the candidate stem, never "
        "gets a chance. Measured 2026-09-18: 41 of the 210 no-canonical-surface descriptors "
        "would gain a suffix candidate under a length-insensitive suffix match, and among them "
        "are agnidaivatam and indradaivatam, whose stems are registered deities. Those are "
        "resolvable descriptors sitting in the unresolved bucket, so the clause fails. NOT "
        "fixed in R3 on purpose: shortening the suffix match widens the matcher, and this "
        "registry's own ascription entry records that over-normalising and under-normalising "
        "both look like a clean run -- the change needs the collision list re-enumerated per "
        "candidate before it lands, not a same-session edit. The 41 are fully diagnosed so the "
        "next pass starts from the measurement rather than the symptom.",
        "MATCH (a:DevataAscription) WHERE (a)-->(:Devata) RETURN count(a)",
        39,
        prior_expect=39,
        reaudit=(
            "39 resolved is unchanged, and that is the point: R3 closed the two clauses that "
            "were about DISCLOSURE (typing the 285, and making the Atharvavedic dedication "
            "visible with its method) and found that the clause about RESOLUTION fails for a "
            "reason nobody had measured -- a suffix list written in short-a against a source "
            "that prints the vrddhi form. The count did not move because the resolver did not "
            "change; the entry is better understood, not further along."
        ),
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
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE",
        "The ruling asserted 'the patronymic evidence is in the registries already held; "
        "nothing external is needed', and the repository's own findings document contradicts "
        "it. docs/architecture/RIGVEDA_RISHI_STRUCTURE_FINDINGS.md opens with 'Finding: NO "
        "SUFFICIENT DETERMINISTIC SOURCE FOUND' and records that a suffix rule 'applied "
        "blindly would manufacture relationships', that the same derived name points to more "
        "than one ancestor across the tradition with the Anukramani not disambiguating, and "
        "that 'an inference that is right most of the time is still an inference, and this "
        "repository does not record inferences as source-explicit edges'. Deriving families "
        "from the held labels is exactly the inference that document declines. Measured "
        "2026-09-17: 427 of 729 seers carry no BELONGS_TO_FAMILY, unchanged, so the first "
        "clause of the test does not pass; the second clause now does -- "
        "rishi_families_v1.json is built and tests/domain/test_rishi_families.py runs rather "
        "than skipping, with one test skipped only for want of VEDAGRAPH_LIVE_NEO4J.",
        "MATCH (r:Rishi) WHERE NOT (r)-[:BELONGS_TO_FAMILY]->() RETURN count(r)",
        427,
        blocked_evidence=_SOURCE_ABSENT_RISHI_LINEAGE,
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
        citation="PRODUCT_V1_SCOPE.md:212-221 (no audio redistribution)",
    ),
    "GAP-AUDIO-006": Ruling(
        "CLOSED_SCOPE_DECISION",
        "No sub-verse timing. Deriving it from proxied streams needs forced alignment, and "
        "inventing timings was explicitly refused. The expected population is not knowable "
        "because it is not a population -- it is a capability that was declined.",
        "",
        None,
        citation="PRODUCT_V1_SCOPE.md:212-221",
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
        "Unmoved, and unmoved on the clause that needs no curation question answered. Measured "
        "2026-09-17: of 214 :Devata nodes, 38 carry structure PAIR and 33 carry structure "
        "GROUP. Only 14 PAIR nodes are is_composite with component_count 2; the other 24 PAIRs "
        "and all 33 GROUPs carry component_count 0 and no decomposition of any kind, which is "
        "exactly the 57 the entry recorded. Neither arm of the test passes: the 24 remaining "
        "pairs are mechanical decomposition over material held, and the 33 groups carry no "
        "typed reason why their membership is not enumerable -- no property on :Devata holds "
        "one. The entry's own measured_cause already withdrew the blocker claim (59 of 71 "
        "composite labels were placed in a community undecomposed), so this constrains "
        "interpretation rather than gating computation, and 'worth doing for interpretation' "
        "is not done.",
        "MATCH (d:Devata) WHERE d.structure IN ['PAIR','GROUP'] AND "
        "coalesce(d.component_count,0)=0 RETURN count(d)",
        57,
    ),
    "GAP-COMMUNITIES-003": Ruling(
        "CLOSED_DERIVED",
        "A stale scorecard claim that CO_OCCURS_WITH is empty. Measured: 306 deity-pair edges.",
        "MATCH ()-[r:CO_OCCURS_WITH]->() RETURN count(r)",
        306,
    ),
    # ---- cross-Veda ------------------------------------------------------------------
    "GAP-CROSS_VEDA-001": Ruling(
        "CLOSED_DERIVED",
        "Both clauses pass and the refusal the entry could not express is now typed. Measured "
        "2026-09-17: REUSES_TEXT_FROM spans two directed corpus pairs, SV->RV 1,684 and AV->RV "
        "311 scoped to kanda 20. Direction is not a pipeline constant: over those 1,995 edges "
        "there are 703 distinct cross_veda_direction_evidence_digest values, 260 distinct "
        "cross_veda_direction_asymmetry values and 23 distinct subject-unit shares, and each "
        "edge carries its own direction_basis, _method, _scope and _status. The other four "
        "pairs carry a typed refusal rather than an empty cell: AV-SV "
        "REFUSED_MEDIATED_BY_THIRD_CORPUS on 467 edges, and AV-YV, RV-YV and SV-YV "
        "REFUSED_UNIT_GRANULARITY_INCOMPARABLE on 210, 662 and 239. All six pairs are "
        "accounted for, and none of the four is left looking unfinished when it is in fact "
        "refused.",
        "MATCH (a)-[:REUSES_TEXT_FROM]->(b) RETURN count(DISTINCT a.veda + '-' + b.veda)",
        2,
        prior_expect=1,
        reaudit=(
            "One directed pair became two, and the four undirected pairs gained the typed "
            "refusal the ruling said was the honest fix and had not been done."
        ),
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
        "CLOSED_DERIVED",
        "Measured 2026-09-17: 4,079 HAS_PARALLEL_PADA edges over 1,434 :PadaParallelGroup "
        "nodes, every edge carrying parallel_granularity 'PADA' where verse-level "
        "EXACT_PARALLEL_OF carries no such value, so the granularities are typed distinctly "
        "and cannot be read as one layer. The RV-only reach is typed in the data rather than "
        "left to prose: all 1,434 groups carry veda_scope and veda_scope_reason, and the edges "
        "touch 2,695 Rigvedic mantras and no mantra of any other corpus -- which is the "
        "entry's own stated requirement that a cross-corpus class covering one corpus must be "
        "typed as such.",
        "MATCH ()-[r:HAS_PARALLEL_PADA]->() WHERE r.parallel_granularity IS NULL RETURN "
        "count(r)",
        0,
    ),
    # ---- entity coverage -------------------------------------------------------------
    "GAP-ENTITY_COVERAGE-001": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Unmoved on all three clauses, measured 2026-09-17. The epithet layer is 13 :Epithet "
        "nodes carrying 13 HAS_EPITHET edges and nothing else: 0 edges of any type between an "
        ":Epithet and a :Passage, 4 distinct deities reached against a 214-node registry, and "
        "no recall property on any epithet node -- the only keys are epithet_key, label_iast, "
        "label_en, display_label, display_type and domain_model_version. So no question about "
        "where an epithet occurs can be answered, which is what the entry says. Genuinely "
        "internal: the Sanskrit is held for all four corpora and the projection was never run. "
        "The alias-recall discipline applies -- epithets are heavily inflected -- so "
        "per-epithet recall must be measured rather than assumed, which is the entry's third "
        "clause.",
        "MATCH (e:Epithet)-[r]-(:Passage) RETURN count(r)",
        0,
    ),
    "GAP-ENTITY_COVERAGE-002": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Unmoved, and the entry's own closure query is the one that says so. Measured "
        "2026-09-17: DerivedMetric rows whose subject_key starts VG:DEVATA: reach 25 distinct "
        "subjects over 75 metrics, against an eligible deity population of 152 and a registry "
        "of 214, so the materialisation covers 16 per cent of the eligible set. 184 :Devata "
        "nodes have a null profile_attributed_total. The second clause fails by name: "
        "VG:DEVATA:SARASVATI returns null for profile_attributed_total and null for "
        "profile_mentions_by_veda. The product handles the null correctly, reporting "
        "INSUFFICIENT_EVIDENCE rather than drawing a zero bar, which is right handling of an "
        "unfinished pass and is not closure. Internal work over mention edges already in the "
        "graph, with the denominator care the entry names: the 214 include 22 HUMAN_PATRON and "
        "7 DANASTUTI_GIFT_PRAISE, and GAP-ENTITY_COVERAGE-008's eligibility predicate now "
        "supplies the 152 to materialise over.",
        "MATCH (m:DerivedMetric) WHERE m.subject_key STARTS WITH 'VG:DEVATA:' RETURN "
        "count(DISTINCT m.subject_key)",
        25,
    ),
    "GAP-ENTITY_COVERAGE-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Unmoved on every clause. Measured 2026-09-17: db.labels() holds no label whose name "
        "contains 'remed', 'bhesaj' or 'heal', and the entry's own query for :Remedy or "
        ":Bhesaja returns 0 nodes, so no remedy entity class exists and there are no "
        "registered aliases to measure. No stated-remedy relation exists; TREATS stands at 160 "
        "edges and the entry already records it as TIER_D and not a substitute. The concerns "
        "endpoint still carries the caveat verbatim at "
        "src/vedagraph/api/services/insight_service.py:2222-2224 -- 'The registry has no "
        "healing entity -- bhesaja was never curated' -- which is honest disclosure and is not "
        "closure. Genuinely internal: bhesaja and the related remedy vocabulary are attested "
        "in text already held and lexically tractable.",
        "MATCH (n) WHERE n:Remedy OR n:Bhesaja RETURN count(n)",
        0,
    ),
    "GAP-ENTITY_COVERAGE-004": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Unmoved, and deliberately NOT recorded as a source block. Measured 2026-09-17: 0 of "
        "384 :DomainEntity nodes carry an expected_source property -- the key does not exist "
        "in the database -- so the query the entry describes, the one that would have found "
        "trapu without a human reading the text, still cannot be written. The entry's "
        "source_dependency names 'a published lexicon or index of Vedic realia', and this "
        "agent did not search for one; claiming BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE on a "
        "search nobody ran would be inferring absence from not looking, which is the one thing "
        "the blocker evidence must exclude. The internal half is real and bounded on its own: "
        "the expected_source field and a coverage report that measures registry membership "
        "against a declared expectation rather than measuring mention recall against the "
        "registry.",
        "MATCH (n:DomainEntity) WHERE n.expected_source IS NULL RETURN count(n)",
        384,
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
        "The known-false cell is verified false for the right reason, and the entry's first "
        "clause is untouched. Clause 1: 0 entities carry a measured recall figure with a "
        "sample size -- no recall property exists on :Metal, :DomainEntity or any entity label "
        "-- so the size of the shortfall across ABOUT_CONCEPT and MENTIONS_ENTITY is still "
        "unknown, which is bounded internal work. Clause 2 is NO_LEXICAL_MATCH and must stay "
        "so. The source attestation EXISTS and was read verbatim from the graph on 2026-09-17: "
        "VG:YV:VSM:A18:V013 carries the metals list, and its accented Devanagari reads "
        "'...hiranyam ca me 'yas ca me syamam ca me loham ca me sisam ca me trapu ca me...', "
        "where ayas appears sandhi-elided after 'me' as avagraha plus yas. The "
        "search-normalised fold drops the avagraha, leaving the bare token 'yasca', which is "
        "indistinguishable from the relative pronoun and from the -ayas ca plural stems "
        "standing in the same line (girayasca, parvatasca, vanaspatayasca). Registering an "
        "alias for it would manufacture false positives demonstrably inside the witness verse "
        "itself, and RIGVEDA_LEXICAL_MENTION_POLICY.md forbids both substring and surface-form "
        "matching for exactly that reason; the annotation-driven route is closed for the YV "
        "because GAP-MORPHOLOGY-002 records no published non-RV morphological annotation. This "
        "is NOT 0 source occurrences and no alias may be invented: the correct product "
        "representation is the NO_LEXICAL_MATCH cell naming its own counter-witness, which the "
        "metals surface already carries. The neighbouring metals in the same list ARE matched "
        "-- trapu, sisa, syama and loha each reach this verse -- which is what makes the ayas "
        "miss a matcher miss rather than an absence.",
        "MATCH (m:Mantra {veda:'YV'})-[:MENTIONS_ENTITY]->(e) WHERE "
        "e.entity_key='VG:CONCEPT:AYAS-METAL' RETURN count(DISTINCT m)",
        0,
    ),
    "GAP-ENTITY_COVERAGE-007": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Unmoved on both clauses. Measured 2026-09-17: only 2 :DomainEntity nodes carry a "
        "multi-word Sanskrit label at all, so phrase matching has not been built and "
        "multi-word realia remain unreachable. And no personification status of any kind "
        "exists -- across the 13 :NaturalPhenomenon nodes, 0 carry a personification_status "
        "and 0 carry a personified_as, and neither key exists in the database -- so an "
        "unresolved entity cannot be distinguished as refused or as unattempted. That is the "
        "specific ambiguity this project forbids elsewhere, and the field to hold the answer "
        "does not exist. Genuinely internal: source_dependency is NONE.",
        "MATCH (n:NaturalPhenomenon) WHERE n.personification_status IS NULL RETURN count(n)",
        13,
    ),
    "GAP-ENTITY_COVERAGE-008": Ruling(
        "CLOSED_DERIVED",
        "Closed on PRODUCT CONSUMER CONSISTENCY, which replaces a measure that asked two "
        "intentionally different predicates to agree. "
        "OWNER_DECISION_ENTITY_008_DEITY_MEMBERSHIP, recorded at "
        "docs/reports/data-completeness/OWNER_DECISIONS.md section 35, rules that canonical "
        "product Deity membership and source addressability-as-deity are NOT the same "
        "semantic predicate, and that d.is_deity is the authoritative PRODUCT predicate. "
        "WHY THE OLD MEASURE WAS WRONG, proven before it was replaced. It read `(structure IN "
        "['HUMAN','PATRON_PRAISE','UNSPECIFIED']) <> (is_deity = false)` and returned 29 BY "
        "CONSTRUCTION: measured 2026-09-18 the 29 decompose exactly as 28 ABSTRACT labels "
        "ruled NOT_DEITY, which the structure predicate admits because ABSTRACT is not in its "
        "exclusion set, plus 1 UNSPECIFIED label ruled DEITY -- VG:DEVATA:SUNAH, the dog -- "
        "which the structure predicate excludes. Driving it to 0 requires either admitting 28 "
        "abstractions each carrying its own recorded refusal reason, or expelling the dog on "
        "the recorded ground that excluding it for a structure of UNSPECIFIED rather than "
        "INDIVIDUAL would be 'excluding on a morphological accident'. Both are overturning "
        "recorded curation to satisfy a metric, which the owner decision refuses. AND THE "
        "COINCIDENCE THAT HID IT: this entry's own closure TEST says 'counts over it exclude "
        "the 29 non-deities', and that 29 is a DIFFERENT quantity -- 22 HUMAN plus 7 "
        "PATRON_PRAISE, the figure deity_eligibility.check_rows gates as `excludes_the_29`. "
        "Two unrelated quantities that both equal 29, one in the test and one in the measure, "
        "is why a measure comparing the wrong two things read as though it were checking the "
        "test. That is this project's own recorded trap: a grade can be wrong while every "
        "figure is right. WHAT IS MEASURED INSTEAD, all five clauses of the owner decision: "
        "(1) every product surface derives membership from "
        "deity_eligibility.ELIGIBLE_DEITY_PREDICATE -- 0 modules outside the five recorded "
        "exemptions in _STRUCTURE_PREDICATE_ALLOWED_IN reference a structure-based deity "
        "predicate, each exemption naming why it is structural rather than membership; "
        "(2) no consumer substitutes the source predicate -- pinned by "
        "test_no_consumer_outside_the_contract_substitutes_the_source_predicate; "
        "(3) the divergence is documented -- OWNER_DECISIONS section 35 plus this basis, and "
        "all 29 divergent nodes carry both a recorded ruling and a recorded reason, 0 "
        "unexplained; (4) a regression test pins the intentional distinction -- "
        "test_the_intentional_divergence_is_exactly_the_recorded_curation asserts the exact "
        "28+1 decomposition and says in its own failure message that agreement would mean a "
        "curation was overturned; (5) no stale consumer exposes the former population -- 0 "
        "reader-facing surfaces publish 184 or 192 as a deity count, swept over "
        "frontend/src/**/*.ts(x) and frontend/public/**/*.json. Measured live by "
        "deity_eligibility.check_product_consumers: 214 :Devata, 157 authoritative, 0 "
        "unruled, 29 documented divergence, 0 unexplained, passes=true. The 29 is REPORTED "
        "rather than driven to 0, and it is the real measured number.",
        "MATCH (d:Devata) WHERE d.is_deity IS NULL RETURN count(d)",
        0,
        prior_expect=29,
        reaudit=(
            "The R1 gate asked 'deity_eligibility_ruling IS NULL -> 0', which passes on a "
            "field nothing reads. R2 replaced it with a predicate-equality gate, which cannot "
            "reach 0 without overturning curation. R3 replaces that with product-consumer "
            "consistency per the owner decision: the authoritative predicate must be the only "
            "one any product surface reads, and an unruled node -- which fails closed and so "
            "silently shrinks the pantheon -- is the thing that must be 0. The 29-node "
            "divergence is retained as a documented invariant and pinned by a regression test "
            "so a later pass cannot flatten one predicate into the other."
        ),
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
        "CLOSED_DERIVED",
        "Closed in RELEASE BLOCKER CLOSURE R2. Clause one already passed and clause two now "
        "does. Re-measured 2026-09-18: all 4,825 :Formula carry formula_nesting_type, 0 "
        "untyped. The open clause was the ranking disclosure, and both rankings the R1 basis "
        "names now carry it: formula_service._formula_caveats and the deity top_formulas "
        "ranking in entity_service each append "
        "vedagraph.domain.layer_figures.formula_nesting_policy(). That sentence was already "
        "this project's single derived statement of the policy -- built from the live "
        "FORMULA_NESTING population rather than typed, so it cannot quote a stale share -- "
        "and it had been applied to formula-diffusion only. Nothing was re-worded and no "
        "second spelling was introduced, which is the failure mode the R1 basis named: "
        "applying different rules in different queries is how one attribution axis once "
        "produced three disagreeing answers. PRIOR RULING, superseded: "
        "STILL_IMPLEMENTATION_FIXABLE -- \"Clause one passes and clause two does not, and "
        "clause two is the one that protects "
        "the reader. Measured 2026-09-17: all 4,825 :Formula nodes carry formula_nesting_type "
        "over a four-valued vocabulary -- INDEPENDENT 2,788, CONTAINS_ANOTHER 934, "
        "NESTED_IN_ANOTHER 918, NESTED_AND_CONTAINING 185 -- so every formula standing in a "
        "strict-substring relation is now explicitly typed and the nesting is no longer "
        "invisible. But no surface states which nesting policy its ranking applies: neither "
        "src/vedagraph/api/services/formula_service.py nor the top_formulas ranking in "
        "entity_service.py:1171-1176 mentions nesting at all, and both order by passage count, "
        "so a frequency ranking still leaves all three readings available to the reader. "
        "Applying different rules in different queries is how this project previously produced "
        "three disagreeing answers for one attribution axis. Internal API work.\"",
        "MATCH (f:Formula) WHERE f.formula_nesting_type IS NULL RETURN count(f)",
        0,
    ),
    # ---- morphology ------------------------------------------------------------------
    "GAP-MORPHOLOGY-001": Ruling(
        "CLOSED_DERIVED",
        "The inert registry is now an index. Measured 2026-09-17: 0 of 10,031 :Lemma nodes are "
        "reached by no edge, against the 9,992 the entry recorded, carried by 154,261 "
        "MENTIONS_LEMMA edges reaching all 10,031 distinct lemmas -- so the entry's own test, "
        "'falls far below 9,992', passes at zero. The second clause is satisfied because no "
        "product surface reports lemma coverage at all: all 10,031 :Lemma nodes are :Internal "
        "and excluded from product traversal by graph_service.py, which admits them only under "
        "an explicit include_internal parameter. The '39 deity lemmas' figure that remains in "
        "graph_service.py:214 and :1244 is stated as the history of why the layer was demoted, "
        "which it accurately is, and not as a current coverage figure.",
        "MATCH (:Mantra)-[:MENTIONS_LEMMA]->(l:Lemma) RETURN count(DISTINCT l)",
        10031,
        prior_expect=39,
        reaudit=(
            "39 distinct lemmas reached became 10,031, and lemmas reached by nothing fell from "
            "9,992 to 0. Verified by the entry's own closure query, not by the projection's "
            "manifest."
        ),
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
        "CLOSED_DERIVED",
        "Both clauses pass, and the second is the one the entry made checkable. Verified "
        "2026-09-17 by independent readback of "
        "data/staging/final_closure_sprint/agent3/lexical_nonresolution_typed.jsonl: 711 rows, "
        "0 untyped, over exactly three typed linguistic reasons -- "
        "LEXEME_COVERS_DEITY_AND_APPELLATIVE 625, DEVATA_OR_RISHI_UNDECIDABLE 74, "
        "REGISTRY_HOLDS_TWO_ENTITIES_FOR_ONE_LEMMA 12 -- over 10 lemmas, with 79 rows flagged "
        "anukramani_corroborated and each carrying edge_withheld_because. And "
        "docs/architecture/RIGVEDA_LEXICAL_MENTION_POLICY.md:122-129 no longer lists the "
        "deferral: it states 'the feature-conditioned alias deferral is closed and this "
        "paragraph used to be wrong about it', names the five allowed_* fields that implement "
        "the mechanism, and records that none of the ten residual lemmas is separable by any "
        "annotated feature -- so the obstruction is the lexicon, not the missing mechanism the "
        "entry blamed.",
        "",
        None,
    ),
    "GAP-MORPHOLOGY-005": Ruling(
        "CLOSED_SCOPE_DECISION",
        "No mantra is available in both scripts. The refusal to ship a generated "
        "transliteration is a recorded decision with a measured basis: accent placement in "
        "generated Devanagari was 0 of 21 acceptable at band scale, and shipping it would put "
        "wrong tone marks on scripture. Owner decision 5 carries the general form of the same "
        "ruling for the Samaveda -- the annotation source is absent, the analysis is not, and "
        "lack of scholarly annotation is not inability to build an analytical layer. Citation "
        "corrected in R1: the previous one named docs/reports/data-completeness/morphology.md, "
        "which is not on disk. The measure attached here counts SEARCH_DERIVATIVE rows, which "
        "moved from 5,839 over one work to 20,210 over four when GAP-MORPHOLOGY-006's "
        "derivation ran; that is context for this entry rather than its proof, so the "
        "expectation is re-declared to the measured value and the dual-script refusal is "
        "untouched by it.",
        "MATCH (t:TextVersion) WHERE t.text_role = 'SEARCH_DERIVATIVE' RETURN count(t)",
        20210,
        citation=(
            "docs/reports/data-completeness/OWNER_DECISIONS.md:121-137 (decision 5, Samaveda "
            "morphology); docs/av_accent_binding_final_production_gate_report.md"
        ),
        prior_expect=5839,
        reaudit=(
            "Context figure only. The search-derivative layer reached the other three corpora; "
            "the dual-script refusal this entry records is untouched by that."
        ),
    ),
    "GAP-MORPHOLOGY-006": Ruling(
        "CLOSED_DERIVED",
        "All three clauses pass, measured 2026-09-17. (1) Every work now carries a "
        "search-normalised text version: SEARCH_DERIVATIVE stands at 20,210 and decomposes as "
        "RV 10,552, AV 5,839, YV 1,975, SV 1,844, against 5,839 over one work before. (2) The "
        "139 Yajurvedic mantras that had no unaccented form have one: 139 TextVersion rows "
        "with text_role NORMALIZED, reaching exactly the 139 mantras that carry no "
        "PARALLEL_TEXT, and 1,836 + 139 = 1,975 reconciles. (3) A single lexical query over "
        "that one instrument reaches all four corpora rather than one: 'agni' over "
        "SEARCH_DERIVATIVE returns RV 587, AV 275, YV 170 and SV 108 mantras, where the same "
        "query over the accented witnesses reaches AV and RV only. Residual, named rather than "
        "absorbed: the Samaveda still has no accented witness at all -- 1,844 Latin and 1,844 "
        "Devanagari versions, all unaccented -- which the entry's test does not ask for and "
        "GAP-MORPHOLOGY-005 holds as a recorded scope decision.",
        "MATCH (t:TextVersion) WHERE t.text_role = 'SEARCH_DERIVATIVE' RETURN count(t)",
        20210,
        prior_expect=5839,
        reaudit=(
            "5,839 SEARCH_DERIVATIVE rows over one work became 20,210 over four, and the 139 "
            "YV mantras gained a NORMALIZED unaccented form. Reconciled per corpus."
        ),
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
        "CLOSED_DERIVED",
        "Both clauses are now structurally unrepresentable rather than merely avoided. "
        "src/vedagraph/api/models/common.py:153-193 defines _reject_contradictory_coverage, "
        "which RAISES on a Veda appearing in both vedas_in_scope and vedas_not_covered, and "
        "raises again on the subtler form the entry actually reported -- a Veda carrying a "
        "non-zero measured figure while listed as not covered, which is what would make a "
        "client discard the figures the endpoint measured. It is wired at two call sites "
        "(common.py:229 and :276), not merely defined. A measured zero beside not_covered is "
        "deliberately still legal, which is how an absent layer stays distinguishable from a "
        "silent corpus. The second clause is served by CoverageDimension, which reports reach "
        "per dimension so the naming axis and the ascription axis cannot be merged into one "
        "block.",
        "",
        None,
    ),
    "GAP-PRODUCT_SURFACE-002": Ruling(
        "CLOSED_DERIVED",
        "src/vedagraph/api/services/capability_probes.py supplies the fourteen missing "
        "dimensions plus Q49 as 15 PROBED_LIMIT_SPECS, each with a probe that measures on "
        "every request rather than copying the frozen grade -- which matters, because three of "
        "the dimensions have moved since V3.3 was frozen and pasting the grades forward would "
        "have published three limitations that no longer hold. BENCHMARK_NOT_ANSWERABLE "
        "declares the 21-question population in code and "
        "tests/api/test_capability_catalogue.py asserts it against "
        "docs/reports/V3_3_FINAL_100_QUESTION_BENCHMARK.jsonl, so the denominator is checked "
        "against the artifact rather than remembered -- verified 2026-09-17 by running that "
        "module: 42 tests pass. CapabilitiesResponse recomputes "
        "benchmark_not_answerable_published from the cards and republishes "
        "unpublished_not_answerable, so the completeness claim is a measurement whose closed "
        "state is an empty list, not an assurance.",
        "",
        None,
    ),
    "GAP-PRODUCT_SURFACE-003": Ruling(
        "CLOSED_DERIVED",
        "All three clauses pass. The aggregates are served: /insights/devatas/{id}/by-book, "
        "devata_by_metre and /insights/devatas/{id}/dispersion are routed in "
        "src/vedagraph/api/routes/insights.py. The page-size cap is not worked around but "
        "removed from the path: insight_service.devata_dispersion returns integer positions "
        "rather than passages, because 'returning them as passages would be eighteen pages at "
        "the 200-row cap, and the cap is what made the landscape unfetchable rather than "
        "merely slow'. And the third clause is the checkable one -- "
        "docs/design/research/04-visualization-research.md marks VIZ_BLOCKER_01 at :1071, "
        "VIZ_BLOCKER_02 at :1097 and VIZ_BLOCKER_03 at :1118 all CLOSED, with VIZ_BLOCKER_03 "
        "noted as saying where it is hatched, which is the right handling of a matrix that "
        "metre reaches for RV (10,518 mantras) and AV (4,068) and for neither SV nor YV. "
        "Residual, named: the same document still says at :1797 that a discovery surface is "
        "'blocked on VIZ_BLOCKER_01', which is stale prose in a forward-looking section and "
        "not a live blocker.",
        "",
        None,
    ),
    "GAP-PRODUCT_SURFACE-004": Ruling(
        "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA",
        "The retrieval work is done, the formal re-grade is not, and the reason is on record "
        "with its exact error. Clause 1, Ask reaches Samavedic passages: "
        "src/vedagraph/api/ask/planner.py maps SAMAVEDA to SV and carries a per-corpus "
        "matcher, and the evidence is in the graded artifact rather than the code -- in "
        "data/gold/ask_benchmark_runs/ask_product_v1_final_composite.json, Q34 'What does SV "
        "ARANYA 1.1 contain?' is graded PARTIAL_CORRECT from a POST_FIX_DELTA_RUN at "
        "code_commit 6467c3b with citation_validation PASS, where it had been the MISLEADING "
        "this entry was opened for. Clause 2, the metals route: planner.py :246-255 records "
        "the route to /api/v1/insights/metals and why the English string 'metals' resolved to "
        "nothing before it. Clause 3 is blocked and is NOT claimed passed. The composite "
        "artifact holds MISLEADING 0 and HALLUCINATED 0 over its 60 questions, but at commits "
        "8353167 / 6467c3b / 9dd3ef6 rather than at this HEAD, and owner decision 28 records "
        "what happened when a fresh commit-keyed run was attempted: it 'reached 19 of 60 and "
        "stopped at Q20 with LLMRateLimitError: the daily allowance is exhausted; waiting will "
        "not clear it', only OpenRouter is credentialed, switching model would produce a "
        "different grade rather than a resumption, the earlier partial run is diagnostic only "
        "and not combined, and -- stated in the decision and repeated here -- 'misleading = 0 "
        "is not claimed'. The blocker is recorded with the exact error in "
        "data/staging/integration/dependency_ledger.json and dependency_status.json. Terminal "
        "for the purpose of nothing reading OPEN, counted apart from the closures, and "
        "explicitly not data-completeness closure.",
        "MATCH (m:Mantra {veda:'SV'}) RETURN count(m)",
        1844,
    ),
    "GAP-PRODUCT_SURFACE-005": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The first clause passes and the second is staged and unapplied, by a restriction this "
        "agent also holds. .gitignore now carves the release digests out of the corpus ignore "
        "-- '!data/canonical/*/manifest.json', with the reasoning written beside it and the "
        "SV-UNTRACKED-RELEASE-01 backlog id cited -- so each release's per-file sha256, record "
        "counts and source-snapshot hashes are tracked even while the verse text is not, which "
        "satisfies 'covered by a verified external snapshot with a recorded checksum'. The "
        "four apparatus-contaminated Samavedic verses are not corrected. "
        "data/source_registry/four_veda_backlog.jsonl records SV-APPARATUS-LIFT-01 as "
        "OPEN_CORRECTION_STAGED with the proposal at "
        "data/staging/final_closure_sprint/agent6/gap005_sv_apparatus_corrections.json, naming "
        "the four keys VG:SV:KAU:CHANDA:P01:D08:V04, VG:SV:KAU:ARANYA:D01:V04, "
        "VG:SV:KAU:CHANDA:P04:D05:V06 and VG:SV:KAU:CHANDA:P02:D07:V07, and stating "
        "not_applied_because: 'The agent staging this correction may not write to Neo4j and "
        "may not edit data/canonical in place... applying it is a lead action.' The exact "
        "Cypher and the corrected strings are held. Applying it also moves four content_sha256 "
        "values, so the referent bindings, the release manifest and the derived formula and "
        "reuse edges for those four passages must follow. Genuinely internal actionable work, "
        "held by a permission boundary rather than by a missing source.",
        "",
        None,
    ),
    # ---- quality ---------------------------------------------------------------------
    "GAP-QUALITY-001": Ruling(
        "CLOSED_SCOPE_DECISION",
        "The measurement is unchanged and the classification was wrong. Verified 2026-09-17 by "
        "reading the artifact: data/gold/rigveda_semantic_gold_v1.jsonl holds 120 rows, all "
        "120 with annotator UNANNOTATED, and the declared adjudication and manifest files do "
        "not exist in data/gold, whose whole contents are .reviewer_identity.json, "
        "ask_benchmark_runs, ask_benchmark_v1.jsonl and the two gold files. So the entry's "
        "test does not pass. But it is not internal actionable work and the owner has already "
        "ruled that it is not a gap: "
        "docs/reports/data-completeness/OWNER_DECISIONS.md:106-119, decision 4, is a "
        "correction to exactly this lead error and says 'the original contract allows an "
        "INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET where human annotation is unavailable. "
        "So HUMAN_GOLD_NOT_AVAILABLE is a documented evaluation limitation, not an open "
        "implementation gap, and it does not by itself prevent a COMPLETE decision.' The "
        "registry's own fields agree: implementation_dependency reads 'NONE - the harness, "
        "schema and validator all exist and the validator already flags the emptiness'. The "
        "limitation stays disclosed -- the capability limit calibrated_confidence reports "
        "human_annotated_assertions 0 -- and the same decision forbids the shortcut, that a "
        "source-adjudicated or model-adjudicated set is never to be called human gold.",
        "",
        None,
        citation=(
            "docs/reports/data-completeness/OWNER_DECISIONS.md:106-119 (decision 4, human gold "
            "is not required where source adjudication is the strongest available); "
            "docs/decisions/ADR-014-llm-output-is-candidate-only.md"
        ),
    ),
    "GAP-QUALITY-002": Ruling(
        "CLOSED_SCOPE_DECISION",
        "Verified 2026-09-17 by reading data/gold/theonym_mention_gold_v1.jsonl: 575 rows, all "
        "575 with annotator MODEL_ADJUDICATED and annotator_model recorded, and no human field "
        "of any kind on any row -- no adjudicator, no label_source, no human_reviewed -- so "
        "the entry's test does not pass and no human-labelled evaluation data exists. The set "
        "is honestly typed rather than passed off as human, which is precisely what decision 4 "
        "requires: docs/reports/data-completeness/OWNER_DECISIONS.md:106-119 rules that "
        "HUMAN_GOLD_NOT_AVAILABLE is 'a documented evaluation limitation, not an open "
        "implementation gap', while insisting that 'a source-adjudicated or model-adjudicated "
        "set is never to be called human gold'. The harness for the subsample the entry asks "
        "for is already in the rows -- borderline, stratum and ambiguity_class are present on "
        "all 575 -- so nothing internal is unbuilt; what is missing is reviewer time, which "
        "the decision has disposed of.",
        "",
        None,
        citation=(
            "docs/reports/data-completeness/OWNER_DECISIONS.md:106-119 (decision 4); "
            "docs/decisions/ADR-014-llm-output-is-candidate-only.md"
        ),
    ),
    "GAP-QUALITY-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Clause one is blocked through GAP-QUALITY-001, and clause two is internal and "
        "unwritten -- which is what keeps this entry open honestly rather than parked behind "
        "someone else's blocker. Measured 2026-09-17 by enumerating the confidence value space "
        "per relationship type rather than by querying the value expected: seven predicates "
        "carry a single constant 1.0 on every edge -- HAS_RISHI 17,889, HAS_CHANDAS 16,298, "
        "HAS_DEVATA 10,558, HAS_DEVATA_ASCRIPTION 5,385, HAS_DEVATA_DERIVED 882, "
        "BELONGS_TO_FAMILY 305, ASCRIBES_TO_DEVATA 39 -- and two more are constant on tiny "
        "populations (INVOLVES_SUBSTANCE 0.85 on 3, REFERS_TO_PLACE 0.75 on 1). 51,356 edges "
        "therefore present a filterable quality signal that selects everything or nothing. "
        "Those 1.0s stand for 'source-explicit', which is a tier and not a probability, so "
        "removing or renaming the field on those predicates is deterministic work needing no "
        "ground truth. Only the calibration curves wait on a human-labelled sample.",
        "",
        None,
    ),
    "GAP-QUALITY-004": Ruling(
        "CLOSED_NOT_APPLICABLE",
        "A roll-up with no implementation of its own, and the registry says so in its own "
        "field: implementation_dependency reads 'Closing the layer gaps. This gap is a roll-up "
        "rather than independent work, and should be re-measured after each wave rather than "
        "worked on directly.' Classifying it STILL_IMPLEMENTATION_FIXABLE double-counts work "
        "already held by the entries it rolls up. Verified 2026-09-17 by reading "
        "docs/reports/V3_3_FINAL_100_QUESTION_BENCHMARK.jsonl: 100 rows, 11 FULLY_ANSWERABLE, "
        "68 PARTIALLY_ANSWERABLE, 21 NOT_ANSWERABLE, every row hand-written with method PROBED "
        "and its own caveat and evidence prose -- so a re-run is a human re-probe, not a "
        "script. The 21 NOT_ANSWERABLE are now all published as declared capability limits "
        "with live probes (GAP-PRODUCT_SURFACE-002), and each of the 68 partials reduces to a "
        "named layer gap elsewhere in this registry, so the roll-up has no residue of its own. "
        "The figure this entry should be read for is the constituent count, not a separate "
        "closure.",
        "",
        None,
    ),
    "GAP-QUALITY-005": Ruling(
        "CLOSED_DERIVED",
        "The baseline row that read 'Lemma: RV 6,560' was a true count of mantras carrying at "
        "least one MENTIONS_LEMMA edge and concealed that those edges reached 39 words, so a "
        "reader would infer a 62 per cent lexical index over a 0.4 per cent one. That is now "
        "closed at the source rather than by annotating the row: measured 2026-09-17, "
        "MENTIONS_LEMMA reaches all 10,031 distinct lemmas over 154,261 edges, so "
        "mantras-reached and lemmas-reached no longer tell different stories. Expectation "
        "re-declared from 39 to 10,031.",
        "MATCH (:Mantra)-[:MENTIONS_LEMMA]->(l:Lemma) RETURN count(DISTINCT l)",
        10031,
        prior_expect=39,
        reaudit=(
            "39 distinct lemmas reached became 10,031, which removes the misleading reading "
            "this entry was opened for."
        ),
    ),
    "GAP-QUALITY-006": Ruling(
        "CLOSED_DERIVED",
        "Every clause of a four-clause test passes, measured 2026-09-17, and this was the "
        "entry where every figure in the row was right and the row was still wrong. (1) All "
        "729 :Rishi, 214 :Devata and 575 :Chandas nodes carry occurrence_count; none is null. "
        "(2) Each equals its edge count under one declared scope: 729 of 729, 214 of 214 and "
        "575 of 575 match the degree of the node's own occurrence_predicate (HAS_RISHI, "
        "HAS_DEVATA, HAS_CHANDAS). (3) Rishi nodes reporting zero occurrences fell from 367 to "
        "0, and the Rigvedic seers' figures match their HAS_RISHI degree with a minimum of 2. "
        "(4) The scope is on the node so a reader can tell the conventions apart: "
        "occurrence_scope reads PASSAGE_DEGREE_ALL_GRAINS on all 1,518, beside "
        "occurrence_count_mantra_scope, occurrence_count_container_scope and "
        "occurrence_contract_version. One contract, applied after all loaders.",
        "MATCH (r:Rishi) WHERE r.occurrence_count = 0 RETURN count(r)",
        0,
        prior_expect=367,
        reaudit=(
            "367 Rigveda-only seers reporting zero became 0, and all three labels now carry "
            "the property with a declared scope. Checked against edge degree per label, not "
            "against the loader's own report."
        ),
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
        "Unmoved on both clauses and both are internal. Measured 2026-09-17: USES_OBJECT "
        "stands at 24 edges reaching 15 objects. Of the three objects the entry names by name, "
        "only VG:CONCEPT:MANI-AMULET is wired, at one rite; VG:CONCEPT:DUNDUBHI-DRUM and "
        "VG:CONCEPT:AUDUMBARA-AMULET are wired to no rite at all, so mani at 86 mentions and "
        "dundubhi at 17 stay absent from the ritual-object ranking. The second clause is "
        "unmeasurable as well as unmet: VG:CONCEPT:YUPA-SACRIFICIAL-POST carries no "
        "vedas_with_matches property, so 'reads 3 with VSM 19.17 and 25.29 both matched' "
        "cannot even be evaluated, and the compound Yajurvedic forms the entry names are still "
        "unregistered. The definition -- an object a curated rite is wired to use -- is right "
        "and is what stopped the earlier version ranking a war-chariot and Indra's thunderbolt "
        "as the corpus's foremost ritual objects; the wiring over the enlarged rite population "
        "was not redone.",
        "MATCH ()-[r:USES_OBJECT]->() RETURN count(r)",
        24,
    ),
    "GAP-RITUAL-004": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Moved substantially and does not close. Measured 2026-09-17: :RitualRole stands at 20 "
        "nodes against 11, the hotr now carries a PERFORMED_BY edge -- which was the entry's "
        "clearest symptom, the officiant the Rigveda names most wired to no rite -- and the "
        "denominator is labelled rather than assumed: 18 of the 20 carry denominator_schema, "
        "in_classical_sixteen, samhita_attested and existence_evidence_type, with one row "
        "stating outright that the sixteen are a SRAUTASUTRA schema and not a Samhita one. Two "
        "things keep it open. Only 14 of the 20 are flagged in_classical_sixteen, so 2 of the "
        "classical sixteen are still absent from the registry and the test's 'holds the "
        "classical sixteen' is unmet; and 2 nodes carry a null denominator_schema, null "
        "in_classical_sixteen and null existence_evidence_type, so for those two a reader "
        "cannot tell a non-member from an unclassified row. Both are bounded internal work "
        "over well-attested material.",
        "MATCH (r:RitualRole) WHERE r.in_classical_sixteen IS NULL RETURN count(r)",
        2,
        prior_expect=11,
        reaudit=(
            "The ruling counted RitualRole nodes and declared 11; there are 20. Re-declared on "
            "what the test actually asks -- the classical sixteen with their source stated -- "
            "which leaves 2 unclassified rows and 2 missing officiants."
        ),
    ),
    "GAP-RITUAL-005": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Clause one passes with unusually good evidence and clause two fails wide. Measured "
        "2026-09-17: RECEIVES_OFFERING carries 4 edges, all Devata to Offering, and each "
        "carries real per-edge verse evidence rather than a pipeline constant -- "
        "evidence_citations naming Brahmana and Srautasutra loci (Agni/purodasa cites 19 of "
        "them, AB 7.6.1 through SankhSS 14.2.17), a verbatim evidence_quote in Sanskrit, "
        "mapping_confidence and a reader field. Co-occurrence was not promoted: the four are "
        "asserted from external ritual citation. But only 3 of 103 :Ritual nodes carry an "
        "offering of any kind, so 'every modelled rite carries its offerings' fails at 3 per "
        "cent, which is the entry's second clause and is internal curation over material the "
        "Samhitas state directly.",
        "MATCH ()-[r:RECEIVES_OFFERING]->() RETURN count(r)",
        4,
        prior_expect=0,
        reaudit=(
            "The typed predicate that existed with zero edges now carries 4, each with verse "
            "evidence. The entry stays open on rites without offerings, 100 of 103."
        ),
    ),
    "GAP-RITUAL-006": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The dimension now exists and the test's guarantees about it do not. Measured "
        "2026-09-17: all 20,210 mantras carry a ritual_context, and the absence is typed in "
        "the row rather than left to prose -- NO_RITUAL_CITATION_FOUND 10,538, "
        "UNRESOLVED_SHARED_OPENING 7,769, EMPLOYED_IN_RITE_PROBABLE 1,275, EMPLOYED_IN_RITE "
        "416, RITE_NAMED_IN_THIS_MANTRA 212, which is five values and not the four the "
        "integration report stated. What the test demands and the graph does not supply: the "
        "method is not declared and the precision is not measured. ritual_context is the ONLY "
        "ritual-prefixed property on any Mantra -- there is no ritual_context_method and no "
        "ritual_context_precision anywhere in the database -- so a reader cannot tell what "
        "produced EMPLOYED_IN_RITE_PROBABLE or how often it is right, and the entry's warning "
        "that assigning context by proximity to ritual vocabulary would be circular cannot be "
        "checked from the data. Nor are material-culture counts reported split by context. "
        "Both are internal work over an assignment already landed.",
        "MATCH (m:Mantra) WHERE m.ritual_context IS NOT NULL RETURN count(m)",
        20210,
        prior_expect=0,
        reaudit=(
            "0 mantras carrying a ritual_context became 20,210, five-valued with absence "
            "typed. The entry stays open because its method and precision clauses have no "
            "property in the graph to satisfy them."
        ),
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
        "REVERTED from BLOCKED_OWNER_DECISION_REQUIRED by the R1 hostile pass, against the R1 "
        "adjudication's own ruling, which named this its least certain call. The entry has TWO "
        "clauses and only the second is behind the owner gate. Clause 1 -- 'Every Samavedic "
        "mantra exposes its running Samhita number' -- is unblocked, additive, needs no owner "
        "decision, and is undone: measured 2026-09-17, 0 of 1,844 SV mantras carry a "
        "source_locator or a running_samhita_number, and the source_locator that does exist on "
        "1,844 SV TextVersion rows holds ONE distinct value across all 1,844, the derivation "
        "recipe "
        "'derived:normalize_nfc+fold_devanagari_source_conventions+to_iast+comparison_form:SEARCH_NORMALIZED', "
        "which is not a locator. The number is already captured in the staging artifact by the "
        "entry's own source_dependency field ('NONE. The number is already captured in the "
        "staging artifact'). Clause 2 -- re-deriving all 495 MUSICALIZED_AS edges from the "
        "graph alone -- is genuinely gated behind OWNER_DECISION_E_AUDIO_GATE, and "
        "MUSICALIZED_AS carries 0 edges. Attaching an execution blocker to a row that also "
        "contains undone internal work is the disguise the vocabulary exists to prevent: owner "
        "decision 29 records BLOCKED_OWNER_DECISION_REQUIRED for rows whose obstacle IS the "
        "ungiven decision, and this row's first clause has no such obstacle. It stays not "
        "terminal, and the owner gate on clause 2 is stated rather than used to terminate the "
        "entry. Also verified by independent readback and NOT taken from the manifest: "
        "data/staging/samaveda_music/manifest.json asserts the join was re-derived 495/495 "
        "from the live graph's stored arcika text, which is a text re-derivation rather than "
        "the running-number join the entry requires, and the edges it describes are not in the "
        "graph.",
        "MATCH (m:Mantra {veda:'SV'}) WHERE m.running_samhita_number IS NULL RETURN count(m)",
        1844,
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
        citation="data/registry/works.yaml (all four work scopes); PRODUCT_V1_SCOPE.md",
    ),
    # ---- semantics -------------------------------------------------------------------
    "GAP-SEMANTICS-001": Ruling(
        "CLOSED_DERIVED",
        "Closed in RELEASE BLOCKER CLOSURE R2. Two clauses already passed and the third now "
        "does. Re-measured 2026-09-18: AV 3,295 mantras / 6,167 assertions, YV 574 / 1,543, "
        "SV 211 / 364, RV 10,173 / 27,057. The open clause was the blended total, and the "
        "cross-Veda cell no longer publishes one: it breaks the figure out per derivation, "
        "names the model-assisted share (2,459 of 35,131) apart from the rule-derived "
        "remainder, carries the human-reviewed count -- 0, counted on the positive predicate "
        "review_state = 'HUMAN_REVIEWED' so that adding a new review state cannot silently "
        "promote assertions into review -- and states that coverage is incomplete and uneven. "
        "The same cell was the R2 CROSS_VEDA_FALSE_NOT_BUILT defect and its status moved from "
        "NOT_BUILT to CLASS_NOT_CROSS_VEDA; both changes are held by "
        "tests/api/test_cross_veda_granularity_and_direction.py. PRIOR RULING, superseded: "
        "STILL_IMPLEMENTATION_FIXABLE -- \"Two clauses pass, the third fails on a surface, "
        "and the third is the one the entry's "
        "implementation_dependency was written to protect. Measured 2026-09-17: "
        "HAS_SEMANTIC_ASSERTION reaches three non-Rigvedic corpora -- AV 3,295 mantras / 6,167 "
        "assertions, YV 574 / 1,543, SV 211 / 364 -- and Rigvedic coverage rose from 2,542 to "
        "10,173 mantras over 27,057 assertions. The derivations are separately typed in the "
        "data, five ways. But the cross-Veda insight surface reports a single blended figure: "
        "insight_service.py:1249 emits 'Measured: {assertion_total:,} assertions over {vedas}' "
        "from one sum across all five derivations, so the reader is shown 35,131 with no "
        "indication that 2,459 are TIER_D model extraction over a 19th-century English "
        "translation and 2,406 are TIER_B rule output. The entry states the requirement "
        "plainly -- 'must not present a blended count' -- and splitting that note by "
        "derivation is bounded internal API work.\"",
        "MATCH (:Mantra)-[:HAS_SEMANTIC_ASSERTION]->() RETURN count(*)",
        35131,
    ),
    "GAP-SEMANTICS-002": Ruling(
        "CLOSED_SCOPE_DECISION",
        "Measured 2026-09-17: all 35,131 :SemanticAssertion nodes read review_state UNREVIEWED "
        "and the value space has exactly one member, so the entry's test -- that the count "
        "fall below 4,865 -- does not pass, and coverage work made the review gap 7.2x LARGER "
        "rather than smaller. That is a trade and it is recorded as one. The reason it is not "
        "internal work is measured rather than asserted: "
        "data/staging/final_closure_sprint/agent3/semantic_review_frame_manifest.json declares "
        "the four-valued review_state vocabulary with the per-state fields each requires, "
        "stages a 120-row frame stratified 60/60 by derivation, wrote 0 rows to any reviewed "
        "state, and concludes from its own measurement that 'SOURCE_ADJUDICATED reaches 0 of "
        "the live layer. What remains is a human reading verses. That is reviewer time, not an "
        "unavailable external source, and it is not an implementation gap either.' Owner "
        "decision 4 disposes of that class of absence as a documented evaluation limitation. "
        "The stratification the entry asks for needs no further build: derivation is typed "
        "five ways in the graph (MORPHOLOGY_RULE_PREDICATE_ONLY 28,370, MODEL_EXTRACTION "
        "TIER_D 2,459, MORPHOLOGY_RULE TIER_B 2,406, TREEBANK_DEPREL 1,532, "
        "CROSS_VEDA_TEXT_IDENTITY 364). The limitation must keep being published as one; "
        "closing the entry does not make any assertion reviewed.",
        "MATCH (a:SemanticAssertion) WHERE a.review_state = 'UNREVIEWED' RETURN count(a)",
        35131,
        citation=(
            "docs/reports/data-completeness/OWNER_DECISIONS.md:106-119 (decision 4); "
            "data/staging/final_closure_sprint/agent3/semantic_review_frame_manifest.json"
        ),
        prior_expect=4865,
        reaudit=(
            "4,865 UNREVIEWED became 35,131. The figure is re-declared upward rather than "
            "quietly re-based, and the entry closes on a recorded decision about human review, "
            "not on the count having improved -- it did not."
        ),
    ),
    "GAP-SEMANTICS-003": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "Moved on one reading, unmoved on the range restriction the entry calls its deeper "
        "limit. Measured 2026-09-17: under the named slot edges the entry describes, "
        "assertions carrying ASSERTION_AGENT and ASSERTION_PREDICATE and ASSERTION_TARGET "
        "together number 0, unchanged. Under the RoleFiller mechanism, 341 assertions carry a "
        "predicate plus both an AGENT and a PATIENT role, split AV 285 and YV 56 with 0 in the "
        "Rigveda -- which reproduces the integration report's 341 exactly, and is worth "
        "stating because a looser predicate (AGENT plus any of PATIENT, BENEFICIARY or GOAL) "
        "gives 438 and neither number is wrong, only differently scoped. The second clause "
        "fails outright either way: ASSERTION_TARGET runs to :Devata on all 799 edges and 0 "
        "have a non-Devata target, so an assertion about a deity acting on a mortal, a place "
        "or an object still cannot be expressed. And the 2,052 :RoleFiller nodes are :Internal "
        "with filler_kind and resolved_label null on every one, so the three-slot structure "
        "that does exist points at unresolved strings. Widening the range and reconciling the "
        "two derivations is internal work; both halves are in the graph.",
        "MATCH (a:SemanticAssertion)-[:ASSERTION_TARGET]->(x) WHERE NOT x:Devata RETURN "
        "count(*)",
        0,
    ),
    "GAP-SEMANTICS-004": Ruling(
        "CLOSED_SCOPE_DECISION",
        "No chronological or stratigraphic dimension, and Veda membership is not a period. "
        "The entry's test offers two disjuncts and the second is the one met: 'the absence is "
        "recorded as a deliberate decision with its reasoning'. SELF-CITATION CLEARED in R3. "
        "The R1 hostile pass corrected a citation naming a file not on disk and then named the "
        "residual weakness in terms of its own fix -- 'the decision is written down only in the "
        "audit that closed it. The owner should write it into OWNER_DECISIONS.md, at which "
        "point the citation becomes independent of this file.' The owner has now done exactly "
        "that: OWNER_DECISION_SEMANTICS_004_STRATUM_MAP is recorded verbatim at "
        "docs/reports/data-completeness/OWNER_DECISIONS.md section 34, outside this registry "
        "and outside the audit. It rules that VedAnvaya SHALL NOT ingest or publish an "
        "unattributed historical/chronological stratum map, that a stratum assignment requires "
        "five conjunctive conditions (a named scholarly source, an identifiable work, "
        "attributable methodology, source-local citation, and provenance to the specific "
        "assignment), and that the existence of a named asserter alone is insufficient. "
        "Historical-stratum enrichment is intentionally unsupported for this release until a "
        "specific scholarly stratum source is selected and attributed. Explicitly NOT a source "
        "block: nobody has established that no lawful attributed stratum source exists -- "
        "several do, each one scholar's position -- so calling it "
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE would infer unavailability from not choosing. No "
        "stratum node, edge or property was created; measured 2026-09-18, db.propertyKeys() "
        "holds no stratum, period or chronological_layer key.",
        "",
        None,
        citation=(
            "docs/reports/data-completeness/OWNER_DECISIONS.md section 34 "
            "(OWNER_DECISION_SEMANTICS_004_STRATUM_MAP, recorded verbatim by the owner in a "
            "tracked file outside this registry and outside this audit)"
        ),
    ),
    "GAP-SEMANTICS-005": Ruling(
        "CLOSED_DERIVED",
        "Both clauses pass, including the one that would have forced a false choice. Measured "
        "2026-09-17: 0 of 384 :DomainEntity nodes have a null domain, against 375 with none "
        "when the ruling was written. And multi-domain entities carry every applicable sphere "
        "rather than one -- domain is a list, and 66 entities hold two or three values "
        "(RITUAL+SOCIAL 27, MATERIAL+RITUAL 17, COSMOLOGICAL+GEOGRAPHIC 9, CORPOREAL+SOCIAL 9, "
        "BIOTIC+MATERIAL 5, BIOTIC+MATERIAL+RITUAL 4, and six further pairs) over a declared "
        "VG_DOMAIN_SPHERES_V1 vocabulary, with domain_basis and domain_is_human_annotation "
        "recorded per node.",
        "MATCH (e:DomainEntity) WHERE e.domain IS NULL RETURN count(e)",
        0,
        prior_expect=375,
        reaudit=(
            "375 entities with no domain became 0 over a population that grew to 384, and the "
            "soma problem the entry raised is answered by a list rather than a single value."
        ),
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
        citation="PRODUCT_V1_SCOPE.md:212-221 (no vector database, no embedding "
        "retrieval)",
    ),
    # ---- translation -----------------------------------------------------------------
    # The four below were ruled BLOCKED_OWNER_DECISION_REQUIRED until b4b1b0b resolved the
    # decisions they named: A CLOSED, D CLOSED, C NARROWED_TO_THREE_WITHHELD, recorded in
    # ``owner_decisions_resolved`` on each registry entry and in
    # scripts/translation_integration_registry.py. An entry may not stay blocked on a decision
    # that has been made, so the block is withdrawn -- and the entries do NOT become closures,
    # because each one's own acceptance test still fails over a measured population.
    #
    # The expectation below is the partition b4b1b0b published, not a number read back from
    # the graph afterwards. A MANTRA_RANGE rendering is attached to the odd anchor only and
    # covers the even partner by a derived span rule, so the anchor's partner carries no edge:
    # the graph-measurable "no HAS_TRANSLATION edge at all" population is
    # uncovered + range_covered/2 -- RV 7+30, SV 1671+0, YV 36+0, AV 17+34. Gating on the edge
    # count rather than on "uncovered" keeps the gate independent of the span rule it would
    # otherwise be asserting and measuring at the same time.
    "GAP-TRANSLATION-001": Ruling(
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE",
        "The ruling was right that b4b1b0b's import did not close this and wrong that the "
        "residual is 'unfinished import over material that is staged and addressable'. "
        "Measured 2026-09-17: 1,671 of 1,844 Samavedic mantras are reached by no rendering of "
        "any kind, and every one of the 173 that are reached holds a single source, "
        "VEDAGRAPH_CANONICAL_RV_GRIFFITH, typed REUSED_SURFACE_IDENTICAL -- Griffith's "
        "Rigvedic English on verified-identical text, disclosed as reuse. The count of "
        "Kauthuma-aligned Samavedic translations is still 0, which is what the entry's test "
        "demands, and the reason is on record: the only located Samavedic translation is "
        "Ranayaniya and does not align, and campaign rule 3 forbids force-aligning another "
        "recension onto the one held. The 1,242 staged rows prove the addressing works and do "
        "not supply a Kauthuma witness.",
        "MATCH (m:Mantra {veda:'SV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN count(m)",
        1671,
        blocked_evidence=_SOURCE_ABSENT_SV_TRANSLATION,
    ),
    "GAP-TRANSLATION-002": Ruling(
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE",
        "944 of 961 landed at b4b1b0b and the residual 17 are confirmed absent from the print, "
        "per verse, with the reuse route refused on measurement rather than on policy alone. "
        "Measured 2026-09-17: 51 AV mantras carry no HAS_TRANSLATION edge, and the population "
        "reconciles with no remainder as 34 covered by a DECLARED_RANGE rendering attached to "
        "their anchor plus 17 uncovered -- the entry's own closure_test_as_written_measured "
        "already carries the caveat that this predicate counts a verse inside a multi-verse "
        "print unit as untranslated. All 17 uncovered keys are in kanda 20 and all 17 are "
        "named in data/staging/final_closure_sprint/agent7/residual_disposition.json as "
        "CONFIRMED ABSENT FROM THE PRINT, each tested against every one of the 21,104 Rigvedic "
        "text versions in the store rather than only its asserted parallel. There is no "
        "unfinished import here; there are 17 verses Griffith did not print.",
        "MATCH (m:Mantra {veda:'AV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN count(m)",
        51,
        blocked_evidence=_SOURCE_ABSENT_AV_KANDA20_RESIDUAL,
    ),
    "GAP-TRANSLATION-003": Ruling(
        "CLOSED_VERIFIED_ZERO",
        "A measured, enumerated absence with a per-verse cause for every row, which is the "
        "shape GAP-OTHER-004 already closes under. Measured 2026-09-17: 25 Yajurvedic mantras "
        "carry no rendering, down from 36, and "
        "data/staging/final_closure_sprint/agent7/residual_disposition.json names all 36 "
        "individually -- 11 resolved and imported, leaving exactly 25, which reconciles "
        "against the graph. The 25 decompose with no remainder: 12 are CONFIRMED ABSENT, "
        "PRINTED AS AN OMISSION at VSM 23.20-31, where Griffith printed a row of ellipsis "
        "dots; 9 at VSM 12.97-105 are UNDECIDABLE SPINE DIVERGENCE where 'the English is on "
        "disk and deliberately withheld; binding it is a one-in-ten guess'; 1 at VSM 12.117 "
        "has its address forced by the boundary with no content control; and 3 -- VSM 20.85, "
        "21.45 and 36.24 -- are withheld by name under a standing owner decision. The entry's "
        "own closure_method records that ruling verbatim: 'Owner decision C then ruled the 31 "
        "rows lacking independent content control ineligible, so accepted recovery is 19.' No "
        "deterministic import remains; every remaining route is a guess the campaign has "
        "already refused.",
        "MATCH (m:Mantra {veda:'YV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN count(m)",
        25,
        citation=(
            "data/gap_registry.json GAP-TRANSLATION-003.closure_method (owner decision C, "
            "quoted); data/staging/final_closure_sprint/agent7/residual_disposition.json"
        ),
        prior_expect=36,
        reaudit=(
            "36 untranslated became 25 after b4b1b0b imported the 11 whose provenance defect "
            "was resolved. The residual 25 matches the per-key disposition file exactly."
        ),
    ),
    "GAP-TRANSLATION-004": Ruling(
        "STILL_IMPLEMENTATION_FIXABLE",
        "The residual is 6 verses, 2 of them source-absent and 4 of them deterministic "
        "internal work, so this entry stays open on a named list rather than on a count. "
        "Measured 2026-09-17: 36 Rigvedic mantras carry no HAS_TRANSLATION edge, and the "
        "population reconciles with no remainder as 30 covered by a DECLARED_RANGE rendering "
        "attached to their anchor -- decision A closed and M13 typed Griffith's merged "
        "pair-scope unit rather than splitting it -- plus 6 uncovered. Of the 6, "
        "data/staging/final_closure_sprint/agent7/residual_disposition.json confirms RV "
        "10.86.16 and 10.86.17 absent from the only ingested source, and names four as "
        "MIS-GRAINED, NOT ABSENT: VG:RV:SAK:M05:S055:V008, VG:RV:SAK:M09:S007:V009, "
        "VG:RV:SAK:M10:S048:V007 and VG:RV:SAK:M10:S132:V005. For those four the honest route "
        "is the one already applied to the 30 -- re-type the neighbouring rendering "
        "MANTRA_RANGE so it covers the merged pair -- and not a split of Griffith's prose, "
        "which would fabricate. Four rows of bounded internal work, listed by key.",
        "MATCH (m:Mantra {veda:'RV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN count(m)",
        36,
        prior_expect=37,
        reaudit=(
            "37 untranslated became 36 after one provenance-blocked row was resolved and "
            "imported. The 4 genuinely fixable keys are named in the basis."
        ),
    ),
    "GAP-TRANSLATION-005": Ruling(
        "CLOSED_DERIVED",
        "Both clauses pass, and the second is the interesting one. Measured 2026-09-17: 0 of "
        "18,427 :Translation nodes have a null alignment_confidence. The values are a typed "
        "six-valued vocabulary rather than a number pretending to be a probability -- "
        "MACHINE_ALIGNED_NO_PER_ROW_CONTROL 17,095, SOURCE_LABELLED_MANTRA 880, "
        "REUSED_SURFACE_IDENTICAL 194, HYMN_GRAIN_ONLY 158, DECLARED_RANGE 64, "
        "CONTENT_VERIFIED_MANTRA 36. PRODUCT_V1_SCOPE.md:57 claims '158 are recorded as "
        "uncertain', and that claim is now reproducible from the data rather than "
        "unverifiable: exactly 158 Translation nodes carry HYMN_GRAIN_ONLY and all 158 are "
        "Rigvedic, which is the corpus the sentence is about. A live document's figure stopped "
        "being the one thing nothing could check.",
        "MATCH (t:Translation) WHERE t.alignment_confidence IS NULL RETURN count(t)",
        0,
        prior_expect=0,
        reaudit=(
            "The ruling measured the positive form and declared 0 against 18,427 populated "
            "rows. Re-declared on the entry's own negative predicate, which returns 0, and the "
            "158-uncertain claim reproduces as 158 RV HYMN_GRAIN_ONLY rows."
        ),
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
        "CLOSED_DERIVED",
        "All three clauses of the entry's own test now pass, read back out of Neo4j on "
        "2026-09-17 rather than out of a resolver. (1) A cross-Veda deity query returns RV and "
        "AV dedications for one canonical Devata joining on node identity and no display "
        "label: Agni 1,988 RV dedications and 176 AV, Vanaspati 10 and 122, Indra 2,869 and "
        "76, over 39 ASCRIBES_TO_DEVATA edges reaching 35 distinct deities. (2) Every "
        "unresolved ascription is still addressable in its ascription form -- all 324 "
        ":DevataAscription nodes are present with their entity_key and "
        "is_ascription_descriptor intact. (3) The resolved share was read from the database. "
        "The test never demanded that all 324 resolve; the residual resolution work is "
        "GAP-ATTRIBUTION-002 and stays open there.",
        "MATCH (a:DevataAscription) WHERE (a)-->(:Devata) RETURN count(a)",
        39,
        prior_expect=0,
        reaudit=(
            "The bridge was declared unbuilt and is built for 39 of 324. The entry's test asks "
            "for a label-free join, not for full resolution, so the move closes it."
        ),
    ),
    "GAP-ATTRIBUTION-WHITNEY-UNRESOLVED-OBJECT-001": Ruling(
        "CLOSED_SCOPE_DECISION",
        "The ruling said the stated precondition is now met and the import has not been run, "
        "and that is half the picture. Measured 2026-09-17: the 466 rows have not landed -- no "
        "relationship in the graph carries a source_bracket or a whitney_verse_attribution "
        "property -- and the bounded half of the metre repair IS applied, exactly as "
        "authorised: 28 :Chandas identities are :Internal against 547 public, HAS_CHANDAS "
        "stands at 16,298, and 0 public :Chandas carries a colon. Both figures match decision "
        "27's authorised correction to the digit. What the ruling missed is that the owner has "
        "already disposed of the 466: "
        "docs/reports/data-completeness/OWNER_DECISIONS.md:542-566, decision 25, records that "
        "the permitted resolution channel works (405 of 477, 0 ambiguous) and that nothing is "
        "imported anyway, because 'separating a deity adjective from a metre name inside these "
        "strings is philological adjudication, which may not act as identity evidence, so a "
        "partial import cannot be made safe' -- the three tests written to bound the "
        "contaminated share disagree at 17, 28 and 39, and that disagreement is the finding. "
        "The ruling is explicit: 'All 466 stay RETAINED_NON_IMPORTABLE_UNRESOLVED_OBJECT; the "
        "graph is not mutated.' The stated reason the entry's test asks for therefore exists, "
        "in the decision rather than in Neo4j, and writing it into Neo4j is the mutation the "
        "same decision forbids. The rows are correct, retained and evidenced; what is refused "
        "is turning a philological reading into identity evidence.",
        "MATCH (c:Chandas) WHERE NOT c:Internal AND c.preferred_label CONTAINS ':' RETURN "
        "count(c)",
        0,
        citation=(
            "docs/reports/data-completeness/OWNER_DECISIONS.md:542-566 (decision 25, Whitney "
            "466 withheld and not for want of evidence); "
            "docs/reports/data-completeness/OWNER_DECISIONS.md:589-600 (decision 27, the "
            "authorised 33)"
        ),
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
    """Run one counting query under a real server-side bound.

    ``session.run(timeout=...)`` does not bound anything in this driver -- it binds a
    ``$timeout`` parameter the query never reads. The bound has to travel inside
    :class:`neo4j.Query`.
    """
    record = session.run(Query(cypher, timeout=QUERY_TIMEOUT_SECONDS)).single()
    return None if record is None else int(record[0])


#: Extensions a citation may name directly at the repository root.
_FILE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {"md", "json", "jsonl", "py", "yaml", "yml", "ts", "tsx", "mjs", "txt"}
)


def _cited_paths(citation: str) -> list[str]:
    """Repo-relative paths a reader could actually open, pulled out of a citation.

    Citations in this table are prose with paths in them: ``data/registry/works.yaml (AV
    work scope)``, ``PRODUCT_V1_SCOPE.md:212-221 (no audio redistribution)``,
    ``docs/x.md; the owner ledger``. Splitting on a comma breaks the parentheticals and
    requiring a ``/`` misses every file at the repository root, so a naive parser reports
    a good citation as missing -- which is how the first version of this check produced
    seven false positives.
    """
    paths: list[str] = []
    for clause in citation.split(";"):
        head = clause.split("(", 1)[0].strip().rstrip(".,")
        for token in head.split():
            token = token.strip("`'\",.").split(":", 1)[0]
            # A dotted token is not automatically a path. ``GAP-SEMANTICS-004.closure_basis``
            # names a FIELD, and admitting it as a path made the self-citation check silently
            # pass: ``all(p in _SELF)`` was False because of a token that is not a file at
            # all. Require a directory separator or a known extension.
            if token.endswith("."):
                continue
            if "/" in token or token.rsplit(".", 1)[-1] in _FILE_EXTENSIONS:
                paths.append(token)
    return paths


def audit(session: Session, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [str(g["gap_id"]) for g in gaps]
    unruled = [gid for gid in ids if gid not in RULINGS]
    stray = [gid for gid in RULINGS if gid not in ids]

    on_disk = {str(g["gap_id"]): g for g in gaps}

    rows: list[dict[str, Any]] = []
    findings: list[str] = []
    drift: list[str] = []
    resolved: list[str] = []
    undeclared_reaudit: list[str] = []
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
        if ruling.prior_expect is not None:
            if not ruling.reaudit:
                undeclared_reaudit.append(gid)
            resolved.append(
                f"{gid}: declared {ruling.prior_expect} before integration, re-declared "
                f"{ruling.expect}, graph measures {measured}. {ruling.reaudit}"
            )

        # The registry is not only this audit's output. ``translation_integration_registry.py``
        # writes ``status`` too, so two mechanisms write one field, and until this check existed
        # the audit could disagree with the file it had written and still print
        # ``measurement_disagreements 0`` -- because that list only ever held graph measurements
        # against a pre-declared number, never a ruling against the registry. That is how the
        # gate ruled four translation entries BLOCKED_OWNER_DECISION_REQUIRED, against a
        # registry correctly holding them STILL_IMPLEMENTATION_FIXABLE after their decisions
        # were made, and reported no disagreement at all.
        entry = on_disk[gid]
        registry_status = str(entry.get("status") or "")
        if registry_status and registry_status != status:
            drift.append(
                f"{gid}: the ruling table says {status} and data/gap_registry.json says "
                f"{registry_status}. One of the two is stale. The audit does not get to "
                f"decide which by overwriting the other without the disagreement being read."
            )
        registry_measure = entry.get("closure_measure") or None
        if registry_status and registry_measure != (ruling.measure or None):
            drift.append(
                f"{gid}: the registry publishes a different closure test from the one this "
                f"audit runs. Registry: {registry_measure!r}. Ruling: {ruling.measure!r}. A "
                f"reader checking the entry would measure something the gate never measured."
            )

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
                "closure_prior_expected_value": ruling.prior_expect,
                "closure_reaudit": ruling.reaudit or None,
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

    # Coverage, not just precision. A ruling with no ``expect`` is never compared to anything,
    # so it passes by being skipped -- and 9 of the closures are asserted with no live
    # measurement at all. Reported here so the gate's own blind spot is a number in the
    # artifact rather than an absence a reader has to notice.
    # A scope decision nobody can find is indistinguishable from one invented to clear
    # the board, so the citation has to name a file that is there. Reported, not gating:
    # the rows this finds are pre-existing closures outside the R1 re-adjudication's
    # scope, and silently downgrading a closure this agent did not investigate would be
    # the same class of error in the other direction. Named so it cannot be missed.
    uncitable = sorted(
        r["gap_id"]
        for r in rows
        if r["closure_status"] == "CLOSED_SCOPE_DECISION"
        and not any(
            (PROJECT_ROOT / p).exists()
            for p in _cited_paths(str(r["closure_citation"] or ""))
        )
    )
    # A findable path is not yet an independent one. A scope decision whose only evidence is
    # the registry or this audit is recorded by the mechanism that closed it, which is weaker
    # than the guard's intent even though the file exists. Reported separately, never merged
    # into the count above, so neither number absorbs the other.
    _SELF = ("data/gap_registry.json", "data/staging/wave4/registry_closure_audit.json")
    self_cited = sorted(
        r["gap_id"]
        for r in rows
        if r["closure_status"] == "CLOSED_SCOPE_DECISION"
        and r["gap_id"] not in uncitable
        and all(
            p in _SELF for p in _cited_paths(str(r["closure_citation"] or ""))
        )
    )

    ungated = sorted(
        r["gap_id"] for r in rows if not (r["closure_measure"] and r["closure_expected_value"] is not None)
    )
    ungated_closures = sorted(
        r["gap_id"]
        for r in rows
        if r["gap_id"] in set(ungated) and r["closure_status"] in CLOSED
    )

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
        "resolved_measurement_disagreements": resolved,
        "reaudited_without_a_stated_basis": undeclared_reaudit,
        "registry_status_disagreements": drift,
        "scope_citations_naming_no_file": uncitable,
        "scope_citations_only_self_cited": self_cited,
        "gate_coverage": {
            "entries": len(rows),
            "with_a_gating_measurement": len(rows) - len(ungated),
            "without_a_gating_measurement": len(ungated),
            "ungated": ungated,
            "closures_asserted_with_no_live_measurement": ungated_closures,
        },
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
        with driver.session(database=DB, default_access_mode="READ") as session:
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
    cov = report["gate_coverage"]
    print(
        f"  gated by a measurement        {cov['with_a_gating_measurement']:3} of "
        f"{cov['entries']}  ({cov['without_a_gating_measurement']} ungated, of which "
        f"{len(cov['closures_asserted_with_no_live_measurement'])} are closures)"
    )
    if report["scope_citations_only_self_cited"]:
        print(
            f"\n  SCOPE CITATION IS SELF-CITED: "
            f"{report['scope_citations_only_self_cited']}"
        )
    if report["scope_citations_naming_no_file"]:
        print(
            f"\n  SCOPE CITATION NAMES NO FILE ON DISK: "
            f"{report['scope_citations_naming_no_file']}"
        )
    for finding in report["resolved_measurement_disagreements"]:
        print(f"\n  RESOLVED: {finding}")
    if report["reaudited_without_a_stated_basis"]:
        print(
            f"\n  RE-AUDIT WITHOUT A STATED BASIS: "
            f"{report['reaudited_without_a_stated_basis']}"
        )
    for finding in report["measurement_disagreements"]:
        print(f"\n  DISAGREEMENT: {finding}")
    for finding in report["registry_status_disagreements"]:
        print(f"\n  REGISTRY DRIFT: {finding}")
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
                "closure_prior_expected_value",
                "closure_reaudit",
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
        or report["registry_status_disagreements"]
    )
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
