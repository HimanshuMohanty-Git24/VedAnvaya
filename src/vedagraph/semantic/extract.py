"""The extraction boundary: schema, prompt, provider, and the parsing of a reply.

The pipeline talks to a :class:`SemanticExtractorProvider`, never to a vendor SDK. Only
one implementation exists today and only one is needed; the interface is here because
the validator, the acceptance policy and the evaluator must be testable without a
network, and a fake provider is the cheapest way to guarantee that.

Structured Outputs is used in strict mode and there is no free-form parser anywhere. A
reply that does not fit the schema is a failed request, not something to salvage with a
regular expression: a half-parsed assertion is exactly the kind of plausible artefact
this layer exists to keep out.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vedagraph.models.semantic import EvidencePacket, TokenUsage
from vedagraph.semantic.ontology import (
    ALLOWED_PREDICATES,
    ONTOLOGY_VERSION,
    Explicitness,
    SemanticNodeType,
)

SCHEMA_NAME = "rigveda_semantic_extraction_v1"
DEFAULT_PROMPT_PATH = Path("prompts/semantic_extraction_v1.md")

#: Published list price for gpt-5.6-luna, USD per million tokens. Recorded here so a
#: cost report is reproducible, and overridable per run so a price change does not
#: silently rewrite history. Actual token counts always come from the API response.
LUNA_INPUT_USD_PER_MILLION = 0.20
LUNA_OUTPUT_USD_PER_MILLION = 1.20
#: Cached input is billed at a discount. This is the value used until a run observes the
#: provider's own figure; it affects only the cost report, never what is sent.
LUNA_CACHED_INPUT_USD_PER_MILLION = 0.02

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class SystemPrompt:
    """A version-controlled prompt read from disk, never assembled in Python."""

    version: str
    ontology_version: str
    packet_version: str
    text: str


def load_system_prompt(path: Path = DEFAULT_PROMPT_PATH) -> SystemPrompt:
    """Read the prompt file and its declared versions, refusing an ontology mismatch."""
    raw = path.read_text(encoding="utf-8")
    match = _FRONT_MATTER.match(raw)
    if match is None:
        raise ValueError(f"{path} has no version front matter")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        if key.strip():
            meta[key.strip()] = value.strip()
    declared = meta.get("ontology_version", "")
    if declared != ONTOLOGY_VERSION:
        raise ValueError(
            f"{path} was written against ontology {declared!r}, code declares {ONTOLOGY_VERSION!r}"
        )
    return SystemPrompt(
        version=meta["prompt_version"],
        ontology_version=declared,
        packet_version=meta["packet_version"],
        text=raw[match.end() :].strip(),
    )


def _enum(values: list[str]) -> dict[str, Any]:
    return {"type": "string", "enum": values}


def extraction_json_schema() -> dict[str, Any]:
    """The strict Structured Outputs schema.

    Every object forbids additional properties and lists every property as required,
    because strict mode requires it and because an optional field is a field a model will
    omit precisely when it matters. Fields that may be absent are typed nullable instead,
    which keeps "the model declined to say" distinguishable from "the model forgot".
    """
    evidence = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "passage_key": {"type": "string"},
            "span_type": _enum(
                [
                    "SANSKRIT_TOKEN",
                    "SANSKRIT_LINE",
                    "TRANSLATION_LINE",
                    "TRADITIONAL_METADATA",
                    "LEXICAL_MENTION",
                ]
            ),
            "sanskrit_token_keys": {"type": "array", "items": {"type": "string"}},
            "translation_id": {"type": ["string", "null"]},
            "note": {"type": "string"},
        },
        "required": ["passage_key", "span_type", "sanskrit_token_keys", "translation_id", "note"],
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "mantra_id": {"type": "string"},
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "local_id": {"type": "string"},
                        "entity_type": _enum([item.value for item in SemanticNodeType]),
                        "label": {"type": "string"},
                        "description": {"type": "string"},
                        "aliases": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["local_id", "entity_type", "label", "description", "aliases"],
                },
            },
            "assertions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "predicate": _enum(sorted(item.value for item in ALLOWED_PREDICATES)),
                        "subject_passage_key": {"type": "string"},
                        # Exactly one of these is filled; the validator enforces it,
                        # because strict mode has no way to express "one of these two".
                        "object_entity_key": {"type": ["string", "null"]},
                        "object_local_id": {"type": ["string", "null"]},
                        "explicitness": _enum([item.value for item in Explicitness]),
                        "confidence": {"type": "number"},
                        "evidence": {"type": "array", "items": evidence},
                    },
                    "required": [
                        "predicate",
                        "subject_passage_key",
                        "object_entity_key",
                        "object_local_id",
                        "explicitness",
                        "confidence",
                        "evidence",
                    ],
                },
            },
            "uncertainties": {"type": "array", "items": {"type": "string"}},
            "no_claim_reasons": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["mantra_id", "entities", "assertions", "uncertainties", "no_claim_reasons"],
    }


def render_user_message(packet: EvidencePacket) -> str:
    """Serialise the packet for the request. Deterministic, so the input hash means something."""
    payload = packet.model_dump(
        mode="json", exclude={"passage_id", "input_sha256", "schema_version"}
    )
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=1)


@dataclass(frozen=True)
class ExtractionConfig:
    """Everything about a run that changes the output. No undocumented defaults."""

    #: gpt-5.6-luna publishes no dated snapshot: the model id *is* the pin. Every result
    #: therefore records the model string the API returned, which is the only version
    #: evidence available, and no run may claim more reproducibility than that.
    model: str = "gpt-5.6-luna"
    #: One of none, low, medium (the provider default), high, xhigh, max.
    reasoning_effort: str = "medium"
    max_output_tokens: int = 8000
    temperature: float | None = None
    prompt_path: Path = DEFAULT_PROMPT_PATH
    input_usd_per_million: float = LUNA_INPUT_USD_PER_MILLION
    cached_input_usd_per_million: float = LUNA_CACHED_INPUT_USD_PER_MILLION
    output_usd_per_million: float = LUNA_OUTPUT_USD_PER_MILLION
    #: Retries for transport and schema failures. A refusal is not retried: asking again
    #: for something the model declined to produce is not a fix.
    max_attempts: int = 3


@dataclass
class ExtractionResult:
    """One reply, parsed, with what it cost and which model version produced it."""

    passage_key: str
    payload: dict[str, Any]
    usage: TokenUsage
    model: str
    model_snapshot: str | None = None
    refused: bool = False
    error: str = ""
    attempts: int = 1
    raw_response_id: str | None = None

    @property
    def ok(self) -> bool:
        return not self.refused and not self.error


class SemanticExtractorProvider(ABC):
    """What the pipeline needs from a model. Deliberately one method wide."""

    name: str = "abstract"

    @abstractmethod
    def extract(self, packet: EvidencePacket, prompt: SystemPrompt) -> ExtractionResult:
        """Return one parsed reply for one packet, or a result recording why not."""

    def model_identity(self) -> str:
        return self.name


@dataclass
class RecordedProvider(SemanticExtractorProvider):
    """A provider that replays fixed payloads. The whole offline test suite runs on this.

    It exists so that validation, acceptance, evaluation, cost accounting and the
    parallel-consistency report are all testable without a key, a network or a bill.
    """

    payloads: dict[str, dict[str, Any]]
    usage: TokenUsage = field(default_factory=TokenUsage)
    name: str = "recorded"
    model: str = "recorded"

    def extract(self, packet: EvidencePacket, prompt: SystemPrompt) -> ExtractionResult:
        payload = self.payloads.get(packet.passage_key)
        if payload is None:
            return ExtractionResult(
                passage_key=packet.passage_key,
                payload={},
                usage=TokenUsage(requests=1),
                model=self.model,
                error="no recorded payload for this passage",
            )
        return ExtractionResult(
            passage_key=packet.passage_key,
            payload=payload,
            usage=self.usage + TokenUsage(requests=1),
            model=self.model,
        )


class OpenAILunaProvider(SemanticExtractorProvider):
    """gpt-5.6-luna over the OpenAI Responses API with strict Structured Outputs.

    The SDK is imported lazily and the key is read from the environment by the SDK
    itself, so importing this module costs nothing and never touches a credential. A run
    with no key configured fails at construction, loudly, before any packet is built.
    """

    name = "openai"

    def __init__(self, config: ExtractionConfig, *, client: Any | None = None) -> None:
        self.config = config
        if client is not None:
            self._client = client
            return
        try:
            from openai import OpenAI
        except ImportError as error:  # pragma: no cover - exercised only with the extra
            raise RuntimeError(
                "the openai package is required for live extraction: "
                "install the 'llm' extra, or use RecordedProvider offline"
            ) from error
        self._client = OpenAI()

    def model_identity(self) -> str:
        return self.config.model

    def _request(self, packet: EvidencePacket, prompt: SystemPrompt) -> Any:
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "input": [
                {"role": "system", "content": prompt.text},
                {"role": "user", "content": render_user_message(packet)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": SCHEMA_NAME,
                    "schema": extraction_json_schema(),
                    "strict": True,
                }
            },
            "reasoning": {"effort": self.config.reasoning_effort},
            "max_output_tokens": self.config.max_output_tokens,
            "store": False,
        }
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature
        return self._client.responses.create(**kwargs)

    def extract(self, packet: EvidencePacket, prompt: SystemPrompt) -> ExtractionResult:
        last_error = ""
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                response = self._request(packet, prompt)
            except Exception as error:  # a transport failure is data here, not a crash
                last_error = f"{type(error).__name__}: {error}"
                continue
            usage = _usage_from(response)
            text = _output_text(response)
            if text is None:
                # A refusal is a decision, not a fault. Retrying would only ask the same
                # question again, so it is recorded and the run moves on.
                return ExtractionResult(
                    passage_key=packet.passage_key,
                    payload={},
                    usage=usage,
                    model=getattr(response, "model", self.config.model),
                    refused=True,
                    error="model returned no structured content",
                    attempts=attempt,
                    raw_response_id=getattr(response, "id", None),
                )
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as error:
                last_error = f"structured output was not valid JSON: {error}"
                continue
            return ExtractionResult(
                passage_key=packet.passage_key,
                payload=payload,
                usage=usage,
                model=getattr(response, "model", self.config.model),
                model_snapshot=getattr(response, "model", None),
                attempts=attempt,
                raw_response_id=getattr(response, "id", None),
            )
        return ExtractionResult(
            passage_key=packet.passage_key,
            payload={},
            usage=TokenUsage(requests=self.config.max_attempts),
            model=self.config.model,
            error=last_error or "extraction failed",
            attempts=self.config.max_attempts,
        )


def _usage_from(response: Any) -> TokenUsage:
    """Read actual usage off a reply. Estimated token counts are never substituted."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return TokenUsage(requests=1)
    details = getattr(usage, "input_tokens_details", None)
    output_details = getattr(usage, "output_tokens_details", None)
    return TokenUsage(
        requests=1,
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        cached_input_tokens=int(getattr(details, "cached_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        reasoning_tokens=int(getattr(output_details, "reasoning_tokens", 0) or 0),
    )


def _output_text(response: Any) -> str | None:
    """The structured payload as text, or ``None`` if the model produced none."""
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            value = getattr(content, "text", None)
            if isinstance(value, str) and value.strip():
                return value
    return None
