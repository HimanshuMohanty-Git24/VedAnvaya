"""The resolved deity population: one answer to "what counts as a Devata", used everywhere.

**The problem this module owns.** The Anukramani names a *devata* for every Rigvedic hymn,
and that slot is not a theological claim. It holds Indra and Agni; it also holds the patron
who commissioned the hymn (22 of them), the gift he gave (7 danastuti topic labels, e.g.
"praise of the gift of Sudas son of Pijavana"), and 28 abstractions ruled not to name an
addressee at all. The frozen graph types all 214 of them ``:Devata`` because the Anukramani
does. That is faithful to the source and wrong for a product: a user who opens a deity list
must not find Vasistha or "the course of becoming" in it. It must find the dog, which is a
deified animal beside thirteen others and is in the population by recorded ruling.

**Why it is solved here and not in the graph.** The ontology is frozen for Product V1, and
V3.2 carried forward two bounded query defects by name:

*Defect A* -- ``deity_profile`` surfaces ``profile_co_devatas``, a materialised list of
*display labels* on each Devata node, and for Indra that list is ``['Vasukra']``: a human.
The property is frozen, so the API resolves those labels back to nodes and filters them by
their recorded eligibility ruling rather than trusting the list.

*Defect B* -- ``deities_through_common_rishis`` walks ``HAS_DEVATA`` twice and lands on
whatever the Anukramani ascribed, which for Indra alone reaches Vasukra, Vamadeva, Atri,
Brbu the carpenter and four danastuti labels.

Neither is fixed by editing the graph. Both are contained by making every deity surface
pass through this module, so there is exactly one definition of the population and adding a
deity endpoint cannot reintroduce the defect by forgetting a filter.

**Fail closed, and notice.** A ``:Devata`` with no eligibility ruling is excluded from the
deity population: we cannot certify as a god a thing nobody has ruled on. That alone would
let a rebuild that failed to rule on a node silently delete deities, so
:data:`KNOWN_DEITY_STRUCTURES` is still asserted to partition ``structure`` in
``tests/api/test_deity_population.py`` -- structure is no longer the eligibility rule but it
is still a fact about every row, and an unknown value fails a test rather than quietly
shrinking the pantheon. Same discipline that stopped a guard from cascading into deleting
all 419 layer-owned grades.
"""

from __future__ import annotations

from typing import Any, Final, NamedTuple

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
#:
#: Named for what it now binds. It was ``deity_structures`` and bound a list of structure
#: names; it binds ``is_deity`` values, and a parameter whose name says "structures" while
#: it carries booleans is the kind of small untruth that makes the next reader reintroduce
#: the structure filter. Every caller spreads ``deity_structure_parameters(...)``, so no
#: call site hardcodes the name.
DEITY_STRUCTURE_PARAM: Final = "deity_eligibility"

#: What a client is told when a response has filtered the Anukramani's slot down to gods.
#: Measured against the live counts rather than asserted, so the sentence cannot drift from
#: the graph the way three V3.1 caveats did.
NON_DEITY_EXCLUSION_CAVEAT: Final = (
    "The Anukramani names a 'devata' for every hymn, and 57 of the 214 are not gods: 22 "
    "human patrons and seers (Vasistha, Visvamitra, Brbu the carpenter), 7 danastuti "
    "labels naming the gift rather than a recipient ('praise of the gift of Sudas son of "
    "Pijavana'), and 28 abstractions ruled not to name an addressee, each with its reason "
    "recorded. This response excludes all 57 and KEEPS the 5 labels ruled UNDECIDED "
    "(Atma, Annam, Brahma, Rati, Saci), because an undecided label removed is a decision "
    "made by default. Ask with population=all_ascriptions to see the Anukramani's slot as "
    "it stands, with each row's ruling stated."
)


