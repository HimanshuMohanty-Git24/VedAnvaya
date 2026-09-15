#!/usr/bin/env python3
"""Agent 8 -- the negative-result and disproof evidence for data/staging/attribution/.

Run this BEFORE build_attribution_staging.py: the manifest's ``unresolved`` count is read
off ``proofs/sv_saman_attribution_unresolved.jsonl``, which this script writes.

Read-only against Neo4j and against every repo artifact. Writes only into
``data/staging/attribution/proofs/``.

Five proofs, and each one exists because a plausible claim in this domain is wrong:

1. ``yv_katyayana_measurement.json`` -- the Yajurvedic extractability verdict, measured on
   the local snapshot rather than taken on reconnaissance's word.
2. ``sv_saman_scope_decision.json`` + ``sv_gana_page_sample.jsonl`` +
   ``sv_saman_attribution_unresolved.jsonl`` -- the Samavedic sāman-scope decision and the
   33 revision-pinned gāna pages it rests on.
3. ``deity_population_contamination.json`` -- what is standing in the deity and seer
   namespaces and is not a deity or a seer.
4. ``stale_claim_disproofs.json`` -- the two live claims the lead asked to have closed with
   data, plus a third found on the way.
5. ``entity_aggregate_gaps.json`` -- which entity types carry no occurrence aggregate at
   all, so an entity page's "0" is an absent property rather than a measured zero.
"""

from __future__ import annotations

import collections
import json
import os
import pathlib
import re
import sys
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[3]
#: Every JSON artifact in this directory is written with newline=LF. Without it,
#: pathlib on Windows emits CRLF into a directory whose .jsonl siblings are LF, and
#: the next LF-writing edit then rewrites the whole file in the diff for no reason.
LF = chr(10)

PROOFS = REPO / "data" / "staging" / "attribution" / "proofs"
SCRATCH_SAMPLE = None  # set by --sv-sample

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def session():
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


def rows(sess, query: str) -> list[dict[str, Any]]:
    return [record.data() for record in sess.run(query)]


DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


