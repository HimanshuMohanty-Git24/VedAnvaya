"""One occurrence-count contract, applied after every loader, for every registry label.

**The defect this exists to remove.** ``occurrence_count`` was written by three loaders to
three conventions and by none to a declared one, so the property could not be read without
knowing which loader had touched the node -- which nothing recorded. Measured per registry
namespace rather than per sampled row, because a row sample says the layer is fine:

===========================  =====  ==========  ============  ===============
namespace                    nodes  stored sum  mantra edges  container edges
===========================  =====  ==========  ============  ===============
``RV_WSC2023_ANUKRAMANI``      367           0        10,565                0
``AV_WHITNEY_ANUKRAMANI``      134         542         4,542              542
``YV_VSM_RSISUCI``             228       2,240         2,240                0
===========================  =====  ==========  ============  ===============

The Yajurvedic loader counts mantra-scope, the Atharvavedic one counts container-scope, and
the Rigvedic path writes a literal ``0`` over the most complete seer layer in the corpus.
Every one of those figures is internally consistent, which is exactly why no check caught
it: the Rigvedic ``0`` is *arithmetically correct* under the Atharvavedic convention, since
no Rigvedic seer is attached to a container. ``:Devata`` and ``:Chandas`` were never written
at all, so their ``null`` was indistinguishable from a real zero.

**The contract.**

* One declared predicate per label. Not "every edge that touches the node": a
  ``:Devata``'s ``MENTIONS_DEVATA`` degree is a different question from its dedication
  degree, and one property may not carry both.
* ``occurrence_count`` is the node's full in-degree on that predicate from ``:Passage``,
  at every grain. That is the figure the closure test names -- *a Rigvedic seer's figure
  matches its HAS_RISHI degree* -- and it is the only scope under which the three
  namespaces above become comparable.
* The grain split is landed beside it, because a scope note that says "all grains" is
  useless to a reader who needs to know whether a figure counts verses or hymns.
  ``occurrence_count_mantra_scope`` + ``occurrence_count_container_scope`` ==
  ``occurrence_count``, and a consumer can assert that.
* An unrecognised label **raises**. A contract that silently skips the label it does not
  know is how the property went missing on 789 nodes in the first place.

**What this deliberately does not do.** It does not touch ``occurrence_count`` on
``:Formula``, ``:FormulaFamily``, ``:DevataAscription`` or the lexical layer. Those are
written by their own generators to their own declared meanings and are out of this
contract's population; ``COVERED_LABELS`` is the whole of it and is asserted to be so.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:  # pragma: no cover - typing only
    from neo4j import Session

#: Bumped when the meaning of any landed property changes, never when a count moves.
CONTRACT_VERSION: Final = "VG:OCCURRENCE_CONTRACT:V1"

#: The one scope every covered label is counted under.
OCCURRENCE_SCOPE: Final = "PASSAGE_DEGREE_ALL_GRAINS"


class UnknownOccurrenceLabel(ValueError):
    """Raised when a label is asked for a count the contract does not define.

    Deliberately an error and not a warning. The alternative -- returning ``None`` for an
    unknown label -- reproduces the original defect one label at a time.
    """


@dataclass(frozen=True)
class OccurrenceRule:
    """The declared predicate for one registry label, and why it is that one."""

    label: str
    predicate: str
    rationale: str


#: The complete population of this contract. Adding a label here is the only way to bring
#: it in, and :func:`rule_for` raises for anything absent.
COVERED_LABELS: Final[dict[str, OccurrenceRule]] = {
    "Rishi": OccurrenceRule(
        label="Rishi",
        predicate="HAS_RISHI",
        rationale=(
            "The seer-attribution predicate, and the only predicate any Passage carries "
            "to a :Rishi. BELONGS_TO_FAMILY runs from a family and is not an attestation."
        ),
    ),
    "Devata": OccurrenceRule(
        label="Devata",
        predicate="HAS_DEVATA",
        rationale=(
            "The dedication predicate, parallel to HAS_RISHI and HAS_CHANDAS. NOT "
            "MENTIONS_DEVATA: a mention is the text naming a deity, a dedication is the "
            "Anukramani ascribing the passage to one, and 17,165 mentions against 10,558 "
            "dedications is two questions rather than one number."
        ),
    ),
    "Chandas": OccurrenceRule(
        label="Chandas",
        predicate="HAS_CHANDAS",
        rationale=(
            "The metre-attribution predicate, and the only predicate a Passage carries "
            "to a :Chandas."
        ),
    ),
}


def rule_for(label: str) -> OccurrenceRule:
    """The rule for one label, or :class:`UnknownOccurrenceLabel`."""
    try:
        return COVERED_LABELS[label]
    except KeyError as exc:
        raise UnknownOccurrenceLabel(
            f"{label!r} is not in the occurrence-count contract. "
            f"Covered labels: {sorted(COVERED_LABELS)}. Add an OccurrenceRule with its "
            f"declared predicate rather than letting the property go unwritten."
        ) from exc


def measure_cypher(label: str) -> str:
    """Read-only Cypher measuring one label's true counts against what is stored.

    Scoped by label, never by an unlabelled ``MATCH (n)``.
    """
    rule = rule_for(label)
    return f"""
