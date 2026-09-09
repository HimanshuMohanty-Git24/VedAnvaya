"""The only place in the graph allowed to say what the corpus *means*.

Everything else in this package counts. This module is where a reading lives, and its whole
design is about making a reading impossible to mistake for a count.

The spec this implements is blunt about the failure mode it is preventing: there must be no
``Indra -[:DECLINED_IN]-> LaterVeda`` edge. Such an edge is attractive because it is the
interesting thing to know, and it is exactly wrong, because as a graph edge it is
indistinguishable from ``Indra -[:HAS_EPITHET]-> vṛtrahan``. One is a summary of somebody's
argument and the other is in the text. So an interpretation here is a **node, not an edge**:
it has to be reached deliberately, it cannot be traversed into by accident while walking
deity relationships, and it carries its own supporting evidence rather than borrowing the
authority of the entity it concerns.

Three rules make that hold.

**A claim must cite something.** :func:`load_claims` refuses a claim with neither a
supporting passage nor a supporting metric. An assertion with no evidence is an opinion,
and the enrichment layer's :class:`~vedagraph.enrich.provenance.Provenance` already refuses
those; claims are held to the same bar by the same machinery.

**A claim may only cite metrics that exist.** ``SUPPORTED_BY_STATISTIC`` points at a
:class:`~vedagraph.domain.profiles.DerivedMetric` computed by this pipeline, so "the
numbers support this" is checkable rather than asserted. A claim naming a metric nobody
computed fails the load.

**A claim can never be ACCEPTED.** ``INTERPRETIVE_CLAIM`` is deliberately absent from
:data:`~vedagraph.enrich.provenance.ACCEPTABLE_WITHOUT_REVIEW`, so the envelope itself
raises if anything tries to promote one. Its tier is
:attr:`~vedagraph.domain.ontology.QualityTier.TIER_D` regardless of how well evidenced it
is, because tier records *how a claim was reached*, and no amount of supporting statistics
turns a reading into a report.
"""

from __future__ import annotations

import pathlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

import yaml

from vedagraph.domain.ontology import (
    DOMAIN_MODEL_VERSION,
    LABEL_INTERPRETIVE_CLAIM,
    ClaimStatus,
    QualityTier,
)
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    TrustClass,
)

CLAIMS_PATH: Final = (
    pathlib.Path("data") / "domain" / "vedagraph_domain_v2" / "interpretive_claims.yaml"
)

CLAIM_ID_PREFIX: Final = "VG:CLAIM:"


class ClaimRegistryError(ValueError):
    """The claims file is not loadable as written.

    A distinct type because every one of these is an error in a hand-authored file and the
    only useful response is to fix the file. Nothing here repairs a claim.
    """


@dataclass(frozen=True)
class InterpretiveClaim:
    """One reading of the corpus, with what it rests on."""

    claim_id: str
    claim_text: str
    claim_type: str
    status: ClaimStatus
    scope: str
    #: Passage canonical keys the claim rests on.
    supported_by: tuple[str, ...]
    #: DerivedMetric ids the claim rests on.
    supported_by_statistic: tuple[str, ...]
    #: Entities the claim is about: Devatā keys, concept ids, work ids.
    concerns: tuple[str, ...]
    #: Source id for a claim held by a named commentator, empty for our own synthesis.
    asserted_by: str
    #: Other claim ids this one contradicts.
    contradicts: tuple[str, ...]
    confidence: str
    method: str
    #: What would have to be true for this claim to be wrong. Mandatory: a claim nobody
    #: can imagine being wrong is not a claim, it is a slogan.
    falsifier: str

    @property
    def provenance(self) -> Provenance:
        """The envelope. Always CANDIDATE -- the trust class forbids anything else."""
        return Provenance(
            trust=TrustClass.INTERPRETIVE_CLAIM,
            method=self.method,
            score=0.0,
            evidence=(
                EvidenceSpan(
                    locator=self.claim_id,
                    surface=str(CLAIMS_PATH).replace("\\", "/"),
                    quote=self.claim_text,
                ),
            ),
            state=AssertionState.CANDIDATE,
        )

    def as_row(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type,
            "status": str(self.status),
            "scope": self.scope,
            "confidence": self.confidence,
            "method": self.method,
            "falsifier": self.falsifier,
            "asserted_by": self.asserted_by,
            "quality_tier": str(QualityTier.TIER_D),
            "evidence_passages": len(self.supported_by),
            "evidence_metrics": len(self.supported_by_statistic),
            "display_label": self.claim_text[:80],
            "display_type": LABEL_INTERPRETIVE_CLAIM,
            "short_description": self.claim_text,
            "domain_model_version": DOMAIN_MODEL_VERSION,
        }