# --------------------------------------------------------------------------- 1. Yajurveda
def yv_katyayana() -> dict[str, Any]:
    """Measure the local Katyayana snapshot. The verdict must rest on counts, not on tone."""
    path = (
        REPO
        / "data"
        / "raw"
        / "wikisource_sa"
        / "2026-09-07"
        / "91203256234de6dbe6fa626c911a9bb674aebe0a6688acd2ba2a5388c0208e28.php"
    )
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    page = payload["query"]["pages"][0]
    revision = page["revisions"][0]
    text = revision["slots"]["main"]["content"]

    sutra_numbers = re.findall(r"॥\s*([०-९\d]+)\s*॥", text)
    values = [int(n.translate(DEVANAGARI_DIGITS)) for n in sutra_numbers]
    return {
        "verdict": "NOT_EXTRACTABLE_AT_SOURCE_EXPLICIT",
        "artifact_id": "WIKISOURCE_SA.YV.VSM.SARVANUKRAMANI",
        "page_title": page["title"],
        "revid": revision["revid"],
        "local_path": str(path.relative_to(REPO)).replace("\\", "/"),
        "recension": "Madhyandina (Sukla Yajurveda) -- the correct recension for "
        "VG:WORK:YV:VSM, so the verdict is not a recension mismatch",
        "characters": len(text),
        "numbered_sutra_terminators": len(sutra_numbers),
        "highest_sutra_number": max(values) if values else None,
        "section_headings": len(re.findall(r"==+\s*.{0,60}?\s*==+", text)),
        "adhyaya_markers": len(re.findall("अध्याय", text)),
        "anuvaka_markers": len(re.findall("अनुवाक", text)),
        "numeric_mantra_coordinates": len(re.findall(r"[०-९]+\s*[।\.]\s*[०-९]+", text)),
        "lingokta_occurrences": len(re.findall("लिङ्गोक्त", text)),
        "anadista_occurrences": len(re.findall("अनादिष्ट", text)),
        "devata_token_occurrences": len(re.findall("देवत", text)),
        "chandas_token_occurrences": len(re.findall("छन्द", text)),
        "why_not_extractable": [
            "ZERO numeric mantra coordinates in 49,708 characters. The Yajurvedic rsi layer "
            "that DID parse -- 2,240 assertions over 1,960 of 1,975 mantras -- parsed because "
            "the Wikisource rsisuci prints explicit numeric ranges ('atrih 8.15-22, 24-30'). "
            "Katyayana prints none. It addresses mantras by pratika (incipit) only, so the "
            "join to our 1,975 keys would require sandhi-splitting a continuous stream and "
            "matching incipits, which is an interpretive act and not a parse.",
            "102 lingokta deferrals. In 102 places the sutra does not name the deity; it says "
            "the deity is 'stated by the characteristic mark' in the mantra. Resolving those "
            "means reading the mantra and judging, which is SEMANTIC_MODEL_EXTRACTION at best "
            "and INTERPRETIVE_CLAIM in practice. No LLM was used on this source and none may "
            "be.",
            "No field delimiters and no headings. The rsi, devata and chandas run together in "
            "sandhi-fused prose with no markers, so even a correctly segmented sutra does not "
            "say which slot a token belongs to.",
        ],
        "constraints_the_source_itself_imposes": [
            "chandas is legitimately ASSERTED-ABSENT for many yajus. The opening sutra reads "
            "'yajusam aniyataksaratvad ekesam chando na vidyate' -- because the yajus have an "
            "unfixed syllable count, for some of them no metre is known. That absence needs a "
            "reason code; it must not be ingested as unknown and must not be filled.",
            "the devata co-domain includes ritual implements as pratimabhuta. The same sutra "
            "lists anas (cart), sakha (branch), ukha (pot), sabhya, upavesa, kapala "
            "(potsherd), idhma (firewood), ulukhala (mortar) among the devatas. A shared "
            "RV/YV devata enum would therefore be a modelling error, and Agent 15's "
            "contamination sweep must not treat a YV ritual implement as contamination.",
            "the tradition keeps its own register of non-assignments, anadista-devatadayah. A "
            "pipeline must reproduce those gaps rather than fill them.",
        ],
        "if_attempted_anyway": "evidence_layer would be INTERPRETIVE_CLAIM, never "
        "SOURCE_EXPLICIT, and mapping_confidence UNVERIFIED -- so every row would stage and "
        "none would import. Nothing was attempted here and nothing is staged.",
        "the_one_lead_that_would_change_this": "reconnaissance names an UNCHECKED lead: "
        "printed Indian editions commonly head each mantra with rsih / devata / chandah / "
        "svarah. Weber 1852 (in.ernet.dli.2015.345056) and the Uvata+Mahidhara printings are "
        "the candidates. If one prints the apparatus per mantra it is the fastest route to YV "
        "devata and chandas -- with the caveat that a printed edition's headings are an "
        "EDITORIAL apparatus and not the Sarvanukramani itself, the two can disagree, and "
        "whichever is used must be recorded as the attributing authority. This agent did not "
        "check it: it is a page-image inspection, not a fetch, and it is out of this agent's "
        "reach.",
    }


