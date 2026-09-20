"""Admit withheld staged recordings into the published catalogue, under the 2026-09-19 policy.

``OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION`` (``docs/decisions/``) replaced the absolute
audible-review publication gate with two tiers. This script is the only thing that writes
the weaker one. It reads the three withheld staging sets, applies the decision's five
admission conditions to every candidate, and rewrites
``data/product/audio_catalog.jsonl`` with the survivors added.

**Every refusal is reported, and the refusals are the interesting output.** A run that
admitted everything would mean the conditions were decorative. The conditions:

1. ``MEDIA_DOES_NOT_RESOLVE`` -- the candidate's URL was not confirmed live by
   :mod:`scripts.audio.probe_staged_addressability` on the day of admission. The staging
   row's own ``availability: AVAILABLE`` is a claim from 2026-09-15 and is not evidence.
2. ``KEY_NOT_IN_CORPUS`` / ``SCOPE_TYPE_WRONG_FOR_NODE`` -- checked against the live graph,
   which is read and never written. A ``scope_type`` of MANTRA over a HYMN node is the
   Section 44 defect and is refused here as well as by the catalogue validator.
3. ``TEXT_ALIGNMENT_NOT_ESTABLISHED`` -- ``text_verified`` is false. The eight Yajurvedic
   residue rows are refused on this clause: their source text field is dittographic or
   truncated and what the recording says is genuinely unknown. The new policy widens what
   may be *published unheard*; it does not widen what may be published *unmapped*.
4. ``REJECTION_STANDS`` -- a row in the set's ``rejected.jsonl`` bars this candidate. The
   match is per candidate, not per key, and that distinction decides the whole Rigvedic
   set: all 150 accepted RV keys appear in ``rejected.jsonl``, five times each, because the
   file records five *declined rival sources* per key. Excluding on the key alone would
   refuse every admissible Rigvedic row while looking rigorous. A rejection that names no
   candidate at all is read as a rejection of the key and bars everything for it.
5. ``ALREADY_PUBLISHED`` / ``DUPLICATE`` -- the key or the audio id is already in the
   catalogue, or two candidates claim the same key or the same media URL.

**The reviewed tier is earned per row, never per population.**
``OWNER_DECISION_AUDIO_SAMPLE_ACCEPTANCE`` accepted 20 hearings as sufficient release QA of
the *pipeline*; it states in terms that it is not evidence about any row it did not cover.
So :func:`reviewed_keys` takes the effective verdict per row from the append-only decision
log and requires the played ``media_url`` to be the URL the published record will play --
because a verdict about a recording is not a verdict about a different recording of the
same passage, which is exactly how an audit ends up measuring the wrong artifact.

Usage::

    python scripts/audio/probe_staged_addressability.py      # first, and on the same day
    python scripts/audio/admit_source_mapped_rows.py --dry-run
    python scripts/audio/admit_source_mapped_rows.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Final

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from vedagraph.product.audio.catalog import (  # noqa: E402
    CATALOG_RELATIVE_PATH,
    AudioCatalog,
    write_catalog,
)
from vedagraph.product.audio.models import (  # noqa: E402
    SCOPE_TO_ENTITY_TYPES,
    VEDA_RECENSIONS,
    AudioRecord,
    AudioScope,
    Availability,
    MappingConfidence,
    PlaybackMode,
    PublicationTier,
)

STAGED_SETS: Final = ("audio_rv", "audio_av", "audio_yv")

#: The publisher behind each staging source id. Held here rather than guessed from the URL
#: because ``source_name`` is what a reader is shown, and two of the three staging sets
#: leave the field out of their payload entirely.
SOURCE_NAMES: Final[dict[str, str]] = {
    "VEDAWEB.RV.SAK.KIRCHHEINER.2026-09-15": (
        "VedaWeb (Kirchheiner collection, National Library of Denmark)"
    ),
    "HF.VEDAVANI.AVS.SEGMENTED.2026-09-15": "Vedavani (Hugging Face)",
    "VEDSEARCH.AV.SAU.RECITATION.2026-09-12": "VedSearch",
    "VEDSEARCH_YV_HARVEST_2026-09-12": "VedSearch",
}

#: Staging ``mapping_confidence`` values that are not members of :class:`MappingConfidence`.
#:
#: ``PROBABLE`` is the Atharvavedic re-mapping's own word for "the source's coordinate had
#: to be transformed before it agreed, and the transformed text matches". That is precisely
#: :attr:`MappingConfidence.HIGH` -- the source states the passage and independent structure
#: confirms it -- and deliberately not ``EXACT``, which in this catalogue asserts the source
#: placed the file at this passage's own granularity with no transform in between.
STAGED_CONFIDENCE: Final[dict[str, MappingConfidence]] = {
    "EXACT": MappingConfidence.EXACT,
    "PROBABLE": MappingConfidence.HIGH,
}

#: Payload keys that are staging measurements rather than catalogue fields. They are not
#: dropped: :func:`_retained_evidence` folds them into ``notes`` so the provenance the
#: decision requires travels onto the published row.
NON_RECORD_KEYS: Final = frozenset(
    {
        "audio_decoded_as_mp3",
        "audio_fetched_bytes",
        "bytes_per_text_letter",
        "patha_type",
        "text_match_score",
        "text_similarity",
        "unverified_detail",
        "unverified_reason_code",
        "what_would_settle_it",
    }
)

BOLT_URI: Final = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
BOLT_AUTH: Final = (
    os.environ.get("NEO4J_USER", "neo4j"),
    os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
)


@dataclass
class Outcome:
    canonical_key: str
    audio_id: str
    staged_set: str
    admitted: bool
    tier: str | None
    reason: str
    detail: str


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def resolving_urls(probe_path: Path) -> dict[tuple[str, str], str]:
    """``(canonical_key, media_url) -> detail`` for every probe row that resolved."""
    rows = _jsonl(probe_path)
    if not rows:
        raise SystemExit(
            f"No addressability probe at {probe_path}. Run "
            f"scripts/audio/probe_staged_addressability.py first: the policy admits a row "
            f"only when its media was measured to resolve, and a staging row's own "
            f"availability field is not that measurement."
        )
    return {
        (row["canonical_key"], row["media_url"]): row["detail"]
        for row in rows
        if row.get("resolves") and row.get("checksum_matches") is not False
    }


def rejection_index(staged_set: str) -> tuple[set[tuple[str, str]], set[str]]:
    """``({(key, candidate identity)}, {key rejected outright})`` for one staging set.

    Two collections because the three ``rejected.jsonl`` files disagree about what a
    rejection is *of*. The Rigvedic file names a declined rival source per row and the
    Atharvavedic one names a list of them, so those rejections bar one candidate; the
    Yajurvedic file names a candidate URL. A row naming no candidate identity at all is a
    statement about the passage and bars every candidate for it.
    """
    per_candidate: set[tuple[str, str]] = set()
    whole_key: set[str] = set()
    for row in _jsonl(REPO_ROOT / "data" / "staging" / staged_set / "rejected.jsonl"):
        key = row["canonical_key"]
        identities = {
            value
            for value in [
                row.get("candidate_source_id"),
                row.get("source_id"),
                row.get("candidate_url"),
            ]
            if value
        }
        identities.update(value for value in row.get("candidate_source_ids") or [] if value)
        if identities:
            per_candidate.update((key, str(value)) for value in identities)
        else:
            whole_key.add(key)
    return per_candidate, whole_key


def reviewed_keys(decisions_path: Path) -> dict[tuple[str, str], str]:
    """``(canonical_key, media_url) -> evidence phrase`` for effectively verified rows.

    Effective means the *last* line per ``review_id``: the log is append-only and a
    correction supersedes rather than edits, so reading anything but the last line reports
    a verdict the reviewer has since replaced.
    """
    effective: dict[str, dict[str, Any]] = {}
    for row in _jsonl(decisions_path):
        effective[row["review_id"]] = row
    verified: dict[tuple[str, str], str] = {}
    for row in effective.values():
        if row.get("verdict") != "AUDIBLY_VERIFIED":
            continue
        if not row.get("recording_opened") or not row.get("reviewer"):
            continue
        verified[(row["canonical_key"], row["media_url"])] = (
            f"{decisions_path.as_posix().split('D:/VedaGraph/')[-1]}: reviewer "
            f"{row['reviewer']} played {row['media_url']} on {row['reviewed_at']} and "
            f"recorded AUDIBLY_VERIFIED "
            f"(OWNER_DECISION_AUDIO_SAMPLE_ACCEPTANCE, OWNER_DECISIONS.md section 43)."
        )
    return verified


def graph_nodes(keys: list[str]) -> dict[str, tuple[str, str]]:
    """``canonical_key -> (veda, entity_type)`` read from the live graph. Read-only."""
    from neo4j import GraphDatabase

    found: dict[str, tuple[str, str]] = {}
    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    try:
        with driver.session() as session:
            for start in range(0, len(keys), 1000):
                rows = session.run(
                    "MATCH (p:Passage) WHERE p.canonical_key IN $keys "
                    "RETURN p.canonical_key AS key, p.veda AS veda, "
                    "p.entity_type AS entity_type",
                    keys=keys[start : start + 1000],
                )
                for row in rows:
                    found[str(row["key"])] = (str(row["veda"]), str(row["entity_type"]))
    finally:
        driver.close()
    return found


def _retained_evidence(row: dict[str, Any]) -> str:
    """The staging measurements that have no catalogue field, as one readable clause."""
    payload = row["payload"]
    parts: list[str] = []
    for key in sorted(NON_RECORD_KEYS):
        value = payload.get(key)
        if value not in (None, ""):
            parts.append(f"{key}={value}")
    for key, value in sorted((row.get("measurements") or {}).items()):
        if value not in (None, ""):
            parts.append(f"{key}={value}")
    if row.get("quality_class"):
        parts.append(f"quality_class={row['quality_class']}")
    if row.get("evidence_layer"):
        parts.append(f"evidence_layer={row['evidence_layer']}")
    return "; ".join(parts)


#: Reader-facing name and edition tag per Veda, read off the 16,834 incumbent titles.
VEDA_TITLE_PREFIX: Final[dict[str, str]] = {
    "RV": "Rigveda RV",
    "AV": "Atharvaveda AVS",
    "YV": "Yajurveda VSM",
    "SV": "Samaveda KAU",
}


def _title(row: dict[str, Any], veda: str) -> str:
    """The source's own title where it states one, otherwise the incumbent shape.

    Only the Yajurvedic staging set omits a title. It is derived from the *canonical key*
    and not from ``source_reference``: the source's Yajurvedic coordinate is
    ``chapter.sukt.shlok`` with a constant ``sukt`` of 1, so "1.1.16" as a title would read
    to any reader as a three-level citation of a text that has two levels. The key's own
    ``A01:V016`` gives VSM 1.16, which is what the other 1,752 Yajurvedic titles say.
    """
    stated = row["payload"].get("title")
    if stated:
        return str(stated)
    segments = row["canonical_key"].split(":")[3:]
    numbers = ".".join(segment.lstrip("MSVAK").lstrip("0") or "0" for segment in segments)
    return f"{VEDA_TITLE_PREFIX.get(veda, veda)} {numbers} - recitation of this verse"


def build_record(
    row: dict[str, Any],
    *,
    veda: str,
    tier: PublicationTier,
    evidence: str | None,
    admitted_on: str,
    probe_detail: str,
) -> AudioRecord:
    payload = row["payload"]
    media_url = payload.get("media_url")
    proxied = "vedsearch.org" in (media_url or "")
    notes = str(payload.get("notes") or "").strip()
    retained = _retained_evidence(row)
    admission = (
        f"Admitted {admitted_on} under OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION as "
        f"{tier.value}. Media re-fetched that day and confirmed to resolve: {probe_detail}."
    )
    if retained:
        admission += f" Staging evidence retained: {retained}."
    return AudioRecord(
        audio_id=str(payload["audio_id"]),
        veda=veda,
        recension=str(payload["recension"]),
        scope_type=AudioScope(payload["scope_type"]),
        scope_key=row["canonical_key"],
        audio_type=payload["audio_type"],
        title=_title(row, veda),
        performer=payload.get("performer"),
        tradition=payload.get("tradition"),
        location=payload.get("location"),
        source_name=SOURCE_NAMES.get(row["source_id"]) or str(payload.get("source_name") or ""),
        source_page=str(payload["source_page"]),
        media_url=media_url,
        embed_url=payload.get("embed_url"),
        local_cache_path=payload.get("local_cache_path"),
        duration_seconds=payload.get("duration_seconds"),
        start_seconds=payload.get("start_seconds"),
        end_seconds=payload.get("end_seconds"),
        mapping_method=str(row["mapping_method"]),
        mapping_confidence=STAGED_CONFIDENCE[str(row["mapping_confidence"])],
        # Measured by the probe on this run, not copied from the staging row's own claim.
        availability=Availability.AVAILABLE,
        # VedSearch serves audio as base64 inside JSON, which no browser can play, so those
        # rows must go through this product's own streaming route. Everything else is a
        # real media file at a real URL and is played directly -- including the 46 Vedavani
        # WAVs, whose staging payload says PROXIED_STREAM and is wrong about it: the proxy
        # resolves through the VedSearch client and would fail on a Hugging Face path.
        playback_mode=PlaybackMode.PROXIED_STREAM if proxied else PlaybackMode.REMOTE_DIRECT,
        licence=payload.get("licence"),
        local_copy_permitted=bool(payload.get("local_copy_permitted", False)),
        attribution=payload.get("attribution"),
        source_reference=payload.get("source_reference"),
        text_verified=bool(payload.get("text_verified", False)),
        last_verified=admitted_on,
        checksum=payload.get("checksum"),
        notes=f"{notes} {admission}".strip(),
        publication_tier=tier,
        audible_review_evidence=evidence,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Admit staged audio under the two-tier policy.")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument(
        "--probe",
        type=Path,
        default=REPO_ROOT / "docs" / "reports" / "audio" / "staged_addressability_probe.jsonl",
    )
    parser.add_argument(
        "--decisions",
        type=Path,
        default=REPO_ROOT / "data" / "manual" / "audio_review" / "sample_decisions.jsonl",
    )
    parser.add_argument("--offline", action="store_true", help="skip the live graph check")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "docs" / "reports" / "audio" / "admission_report.json",
    )
    args = parser.parse_args()

    admitted_on = date.today().isoformat()
    catalog_path = args.data_dir / CATALOG_RELATIVE_PATH
    existing = AudioCatalog.load(catalog_path)
    existing_keys = {r.scope_key for r in existing if r.scope_key}
    existing_ids = {r.audio_id for r in existing}
    existing_urls = {r.media_url for r in existing if r.media_url}

    resolving = resolving_urls(args.probe)
    verified = reviewed_keys(args.decisions)

    candidates: list[tuple[str, dict[str, Any]]] = []
    for staged_set in STAGED_SETS:
        for row in _jsonl(REPO_ROOT / "data" / "staging" / staged_set / "rows.jsonl"):
            candidates.append((staged_set, row))

    nodes: dict[str, tuple[str, str]] = {}
    if not args.offline:
        nodes = graph_nodes([row["canonical_key"] for _, row in candidates])

    outcomes: list[Outcome] = []
    admitted: list[AudioRecord] = []
    seen_keys: set[str] = set()
    seen_urls: set[str] = set()
    rejections = {name: rejection_index(name) for name in STAGED_SETS}

    for staged_set, row in candidates:
        key = row["canonical_key"]
        payload = row["payload"]
        audio_id = str(payload.get("audio_id", ""))
        media_url = str(payload.get("media_url") or "")
        veda = str(payload.get("veda") or key.split(":")[1])

        def refuse(
            reason: str,
            detail: str,
            # Bound at definition rather than closed over: this function is redefined once
            # per candidate and a late-binding closure would stamp every refusal with the
            # last candidate's identity.
            _key: str = key,
            _audio_id: str = audio_id,
            _staged_set: str = staged_set,
        ) -> None:
            outcomes.append(Outcome(_key, _audio_id, _staged_set, False, None, reason, detail))

        per_candidate, whole_key = rejections[staged_set]
        identities = {row.get("source_id"), media_url}
        if key in whole_key:
            refuse("REJECTION_STANDS", "a rejected.jsonl row names this key and no candidate")
            continue
        barred = sorted(str(i) for i in identities if i and (key, str(i)) in per_candidate)
        if barred:
            refuse("REJECTION_STANDS", f"rejected.jsonl bars candidate {barred[0]}")
            continue

        if not payload.get("text_verified"):
            refuse(
                "TEXT_ALIGNMENT_NOT_ESTABLISHED",
                str(payload.get("unverified_reason_code") or "text_verified is false"),
            )
            continue
        if str(row.get("mapping_confidence")) not in STAGED_CONFIDENCE:
            refuse("CONFIDENCE_NOT_PUBLISHABLE", f"staged as {row.get('mapping_confidence')}")
            continue

        detail = resolving.get((key, media_url))
        if detail is None:
            refuse("MEDIA_DOES_NOT_RESOLVE", "not confirmed live by the addressability probe")
            continue

        if key in existing_keys or audio_id in existing_ids:
            refuse("ALREADY_PUBLISHED", "the catalogue already holds this key or id")
            continue
        if key in seen_keys:
            refuse("DUPLICATE_KEY_IN_THIS_RUN", "another candidate already claimed this key")
            continue
        if media_url in seen_urls or media_url in existing_urls:
            refuse("DUPLICATE_MEDIA_URL", "another record already plays this URL")
            continue

        if nodes:
            node = nodes.get(key)
            if node is None:
                refuse("KEY_NOT_IN_CORPUS", "no Passage node carries this canonical_key")
                continue
            node_veda, entity_type = node
            if node_veda != veda:
                refuse("VEDA_DISAGREES_WITH_NODE", f"node is {node_veda}, row claims {veda}")
                continue
            allowed = SCOPE_TO_ENTITY_TYPES.get(AudioScope(payload["scope_type"]), frozenset())
            if entity_type not in allowed:
                refuse(
                    "SCOPE_TYPE_WRONG_FOR_NODE",
                    f"scope {payload['scope_type']} over a {entity_type} node",
                )
                continue

        evidence = verified.get((key, media_url))
        tier = (
            PublicationTier.RELEASED_VERIFIED
            if evidence
            else PublicationTier.SOURCE_MAPPED_UNREVIEWED
        )
        try:
            record = build_record(
                row,
                veda=veda,
                tier=tier,
                evidence=evidence,
                admitted_on=admitted_on,
                probe_detail=detail,
            )
        except Exception as error:
            refuse("MODEL_REFUSED_THE_RECORD", f"{type(error).__name__}: {error}")
            continue

        admitted.append(record)
        seen_keys.add(key)
        seen_urls.add(media_url)
        outcomes.append(Outcome(key, audio_id, staged_set, True, tier.value, "ADMITTED", detail))

    merged = list(existing.records) + admitted
    report: dict[str, Any] = {
        "artifact": "AUDIO_TWO_TIER_ADMISSION_REPORT",
        "decision": "OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION",
        "admitted_on": admitted_on,
        "candidates_evaluated": len(candidates),
        "admitted": len(admitted),
        "refused": len(candidates) - len(admitted),
        "admitted_by_tier": dict(Counter(o.tier for o in outcomes if o.admitted and o.tier)),
        "refused_by_reason": dict(
            sorted(Counter(o.reason for o in outcomes if not o.admitted).items())
        ),
        "refused_by_set_and_reason": {},
        "catalogue_before": len(existing),
        "catalogue_after": len(merged),
        "per_veda_by_tier": {},
        "graph_checked": bool(nodes),
    }
    by_set: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for outcome in outcomes:
        if not outcome.admitted:
            by_set[outcome.staged_set][outcome.reason] += 1
    report["refused_by_set_and_reason"] = {k: dict(sorted(v.items())) for k, v in by_set.items()}

    tiers: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for record in merged:
        tiers[record.veda][record.publication_tier.value] += 1
    report["per_veda_by_tier"] = {
        veda: {tier.value: tiers[veda][tier.value] for tier in PublicationTier}
        for veda in sorted(set(VEDA_RECENSIONS) | set(tiers))
    }

    if not args.dry_run:
        write_catalog(catalog_path, merged)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
        outcome_path = args.report.with_name("admission_outcomes.jsonl")
        with outcome_path.open("w", encoding="utf-8", newline="\n") as handle:
            for outcome in sorted(outcomes, key=lambda o: (o.staged_set, o.canonical_key)):
                handle.write(json.dumps(vars(outcome), ensure_ascii=False, sort_keys=True) + "\n")
        print(f"catalogue: {catalog_path}\nreport: {args.report}\noutcomes: {outcome_path}")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