MATCH (n:{rule.label})
CALL (n) {{
    OPTIONAL MATCH (m:Mantra)-[e:{rule.predicate}]->(n)
    RETURN count(e) AS mantra_edges
}}
CALL (n) {{
    OPTIONAL MATCH (p:Passage)-[e:{rule.predicate}]->(n)
    WHERE NOT p:Mantra
    RETURN count(e) AS container_edges
}}
RETURN n.entity_key AS entity_key,
       n.display_label AS display_label,
       n.registry_namespace AS registry_namespace,
       labels(n) AS node_labels,
       n.occurrence_count AS stored_occurrence_count,
       mantra_edges, container_edges,
       mantra_edges + container_edges AS occurrence_count
ORDER BY entity_key
"""


def build_row(measured: dict[str, Any], rule: OccurrenceRule) -> dict[str, Any]:
    """One measured node becomes the whole property set this contract owns.

    Whole, because landing half of it leaves a reader unable to tell which convention a
    figure is in, which is the state this contract ends.
    """
    return {
        "entity_key": measured["entity_key"],
        "display_label": measured["display_label"],
        "registry_namespace": measured["registry_namespace"],
        "node_labels": list(measured["node_labels"]),
        "stored_occurrence_count": measured["stored_occurrence_count"],
        "occurrence_count": int(measured["occurrence_count"]),
        "occurrence_count_mantra_scope": int(measured["mantra_edges"]),
        "occurrence_count_container_scope": int(measured["container_edges"]),
        "occurrence_scope": OCCURRENCE_SCOPE,
        "occurrence_predicate": rule.predicate,
        "occurrence_contract_version": CONTRACT_VERSION,
    }


def rows_for(session: Session, label: str) -> list[dict[str, Any]]:
    """The contract's landed row for every node of one label."""
    rule = rule_for(label)
    return [build_row(dict(record), rule) for record in session.run(measure_cypher(label))]


#: The properties this contract writes. Anything not here is not its business.
WRITTEN_PROPERTIES: Final[tuple[str, ...]] = (
    "occurrence_count",
    "occurrence_count_mantra_scope",
    "occurrence_count_container_scope",
    "occurrence_scope",
    "occurrence_predicate",
    "occurrence_contract_version",
)


def check_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The contract's own gate over a staged row set. Returns findings, not a boolean.

    Three assertions, each of which has a way to fail:

    ``split_sums``
        the two grain figures must sum to the headline. A row where they do not is a row
        whose scope note lies.
    ``every_node_covered``
        no row may carry a null ``occurrence_count``; ``null`` is the state this contract
        was written to end.
    ``scope_recorded``
        every row states its scope and predicate, so a reader never has to know which
        loader touched the node.
    """
    split_mismatches = [
        row["entity_key"]
        for row in rows
        if row["occurrence_count"] is None
        or row["occurrence_count_mantra_scope"] + row["occurrence_count_container_scope"]
        != row["occurrence_count"]
    ]
    nulls = [row["entity_key"] for row in rows if row["occurrence_count"] is None]
    unscoped = [
        row["entity_key"]
        for row in rows
        if not row.get("occurrence_scope") or not row.get("occurrence_predicate")
    ]
    return {
        "rows": len(rows),
        "split_sums": not split_mismatches,
        "split_mismatch_keys": split_mismatches[:20],
        "every_node_covered": not nulls,
        "null_keys": nulls[:20],
        "scope_recorded": not unscoped,
        "unscoped_keys": unscoped[:20],
        "passes": not (split_mismatches or nulls or unscoped),
    }