# ------------------------------------------------------------------------- 2. Samaveda
def sv_scope(sample_path: pathlib.Path | None) -> tuple[dict[str, Any], list[dict], list[dict]]:
    inventory = [
        json.loads(line)
        for line in (
            REPO / "data" / "source_registry" / "samaveda_gana_page_inventory.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    by_book = collections.Counter(str(row.get("gana_book")) for row in inventory)
    snapshotted = collections.Counter(str(row.get("content_snapshotted")) for row in inventory)

    sample: list[dict] = []
    unresolved: list[dict] = []
    if sample_path and sample_path.exists():
        fetched = json.loads(sample_path.read_text(encoding="utf-8"))
        triad = re.compile(
            r"\(\s*([०-९]{1,4})\s*।?\s*([०-९]{0,2})\s*\)\s*॥\s*([^॥\n]{3,160}?)\s*॥"
        )
        arcika_link = re.compile(r"\[https://sa\.wikisource\.org/s/\w+\s+([०-९]+)\]")
        for record in fetched:
            text = record.get("text") or ""
            triads = [
                {
                    "arcika_number": int(m.group(1).translate(DEVANAGARI_DIGITS)),
                    "gana_variant": (
                        int(m.group(2).translate(DEVANAGARI_DIGITS)) if m.group(2) else None
                    ),
                    "printed_triad": m.group(3).strip(),
                }
                for m in triad.finditer(text)
            ]
            sample.append(
                {
                    "page_title": record["page_title"],
                    "gana_book": record["gana_book"],
                    "page_id": record["page_id"],
                    "revid": record["revid"],
                    "wikitext_sha256": record["sha256"],
                    "wikitext_bytes": record["bytes"],
                    "arcika_link_numbers": [
                        int(n.translate(DEVANAGARI_DIGITS)) for n in arcika_link.findall(text)
                    ],
                    "arseya_brahmana_citation": "आर्षेयब्रा" in text,
                    "triads_detected": triads,
                }
            )
            for entry in triads:
                unresolved.append(
                    {
                        "canonical_key": None,
                        "reason_unresolved": "the triad's subject is a GANA rendering of a "
                        "saman. VG:WORK:SV:KAU addresses the Kauthuma ARCIKA only and its own "
                        "scope statement says the gana collections 'are a PARALLEL AND LARGER "
                        "body which requires its own work_id'. There is no gana Work, no "
                        ":Saman node, and therefore no canonical_key this claim can be "
                        "attached to without widening it onto a verse.",
                        "dimension": "devata|rishi|chandas (one printed triad, three slots)",
                        "printed_triad": entry["printed_triad"],
                        "arcika_number_printed_on_the_page": entry["arcika_number"],
                        "gana_variant": entry["gana_variant"],
                        "page_title": record["page_title"],
                        "revid": record["revid"],
                        "wikitext_sha256": record["sha256"],
                        "source_id": "WIKISOURCE_SA_SV_GANA",
                        "evidence_layer_if_staged": "SOURCE_EXPLICIT at SAMAN granularity; "
                        "INTERPRETIVE_CLAIM if projected onto the arcika verse",
                    }
                )

    return (
        {
            "decision": "SV attribution is asserted at SAMAN (gana-rendering) scope and NO "
            "verse-level Samavedic attribution row is staged by this agent.",
            "what_licenses_a_verse_level_claim": "nothing currently does. Three independent "
            "blockers, all measured, and each one alone is sufficient:",
            "blocker_1_scope_and_it_is_worse_than_a_widening": {
                "finding": "the same arcika number receives MUTUALLY INCONSISTENT triads from "
                "its several gana renderings, so a projection onto the verse is not merely "
                "over-wide -- it is multi-valued and self-contradictory.",
                "verbatim_evidence": "Page सामवेदः/कौथुमीया/संहिता/ग्रामगेयः/प्रपाठकः १७/सफम्(पवस्व) "
                "prints five gana renderings of arcika 578 on one page. Four print a triad and "
                "they disagree: (578.1) 'वासिष्ठम् । वसिष्ठः ककुप् सोमः' -- rsi vasistha, metre "
                "kakup, deity soma; (578.2) 'सफे द्वे । द्वयोर्देवाः ककुप् इन्द्रसोमौ' -- deity "
                "indra-soma; (578.3) prints NO triad at all; (578.4) 'वासिष्ठम् । वसिष्ठः ककुप् "
                "सोमेन्द्रौ' -- deity soma-indra; (578.5) 'सफम् । देवाः ककुप् सोमः' -- rsi devah, "
                "deity soma. One arcika verse, four deity values, three seer values.",
                "read_by": "hand, on the fetched wikitext, revision-pinned in "
                "sv_gana_page_sample.jsonl",
            },
            "blocker_2_identity": "VG:WORK:SV:KAU's scope property states verbatim that the "
            "gana collections 'are a PARALLEL AND LARGER body (roughly 2,639 ganas against "
            "1,875 arcika verses) which requires its own work_id'. No such Work exists, no "
            ":Saman label exists, and the contract requires every row's canonical_key to "
            "resolve to an existing node. A gana-scoped claim has nowhere to land.",
            "blocker_3_join": "no SV mantra carries a running arcika number. Measured: "
            "`MATCH (m:Mantra {veda:'SV'}) RETURN keys(m)` returns no running-number property, "
            "and the spine is ARANYA/CHANDA/UTTARA/MAHANAMNYA with dasati and verse. The gana "
            "page's join key is exactly that running number (e.g. ४६१, ५७८), so even at saman "
            "scope the number cannot be resolved to a canonical key until a running-number "
            "index is built over the 1,844 mantras AND reconciled against the 1,844-vs-1,875 "
            "delta.",
            "capacity_correction_to_reconnaissance": {
                "claim_checked": "reconnaissance describes 726 gana pages carrying the triads "
                "and leaves the per-saman fill rate unverified.",
                "finding": "the triads are not spread across all 726. In a 33-page stratified "
                "sample, every triad found was on a GRAMAGEYA or ARANYAKAGEYA page; the 16 "
                "UHAGANA and UHYAGANA pages sampled carried none. That is structurally "
                "expected -- uha means 'modification', and the uha/uhya ganas are derived "
                "renderings of the gramageya and aranyakageya samans, so they inherit the "
                "ascription rather than restate it. The attributable page population is "
                "therefore about 276 (190 GRAMAGEYA + 86 ARANYAKAGEYA), not 726.",
                "not_claimed": "a per-saman fill rate. Automated triad detection over this "
                "wikitext produces false positives, because the gana notation itself is "
                "delimited with the same danda pair as the triad. Two of the seven arcika "
                "numbers my detector reached were notation, not triads. A fill rate is "
                "therefore NOT reported, and the 33 pinned pages are handed on so the next "
                "pass can measure it without refetching.",
            },
            "inventory": {
                "gana_pages_inventoried": len(inventory),
                "by_gana_book": dict(by_book),
                "content_snapshotted": dict(snapshotted),
                "note": "content_snapshotted is False on all 733 rows: the inventory records "
                "titles and revids, and not one page's bytes had been fetched before this "
                "agent fetched 33 of them.",
            },
            "sample": {
                "pages_fetched": len(sample),
                "stratified_by": "gana_book, seed 20260915, non-redirect pages of >= 2,000 "
                "bytes",
                "eligible_population": 517,
                "pinned": "every page carries its revid and the sha256 of its wikitext",
            },
            "what_would_unblock_it": [
                "a gana Work identity plus a :Saman node type, which is a schema decision and "
                "belongs to the lead, not to a specialist agent;",
                "a running-arcika-number index over the 1,844 SV mantras, reconciled against "
                "the 1,875 the tradition counts;",
                "the Arseya Brahmana as the attributing authority rather than the gana page: "
                "the gana pages cite it directly (e.g. 'आर्षेयब्रा. ४.१२.६' on the Yajnaturam "
                "page), which is the right citation target for a seer claim.",
            ],
        },
        sample,
        unresolved,
    )


# --------------------------------------------------------------- 3. deity contamination
def contamination(sess) -> dict[str, Any]:
    devata = rows(
        sess,
        "MATCH (d:Devata) RETURN d.entity_key AS entity_key, d.label_iast AS label_iast, "
        "d.label_en AS label_en, d.structure AS structure, d.is_classified AS is_classified, "
        "d.curation_note AS curation_note ORDER BY d.structure, d.entity_key",
    )
    dedication_counts = {
        record["entity_key"]: record["dedications"]
        for record in rows(
            sess,
            "MATCH (m:Mantra)-[:HAS_DEVATA]->(d:Devata) RETURN d.entity_key AS entity_key, "
            "count(*) AS dedications",
        )
    }
    by_structure = collections.Counter(record["structure"] for record in devata)

    excluded_structures = {"HUMAN", "PATRON_PRAISE"}
    excluded = [
        {
            "entity_key": record["entity_key"],
            "label_iast": record["label_iast"],
            "label_en": record["label_en"],
            "structure": record["structure"],
            "dedicated_mantras": dedication_counts.get(record["entity_key"], 0),
            "curation_note": record["curation_note"],
            "exclusion_class": (
                "HUMAN_PATRON" if record["structure"] == "HUMAN" else "DANASTUTI_GIFT_PRAISE"
            ),
        }
        for record in devata
        if record["structure"] in excluded_structures
    ]
    abstract = [
        {
            "entity_key": record["entity_key"],
            "label_iast": record["label_iast"],
            "label_en": record["label_en"],
            "dedicated_mantras": dedication_counts.get(record["entity_key"], 0),
            "curation_note": record["curation_note"],
        }
        for record in devata
        if record["structure"] in {"ABSTRACT", "UNSPECIFIED"}
    ]

    rishi_non_seer = rows(
        sess,
        "MATCH (r:Rishi) WHERE r.is_seer = false RETURN r.entity_key AS entity_key, "
        "r.label_iast AS label_iast, r.non_seer_kind AS non_seer_kind, "
        "r.registry_namespace AS registry_namespace ORDER BY r.non_seer_kind, r.entity_key",
    )
    fused_chandas = rows(
        sess,
        "MATCH (p:Passage)-[r:HAS_CHANDAS]->(c:Chandas) WHERE c.label_iast CONTAINS ':' "
        "RETURN p.canonical_key AS passage, p.entity_type AS entity_type, "
        "c.entity_key AS chandas_key, c.label_iast AS value ORDER BY p.canonical_key",
    )

    return {
        "note": "The eligible deity population is :Devata (214 nodes). Exclusions are taken "
        "from the node's own curated `structure` property, not from a name heuristic, so the "
        "list is reproducible and each row carries the curator's reason. Agent 15 needs this.",
        "devata_total": len(devata),
        "devata_by_structure": dict(by_structure),
        "excluded_from_the_eligible_deity_population": {
            "count": len(excluded),
            "human_patrons": sum(1 for e in excluded if e["exclusion_class"] == "HUMAN_PATRON"),
            "danastuti_gift_praise": sum(
                1 for e in excluded if e["exclusion_class"] == "DANASTUTI_GIFT_PRAISE"
            ),
            "dedicated_mantras_affected": sum(e["dedicated_mantras"] for e in excluded),
            "entities": excluded,
        },
        "abstract_labels_flagged_not_excluded": {
            "count": len(abstract),
            "why_not_excluded": "an abstract noun in the devata slot is NOT automatically "
            "contamination. Sraddha, Manyu and Vac are abstractions and are genuine Vedic "
            "deities; abhisapa ('the curse') and adhyetrstuti ('praise of the reciter') are "
            "not. The distinction is a curation judgement and this agent does not make it "
            "silently. The list is handed to Agent 15 with each node's own curation_note.",
            "entities": abstract,
        },
        "contamination_in_the_seer_namespace": {
            "count": len(rishi_non_seer),
            "by_kind": dict(collections.Counter(r["non_seer_kind"] for r in rishi_non_seer)),
            "reading": "113 of the 729 :Rishi nodes are marked is_seer=false by the layer "
            "itself -- 58 deities, 21 abstractions, 13 mythic beings, 11 deity groups, 5 "
            "plants or animals, 3 collectives, 2 objects. They are correctly typed and they "
            "are NOT an unresolved-seer gap. Counting them as one inflates that gap by 113.",
            "entities": rishi_non_seer,
        },
        "contamination_in_the_metre_namespace": {
            "count_chandas_entities": 17,
            "count_edges": len(fused_chandas),
            "finding": "17 :Chandas entities carrying 20 HAS_CHANDAS edges are not metre "
            "names. They are un-split bracket fragments in which a PER-VERSE DEVATA exception "
            "ran into the metre list, e.g. 'mantroktadevatya. anustubham: 1. bhurik tristubh' "
            "and 'raudryau: 2. anustubh'. The builder names this residual in its own docstring "
            "and leaves it deliberately. This agent has now staged the devata halves as "
            "verse-scope ascriptions; the metre halves are still fused and the 17 entities "
            "still stand in the Chandas namespace.",
            "edges": fused_chandas,
        },
    }


# -------------------------------------------------------------------- 4. stale claims
def stale_claims(sess) -> dict[str, Any]:
    av_ascription = rows(
        sess,
        "MATCH (m:Mantra {veda:'AV'})-[r:HAS_DEVATA_ASCRIPTION]->(d:DevataAscription) "
        "RETURN count(DISTINCT m) AS mantras, count(r) AS edges, "
        "count(DISTINCT d) AS distinct_ascriptions",
    )[0]
    av_hymn = rows(
        sess,
        "MATCH (p:Passage {veda:'AV'})-[r:HAS_DEVATA_ASCRIPTION]->() WHERE NOT p:Mantra "
        "RETURN count(DISTINCT p) AS hymns, count(r) AS edges",
    )[0]
    families = rows(
        sess,
        "MATCH (f:RishiFamily) WITH count(*) AS families "
        "MATCH (r:Rishi)-[b:BELONGS_TO_FAMILY]->(:RishiFamily) "
        "RETURN families, count(DISTINCT r) AS resolved_seers, count(b) AS edges",
    )[0]
    rishi_total = rows(sess, "MATCH (r:Rishi) RETURN count(*) AS total")[0]["total"]
    unresolved = rows(
        sess,
        "MATCH (r:Rishi) WHERE NOT (r)-[:BELONGS_TO_FAMILY]->() "
        "RETURN r.is_seer AS is_seer, r.family_assignment_class AS cls, count(*) AS c "
        "ORDER BY c DESC",
    )
    devata_scope = rows(
        sess,
        "MATCH (d:Devata) RETURN d.attribution_scope AS attribution_scope, count(*) AS c",
    )

    return {
        "ATTRIBUTION-003": {
            "stale_claim": "a live API caveat states that the Atharvaveda carries no "
            "Anukramani deity ascription.",
            "verdict": "DISPROVEN",
            "measurement": {
                "query": "MATCH (m:Mantra {veda:'AV'})-[r:HAS_DEVATA_ASCRIPTION]->"
                "(d:DevataAscription) RETURN count(DISTINCT m), count(r), count(DISTINCT d)",
                "mantras_with_an_ascription": av_ascription["mantras"],
                "mantra_level_edges": av_ascription["edges"],
                "distinct_ascription_descriptors": av_ascription["distinct_ascriptions"],
                "hymns_with_an_ascription": av_hymn["hymns"],
                "hymn_level_edges": av_hymn["edges"],
            },
            "provenance_of_the_data": "data/canonical/atharvaveda_saunaka_digital_working_v1/"
            "traditional_metadata.jsonl, 569 HAS_DEVATA rows at WHOLE_PASSAGE scope, built by "
            "scripts/build_atharvaveda_anukramani.py from 1,254 pinned Whitney & Lanman "
            "Page:-namespace revisions. The builder was re-run --dry-run on 2026-09-15 and "
            "reproduced all 3,252 assertions exactly, so the artifact and the graph agree.",
            "the_correction_that_still_belongs_on_the_caveat": "the layer exists but it is "
            "0% source-explicit at verse level before this artifact: all 4,816 mantra-level "
            "edges are knowledge_layer=L2_DETERMINISTIC_DERIVED, "
            "attribution_precision=CONTAINER_INHERITED, scope_origin=SUKTA_WIDE. So the honest "
            "replacement caveat is not 'no ascription' and not '4,160 mantras have a deity' "
            "but 'the Atharvavedic deity layer covers 4,160 of 5,839 mantras, every one of "
            "them a hymn-scope label read down onto its verses'. Removing the caveat without "
            "that sentence would replace an understatement with an overstatement.",
            "note": "product copy is NOT edited here. This is the proof only.",
        },
        "ATTRIBUTION-008": {
            "stale_claim": "RishiFamily is reported as 0 nodes.",
            "verdict": "DISPROVEN",
            "measurement": {
                "rishi_family_nodes": families["families"],
                "belongs_to_family_edges": families["edges"],
                "seers_resolved_to_a_family": families["resolved_seers"],
                "rishi_nodes_total": rishi_total,
                "rishi_nodes_without_a_family_edge": rishi_total - families["resolved_seers"],
            },
            "and_the_gap_figure_needs_correcting_twice": {
                "the_729_figure": "wrong. 729 is the :Rishi node count, not an unresolved "
                "count.",
                "the_427_figure": "arithmetically right but it is not a gap. 427 nodes lack a "
                "BELONGS_TO_FAMILY edge, and the layer already records WHY for every one of "
                "them in r.family_assignment_class.",
                "decomposition": [
                    {
                        "is_seer": record["is_seer"],
                        "family_assignment_class": record["cls"],
                        "count": record["c"],
                    }
                    for record in unresolved
                ],
                "what_is_actually_unresolved": "6. Five nodes are "
                "SOURCE_SPELLING_OUTSIDE_TABLE and one is ETYMON_UNCERTAIN. Everything else "
                "is a typed non-assignment: 113 are not seers at all, 170 have "
                "NO_PATRONYMIC_STATED in the source, 69 are an eponym for whom no patronymic "
                "is printed, 45 are THEONYMIC_DESCENT, 12 a COLLECTIVE_LINEAGE_COMPOUND, 8 "
                "TITULAR_NOT_DESCENT, 3 KINSHIP_NOT_DESCENT, 1 MYTHIC_DESCENT.",
                "how_to_report_it": "three numbers, not one: 427 lack a family edge; 421 lack "
                "one for a stated reason; 6 lack one for an unresolved reason.",
            },
        },
        "DEVATA_ATTRIBUTION_SCOPE_CARRIES_THE_SAME_STALE_CLAIM": {
            "found_while_checking_the_above": True,
            "finding": "all 214 :Devata nodes carry attribution_scope=['RV'] together with an "
            "attribution_scope_note that reads 'The Anukramani attribution layer covers the "
            "Rigveda only. A zero for SV, YV or AV means that corpus has no attribution "
            "layer, NOT that the deity is absent from it.'",
            "measurement": devata_scope,
            "why_it_matters": "that note is now half false. The Atharvaveda DOES have an "
            "Anukramani attribution layer -- 4,160 mantras, 4,816 edges, 324 descriptors -- it "
            "simply lands on :DevataAscription rather than on :Devata, because Whitney's "
            "bracket prints descriptors ('agneyam', 'mantroktadevatyam') rather than deity "
            "names. So the sentence is true of the :Devata NODE and false of the CORPUS, and a "
            "reader cannot tell which is meant. It is ATTRIBUTION-003 wearing different "
            "clothes, and it is served from a node property rather than from a caveat string, "
            "which is why the stale-claim sweep did not catch it.",
            "not_fixed_here": "this is a canonical node property. Only the lead may write it.",
        },
    }


# ------------------------------------------------------- 5. missing entity aggregates
def entity_aggregates(sess) -> dict[str, Any]:
    result: dict[str, Any] = {
        "note": "Campaign brief: no entity page should say 'not yet modelled' merely because "
        "an aggregate was never computed. These are the aggregates that do not exist, "
        "separated from the ones that exist and are wrong. An absent property and a measured "
        "zero are different facts and a UI renders both as 0.",
        "types": {},
    }
    for label, predicate in (
        ("Devata", "HAS_DEVATA"),
        ("Chandas", "HAS_CHANDAS"),
        ("Rishi", "HAS_RISHI"),
        ("DevataAscription", "HAS_DEVATA_ASCRIPTION"),
    ):
        total = rows(sess, f"MATCH (n:{label}) RETURN count(*) AS c")[0]["c"]
        with_prop = rows(
            sess, f"MATCH (n:{label}) RETURN count(n.occurrence_count) AS c"
        )[0]["c"]
        edges = rows(
            sess, f"MATCH ()-[r:{predicate}]->(:{label}) RETURN count(r) AS c"
        )[0]["c"]
        mismatch = rows(
            sess,
            f"MATCH (n:{label}) WHERE n.occurrence_count IS NOT NULL "
            f"OPTIONAL MATCH ()-[r:{predicate}]->(n) WITH n, count(r) AS actual "
            f"RETURN sum(CASE WHEN n.occurrence_count <> actual THEN 1 ELSE 0 END) AS c",
        )[0]["c"]
        entry = {
            "nodes": total,
            "nodes_carrying_occurrence_count": with_prop,
            "nodes_with_no_aggregate_at_all": total - with_prop,
            "incoming_edges_of_the_primary_predicate_all_scopes": edges,
            "nodes_whose_stored_aggregate_disagrees_with_the_ALL_SCOPES_edge_count": mismatch,
        }
        # The all-scopes comparison is the wrong comparison for a layer whose aggregate
        # counts containers. Break it down rather than report a number that reads as a
        # defect when it is a scope convention.
        by_scope = rows(
            sess,
            f"MATCH (n:{label}) WHERE n.occurrence_count IS NOT NULL "
            f"OPTIONAL MATCH (m:Mantra)-[r:{predicate}]->(n) WITH n, count(r) AS mantra_edges "
            f"OPTIONAL MATCH (p:Passage)-[r2:{predicate}]->(n) WHERE NOT p:Mantra "
            f"WITH n, mantra_edges, count(r2) AS container_edges RETURN "
            f"sum(CASE WHEN n.occurrence_count = mantra_edges THEN 1 ELSE 0 END) AS at_mantra, "
            f"sum(CASE WHEN n.occurrence_count = container_edges THEN 1 ELSE 0 END) "
            f"AS at_container",
        )
        if by_scope:
            entry["stored_aggregate_matches_the_MANTRA_scope_edge_count"] = by_scope[0]["at_mantra"]
            entry["stored_aggregate_matches_the_CONTAINER_scope_edge_count"] = by_scope[0][
                "at_container"
            ]
        result["types"][label] = entry

    per_namespace = rows(
        sess,
        "MATCH (r:Rishi) OPTIONAL MATCH (m:Mantra)-[a:HAS_RISHI]->(r) "
        "WITH r, count(a) AS mantra_edges "
        "OPTIONAL MATCH (p:Passage)-[b:HAS_RISHI]->(r) WHERE NOT p:Mantra "
        "WITH r, mantra_edges, count(b) AS container_edges "
        "RETURN r.registry_namespace AS namespace, count(*) AS nodes, "
        "sum(mantra_edges) AS mantra_edges, sum(container_edges) AS container_edges, "
        "sum(r.occurrence_count) AS stored_total, "
        "sum(CASE WHEN r.occurrence_count = mantra_edges THEN 1 ELSE 0 END) AS matches_mantra, "
        "sum(CASE WHEN r.occurrence_count = container_edges THEN 1 ELSE 0 END) "
        "AS matches_container ORDER BY namespace",
    )
    result["rishi_occurrence_count_by_namespace"] = per_namespace
    result["findings"] = [
        "NO :Devata node (0 of 214) and NO :Chandas node (0 of 575) carries an "
        "occurrence_count property at all, against 10,558 HAS_DEVATA and 16,331 HAS_CHANDAS "
        "edges. An entity page reading that property gets null for every deity and every "
        "metre. That is UNKNOWN, not VERIFIED ZERO, and it is the exact failure the brief "
        "names: a page reading as 'not yet modelled' because an aggregate was never computed. "
        "Two aggregates are wanted and neither exists -- dedications (HAS_DEVATA / "
        "HAS_DEVATA_ASCRIPTION) and mentions (MENTIONS_DEVATA) -- and they must not be one "
        "number, because a verse naming Indra is not thereby dedicated to Indra.",
        "all 729 :Rishi nodes DO carry occurrence_count, and the property is written to TWO "
        "DISAGREEING CONVENTIONS across three namespaces. Measured: the 134 Atharvavedic nodes "
        "store a CONTAINER-scope count (542 stored, 542 hymn-level edges, 4,542 mantra-level "
        "edges); the 228 Yajurvedic nodes store a MANTRA-scope count (2,240 stored, 2,240 "
        "mantra-level edges, 0 container edges); the 367 Rigvedic nodes store 0 in total "
        "against 10,565 mantra-level edges. The Rigvedic zero is 'correct' under the "
        "Atharvavedic convention, because the Rigvedic layer has no container-level HAS_RISHI "
        "edge at all -- and that is precisely what makes it dangerous. Every Rigvedic seer "
        "page reads '0 occurrences' over a complete 10,565-edge layer, and no figure in the "
        "row is wrong.",
        "all 324 :DevataAscription nodes store a CONTAINER-scope count. It matches the "
        "hymn-level edge count on all 324 and the mantra-level count on only 21. Internally "
        "consistent rather than wrong, but the property name does not say which scope it "
        "counts, so 'abdevatyam: 2 occurrences' means 2 hymns and 4 mantras and nothing on "
        "the node distinguishes them.",
        "the fix is not 'recompute occurrence_count'. One property cannot carry a "
        "container-scope count for one Veda and a mantra-scope count for another and be read "
        "safely by a single UI. Either the scope travels with the number or there are two "
        "properties. That is a schema decision and it belongs to the lead.",
    ]
    return result


def main() -> int:
    PROOFS.mkdir(parents=True, exist_ok=True)
    sample_path = None
    for index, argument in enumerate(sys.argv):
        if argument == "--sv-sample" and index + 1 < len(sys.argv):
            sample_path = pathlib.Path(sys.argv[index + 1])

    (PROOFS / "yv_katyayana_measurement.json").write_text(
        json.dumps(yv_katyayana(), indent=2, ensure_ascii=False), encoding="utf-8", newline=LF
    )
    print("wrote yv_katyayana_measurement.json")

    decision, sample, unresolved = sv_scope(sample_path)
    (PROOFS / "sv_saman_scope_decision.json").write_text(
        json.dumps(decision, indent=2, ensure_ascii=False), encoding="utf-8", newline=LF
    )
    with (PROOFS / "sv_gana_page_sample.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for record in sample:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    with (PROOFS / "sv_saman_attribution_unresolved.jsonl").open(
        "w", encoding="utf-8", newline="\n"
    ) as fh:
        for record in unresolved:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote sv_* proofs: {len(sample)} pages, {len(unresolved)} unresolved triads")

    driver, sess = session()
    try:
        (PROOFS / "deity_population_contamination.json").write_text(
            json.dumps(contamination(sess), indent=2, ensure_ascii=False), encoding="utf-8", newline=LF
        )
        print("wrote deity_population_contamination.json")
        (PROOFS / "stale_claim_disproofs.json").write_text(
            json.dumps(stale_claims(sess), indent=2, ensure_ascii=False), encoding="utf-8", newline=LF
        )
        print("wrote stale_claim_disproofs.json")
        (PROOFS / "entity_aggregate_gaps.json").write_text(
            json.dumps(entity_aggregates(sess), indent=2, ensure_ascii=False), encoding="utf-8", newline=LF
        )
        print("wrote entity_aggregate_gaps.json")
    finally:
        sess.close()
        driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
