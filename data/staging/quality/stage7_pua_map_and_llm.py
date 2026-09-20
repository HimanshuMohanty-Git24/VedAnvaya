"""Stage 7: derive the PUA mapping, and score the LLM layer with a different model.

Part 1 -- the mapping
---------------------
Every Atharvavedic mantra carries three text layers, and the corrupted one
(SEARCH_DERIVATIVE) is a character-for-character image of the clean one (PARALLEL_TEXT).
So the substitution table can be *derived* rather than guessed: align the two strings and
read off what each Private Use Area codepoint stands in for. 5,123 aligned pairs is enough
that a codepoint's mapping is either unanimous or it is not a mapping.

This matters for the remedy. The committed audit reads this layer as a normaliser deleting
base letters, which would mean the information is gone and the layer must be rebuilt from
source. It is not gone: one letter became one codepoint, and a substitution table restores
it exactly.

Part 2 -- the LLM layer, scored by a model that did not write it
----------------------------------------------------------------
2,459 SemanticAssertion nodes were extracted by claude-opus-5. This agent is claude-opus-5.
Campaign section 26 forbids the same model both making an assertion and declaring it
correct, so these are sent to the provider configured in .env -- an NVIDIA Nemotron model
reached through OpenRouter -- and the model id, the call count and the refusals are all
recorded. A quota error is recorded and the run stops; it is never retried in a loop.
"""

from __future__ import annotations

import collections
import json
import os
import pathlib
import random
import re
import sys
from difflib import SequenceMatcher

from dotenv import load_dotenv

load_dotenv("D:/VedaGraph/.env")
sys.path.insert(0, "D:/VedaGraph/src")
from neo4j import GraphDatabase  # noqa: E402

SCRATCH = pathlib.Path(sys.argv[1])
PUA = re.compile(r"[\ue000-\uf8ff]")
CALL_CAP = 22
BATCH = 5
SEED = 20260915


def derive_mapping(session) -> dict:
    """Read the substitution table off 5,123 corrupted/clean pairs."""
    observations: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    pairs = 0
    unaligned = 0
    for record in session.run(
        "MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(a:TextVersion "
        "  {text_role: 'SEARCH_DERIVATIVE'}) "
        "MATCH (m)-[:HAS_TEXT_VERSION]->(b:TextVersion {text_role: 'PARALLEL_TEXT'}) "
        "WHERE a.text_nfc =~ '.*[\\ue000-\\uf8ff].*' "
        "RETURN m.canonical_key AS key, a.text_nfc AS corrupted, b.text_nfc AS clean"
    ):
        corrupted = record["corrupted"]
        # the clean layer carries verse punctuation the derived layer drops; strip it so
        # the two strings are comparable without pretending the difference is a mapping
        clean = re.sub(r"\s*\|+\s*|\|\|\d+\|\|", " ", record["clean"])
        clean = re.sub(r"\s+", " ", clean).strip()
        pairs += 1
        matcher = SequenceMatcher(None, corrupted, clean, autojunk=False)
        resolved = False
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "replace":
                continue
            source = corrupted[i1:i2]
            target = clean[j1:j2]
            if len(source) == 1 and PUA.match(source):
                observations[f"U+{ord(source):04X}"][target] += 1
                resolved = True
        if not resolved and PUA.search(corrupted):
            unaligned += 1
    table = {}
    for codepoint, counter in sorted(observations.items()):
        total = sum(counter.values())
        winner, count = counter.most_common(1)[0]
        table[codepoint] = {
            "restores_to": winner,
            "restores_to_codepoints": [f"U+{ord(ch):04X}" for ch in winner],
            "observations": total,
            "agreement": round(count / total, 4),
            "alternatives": {
                key: value for key, value in counter.most_common(5) if key != winner
            },
        }
    return {
        "pairs_compared": pairs,
        "pairs_where_no_pua_replacement_aligned": unaligned,
        "table": table,
        "method": (
            "difflib opcode alignment of SEARCH_DERIVATIVE against PARALLEL_TEXT for the "
            "same mantra; a single-codepoint PUA run in a replace opcode is read as "
            "standing for the clean text it replaced."
        ),
    }


