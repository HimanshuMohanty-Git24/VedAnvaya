"""Entity resolution: a name in a question becomes a node in the graph, or stays a name.

**Why this cannot be left to the model.** Asked who Indra is, a language model answers
from its training data. Asked the same question by this product, the answer must be built
from the 6,539 edges the graph actually carries. So the entity is resolved *here*, against
the registry, before any prompt exists -- and a name that does not resolve is reported
unresolved rather than quietly answered from memory.

**Why the label properties are enumerated rather than guessed.** There is no single label
property in this graph. ``Devata`` carries ``preferred_label``, ``label_en``, ``label_iast``
and ``aliases_iast``; ``Rishi`` carries ``preferred_label``, ``normalized_name`` and two
name lists; ``Concept``, ``Condition`` and ``Ritual`` carry ``preferred_label_en``,
``preferred_label_sa``, ``aliases_en`` and ``aliases_sa``. Only ``display_label`` is
universal. A resolver written against a ``label`` property -- which is the obvious guess
and which this one was, first -- matches *nothing*: the property does not exist anywhere in
the graph, every lookup returns zero rows, and the pipeline still returns HTTP 200 with an
answer built from no entity evidence at all.

**Why exactness is ranked and not required.** ``rta`` should reach *Ṛta* and ``fever``
should reach *takman*, so alias and containment matching are needed. But containment also
means ``soma`` reaches *Somapa* and *Soma-Pusan*, so an exact hit must outrank a contained
one or the wrong node wins. :data:`_MATCH_RANK` is that ordering, and it travels back to
the caller so a response can say which rung resolved a name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Final

from vedagraph.api.ask.matching import FOLD_LADDER, cypher_folded, cypher_tokens
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

#: Types a question may name. Deliberately not every label in the graph: ``Chandas`` is
#: here because "which metre" is a real question, while ``Lemma``, ``TextVersion`` and
#: ``QAIssue`` are internal and must never surface as an answer's subject.
RESOLVABLE_LABELS: Final[tuple[str, ...]] = (
    "Devata",
    "Rishi",
    "Concept",
    "Condition",
    "Ritual",
    "Chandas",
)


class MatchRank(IntEnum):
    """How a name reached a node. Lower is a stronger claim."""

    EXACT_LABEL = 0
    EXACT_ALIAS = 1
    TOKEN_IN_LABEL = 2
    """The name is one whole word of a multi-word label: *takman* in *fever (takman)*.

    Never a bare substring. See :mod:`vedagraph.api.ask.matching` for why: *rta* is a
    substring of *mortar*, and character containment resolved a question about cosmic
    order onto a kitchen implement.
    """


@dataclass(frozen=True)
class ResolvedEntity:
    name_as_asked: str
    entity_key: str
    label: str
    entity_type: str
    match_rank: MatchRank
    description: str | None = None

    @property
    def is_exact(self) -> bool:
        return self.match_rank in (MatchRank.EXACT_LABEL, MatchRank.EXACT_ALIAS)


# Every label-bearing property in the graph, collected once. `coalesce` is not used for
# matching because a name can sit in any of them independently -- Ṛta's English label and
# its IAST label are different strings and either may be what was typed.
_LABEL_PROPS: Final = (
    "n.display_label",
    "n.preferred_label",
    "n.preferred_label_en",
    "n.preferred_label_sa",
    "n.label_en",
    "n.label_iast",
    "n.normalized_name",
)

_ALIAS_PROPS: Final = (
    "n.aliases_iast",
    "n.aliases_en",
    "n.aliases_sa",
    "n.personal_names_iast",
    "n.patronymics_iast",
)

# Built once at import. The property names are literals from the two tuples above and
# never client input, so this is interpolation of this module's own constants.
_LABELS_LIST: Final = "[" + ", ".join(_LABEL_PROPS) + "]"
_ALIASES_LIST: Final = "(" + " + ".join(f"coalesce({p}, [])" for p in _ALIAS_PROPS) + ")"

# One query for every candidate the planner nominated, not one per name.
#
# Batched because nomination is deliberately broad -- the planner offers every content
# word and lets the registry reject what it does not know -- and per-name resolution made
# that unaffordable: each name cost a scan of the label-bearing registry at roughly 140ms,
# doubled on a miss by the fold ladder, so eight candidates approached two seconds before
# retrieval had begun. Here the registry is scanned once and every candidate is tested
# against each node as it passes.
#
# `$candidates` is a list of maps: {asked, folded, rung}. Both sides of every comparison
# are folded, so `rta` meets the stored `ṛta` and neither spelling is privileged.
_RESOLVE_BATCH: Final = f"""
MATCH (n)
WHERE any(l IN labels(n) WHERE l IN $resolvable)
  AND NOT n:Internal AND NOT n:QAIssue
WITH n,
     [x IN {_LABELS_LIST} WHERE x IS NOT NULL] AS label_values,
     [a IN {_ALIASES_LIST} WHERE a IS NOT NULL] AS alias_values
WITH n, label_values,
     [x IN label_values | {cypher_folded("x")}] AS folded_labels,
     [a IN alias_values | {cypher_folded("a")}] AS folded_aliases,
     reduce(acc = [], x IN label_values | acc + {cypher_tokens("x")}) AS label_tokens
