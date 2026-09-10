"""The resolved deity population: one answer to "what counts as a Devata", used everywhere.

**The problem this module owns.** The Anukramani names a *devata* for every Rigvedic hymn,
and that slot is not a theological claim. It holds Indra and Agni; it also holds the patron
who commissioned the hymn (22 of them), the gift he gave (7 danastuti topic labels, e.g.
"praise of the gift of Sudas son of Pijavana"), and, once, a dog. The frozen graph types
all 214 of them ``:Devata`` because the Anukramani does. That is faithful to the source and
wrong for a product: a user who opens a deity list must not find Vasistha and a dog in it.

**Why it is solved here and not in the graph.** The ontology is frozen for Product V1, and
V3.2 carried forward two bounded query defects by name:

*Defect A* -- ``deity_profile`` surfaces ``profile_co_devatas``, a materialised list of
*display labels* on each Devata node, and for Indra that list is ``['Vasukra']``: a human.
The property is frozen, so the API resolves those labels back to nodes and filters them by
structure rather than trusting the list.

*Defect B* -- ``deities_through_common_rishis`` walks ``HAS_DEVATA`` twice and lands on
whatever the Anukramani ascribed, which for Indra alone reaches Vasukra, Vamadeva, Atri,
Brbu the carpenter and four danastuti labels.

Neither is fixed by editing the graph. Both are contained by making every deity surface
pass through this module, so there is exactly one definition of the population and adding a
deity endpoint cannot reintroduce the defect by forgetting a filter.

**Fail closed, and notice.** An unrecognised or null ``structure`` is excluded from the
deity population: we cannot certify as a god a thing whose type we do not recognise. That
alone would let a rebuild introducing a new structure silently delete deities, so
:data:`KNOWN_DEITY_STRUCTURES` is asserted to partition the label in
``tests/api/test_deity_population.py``. An unknown structure therefore fails a test rather
than quietly shrinking the pantheon -- the same discipline that stopped a guard from
cascading into deleting all 419 layer-owned grades.
"""

from __future__ import annotations

from typing import Any, Final

from vedagraph.api.models.common import CaveatView
from vedagraph.api.models.entity import (
    DEITY_STRUCTURES,
    NON_DEITY_STRUCTURES,
    DeityPopulation,
)

#: Every ``structure`` value the frozen graph is known to carry. Deliberately the union of
#: the two contract sets and not a third list: if these fall out of step the partition test
#: fails, which is the point.
KNOWN_DEITY_STRUCTURES: Final[frozenset[str]] = DEITY_STRUCTURES | NON_DEITY_STRUCTURES

#: Bound as a query parameter, never interpolated. Read by :func:`deity_structure_clause`.
DEITY_STRUCTURE_PARAM: Final = "deity_structures"

#: What a client is told when a response has filtered the Anukramani's slot down to gods.
#: Measured against the live counts rather than asserted, so the sentence cannot drift from
#: the graph the way three V3.1 caveats did.
NON_DEITY_EXCLUSION_CAVEAT: Final = (
    "The Anukramani names a 'devata' for every hymn, and 30 of the 214 are not gods: 22 "
    "human patrons and seers (Vasistha, Visvamitra, Brbu the carpenter), 7 danastuti "
    "labels naming the gift rather than a recipient ('praise of the gift of Sudas son of "
    "Pijavana'), and one dog. This response excludes all 30. Ask with "
    "population=all_ascriptions to see the Anukramani's slot as it stands, with each row's "
    "structure stated."
)


def deity_structure_clause(variable: str) -> str:
    """A Cypher predicate restricting ``variable`` to the resolved deity population.

    ``variable`` is a query-author's own alias -- never a client value -- and the structure
    list travels as a bound parameter, so nothing a caller controls reaches the query text.

    ``coalesce`` is what makes this fail closed: a Devata whose ``structure`` is null
    becomes ``'UNSPECIFIED'``, which is in :data:`NON_DEITY_STRUCTURES`, so it is excluded
    rather than admitted on the strength of a missing property.
    """
    return f"coalesce({variable}.structure, 'UNSPECIFIED') IN ${DEITY_STRUCTURE_PARAM}"