def _text(claim_id: str, field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ClaimRegistryError(f"{claim_id}: {field} must be a non-empty string")
    return " ".join(value.split())


def _keys(claim_id: str, field: str, value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ClaimRegistryError(f"{claim_id}: {field} must be a list")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ClaimRegistryError(f"{claim_id}: {field} contains an empty entry")
        out.append(item.strip())
    return tuple(out)


def load_claims(
    project_root: pathlib.Path,
    *,
    known_metric_ids: frozenset[str] = frozenset(),
    known_passage_keys: frozenset[str] = frozenset(),
) -> tuple[InterpretiveClaim, ...]:
    """Parse and validate the claims file.

    ``known_metric_ids`` and ``known_passage_keys`` are checked when supplied. They are
    optional so the file can be validated without a corpus load, but the build passes them:
    a claim citing a metric nobody computed is the interpretive-layer equivalent of an edge
    to a node that does not exist, and it fails silently in exactly the same way.
    """
    path = project_root / CLAIMS_PATH
    if not path.exists():
        return ()
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ClaimRegistryError(f"{CLAIMS_PATH}: expected a mapping at the top level")
    entries = document.get("claims")
    if not isinstance(entries, list):
        raise ClaimRegistryError(f"{CLAIMS_PATH}: 'claims' must be a list")

    statuses = {str(member) for member in ClaimStatus}
    claims: list[InterpretiveClaim] = []
    seen: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            raise ClaimRegistryError("every claim must be a mapping")
        claim_id = str(entry.get("claim_id", "")).strip()
        if not claim_id.startswith(CLAIM_ID_PREFIX):
            raise ClaimRegistryError(f"{claim_id!r} must start with {CLAIM_ID_PREFIX}")
        if claim_id in seen:
            raise ClaimRegistryError(f"duplicate claim_id {claim_id}")
        seen.add(claim_id)

        status = str(entry.get("status", ""))
        if status not in statuses:
            raise ClaimRegistryError(
                f"{claim_id}: status {status!r} is not a ClaimStatus. "
                f"Allowed: {', '.join(sorted(statuses))}"
            )

        supported_by = _keys(claim_id, "supported_by", entry.get("supported_by"))
        statistics = _keys(
            claim_id, "supported_by_statistic", entry.get("supported_by_statistic")
        )
        if not supported_by and not statistics:
            raise ClaimRegistryError(
                f"{claim_id}: cites neither a passage nor a metric. An interpretation "
                "with no evidence is an opinion, and this layer does not store opinions."
            )
        if known_metric_ids:
            for metric in statistics:
                if metric not in known_metric_ids:
                    raise ClaimRegistryError(
                        f"{claim_id}: cites metric {metric!r}, which this pipeline does "
                        "not compute. Either compute it or stop citing it."
                    )
        if known_passage_keys:
            for key in supported_by:
                if key not in known_passage_keys:
                    raise ClaimRegistryError(
                        f"{claim_id}: cites passage {key!r}, which is not in the corpus"
                    )

        claims.append(
            InterpretiveClaim(
                claim_id=claim_id,
                claim_text=_text(claim_id, "claim_text", entry.get("claim_text")),
                claim_type=_text(claim_id, "claim_type", entry.get("claim_type")),
                status=ClaimStatus(status),
                scope=_text(claim_id, "scope", entry.get("scope")),
                supported_by=supported_by,
                supported_by_statistic=statistics,
                concerns=_keys(claim_id, "concerns", entry.get("concerns")),
                asserted_by=str(entry.get("asserted_by", "") or ""),
                contradicts=_keys(claim_id, "contradicts", entry.get("contradicts")),
                confidence=str(entry.get("confidence", "MEDIUM")),
                method=_text(claim_id, "method", entry.get("method")),
                falsifier=_text(claim_id, "falsifier", entry.get("falsifier")),
            )
        )

    known = {claim.claim_id for claim in claims}
    for claim in claims:
        for other in claim.contradicts:
            if other not in known:
                raise ClaimRegistryError(
                    f"{claim.claim_id}: contradicts unknown claim {other!r}"
                )
    return tuple(sorted(claims, key=lambda claim: claim.claim_id))


def claim_summary(claims: Sequence[InterpretiveClaim]) -> dict[str, Any]:
    """Counts for the scorecard: how many claims, and how many actually cite evidence."""
    by_status: dict[str, int] = {}
    for claim in claims:
        by_status[str(claim.status)] = by_status.get(str(claim.status), 0) + 1
    return {
        "claims": len(claims),
        "with_passage_evidence": sum(1 for c in claims if c.supported_by),
        "with_statistical_evidence": sum(1 for c in claims if c.supported_by_statistic),
        "with_both": sum(
            1 for c in claims if c.supported_by and c.supported_by_statistic
        ),
        "with_external_source": sum(1 for c in claims if c.asserted_by),
        "by_status": dict(sorted(by_status.items())),
    }