UNWIND $candidates AS candidate
WITH n, label_values, candidate,
     candidate.folded IN folded_labels AS exact_label,
     candidate.folded IN folded_aliases AS exact_alias,
     candidate.folded IN label_tokens AS token_label
WHERE exact_label OR exact_alias OR token_label
RETURN candidate.asked AS asked,
       candidate.rung AS rung,
       n.entity_key AS entity_key,
       coalesce(n.display_label, head(label_values), n.entity_key) AS label,
       head([l IN labels(n) WHERE l IN $resolvable]) AS entity_type,
       coalesce(n.short_description, n.definition) AS description,
       CASE WHEN exact_label THEN 0 WHEN exact_alias THEN 1 ELSE 2 END AS match_rank
ORDER BY asked, rung, match_rank, size(coalesce(n.display_label, '')), n.entity_key
"""

_RESOLVE_PASSAGE: Final = """
MATCH (p:Passage)
WHERE p.canonical_key = $name OR p.canonical_citation = $name
RETURN p.canonical_key AS entity_key,
       p.canonical_citation AS label,
       'Passage' AS entity_type,
       null AS description,
       0 AS match_rank
LIMIT 1
"""

#: A canonical key or citation, both of which carry digits. No Vedic entity label does,
#: so this separates "RV 1.1.1" and "VG:RV:SAK:M01:S001:V001" from an ordinary word
#: without needing to parse either.
_CITATION_SHAPE: Final = re.compile(r"\d")


def _looks_like_citation(name: str) -> bool:
    return bool(_CITATION_SHAPE.search(name))


#: Cap on how many candidate names one question may offer. Nomination is broad, so this
#: bounds the size of the UNWIND rather than a number of round trips.
MAX_CANDIDATES: Final = 14

#: Cap on how many *resolved* subjects reach retrieval. A question with more real
#: subjects than this is not a research question, and every extra one dilutes the
#: evidence budget.
MAX_RESOLVED: Final = 6


def resolve_entities(names: list[str], repository: Neo4jRepository) -> list[ResolvedEntity]:
    """Resolve candidate names to graph nodes: one query, best match per name.

    The fold ladder is expressed as a ``rung`` on each candidate rather than as a retry
    loop, so all rungs are tested in the same pass and the ``ORDER BY`` still guarantees
    a stricter fold outranks a looser one. A permissive rewrite (``ri`` for ``ṛ``) can
    therefore never beat an exact spelling, which is the property the ladder existed for.

    Nomination order from the planner is preserved: a known deity is offered before an
    incidental content word, and the retriever profiles only the first few.

    A name resolving to a node an earlier name already claimed is dropped, not repeated:
    "Soma" and "soma" in one question are one subject, and duplicate evidence items would
    spend the packet's budget saying the same thing twice.
    """
    candidates: list[dict[str, object]] = []
    seen_folds: set[tuple[str, str]] = set()

    for name in names[:MAX_CANDIDATES]:
        candidate = name.strip()
        if len(candidate) < 2:
            # A single character is a token of half the registry.
            continue
        for rung, fold in enumerate(FOLD_LADDER):
            folded = fold(candidate)
            if not folded or (candidate, folded) in seen_folds:
                continue
            seen_folds.add((candidate, folded))
            candidates.append({"asked": candidate, "folded": folded, "rung": rung})

    if not candidates:
        return []

    rows = repository.run(
        _RESOLVE_BATCH,
        candidates=candidates,
        resolvable=list(RESOLVABLE_LABELS),
    )

    # The query returns every match for every candidate, ordered best-first per name.
    # Take the first row per asked-name and keep the planner's nomination order.
    best_by_name: dict[str, dict[str, object]] = {}
    for row in rows:
        asked = str(row["asked"])
        if asked not in best_by_name:
            best_by_name[asked] = row

    resolved: list[ResolvedEntity] = []
    claimed: set[str] = set()

    for name in names[:MAX_CANDIDATES]:
        candidate = name.strip()
        # Named `best` rather than reusing `row`: that name is already bound by the
        # loop above, with a different type, and mypy --strict rejects the rebind.
        best: dict[str, object] | None = best_by_name.get(candidate)
        if best is None:
            if not _looks_like_citation(candidate):
                continue
            # Passage citations are matched unfolded: they are ASCII structural keys
            # ("RV 1.1.1"), so folding would be a no-op with a misleading name. Guarded
            # by shape because nomination is broad -- without the guard every ordinary
            # word that named no entity would cost its own passage lookup.
            passage_rows = repository.run(_RESOLVE_PASSAGE, name=candidate)
            if not passage_rows:
                continue
            best = passage_rows[0]

        key = str(best["entity_key"])
        if key in claimed:
            continue
        claimed.add(key)
        resolved.append(
            ResolvedEntity(
                name_as_asked=candidate,
                entity_key=key,
                label=str(best["label"]),
                entity_type=str(best["entity_type"] or "Entity"),
                match_rank=MatchRank(int(str(best["match_rank"]))),
                description=(str(best["description"]) if best.get("description") else None),
            )
        )
        if len(resolved) >= MAX_RESOLVED:
            break

    return resolved
