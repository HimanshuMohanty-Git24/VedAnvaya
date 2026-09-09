"""Trust, evidence and run identity for every enrichment edge.

The enrichment layer asserts things the corpus does not say: that two mantras in
different Vedas are the same verse, that a phrase is a formula, that a passage is about a
concept. None of that is source data, and the whole layer is worthless if a reader cannot
tell which is which. So every enrichment record carries the same envelope:

* **trust** -- how the claim was reached. A deterministic string comparison and a model's
  reading of a translation are not the same kind of fact and never share a class.
* **method** -- the specific rule or algorithm, named so it can be re-run.
* **score** -- comparable *within* a method, never across methods.
* **evidence** -- the actual text the claim rests on. An edge without evidence is an
  opinion, and :mod:`vedagraph.enrich.validate` rejects it.
* **run** -- pipeline version plus run id, so a claim can be attributed to a build.

The evidence-first UI contract is exactly this envelope: given any edge, "why are these
connected?" is answerable from the edge alone, without re-running anything.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Final

import orjson

#: Bumped whenever a change would make two runs produce different edges from the same
#: corpus. Stored on every record: a candidate produced under one version is not silently
#: comparable with one produced under another.
PIPELINE_VERSION: Final = "vedagraph-graph-enrichment-v1"


class TrustClass(StrEnum):
    """How a claim was reached. Never inferred from confidence.

    The ordering here is not a ranking of usefulness. ``DETERMINISTIC_DERIVED`` is
    reproducible but can still be wrong; ``LLM_EXTRACTED`` can be right and still is not
    permitted to become canonical. They are different kinds of claim, kept apart so a
    query can ask for one and get only that.
    """

    #: A rule over stored text produced this, and re-running the rule reproduces it byte
    #: for byte. The overwhelming majority of this layer.
    DETERMINISTIC_DERIVED = "DETERMINISTIC_DERIVED"
    #: A language model read evidence and proposed this. Candidate unless a person
    #: accepts it. Not byte-deterministic and never claimed to be.
    LLM_EXTRACTED = "LLM_EXTRACTED"
    #: A person reviewed and accepted it. Nothing in this release carries it; it exists
    #: so the promotion path has a target that is not "overwrite the deterministic row".
    HUMAN_REVIEWED = "HUMAN_REVIEWED"
    #: A source states it outright. Reserved for enrichment lifted from an edition's own
    #: apparatus rather than computed.
    SOURCE_EXPLICIT = "SOURCE_EXPLICIT"
    #: A reading of the corpus rather than a report of it, held either by this project or
    #: by a named commentator. Added by Knowledge Model V2 so that an interpretation has
    #: somewhere to live that is not a textual fact -- previously the only way to record
    #: "the Yajurveda reflects a more settled ritual environment" was to dress it as one of
    #: the four classes above. Deliberately absent from :data:`ACCEPTABLE_WITHOUT_REVIEW`.
    INTERPRETIVE_CLAIM = "INTERPRETIVE_CLAIM"


class AssertionState(StrEnum):
    """Whether an assertion is being proposed or is in force."""

    CANDIDATE = "CANDIDATE"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


#: Trust classes whose records may be written with ``AssertionState.ACCEPTED``. A model's
#: output is not on this list, which is the whole of the "never make LLM output canonical
#: source data" policy expressed as data rather than as a convention.
ACCEPTABLE_WITHOUT_REVIEW: Final[frozenset[TrustClass]] = frozenset(
    {TrustClass.DETERMINISTIC_DERIVED, TrustClass.SOURCE_EXPLICIT}
)


@dataclass(frozen=True)
class EvidenceSpan:
    """One quoted piece of the corpus that supports a claim.

    ``locator`` names where the quote came from precisely enough to find it again: a
    canonical key plus the surface it was read on. ``quote`` is the text itself, stored
    rather than recomputed, because the point of evidence is that it survives a later
    change to the derivation.
    """

    locator: str
    surface: str
    quote: str

    def as_dict(self) -> dict[str, str]:
        return {"locator": self.locator, "surface": self.surface, "quote": self.quote}


@dataclass(frozen=True)
class Provenance:
    """The envelope every enrichment record carries."""

    trust: TrustClass
    method: str
    score: float
    evidence: tuple[EvidenceSpan, ...]
    state: AssertionState = AssertionState.CANDIDATE
    pipeline_version: str = PIPELINE_VERSION
    run_id: str = ""
    #: Only set for LLM_EXTRACTED records. Empty elsewhere, and validation enforces both
    #: directions: a model name on a deterministic row is as wrong as its absence here.
    model: str = ""
    prompt_policy: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.method:
            raise ValueError("provenance requires a method")
        if not self.evidence:
            raise ValueError(f"{self.method}: an enrichment record requires evidence")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"{self.method}: score {self.score} outside [0, 1]")
        if self.state is AssertionState.ACCEPTED and self.trust not in ACCEPTABLE_WITHOUT_REVIEW:
            raise ValueError(f"{self.trust} may not be ACCEPTED without human review")
        if (self.trust is TrustClass.LLM_EXTRACTED) != bool(self.model):
            raise ValueError("model is required for LLM_EXTRACTED and forbidden otherwise")

    def as_dict(self) -> dict[str, Any]:
        return {
            "trust": str(self.trust),
            "method": self.method,
            "score": round(self.score, 6),
            "evidence": [span.as_dict() for span in self.evidence],
            "state": str(self.state),
            "pipeline_version": self.pipeline_version,
            "run_id": self.run_id,
            "model": self.model,
            "prompt_policy": self.prompt_policy,
            "notes": self.notes,
        }

    def as_edge_properties(self) -> dict[str, Any]:
        """Flatten to Neo4j-storable scalars.

        Neo4j has no nested map property, so evidence is stored as a JSON string. It is
        stored rather than dropped because the API contract requires an edge to be able
        to explain itself without a second lookup.
        """
        return {
            "trust": str(self.trust),
            "method": self.method,
            "score": round(self.score, 6),
            "evidence": orjson.dumps([span.as_dict() for span in self.evidence]).decode(),
            "evidence_count": len(self.evidence),
            "state": str(self.state),
            "pipeline_version": self.pipeline_version,
            "run_id": self.run_id,
            "model": self.model,
            "prompt_policy": self.prompt_policy,
        }


@dataclass
class RunReport:
    """Counts that make one enrichment stage auditable instead of assumed.

    Every stage reports what it *rejected* alongside what it produced. A stage that only
    reports its output cannot be told apart from a stage that silently capped itself.
    """

    stage: str
    produced: int = 0
    rejected: dict[str, int] = field(default_factory=dict)
    capped: dict[str, int] = field(default_factory=dict)
    notes: dict[str, Any] = field(default_factory=dict)

    def reject(self, reason: str, count: int = 1) -> None:
        self.rejected[reason] = self.rejected.get(reason, 0) + count

    def cap(self, reason: str, count: int = 1) -> None:
        self.capped[reason] = self.capped.get(reason, 0) + count

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "produced": self.produced,
            "rejected": dict(sorted(self.rejected.items())),
            "capped": dict(sorted(self.capped.items())),
            "notes": self.notes,
        }


def stable_id(kind: str, *parts: object) -> str:
    """A deterministic identifier for an enrichment record.

    Derived from the record's own identity fields, so two runs over the same corpus
    produce the same ids and a re-load MERGEs rather than duplicates. Blake2b rather than
    UUID5 because these are enrichment-local keys, not corpus entity ids, and they should
    not be mistakable for one.
    """
    payload = "|".join(str(part) for part in parts)
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=16).hexdigest()
    return f"VG:ENRICH:{kind.upper()}:{digest}"


def run_id(stage: str, *inputs: object) -> str:
    """A run identifier that changes when the stage's inputs or version change."""
    payload = "|".join([PIPELINE_VERSION, stage, *(str(item) for item in inputs)])
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()
    return f"{PIPELINE_VERSION}:{stage}:{digest}"
