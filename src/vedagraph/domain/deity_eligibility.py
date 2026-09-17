"""One documented predicate for the eligible deity population, landed on the node.

**The defect.** ``:Devata`` is the label the Anukramaṇī's deity slot projects into, and that
slot holds more than deities. 29 of the 214 nodes are not deities at all -- 22 curated
``structure='HUMAN'`` patrons and 7 ``structure='PATRON_PRAISE'`` dānastuti gift-praise
labels -- and they carry 171 dedications between them. A further 42 carry ``ABSTRACT`` or
``UNSPECIFIED`` structure, where *Śraddhā* is a deity addressed in the vocative throughout
RV 10.151 and *abhiśāpa*, a curse, is not.

Nothing held the answer. The eligibility rule existed only inside two staging scripts and
one report, in three different spellings, and the shipped product surface had a fourth:
``domain/queries.py`` excluded ``structure='HUMAN'`` and nothing else, so
``/api/v1/insights/capabilities`` published ``eligible_deities: 192`` -- 35 above the ruled
population and 7 above even the crude one. The registry entry names this as the fixable
part: *"no eligibility field exists to hold the answer"*.

**What this module is.** The field, the one predicate that reads it, and the rulings that
populate it. It mirrors :class:`~vedagraph.domain.rishi_families` prior art on ``:Rishi``,
which already carries ``is_seer`` / ``non_seer_kind`` for exactly this reason, so the two
registries answer the same question the same way.

**The predicate.** :data:`ELIGIBLE_DEITY_PREDICATE` -- ``d.is_deity = true``. One clause.
Not a structure list, because a structure list is the thing that got spelled four ways.

**Three exclusion classes, and a fourth state that is not an exclusion.**

``HUMAN_PATRON`` (22)
    Curated ``structure='HUMAN'``. Taken from the node's own curated structure, never from
    a name heuristic. Still addressable, still carries its dedications; it is simply not a
    member of the deity population.
``DANASTUTI_GIFT_PRAISE`` (7)
    Curated ``structure='PATRON_PRAISE'``. *dānastutiḥ*, "praise of a patron's gift", has
    50 dedications across 15 hymns and was the top-ranked member of a deity co-occurrence
    table once already, graded MISLEADING.
``ABSTRACTION_NOT_AN_ADDRESSEE`` (28)
    Ruled per label in ``data/staging/communities/abstract_label_rulings.json`` against the
    line ``DEVATA_TAXONOMY_V1`` sections 7-8 already drew: *does the label name an
    addressee with a domain, or does it name the hymn's subject or its intended effect?*
    Each carries its own recorded reason. The ruling is loaded from that file, never
    re-derived here, so there is one copy of the judgement.
``UNDECIDED`` (5)
    **Kept in the population**, with ``deity_eligibility_ruling='UNDECIDED'`` recorded on
    the node. An undecided label removed is a decision made by default. Ātmā, Annam,
    Brahma, Rāti and Śacī.

**Yajurvedic ritual implements are deities here and must stay so.** Kātyāyana's opening
sūtra admits *anas*, *śākhā*, *ukhā*, *kapāla*, *idhma* and *ulūkhala* among the devatās as
*pratimābhūta*. Eight are in this graph and all eight are eligible; :data:`RITUAL_IMPLEMENTS`
names them and :func:`check_rows` fails if any is excluded. A contamination sweep that
treats a ritual implement as noise is wrong about the Yajurveda, not about the data.

**The guard that earned itself.** :func:`rulings_for` raises if a ruling key resolves to no
``:Devata``, or if the ruling file does not cover the ABSTRACT/UNSPECIFIED population
exactly. In the communities build the same guard caught a run that silently applied 27 of
28 rulings and reported 158 eligible instead of 157, because one key was spelled
``SAMJNANAM`` against the graph's ``SANJNANAM``. A ruling that matches nothing is not
applied and, without the guard, not reported either.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:  # pragma: no cover - typing only
    from neo4j import Session

CONTRACT_VERSION: Final = "VG:DEITY_ELIGIBILITY:V1"

#: The one documented predicate. Every count over the deity population uses this string.
ELIGIBLE_DEITY_PREDICATE: Final = "d.is_deity = true"

#: The predicate a query must use UNTIL ``is_deity`` has landed on all 214 nodes.
#:
#: **Why a shim exists at all.** ``is_deity = true`` is the end state, but a query is code
#: and the property is data, and the two land in different changes. A shipped query that
#: reads a property the graph does not hold does not error -- Neo4j returns null, the
#: WHERE excludes every row, and the endpoint answers with an empty result that looks like
#: a finding. ``tests/api/test_cypher_property_hygiene.py`` exists because that exact
#: failure shipped once.
#:
#: So the shim reads the ruling where it exists and falls back to the strongest rule the
#: graph can state without it: the curated structure. Pre-landing it reads 185 (the 29
#: curated non-members excluded, the 28 ABSTRACT rulings not yet available); post-landing it
#: reads 157 and is identical to :data:`ELIGIBLE_DEITY_PREDICATE`. Both figures exclude the
#: 29 the closure test names; neither is the 192 that shipped.
#:
#: **Removal condition.** When ``MATCH (d:Devata) WHERE d.is_deity IS NULL RETURN count(d)``
#: is 0, replace every call with :data:`ELIGIBLE_DEITY_PREDICATE`. Queries that use the shim
#: must also return the count of unruled nodes, so the transitional state is typed in the
#: row rather than left to a caveat.
def eligible_predicate(alias: str = "d") -> str:
    """The convergent eligibility predicate for one Cypher alias."""
    return (
        f"coalesce({alias}.is_deity, "
        f"NOT coalesce({alias}.structure, 'UNSPECIFIED') IN ['HUMAN', 'PATRON_PRAISE'])"
    )


#: Repo root, so the ruling file resolves the same from a test runner, a script and the
#: API process. A relative default here reads as an empty ruling set from any other cwd,
#: and an empty ruling set raises rather than silently keeping all 42 -- but only because
#: :func:`rulings_for` checks coverage, so the anchor is what makes the error legible.
_REPO_ROOT: Final = pathlib.Path(__file__).resolve().parents[3]

#: Where the per-label ABSTRACT judgement lives. One copy, loaded, never re-derived.
ABSTRACT_RULINGS_PATH: Final = (
    _REPO_ROOT / "data" / "staging" / "communities" / "abstract_label_rulings.json"
)

#: Curated structures that are not deities, and the class each becomes.
STRUCTURE_EXCLUSIONS: Final[dict[str, str]] = {
    "HUMAN": "HUMAN_PATRON",
    "PATRON_PRAISE": "DANASTUTI_GIFT_PRAISE",
}

#: The structures whose membership is decided per label rather than by structure.
RULED_STRUCTURES: Final[frozenset[str]] = frozenset({"ABSTRACT", "UNSPECIFIED"})

#: Yajurvedic ritual implements admitted as *pratimābhūta*. Eligible, and asserted to be.
RITUAL_IMPLEMENTS: Final[frozenset[str]] = frozenset(
    {
        "VG:DEVATA:BARHIH",
        "VG:DEVATA:DEVIRDVARAH",
        "VG:DEVATA:GRAVANAH",
        "VG:DEVATA:HAVIRDHANE-SAKATE",
        "VG:DEVATA:ULUKHALAM",
        "VG:DEVATA:ULUKHALAMUSALE",
        "VG:DEVATA:VANASPATIH",
        "VG:DEVATA:YUPAH",
    }
)

#: The closed vocabulary of ``deity_eligibility_ruling``.
RULINGS: Final[frozenset[str]] = frozenset({"DEITY", "NOT_DEITY", "UNDECIDED"})


class RulingCoverageError(ValueError):
    """The ruling file and the graph population do not correspond exactly."""


@dataclass(frozen=True)
class EligibilityRow:
    """One ``:Devata``'s eligibility, with the basis and reason that produced it."""

    entity_key: str
    display_label: str | None
    structure: str | None
    is_deity: bool
    non_deity_kind: str | None
    ruling: str
    basis: str
    reason: str

    def as_properties(self) -> dict[str, Any]:
        return {
            "entity_key": self.entity_key,
            "is_deity": self.is_deity,
            "non_deity_kind": self.non_deity_kind,
            "deity_eligibility_ruling": self.ruling,
            "deity_eligibility_basis": self.basis,
            "deity_eligibility_reason": self.reason,
            "deity_eligibility_contract_version": CONTRACT_VERSION,
        }


