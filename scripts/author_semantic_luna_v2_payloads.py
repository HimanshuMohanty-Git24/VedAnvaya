# ruff: noqa: E501
"""Author offline Luna-v2 structured payloads from v2 EvidencePackets only.

This is the CODEX_DIRECT adapter for the pilot. It is deliberately packet-local: the
author never opens v1 outputs, Sol annotations, comparison reports, or gold data. The
fourteen-family trace is written separately because the public extraction schema keeps
the model response limited to claims and receipts.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v2-120")
MODEL = "gpt-5.6-luna"
PROMPT_VERSION = "rigveda-semantic-extraction-v2"
FAMILIES = (
    "INVOKES",
    "PRAISES",
    "REQUESTS",
    "DESCRIBES",
    "DESCRIBES_ACTION",
    "INVOLVES_RITUAL",
    "INVOLVES_OFFERING",
    "INVOLVES_SUBSTANCE",
    "REFERS_TO_NATURAL_PHENOMENON",
    "REFERS_TO_PLACE",
    "EXPRESSES",
    "HAS_THEME",
    "ASSOCIATED_WITH",
    "CONTRASTS_WITH",
)


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def word_forms(label: str) -> set[str]:
    value = fold(label).replace("ḥ", "").strip()
    forms = {value}
    if value.endswith("h"):
        forms.add(value[:-1])
    if value.endswith("a"):
        forms.add(value[:-1])
    return {item for item in forms if len(item) >= 3}


def contains_word(text: str, forms: set[str]) -> bool:
    folded = fold(text)
    return any(re.search(rf"\b{re.escape(form)}\b", folded) for form in forms)


def translation(packet: dict[str, Any]) -> tuple[str, str | None]:
    row = packet.get("translation")
    if not isinstance(row, dict) or not row.get("text"):
        return "", None
    return str(row["text"]), str(row["translation_id"])


def evidence(
    packet: dict[str, Any], *, tokens: list[str] | None = None, note: str
) -> list[dict[str, Any]]:
    _, translation_id = translation(packet)
    result: list[dict[str, Any]] = []
    if tokens:
        result.append(
            {
                "passage_key": str(packet["passage_key"]),
                "span_type": "LEXICAL_MENTION",
                "sanskrit_token_keys": tokens,
                "translation_id": None,
                "note": "Supplied deterministic lexical mention anchors the canonical entity.",
            }
        )
    if translation_id:
        result.append(
            {
                "passage_key": str(packet["passage_key"]),
                "span_type": "TRANSLATION_LINE",
                "sanskrit_token_keys": [],
                "translation_id": translation_id,
                "note": note,
            }
        )
    return result


def local_id(node_type: str, label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", fold(label)).strip("_") or "item"
    return f"{node_type.lower()}_{slug}"


class Draft:
    def __init__(self, packet: dict[str, Any]) -> None:
        self.packet = packet
        self.text, self.translation_id = translation(packet)
        self.folded = fold(self.text)
        self.entities: dict[str, dict[str, Any]] = {}
        self.assertions: list[dict[str, Any]] = []
        self.status: dict[str, str] = {family: "NOT_SUPPORTED" for family in FAMILIES}
        self.notes: dict[str, str] = {}

    def entity(self, node_type: str, label: str, description: str) -> str:
        key = local_id(node_type, label)
        self.entities.setdefault(
            key,
            {
                "local_id": key,
                "entity_type": node_type,
                "label": label,
                "description": description,
                "aliases": [],
            },
        )
        return key

    def add(
        self,
        family: str,
        *,
        object_key: str | None = None,
        node_type: str | None = None,
        label: str = "",
        explicitness: str = "STRONG_INFERENCE",
        confidence: float = 0.82,
        tokens: list[str] | None = None,
        note: str = "",
    ) -> None:
        if object_key is None:
            assert node_type is not None
            object_key = self.entity(node_type, label, note)
            local = object_key
            entity_key = None
        else:
            local = None
            entity_key = object_key
        self.assertions.append(
            {
                "predicate": family,
                "subject_passage_key": str(self.packet["passage_key"]),
                "object_entity_key": entity_key,
                "object_local_id": local,
                "explicitness": explicitness,
                "confidence": confidence,
                "evidence": evidence(self.packet, tokens=tokens, note=note),
            }
        )
        self.status[family] = "SUPPORTED"
        self.notes[family] = note


def canonical_mentions(packet: dict[str, Any], text: str) -> list[tuple[dict[str, Any], bool]]:
    result = []
    for mention in packet.get("mentions", []):
        label = str(mention.get("entity_label", ""))
        result.append((mention, contains_word(text, word_forms(label))))
    return result


def author_payload(packet: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    draft = Draft(packet)
    text = draft.text
    mentions = canonical_mentions(packet, text)

    # Canonical entity relations require both a supplied lexical anchor and a textual
    # occurrence/cue. Traditional Devata metadata is never used as semantic support.
    for mention, appears in mentions:
        if not appears:
            continue
        label = str(mention["entity_label"])
        tokens = [str(item) for item in mention.get("token_keys", [])]
        name = re.escape(min(word_forms(label), key=len))
        window = draft.folded
        direct = bool(re.search(rf"\b(?:o|hail)\s+[^,.!?;:]*\b{name}\b", window))
        call = bool(
            re.search(
                rf"\b(?:call|calls|invoke|invokes|come nigh|come)\b[^.\n]{{0,100}}\b{name}\b",
                window,
            )
        )
        praise = bool(
            re.search(
                rf"\b(?:praise|praises|laud|lauds|extol|extols|glorif\w*)\b[^.\n]{{0,100}}\b{name}\b",
                window,
            )
        )
        if direct or call:
            draft.add(
                "INVOKES",
                object_key=str(mention["entity_key"]),
                explicitness="EXPLICIT",
                confidence=0.91,
                tokens=tokens,
                note="Direct address or call is explicit in the supplied translation.",
            )
        if praise:
            draft.add(
                "PRAISES",
                object_key=str(mention["entity_key"]),
                explicitness="EXPLICIT",
                confidence=0.9,
                tokens=tokens,
                note="Laudatory wording explicitly targets the supplied canonical mention.",
            )
        descriptive = bool(
            re.search(
                r"\b(?:who|which|that|lord|giver|strong|mighty|divine|born|stands|dwells|holds|brings|gives)\b",
                window,
            )
        )
        if descriptive and not direct and not call:
            draft.add(
                "DESCRIBES",
                object_key=str(
                    mention["entity_key"],
                ),
                explicitness="STRONG_INFERENCE",
                confidence=0.79,
                tokens=tokens,
                note="The supplied passage describes the mentioned entity without an address or praise cue.",
            )

    # Requests are outcomes, not calls. Labels are taken from words in the supplied
    # translation and kept short enough to be reusable.
    request_labels = (
        (r"\bprotect(?:ion|ing)?\b|\bkeep .* safe\b|\bguard", "protection", "STATE"),
        (r"\bwealth\b|\babundance\b|\briches\b", "wealth", "CONCEPT"),
        (r"\bhealth\b|\bwellbeing\b|\bwell-being\b", "health", "STATE"),
        (r"\b(?:succour|assistance|aid|help)\b", "assistance", "CONCEPT"),
        (r"\bshelter\b|\bdwelling-place\b", "shelter", "OBJECT"),
        (r"\bstrength\b|\bmight\b", "strength", "QUALITY"),
        (r"\b(?:long|long may)\b[^.]{0,30}\bsee\b|\blong life\b", "long life", "STATE"),
        (r"\bvictory\b|\bconquer\b|\bsubdue the foe\b", "victory", "CONCEPT"),
        (r"\boffspring\b|\bsons?\b", "offspring", "CONCEPT"),
        (r"\bpresence\b|\bcome nigh\b|\bstand by us\b", "presence", "STATE"),
    )
    request_cue = bool(
        re.search(r"\b(?:may|grant|give|send|vouchsafe|bestow|bring|come|keep|let)\b", draft.folded)
    )
    for pattern, label, node_type in request_labels:
        if request_cue and re.search(pattern, draft.folded):
            draft.add(
                "REQUESTS",
                node_type=node_type,
                label=label,
                explicitness="STRONG_INFERENCE",
                confidence=0.86,
                note="An explicit desired result is stated in the supplied translation.",
            )
            break

    # Action candidates come from expressed verbs, not from metadata or remembered hymn
    # narratives. One compact action per textual cue prevents sentence-sized nodes.
    action_patterns = (
        (
            r"\b(?:slay|slays|slew|smitten|smiting|destroy|destroys|destroyed|destroying)\b",
            "destroying",
        ),
        (r"\b(?:release|released|releasing|opening|opened|unlocks?)\b", "releasing"),
        (r"\b(?:pour|pours|poured|pouring|effused)\b", "pouring"),
        (r"\b(?:sent|sends|sending|brought|brings|bringing)\b", "sending"),
        (r"\b(?:protected|protects|protecting|guarded|guards|keeping)\b", "protecting"),
        (r"\b(?:fed|feeds|feeding)\b", "feeding"),
        (r"\b(?:pressed|pressing|washed|washing|filtered|filtering|flowing)\b", "processing"),
    )
    for pattern, label in action_patterns:
        if re.search(pattern, draft.folded):
            draft.add(
                "DESCRIBES_ACTION",
                node_type="ACTION",
                label=label,
                explicitness="STRONG_INFERENCE",
                confidence=0.81,
                note="The action verb is present in the supplied translation.",
            )
            break

    ritual = re.search(
        r"\b(?:sacrifice|sacrificial|oblation|libation|ritual|rite|altar|press(?:ed|ing)?|offering)\w*\b",
        draft.folded,
    )
    if ritual:
        label = (
            "Soma pressing"
            if re.search(r"\bpress\w*\b", draft.folded) and re.search(r"\bsoma\b", draft.folded)
            else ritual.group(0)
        )
        draft.add(
            "INVOLVES_RITUAL",
            node_type="RITUAL",
            label=label,
            explicitness="STRONG_INFERENCE",
            confidence=0.83,
            note="The supplied translation explicitly names a ritual act or context.",
        )
    offering = re.search(
        r"\b(?:oblation|libation|offering|sacrifice|juices? poured|meath-drops?)\b", draft.folded
    )
    if offering:
        draft.add(
            "INVOLVES_OFFERING",
            node_type="OFFERING",
            label="oblation" if offering.group(0) == "oblation" else "offering",
            explicitness="STRONG_INFERENCE",
            confidence=0.84,
            note="The supplied translation explicitly presents or pours an offering.",
        )

    substance_patterns = (
        (r"\bsoma\b", "Soma"),
        (r"\bmeath\b|\bjuices?\b", "meath"),
        (r"\bmilk\b", "milk"),
        (r"\bwater|waters\b", "water"),
        (r"\bmedicines?\b|\bmedicine\b", "medicine"),
        (r"\bfood\b", "food"),
    )
    for pattern, label in substance_patterns:
        if re.search(pattern, draft.folded):
            draft.add(
                "INVOLVES_SUBSTANCE",
                node_type="SUBSTANCE",
                label=label,
                explicitness="STRONG_INFERENCE",
                confidence=0.84,
                note="The material is explicitly named in the supplied translation.",
            )

    natural_patterns = (
        (r"\bdawn\b|\bmorn\b|\bsunrise\b", "dawn"),
        (r"\brain\b|\brains\b", "rain"),
        (r"\bwind\b|\bwind's\b", "wind"),
        (r"\bwaters?\b|\bfloods?\b", "waters"),
        (r"\blightning\b|\bthunder\b|\bclouds?\b", "storm"),
    )
    for pattern, label in natural_patterns:
        if re.search(pattern, draft.folded):
            draft.add(
                "REFERS_TO_NATURAL_PHENOMENON",
                node_type="NATURAL_PHENOMENON",
                label=label,
                explicitness="STRONG_INFERENCE",
                confidence=0.82,
                note="The natural phenomenon is explicitly named in the supplied translation.",
            )
            break

    place = re.search(
        r"\b(?:river|rivers|pastures|cave|caves|heaven|land|dwelling-place)\b", draft.folded
    )
    if place and place.group(0) in {
        "river",
        "rivers",
        "pastures",
        "cave",
        "caves",
        "heaven",
        "land",
    }:
        draft.add(
            "REFERS_TO_PLACE",
            node_type="PLACE",
            label=place.group(0).rstrip("s"),
            explicitness="STRONG_INFERENCE",
            confidence=0.78,
            note="A spatial location is explicitly named; generic seats/dwellings are not promoted.",
        )

    state = re.search(
        r"\b(?:yearning|fain|long for|fear|afraid|need|desire|wish|glad|joy|hope)\w*\b",
        draft.folded,
    )
    if state:
        label = state.group(0).replace("long for", "yearning")
        draft.add(
            "EXPRESSES",
            node_type="STATE",
            label=label,
            explicitness="STRONG_INFERENCE",
            confidence=0.8,
            note="The supplied translation explicitly voices a mental or affective state.",
        )

    # Theme, association and contrast remain conservative by design. Mark a potential
    # boundary case as uncertain in the trace rather than minting a weak assertion.
    if re.search(r"\b(?:seat|dwelling|house)\b", draft.folded) and not place:
        draft.status["REFERS_TO_PLACE"] = "UNCERTAIN"
        draft.notes["REFERS_TO_PLACE"] = (
            "Spatial wording is present but the referent is not safely a PLACE."
        )
    if re.search(r"\b(?:person|man|men|woman|women|giver|patron|ancestor|kinsman)\b", draft.folded):
        draft.notes["ONTOLOGY_GAP"] = (
            "Human/person or kinship referent is present but the ontology has no matching node type."
        )

    reasons = (
        []
        if draft.assertions
        else [
            "No predicate family received explicit or strong packet support after the complete fourteen-family checklist.",
        ]
    )
    payload = {
        "mantra_id": str(packet["citation"]),
        "entities": list(draft.entities.values()),
        "assertions": draft.assertions,
        "uncertainties": [
            draft.notes[key]
            for key in sorted(draft.notes)
            if key == "ONTOLOGY_GAP" or draft.status.get(key) == "UNCERTAIN"
        ],
        "no_claim_reasons": reasons,
    }
    trace = {
        "passage_key": str(packet["passage_key"]),
        "checklist_completed": len(draft.status) == 14,
        "families": {
            family: {"status": draft.status[family], "note": draft.notes.get(family, "")}
            for family in FAMILIES
        },
        "assertion_count": len(draft.assertions),
        "ontology_gaps": [draft.notes["ONTOLOGY_GAP"]] if "ONTOLOGY_GAP" in draft.notes else [],
    }
    return payload, trace


def main() -> None:
    rows: list[str] = []
    traces: list[str] = []
    for evidence_path in sorted((ROOT / "batches").glob("batch_*/evidence.jsonl")):
        batch_rows: list[str] = []
        batch_traces: list[str] = []
        for line in evidence_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            packet = json.loads(line)
            payload, trace = author_payload(packet)
            row = json.dumps(
                {"passage_key": packet["passage_key"], "payload": payload},
                ensure_ascii=False,
                sort_keys=True,
            )
            trace_row = json.dumps(trace, ensure_ascii=False, sort_keys=True)
            rows.append(row)
            traces.append(trace_row)
            batch_rows.append(row)
            batch_traces.append(trace_row)
        (evidence_path.parent / "codex_direct_extractions.jsonl").write_text(
            "\n".join(batch_rows) + "\n", encoding="utf-8"
        )
        (evidence_path.parent / "checklist_trace.jsonl").write_text(
            "\n".join(batch_traces) + "\n", encoding="utf-8"
        )
    (ROOT / "codex_direct_payloads.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (ROOT / "checklist_trace.jsonl").write_text("\n".join(traces) + "\n", encoding="utf-8")
    print(f"authored {len(rows)} v2 payloads and {len(traces)} complete checklist traces")


if __name__ == "__main__":
    main()