def deity_structure_clause(variable: str) -> str:
    """A Cypher predicate restricting ``variable`` to the ruled deity population.

    ``variable`` is a query-author's own alias -- never a client value -- and the admitted
    values travel as a bound parameter, so nothing a caller controls reaches the query text.

    **This reads the ruling, not the structure.** It used to filter on ``structure IN
    DEITY_STRUCTURES``, which made it a *second* eligibility predicate beside the documented
    one in :mod:`vedagraph.domain.deity_eligibility`, and the two disagreed on 29 of the 214
    nodes -- the whole of GAP-ENTITY_COVERAGE-008. 28 were ABSTRACT labels ruled
    ABSTRACTION_NOT_AN_ADDRESSEE, each with a recorded reason, which this clause admitted
    anyway. The 29th was ``VG:DEVATA:SUNAH``, the dog, ruled a deity on the recorded ground
    that thirteen other animals are in the population and "excluding this one because its
    structure is UNSPECIFIED rather than INDIVIDUAL would be excluding on a morphological
    accident" -- and this clause was that accident.

    ``deity_eligibility`` states its own removal condition: when no ``:Devata`` has a null
    ``is_deity``, use :data:`~vedagraph.domain.deity_eligibility.ELIGIBLE_DEITY_PREDICATE`.
    Measured: 214 of 214 ruled, 0 unruled, 0 excluded without a recorded reason. So the
    condition is met and this is that predicate, bound rather than interpolated.

    ``coalesce`` is what keeps it failing closed: a Devata with no ruling reads ``false`` and
    is excluded, rather than being admitted on the strength of a missing property.
    """
    return f"coalesce({variable}.is_deity, false) IN ${DEITY_STRUCTURE_PARAM}"


def deity_structure_parameters(population: DeityPopulation) -> dict[str, Any]:
    """Parameters for :func:`deity_structure_clause` under the requested population.

    ``ALL_ASCRIPTIONS`` passes every known structure rather than dropping the clause, so
    the two populations run the *same* Cypher and differ only in a bound list. A query that
    dropped the filter instead would be a second code path, and a second code path is how
    one of these two defects gets reintroduced.
    """
    admitted = [True] if population is DeityPopulation.DEITIES else [True, False]
    return {DEITY_STRUCTURE_PARAM: admitted}


def is_deity(structure: str | None) -> bool:
    """Whether a ``structure`` value denotes a god. Unknown and null are False."""
    return structure in DEITY_STRUCTURES


def population_caveats(population: DeityPopulation) -> list[CaveatView]:
    """The caveat a response must carry for the population it used.

    Both populations get one. Filtering to gods hides 57 real Anukramani ascriptions, and
    *not* filtering returns human patrons and ruled-out abstractions typed ``DEVATA``; a
    client cannot read either payload correctly without being told which happened.
    """
    if population is DeityPopulation.DEITIES:
        return [CaveatView(text=NON_DEITY_EXCLUSION_CAVEAT, source="deity_population_contract")]
    return [
        CaveatView(
            text=(
                "population=all_ascriptions: these rows are the Anukramani's devata slot, "
                "not a pantheon. 57 of them are human patrons, praise of a gift, or an "
                "abstraction ruled not to name an addressee. Read each row's `is_deity` "
                "before calling any of them a deity."
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
    "THIS SUBJECT IS NOT A DEITY. Its Anukramani structure is {structure!r} and it is ruled "
    "{kind}. The devata slot holds 22 human patrons, 7 praise-of-a-gift labels and 28 "
    "abstractions ruled not to name an addressee alongside the gods; do not render this "
    "subject as a god. Its ascription figures are real -- what is not real is the "
    "implication that the thing ascribed to is divine."
)


class DevataSubject(NamedTuple):
    """One devata-slot subject's structure and its recorded eligibility ruling.

    Both travel together because the gate needs the ruling and the response needs the
    structure, and passing only the structure is what let three surfaces re-derive
    eligibility from it and disagree with the filter that selected the row.
    """

    structure: str | None
    is_deity: bool
    non_deity_kind: str | None = None


def subject_disclosure(subject: DevataSubject) -> tuple[bool, list[CaveatView]]:
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
    if subject.is_deity:
        return True, []
    return False, [
        CaveatView(
            text=NOT_A_DEITY_SUBJECT.format(
                structure=subject.structure,
                kind=subject.non_deity_kind or "not a deity",
            ),
            source="deity_population_contract",
        )
    ]


def filter_co_deity_labels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop non-deity rows from a resolved co-deity list (defect A).

    ``profile_co_devatas`` stores display labels, not keys, so a caller resolves them
    against ``:Devata`` nodes first and hands the rows here. Rows that resolved to nothing
    are dropped too: an unresolvable label cannot be shown as a deity on the strength of
    being a string in a frozen property.

    Reads the ruling, for the same reason :func:`deity_structure_clause` does: this filtered
    on ``structure`` and so dropped the dog, whom the recorded ruling admits. ``is not True``
    rather than ``is False`` keeps it failing closed on a row that carries no ruling at all.
    """
    return [row for row in rows if row.get("is_deity") is True]