def load_abstract_rulings(path: pathlib.Path | None = None) -> dict[str, dict[str, str]]:
    """The per-label ABSTRACT rulings, keyed by entity key."""
    source = path or ABSTRACT_RULINGS_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    rulings = {}
    for item in payload["rulings"]:
        ruling = str(item["ruling"])
        if ruling not in RULINGS:
            raise RulingCoverageError(
                f"{item['key']} carries ruling {ruling!r}, which is outside {sorted(RULINGS)}."
            )
        rulings[str(item["key"])] = {"ruling": ruling, "reason": str(item["reason"])}
    return rulings


def rulings_for(
    devatas: list[dict[str, Any]], rulings: dict[str, dict[str, str]]
) -> list[EligibilityRow]:
    """Every ``:Devata`` becomes exactly one :class:`EligibilityRow`, or this raises.

    ``devatas`` carries ``entity_key``, ``display_label`` and ``structure`` per node.
    """
    ruled_population = {
        str(row["entity_key"])
        for row in devatas
        if str(row.get("structure") or "UNSPECIFIED") in RULED_STRUCTURES
    }
    missing = sorted(ruled_population - set(rulings))
    orphaned = sorted(set(rulings) - ruled_population)
    if missing or orphaned:
        raise RulingCoverageError(
            "The ABSTRACT ruling file does not cover the graph population exactly. "
            f"Ruled in the graph but absent from the file: {missing}. "
            f"In the file but resolving to no ABSTRACT/UNSPECIFIED :Devata: {orphaned}. "
            "A ruling that matches nothing is not applied and must not be reported as if "
            "it were."
        )

    rows: list[EligibilityRow] = []
    for record in devatas:
        key = str(record["entity_key"])
        structure = str(record.get("structure") or "UNSPECIFIED")
        label = record.get("display_label")
        if structure in STRUCTURE_EXCLUSIONS:
            kind = STRUCTURE_EXCLUSIONS[structure]
            rows.append(
                EligibilityRow(
                    entity_key=key,
                    display_label=label,
                    structure=structure,
                    is_deity=False,
                    non_deity_kind=kind,
                    ruling="NOT_DEITY",
                    basis="CURATED_STRUCTURE",
                    reason=(
                        "Curated structure HUMAN: a named human patron the Anukramani puts "
                        "in the deity slot, not an addressee."
                        if kind == "HUMAN_PATRON"
                        else "Curated structure PATRON_PRAISE: a danastuti gift-praise "
                        "label, praise of a gift rather than an addressee."
                    ),
                )
            )
            continue
        if structure in RULED_STRUCTURES:
            ruling = rulings[key]
            not_deity = ruling["ruling"] == "NOT_DEITY"
            rows.append(
                EligibilityRow(
                    entity_key=key,
                    display_label=label,
                    structure=structure,
                    is_deity=not not_deity,
                    non_deity_kind="ABSTRACTION_NOT_AN_ADDRESSEE" if not_deity else None,
                    ruling=ruling["ruling"],
                    basis="ABSTRACT_LABEL_RULING",
                    reason=ruling["reason"],
                )
            )
            continue
        rows.append(
            EligibilityRow(
                entity_key=key,
                display_label=label,
                structure=structure,
                is_deity=True,
                non_deity_kind=None,
                ruling="DEITY",
                basis="CURATED_STRUCTURE",
                reason=(
                    f"Curated structure {structure}: an addressee the Anukramani ascribes "
                    "passages to. Ritual implements are included, per Katyayana's opening "
                    "sutra admitting them as pratimabhuta."
                ),
            )
        )
    return rows