def deity_structure_parameters(population: DeityPopulation) -> dict[str, Any]:
    """Parameters for :func:`deity_structure_clause` under the requested population.

    ``ALL_ASCRIPTIONS`` passes every known structure rather than dropping the clause, so
    the two populations run the *same* Cypher and differ only in a bound list. A query that
    dropped the filter instead would be a second code path, and a second code path is how
    one of these two defects gets reintroduced.
    """
    structures = (
        DEITY_STRUCTURES if population is DeityPopulation.DEITIES else KNOWN_DEITY_STRUCTURES
    )
    return {DEITY_STRUCTURE_PARAM: sorted(structures)}


def is_deity(structure: str | None) -> bool:
    """Whether a ``structure`` value denotes a god. Unknown and null are False."""
    return structure in DEITY_STRUCTURES


def population_caveats(population: DeityPopulation) -> list[CaveatView]:
    """The caveat a response must carry for the population it used.

    Both populations get one. Filtering to gods hides 30 real Anukramani ascriptions, and
    *not* filtering returns a dog as a deity; a client cannot read either payload correctly
    without being told which happened.
    """
    if population is DeityPopulation.DEITIES:
        return [CaveatView(text=NON_DEITY_EXCLUSION_CAVEAT, source="deity_population_contract")]
    return [
        CaveatView(
            text=(
                "population=all_ascriptions: these rows are the Anukramani's devata slot, "
                "not a pantheon. 30 of them are human patrons, praise of a gift, or a dog. "
                "Read each row's `structure` before calling any of them a deity."
            ),
            source="deity_population_contract",
        )
    ]


#: The disclosure owed by any response whose *subject* is a devata-slot entry that is not a
#: god. Hoisted here from ``entity_service`` because this module is the single producer for
#: the population contract and four services now need it -- a generic graph explorer was
#: importing a 2,600-line entity service for one pure function, and the dependency between
#: two peer services pointed the wrong way.
#:
#: Deliberately route-agnostic. The earlier wording ended "and it is served here only
#: because population=all_ascriptions was requested", which is true of the deity routes and
#: **false** of ``/graph/neighborhood`` and ``/graph/path``, which have no ``population``
#: parameter at all: they are generic explorers that resolve 16 id kinds and will surface a
#: non-deity whenever the graph connects one. A shared caveat may not name a parameter only
#: some of its consumers have. Callers that *do* have one add that sentence themselves.
NOT_A_DEITY_SUBJECT: Final = (
    "THIS SUBJECT IS NOT A DEITY. Its Anukramani structure is {structure!r}. The devata "
    "slot holds 22 human patrons, 7 praise-of-a-gift labels and one dog alongside the "
    "gods; do not render this subject as a god. Its ascription figures are real -- what is "
    "not real is the implication that the thing ascribed to is divine."
)


def subject_disclosure(structure: str | None) -> tuple[bool, list[CaveatView]]:
    """Whether a devata-slot subject is a deity, and the caveat owed if it is not.

    Both halves come from here so they cannot disagree. Returning them together is the
    point: a route that wants the flag gets the caveat in the same expression, and there is
    no way to take one without the other.

    That property was learned the hard way. The population contract was enforced on one
    deity route and forgotten on the next five times running -- ``/network`` and
    ``/passages`` in the first adversarial pass, ``/devatas/{id}`` in the first fix round,
    then ``/insights/devatas/{id}`` and the two graph routes in the second pass. Twice the
    flag was set without the caveat, which is the failure mode this signature makes
    unrepresentable.
    """
    if is_deity(structure):
        return True, []
    return False, [
        CaveatView(
            text=NOT_A_DEITY_SUBJECT.format(structure=structure),
            source="deity_population_contract",
        )
    ]


def filter_co_deity_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop non-deity rows from a resolved co-deity list (defect A).

    ``profile_co_devatas`` stores display labels, not keys, so a caller resolves them
    against ``:Devata`` nodes first and hands the rows here. Rows that resolved to nothing
    are dropped too: an unresolvable label cannot be shown as a deity on the strength of
    being a string in a frozen property.
    """
    return [row for row in rows if is_deity(row.get("structure"))]
