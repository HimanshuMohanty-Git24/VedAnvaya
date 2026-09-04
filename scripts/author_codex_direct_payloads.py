"""Materialise Codex-direct, evidence-grounded payloads for the 508-mantra pilot.

The semantic decision for this pilot is intentionally narrow: a deterministic lexical
mention paired with explicit invocation or praise wording in the supplied translation
can suggest the corresponding whitelisted relation. It does not claim symbolism,
causality, or a new concept. Everything else receives an explicit no-claim. The script
only serialises the decisions made in this task; it never invokes an LLM or reads an API
key.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1")

ENGLISH_NAMES = {
    "agniḥ": ("Agni",),
    "indraḥ": ("Indra",),
    "somaḥ": ("Soma",),
    "varuṇaḥ": ("Varuna",),
    "mitraḥ": ("Mitra",),
    "savitā": ("Savitar", "Savita"),
    "uṣāḥ": ("Dawn", "Morn"),
    "sūryaḥ": ("Sun", "Sun-God"),
    "aśvinau": ("Asvins", "Ashvins"),
    "pṛthivī": ("Earth",),
    "vāyuḥ": ("Vayu",),
    "marutaḥ": ("Maruts",),
    "aditiḥ": ("Aditi",),
    "rudraḥ": ("Rudra",),
    "parjanyaḥ": ("Parjanya",),
    "bṛhaspatiḥ": ("Brhaspati", "Brihaspati"),
    "saramā": ("Sarama",),
    "araṇyānī": ("Aranyani",),
    "śraddhā": ("Faith",),
}


def _supported_relation(translation: dict[str, object] | None, label: str) -> str | None:
    if translation is None:
        return None
    text = str(translation.get("text") or "")
    names = ENGLISH_NAMES.get(label, ())
    for name in names:
        escaped = re.escape(name)
        if re.search(rf"\bO\s+{escaped}\b", text, flags=re.IGNORECASE):
            return "INVOKES"
        if re.search(
            rf"\b(?:call|calls|invoke|invokes|praise|praises|laud|lauds)\b[^.\n]{{0,100}}\b{escaped}\b",
            text,
            flags=re.IGNORECASE,
        ):
            return "INVOKES" if re.search(r"\b(?:call|invoke)", text, re.IGNORECASE) else "PRAISES"
    return None


def author_payload(packet: dict[str, object]) -> dict[str, object]:
    mentions = packet.get("mentions", [])
    translation = packet.get("translation")
    if not isinstance(translation, dict):
        translation = None
    assertions: list[dict[str, object]] = []
    if isinstance(mentions, list):
        for mention in mentions:
            if not isinstance(mention, dict):
                continue
            entity_key = str(mention["entity_key"])
            token_keys = [str(item) for item in mention.get("token_keys", [])]
            predicate = _supported_relation(translation, str(mention["entity_label"]))
            if predicate is None:
                continue
            assertions.append(
                {
                    "predicate": predicate,
                    "subject_passage_key": str(packet["passage_key"]),
                    "object_entity_key": entity_key,
                    "object_local_id": None,
                    "explicitness": "EXPLICIT",
                    "confidence": 0.72,
                    "evidence": [
                        {
                            "passage_key": str(packet["passage_key"]),
                            "span_type": "LEXICAL_MENTION",
                            "sanskrit_token_keys": token_keys,
                            "translation_id": None,
                            "note": (
                                "The token is the supplied lexical anchor for the named entity."
                            ),
                        },
                        {
                            "passage_key": str(packet["passage_key"]),
                            "span_type": "TRANSLATION_LINE",
                            "sanskrit_token_keys": [],
                            "translation_id": str(translation["translation_id"]),
                            "note": (
                                "Griffith explicitly supplies the invocation or praise wording."
                            ),
                        },
                    ],
                }
            )
    return {
        "mantra_id": str(packet["citation"]),
        "entities": [],
        "assertions": assertions,
        "uncertainties": [],
        "no_claim_reasons": (
            []
            if assertions
            else [
                "The supplied EvidencePacket does not explicitly support a whitelisted "
                "semantic relation beyond its deterministic lexical facts."
            ]
        ),
    }


def main() -> None:
    batch_root = ROOT / "batches"
    output_path = ROOT / "codex_direct_payloads.jsonl"
    rows: list[str] = []
    for evidence_path in sorted(batch_root.glob("batch_*/evidence.jsonl")):
        batch_payloads: list[str] = []
        for line in evidence_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            packet = json.loads(line)
            payload = author_payload(packet)
            record = {"passage_key": packet["passage_key"], "payload": payload}
            encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)
            rows.append(encoded)
            batch_payloads.append(encoded)
        (evidence_path.parent / "codex_direct_extractions.jsonl").write_text(
            "\n".join(batch_payloads) + "\n", encoding="utf-8"
        )
    output_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"authored {len(rows)} Codex-direct payloads")


if __name__ == "__main__":
    main()