DEVATA_QUERY: Final = (
    "MATCH (d:Devata) RETURN d.entity_key AS entity_key, "
    "d.display_label AS display_label, d.structure AS structure ORDER BY entity_key"
)


def rows_from_session(session: Session, path: pathlib.Path | None = None) -> list[EligibilityRow]:
    devatas = [dict(record) for record in session.run(DEVATA_QUERY)]
    return rulings_for(devatas, load_abstract_rulings(path))


def check_rows(rows: list[EligibilityRow]) -> dict[str, Any]:
    """The contract's gate. Each finding has a way to fail.

    ``every_node_typed``
        no ``:Devata`` may be left without a ruling.
    ``excludes_the_29``
        the curated non-members must all be excluded; this is the figure the closure test
        names.
    ``ritual_implements_retained``
        all eight *pratimābhūta* implements must be eligible. This is the assertion that
        stops a contamination sweep from being run over the Yajurveda.
    ``reasons_recorded``
        an exclusion without a reason is a rule applied implicitly, which is the thing the
        closure test forbids.
    """
    by_kind: dict[str, int] = {}
    for row in rows:
        if row.non_deity_kind:
            by_kind[row.non_deity_kind] = by_kind.get(row.non_deity_kind, 0) + 1
    curated_excluded = by_kind.get("HUMAN_PATRON", 0) + by_kind.get("DANASTUTI_GIFT_PRAISE", 0)
    eligible = [row for row in rows if row.is_deity]
    implements_excluded = sorted(
        row.entity_key for row in rows if row.entity_key in RITUAL_IMPLEMENTS and not row.is_deity
    )
    unreasoned = sorted(row.entity_key for row in rows if not row.reason)
    implements_present = {row.entity_key for row in rows} & RITUAL_IMPLEMENTS
    return {
        "devata_nodes": len(rows),
        "eligible_deities": len(eligible),
        "excluded": len(rows) - len(eligible),
        "excluded_by_kind": dict(sorted(by_kind.items())),
        "every_node_typed": all(row.ruling in RULINGS for row in rows),
        "excludes_the_29": curated_excluded == 29,
        "curated_non_members_excluded": curated_excluded,
        "ritual_implements_present": len(implements_present),
        "ritual_implements_retained": not implements_excluded,
        "ritual_implements_wrongly_excluded": implements_excluded,
        "reasons_recorded": not unreasoned,
        "rows_without_a_reason": unreasoned,
        "undecided_kept": sorted(row.entity_key for row in rows if row.ruling == "UNDECIDED"),
        "passes": (
            all(row.ruling in RULINGS for row in rows)
            and curated_excluded == 29
            and not implements_excluded
            and not unreasoned
        ),
    }
