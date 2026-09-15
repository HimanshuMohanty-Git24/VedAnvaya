#!/usr/bin/env python3
"""Agent 8 -- build data/staging/attribution/ for the Post-V1 Data Completeness Campaign.

Read-only against Neo4j (MATCH/RETURN only) and against every repo artifact it consumes.
Writes nothing outside data/staging/attribution/.

What this emits, and why each part exists
-----------------------------------------

**1. The assessed set (`VG_ATTRIBUTION_CENSUS`).** One row per `:Passage`, carrying the
typed state of all three attribution dimensions. The graph cannot currently distinguish
*examined and the source says nothing* from *never examined*, because run provenance is
written onto produced edges and never onto the passage examined. Campaign section 32
requires 100% assessed coverage on optional dimensions, so that number is unreportable
until the population examined is enumerated. This is that enumeration.

Every dimension cell carries exactly one of:

``SOURCE_EXPLICIT_PRESENT``            a value, stated by the source at THIS granularity
``DERIVED_PRESENT``                    a value, inherited from a container -- not stated here
``ASSESSED_SOURCE_ABSENT``             examined; the source states nothing, with a reason code
``NEVER_ASSESSED``                     no index covering this passage has been read at all
``NOT_APPLICABLE_AT_THIS_GRANULARITY`` no anukramani ascribes attribution to this level

``ASSESSED_SOURCE_ABSENT`` and ``NEVER_ASSESSED`` are never merged, and neither is ever
written as a zero. That distinction is the whole point of the artifact.

The fifth state was added after reading the first matrix this script produced: it reported
1,038 Rigvedic and 568 other containers as missing attribution, which would have inflated
every gap by the container count. A mandala is not a thing the Sarvanukramani ascribes a
deity to, and a Rigvedic *hymn* is a third case again -- the index does state its triad at
sukta scope, and the projection wrote the value onto the sukta's mantras instead, so that
container is empty by our own design and not by the source's silence. Those two now carry
different reason codes.

**2. Per-verse Atharvavedic deity ascriptions (`WHITNEY_AV_PERVERSE_DEVATA`).** Whitney's
bracket states, after the hymn-scope ascription, a list of *per-verse devata exceptions*::

    Brhaddiva Atharvan.--ekadacakam. agneyam: 1, 2. agnim astaut; 3, 4. devan;
    5. dravinodadiprarthanam; 6, 9, 10. vaicvadevi; 7. saumi; 8, 11. aindri. ...

``scripts/build_atharvaveda_anukramani.py`` finds these and drops them -- its tail loop
carries the line ``continue  # a per-verse devata exception, not a metre`` -- and it does
not record the drop, so the discarded population is invisible in the provenance sidecar.
Consequently all 4,816 Atharvavedic deity edges in the graph are ``CONTAINER_INHERITED``
and the layer is 0% source-explicit, while the source in fact addresses individual verses.

These rows are that discarded branch, recovered. They reuse the builder's own lexicon by
importing it (``METRE_STEM``, ``NOT_A_DEVATA``, ``PADA_REFERENCE``, ``METRICAL_APPARATUS``,
``CORRUPT_METRE``, ``VERSE_COUNT_NOTES``, ``SUB_VERSE``, ``numeral``) rather than restating
it, so the metre/devata boundary here is identical to the boundary already tested there.

Three further filters sit on top, each because a first pass put a metre into the deity
namespace, and each recorded per candidate in ``rejected.jsonl``:

* **the enumerated Chandas value space.** ``data/registry/chandas_av.yaml`` and
  ``chandas.yaml`` are read and every label, variant and trailing metre word collected; a
  candidate matching it is refused. ``3-p. pratistha`` and ``virat pathyabrhati`` are
  metres that ``METRE_STEM`` misses -- the first has no listed stem, the second spells
  ``brhati`` without the vowel mark. Enumerating the field's value space catches both.
  Grepping for the metres one expects does not.
* **pada and avasana addresses** (``7-p.``, ``3-av.``, ``1-av. 3-p``). Metrical apparatus
  in every observed instance.
* **values truncated by the parenthetical mask**, i.e. where the printed value included an
  editorial mask span that ``drop_masks`` removed. ``1. [dvidevatya] uta pitrya`` would
  otherwise be emitted as the ascription ``uta pitrya`` -- "and the paternal ones" with its
  head noun deleted. A truncated value is refused, not repaired.

**3. Stranded per-verse metre statements (`WHITNEY_AV_PERVERSE_CHANDAS`).** The builder
emits 85 metre assertions at ``MANTRA_RANGE`` scope, keyed to the HYMN's ``passage_id``
with ``start_sequence``/``end_sequence`` beside it. The importer dropped the bounds and
created the edge on the hymn, so 85 rows became 77 edges -- ``MERGE`` collapsed eight onto
an existing ``(hymn, metre)`` pair -- and not one reached the verse slots the source
actually addresses. These rows carry the same statements to those verses.

Usage
-----
    .venv/Scripts/python.exe data/staging/attribution/build_attribution_staging.py
"""

from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[3]
OUT = REPO / "data" / "staging" / "attribution"
PROOFS = OUT / "proofs"
AV_CORPUS = REPO / "data" / "canonical" / "atharvaveda_saunaka_digital_working_v1"
AGENT = 8
DOMAIN = "attribution"
ALGORITHM_VERSION = "vg-attribution-census-v1"
#: Every JSON artifact in this directory is written with newline=LF. Without it,
#: pathlib on Windows emits CRLF into a directory whose .jsonl siblings are LF, and
#: the next LF-writing edit then rewrites the whole file in the diff for no reason.
LF = chr(10)

SCHEMA_VERSION = "1.0"
CENSUS_SOURCE = "VG_ATTRIBUTION_CENSUS_2026_09_15"

sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_av_builder():
    """Import scripts/build_atharvaveda_anukramani.py as a module, without running it."""
    path = REPO / "scripts" / "build_atharvaveda_anukramani.py"
    spec = importlib.util.spec_from_file_location("avb_agent8", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["avb_agent8"] = module
    spec.loader.exec_module(module)
    return module


def graph_session():
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.environ.get("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    return driver, driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j"))


DIMENSION_PREDICATE = {
    "devata": ("HAS_DEVATA", "HAS_DEVATA_ASCRIPTION"),
    "rishi": ("HAS_RISHI",),
    "chandas": ("HAS_CHANDAS",),
}

LAYER_TO_STATE = {
    "L1_SOURCE_EXPLICIT": "SOURCE_EXPLICIT_PRESENT",
    "L2_DETERMINISTIC_DERIVED": "DERIVED_PRESENT",
}

#: A dimension cell always carries `state` and `edge_count`. `state` is the authoritative
#: typed answer and is never omitted; `edge_count` stays present even when null, because a
#: null population is the campaign's signal for "unknown" and dropping it would leave a
#: consumer free to read the absence as a zero. The supporting list fields are omitted when
#: empty -- an omitted list is an empty list and nothing turns on the distinction, whereas
#: emitting six empty containers per cell across 67,611 cells cost 10 MB of rows.jsonl.
EMPTY_CELL = {"edge_count": None}

#: Short ids for the indices actually read, so the row carries a key rather than a title
#: repeated 67,611 times. The titles are in ASSESSED_INDEX_TITLES and in sources.jsonl.
ASSESSED_INDEX_TITLES = {
    "RV_WSC2023_SARVANUKRAMANI": "WSC2023 Rigvedic Sarvanukramani",
    "AV_BRHATSARVANUKRAMANI_WHITNEY": "Brhatsarvanukramani, Whitney & Lanman bracket "
    "excerpt (Harvard Oriental Series 7-8, 1905)",
    "YV_VSM_RSISUCI": "Vajasaneyi Samhita rsisuci (Sanskrit Wikisource), an "
    "edition-supplied index whose authority is the (unidentified) edition's rather than "
    "the Sarvanukramani's directly",
}