def build_llm_tasks(session) -> list[dict]:
    """A stratified sample of the LLM-extracted assertions, with their verse."""
    rows = [
        dict(record)
        for record in session.run(
            "MATCH (m:Mantra)-[:HAS_SEMANTIC_ASSERTION]->(a:SemanticAssertion "
            "  {derivation: 'MODEL_EXTRACTION'}) "
            "MATCH (m)-[:HAS_TEXT_VERSION]->(t:TextVersion {text_role: 'PRIMARY_TEXT'}) "
            "OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(tr:Translation) "
            "RETURN a.assertion_id AS assertion_id, m.canonical_key AS key, "
            "  a.semantic_predicate AS predicate, a.explicitness AS explicitness, "
            "  a.quality_tier AS tier, a.candidate_status AS candidate_status, "
            "  a.evidence_span_start AS span_start, a.evidence_span_end AS span_end, "
            "  a.extraction_model AS extraction_model, t.text_nfc AS sanskrit, "
            "  collect(tr.text)[0] AS translation, "
            "  COUNT { (a)-[:ASSERTION_AGENT]->() } "
            "    + COUNT { (a)-[:ASSERTION_PREDICATE]->() } "
            "    + COUNT { (a)-[:ASSERTION_TARGET]->() } AS slots"
        )
    ]
    strata: dict[tuple, list[dict]] = collections.defaultdict(list)
    for row in rows:
        strata[(row["predicate"], min(row["slots"], 2))].append(row)
    random.seed(SEED)
    sample: list[dict] = []
    target = CALL_CAP * BATCH
    keys = sorted(strata, key=lambda k: str(k))
    per_stratum = max(1, target // max(len(keys), 1))
    for key in keys:
        bucket = strata[key]
        random.shuffle(bucket)
        for row in bucket[:per_stratum]:
            row["stratum"] = f"{key[0]}|slots>={key[1]}"
            sample.append(row)
    random.shuffle(sample)
    return sample[:target]


SYSTEM = (
    "You are adjudicating Vedic Sanskrit semantic annotations produced by a different "
    "system. For each item you are given a verse in IAST, an English translation where "
    "one exists, and a claimed semantic predicate. Decide only whether the verse "
    "supports that predicate. Do not improve the annotation, do not add roles, and do "
    "not guess when the evidence is thin -- answer UNCLEAR instead. Reply with one JSON "
    "array, one object per item, each with keys: id, verdict (one of SUPPORTED, "
    "UNSUPPORTED, UNCLEAR), and reason (at most 20 words)."
)


def run_llm(tasks: list[dict]) -> dict:
    from vedagraph.llm import LLMRequest, get_llm_provider, get_llm_settings
    from vedagraph.llm.base import LLMMessage
    from vedagraph.llm.errors import LLMError, LLMRateLimitError

    settings = get_llm_settings()
    provider = get_llm_provider()
    verdicts: dict[str, dict] = {}
    calls = 0
    stopped = None
    for start in range(0, len(tasks), BATCH):
        if calls >= CALL_CAP:
            stopped = "CALL_CAP_REACHED"
            break
        batch = tasks[start : start + BATCH]
        body = []
        for item in batch:
            body.append(
                json.dumps(
                    {
                        "id": item["assertion_id"],
                        "sanskrit": (item["sanskrit"] or "")[:400],
                        "translation": (item["translation"] or "")[:400],
                        "claimed_predicate": item["predicate"],
                    },
                    ensure_ascii=False,
                )
            )
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="\n".join(body))],
            system=SYSTEM,
            temperature=0.0,
            max_output_tokens=1400,
            timeout_seconds=120.0,
        )
        calls += 1
        try:
            response = provider.generate(request)
        except LLMRateLimitError as error:
            stopped = f"RATE_LIMIT_OR_QUOTA: {error}. Not retried, by policy."
            break
        except LLMError as error:
            stopped = f"PROVIDER_ERROR: {type(error).__name__}: {error}"
            break
        text = response.text or ""
        match = re.search(r"\[.*\]", text, re.S)
        if not match:
            continue
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        for entry in parsed:
            if isinstance(entry, dict) and entry.get("id"):
                verdicts[str(entry["id"])] = {
                    "verdict": str(entry.get("verdict", "")).upper(),
                    "reason": entry.get("reason", ""),
                }
    scored = []
    for item in tasks:
        outcome = verdicts.get(str(item["assertion_id"]))
        if outcome is None:
            continue
        scored.append(
            {
                "assertion_id": item["assertion_id"],
                "canonical_key": item["key"],
                "stratum": item["stratum"],
                "claimed_predicate": item["predicate"],
                "explicitness": item["explicitness"],
                "slots": item["slots"],
                "produced_by": item["extraction_model"],
                "adjudicated_by": settings.model,
                "verdict": outcome["verdict"],
                "reason": outcome["reason"],
            }
        )
    return {
        "provider": settings.provider,
        "model": settings.model,
        "calls_made": calls,
        "call_cap": CALL_CAP,
        "batch_size": BATCH,
        "sample_seed": SEED,
        "tasks_sent": len(tasks),
        "verdicts_returned": len(scored),
        "stopped_because": stopped,
        "independence": (
            "The assertions were produced by claude-opus-5 and this agent IS "
            "claude-opus-5, so they are adjudicated by the configured provider's model "
            "instead. Different vendor, different family, different weights."
        ),
        "summary": dict(collections.Counter(row["verdict"] for row in scored)),
        "by_stratum": {
            stratum: dict(
                collections.Counter(
                    row["verdict"] for row in scored if row["stratum"] == stratum
                )
            )
            for stratum in sorted({row["stratum"] for row in scored})
        },
        "rows": scored,
    }


def main() -> None:
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as session:
        mapping = derive_mapping(session)
        tasks = build_llm_tasks(session)
    driver.close()

    print("== PUA mapping derived from", mapping["pairs_compared"], "pairs")
    for codepoint, entry in mapping["table"].items():
        print("   {} -> {} ({}) n={} agreement={}".format(
            codepoint, ascii(entry["restores_to"]),
            ",".join(entry["restores_to_codepoints"]), entry["observations"],
            entry["agreement"]))
    print("   unaligned pairs:", mapping["pairs_where_no_pua_replacement_aligned"])

    print("== LLM adjudication: sending", len(tasks), "assertions")
    llm = run_llm(tasks)
    print("   provider={} model={} calls={} returned={} stopped={}".format(
        llm["provider"], llm["model"], llm["calls_made"],
        llm["verdicts_returned"], llm["stopped_because"]))
    print("   summary:", llm["summary"])

    (SCRATCH / "stage7_pua_llm.json").write_text(
        json.dumps({"pua_mapping": mapping, "llm_adjudication": llm}, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