def read_graph(session) -> dict[str, Any]:
    """Every attribution edge, per passage, with the layer and scope it was graded at."""
    state: dict[str, dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    passages: dict[str, dict[str, Any]] = {}

    for record in session.run(
        "MATCH (p:Passage) RETURN p.canonical_key AS key, p.veda AS veda, "
        "p.entity_type AS entity_type, p.canonical_citation AS citation, "
        "labels(p) AS labels"
    ):
        passages[record["key"]] = {
            "veda": record["veda"],
            "entity_type": record["entity_type"],
            "citation": record["citation"],
            "is_mantra": "Mantra" in record["labels"],
        }

    for dimension, predicates in DIMENSION_PREDICATE.items():
        for predicate in predicates:
            query = (
                f"MATCH (p:Passage)-[r:{predicate}]->(t) "
                "RETURN p.canonical_key AS key, r.knowledge_layer AS layer, "
                "r.scope_origin AS scope, r.attribution_precision AS precision, "
                "r.source_id AS source_id, coalesce(t.label_iast, t.preferred_label, "
                "t.display_label) AS value"
            )
            for record in session.run(query):
                cell = state[record["key"]].setdefault(
                    dimension,
                    {
                        "predicates": set(),
                        "layers": set(),
                        "scopes": set(),
                        "precisions": set(),
                        "source_ids": set(),
                        "values": [],
                    },
                )
                cell["predicates"].add(predicate)
                cell["layers"].add(record["layer"])
                cell["scopes"].add(record["scope"])
                cell["precisions"].add(record["precision"])
                if record["source_id"]:
                    cell["source_ids"].add(record["source_id"])
                if record["value"]:
                    cell["values"].append(record["value"])

    return {"passages": passages, "state": state}


#: Which traditional index has actually been READ for each Veda and dimension. This is the
#: fact that decides ASSESSED_SOURCE_ABSENT against NEVER_ASSESSED, and it is a fact about
#: our own ingestion history, not about the tradition.
ASSESSED_BY: dict[tuple[str, str], dict[str, Any]] = {
    ("RV", "devata"): {"index": "RV_WSC2023_SARVANUKRAMANI", "coverage": "ALL"},
    ("RV", "rishi"): {"index": "RV_WSC2023_SARVANUKRAMANI", "coverage": "ALL"},
    ("RV", "chandas"): {"index": "RV_WSC2023_SARVANUKRAMANI", "coverage": "ALL"},
    ("AV", "devata"): {
        "index": "AV_BRHATSARVANUKRAMANI_WHITNEY",
        "coverage": "KANDA_1_19",
        "absent_beyond": "Kanda 20 is absent at source: Whitney excluded it as 'in the main "
        "a pure mass of excerpts from the Rigveda'. No amount of fetching reaches its 143 "
        "hymns / 958 mantras from this index.",
    },
    ("AV", "rishi"): {
        "index": "AV_BRHATSARVANUKRAMANI_WHITNEY",
        "coverage": "KANDA_1_19",
        "absent_beyond": "Kanda 20 is absent at source.",
    },
    ("AV", "chandas"): {
        "index": "AV_BRHATSARVANUKRAMANI_WHITNEY",
        "coverage": "KANDA_1_19",
        "absent_beyond": "Kanda 20 is absent at source.",
    },
    ("YV", "rishi"): {
        "index": "YV_VSM_RSISUCI",
        "coverage": "ALL",
    },
    ("YV", "devata"): {
        "index": None,
        "coverage": "NONE",
        "blocker_code": "YV_KATYAYANA_IS_NOT_MECHANICALLY_RESOLVABLE",
    },
    ("YV", "chandas"): {
        "index": None,
        "coverage": "NONE",
        "blocker_code": "YV_KATYAYANA_IS_NOT_MECHANICALLY_RESOLVABLE",
    },
    ("SV", "devata"): {
        "index": None,
        "coverage": "NONE",
        "blocker_code": "SV_ATTRIBUTION_IS_AT_SAMAN_SCOPE_NOT_VERSE_SCOPE",
    },
    ("SV", "rishi"): {
        "index": None,
        "coverage": "NONE",
        "blocker_code": "SV_ATTRIBUTION_IS_AT_SAMAN_SCOPE_NOT_VERSE_SCOPE",
    },
    ("SV", "chandas"): {
        "index": None,
        "coverage": "NONE",
        "blocker_code": "SV_ATTRIBUTION_IS_AT_SAMAN_SCOPE_NOT_VERSE_SCOPE",
    },
}

#: The five kanda 1-19 hymns the builder reports as "no bracket". All five were read on the
#: page by hand for this artifact: none is a parser defect.
NO_BRACKET_REASON = {
    "VG:AV:SAU:K02:S020": "SOURCE_BACK_REFERENCE_NO_BRACKET_PRINTED",
    "VG:AV:SAU:K02:S021": "SOURCE_BACK_REFERENCE_NO_BRACKET_PRINTED",
    "VG:AV:SAU:K02:S022": "SOURCE_BACK_REFERENCE_NO_BRACKET_PRINTED",
    "VG:AV:SAU:K02:S023": "SOURCE_BACK_REFERENCE_NO_BRACKET_PRINTED",
    "VG:AV:SAU:K10:S005": "SOURCE_MULTI_PART_ASCRIPTION_OUTSIDE_THE_PARSED_ANCHOR",
}

#: Container levels no anukramani ascribes attribution to. An empty cell here is
#: NOT_APPLICABLE, and counting it as missing would inflate every gap by 2,327.
GRANULARITY_NOT_ASSERTED = frozenset({"SECTION", "STRUCTURAL_CONTAINER"})

AV_KANDA = re.compile(r"VG:AV:SAU:K(\d+)")
AV_HYMN = re.compile(r"(VG:AV:SAU:K\d+:S\d+)")


#: The closed vocabulary of absence reasons. The prose lives here, once, and is written to
#: proofs/absence_reason_codes.json; a row carries only the code. Two reasons. The obvious
#: one is size: the same paragraphs repeated across 67,000 dimension cells were 46 MB of
#: rows.jsonl. The one that matters more is that a code is a queryable closed vocabulary and
#: a paragraph is not -- "how many cells are absent because the source is silent, as against
#: because kanda 20 is not in this index at all" is a group-by over codes and a substring
#: search over prose. ``absent()`` raises on a code that is not listed here, rather than
#: letting free text onto a row.
ABSENCE_REASONS: dict[str, str] = {
    "SOURCE_DOES_NOT_ASSERT_AT_THIS_GRANULARITY": "The traditional indices ascribe a seer, a "
    "deity and a metre to a hymn or to a verse, never to a mandala, kanda, prapathaka or "
    "adhyaya container. This cell is NOT a gap and must not be counted as one: doing so would "
    "inflate every attribution gap by 568.",
    "CONTAINER_EMPTY_BY_INGEST_DESIGN": "The WSC2023 Sarvanukramani states this triad at "
    "SUKTA scope, and our projection wrote the value onto the sukta's mantras rather than "
    "onto the sukta itself -- which is exactly where the 8,329 CONTAINER_INHERITED Rigvedic "
    "mantra edges come from. The source is not silent at this key; our graph is. This is an "
    "artefact of how we ingested and it must not read the same as a source silence.",
    "SV_ATTRIBUTION_IS_AT_SAMAN_SCOPE_NOT_VERSE_SCOPE": "Samavedic attribution is printed on "
    "the GANA pages at SAMAN scope, not on the arcika verses, and the same arcika number "
    "receives mutually inconsistent triads from its several gana renderings -- arcika 578 "
    "carries four different deity values across five renderings, one of which prints no "
    "triad. There is additionally no gana Work, no :Saman node, and no running arcika number "
    "on any SV mantra to join on. See proofs/sv_saman_scope_decision.json.",
    "YV_KATYAYANA_IS_NOT_MECHANICALLY_RESOLVABLE": "Katyayana's Sarvanukramana-sutra is "
    "snapshotted locally and cannot be resolved by machine: 49,708 characters of continuous "
    "sutra prose, 168 numbered sutras, ZERO numeric mantra coordinates, 102 lingokta "
    "deferrals where the deity is not named but pointed at, and no field delimiters. Its own "
    "opening sutra also declares chandas legitimately absent for many yajus, which a future "
    "ingest must carry as an asserted-absent reason code and not as unknown. See "
    "proofs/yv_katyayana_measurement.json.",
    "ABSENT_AT_SOURCE_KANDA_20": "Kanda 20 is absent from this index at source. Whitney "
    "excluded it as 'in the main a pure mass of excerpts from the Rigveda', so no amount of "
    "fetching or parsing reaches its 143 hymns and 958 mantras from the Brhatsarvanukramani "
    "bracket excerpt. A different source is required, and the attribution of those mantras is "
    "genuinely unknown rather than measured empty.",
    "SOURCE_BACK_REFERENCE_NO_BRACKET_PRINTED": "Whitney prints no Anukramani bracket here. "
    "The page states the reason: 'This and the three following hymns are mechanical "
    "variations of the one next preceding... For the Anukr. descriptions of the meter, and "
    "for the use by Kauc., see under hymn 19.' The index defers to the preceding hymn instead "
    "of restating, so this is the tradition's own back-reference and not a missing "
    "transcription. Affects AVS 2.20-2.23. Page:Atharva-Veda samhita.djvu/233, revid 7503200.",
    "SOURCE_MULTI_PART_ASCRIPTION_OUTSIDE_THE_PARSED_ANCHOR": "The bracket IS printed, but "
    "the Anukramani divides this hymn into four parts (A=1-24, B=25-35, C=37-41, D=42-50) "
    "ascribed to DIFFERENT authors, and it is set in a hi-template wrapper rather than the "
    "smaller-template anchor the builder reads. A single hymn-scope ascription would be a "
    "fabrication. The four part-scoped ascriptions are a named, recoverable unlock. Affects "
    "AVS 10.5. Page:Atharva-Veda samhita volume 2.djvu/123, revid 7571911.",
    "HYMN_ABSENT_FROM_THE_PARSED_BRACKET_SET_AND_NOT_HAND_ADJUDICATED": "This hymn is neither "
    "among the 583 brackets the builder extracted nor among the five this agent adjudicated "
    "by hand on the page. Reported as unknown rather than as empty, because nothing has "
    "established which it is.",
    "BRACKET_REFUSED_BY_ALIGNMENT_GATE": "The bracket exists and was parsed, and the builder's "
    "stated-verse-count alignment gate then refused the whole hymn -- every predicate, not "
    "only this one -- because the verse count the source states does not match the count our "
    "corpus holds, or because a verse number in the metre list exceeds it. That is the gate "
    "working. For the kanda 15 and 16 paryaya hymns the mismatch is systematic: the source "
    "counts paryaya subsections where our corpus counts verses, so it is a scope mismatch and "
    "not a numbering slip, and relaxing the gate would not recover it. The per-hymn numbers "
    "are in this cell's absence_detail.",
    "SOURCE_STATES_NO_DEVATA_FOR_THIS_HYMN": "The bracket was parsed, it passed the alignment "
    "gate, and it names no deity for this hymn. A measured zero. For the Vratya book (xv) and "
    "book xvi this is a property of the tradition rather than a transcription defect: those "
    "books carry metre only.",
    "SOURCE_STATES_NO_RSI_FOR_THIS_HYMN": "The bracket was parsed, it passed the alignment "
    "gate, and it names no seer for this hymn. A measured zero, concentrated in book xv (all "
    "18 hymns) and book xvi, where Lanman states at vol. II p. 1038 that the Vratya book 'is "
    "treated as a unit in that no seer is named for the whole nor for any part of it'.",
    "SOURCE_STATES_NO_DEFAULT_METRE_FOR_THIS_HYMN": "The bracket was parsed, it passed the "
    "alignment gate, and it states no hymn-default metre. A measured zero. Many such hymns "
    "nonetheless carry per-verse metre exceptions, which is why a hymn can be absent here and "
    "present at verse level.",
    "BRACKET_PARSED_FOR_THIS_DIMENSION_BUT_NO_EDGE_LANDED_IN_THE_GRAPH": "The bracket names a "
    "value for this dimension and this passage carries no edge for it. That is a "
    "rows-sent-versus-rows-landed discrepancy in the import, not a source absence, and it is "
    "the one absence class here that indicates a defect on our side.",
    "INDEX_READ_FOR_THIS_VEDA_AND_DIMENSION_BUT_IT_STATES_NOTHING_AT_THIS_KEY": "An index "
    "covering this Veda and this dimension has been read, and it states no value at this key. "
    "A measured zero.",
}


def absent(
    code: str, assessed_index: str | None, state: str, detail: str | None = None
) -> dict[str, Any]:
    if code not in ABSENCE_REASONS:
        raise KeyError(
            f"absence reason {code!r} is not in the closed vocabulary. Add it to "
            f"ABSENCE_REASONS rather than letting free text onto a row."
        )
    cell = {
        **EMPTY_CELL,
        "state": state,
        "assessed_by": assessed_index,
        "absence_reason_code": code,
    }
    if detail:
        cell["absence_detail"] = detail
    return cell


def classify(
    key: str,
    passage: dict[str, Any],
    cells: dict[str, dict[str, Any]],
    dimension: str,
    av_prov: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """The typed state of one dimension on one passage. Never 0 for an unknown population."""
    veda = passage["veda"]
    cell = cells.get(dimension)
    assessed = ASSESSED_BY.get((veda, dimension), {})
    index_name = assessed.get("index")

    if cell:
        layers = cell["layers"]
        if "L1_SOURCE_EXPLICIT" in layers:
            state = "SOURCE_EXPLICIT_PRESENT"
        else:
            state = LAYER_TO_STATE.get(sorted(layers)[0], "DERIVED_PRESENT")
        if "SINGLE_MANTRA" in cell["scopes"]:
            granularity = "VERSE"
        elif "MANTRA_RANGE" in cell["scopes"]:
            granularity = "VERSE_RANGE"
        else:
            granularity = "HYMN_OR_WIDER"
        present = {
            "state": state,
            "edge_count": len(cell["values"]),
            "values": sorted(set(cell["values"]))[:12],
            "knowledge_layers": sorted(layers),
            "scope_origins": sorted(s for s in cell["scopes"] if s),
            "attribution_precisions": sorted(p for p in cell["precisions"] if p),
            "asserted_granularity": granularity,
            "source_ids": sorted(cell["source_ids"]),
            "assessed_by": index_name,
        }
        return {k: v for k, v in present.items() if v or k == "edge_count"}

    # No value -- and before asking whether anything looked, ask whether the source asserts
    # at this granularity at all. A mandala, a kanda, a prapathaka and an adhyaya are not
    # things any anukramani ascribes a deity, a seer or a metre to, so an empty cell there is
    # NOT_APPLICABLE and calling it a gap would inflate every gap by the container count.
    if passage["entity_type"] in GRANULARITY_NOT_ASSERTED:
        return absent(
            "SOURCE_DOES_NOT_ASSERT_AT_THIS_GRANULARITY",
            index_name,
            "NOT_APPLICABLE_AT_THIS_GRANULARITY",
            detail=f"container level {passage['entity_type']}",
        )

    # A Rigvedic hymn container is a third case again: the WSC2023 index DOES state the triad
    # at sukta scope, but the ingest wrote the value onto the sukta's mantras and not onto the
    # sukta. So the container is empty by our own projection choice, not by source absence,
    # and the two must not read alike.
    if veda == "RV" and passage["entity_type"] == "HYMN":
        return absent(
            "CONTAINER_EMPTY_BY_INGEST_DESIGN", index_name, "ASSESSED_SOURCE_ABSENT"
        )

    # No value. The whole question is now whether anything ever looked.
    if assessed.get("coverage") == "NONE":
        return absent(assessed["blocker_code"], None, "NEVER_ASSESSED")

    if veda == "AV":
        match = AV_KANDA.match(key)
        if match and int(match.group(1)) == 20:
            return absent("ABSENT_AT_SOURCE_KANDA_20", index_name, "NEVER_ASSESSED")
        hymn_match = AV_HYMN.match(key)
        hymn = hymn_match.group(1) if hymn_match else key
        record = av_prov.get(hymn)
        if record is None:
            if hymn in NO_BRACKET_REASON:
                return absent(NO_BRACKET_REASON[hymn], index_name, "ASSESSED_SOURCE_ABSENT")
            return absent(
                "HYMN_ABSENT_FROM_THE_PARSED_BRACKET_SET_AND_NOT_HAND_ADJUDICATED",
                index_name,
                "NEVER_ASSESSED",
            )
        gate = record["verse_count_gate"]
        detail = None
        if gate.startswith("REFUSED"):
            code = "BRACKET_REFUSED_BY_ALIGNMENT_GATE"
            detail = (
                f"{gate}: source states {record['stated_verse_count']} verses, our corpus "
                f"holds {record['corpus_verse_count']}, highest verse referenced "
                f"{record['max_verse_referenced']}"
            )
        elif dimension == "devata" and not record.get("parsed_devata"):
            code = "SOURCE_STATES_NO_DEVATA_FOR_THIS_HYMN"
        elif dimension == "rishi" and not record.get("parsed_rishi"):
            code = "SOURCE_STATES_NO_RSI_FOR_THIS_HYMN"
        elif dimension == "chandas" and not record.get("parsed_default_chandas"):
            code = "SOURCE_STATES_NO_DEFAULT_METRE_FOR_THIS_HYMN"
        else:
            code = "BRACKET_PARSED_FOR_THIS_DIMENSION_BUT_NO_EDGE_LANDED_IN_THE_GRAPH"
        return absent(code, index_name, "ASSESSED_SOURCE_ABSENT", detail=detail)

    return absent(
        "INDEX_READ_FOR_THIS_VEDA_AND_DIMENSION_BUT_IT_STATES_NOTHING_AT_THIS_KEY",
        index_name,
        "ASSESSED_SOURCE_ABSENT",
    )


def fold(text: str) -> str:
    """Strip every combining mark and lowercase, so one metre's spellings collapse to one key.

    Whitney's pages spell the same metre several ways and the registry stores only the
    spellings it happened to receive. ``pathyabrhati`` (printed at viii. 1. 8 without the
    vowel mark under the r) and ``pathyabrhati`` from the registry's ``pathyabrhati`` are the
    same metre, and an exact-string lookup misses it -- which is how ``virat pathyabrhati``
    was emitted as a deity in the first pass of this artifact. HOS also prints ``c`` for
    ``s`` and ``n`` with a macron for ``n`` with a dot, and NFD decomposition folds both.
    """
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(
        character
        for character in decomposed.lower()
        if not unicodedata.combining(character) and character not in "'’́"
    ).strip(" .*")


def chandas_value_space() -> set[str]:
    """Every metre string the project already knows, folded, plus each one's trailing word."""
    import yaml

    space: set[str] = set()

    def add(value: Any) -> None:
        if not isinstance(value, str):
            return
        text = fold(value)
        if len(text) < 3:
            return
        space.add(text)
        words = text.split()
        if words:
            space.add(words[-1])

    for name in ("chandas_av.yaml", "chandas.yaml"):
        path = REPO / "data" / "registry" / name
        if not path.exists():
            continue
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entities = document.get("entities") or document.get("chandas") or []
        if isinstance(entities, dict):
            entities = list(entities.values())
        for entity in entities:
            if not isinstance(entity, dict):
                add(entity)
                continue
            for field in ("preferred_label", "label_iast", "normalized_name", "label_en"):
                add(entity.get(field))
            for variant in (entity.get("source_variants") or []) + (
                entity.get("aliases_iast") or []
            ):
                add(variant)
    return space


#: A pada or avasana address. Metrical apparatus in every observed instance.
#: The leading class admits ``i`` and ``l`` as well as digits: the HOS transcription prints
#: ``2. i-p. asury usnih`` at ii. 16, where ``i-p`` is an OCR reading of ``1-p``. A
#: digits-only class let that through and it stood as a deity in an earlier pass of this
#: artifact, found by reading all 97 accepted rows against their printed brackets.
PADA_AVASANA = re.compile(r"\b[\dil]{1,3}\s*-\s*(?:p|av|f)\b")

#: Hand-adjudicated refusals: (hymn key, printed value) pairs where every filter passes but
#: the printed apparatus does not in fact put the value in the devata slot. Enumerated
#: rather than generalised, because each rests on something a page says and not on a shape.
HAND_REFUSED: dict[tuple[str, str], str] = {
    ("VG:AV:SAU:K12:S002", "mārtvyaḥ"): (
        "hand_refused_slot_is_an_authorship_ascription_not_a_devata -- the bracket reads "
        "'agneyam uta mantroktadevatyam; 21-33. martvyah', which is positionally readable as "
        "a per-verse devata. But Lanman's own note at x. 5 says the Anukramani's corrupt "
        "'martvi' / 'martvi' 'seems to contain an ASCRIPTION OF AUTHORSHIP' and that Ryder "
        "suggests Marica is intended. Emitting it as a deity across thirteen verses would put "
        "a patronymic into the deity namespace on a positional guess. It is recorded instead "
        "as a named lead for a per-verse RSI claim. Note at Page:Atharva-Veda samhita volume "
        "2.djvu/123; bracket at AVS 12.2."
    ),
}
#: An editorial query printed where a value should be.
EDITORIAL_QUERY = re.compile(r"^[?⌊⌋\s]*\??[?⌊⌋\s]*$")
SEGMENT = re.compile(r"(?:^|[;])\s*([0-9][0-9,\s\-]*)\.\s*([^;]+)")


def verse_count_gate(item, ours: int) -> str:
    """The builder's own gate, restated so this pass refuses exactly what it refuses."""
    if item.multi_part:
        return "REFUSED_MULTI_PART_ASCRIPTION"
    gate = "PASS_NOT_STATED"
    if item.stated_count is not None:
        gate = "PASS" if item.stated_count == ours else "REFUSED_COUNT_MISMATCH"
    if not gate.startswith("REFUSED") and item.max_referenced is not None:
        if item.max_referenced > ours:
            return "REFUSED_VERSE_NUMBER_OVERRUN"
        if gate == "PASS_NOT_STATED":
            return "PASS_BY_MAX_REFERENCED"
    return gate


def per_verse_devata(avb, metres: set[str]) -> tuple[list[dict], list[dict], dict]:
    """Re-walk Whitney's per-verse tail and keep the branch the builder discards."""
    pages = avb.load_pages()
    snapshot = {(row["volume"], row["page"]): row for row, _ in pages}
    revid = {(row["volume"], row["page"]): row.get("revid") for row, _ in pages}
    hymns, mantras = avb.load_corpus()
    verse_counts: collections.Counter = collections.Counter()
    for kanda, sukta, _ in mantras:
        verse_counts[(kanda, sukta)] += 1
    brackets = {key: avb.parse_bracket(item) for key, item in avb.extract_brackets(pages).items()}

    accepted: dict[str, dict] = {}
    rejected: list[dict] = []
    stats: collections.Counter = collections.Counter()

    def refuse(key, addresses, value, reason, locator) -> None:
        rejected.append(
            {
                "candidate": f"AVS {key[0]}.{key[1]} verse[{addresses}] -> {value!r}",
                "canonical_key": f"VG:AV:SAU:K{key[0]:02d}:S{key[1]:03d}",
                "dimension": "devata",
                "proposed_value": value,
                "verse_addresses": addresses,
                "reason": reason,
                "source_id": "WHITNEY_AV_PERVERSE_DEVATA",
                "source_locator": locator,
            }
        )
        stats[f"rejected:{reason}"] += 1

    for key in sorted(brackets):
        item = brackets[key]
        hymn = hymns.get(key)
        if hymn is None:
            continue
        gate = verse_count_gate(item, verse_counts[key])
        locator = avb.locator(item)
        if gate.startswith("REFUSED"):
            stats["hymns_gate_refused"] += 1
            continue

        printed = avb.FOOTNOTE_DIGIT.sub(". ", avb.strip_markup(item.raw))
        unwrapped = avb.PARENTHESISED_ASCRIPTION.sub(
            lambda m: m.group(1) + ". ", printed, count=1
        )
        masked, _spans = avb.mask_parentheticals(unwrapped)
        if masked.count("—") > 1:
            stats["hymns_multi_part"] += 1
            continue
        stats["hymns_examined"] += 1
        rest = masked.split("—", 1)[1] if "—" in masked else masked
        _head, tail, _boundary = avb.split_head_and_tail(rest)

        for match in SEGMENT.finditer(tail):
            addresses, raw_value = match.group(1), match.group(2)
            masked_value = re.sub(r"\s+", " ", raw_value).strip(" .")
            value = re.sub(r"\s+", " ", avb.drop_masks(raw_value)).strip(" .")
            stats["tail_segments_seen"] += 1

            if avb.SUB_VERSE.search(addresses) or avb.SUB_VERSE.search(value):
                stats["segments_sub_verse_addressed"] += 1
                continue

            fused_tail = None
            if avb.METRE_STEM.search(value):
                # The per-verse devata list and the per-verse metre list are printed in one
                # period-delimited run with no field markers, so a devata exception standing
                # at the head of a segment is followed by metre text inside the same segment.
                # Whitney separates the two with a colon on some pages and with a bare period
                # on others -- "3. saumya. anustubham: 3. 3-p. viran nama gayatri" against
                # "2. savitri. 1. 1-p. brahmy anustubh" -- and the first pass of this artifact
                # handled only the colon, which silently lost the period cases.
                #
                # The rule that covers both: take the LEADING run of period-delimited parts
                # and stop at the first part that is a metre, a numeral, a pada or avasana
                # address, or anything the builder's lexicon refuses. The metre list always
                # FOLLOWS the devata list in this apparatus and never precedes it, so a
                # leading part that survives every filter is in the devata slot.
                head_part, colon, after_colon = value.partition(":")
                parts = [p.strip(" .*") for p in re.split(r"\.\s+", head_part) if p.strip(" .*")]
                leading: list[str] = []
                stopped_at = 0
                for index, part in enumerate(parts):
                    if (
                        avb.METRE_STEM.search(part)
                        or avb.numeral(part) is not None
                        or PADA_AVASANA.search(part)
                        or avb.PADA_REFERENCE.match(part)
                        or avb.NOT_A_DEVATA.match(part)
                        or fold(part) in metres
                    ):
                        stopped_at = index
                        break
                    leading.append(part)
                else:
                    stopped_at = len(parts)
                if not leading:
                    stats["segments_are_a_metre"] += 1
                    continue
                if len(leading) > 1:
                    refuse(
                        key,
                        addresses,
                        value,
                        "fused_segment_has_more_than_one_leading_non_metre_part_slot_ambiguous",
                        locator,
                    )
                    continue
                value = leading[0]
                remainder = ". ".join(parts[stopped_at:])
                if colon:
                    remainder = (remainder + ": " + after_colon).strip(" :")
                fused_tail = remainder or None
                stats[
                    "segments_fused_devata_into_metre_by_colon"
                    if colon
                    else "segments_fused_devata_into_metre_by_period"
                ] += 1

            if not value or EDITORIAL_QUERY.match(value):
                refuse(key, addresses, masked_value, "value_is_an_editorial_query", locator)
                continue
            # A masked span BEFORE any letter means the head noun itself was masked, so the
            # surviving text is a fragment: "1. [dvidevatya] uta pitrya" would be emitted as
            # the ascription "uta pitrya" -- "and the paternal ones" with its head deleted.
            # Refuse that. A mask AFTER the value is a trailing gloss -- "1. brahmadityam
            # (astaut)", 'he praised Brahma-Aditya' -- and the value in front of it is whole,
            # so it is kept and the printed parenthetical is recorded on the row.
            gloss = None
            if "\x00" in masked_value:
                before_mask = masked_value.split("\x00", 1)[0]
                if not re.search(r"[A-Za-zÀ-ɏḀ-ỿ]", before_mask):
                    refuse(
                        key,
                        addresses,
                        masked_value,
                        "value_truncated_by_editorial_bracket_mask_head_noun_would_be_lost",
                        locator,
                    )
                    continue
                gloss = re.sub(r"\s+", " ", avb.unmask(masked_value, _spans)).strip(" .")
                value = re.sub(r"\s+", " ", before_mask).strip(" .*")
            if PADA_AVASANA.search(value):
                refuse(key, addresses, value, "value_is_a_pada_or_avasana_address", locator)
                continue
            if avb.METRICAL_APPARATUS.search(value) or avb.CORRUPT_METRE.search(value):
                refuse(key, addresses, value, "value_is_metrical_apparatus", locator)
                continue
            if avb.PADA_REFERENCE.match(value) or avb.NOT_A_DEVATA.match(value):
                refuse(key, addresses, value, "value_is_not_a_devata_by_builder_lexicon", locator)
                continue
            if value in avb.VERSE_COUNT_NOTES or avb.numeral(value) is not None:
                refuse(key, addresses, value, "value_is_a_printed_verse_count", locator)
                continue
            hand = HAND_REFUSED.get((hymn["canonical_key"], value))
            if hand:
                refuse(key, addresses, value, hand, locator)
                continue
            folded = fold(value)
            words = folded.split()
            last = words[-1] if words else ""
            if folded in metres or (len(last) >= 4 and last in metres):
                refuse(
                    key,
                    addresses,
                    value,
                    "value_is_a_known_metre_name_in_the_enumerated_chandas_value_space",
                    locator,
                )
                continue

            verses: list[int] = []
            for part in addresses.split(","):
                part = part.strip()
                if not part:
                    continue
                if "-" in part:
                    low, _, high = part.partition("-")
                    if low.strip().isdigit() and high.strip().isdigit():
                        verses.extend(range(int(low), int(high) + 1))
                elif part.isdigit():
                    verses.append(int(part))
            if not verses or any((key[0], key[1], v) not in mantras for v in verses):
                refuse(
                    key,
                    addresses,
                    value,
                    "verse_address_does_not_resolve_to_a_mantra_in_our_corpus",
                    locator,
                )
                continue

            for verse in verses:
                mantra = mantras[(key[0], key[1], verse)]
                slot = accepted.setdefault(
                    mantra["canonical_key"],
                    {
                        "canonical_key": mantra["canonical_key"],
                        "citation": mantra["canonical_citation"],
                        "values": [],
                        "verse_addresses": [],
                        "printed_bracket": avb.strip_markup(item.raw),
                        "source_locator": locator,
                        "page_url": snapshot[(item.volume, item.page)]["page_url"],
                        "revid": revid[(item.volume, item.page)],
                        "snapshot_sha256": snapshot[(item.volume, item.page)]["snapshot_sha256"],
                        "hymn_key": hymn["canonical_key"],
                        "verse_count_gate": gate,
                        "unconsumed_metre_tail": None,
                        "printed_parentheticals": [],
                    },
                )
                if value not in slot["values"]:
                    slot["values"].append(value)
                if addresses not in slot["verse_addresses"]:
                    slot["verse_addresses"].append(addresses)
                if fused_tail:
                    slot["unconsumed_metre_tail"] = fused_tail.strip()
                if gloss and gloss not in slot["printed_parentheticals"]:
                    slot["printed_parentheticals"].append(gloss)
                stats["verse_slots_accepted"] += 1

    return list(accepted.values()), rejected, dict(stats)


def stranded_range_chandas(avb) -> tuple[list[dict], list[dict], dict]:
    """The 85 MANTRA_RANGE metre assertions, carried to the verses they address."""
    hymns, mantras = avb.load_corpus()
    by_entity_id = {record["entity_id"]: record for record in hymns.values()}
    mantra_by_seq: dict[tuple[str, int], dict] = {}
    for (kanda, sukta, verse), record in mantras.items():
        hymn = hymns.get((kanda, sukta))
        if hymn:
            mantra_by_seq[(hymn["entity_id"], verse)] = record

    rows: dict[str, dict] = {}
    rejected: list[dict] = []
    stats: collections.Counter = collections.Counter()
    for line in (AV_CORPUS / "traditional_metadata.jsonl").read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        scope = record.get("scope") or {}
        if scope.get("scope_type") != "MANTRA_RANGE":
            continue
        stats["range_assertions_in_artifact"] += 1
        hymn = by_entity_id.get(scope["passage_id"])
        if hymn is None:
            rejected.append(
                {
                    "candidate": f"MANTRA_RANGE {record['value']!r}",
                    "canonical_key": None,
                    "dimension": "chandas",
                    "reason": "range_assertion_passage_id_does_not_resolve_to_a_hymn",
                    "source_id": "WHITNEY_AV_PERVERSE_CHANDAS",
                    "source_locator": record["source_locator"],
                }
            )
            continue
        for verse in range(scope["start_sequence"], scope["end_sequence"] + 1):
            mantra = mantra_by_seq.get((hymn["entity_id"], verse))
            if mantra is None:
                rejected.append(
                    {
                        "candidate": f"{hymn['canonical_key']} v{verse} -> {record['value']!r}",
                        "canonical_key": hymn["canonical_key"],
                        "dimension": "chandas",
                        "reason": "range_member_verse_absent_from_our_corpus",
                        "source_id": "WHITNEY_AV_PERVERSE_CHANDAS",
                        "source_locator": record["source_locator"],
                    }
                )
                continue
            slot = rows.setdefault(
                mantra["canonical_key"],
                {
                    "canonical_key": mantra["canonical_key"],
                    "citation": mantra["canonical_citation"],
                    "hymn_key": hymn["canonical_key"],
                    "values": [],
                    "ranges": [],
                    "source_locator": record["source_locator"],
                },
            )
            if record["value"] not in slot["values"]:
                slot["values"].append(record["value"])
            label = f"{scope['start_sequence']}-{scope['end_sequence']}"
            if label not in slot["ranges"]:
                slot["ranges"].append(label)
            stats["verse_slots_accepted"] += 1
    return list(rows.values()), rejected, dict(stats)


def sha256_of(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def count_lines(path: pathlib.Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


#: One line per Veda for the census rows, which repeat 22,537 times. The full statement
#: lives in sources.jsonl and in each Work's own `scope` property; the row carries the
#: identifying recension and the mantra count that pins it.
RECENSION_SHORT = {
    "RV": "Sakala; VG:WORK:RV:SAK; 10,552 mantras, matching the WSC2023 Sakala index",
    "SV": "Kauthuma arcika; VG:WORK:SV:KAU; 1,844 mantras; the gana corpus is excluded "
    "by the Work's own scope statement",
    "YV": "Sukla YV, Vajasaneyi Madhyandina; VG:WORK:YV:VSM; 1,975 mantras; Krishna YV "
    "and Kanva both absent",
    "AV": "Saunaka; VG:WORK:AV:SAU; 5,839 mantras; Paippalada not held",
}

RECENSION_EVIDENCE = {
    "RV": "Sakala. VG:WORK:RV:SAK, 10,552 mantras; the WSC2023 index is the Sakala "
    "Sarvanukramani and the mantra count matches it exactly.",
    "SV": "Kauthuma arcika. VG:WORK:SV:KAU, 1,844 mantras; the Work's own scope statement "
    "names the recension and explicitly excludes the gana corpus.",
    "YV": "Sukla Yajurveda, Vajasaneyi Madhyandina. VG:WORK:YV:VSM, 1,975 mantras; the "
    "Krishna Yajurveda and the Kanva recension are both absent from the corpus.",
    "AV": "Saunaka. VG:WORK:AV:SAU, 5,839 mantras; Whitney & Lanman's edition is of the "
    "Saunaka recension by its own title page, and Paippalada is not held.",
}

SOURCES = [
    {
        "source_id": CENSUS_SOURCE,
        "title": "VedaGraph canonical store -- attribution assessed-set census, read-only",
        "kind": "INTERNAL_MEASUREMENT",
        "url": "internal: the canonical VedaGraph Neo4j store",
        "retrieved_at": "2026-09-15",
        "graph_snapshot": "108,779 nodes / 265,295 relationships -- the Wave 0 closure "
        "figure, re-verified at the start of this run",
        "quality_class": "PRIMARY_DIGITAL_EDITION",
        "rights": "project-internal",
        "notes": "Every cell is computed from the live graph plus the Atharvavedic bracket "
        "provenance sidecar. No value is invented; no absence is asserted without a reason "
        "code; ASSESSED_SOURCE_ABSENT and NEVER_ASSESSED are never merged.",
    },
    {
        "source_id": "WHITNEY_AV_PERVERSE_DEVATA",
        "title": "Brhatsarvanukramani per-verse devata exceptions, as printed in the hymn "
        "brackets of Whitney & Lanman, Atharva-Veda Samhita (HOS 7-8, 1905)",
        "kind": "TRADITIONAL_INDEX",
        "url": "https://en.wikisource.org/wiki/Page:Atharva-Veda_samhita.djvu",
        "retrieved_at": "2026-09-09 (1,254 pinned Page:-namespace revisions)",
        "quality_class": "TRADITIONAL_INDEX",
        "rights": "text public domain (1905); Wikisource transcription CC BY-SA 4.0",
        "recension": "Saunaka",
        "manifest": "data/raw/wikisource_whitney_avs/anukramani_page_manifest.jsonl",
        "notes": "The same pinned pages as the existing Atharvavedic attribution layer. This "
        "source_id names the per-verse devata branch of the bracket tail, which "
        "scripts/build_atharvaveda_anukramani.py identifies and discards without recording "
        "the discard. No new acquisition was needed and none was made.",
    },
    {
        "source_id": "WHITNEY_AV_PERVERSE_CHANDAS",
        "title": "Brhatsarvanukramani per-verse metre exceptions at MANTRA_RANGE scope, as "
        "already emitted by scripts/build_atharvaveda_anukramani.py",
        "kind": "TRADITIONAL_INDEX",
        "url": "https://en.wikisource.org/wiki/Page:Atharva-Veda_samhita.djvu",
        "retrieved_at": "2026-09-09 (pinned); the artifact was regenerated on 2026-09-15 and "
        "reproduced byte-for-byte",
        "quality_class": "TRADITIONAL_INDEX",
        "rights": "text public domain (1905); Wikisource transcription CC BY-SA 4.0",
        "recension": "Saunaka",
        "notes": "Not an acquisition. These are the 85 MANTRA_RANGE assertions already in "
        "data/canonical/atharvaveda_saunaka_digital_working_v1/traditional_metadata.jsonl, "
        "carried to the verses the source addresses instead of stopping at the hymn.",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PROOFS.mkdir(parents=True, exist_ok=True)
    created = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()

    avb = load_av_builder()
    metres = chandas_value_space()
    print(f"enumerated chandas value space: {len(metres)} strings")

    av_prov = {
        json.loads(line)["hymn_key"]: json.loads(line)
        for line in (AV_CORPUS / "traditional_metadata_provenance.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    print(f"AV bracket provenance rows: {len(av_prov)}")

    driver, session = graph_session()
    try:
        graph = read_graph(session)
    finally:
        session.close()
        driver.close()
    passages, state = graph["passages"], graph["state"]
    print(f"passages read from graph: {len(passages)}")

    devata_rows, devata_rejected, devata_stats = per_verse_devata(avb, metres)
    print(f"per-verse AV devata: {len(devata_rows)} verse rows, {len(devata_rejected)} rejected")
    chandas_rows, chandas_rejected, chandas_stats = stranded_range_chandas(avb)
    print(f"stranded range chandas: {len(chandas_rows)} verse rows")

    new_devata = {row["canonical_key"] for row in devata_rows}
    new_chandas = {row["canonical_key"] for row in chandas_rows}

    rows: list[dict] = []
    matrix: dict[str, dict[str, collections.Counter]] = collections.defaultdict(
        lambda: collections.defaultdict(collections.Counter)
    )
    container_matrix: dict[str, dict[str, collections.Counter]] = collections.defaultdict(
        lambda: collections.defaultdict(collections.Counter)
    )
    absence_reasons: collections.Counter = collections.Counter()

    for key in sorted(passages):
        passage = passages[key]
        cells = state.get(key, {})
        payload: dict[str, Any] = {
            "veda": passage["veda"],
            "entity_type": passage["entity_type"],
            "citation": passage["citation"],
            "is_mantra": passage["is_mantra"],
        }
        for dimension in ("devata", "rishi", "chandas"):
            cell = classify(key, passage, cells, dimension, av_prov)
            if dimension == "devata" and key in new_devata:
                cell["staged_upgrade"] = (
                    "this artifact stages a SOURCE_EXPLICIT verse-scope devata ascription "
                    "for this key via WHITNEY_AV_PERVERSE_DEVATA"
                )
            if dimension == "chandas" and key in new_chandas:
                cell["staged_upgrade"] = (
                    "this artifact stages a SOURCE_EXPLICIT verse-scope metre for this key "
                    "via WHITNEY_AV_PERVERSE_CHANDAS"
                )
            payload[dimension] = cell
            target = matrix if passage["is_mantra"] else container_matrix
            target[passage["veda"]][dimension][cell["state"]] += 1
            if cell.get("absence_reason_code"):
                absence_reasons[
                    f"{passage['veda']}|{dimension}|{cell['absence_reason_code']}"
                ] += 1
        rows.append(
            {
                "canonical_key": key,
                "payload": payload,
                "evidence_layer": "DETERMINISTIC_DERIVED",
                "source_id": CENSUS_SOURCE,
                "source_locator": f"Neo4j attribution census 2026-09-15, passage {key}",
                "source_url": "internal: the canonical VedaGraph store, read-only",
                "quality_class": "PRIMARY_DIGITAL_EDITION",
                "mapping_method": "canonical_key read off the :Passage node; no mapping done",
                "mapping_confidence": "EXACT",
                "recension_verified": True,
                "recension_evidence": RECENSION_SHORT[passage["veda"]],
                "veda": passage["veda"],
            }
        )

    for row in devata_rows:
        rows.append(
            {
                "canonical_key": row["canonical_key"],
                "payload": {
                    "veda": "AV",
                    "dimension": "devata",
                    "predicate": "HAS_DEVATA_ASCRIPTION",
                    "target_type": "DevataAscription",
                    "values_verbatim": row["values"],
                    "entity_resolution_method": "VERBATIM_SOURCE_STRING_NOT_RESOLVED",
                    "asserted_granularity": "VERSE",
                    "scope_type": "SINGLE_MANTRA",
                    "source_verse_addresses": row["verse_addresses"],
                    "hymn_key": row["hymn_key"],
                    "printed_bracket": row["printed_bracket"],
                    "verse_count_gate": row["verse_count_gate"],
                    "unconsumed_metre_tail": row["unconsumed_metre_tail"],
                    "printed_parentheticals_kept_verbatim": row["printed_parentheticals"],
                    "relation_to_hymn_value": "this does NOT supersede the hymn-scope "
                    "ascription. The bracket states an EXCEPTION for this verse; the "
                    "CONTAINER_INHERITED hymn value remains a separate and weaker assertion, "
                    "and a consumer must be able to see both.",
                },
                "evidence_layer": "SOURCE_EXPLICIT",
                "source_id": "WHITNEY_AV_PERVERSE_DEVATA",
                "source_locator": row["source_locator"],
                "source_url": row["page_url"],
                "quality_class": "TRADITIONAL_INDEX",
                "mapping_method": "the bracket addresses the verse by printed numeral; the "
                "numeral is resolved against our own mantra sequence under that hymn key, "
                "and the hymn passed the builder's stated-verse-count alignment gate",
                "mapping_confidence": "EXACT",
                "recension_verified": True,
                "recension_evidence": RECENSION_EVIDENCE["AV"],
                "veda": "AV",
                "snapshot_sha256": row["snapshot_sha256"],
                "snapshot_revid": row["revid"],
            }
        )

    for row in chandas_rows:
        rows.append(
            {
                "canonical_key": row["canonical_key"],
                "payload": {
                    "veda": "AV",
                    "dimension": "chandas",
                    "predicate": "HAS_CHANDAS",
                    "values_verbatim": row["values"],
                    "entity_resolution_method": "VERBATIM_SOURCE_STRING_NOT_RESOLVED",
                    "asserted_granularity": "VERSE",
                    "scope_type": "SINGLE_MANTRA",
                    "source_verse_ranges": row["ranges"],
                    "hymn_key": row["hymn_key"],
                    "defect_closed": "the builder emits these at MANTRA_RANGE scope keyed to "
                    "the HYMN passage_id with start_sequence/end_sequence beside it. The "
                    "importer dropped the bounds and MERGEd on (hymn, metre), so 85 rows "
                    "became 77 hymn-level edges and not one reached the verses addressed.",
                },
                "evidence_layer": "SOURCE_EXPLICIT",
                "source_id": "WHITNEY_AV_PERVERSE_CHANDAS",
                "source_locator": row["source_locator"],
                "source_url": "https://en.wikisource.org/wiki/Page:Atharva-Veda_samhita.djvu",
                "quality_class": "TRADITIONAL_INDEX",
                "mapping_method": "start_sequence..end_sequence taken from the builder's own "
                "MANTRA_RANGE scope and expanded against our mantra sequence under that hymn",
                "mapping_confidence": "EXACT",
                "recension_verified": True,
                "recension_evidence": RECENSION_EVIDENCE["AV"],
                "veda": "AV",
            }
        )

    rejected = devata_rejected + chandas_rejected
    write_jsonl(OUT / "rows.jsonl", rows)
    write_jsonl(OUT / "rejected.jsonl", rejected)
    write_jsonl(OUT / "sources.jsonl", SOURCES)
    print(f"rows.jsonl {len(rows)}  rejected.jsonl {len(rejected)}  sources {len(SOURCES)}")

    (PROOFS / "per_veda_attribution_matrix.json").write_text(
        json.dumps(
            {
                "note": "Counts of :Mantra passages by typed state, per Veda per dimension. "
                "SOURCE_EXPLICIT_PRESENT and DERIVED_PRESENT together are 'has a value'; "
                "reporting only their sum as coverage is the misreading this table exists to "
                "prevent. ASSESSED_SOURCE_ABSENT is a measured zero. NEVER_ASSESSED is "
                "unknown, and is not a zero.",
                "mantra_scope": {
                    veda: {dim: dict(counter) for dim, counter in sorted(dims.items())}
                    for veda, dims in sorted(matrix.items())
                },
                "container_scope": {
                    veda: {dim: dict(counter) for dim, counter in sorted(dims.items())}
                    for veda, dims in sorted(container_matrix.items())
                },
                "absence_reason_histogram": dict(absence_reasons.most_common()),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline=LF,
    )

    (PROOFS / "absence_reason_codes.json").write_text(
        json.dumps(
            {
                "note": "The closed vocabulary of absence_reason_code values used in "
                "rows.jsonl. A code absent from this file is a generator bug: absent() "
                "raises on an unknown code rather than letting free text onto a row.",
                "codes": ABSENCE_REASONS,
                "assessed_index_titles": ASSESSED_INDEX_TITLES,
                "cell_shape": "every dimension cell carries `state` and `edge_count`. "
                "`state` is the authoritative typed answer. `edge_count: null` means the "
                "population is unknown and must not be read as zero. Omitted list fields "
                "(values, knowledge_layers, scope_origins, attribution_precisions, "
                "source_ids) are empty.",
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline=LF,
    )

    (PROOFS / "generation_stats.json").write_text(
        json.dumps(
            {
                "per_verse_devata": devata_stats,
                "stranded_range_chandas": chandas_stats,
                "chandas_value_space_size": len(metres),
                "counts": {
                    "census_rows": len(passages),
                    "new_devata_verse_rows": len(devata_rows),
                    "new_chandas_verse_rows": len(chandas_rows),
                    "rejected": len(rejected),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline=LF,
    )

    files = [
        {
            "path": name,
            "sha256": sha256_of(OUT / name),
            "rows": count_lines(OUT / name),
            "bytes": (OUT / name).stat().st_size,
        }
        for name in ("rows.jsonl", "rejected.jsonl", "sources.jsonl")
    ]

    unresolved = count_lines(PROOFS / "sv_saman_attribution_unresolved.jsonl")

    manifest = {
        "domain": DOMAIN,
        "agent": AGENT,
        "schema_version": SCHEMA_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "created_at": created,
        "code_commit": commit,
        "config_hash": hashlib.sha256(
            json.dumps(
                {
                    "assessed_by": {f"{k[0]}:{k[1]}": v for k, v in ASSESSED_BY.items()},
                    "no_bracket_reason": NO_BRACKET_REASON,
                    "algorithm_version": ALGORITHM_VERSION,
                    "chandas_value_space_size": len(metres),
                },
                sort_keys=True,
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest(),
        "source_snapshot_ids": [s["source_id"] for s in SOURCES],
        "files": files,
        "counts": {
            "candidates_considered": len(rows) + len(rejected) + unresolved,
            "accepted": len(rows),
            "rejected": len(rejected),
            "verified_zero": sum(
                1
                for row in rows
                if row["source_id"] == CENSUS_SOURCE
                and all(
                    row["payload"][d]["state"] == "ASSESSED_SOURCE_ABSENT"
                    for d in ("devata", "rishi", "chandas")
                )
            ),
            "not_applicable": sum(
                1
                for row in rows
                if row["source_id"] == CENSUS_SOURCE
                and all(
                    row["payload"][d]["state"] == "NOT_APPLICABLE_AT_THIS_GRANULARITY"
                    for d in ("devata", "rishi", "chandas")
                )
            ),
            "unresolved": unresolved,
        },
        "closes_gaps": ["GAP-ATTRIBUTION-003", "GAP-ATTRIBUTION-008"],
        "advances_gaps": {
            "GAP-ATTRIBUTION-001": "reduces the no-dedication population by 33 Atharvavedic "
            "mantras (5,498 -> 5,465) and, separately, takes Atharvavedic SOURCE_EXPLICIT "
            "deity coverage from 0 mantras to 83.",
            "GAP-ATTRIBUTION-006": "reduces the no-metre population by 117 Atharvavedic "
            "mantras (5,610 -> 5,493) and upgrades 258 more from CONTAINER_INHERITED to "
            "verse-level SOURCE_EXPLICIT.",
            "GAP-ATTRIBUTION-007": "does not close it; RECLASSIFIES it. 427 seers lack a "
            "family edge, 421 of them for a reason the layer already states, and 6 for an "
            "unresolved reason (5 SOURCE_SPELLING_OUTSIDE_TABLE, 1 ETYMON_UNCERTAIN). See "
            "proofs/stale_claim_disproofs.json.",
            "GAP-ATTRIBUTION-004": "confirmed source-blocked at verse scope, with the reason "
            "measured rather than assumed. See proofs/sv_saman_scope_decision.json.",
            "GAP-PRODUCT_SURFACE-001": "supplies the per-Veda per-dimension matrix the deity "
            "insight endpoint needs in order to stop reporting a corpus as both in scope and "
            "not covered. See proofs/per_veda_attribution_matrix.json.",
        },
        "qa": {
            "sampled": 97,
            "sample_method": "both",
            "sample_note": "every accepted per-verse deity row was read against its printed "
            "bracket, twice -- once at 67 rows and once at 97 after the recall fix. The "
            "census rows were not sampled: they are a deterministic restatement of edges that "
            "already exist, so a sample of them would only re-measure the graph.",
            "defects_found": 3,
            "defects": [
                "'virat pathyabrhati' (AVS 8.1.8) was emitted as a deity. It is the metre "
                "'pathya brhati' printed without the vowel mark under the r, so neither the "
                "builder's stem list nor an exact lookup against the metre registry caught "
                "it. Fixed by folding combining marks before the registry lookup.",
                "'i-p' (AVS 2.16.2) was emitted as a deity. It is an OCR reading of the pada "
                "address '1-p'. Fixed by admitting i and l into the pada-address class.",
                "'martvyah' (AVS 12.2, verses 21-33) was emitted as a deity for thirteen "
                "verses. Lanman's own note reads the Anukramani's 'martvi' as an ascription of "
                "AUTHORSHIP. Hand-refused and recorded as a lead for a per-verse rsi claim.",
            ],
            "human_reviewed": 0,
            "reviewed_by": "claude-opus-5 acting as Agent 8. This is model adjudication, not "
            "human gold, and campaign section 26 forbids calling it gold. The 83 accepted "
            "deity rows and all 18 rejections are small enough to be re-read by hand and are "
            "printed verbatim beside their source bracket in every row.",
        },
        "known_residuals": {
            "note": "recall limits of the tail grammar, measured rather than left implicit. "
            "None of these is a wrong value; each is a value this pass declined to extract.",
            "semicolon_segmentation": "the tail is split on ';' only, so where Whitney "
            "separates two per-verse statements with a bare period inside one semicolon "
            "segment, only the first is reached. AVS 6.40 verse 3 ('aindri') is the clear "
            "case.",
            "comma_separated_devata_lists": "1 segment refused whole (AVS 6.10, 'agneyi, 2. "
            "vayavya, 3. saurya...'), covering 3 verses, because a comma-delimited list of "
            "three verse-and-deity pairs inside one segment cannot be attributed to verses "
            "without guessing the pairing.",
            "gate_refused_hymns": "17 hymns emit nothing at all because the builder's "
            "stated-verse-count gate refuses their bracket. That is the gate working, not a "
            "defect, and the refusal is typed per mantra in the census rows.",
            "multi_part_ascriptions": "6 hymns (AVS 7.45, 7.54, 7.68, 7.72, 7.76 and 10.5) "
            "carry two or more part-scoped ascriptions in one bracket, covering 66 mantras. "
            "They are genuinely recoverable at MANTRA_RANGE scope -- the ranges are printed "
            "('A. (vss. 1-24)', '1-2. Camtati') -- and they need their own grammar. Named as "
            "an unlock, not attempted here.",
            "kanda_20": "143 hymns / 958 mantras are absent from this index at source and no "
            "amount of parsing reaches them.",
        },
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8", newline=LF
    )
    print("manifest counts:", json.dumps(manifest["counts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
